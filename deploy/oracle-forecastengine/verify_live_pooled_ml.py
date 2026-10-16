"""Live Oracle HTTPS 61-crop site acceptance against LOCAL trained ML weights.

No browser password, MCP origin token, private records or other credentials.
Uses system TLS trust and no proxy. Compares all deterministic ML fields to
the original Windows ML artifact, ignoring ONLY fresh server request IDs.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "https://161.33.19.220"
BASE = {
    "crop_id": "taichung_04",
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}

OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
)


def fetch(path: str, *, body: dict | None = None, origin: str = HOST):
    headers = {}
    if body is not None:
        headers = {
            "Content-Type": "application/json",
            "Origin": origin,
            "Referer": HOST + "/web/",
            "Sec-Fetch-Site": "same-origin" if origin == HOST else "cross-site",
        }
    request = urllib.request.Request(
        HOST + path,
        method="POST" if body is not None else "GET",
        headers=headers,
        data=(json.dumps(body, ensure_ascii=False).encode("utf-8")
              if body is not None else None),
    )
    try:
        with OPENER.open(request, timeout=28) as response:
            return response.status, response.read(750_000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(750_000)


def stable(obj: dict):
    reduced = dict(obj)
    reduced.pop("request_id", None)
    return reduced


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--ml-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse overwrite of acceptance evidence")
    os.environ["FMPA_EXTENDED_CATALOG_DIR"] = str(args.catalog_dir)
    os.environ["FMPA_POOLED_ML_DIR"] = str(args.ml_dir)
    from pooled_ml_runtime import forecast_ml

    cases = []
    samples = []

    def accept(name: str, passed: bool, **details):
        row = {"name": name, "pass": bool(passed), **details}
        cases.append(row)
        print(("PASS" if passed else "FAIL") + " " + name, flush=True)

    status, data = fetch("/web/")
    html = data.decode("utf-8")
    accept("public_page_and_branding", status == 200
           and "<title>菜市場現場價格預測</title>" in html
           and "<h1>菜市場現場價格預測</h1>" in html
           and all(x in html for x in ("cropCategory", "cropSearch", "hasLastWeek")),
           http_status=status)
    status, raw = fetch("/web/app.js")
    text = raw.decode("utf-8")
    accept("trained_ml_js_frozen_original_separate", status == 200
           and ("已訓練的 HGB" in text or "真正訓練的 HGB" in text)
           and "trained_pooled_hgb_ml_1.0.0" in text
           and "historic-trend-baseline/1.0" not in text
           and "readBrowserRecords" in text,
           http_status=status, js_bytes=len(raw))
    status, raw = fetch("/web/catalog.json")
    catalog = json.loads(raw)
    methods = {item["crop_id"]: item["method"] for item in catalog["items"]}
    accept("61_source_fields_with_correct_ml_scope", status == 200
           and len(methods) == 61
           and sum(value == "trained_pooled_hgb_ml_1.0.0"
                   for value in methods.values()) == 57
           and sum(value == "frozen_rf_hgb_v0.1.0"
                   for value in methods.values()) == 3
           and methods["taichung_25"] == "no_public_price"
           and catalog["extended_ml_model_version"] == "multi-crop-ml/1.0.0",
           http_status=status, item_count=len(methods))

    requests = [
        ("radish_ml_A", BASE),
        ("radish_ml_B", {
            **BASE, "mode": "both", "previous_price": 30,
            "previous_price_unit": "NTD_per_taiwan_jin",
            "previous_observed_at": "2026-10-07T12:00:00+08:00",
        }),
        ("banana_ml_A", {**BASE, "crop_id": "taichung_11"}),
        ("seafood_ml_A", {**BASE, "crop_id": "taichung_43"}),
        ("egg_ml_A", {**BASE, "crop_id": "taichung_56"}),
    ]
    for idx, (name, req) in enumerate(requests):
        # Limit public inference rate on 1GB Oracle VPS while testing.
        if idx:
            time.sleep(3)
        code, body = fetch("/web/forecast", body=req)
        response = json.loads(body)
        expected = forecast_ml(req)
        exact = code == 200 and stable(response) == stable(expected)
        correct = (
            response.get("model_version") == "multi-crop-ml/1.0.0"
            and response.get("forecast_method") == "supervised_hgb_pooled"
            and response.get("ml_training_scope") == "57_new_public_market_crops"
            and all(x.get("validation_scope") == "unvalidated"
                    for x in response.get("results", []))
        )
        accept(name, exact and correct,
               http_status=code, full_original_model_parity=exact,
               model=response.get("model_version"),
               mode=response.get("mode_executed"),
               estimated_h7_h14=[
                   [r["horizon_days"], r["target_date"], r["price_estimate"],
                    r["relative_change_estimate"]]
                   for r in response.get("results", [])
               ],
               b_result_count=len(response.get("results_with_last_week", [])))

    # Original frozen three-crop RF/HGB must be used even in the new website.
    time.sleep(3)
    status, data = fetch("/web/forecast", body={**BASE, "crop_id": "cabbage"})
    cabbage = json.loads(data)
    accept("frozen_cabbage_original_rf_hgb", status == 200
           and cabbage.get("model_version") == "0.1.0"
           and "forecast_method" not in cabbage
           and [r["horizon_days"] for r in cabbage["results"]] == [7, 14],
           http_status=status)

    # The all-zero no-quote entry is in the catalog but MUST fail closed.
    time.sleep(3)
    status, data = fetch("/web/forecast", body={**BASE, "crop_id": "taichung_25"})
    error = json.loads(data)
    accept("no_price_is_not_fake_ml_prediction", status == 503
           and error.get("results") == []
           and (error.get("error") or {}).get("code") == "no_public_price",
           http_status=status)
    status, data = fetch("/healthz")
    info = json.loads(data)
    accept("original_origin_remains_ready", status == 200
           and info["status"] == "ready"
           and info["model_version"] == "0.1.0")
    status, data = fetch(
        "/v1/forecast",
        body={"crop_id":"taichung_04", "market_id":"中義市場",
              "current_price":32, "price_unit":"NTD_per_taiwan_jin",
              "observed_on":"2026-10-14"},
    )
    accept("existing_mcp_bearer_protected", status == 401,
           http_status=status)
    status, _ = fetch("/records")
    accept("no_private_records_public", status == 404, http_status=status)
    status, _ = fetch("/web/style.css")
    accept("public_web_css_remains_available", status == 200, http_status=status)

    summary = {
        "status": "PASS" if all(r["pass"] for r in cases) else "FAIL",
        "total": len(cases), "passed": sum(r["pass"] for r in cases),
        "public_url": HOST + "/web/",
        "model_version_new": "multi-crop-ml/1.0.0",
        "original_frozen_model_version": "0.1.0",
        "source_cutoff": "2026-10-02",
        "ml_holdout_did_not_beat_flat_baseline": True,
        "store_price_validation": "not_performed",
        "results": cases,
    }
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("RESULT", summary["passed"], "/", summary["total"], flush=True)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
