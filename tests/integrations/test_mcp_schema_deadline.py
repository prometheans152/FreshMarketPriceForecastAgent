"""SDK input validation must execute inside the 15s production watchdog scope."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name("_mcp_schema_deadline_probe.py")


def test_native_input_schema_stall_is_killed_before_it_can_resume(tmp_path):
    assert os.name == "nt", "Real Job Object acceptance requires Windows"
    transport = os.environ.get("TW01_MCP_PYTHON")
    assert transport and Path(transport).is_file(), "Native schema acceptance requires TW01_MCP_PYTHON"
    from aiot_price.integrations.chatgpt_mcp import worker_environment
    evidence_root = Path(os.environ.get("TW01_LIFECYCLE_EVIDENCE_DIR", str(tmp_path)))
    directory = evidence_root / ("schema_" + tmp_path.name)
    directory.mkdir(parents=True, exist_ok=False)
    env = worker_environment(directory / "client_home")
    command = [transport, "-X", "utf8", str(HELPER), "client", str(directory), str(ROOT)]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=32,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / "client_stdout.log").write_bytes(result.stdout)
    (directory / "client_stderr.log").write_bytes(result.stderr)
    (directory / "command.json").write_text(json.dumps({
        "command": command, "env": env, "exit_code": result.returncode,
    }, indent=2), encoding="utf-8")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    record = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert record["validator_entered"] is True, record
    assert record["validator_resumed"] is False, record
    assert record["returned_success"] is False, record
    assert record["transport_exit"] is not None, record
    assert record["dispatch_start"] <= record["validator_entered_at"], record
    assert record["transport_exit"] <= record["client_dispatch_start"] + 15.5, record
    assert record["transport_exit"] <= record["work_deadline"] + 0.5, record
    assert record["cleanup_completed"] <= record["work_deadline"] + 4.0, record
