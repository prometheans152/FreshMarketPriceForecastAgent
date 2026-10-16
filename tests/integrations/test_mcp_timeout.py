"""Real child termination, and poisoned private stdout (not fake thread timeout)."""
from __future__ import annotations

import os
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from aiot_price.integrations.chatgpt_mcp import (
    HARD_TIMEOUT_SECONDS, WorkerStopped, execute_worker_async, worker_environment,
)


def test_hard_timeout_kills_real_worker(tmp_path):
    assert HARD_TIMEOUT_SECONDS == 15.0
    pid_file = tmp_path / "worker.pid"
    child = (
        "import os,time,pathlib; "
        + f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); "
        + "time.sleep(90)"
    )
    started = time.monotonic()
    with pytest.raises(WorkerStopped, match="15 秒"):
        asyncio.run(execute_worker_async(
            [sys.executable, "-X", "utf8", "-c", child],
            {"tool": "get_market_quote", "arguments": {}},
            worker_environment(tmp_path / "child_home"),
            expires_at=started + HARD_TIMEOUT_SECONDS,
        ))
    elapsed = time.monotonic() - started
    assert 15.0 <= elapsed < 20.0, f"no hard 15-second deadline: {elapsed}"
    assert pid_file.is_file(), "Child did not really start"
    pid = int(pid_file.read_text())
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        # Windows may retain an exited process object while another process
        # still holds a handle. OpenProcess success != STILL_RUNNING.
        if handle:
            try:
                exit_code = wintypes.DWORD()
                assert kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                assert exit_code.value != 259, f"worker pid {pid} still active"
            finally:
                kernel.CloseHandle(handle)
        else:
            assert ctypes.get_last_error() in (87, 1168), (
                "Process state was unobservable, not proven exited"
            )
    else:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    print(json.dumps({
        "event": "hard_timeout_worker_confirmed_killed",
        "hard_deadline_seconds": HARD_TIMEOUT_SECONDS,
        "elapsed_seconds": round(elapsed, 3),
        "original_child_pid": pid,
        "child_exited_confirmed": True,
        "worker_invocation": "synthetic sleep(90)",
        "model_gpu_used": False,
    }))


def test_worker_stdout_protocol_poison_rejected(tmp_path):
    poison = "import json;print('diagnostic on stdout');print(json.dumps({'ok':True,'result':{}}))"
    with pytest.raises(WorkerStopped, match="stdout"):
        asyncio.run(execute_worker_async(
            [sys.executable, "-X", "utf8", "-c", poison],
            {"tool": "get_market_quote", "arguments": {}},
            worker_environment(tmp_path / "home"),
            expires_at=time.monotonic() + 3.0,
        ))


def test_worker_env_does_not_forward_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOT_GLM_API_KEY", "NON_SECRET_SENTINEL")
    monkeypatch.setenv("OPENAI_API_KEY", "NON_SECRET_SENTINEL")
    monkeypatch.setenv("AIOT_QWEN_BASE_URL", "http://127.0.0.1:10000")
    env = worker_environment(tmp_path / "home")
    assert not any(x in env for x in ("AIOT_GLM_API_KEY", "OPENAI_API_KEY", "AIOT_QWEN_BASE_URL"))
    assert env["AIOT_RUNTIME_ISOLATED"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"
