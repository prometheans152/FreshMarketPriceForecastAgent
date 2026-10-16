"""Disposable real-Windows Job Object process for integration testing.

Run ONLY as a child interpreter under test_mcp_windows_job.py. Never import
this in a shared host or another persistent process. It cannot access the
original price model, credentials, network, or user private records.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from aiot_price.integrations.windows_job_guard import install_transport_job


def create_child_record(job, child_pid: int, evidence: Path):
    import win32api
    import win32con
    import win32job

    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, child_pid)
    member = bool(win32job.IsProcessInJob(handle, job))
    evidence.write_text(json.dumps({
        "parent_pid": os.getpid(), "child_pid": child_pid,
        "private_job_member": member,
    }), encoding="utf-8")
    if not member:
        raise AssertionError("Synthetic worker escaped the dedicated Windows job")


def simple_exiting_parent(job, evidence: Path):
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-c", "import time;time.sleep(90)"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    create_child_record(job, proc.pid, evidence)
    os._exit(70)  # job handle closing must terminate synthetic child


def held_forever_after_spawn_parent(job, evidence: Path):
    from aiot_price.integrations.chatgpt_mcp import (
        HARD_TIMEOUT_SECONDS, execute_worker_async, worker_environment,
    )

    actual_spawn = asyncio.create_subprocess_exec

    async def forever_after_launch(*args, **kwargs):
        proc = await actual_spawn(*args, **kwargs)
        create_child_record(job, proc.pid, evidence)
        await asyncio.Event().wait()  # deliberate permanent pending spawn
        return proc

    mode = os.environ.get("TW01_SYNTHETIC_FAILCLOSE_MODE", "pending")

    async def run():
        asyncio.create_subprocess_exec = forever_after_launch
        runner = asyncio.create_task(execute_worker_async(
            [sys.executable, "-X", "utf8", "-c", "import time;time.sleep(90)"],
            {"tool": "get_market_quote", "arguments": {}},
            worker_environment(evidence.parent / "worker_home"),
            expires_at=time.monotonic() + (1.0 if mode == "pending_cancel" else 0.3),
        ))
        if mode == "pending_cancel":
            for _ in range(100):
                if evidence.is_file():
                    break
                await asyncio.sleep(0.01)
            if not evidence.is_file():
                raise AssertionError("OS synthetic child did not start")
            runner.cancel()
            await asyncio.sleep(0)
            runner.cancel()
        await runner

    asyncio.run(run())
    raise AssertionError("Indefinite spawn unexpectedly returned a successful result")


def blocked_event_loop_parent(job, evidence: Path):
    """Simulate a synchronous OS process-start operation blocking the loop.

    Only a separate watchdog thread can act when the loop never yields.
    """
    from aiot_price.integrations.windows_job_guard import TransportDeadlineWatchdog

    child = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-c", "import time;time.sleep(90)"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    create_child_record(job, child.pid, evidence)
    guard = TransportDeadlineWatchdog(cleanup_seconds=0.5)
    guard.start()
    guard.register(time.monotonic() + 0.3)
    time.sleep(90)  # event loop thread has no chance to schedule callbacks
    raise AssertionError("Watchdog failed to kill the blocked transport")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("normal", "pending", "pending_cancel", "blocked_loop"):
        raise SystemExit("Usage: <normal|pending|pending_cancel|blocked_loop> <evidence.json>")
    job = install_transport_job()
    evidence_file = Path(sys.argv[2])
    if sys.argv[1] == "normal":
        simple_exiting_parent(job, evidence_file)
    elif sys.argv[1] == "blocked_loop":
        blocked_event_loop_parent(job, evidence_file)
    else:
        os.environ["TW01_SYNTHETIC_FAILCLOSE_MODE"] = sys.argv[1]
        held_forever_after_spawn_parent(job, evidence_file)
