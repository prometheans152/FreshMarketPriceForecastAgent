"""In-process tests of real frozen engine (no mock for prediction values)."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aiot_price.integrations.chatgpt_adapter import verify_frozen_release
from aiot_price.integrations.chatgpt_contracts import normalized_forecast_request, validate_arguments
from aiot_price.models.predict import ForecastEngine
from aiot_price.agent.tools import AgentTools

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "models" / "releases" / "0.1.0"
_spec = importlib.util.spec_from_file_location("tw01_oracle_api_test", Path(__file__).with_name("forecastengine_api.py"))
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)

FAKE_TEST_TOKEN = "test_only_" + "x" * 48


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv("TW01_ORIGIN_API_TOKEN", FAKE_TEST_TOKEN)
    monkeypatch.setenv("TW01_RELEASE_DIR", str(RELEASE))
    # Avoid the global rate limiter impacting independent test scenarios.
    api._timestamps.clear()


@pytest.fixture
def client():
    return TestClient(api.app)


def call(client, body=None, path="/v1/forecast", token=FAKE_TEST_TOKEN):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    return client.post(path, headers=headers, json=body)


BASE = {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
        "price_unit": "NTD_per_taiwan_jin", "observed_on": "2026-10-14"}


def test_health_true_release(client):
    verify_frozen_release(RELEASE)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "model_version": "0.1.0",
                        "data_version": "172dffc76e82", "public_data_cutoff": "2026-10-02",
                        "modes": ["A"], "horizons_days": [7, 14]}


@pytest.mark.parametrize("price,unit,observed_on", [
    (32, "NTD_per_taiwan_jin", "2026-10-14"),
    (65, "NTD_per_kg", "2026-10-14"),
    (32, "NTD_per_taiwan_jin", "2026-09-30"),
])
def test_forecast_matches_real_native_every_field(client, price, unit, observed_on):
    req = dict(BASE, current_price=price, price_unit=unit, observed_on=observed_on)
    actual = call(client, req)
    assert actual.status_code == 200, actual.text
    obj = actual.json()
    assert obj["tool"] == "post_forecast"
    assert obj["normalized_request"]["mode"] == "without_last_week"
    assert obj["normalized_request"]["store_id"] is None
    assert obj["input_echo"]["observed_on"] == observed_on
    rows = obj["engine_result"]["results"]
    assert [r["target_date"] for r in rows] == [
        str(date.fromisoformat(observed_on) + timedelta(days=7)),
        str(date.fromisoformat(observed_on) + timedelta(days=14)),
    ]
    assert [r["horizon_days"] for r in rows] == [7, 14]
    for item in rows:
        assert item["price_estimate_unit"] == unit
        assert item["target_scope"] == "store_price_estimate"
        assert item["validation_scope"] == "unvalidated"
        assert item["probability"] is None
        assert item["interval_low"] is None and item["interval_high"] is None
    native_req = normalized_forecast_request(validate_arguments("post_forecast", req))
    native = ForecastEngine(RELEASE).forecast(native_req)
    # The unique request ID is the only genuinely dynamic native field.
    assert native["request_id"] != obj["engine_result"]["request_id"]
    native.pop("request_id")
    obj["engine_result"].pop("request_id")
    assert native == obj["engine_result"]


def test_missing_date_uses_taipei_calendar(client):
    req = {key: value for key, value in BASE.items() if key != "observed_on"}
    result = call(client, req)
    assert result.status_code == 200
    assert result.json()["input_echo"]["observed_on"] == result.json()["query_date"]


def test_market_quote_matches_agenttools_not_store(client):
    res = call(client, {"crop_id": "cabbage", "market_id": "中義市場"}, "/v1/market-quote")
    assert res.status_code == 200
    raw = AgentTools(ForecastEngine(RELEASE)).get_market_quote("cabbage", "中義市場")
    assert res.json()["engine_result"] == raw
    assert raw["unit"] == "NTD_per_taiwan_jin"
    assert raw["price"] > 0
    assert res.json()["query_date"] >= raw["observed_date"]


@pytest.mark.parametrize("bad,code", [
    ({"crop_id": "invalid"}, "unsupported_crop"),
    ({"market_id": "unknown"}, "unsupported_market"),
    ({"current_price": 0}, "invalid_price"),
    ({"current_price": -1}, "invalid_price"),
    ({"current_price": "32"}, "invalid_price"),
    ({"current_price": True}, "invalid_price"),
    ({"price_unit": "NTD_per_box"}, "non_comparable_unit"),
    ({"observed_on": "2026-02-30"}, "invalid_date"),
    ({"observed_on": "not_a_date"}, "invalid_date"),
    ({"observed_on": "2099-01-01"}, "invalid_date"),
    ({"mode": "with_last_week"}, "unsupported_field"),
    ({"previous_price": 22}, "unsupported_field"),
    ({"store_id": "private"}, "unsupported_field"),
    ({"url": "http://localhost/"}, "unsupported_field"),
    ({"save": True}, "unsupported_field"),
])
def test_rejections(client, bad, code):
    response = call(client, {**BASE, **bad})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_auth_missing_wrong_and_no_secret_in_reply(client):
    missing = call(client, BASE, token=None)
    bad = call(client, BASE, token="bad_token")
    assert missing.status_code == bad.status_code == 401
    assert missing.json()["error"]["code"] == "unauthorized"
    assert FAKE_TEST_TOKEN not in json.dumps(missing.json()) + json.dumps(bad.json())


def test_private_routes_absent(client):
    assert client.get("/records").status_code == 404
    assert client.post("/records", json={}).status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/metadata").status_code == 404


def test_non_json_duplicate_key_nonstandard_constants_and_size(client):
    headers = {"Authorization": "Bearer " + FAKE_TEST_TOKEN, "Content-Type": "application/json"}
    dup = client.post("/v1/market-quote", headers=headers,
                      content=b'{"crop_id":"cabbage","crop_id":"cabbage","market_id":"x"}')
    assert dup.status_code == 400
    nan = client.post("/v1/forecast", headers=headers,
                      content=b'{"crop_id":"cabbage","market_id":"x","current_price":NaN}')
    assert nan.status_code == 400
    huge = client.post("/v1/forecast", headers=headers, content=b"{" + b" " * 4096 + b"}")
    assert huge.status_code == 413
    plain = client.post("/v1/forecast", headers={"Authorization": "Bearer " + FAKE_TEST_TOKEN,
                                                   "Content-Type": "text/plain"}, content=b"{}");
    assert plain.status_code == 415


def test_data_before_public_history_rejected(client):
    response = call(client, dict(BASE, observed_on="2000-01-01"))
    assert response.status_code != 200
    assert response.json()["error"]["code"] in {"stale_data_unusable", "not_ready"}


def test_health_fails_closed_without_origin_token(client, monkeypatch):
    monkeypatch.delenv("TW01_ORIGIN_API_TOKEN", raising=False)
    assert client.get("/healthz").status_code == 503
    assert call(client, BASE).status_code == 401


def test_bad_request_wrong_body_shape(client):
    response = call(client, [], path="/v1/forecast")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_inference_timeout_is_bounded_and_recovers(client, monkeypatch):
    """Isolated fault injection; no sleep/crash on the live Oracle service."""
    import threading
    import time

    original = api.execute_tool
    done = threading.Event()

    def blocked_worker(*args):
        done.wait(timeout=1.0)
        return {"never_expose_stale_result": True}

    monkeypatch.setattr(api, "execute_tool", blocked_worker)
    monkeypatch.setattr(api, "TIMEOUT_SECONDS", 0.03)
    timed_out = call(client, BASE)
    assert timed_out.status_code == 504
    assert timed_out.json()["error"]["code"] == "forecast_timeout"
    assert "never_expose_stale_result" not in timed_out.text
    while_busy = call(client, BASE)
    assert while_busy.status_code == 429
    assert while_busy.json()["error"]["code"] == "rate_limited"

    done.set()
    for _ in range(50):
        if api._busy.acquire(blocking=False):
            api._busy.release()
            break
        time.sleep(0.01)
    else:
        pytest.fail("native worker did not release concurrency gate")
    monkeypatch.setattr(api, "execute_tool", original)
    monkeypatch.setattr(api, "TIMEOUT_SECONDS", 15.0)
    recovered = call(client, BASE)
    assert recovered.status_code == 200
    assert len(recovered.json()["engine_result"]["results"]) == 2


def test_worker_exception_is_masked_and_recovers(client, monkeypatch):
    original = api.execute_tool

    def raises_secret(*args):
        raise RuntimeError("fake_internal_sensitive_traceback")

    monkeypatch.setattr(api, "execute_tool", raises_secret)
    response = call(client, BASE)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "fake_internal_sensitive_traceback" not in response.text
    monkeypatch.setattr(api, "execute_tool", original)
    response2 = call(client, BASE)
    assert response2.status_code == 200


def test_rate_limiter_rejects_excess_requests(client):
    import time

    api._timestamps.extend([time.monotonic()] * api.RATE_LIMIT_PER_MINUTE)
    response = call(client, BASE)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    api._timestamps.clear()
    assert call(client, BASE).status_code == 200
