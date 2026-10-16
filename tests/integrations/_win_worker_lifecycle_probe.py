"""Sacrificial Windows transport probe. Never import into pytest/COS/Web.

Every descendant here is a synthetic sleeper. No model/network/private data.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def write_record(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


def synthetic_worker(mode: str, identity: Path):
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(90)"],
        stdin=subprocess.DEVNULL,
        stdout=None if mode == "normal_inherited" else subprocess.DEVNULL,
        stderr=None if mode == "normal_inherited" else subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    write_record(identity, {"worker_pid": os.getpid(), "grandchild_pid": child.pid})
    if mode.startswith("normal"):
        sys.stdin.buffer.read()
        print(json.dumps({"ok": True, "result": {"synthetic": True}}), flush=True)
    else:
        time.sleep(90)


async def run_probe(mode: str, directory: Path):
    from aiot_price.integrations.chatgpt_mcp import (
        WorkerStopped, execute_worker_async, worker_environment,
    )
    from aiot_price.integrations.windows_job_guard import TransportDeadlineWatchdog
    if mode in ("terminate_failure", "accounting_failure"):
        import win32job
        def controlled_failure(*_args):
            raise OSError("Synthetic Windows cleanup API failure")
        if mode == "terminate_failure":
            win32job.TerminateJobObject = controlled_failure
        else:
            original_query = win32job.QueryInformationJobObject
            def failed_accounting(job, info_class):
                if info_class == win32job.JobObjectBasicAccountingInformation:
                    controlled_failure()
                return original_query(job, info_class)
            win32job.QueryInformationJobObject = failed_accounting

    identity = directory / "identity.json"
    started = time.monotonic()
    work_deadline = started + (15.0 if mode == "blocked_loop" else 1.2 if mode == "timeout" else 10.0)
    write_record(directory / "dispatch.json", {
        "transport_pid": os.getpid(), "dispatch_start": started,
        "work_deadline": work_deadline, "mode": mode,
    })
    command = [sys.executable, "-X", "utf8", __file__, "worker", mode, str(identity)]
    if mode == "blocked_loop":
        # The guard cannot depend on asyncio when a synchronous operation stalls.
        guard = TransportDeadlineWatchdog(cleanup_seconds=4.0)
        guard.start()
        guard.register(work_deadline)
        subprocess.Popen(command, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(90)
        raise AssertionError("Watchdog did not stop the blocked transport")

    task = asyncio.create_task(execute_worker_async(
        command, {"tool": "get_market_quote", "arguments": {}},
        worker_environment(directory / "worker_home"), expires_at=work_deadline,
    ))
    if mode in ("cancel", "terminate_failure", "accounting_failure"):
        while not identity.exists():
            if task.done():
                await task
            await asyncio.sleep(0.01)
        task.cancel()
    try:
        result = await task
        outcome = "returned"
    except asyncio.CancelledError:
        result, outcome = None, "cancelled"
    except WorkerStopped:
        result, outcome = None, "timeout"
    write_record(directory / "completed.json", {
        "outcome": outcome, "result": result,
        "executor_completed_at": time.monotonic(), "transport_pid": os.getpid(),
    })
    # Keep the real transport alive while its parent checks both descendant PIDs.
    while not (directory / "release_parent").exists():
        await asyncio.sleep(0.01)


async def run_ownership_failure(mode: str, directory: Path):
    from aiot_price.integrations import chatgpt_mcp, windows_job_guard
    import win32job
    real_spawn = asyncio.create_subprocess_exec
    captured = {}
    async def capture_pid(*args, **kwargs):
        proc = await real_spawn(*args, **kwargs)
        captured["proc"] = proc
        return proc
    def controlled_denial(*_args):
        raise OSError("Synthetic Windows ownership API denial")
    asyncio.create_subprocess_exec = capture_pid
    if mode == "assign_failure":
        win32job.AssignProcessToJobObject = controlled_denial
    else:
        windows_job_guard._resume_suspended_process = controlled_denial
    marker = directory / "worker_user_code_started"
    started = time.monotonic()
    outcome = None
    try:
        await chatgpt_mcp.execute_worker_async(
            [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
            {"tool": "get_market_quote", "arguments": {}},
            chatgpt_mcp.worker_environment(directory / "worker_home"),
            expires_at=started + 3.0,
        )
    except OSError:
        outcome = "ownership_denied"
    proc = captured.get("proc")
    if proc is None:
        raise AssertionError("Negative probe never launched a suspended process")
    write_record(directory / "failure_completed.json", {
        "outcome": outcome, "worker_pid": proc.pid,
        "worker_exit_code": proc.returncode,
        "worker_user_code_started": marker.exists(),
        "dispatch_start": started, "cleanup_completed": time.monotonic(),
    })


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        synthetic_worker(sys.argv[2], Path(sys.argv[3]))
    else:
        from aiot_price.integrations.windows_job_guard import install_transport_job
        install_transport_job()  # ONLY this sacrificial interpreter enters the job.
        if sys.argv[1] in ("assign_failure", "resume_failure"):
            asyncio.run(run_ownership_failure(sys.argv[1], Path(sys.argv[2])))
        else:
            asyncio.run(run_probe(sys.argv[1], Path(sys.argv[2])))
