"""The /v1 full-catalog extension against real models, catalog and frozen release.

Runs v1ext_probe.py twice in fresh interpreters: once on the sources baked into
the deployed v1.0.0 image (TW01_* settings) and once on this repo (FMPA_*).
The image sources are the portable release folder the image was built from;
set FMPA_V1EXT_IMAGE_DIR to point elsewhere. Skips if those artifacts are absent.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE_DIR = Path(os.environ.get(
    "FMPA_V1EXT_IMAGE_DIR",
    ROOT / "outputs/quality_runs/tw01_docker_portable_final_20261015_025240_Windows5800X/TW01_Docker_Portable_v1.0.0",
))
DAY = "2026-10-27"
TOKEN = "test_only_" + "v" * 48

pytestmark = pytest.mark.skipif(
    not (IMAGE_DIR / "catalog/catalog.json").is_file(), reason="portable release artifacts not present")


def run_probe(code_root: Path, prefix: str, release: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FMPA_", "TW01_"))}
    env.update({
        "PYTHONPATH": os.pathsep.join([str(code_root / "src"), str(code_root / "deploy/oracle-forecastengine"), str(HERE)]),
        "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PROBE_TOKEN": TOKEN, "PROBE_DAY": DAY,
        prefix + "ORIGIN_API_TOKEN": TOKEN,
        prefix + "RELEASE_DIR": str(release),
        prefix + "EXTENDED_CATALOG_DIR": str(IMAGE_DIR / "catalog"),
        prefix + "POOLED_ML_DIR": str(IMAGE_DIR / "models/pooled"),
    })
    done = subprocess.run([sys.executable, str(HERE / "v1ext_probe.py")], env=env, cwd=str(HERE),
                          capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module", params=["image_v1.0.0", "repo"])
def probe(request):
    if request.param == "repo":
        return run_probe(ROOT, "FMPA_", ROOT / "models/releases/0.1.0")
    return run_probe(IMAGE_DIR, "TW01_", IMAGE_DIR / "models/releases/0.1.0")


def plus(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def test_extension_is_wired_and_keeps_every_route(probe):
    assert probe["patched"] == ["v1_full_catalog", "v1_full_catalog"]
    for path in ("/healthz", "/v1/market-quote", "/v1/forecast", "/site/forecast"):
        assert path in probe["routes"]


def test_frozen_crops_are_unchanged(probe):
    quote = probe["quote_frozen"]
    assert quote["status"] == 200 and quote["body"]["engine_result"]["crop_id"] == "cabbage"
    fc = probe["forecast_frozen"]
    assert fc["status"] == 200
    assert fc["body"]["engine_result"]["model_version"] != "multi-crop-ml/1.0.0"
    assert fc["body"]["engine_result"]["results"] == probe["frozen_direct_results"]


def test_catalog_quote_matches_worker_contract(probe):
    r = probe["quote_catalog"]
    assert r["status"] == 200, r
    body, raw = r["body"], r["body"]["engine_result"]
    assert body["tool"] == "get_market_quote" and body["normalized_request"] is None
    assert body["input_echo"] == {"crop_id": "taichung_40", "market_id": "第三市場"}
    assert raw["ok"] is True and raw["crop_id"] == "taichung_40" and raw["crop_display_name"] == "花椰菜"
    assert raw["unit"] == "NTD_per_taiwan_jin" and raw["price"] > 0
    assert raw["observed_date"] <= raw["public_data_cutoff"] == "2026-10-02"
    assert plus(raw["observed_date"], raw["price_age_days_at_cutoff"]) == raw["public_data_cutoff"]
    assert body["price_age_days_at_query"] == (
        date.fromisoformat(body["query_date"]) - date.fromisoformat(raw["observed_date"])).days


@pytest.mark.parametrize("case,unit", [("forecast_catalog", "NTD_per_taiwan_jin"), ("forecast_catalog_kg", "NTD_per_kg")])
def test_catalog_forecast_matches_worker_contract(probe, case, unit):
    r = probe[case]
    assert r["status"] == 200, r
    body, raw = r["body"], r["body"]["engine_result"]
    assert raw["model_version"] == "multi-crop-ml/1.0.0" and raw["data_version"]
    assert raw["mode_executed"] == "without_last_week" and raw["store_id"] is None
    assert not raw["results_with_last_week"] and raw["error"] is None
    assert body["normalized_request"]["observed_at"] == DAY + "T12:00:00+08:00" == raw["input_observed_at"]
    assert body["normalized_request"]["mode"] == "without_last_week" and body["normalized_request"]["store_id"] is None
    assert len(body["input_echo"]) == 5 and body["input_echo"]["observed_on"] == DAY
    assert [row["horizon_days"] for row in raw["results"]] == [7, 14]
    for row in raw["results"]:
        assert row["target_date"] == plus(DAY, row["horizon_days"])
        assert row["price_estimate_unit"] == unit and row["price_estimate"] > 0
        assert row["probability"] is None and row["interval_low"] is None and row["interval_high"] is None
        assert row["target_scope"] == "store_price_estimate" and row["validation_scope"] == "unvalidated"
    assert any("未勝過不變價" in w for w in raw["warnings"])
    assert any("MAE 未勝不變價" in limit for limit in body["limits"])


def test_catalog_forecast_defaults_to_today(probe):
    r = probe["forecast_catalog_no_date"]
    assert r["status"] == 200, r
    assert r["body"]["normalized_request"]["observed_at"] == r["body"]["input_echo"]["observed_on"] + "T12:00:00+08:00"


@pytest.mark.parametrize("case,status,code", [
    ("forecast_no_public_price", 503, "stale_data_unusable"),
    ("forecast_unknown_item", 422, "unsupported_crop"),
    ("forecast_b_field", 422, "unsupported_field"),
    ("forecast_unknown_market", 422, "unsupported_market"),
    ("forecast_future_date", 422, "invalid_date"),
    ("forecast_bad_price", 422, "invalid_price"),
    ("forecast_no_auth", 401, "unauthorized"),
])
def test_refusals_return_no_number(probe, case, status, code):
    r = probe[case]
    assert r["status"] == status, r
    assert r["body"]["error"]["code"] == code
    assert "engine_result" not in r["body"]
