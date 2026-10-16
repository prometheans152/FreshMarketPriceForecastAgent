"""Personal TW01 stdio MCP transport, no ML or model API SDK in this interpreter.

One worker per tool call (serial). Every call has an unmodifiable 15s deadline.
On timeout the actual worker process is killed, then a human must restart this
transport and any tunnel client; no implicit reconnection is claimed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from aiot_price.integrations.windows_job_guard import (
    TransportDeadlineWatchdog, WorkerProcessJob, fail_closed_exit, install_transport_job,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKER_MODULE = "aiot_price.integrations.mcp_worker"
HARD_TIMEOUT_SECONDS = 15.0
MAX_PROCESS_CLEANUP_SECONDS = 4.0
MAX_WORKER_STDOUT_BYTES = 262144
MAX_WORKER_STDERR_BYTES = 65536


class WorkerStopped(RuntimeError):
    """Timeout or controlled subprocess failure."""


def worker_environment(home: Path) -> dict[str, str]:
    """Allowlist only OS process essentials. Never inherit credentials/provider URLs."""
    home = home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    temporary = home / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    env = {k: os.environ[k] for k in (
        "SystemRoot", "SYSTEMROOT", "WINDIR", "COMSPEC",
        "PATH", "PATHEXT", "TEMP", "TMP", "NUMBER_OF_PROCESSORS",
    ) if k in os.environ}
    env.update({
        "HOME": str(home), "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "XDG_CONFIG_HOME": str(home / "xdg" / "config"),
        "XDG_DATA_HOME": str(home / "xdg" / "data"),
        "XDG_CACHE_HOME": str(home / "xdg" / "cache"),
        "HERMES_HOME": str(home / "hermes"),
        "AIOT_HERMES_HOME": str(home / "aiot_hermes"),
        "AIOT_RUNTIME_ISOLATED": "1",
        "TEMP": str(temporary), "TMP": str(temporary), "TMPDIR": str(temporary),
        "AIOT_MCP_SNAPSHOT_DIR": str(temporary),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    })
    return env


def _fixed_command(worker_python: Path, release_dir: Path) -> list[str]:
    return [str(worker_python.resolve()), "-X", "utf8", "-m", WORKER_MODULE,
            "--release-dir", str(release_dir.resolve())]


async def acquire_dispatch_lock(lock: asyncio.Lock, expires_at: float) -> None:
    """Queue time is part of the same 15-second dispatch-to-result budget."""
    remaining = expires_at - time.monotonic()
    if remaining <= 0:
        raise WorkerStopped("工具排隊等待超過 15 秒上限，未啟動數值 worker。")
    try:
        await asyncio.wait_for(lock.acquire(), timeout=remaining)
    except asyncio.TimeoutError as exc:
        raise WorkerStopped("工具排隊等待超過 15 秒上限，未啟動數值 worker。") from exc


async def _stop_async_worker(
    proc: asyncio.subprocess.Process | None, worker_job: WorkerProcessJob | None = None,
) -> None:
    """Stop the invocation tree, then confirm exit within a separate 4s bound."""
    if worker_job is not None:
        worker_job.terminate()
    if proc is None:
        return
    if proc.returncode is None:
        try:
            # Also handles a suspended process whose job assignment failed.
            proc.kill()
        except ProcessLookupError:
            pass
    # A second cancellation may arrive while waiting for the child to exit.
    # Protect the same wait task; never return before it finishes or its
    # independent cleanup deadline has expired.
    wait_task = asyncio.create_task(proc.wait())
    cleanup_deadline = time.monotonic() + MAX_PROCESS_CLEANUP_SECONDS
    while not wait_task.done() or (
        worker_job is not None and worker_job.active_processes() != 0
    ):
        remaining = cleanup_deadline - time.monotonic()
        if remaining <= 0:
            fail_closed_exit(125)
        try:
            if not wait_task.done():
                await asyncio.wait_for(asyncio.shield(wait_task), timeout=remaining)
            else:
                await asyncio.sleep(min(0.01, remaining))
        except asyncio.CancelledError:
            continue
        except asyncio.TimeoutError:
            fail_closed_exit(125)
    wait_task.result()
    if proc.returncode is None:
        fail_closed_exit(126)


async def _stop_child_after_pending_spawn(spawn_task: asyncio.Task, expires_at: float) -> None:
    """Reap a late child within a finite independent cleanup deadline.

    The requesting MCP call may have been cancelled *after the OS launched*
    the child but before create_subprocess_exec returned. Cancelling that
    coroutine directly loses the handle. Keep it alive until we can kill/reap
    the child, even if the caller requests a second cancellation.  If the OS
    spawn never yields a handle, fail closed by exiting the dedicated transport;
    the private Windows Job Object then kills children at the kernel level.
    """
    async def collect_and_stop():
        try:
            created = await asyncio.shield(spawn_task)
        except (Exception, asyncio.CancelledError):
            # No process handle was returned (e.g. OS denied creation).
            return
        await _stop_async_worker(created)

    cleaner = asyncio.create_task(collect_and_stop())
    # The job-backed transport must never spend four *extra* seconds waiting
    # for a spawn that has no Process handle after its 15-second deadline.
    # Closing the dedicated transport kills job children at the kernel level.
    cleanup_deadline = min(
        time.monotonic() + MAX_PROCESS_CLEANUP_SECONDS, expires_at,
    )
    while not cleaner.done():
        remaining = cleanup_deadline - time.monotonic()
        if remaining <= 0:
            fail_closed_exit(125)
        try:
            await asyncio.wait_for(asyncio.shield(cleaner), timeout=remaining)
        except asyncio.CancelledError:
            # Repeat cancellation must not abandon a launched OS process.
            continue
        except asyncio.TimeoutError:
            fail_closed_exit(125)
    cleaner.result()


async def _read_limited_worker_pipe(reader: asyncio.StreamReader, limit: int, label: str) -> bytes:
    """Drain a child pipe in chunks; fail immediately when its bound is exceeded.

    Unlike Process.communicate(), this does not accumulate an unbounded stream
    in the long-lived MCP transport. The caller must kill/reap on any error.
    """
    pieces = []
    total = 0
    while True:
        chunk = await reader.read(65536)
        if not chunk:
            return b"".join(pieces)
        total += len(chunk)
        if total > limit:
            raise WorkerStopped(f"worker {label} 超過大小上限；已拒收回應。")
        pieces.append(chunk)


async def _write_worker_input(writer: asyncio.StreamWriter, encoded: bytes) -> None:
    try:
        writer.write(encoded)
        await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        # A malformed worker may close stdin early; its bounded stdout/stderr
        # and actual exit code still determine whether the call is accepted.
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (BrokenPipeError, ConnectionResetError):
            pass


async def _bounded_communicate_worker(
    proc: asyncio.subprocess.Process, encoded: bytes, expires_at: float,
    worker_job: WorkerProcessJob | None = None,
) -> tuple[bytes, bytes]:
    """Concurrently drain both pipes with fixed memory and time limits."""
    if proc.stdin is None or proc.stdout is None or proc.stderr is None:
        raise WorkerStopped("worker stdio pipe 未建立；拒絕執行。")
    async def wait_for_worker_tree():
        if worker_job is not None:
            # A descendant may keep inherited pipes open after the direct
            # worker exits. Observe its OS exit independently of pipe EOF,
            # terminate its invocation job, then let the bounded readers drain.
            while proc.returncode is None:
                await asyncio.sleep(0.01)
            await _stop_async_worker(proc, worker_job)
        else:
            await proc.wait()

    tasks = [
        asyncio.create_task(_read_limited_worker_pipe(
            proc.stdout, MAX_WORKER_STDOUT_BYTES, "stdout")),
        asyncio.create_task(_read_limited_worker_pipe(
            proc.stderr, MAX_WORKER_STDERR_BYTES, "stderr")),
        asyncio.create_task(_write_worker_input(proc.stdin, encoded)),
        asyncio.create_task(wait_for_worker_tree()),
    ]
    try:
        remaining = expires_at - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        stdout, stderr, _, _ = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=remaining,
        )
        return stdout, stderr
    finally:
        # If any stream was too large, the request cancels the remaining
        # readers/writer before the outer worker cleanup kills the child.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def execute_worker_async(
    command: list[str],
    payload: dict,
    env: dict[str, str],
    *,
    expires_at: float,
) -> dict:
    """Cancellation-safe real Windows child; expires_at includes lock wait.

    Only the private server passes the command and absolute monotonic deadline.
    MCP callers cannot specify either parameter.
    """
    if time.monotonic() >= expires_at:
        raise WorkerStopped("工具排隊等待超過 15 秒上限，未啟動數值 worker。")
    proc = None
    spawn_task = None
    worker_job = None
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        remaining = expires_at - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        if os.name == "nt":
            worker_job = WorkerProcessJob()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if worker_job is not None:
            creationflags |= 0x00000004  # Win32 CREATE_SUSPENDED (not exported by subprocess)
        spawn_task = asyncio.create_task(asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            env=env,
            creationflags=creationflags,
        ))
        # The absolute deadline covers the *wait* for process creation as well.
        # Shielding prevents cancellation from discarding an already-created
        # Windows child before its Process handle reaches the caller.
        proc = await asyncio.wait_for(asyncio.shield(spawn_task), timeout=remaining)
        remaining = expires_at - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        if worker_job is not None:
            # The numeric worker cannot execute or create descendants before
            # it has entered its private invocation job.
            worker_job.attach_and_resume(proc.pid)
        out, _stderr = await _bounded_communicate_worker(proc, encoded, expires_at, worker_job)
        if proc.returncode not in (0, 2) or len(out) > 262144:
            raise WorkerStopped("預測工作程序失敗或輸出異常。")
        try:
            from aiot_price.integrations.chatgpt_contracts import strict_json_loads
            decoded = strict_json_loads(out.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise WorkerStopped("工作程序回傳非預期的 stdout 格式。") from exc
        if not isinstance(decoded, dict) or (
            set(decoded) not in ({"ok", "result"}, {"ok", "error"})
        ):
            raise WorkerStopped("工作程序回應結構不合法。")
        if decoded.get("ok") is False:
            raise WorkerStopped(str(decoded.get("error", "工具執行失敗。"))[:300])
        if decoded.get("ok") is not True or "result" not in decoded:
            raise WorkerStopped("工作程序回應缺失成功結果。")
        if time.monotonic() >= expires_at:
            # Decode can finish after the worker itself exited, but may not
            # convert a time-expired call into a successful result.
            raise asyncio.TimeoutError()
        return decoded["result"]
    except asyncio.TimeoutError as exc:
        # Windows asyncio timers may wake one clock-resolution tick early.
        # The absolute monotonic deadline, not that wakeup, defines expiry.
        # Cancellation still reaches finally immediately; the independent
        # watchdog cannot let a blocked loop turn this into extra work time.
        while time.monotonic() < expires_at:
            await asyncio.sleep(expires_at - time.monotonic())
        if proc is None and spawn_task is not None:
            await _stop_child_after_pending_spawn(spawn_task, expires_at)
        else:
            await _stop_async_worker(proc, worker_job)
        raise WorkerStopped("數值工具已超過 15 秒上限，worker 已終止。請人工重開 MCP 程序。") from exc
    except asyncio.CancelledError:
        # A disconnected/cancelled MCP call must not leave an orphan subprocess.
        if proc is None and spawn_task is not None:
            await _stop_child_after_pending_spawn(spawn_task, expires_at)
        else:
            await _stop_async_worker(proc, worker_job)
        raise
    finally:
        try:
            await _stop_async_worker(proc, worker_job)
        finally:
            if worker_job is not None:
                worker_job.close()


async def serve(worker_python: Path, release_dir: Path, home: Path):
    # Imports happen in transport venv only; no pandas, sklearn, AgentTools here.
    from mcp import types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from aiot_price.integrations.bounded_stdio import BoundedStdin
    import jsonschema

    from aiot_price.integrations.chatgpt_contracts import (
        ANNOTATIONS, OUTPUT_SCHEMA, TOOL_DESCRIPTIONS, TOOL_NAMES, TOOL_SCHEMAS,
        validate_arguments,
    )

    srv = Server("tw01-personal-prices", version="0.1.0",
                 instructions="只讀公開行情與 A 預測；必須問清品項、臺中市場與店價及單位。"
                              "不可聲稱即時店價、同店準確或提供 B／保存。")
    lock = asyncio.Lock()
    env = worker_environment(home)
    command = _fixed_command(worker_python, release_dir)
    exhausted = False
    watchdog = TransportDeadlineWatchdog(cleanup_seconds=MAX_PROCESS_CLEANUP_SECONDS)
    watchdog.start()

    @srv.list_tools()
    async def list_tools():
        return [types.Tool(
            name=name, description=TOOL_DESCRIPTIONS[name],
            inputSchema=TOOL_SCHEMAS[name], outputSchema=OUTPUT_SCHEMA,
            annotations=types.ToolAnnotations(**ANNOTATIONS),
        ) for name in TOOL_NAMES]

    async def call_tool_guarded(name: str, arguments: dict, expires_at: float):
        nonlocal exhausted
        try:
            await acquire_dispatch_lock(lock, expires_at)
        except WorkerStopped as exc:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(exc))], isError=True,
            )
        try:
            try:
                # Validate again inside transport before crossing numeric process.
                cleaned = validate_arguments(name, arguments)
                jsonschema.validate(arguments, TOOL_SCHEMAS[name])
                if exhausted:
                    raise WorkerStopped("worker 曾超時；請先人工重啟 MCP 程序。")
                result = await execute_worker_async(
                    command, {"tool": name, "arguments": cleaned}, env,
                    expires_at=expires_at,
                )
                jsonschema.validate(result, OUTPUT_SCHEMA)
                if time.monotonic() >= expires_at:
                    raise WorkerStopped("結果驗證超過 15 秒上限，請人工重啟 MCP 程序。")
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=result["fact_text"])],
                    structuredContent=result, isError=False,
                )
            except WorkerStopped as exc:
                if "超過 15 秒" in str(exc):
                    exhausted = True
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=str(exc))],
                    isError=True,
                )
            except Exception as exc:
                # Do not echo caller-supplied arbitrary error contents.
                message = str(exc) if type(exc).__name__ == "ContractError" else "工具參數或輸出不符合安全契約。"
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=message[:350])], isError=True,
                )
        finally:
            lock.release()

    @srv.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: dict):
        # Starts before lock wait and our input/output schema validation plus
        # worker decode. Bounded ingress framing and SDK parsing precede this
        # handler. A separate watchdog thread handles a blocked event loop.
        expires_at = time.monotonic() + HARD_TIMEOUT_SECONDS
        token = watchdog.register(expires_at)
        try:
            return await call_tool_guarded(name, arguments, expires_at)
        finally:
            watchdog.unregister(token)

    try:
        async with stdio_server(stdin=BoundedStdin()) as (read_stream, write_stream):
            await srv.run(read_stream, write_stream, srv.create_initialization_options())
    finally:
        watchdog.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description="TW01 personal stdio MCP server")
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--worker-python", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.worker_python.is_file():
        parser.error("Numeric worker Python interpreter does not exist.")
    if not args.release_dir.is_dir():
        parser.error("Frozen release directory does not exist.")
    # Fail closed before MCP initialization if any frozen file drifted. Only
    # stdlib hashing is imported here, never joblib or the ML runtime.
    from aiot_price.integrations.chatgpt_adapter import verify_frozen_release
    try:
        verify_frozen_release(args.release_dir)
    except Exception as exc:
        parser.error(f"Frozen release preflight failed: {type(exc).__name__}")
    # Must hold transport home, not the user's personal provider HOME.
    for key, value in worker_environment(args.home).items():
        if key not in ("PYTHONPATH",):
            os.environ[key] = value
    os.environ["AIOT_RUNTIME_ISOLATED"] = "1"
    # Must happen only in this dedicated Python transport, never in the COS
    # process or manual web server. Fail startup on unsupported Windows jobs.
    install_transport_job()
    asyncio.run(serve(args.worker_python, args.release_dir, args.home))


if __name__ == "__main__":
    main()
