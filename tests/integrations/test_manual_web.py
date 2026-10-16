"""Manual launch safety and isolated real HTTP A/B + record API."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aiot_price.integrations.manual_web import isolated_environment, main

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "models" / "releases" / "0.1.0"


def test_launcher_rejects_public_host():
    import pytest
    with pytest.raises(SystemExit) as e:
        main(["--host", "0.0.0.0"])
    assert e.value.code == 2


def test_initial_environment_scrubs_provider_names(monkeypatch, tmp_path):
    for name in ("AIOT_GLM_API_KEY", "AIOT_QWEN_BASE_URL", "AIOT_AGENT_PROFILE", "HERMES_API_KEY",
                 "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "NON_SECRET_TEST_CANARY")
    removed = isolated_environment(tmp_path / "home", RELEASE, tmp_path / "records")
    assert "AIOT_GLM_API_KEY" in removed
    assert "OPENAI_API_KEY" in removed
    assert "OPENAI_API_KEY" not in os.environ
    assert os.environ["AIOT_MANUAL_WEB"] == "1"
    assert os.environ["AIOT_RUNTIME_ISOLATED"] == "1"
    assert os.environ["HERMES_HOME"].startswith(str(tmp_path))
    assert os.environ["AIOT_RECORDS_DIR"] == str((tmp_path / "records").resolve())


def test_manual_subprocess_real_engine_records_and_no_agent_import(tmp_path):
    script = r"""
import builtins, json, sys
from pathlib import Path
from fastapi.testclient import TestClient
old_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith(("aiot_price.agent.service", "aiot_price.agent.providers",
                        "aiot_price.agent.hermes_runner")):
        raise AssertionError("manual runtime imported prohibited backend: "+name)
    return old_import(name, *args, **kwargs)
builtins.__import__ = guarded
from aiot_price.integrations.manual_web import isolated_environment
isolated_environment(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
from aiot_price.api.app import app
with TestClient(app) as client:
    assert client.get("/agent/status").json()["reason"] == "chat_disabled"
    banned = client.post("/agent/query", json={"query":"hello"})
    assert banned.status_code == 403 and banned.json()["error"]["code"]=="chat_disabled"
    assert client.get("/health").json()["status"] == "ready"
    args={"crop_id":"cabbage","market_id":"中義市場","current_price":32,
          "price_unit":"NTD_per_taiwan_jin",
          "observed_at":"2026-10-12T12:00:00+08:00",
          "mode":"without_last_week"}
    a = client.post("/forecast",json=args)
    assert a.status_code == 200 and len(a.json()["results"]) == 2
    assert a.json()["results"][0]["target_date"] == "2026-10-19"
    b=client.post("/forecast",json={**args,"mode":"both",
            "previous_price":29,"previous_price_unit":"NTD_per_taiwan_jin",
            "previous_observed_at":"2026-10-05T12:00:00+08:00"})
    assert b.status_code == 200 and len(b.json()["results_with_last_week"]) == 2
    fallback=client.post("/forecast",json={**args,"mode":"both",
            "previous_price":29,"previous_price_unit":"NTD_per_taiwan_jin",
            "previous_observed_at":"2026-10-01T12:00:00+08:00"})
    assert fallback.status_code == 200 and not fallback.json()["results_with_last_week"]
    assert client.get("/records").json()["records"]==[]
    assert client.post("/records",json={"request_id":"fake"}).status_code==404
    assert client.post("/records",json={"request_id":a.json()["request_id"],"out_dir":"C:/invalid"}).status_code==400
    saved=client.post("/records",json={"request_id":a.json()["request_id"]})
    assert saved.status_code==200, saved.text
    rid=saved.json()["record_id"]
    assert len(client.get("/records").json()["records"])==1
    assert len(client.get("/records/export").json()["records"])==1
    assert client.delete("/records/invalid/extra").status_code != 200
    assert client.delete("/records/"+rid).status_code==200
    assert client.get("/records").json()["records"]==[]
    print(json.dumps({"A":a.json()["mode_executed"],"B":b.json()["mode_executed"],
          "fallback":fallback.json()["mode_executed"],"saved_id":rid,
          "cutoff":a.json()["public_data_cutoff"]},ensure_ascii=False))
"""
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
           "PYTHONPATH": str(ROOT / "src"), "AIOT_RUNTIME_ISOLATED": "1"}
    p = subprocess.run([sys.executable, "-X", "utf8", "-c", script,
                        str(tmp_path / "home"), str(RELEASE), str(tmp_path / "records")],
                       cwd=ROOT, env=env, text=True, capture_output=True, timeout=45)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert '"B": "both"' in p.stdout
    assert list((tmp_path / "records").glob("prediction_*.json")) == []
