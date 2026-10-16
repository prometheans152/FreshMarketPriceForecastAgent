"""Reject private stdout/input ambiguity: boolean ok and duplicate JSON keys."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from aiot_price.integrations.chatgpt_mcp import (
    WorkerStopped, execute_worker_async, worker_environment,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("raw", [
    '{"ok":null,"result":{}}',
    '{"ok":0,"result":{}}',
    '{"ok":"true","result":{}}',
    '{"ok":true,"ok":true,"result":{}}',
    '{"ok":true,"result":{"x":NaN}}',
])
def test_production_async_stdout_requires_strict_json_bool(raw, tmp_path):
    command = [sys.executable, "-X", "utf8", "-c", f"print({raw!r})"]
    async def verify():
        with pytest.raises(WorkerStopped):
            await execute_worker_async(
                command, {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "home"),
                expires_at=time.monotonic() + 3.0,
            )
    asyncio.run(verify())


def test_async_private_stdout_duplicate_key_is_rejected(tmp_path):
    command = [
        sys.executable, "-X", "utf8", "-c",
        'print(\'{"ok":true,"ok":true,"result":{}}\')',
    ]

    async def verify():
        with pytest.raises(WorkerStopped):
            await execute_worker_async(
                command, {"tool": "get_market_quote", "arguments": {}},
                worker_environment(tmp_path / "home"),
                expires_at=time.monotonic() + 3.0,
            )
    asyncio.run(verify())


def test_worker_stdin_rejects_duplicate_tool_name(tmp_path):
    command = [
        sys.executable, "-X", "utf8", "-m",
        "aiot_price.integrations.mcp_worker",
        "--release-dir", str(ROOT / "models" / "releases" / "0.1.0"),
    ]
    payload = (
        '{"tool":"get_market_quote","tool":"get_market_quote",'
        '"arguments":{"crop_id":"cabbage","market_id":"中義市場"}}'
    )
    env = worker_environment(tmp_path / "home")
    result = subprocess.run(
        command, input=payload, cwd=ROOT, env=env, text=True,
        capture_output=True, encoding="utf-8", timeout=15,
    )
    assert result.returncode == 2, result.stdout
    result_json = json.loads(result.stdout)
    assert result_json["ok"] is False
