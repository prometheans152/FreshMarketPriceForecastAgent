"""Public HTTPS e2e tests for the 61-item site, NO secret/token required.

Output is compact verification metadata and a sample of REAL model values.
The original origin API contract is tested separately, with its secret kept
server-side. Don't turn returned public-market means into shop true prices.
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "https://161.33.19.220"
DIRECT = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
)
HEADERS = {
    "Origin": HOST,
    "Referer": HOST + "/web/",
    "Sec-Fetch-Site": "same-origin",
    "Content-Type": "application/json",
}
BASE = {
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}


def get(path):
    req = urllib.request.Request(HOST + path, method="GET")
    with DIRECT.open(req, timeout=25) as response:
        return response.status, response.read()


def post(body):
    req = urllib.request.Request(
        HOST + "/web/forecast", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=HEADERS,
    )
    try:
        with DIRECT.open(req, timeout=28) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refuse overwrite of verification evidence")
    cases = []

    def record(name, passed, **fields):
        cases.append({"case": name, "pass": bool(passed), **fields})
        print(("PASS " if passed else "FAIL ") + name)

    status, html = get("/web/")
    page = html.decode("utf-8")
    record(
        "https_public_home_search_and_category", status == 200
        and all(x in page for x in (
            'id="cropSearch"', 'id="cropCategory"',
            'id="cropMethodStatus"', 'id="hasLastWeek"',
            'id="recordsPanel"', "61",
        )),
        status=status,
    )
    status, js = get("/web/app.js")
    record("https_catalog_ui_js", status == 200
           and b"taichung_42" in js
           and b"const CROPS = " in js
           and b"setupCropCatalog()" in js
           and b"readBrowserRecords" in js,
           status=status, js_bytes=len(js))
    status, css = get("/web/style.css")
    record("https_catalog_style", status == 200 and b"catalog-tools" in css,
           status=status)
    status, raw = get("/web/catalog.json")
    catalog = json.loads(raw)
    ids = {item["crop_id"]: item for item in catalog["items"]}
    record(
        "https_true_official_61_item_catalog",
        status == 200 and len(ids) == 61
        and len(catalog["markets"]) == 13
        and sum(x["has_ever_had_public_price"] for x in ids.values()) == 60
        and ids["taichung_25"]["has_ever_had_public_price"] is False,
        status=status, items=len(ids), priced=sum(
            x["has_ever_had_public_price"] for x in ids.values()),
    )
    record(
        "all_frozen_source_three_unchanged",
        {cid for cid, item in ids.items()
         if item["method"] == "frozen_rf_hgb_v0.1.0"}
        == {"cabbage", "bok_choy", "sponge_gourd"},
    )
    record(
        "historical_baseline_not_claimed_trained",
        ids["taichung_04"]["method"] == "historical_momentum_baseline"
        and ids["cabbage"]["method"] == "frozen_rf_hgb_v0.1.0",
    )
    # Rate limit applies only to public /web/forecast; space true model calls.
    # A synthetic shop input is never treated as an observed store-validation.
    samples = [
        ("new_radish_A", {**BASE, "crop_id": "taichung_04"},
         "historic-trend-baseline/1.0", "without_last_week"),
        ("new_radish_B", {**BASE, "crop_id": "taichung_04", "mode": "both",
                         "previous_price": 30,
                         "previous_price_unit": "NTD_per_taiwan_jin",
                         "previous_observed_at": "2026-10-07T12:00:00+08:00"},
         "historic-trend-baseline/1.0", "both"),
        ("original_cabbage_A", {**BASE, "crop_id": "cabbage"},
         "0.1.0", "without_last_week"),
        ("fruit_banana_A", {**BASE, "crop_id": "taichung_11"},
         "historic-trend-baseline/1.0", "without_last_week"),
        ("seafood_tilapia_A", {**BASE, "crop_id": "taichung_43"},
         "historic-trend-baseline/1.0", "without_last_week"),
        ("meat_pork_A", {**BASE, "crop_id": "taichung_50"},
         "historic-trend-baseline/1.0", "without_last_week"),
        ("egg_chicken_A", {**BASE, "crop_id": "taichung_56"},
         "historic-trend-baseline/1.0", "without_last_week"),
    ]
    for i, (name, body, model, mode) in enumerate(samples):
        if i > 0:
            time.sleep(4.0)
        status, value = post(body)
        a = value.get("results_without_last_week") or value.get("results") or []
        b = value.get("results_with_last_week", [])
        valid = (
            status == 200 and value.get("error") is None
            and value.get("model_version") == model
            and value.get("mode_executed") == mode
            and [r.get("horizon_days") for r in a] == [7, 14]
            and [r.get("target_date") for r in a] == ["2026-10-21", "2026-10-28"]
            and value.get("store_id") is None
            and all(r.get("validation_scope") == "unvalidated"
                    for r in a)
            and (mode != "both" or [r.get("horizon_days") for r in b] == [7, 14])
        )
        if model.startswith("historic-"):
            valid = valid and (
                value.get("forecast_method") == "untrained_historical_momentum"
                and any(("未訓練" in warning or "沒有受訓" in warning)
                        for warning in value.get("warnings", []))
            )
        else:
            valid = valid and "forecast_method" not in value
        record(
            name, valid, status=status,
            model_version=value.get("model_version"),
            results=[{"h":r["horizon_days"], "date":r["target_date"],
                      "direction":r["direction"], "estimate":r["price_estimate"]}
                     for r in a],
            b_count=len(b), error=value.get("error"),
        )
    # The empty-only public field must explicitly return no figures.
    time.sleep(4.0)
    status, missing = post({**BASE, "crop_id": "taichung_25"})
    record("all_zero_crop_rejected_not_fabricated",
           status == 503 and missing["error"]["code"] == "no_public_price"
           and missing.get("results") == [], status=status)
    status, health_data = get("/healthz")
    healthy = json.loads(health_data)
    record("original_api_health", status == 200
           and healthy.get("status") == "ready"
           and healthy.get("model_version") == "0.1.0")
    report = {
        "status": "PASS" if all(x["pass"] for x in cases) else "FAIL",
        "total": len(cases),
        "passed": sum(x["pass"] for x in cases),
        "source_cutoff": catalog.get("source_observation_cutoff"),
        "source_sha256": catalog.get("source_sha256"),
        "all_data_snapshot_prices_not_live_shop_prices": True,
        "frozen_release_modified": False,
        "cases": cases,
    }
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("RESULT", report["passed"], "/", report["total"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
