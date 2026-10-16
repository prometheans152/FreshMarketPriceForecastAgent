"""Validate A/B same-origin website route; no edits to original Windows app."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))
os.environ["FMPA_RELEASE_DIR"] = str(ROOT / "models" / "releases" / "0.1.0")
os.environ["FMPA_ORIGIN_API_TOKEN"] = "test_only_" + "x" * 48
from oracle_web_site import app, api

HEADERS = {
    "Origin": "https://161.33.19.220",
    "Referer": "https://161.33.19.220/web/",
    "Sec-Fetch-Site": "same-origin",
}
BASE = {
    "crop_id": "cabbage", "market_id": "中義市場",
    "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}


@pytest.fixture(autouse=True)
def clean_rate():
    api._timestamps.clear()


def test_original_api_requires_bearer():
    with TestClient(app) as client:
        assert client.post("/v1/forecast", json={
            "crop_id": "cabbage", "market_id": "中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on": "2026-10-14"
        }).status_code == 401
        assert client.get("/healthz").json()["status"] == "ready"


def test_website_same_origin_a_true_model():
    with TestClient(app) as client:
        response = client.post("/site/forecast", json=BASE, headers=HEADERS)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["mode_executed"] == "without_last_week"
        assert data["store_id"] is None
        assert [r["horizon_days"] for r in data["results"]] == [7, 14]
        assert [r["target_date"] for r in data["results"]] == ["2026-10-21", "2026-10-28"]
        assert data["results_with_last_week"] == []


def test_website_same_origin_b_native_model():
    request = {
        **BASE, "mode": "both", "previous_price": 30,
        "previous_price_unit": "NTD_per_taiwan_jin",
        "previous_observed_at": "2026-10-07T12:00:00+08:00",
    }
    with TestClient(app) as client:
        response = client.post("/site/forecast", json=request, headers=HEADERS)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["mode_executed"] == "both"
        assert [r["horizon_days"] for r in data["results_without_last_week"]] == [7, 14]
        assert [r["horizon_days"] for r in data["results_with_last_week"]] == [7, 14]
        assert data["store_id"] is None
        for r in data["results_with_last_week"]:
            assert r["probability"] is None
            assert r["validation_scope"] == "unvalidated"


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://example.net"},
                                    {"Origin": "https://161.33.19.220", "Sec-Fetch-Site": "cross-site"}])
def test_cross_origin_rejected(headers):
    with TestClient(app) as client:
        response = client.post("/site/forecast", json=BASE, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "origin_not_allowed"


@pytest.mark.parametrize("extra,expected", [
    ({"store_id": "private-store"}, "unsupported_field"),
    ({"save": True}, "unsupported_field"),
    ({"current_price": 0}, "invalid_price"),
    ({"price_unit": "per_box"}, "non_comparable_unit"),
    ({"observed_at": "2026-02-30T12:00:00+08:00"}, "invalid_date"),
    ({"observed_at": "2099-01-01T12:00:00+08:00"}, "invalid_date"),
    ({"mode": "both"}, "bad_request"),
    ({"mode": "with_last_week"}, "bad_request"),
])
def test_web_rejects_bad_input(extra, expected):
    with TestClient(app) as client:
        response = client.post("/site/forecast", json={**BASE, **extra}, headers=HEADERS)
        assert response.status_code in (400, 422)
        assert response.json()["error"]["code"] == expected


def test_server_side_saved_records_absent():
    with TestClient(app) as client:
        assert client.get("/site/records").status_code == 404
        assert client.post("/site/records", json={}, headers=HEADERS).status_code == 404
        assert client.get("/records").status_code == 404
        assert client.get("/docs").status_code == 404
