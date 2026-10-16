"""Real public snapshot 61-column catalog and strictly scoped website tests."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = Path(__file__).resolve().parent
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))
from build_full_market_catalog import SOURCE, build
import full_catalog_runtime as expanded
from oracle_web_site import app, api

HEADERS = {
    "Origin": "https://161.33.19.220",
    "Referer": "https://161.33.19.220/web/",
    "Sec-Fetch-Site": "same-origin",
}
BASE = {
    "crop_id": "taichung_04",  # Official public field: radish
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    directory = tmp_path / "new_public_catalog"
    manifest = build(SOURCE, directory)
    monkeypatch.setenv("TW01_EXTENDED_CATALOG_DIR", str(directory))
    monkeypatch.setenv("TW01_ORIGIN_API_TOKEN", "test_only_" + "x" * 48)
    expanded.data_bundle.cache_clear()
    api._timestamps.clear()
    yield directory, manifest
    expanded.data_bundle.cache_clear()
    api._timestamps.clear()


def test_true_source_and_exact_categories(bundle):
    catalog = expanded.public_catalog()
    assert catalog["source_zero_means_missing"] is True
    assert len(catalog["items"]) == 61
    assert len(catalog["markets"]) == 13
    assert sum(e["has_ever_had_public_price"] for e in catalog["items"]) == 60
    assert {g["id"]: sum(e["category"] == g["id"] for e in catalog["items"])
            for g in catalog["categories"]} == {
        "vegetable": 15, "fruit": 27, "seafood": 7, "meat": 10, "egg": 2
    }
    idx = {e["crop_id"]: e for e in catalog["items"]}
    assert idx["cabbage"]["method"] == "frozen_rf_hgb_v0.1.0"
    assert idx["bok_choy"]["method"] == "frozen_rf_hgb_v0.1.0"
    assert idx["sponge_gourd"]["method"] == "frozen_rf_hgb_v0.1.0"
    assert idx["taichung_04"]["method"] == "historical_momentum_baseline"
    assert not idx["taichung_25"]["has_ever_had_public_price"]
    assert idx["taichung_25"]["total_nonzero_observations"] == 0
    assert len(idx) == 61
    assert bundle[1]["source_sha256"] == (
        "172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259"
    )


def test_new_vegetable_trend_a_untrained(bundle):
    with TestClient(app) as client:
        response = client.post("/site/forecast", json=BASE, headers=HEADERS)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["forecast_method"] == "untrained_historical_momentum"
        assert data["model_version"] == "historic-trend-baseline/1.0"
        assert data["data_version"] == "172dffc76e82"
        assert data["store_id"] is None
        assert data["mode_executed"] == "without_last_week"
        assert [r["target_date"] for r in data["results"]] == [
            "2026-10-21", "2026-10-28"
        ]
        assert [r["horizon_days"] for r in data["results"]] == [7, 14]
        assert "RF/HGB" in data["warnings"][0]
        for r in data["results"]:
            assert r["probability"] is None
            assert r["interval_low"] is None
            assert r["interval_high"] is None
            assert r["validation_scope"] == "unvalidated"


def test_new_vegetable_a_b_and_kg(bundle):
    body = {
        **BASE,
        "mode": "both",
        "price_unit": "NTD_per_kg",
        "current_price": 70,
        "previous_price": 64,
        "previous_price_unit": "NTD_per_kg",
        "previous_observed_at": "2026-10-07T12:00:00+08:00",
    }
    with TestClient(app) as client:
        result = client.post("/site/forecast", json=body, headers=HEADERS)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["mode_executed"] == "both"
        assert [x["horizon_days"] for x in data["results_without_last_week"]] == [7, 14]
        assert [x["horizon_days"] for x in data["results_with_last_week"]] == [7, 14]
        assert all(x["price_estimate_unit"] == "NTD_per_kg"
                   for x in data["results_without_last_week"] + data["results_with_last_week"])
        assert all(any("係數 0.3" in warning and "未經同店" in warning
                       for warning in x["warnings"])
                   for x in data["results_with_last_week"])


def test_b_fallback_when_outside_interval(bundle):
    body = {
        **BASE,
        "mode": "both",
        "previous_price": 29,
        "previous_price_unit": "NTD_per_taiwan_jin",
        "previous_observed_at": "2026-09-29T12:00:00+08:00",
    }
    with TestClient(app) as client:
        result = client.post("/site/forecast", json=body, headers=HEADERS)
        assert result.status_code == 200
        data = result.json()
        assert data["mode_executed"] == "fallback_without_last_week"
        assert data["results_with_last_week"] == []
        assert len(data["results"]) == 2
        assert data["b_unavailable_reason"]


def test_no_quote_never_forecasts_zero(bundle):
    with TestClient(app) as client:
        response = client.post("/site/forecast", json={
            **BASE, "crop_id": "taichung_25"
        }, headers=HEADERS)
        assert response.status_code == 503
        data = response.json()
        assert data["results"] == []
        assert data["error"]["code"] == "no_public_price"


def test_extra_field_rejected_and_original_api_isolated(bundle):
    with TestClient(app) as client:
        bad = client.post("/site/forecast", json={
            **BASE, "store_id": "private-store"
        }, headers=HEADERS)
        assert bad.status_code == 422
        assert bad.json()["error"]["code"] == "unsupported_field"
        secret = client.post("/v1/forecast", json={
            "crop_id": "taichung_04", "market_id": "中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on": "2026-10-14",
        })
        assert secret.status_code == 401
        token = "test_only_" + "x" * 48
        denied = client.post("/v1/forecast", json={
            "crop_id": "taichung_04", "market_id": "中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on": "2026-10-14",
        }, headers={"Authorization": "Bearer " + token})
        assert denied.status_code == 422


def test_historical_early_date_does_not_peek_future(bundle):
    with TestClient(app) as client:
        resp = client.post("/site/forecast", json={
            **BASE, "observed_at": "2000-01-01T12:00:00+08:00"
        }, headers=HEADERS)
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "insufficient_history"


def test_frontend_and_models_not_modified(bundle):
    catalog, history, _, manifest = expanded.data_bundle()
    assert set(manifest["frozen_original_crop_ids"]) == {
        "cabbage", "bok_choy", "sponge_gourd"
    }
    with TestClient(app) as client:
        result = client.post("/site/forecast", json={
            **BASE, "crop_id": "cabbage",
        }, headers=HEADERS)
        assert result.status_code == 200
        assert result.json()["model_version"] == "0.1.0"
        assert "forecast_method" not in result.json()
        assert client.get("/records").status_code == 404


def test_hash_fail_closed(bundle):
    folder, _ = bundle
    file = folder / "catalog.json"
    original = file.read_bytes()
    try:
        file.write_bytes(original + b" ")
        expanded.data_bundle.cache_clear()
        with pytest.raises(RuntimeError):
            expanded.data_bundle()
    finally:
        file.write_bytes(original)
        expanded.data_bundle.cache_clear()
    assert len(expanded.public_catalog()["items"]) == 61
