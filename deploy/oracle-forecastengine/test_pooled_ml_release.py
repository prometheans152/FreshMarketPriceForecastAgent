"""FMPA new supervised models: exact-split/test labels, runtime and isolation.

This file runs in a fresh pytest process from legacy oracle_web_site tests
because the new ASGI overlay intentionally redirects ONLY expanded crop calls
while keeping the same frozen /v1/* API object.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / "deploy/oracle-forecastengine"
sys.path.insert(0, str(OVERLAY))
os.environ.setdefault("FMPA_ORIGIN_API_TOKEN", "test_only_" + "r" * 48)
os.environ["FMPA_RELEASE_DIR"] = str(ROOT / "models/releases/0.1.0")

from pooled_ml_runtime import (
    ML_WARNING, QUALITY_WARNING, check_ml_release_integrity,
    forecast_ml, ml_release,
)
from pooled_ml_features import (
    FROZEN_CROPS, design_matrix, features_at, quotes_as_arrays,
)
from full_catalog_runtime import data_bundle
from oracle_web_site_ml import app

HEADERS = {
    "Origin": "https://161.33.19.220",
    "Referer": "https://161.33.19.220/web/",
    "Sec-Fetch-Site": "same-origin",
}
BASE = {
    "crop_id": "taichung_04",
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}


def test_model_real_trained_artifacts_and_source_integrity():
    manifest, report, models = ml_release()
    source = json.loads((ROOT / "models/releases/0.1.0/manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_sha256"] == source["source"]["json_sha256"]
    assert manifest["model_version"] == "multi-crop-ml/1.0.0"
    assert manifest["method"] == "real_supervised_pooled_regression"
    assert len(manifest["trained_crop_ids"]) == 57
    assert set(manifest["trained_crop_ids"]).isdisjoint(FROZEN_CROPS)
    assert {m["horizon_days"] for m in manifest["models"]} == {7, 14}
    assert {m["algorithm"] for m in manifest["models"]} == {"hgb"}
    assert all(hasattr(estimator, "predict") and hasattr(estimator, "n_iter_")
               and estimator.n_iter_ > 0 for estimator in models.values())
    assert set(check_ml_release_integrity()["models"]) == {"7", "14"}
    for h in ("7", "14"):
        assert report["horizons"][h]["train_rows"] > 50000
        assert report["horizons"][h]["validation_rows"] > 10000
        assert report["horizons"][h]["test_rows"] > 10000
        assert report["horizons"][h]["test"]["ml"]["n"] > 10000
        assert report["horizons"][h]["test"]["flat_baseline"]["n"] > 10000
        assert report["horizons"][h]["test"]["ml"]["mae_relative_change"] > (
            report["horizons"][h]["test"]["flat_baseline"]["mae_relative_change"]
        )


def test_trained_ml_a_from_actual_original_market_snapshot():
    with TestClient(app) as client:
        resp = client.post("/site/forecast", json=BASE, headers=HEADERS)
        assert resp.status_code == 200, resp.text
        obj = resp.json()
        assert obj["model_version"] == "multi-crop-ml/1.0.0"
        assert obj["forecast_method"] == "supervised_hgb_pooled"
        assert obj["ml_training_scope"] == "57_new_public_market_crops"
        assert obj["data_version"] == "172dffc76e82"
        assert obj["store_id"] is None
        assert obj["mode_executed"] == "without_last_week"
        assert [r["horizon_days"] for r in obj["results"]] == [7, 14]
        assert [r["target_date"] for r in obj["results"]] == ["2026-10-21", "2026-10-28"]
        assert obj["results_without_last_week"] == []
        assert "已採用" in obj["warnings"][0] and "HGB" in obj["warnings"][0]
        assert "未勝過不變價基準" in obj["warnings"][1]
        assert all(r["validation_scope"] == "unvalidated" and
                   r["probability"] is None and
                   r["interval_low"] is None and r["interval_high"] is None
                   for r in obj["results"])
        assert obj["ml_holdout_evaluation"]["7"]["ml_mae_relative_change"] > 0


def test_trained_ml_matches_loaded_h7_and_h14_without_baseline_substitution():
    obj = forecast_ml(BASE)
    manifest, _, models = ml_release()
    _, history, _, _ = data_bundle()
    ordinals, prices = quotes_as_arrays(history[BASE["crop_id"]][BASE["market_id"]])
    X = design_matrix(
        features_at(
            ordinals, prices, np.array([date.fromisoformat("2026-10-14").toordinal()]),
            crop_id=BASE["crop_id"], market_id=BASE["market_id"],
        ),
        manifest["feature_columns"],
    )
    for result in obj["results"]:
        h = result["horizon_days"]
        raw_pred = float(models[h].predict(X)[0])
        prediction = np.expm1(np.clip(raw_pred, -1.25, 1.25))
        assert result["relative_change_estimate"] == round(float(prediction), 4)
        assert result["price_estimate"] == round(BASE["current_price"] * (1 + prediction), 1)


def test_trained_ml_b_is_fixed_alpha_not_mislabeled_as_trained_b():
    body = {
        **BASE,
        "mode": "both",
        "previous_price": 30,
        "previous_price_unit": "NTD_per_taiwan_jin",
        "previous_observed_at": "2026-10-07T12:00:00+08:00",
    }
    with TestClient(app) as client:
        resp = client.post("/site/forecast", json=body, headers=HEADERS)
        assert resp.status_code == 200, resp.text
        obj = resp.json()
        assert obj["mode_executed"] == "both"
        assert len(obj["results_without_last_week"]) == 2
        assert len(obj["results_with_last_week"]) == 2
        assert any("非 B 重新訓練模型" in x["evidence_summary"]
                   for x in obj["results_with_last_week"])
        for row in obj["results_with_last_week"]:
            assert any("α=0.3" in warning for warning in row["warnings"])


def test_zero_only_crop_cannot_get_fake_model_prediction():
    with TestClient(app) as client:
        result = client.post("/site/forecast", json={
            **BASE, "crop_id": "taichung_25",
        }, headers=HEADERS)
        assert result.status_code == 503
        body = result.json()
        assert body["results"] == []
        assert body["error"]["code"] == "no_public_price"
        assert body["model_version"] == "multi-crop-ml/1.0.0"


def test_invalid_old_date_and_invalid_extra_field():
    with TestClient(app) as client:
        obsolete = client.post("/site/forecast", json={
            **BASE, "observed_at": "2000-01-01T12:00:00+08:00"
        }, headers=HEADERS)
        assert obsolete.status_code == 503
        assert obsolete.json()["results"] == []
        assert obsolete.json()["error"]["code"] == "insufficient_history"
        extra = client.post("/site/forecast", json={
            **BASE, "save": True,
        }, headers=HEADERS)
        assert extra.status_code == 422
        assert extra.json()["error"]["code"] == "unsupported_field"


def test_unchanged_mcp_origin_and_original_cabbage():
    with TestClient(app) as client:
        result = client.post("/site/forecast", json={
            **BASE, "crop_id": "cabbage",
        }, headers=HEADERS)
        assert result.status_code == 200
        body = result.json()
        assert body["model_version"] == "0.1.0"
        assert "forecast_method" not in body
        noauth = client.post("/v1/forecast", json={
            "crop_id":"taichung_04", "market_id":"中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on":"2026-10-14"
        })
        assert noauth.status_code == 401
        token = "test_only_" + "r" * 48
        unsupported = client.post("/v1/forecast", json={
            "crop_id":"taichung_04", "market_id":"中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on":"2026-10-14"
        }, headers={"Authorization":"Bearer " + token})
        assert unsupported.status_code == 422
        assert client.get("/records").status_code == 404
        assert client.get("/healthz").json()["status"] == "ready"


def test_new_features_never_read_t_or_future_public_quote():
    _, history, _, _ = data_bundle()
    days, prices = quotes_as_arrays(history["taichung_04"]["中義市場"])
    t = date.fromisoformat("2026-09-01").toordinal()
    before = features_at(days, prices, np.array([t]),
                         crop_id="taichung_04", market_id="中義市場")
    contaminated = prices.copy()
    contaminated[days >= t] *= 50
    after = features_at(days, contaminated, np.array([t]),
                        crop_id="taichung_04", market_id="中義市場")
    assert before.equals(after)


def test_market_and_crop_boundaries():
    from full_catalog_runtime import public_catalog
    entries = public_catalog()["items"]
    assert len(entries) == 61
    assert sum(x["has_ever_had_public_price"] for x in entries) == 60
    assert len(ml_release()[0]["trained_crop_ids"]) == 57
