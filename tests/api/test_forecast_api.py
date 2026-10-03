"""T20 API 測試：成功、拒絕、資料不足、B 降級。以 TestClient 對真模型包跑。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi.testclient import TestClient

from aiot_price.api.app import app


@pytest.fixture(scope="module")
def client():
    release = Path("models/releases/0.1.0")
    if not (release / "manifest.json").exists():
        pytest.skip("模型包尚未打包；先跑 aiot_price.models.package")
    return TestClient(app)


BASE_REQ = {
    "crop_id": "cabbage",
    "market_id": "中義市場",
    "current_price": 32.0,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-02T10:00:00+08:00",
    "mode": "without_last_week",
}


class TestHealthMetadata:
    def test_health_ready(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert body["model_version"] == "0.1.0"
        assert "sha" not in body.get("reason", "")

    def test_metadata_lists(self, client):
        r = client.get("/metadata")
        assert r.status_code == 200
        body = r.json()
        assert set(body["crops"]) == {"cabbage", "bok_choy", "sponge_gourd"}
        assert "中義市場" in body["markets"]
        assert body["capability_notes"]["probability_output"] is False


class TestForecast:
    def test_success_mode_a(self, client):
        r = client.post("/forecast", json=BASE_REQ)
        assert r.status_code == 200
        body = r.json()
        assert body["mode_executed"] == "without_last_week"
        assert body["error"] is None
        horizons = {x["horizon_days"] for x in body["results"]}
        assert horizons == {7, 14}
        for item in body["results"]:
            assert item["direction"] in ("up", "flat", "down", "insufficient_data")
            assert item["probability"] is None  # 未校準不輸出

    def test_unsupported_crop_422(self, client):
        req = {**BASE_REQ, "crop_id": "萵苣"}
        r = client.post("/forecast", json=req)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "unsupported_crop"

    def test_non_comparable_unit_422(self, client):
        req = {**BASE_REQ, "price_unit": "per_bunch"}
        r = client.post("/forecast", json=req)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "non_comparable_unit"

    def test_invalid_price_zero_422(self, client):
        req = {**BASE_REQ, "current_price": 0}
        r = client.post("/forecast", json=req)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "invalid_price"

    def test_missing_field_400(self, client):
        req = {k: v for k, v in BASE_REQ.items() if k != "observed_at"}
        r = client.post("/forecast", json=req)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "bad_request"

    def test_not_json_400(self, client):
        r = client.post("/forecast", content=b"not json", headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_unknown_market_422(self, client):
        req = {**BASE_REQ, "market_id": "台北某市場"}
        r = client.post("/forecast", json=req)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "unsupported_market"

    def test_mode_b_out_of_window_falls_back(self, client):
        req = {
            **BASE_REQ,
            "mode": "with_last_week",
            "previous_price": 30.0,
            "previous_price_unit": "NTD_per_taiwan_jin",
            "previous_observed_at": "2026-09-01T10:00:00+08:00",  # 距 10-02 遠超 7±2 天
        }
        r = client.post("/forecast", json=req)
        assert r.status_code == 200
        body = r.json()
        assert body["mode_executed"] == "fallback_without_last_week"
        assert body["b_unavailable_reason"]
        assert len(body["results"]) == 2

    def test_mode_b_valid_returns_both(self, client):
        req = {
            **BASE_REQ,
            "mode": "both",
            "previous_price": 30.0,
            "previous_price_unit": "NTD_per_taiwan_jin",
            "previous_observed_at": "2026-09-25T10:00:00+08:00",  # 10-02 前 7 天
        }
        r = client.post("/forecast", json=req)
        assert r.status_code == 200
        body = r.json()
        assert body["mode_executed"] == "both"
        assert len(body["results_without_last_week"]) == 2
        assert len(body["results_with_last_week"]) == 2
        b_warnings = body["results_with_last_week"][0]["warnings"]
        assert any("實驗性" in w for w in b_warnings)  # B 未驗證標示必須出現

    def test_stale_market_insufficient(self, client):
        # 南屯市場甘藍全期無價 → 503 stale_data_unusable
        req = {**BASE_REQ, "market_id": "南屯市場"}
        r = client.post("/forecast", json=req)
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "stale_data_unusable"
