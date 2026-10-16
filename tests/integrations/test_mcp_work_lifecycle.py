"""Catch work-deadline extensions and live-transport descendant leaks.

Real Windows jobs/abort only occur in a separate sacrificial interpreter.
"""
from __future__ import annotations

import json
import asyncio
import os
import subprocess
import threading
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name("_win_worker_lifecycle_probe.py")


def pid_running(pid):
    import win32api
    import win32con
    import win32event
    try:
        handle = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
    except Exception as exc:
        if getattr(exc, "winerror", None) == 87:
            return False
        raise
    try:
        return win32event.WaitForSingleObject(handle, 0) == win32con.WAIT_TIMEOUT
    finally:
        handle.Close()


def run_disposable(mode, tmp_path):
    assert os.name == "nt", "Acceptance requires the authorized Windows host"
    transport = os.environ.get("FMPA_MCP_PYTHON", os.environ.get("TW01_MCP_PYTHON"))
    assert transport and Path(transport).is_file(), "FMPA_MCP_PYTHON is required for acceptance"
    from aiot_price.integrations.chatgpt_mcp import worker_environment
    evidence_root = Path(os.environ.get(
        "FMPA_LIFECYCLE_EVIDENCE_DIR", os.environ.get("TW01_LIFECYCLE_EVIDENCE_DIR", str(tmp_path))))
    directory = evidence_root / (mode + "_" + tmp_path.name)
    directory.mkdir(parents=True, exist_ok=False)
    env = worker_environment(directory / "transport_home")
    command = [transport, "-X", "utf8", str(HELPER), mode, str(directory)]
    record = {"command": command, "env": env, "mode": mode,
              "timing_semantics": "Stop/exit times are first OS-confirmed observations, not scheduling guarantees"}
    proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    record["transport_pid"] = proc.pid
    record["actual_worker_stop"] = None
    record["grandchild_stop"] = None
    record["cleanup_completed"] = None
    record["transport_exit"] = None
    try:
        expect_abort = mode in ("blocked_loop", "terminate_failure", "accounting_failure")
        safety_deadline = time.monotonic() + (24.0 if mode == "blocked_loop" else 12.0)
        while not (directory / "identity.json").exists():
            assert proc.poll() is None, "Probe failed before any synthetic worker existed"
            assert time.monotonic() < safety_deadline, "No synthetic worker identity"
            time.sleep(0.01)
        identity = json.loads((directory / "identity.json").read_text(encoding="utf-8"))
        record.update(identity)
        record.update(json.loads((directory / "dispatch.json").read_text(encoding="utf-8")))
        while True:
            now = time.monotonic()
            if record["actual_worker_stop"] is None and not pid_running(identity["worker_pid"]):
                record["actual_worker_stop"] = now
            if record["grandchild_stop"] is None and not pid_running(identity["grandchild_pid"]):
                record["grandchild_stop"] = now
            if proc.poll() is not None and record["transport_exit"] is None:
                record["transport_exit"] = now
            if record["actual_worker_stop"] is not None and record["grandchild_stop"] is not None:
                record["cleanup_completed"] = now
            if expect_abort:
                if record["cleanup_completed"] is not None and record["transport_exit"] is not None:
                    break
            elif (directory / "completed.json").exists():
                record.update(json.loads((directory / "completed.json").read_text(encoding="utf-8")))
                record["transport_alive_after_call"] = proc.poll() is None
                record["worker_alive_after_call"] = pid_running(identity["worker_pid"])
                record["grandchild_alive_after_call"] = pid_running(identity["grandchild_pid"])
                # OS exit may occur between the first poll above and this
                # completed-call poll. Record this confirmation too, so a
                # stopped tree cannot have contradictory missing timestamps.
                confirmed_at = time.monotonic()
                if not record["worker_alive_after_call"]:
                    record["actual_worker_stop"] = record["actual_worker_stop"] or confirmed_at
                if not record["grandchild_alive_after_call"]:
                    record["grandchild_stop"] = record["grandchild_stop"] or confirmed_at
                if not record["worker_alive_after_call"] and not record["grandchild_alive_after_call"]:
                    record["cleanup_completed"] = confirmed_at
                break
            assert now < safety_deadline, "Disposable probe exceeded its external safety bound"
            time.sleep(0.005)
        return record
    finally:
        (directory / "release_parent").touch()
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate(timeout=5)
        record["exit_code"] = proc.returncode
        record["transport_exit"] = record["transport_exit"] or time.monotonic()
        (directory / "stdout.log").write_bytes(out)
        (directory / "stderr.log").write_bytes(err)
        (directory / "observed.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def test_blocked_sync_work_stops_at_15_seconds_before_cleanup_allowance(tmp_path):
    record = run_disposable("blocked_loop", tmp_path)
    assert record["exit_code"] == 125
    # 0.5s is an explicit OS observer tolerance, never added to the tool budget.
    assert record["actual_worker_stop"] <= record["work_deadline"] + 0.5, record
    assert record["cleanup_completed"] <= record["work_deadline"] + 4.0, record
    assert record["transport_exit"] <= record["work_deadline"] + 0.5, record


@pytest.mark.parametrize("mode,outcome", [
    ("normal", "returned"), ("normal_inherited", "returned"),
    ("cancel", "cancelled"), ("timeout", "timeout"),
])
def test_worker_descendants_stop_while_transport_is_still_alive(mode, outcome, tmp_path):
    record = run_disposable(mode, tmp_path)
    assert record["outcome"] == outcome, record
    assert record["transport_alive_after_call"] is True, record
    assert record["worker_alive_after_call"] is False, record
    assert record["grandchild_alive_after_call"] is False, record
    assert record["cleanup_completed"] is not None, record
    if mode == "timeout":
        assert record["actual_worker_stop"] <= record["work_deadline"] + 0.5, record
        assert record["cleanup_completed"] <= record["work_deadline"] + 4.0, record


@pytest.mark.parametrize("mode", ["assign_failure", "resume_failure"])
def test_suspended_worker_ownership_failure_cannot_execute_or_leak(mode, tmp_path):
    from aiot_price.integrations.chatgpt_mcp import worker_environment
    transport = os.environ.get("FMPA_MCP_PYTHON", os.environ.get("TW01_MCP_PYTHON"))
    assert transport and Path(transport).is_file(), "FMPA_MCP_PYTHON is required for acceptance"
    evidence_root = Path(os.environ.get(
        "FMPA_LIFECYCLE_EVIDENCE_DIR", os.environ.get("TW01_LIFECYCLE_EVIDENCE_DIR", str(tmp_path))))
    directory = evidence_root / (mode + "_" + tmp_path.name)
    directory.mkdir(parents=True, exist_ok=False)
    env = worker_environment(directory / "transport_home")
    command = [transport, "-X", "utf8", str(HELPER), mode, str(directory)]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=8)
    (directory / "stdout.log").write_bytes(result.stdout)
    (directory / "stderr.log").write_bytes(result.stderr)
    record = json.loads((directory / "failure_completed.json").read_text(encoding="utf-8"))
    record.update({"command": command, "env": env, "transport_exit_code": result.returncode})
    (directory / "observed.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    assert record["outcome"] == "ownership_denied"
    assert record["worker_user_code_started"] is False
    assert record["worker_exit_code"] is not None
    assert not pid_running(record["worker_pid"])
    assert record["cleanup_completed"] - record["dispatch_start"] < 4.0


@pytest.mark.parametrize("mode", ["terminate_failure", "accounting_failure"])
def test_unverifiable_tree_cleanup_aborts_dedicated_transport(mode, tmp_path):
    record = run_disposable(mode, tmp_path)
    assert record["exit_code"] == 125, record
    assert record["actual_worker_stop"] is not None, record
    assert record["grandchild_stop"] is not None, record
    assert record["cleanup_completed"] - record["dispatch_start"] < 4.0, record


def test_watchdog_expiry_is_atomic_with_unregister(monkeypatch):
    """Removing the condition lock around the abort decision must fail this test."""
    from aiot_price.integrations import windows_job_guard
    abort_entered = threading.Event()
    allow_abort = threading.Event()
    unregistered = threading.Event()
    def controlled_abort(code):
        assert code == 125
        abort_entered.set()
        assert allow_abort.wait(2)
    monkeypatch.setattr(windows_job_guard, "fail_closed_exit", controlled_abort)
    guard = windows_job_guard.TransportDeadlineWatchdog(cleanup_seconds=0.1)
    guard.start()
    token = guard.register(time.monotonic() + 0.05)
    runner = threading.Thread(target=lambda: (guard.unregister(token), unregistered.set()))
    try:
        assert abort_entered.wait(1)
        runner.start()
        assert not unregistered.wait(0.1), "unregister passed an in-progress expiry decision"
    finally:
        allow_abort.set()
        if runner.ident is not None:
            runner.join(2)
        guard.stop()
    assert unregistered.is_set()


def test_early_async_timer_does_not_consume_remaining_work_budget(monkeypatch, tmp_path):
    """An early timer tick must not classify a call as past its work deadline."""
    from aiot_price.integrations import chatgpt_mcp
    async def early_timer(*args, **kwargs):
        raise asyncio.TimeoutError()
    monkeypatch.setattr(chatgpt_mcp, "_bounded_communicate_worker", early_timer)
    async def case():
        started = time.monotonic()
        with pytest.raises(chatgpt_mcp.WorkerStopped, match="15 秒"):
            await chatgpt_mcp.execute_worker_async(
                [sys.executable, "-c", "import time; time.sleep(90)"],
                {"tool": "get_market_quote", "arguments": {}},
                chatgpt_mcp.worker_environment(tmp_path / "worker_home"),
                expires_at=started + 0.3,
            )
        assert time.monotonic() >= started + 0.3
    asyncio.run(case())
