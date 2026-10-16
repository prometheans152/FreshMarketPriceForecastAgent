"""Real kernel process-tree no-orphan guarantee in a disposable Windows child.

Do not assign the normal pytest interpreter or COS host to a Job Object.
Both tests start a separate sacrificial Python parent and only synthetic
time.sleep(90) children. The original release, model, GPU and network stay off.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name("_win_job_failclosed_worker.py")


def windows_pid_is_running(pid: int) -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        error_code = ctypes.get_last_error()
        if error_code == 87:
            return False
        raise OSError(error_code, "Unable to inspect synthetic worker PID")
    try:
        value = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(value)):
            raise OSError(ctypes.get_last_error(), "Unable to confirm worker exit")
        return value.value == 259
    finally:
        kernel.CloseHandle(handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object only")
@pytest.mark.parametrize("mode,expected_exit", [
    ("normal", 70),
    ("pending", 125),
    ("pending_cancel", 125),
    ("blocked_loop", 125),
])
def test_private_job_closure_kills_synthetic_worker(mode, expected_exit, tmp_path):
    evidence = tmp_path / (mode + "_process.json")
    home = tmp_path / "client_home"
    home.mkdir()
    allowed = {key: os.environ[key] for key in (
        "SystemRoot", "SYSTEMROOT", "WINDIR", "COMSPEC",
        "PATH", "PATHEXT", "TEMP", "TMP",
    ) if key in os.environ}
    allowed.update({
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "AIOT_RUNTIME_ISOLATED": "1",
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
    })
    parent = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(HELPER), mode, str(evidence)],
        cwd=ROOT, env=allowed,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        _out, err = parent.communicate(timeout=12)
        assert parent.returncode == expected_exit, (
            f"Disposable transport returned {parent.returncode}: {err[:2000]!r}"
        )
        record = json.loads(evidence.read_text(encoding="utf-8"))
        assert record["private_job_member"] is True
        pid = record["child_pid"]
        for _ in range(60):
            if not windows_pid_is_running(pid):
                break
            time.sleep(0.1)
        else:
            raise AssertionError(f"Private Job Object left synthetic worker {pid} alive")
        assert not windows_pid_is_running(pid)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=4)


def test_watchdog_normal_completion_and_shutdown_do_not_abort(monkeypatch):
    """A completed MCP call must not kill its transport during cleanup.

    This test never installs a Job Object in the shared pytest interpreter.
    The real fail-closed exit is tested only in the disposable child process.
    """
    from aiot_price.integrations import windows_job_guard

    unexpected_aborts = []
    monkeypatch.setattr(
        windows_job_guard, "fail_closed_exit", lambda code: unexpected_aborts.append(code)
    )
    guard = windows_job_guard.TransportDeadlineWatchdog(cleanup_seconds=0.1)
    guard.start()
    token = guard.register(time.monotonic() + 0.1)
    guard.unregister(token)
    # If either the call or the transport finished, the expiration of a past
    # deadline must not cause a spurious kill-on-close trigger.
    time.sleep(0.3)
    other = guard.register(time.monotonic() + 0.1)
    guard.stop()  # even if an MCP shutdown begins while a request is pending
    time.sleep(0.3)
    assert other >= 0
    assert unexpected_aborts == []
    assert not guard._thread.is_alive()
