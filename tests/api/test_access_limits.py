"""T28 存取限制測試（本機層）：超量 body、速率限制、正常使用不受影響。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi.testclient import TestClient

from aiot_price.api import app as app_module
from aiot_price.api.app import app


@pytest.fixture()
def client():
    # 每個測試獨立速率桶，避免互相干擾
    app_module._rate_buckets.clear()
    return TestClient(app)


class TestBodySize:
    def test_oversized_body_rejected_413(self, client):
        big = {"query": "x" * (9 * 1024)}
        r = client.post(
            "/agent/query",
            json=big,
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 413
        assert r.json()["error"]["code"] == "payload_too_large"

    def test_normal_body_ok(self, client):
        r = client.post(
            "/forecast",
            json={
                "crop_id": "cabbage",
                "market_id": "中義市場",
                "current_price": 32.0,
                "price_unit": "NTD_per_taiwan_jin",
                "observed_at": "2026-10-02T10:00:00+08:00",
                "mode": "without_last_week",
            },
        )
        assert r.status_code == 200


class TestRateLimit:
    def test_burst_limited_429(self, client):
        req = {
            "crop_id": "cabbage",
            "market_id": "中義市場",
            "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin",
            "observed_at": "2026-10-02T10:00:00+08:00",
            "mode": "without_last_week",
        }
        statuses = [client.post("/forecast", json=req).status_code for _ in range(35)]
        assert 429 in statuses
        assert statuses[-1] == 429
        assert statuses[0] == 200  # 前幾個正常

    def test_health_not_blocked_early(self, client):
        for _ in range(5):
            assert client.get("/health").status_code == 200


class TestNoSecrets:
    def test_health_has_no_secrets_or_paths(self, client):
        body = client.get("/health").json()
        text = str(body)
        for forbidden in ("password", "token", "api_key", "C:\\", "AIOT_QWEN_API_KEY"):
            assert forbidden.lower() not in text.lower()

    def test_metadata_no_secrets(self, client):
        text = str(client.get("/metadata").json())
        for forbidden in ("password", "token", "api_key"):
            assert forbidden.lower() not in text.lower()
