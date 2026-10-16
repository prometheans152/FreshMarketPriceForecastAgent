"""Invoke real SDK stdio process from separate venv; no REST/mock MCP substitute."""
from __future__ import annotations

import json
import copy
import os
import subprocess
import sys
import re
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _transport_configuration():
    run_dir = os.environ.get("TW01_MCP_RUN")
    transport = os.environ.get("TW01_MCP_PYTHON")
    if not run_dir or not transport:
        if os.environ.get("TW01_ACCEPTANCE") == "1":
            pytest.fail("Native acceptance requires TW01_MCP_RUN and TW01_MCP_PYTHON; skipping would hide missing coverage.")
        pytest.skip("Only the isolated transport SDK installation can run this test; set TW01_MCP_RUN and TW01_MCP_PYTHON.")
    return Path(run_dir), Path(transport)


def _assert_native_session(session):
    """Compare the wire against contracts and a separate genuine frozen-engine call."""
    from aiot_price.integrations.chatgpt_contracts import TOOL_SCHEMAS, ANNOTATIONS
    from aiot_price.agent.tools import AgentTools
    from aiot_price.models.predict import ForecastEngine

    assert session["session"] == "initialized"
    assert session["server_version"] == "0.1.0"
    tools = session["tools"]
    assert len(tools) == 2
    assert {tool["name"] for tool in tools} == {"get_market_quote", "post_forecast"}
    for tool in tools:
        assert tool["inputSchema"] == TOOL_SCHEMAS[tool["name"]]
        assert all(tool["annotations"][key] == value for key, value in ANNOTATIONS.items())
    calls = session["calls"]
    assert len(calls) == 6
    assert [bool(x["result"]["isError"]) for x in calls] == [False, False, False, True, True, True]
    engine_tools = AgentTools(ForecastEngine(ROOT / "models/releases/0.1.0"))
    for case in calls[:3]:
        structured = case["result"]["structuredContent"]
        assert structured["tool"] == case["name"]
        assert case["result"]["content"][0]["text"] == structured["fact_text"]
        if case["name"] == "get_market_quote":
            original = engine_tools.get_market_quote(**case["args"])
            assert structured["engine_result"] == original
            assert structured["price_age_days_at_query"] == (
                date.fromisoformat(structured["query_date"]) - date.fromisoformat(original["observed_date"])
            ).days
        else:
            given = case["args"]
            day = given.get("observed_on", structured["query_date"])
            expected_request = dict(crop_id=given["crop_id"], market_id=given["market_id"],
                current_price=float(given["current_price"]), price_unit=given["price_unit"],
                observed_at=day + "T12:00:00+08:00", mode="without_last_week", store_id=None)
            assert structured["normalized_request"] == expected_request
            assert structured["input_echo"] == {**given, "current_price":float(given["current_price"]), "observed_on":day}
            original = engine_tools.post_forecast(expected_request)
            actual = copy.deepcopy(structured["engine_result"])
            # ForecastEngine publishes req- plus a Taipei timestamp, per invocation.
            assert re.fullmatch(r"req-[0-9]{20}", actual.pop("request_id"))
            assert re.fullmatch(r"req-[0-9]{20}", original.pop("request_id"))
            assert actual == original
            assert [row["target_date"] for row in actual["results"]] == [
                date.fromordinal(date.fromisoformat(day).toordinal() + horizon).isoformat()
                for horizon in (7,14)
            ]


def test_acceptance_cannot_silently_skip_native(monkeypatch):
    monkeypatch.setenv("TW01_ACCEPTANCE", "1")
    monkeypatch.delenv("TW01_MCP_RUN", raising=False)
    monkeypatch.delenv("TW01_MCP_PYTHON", raising=False)
    with pytest.raises(pytest.fail.Exception, match="Native acceptance requires"):
        _transport_configuration()


def test_native_stdio_initialize_list_call_and_reject(tmp_path):
    run_dir, transport_path = _transport_configuration()
    transport = str(transport_path)
    script = run_dir / "DE06" / "native_probe.py"
    assert transport_path.is_file() and script.is_file()
    env = {
        **os.environ, "AIOT_RUNTIME_ISOLATED": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(ROOT / "src"),
    }
    cmd = [transport, "-X", "utf8", str(script), str(ROOT), transport,
           sys.executable, str(tmp_path / "session_home"), "from_pytest"]
    result = subprocess.run(cmd, text=True, capture_output=True, env=env, cwd=ROOT, timeout=90)
    assert result.returncode == 0, result.stderr[-5000:]
    session = json.loads(result.stdout)
    _assert_native_session(session)
    # Prove these stronger checks reject otherwise-successful forged wire copies.
    for mutation in ("name", "schema", "price", "date"):
        poisoned = copy.deepcopy(session)
        if mutation == "name":
            poisoned["tools"][0]["name"] = "save_record"
        elif mutation == "schema":
            poisoned["tools"][0]["inputSchema"]["additionalProperties"] = True
        elif mutation == "price":
            poisoned["calls"][1]["result"]["structuredContent"]["engine_result"]["results"][0]["price_estimate"] += 12
        else:
            poisoned["calls"][1]["result"]["structuredContent"]["engine_result"]["results"][0]["target_date"] = "2026-10-20"
        with pytest.raises(AssertionError):
            _assert_native_session(poisoned)
