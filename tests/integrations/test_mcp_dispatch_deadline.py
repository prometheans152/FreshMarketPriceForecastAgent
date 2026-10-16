"""New DE06 follow-up: queue waiting and cancellation cannot strand a worker.

The existing 15s full worker test is preserved. These are separate shorter
private negative controls, not a reduced production tool timeout.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

from aiot_price.integrations.chatgpt_mcp import (
    HARD_TIMEOUT_SECONDS, WorkerStopped, acquire_dispatch_lock,
    _stop_async_worker, execute_worker_async, worker_environment,
)


def child_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error in (87, 1168):  # invalid process identifier / not found
                return False
            raise OSError(error, "Could not examine Windows child PID")
        try:
            exit_code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                raise OSError(ctypes.get_last_error(), "Unable to inspect child exit code")
            # Windows permits OpenProcess on an exited process while another
            # handle is open. A successful OpenProcess is *not* proof it runs.
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_lock_wait_counts_against_total_15_seconds():
    async def case():
        lock = asyncio.Lock()
        await lock.acquire()
        started = time.monotonic()
        with pytest.raises(WorkerStopped, match="排隊"):
            await acquire_dispatch_lock(lock, started + 0.15)
        assert time.monotonic() - started < 0.7
        assert lock.locked()  # This caller never acquired or released it.
        lock.release()
    assert HARD_TIMEOUT_SECONDS == 15.0
    asyncio.run(case())


def test_cancelled_tool_kills_child_without_lingering(tmp_path):
    pid_file = tmp_path / "cancelled_worker.pid"
    command = [sys.executable, "-X", "utf8", "-c",
               f"import os,time,pathlib;pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(90)"]

    async def case():
        started = time.monotonic()
        task = asyncio.create_task(execute_worker_async(
            command, {"tool": "get_market_quote", "arguments": {}},
            worker_environment(tmp_path / "home"), expires_at=started + HARD_TIMEOUT_SECONDS,
        ))
        for _ in range(80):
            if pid_file.is_file():
                break
            await asyncio.sleep(0.05)
        assert pid_file.is_file(), "worker did not start"
        pid = int(pid_file.read_text())
        assert child_alive(pid)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not child_alive(pid), "MCP cancellation left actual numeric worker running"
        assert time.monotonic() - started < 4.0
    asyncio.run(case())


def test_private_short_deadline_really_kills_slow_worker(tmp_path):
    pid_file = tmp_path / "deadline_worker.pid"
    command = [sys.executable, "-X", "utf8", "-c",
               f"import os,time,pathlib;pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(90)"]

    async def case():
        started = time.monotonic()
        with pytest.raises(WorkerStopped, match="15 秒"):
            await execute_worker_async(
                command, {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "home"), expires_at=started + 1.1,
            )
        assert pid_file.is_file()
        assert not child_alive(int(pid_file.read_text()))
        assert 1.0 <= time.monotonic() - started < 3.0
    asyncio.run(case())


def test_poisoned_worker_stdout_fails_closed(tmp_path):
    command = [sys.executable, "-X", "utf8", "-c",
               "print('diagnostic on stdout'); print('{\\\"ok\\\":true,\\\"result\\\":{}}')"]

    async def case():
        with pytest.raises(WorkerStopped, match="stdout"):
            await execute_worker_async(
                command, {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "home"), expires_at=time.monotonic() + 3.0,
            )
    asyncio.run(case())


def test_expired_during_result_decode_does_not_return_success(monkeypatch, tmp_path):
    """Slow protocol validation is included in the observed deadline outcome.

    No child remains alive. Blocking CPU decode cannot be interrupted at an
    exact millisecond; it must at least fail closed after the stalled check.
    """
    from aiot_price.integrations import chatgpt_contracts

    original = chatgpt_contracts.strict_json_loads

    def delayed_decode(raw):
        time.sleep(0.65)
        return original(raw)

    monkeypatch.setattr(chatgpt_contracts, "strict_json_loads", delayed_decode)
    command = [
        sys.executable, "-X", "utf8", "-c",
        'print(\'{"ok":true,"result":{"tool":"get_market_quote"}}\')',
    ]

    async def case():
        with pytest.raises(WorkerStopped, match="15 秒"):
            await execute_worker_async(
                command,
                {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "home"),
                expires_at=time.monotonic() + 0.4,
            )
    asyncio.run(case())


def test_repeated_cancel_during_child_exit_wait_does_not_skip_reaping():
    """A second cancellation cannot interrupt already-started child cleanup.

    Controlled process interface: real Windows PID kill/exit is exercised by
    test_cancelled_tool_kills_child_without_lingering and the JobObject probe.
    Here the wait is intentionally delayed to enlarge the second-cancel race.
    """
    class DelayedExitProcess:
        def __init__(self):
            self.returncode = None
            self.killed = False
            self.released = asyncio.Event()

        def kill(self):
            self.killed = True

        async def wait(self):
            await self.released.wait()
            self.returncode = -9
            return self.returncode

    async def case():
        proc = DelayedExitProcess()
        cleanup = asyncio.create_task(_stop_async_worker(proc))
        await asyncio.sleep(0)
        assert proc.killed
        cleanup.cancel()
        await asyncio.sleep(0)
        cleanup.cancel()
        await asyncio.sleep(0)
        assert not cleanup.done(), "Repeated cancellation prematurely released cleanup"
        proc.released.set()
        await asyncio.wait_for(cleanup, timeout=2.0)
        assert proc.returncode == -9

    asyncio.run(case())


def test_cancel_during_process_creation_cannot_leave_orphan(monkeypatch, tmp_path):
    """Interrupt after OS child exists but before create_subprocess_exec returns.

    The fake delay only enlarges a real cancellation window. Always terminate
    the synthetic sleeper in test cleanup, including while the candidate FAILS.
    """
    pid_file = tmp_path / "spawn_window_worker.pid"
    child_code = (
        "import os,time,pathlib;"
        + f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()));"
        + "time.sleep(90)"
    )
    command = [sys.executable, "-X", "utf8", "-c", child_code]
    original_spawn = asyncio.create_subprocess_exec

    async def case():
        started = asyncio.Event()
        release = asyncio.Event()
        child_ref = {}

        async def held_after_os_creation(*args, **kwargs):
            proc = await original_spawn(*args, **kwargs)
            child_ref["proc"] = proc
            started.set()
            await release.wait()  # deliberate cancellation before caller assignment
            return proc

        monkeypatch.setattr(asyncio, "create_subprocess_exec", held_after_os_creation)
        work = asyncio.create_task(execute_worker_async(
            command, {"tool": "get_market_quote", "arguments": {}},
            worker_environment(tmp_path / "isolated_home"),
            expires_at=time.monotonic() + HARD_TIMEOUT_SECONDS,
        ))
        try:
            await asyncio.wait_for(started.wait(), timeout=5.0)
            proc = child_ref["proc"]
            assert child_alive(proc.pid)
            if os.name == "nt":
                # CREATE_SUSPENDED prevents worker user code before the
                # Process handle is returned and its invocation job assigned.
                assert not pid_file.exists()
            work.cancel()
            # Deliver the cancellation while the child-creation coroutine is
            # still paused. It then resumes, so a shielding/cleanup strategy
            # can acquire and terminate the child rather than deadlocking.
            await asyncio.sleep(0)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(work, timeout=5.0)
            assert not child_alive(proc.pid), (
                "A canceled MCP request orphaned a child launched inside "
                "create_subprocess_exec() before it returned"
            )
        finally:
            release.set()
            if not work.done():
                work.cancel()
            if "proc" in child_ref:
                proc = child_ref["proc"]
                if child_alive(proc.pid):
                    proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5.0)

    asyncio.run(case())


def test_timeout_during_process_creation_requires_job_failclosed(monkeypatch, tmp_path):
    """Without a process handle at expiry, production exits its Job Object.

    A fake fail_closed_exit prevents this *shared pytest interpreter* from
    terminating. The real kernel-level process kill is exercised separately in
    test_mcp_windows_job.py within disposable job-owning interpreters.
    """
    pid_file = tmp_path / "slow_spawn.pid"
    child_code = (
        "import os,time,pathlib;"
        + f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()));"
        + "time.sleep(90)"
    )
    original_spawn = asyncio.create_subprocess_exec
    child_ref = {}
    from aiot_price.integrations import chatgpt_mcp

    class ExpectedJobAbort(RuntimeError):
        pass

    def test_only_abort(code):
        assert code == 125
        raise ExpectedJobAbort("dedicated transport must exit, closing job")

    monkeypatch.setattr(chatgpt_mcp, "fail_closed_exit", test_only_abort)

    async def pause_after_launch(*args, **kwargs):
        child = await original_spawn(*args, **kwargs)
        child_ref["proc"] = child
        await asyncio.sleep(0.9)  # exceeds this test's private 0.2s deadline
        return child

    async def case():
        monkeypatch.setattr(asyncio, "create_subprocess_exec", pause_after_launch)
        try:
            with pytest.raises(ExpectedJobAbort, match="dedicated transport"):
                await execute_worker_async(
                    [sys.executable, "-X", "utf8", "-c", child_code],
                    {"tool": "get_market_quote", "arguments": {}},
                    worker_environment(tmp_path / "isolated_home"),
                    expires_at=time.monotonic() + 0.2,
                )
            assert "proc" in child_ref, "negative test never created a process"
            # The synthetic child remains alive because pytest intercepted
            # os._exit; the kernel Job Object real test proves that production
            # exit kills it. Always clean up this mock's child below.
        finally:
            if "proc" in child_ref:
                child = child_ref["proc"]
                if child_alive(child.pid):
                    child.kill()
                await asyncio.wait_for(child.wait(), timeout=5.0)

    asyncio.run(case())


@pytest.mark.parametrize("stream,limit", [("stdout", 262144), ("stderr", 65536)])
def test_async_pipe_overflow_rejected_without_unbounded_communicate(
    monkeypatch, tmp_path, stream, limit
):
    """A malicious child must not be allowed to grow stdout/stderr unbounded.

    Avoid real OOM: write just one byte beyond the expected per-pipe bound,
    and make the old Process.communicate() explicitly fail if invoked.
    """
    async def reject_unbounded_communicate(self, *args, **kwargs):
        raise AssertionError("UNBOUNDED_PROCESS_COMMUNICATE_CALLED")

    monkeypatch.setattr(
        asyncio.subprocess.Process, "communicate", reject_unbounded_communicate,
    )
    child_code = (
        "import sys;"
        + f"sys.{stream}.buffer.write(b'X' * {limit + 1});"
        + f"sys.{stream}.flush()"
    )

    async def case():
        with pytest.raises(WorkerStopped, match=stream):
            await execute_worker_async(
                [sys.executable, "-X", "utf8", "-c", child_code],
                {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "isolated_home"),
                expires_at=time.monotonic() + 5.0,
            )

    asyncio.run(case())
