"""Run real /v1 requests against the extension in-process and print the results as JSON.

Started by test_v1_full_catalog.py in a separate interpreter whose PYTHONPATH
points at one code base (the deployed v1.0.0 image sources or this repo), so
the two never mix. Uses the real frozen release, catalog and pooled models.
"""
import json
import os

from fastapi.testclient import TestClient

import forecastengine_api as api
import v1_full_catalog as ext

TOKEN = os.environ["PROBE_TOKEN"]
DAY = os.environ.get("PROBE_DAY", "2026-10-27")
client = TestClient(ext.app)


def call(path, body, auth=True):
    api._timestamps.clear()
    headers = {"Authorization": "Bearer " + TOKEN} if auth else {}
    response = client.post(path, json=body, headers=headers)
    return {"status": response.status_code, "body": response.json()}


def forecast(crop, market="第三市場", price=50, unit="NTD_per_taiwan_jin", **extra):
    body = {"crop_id": crop, "market_id": market, "current_price": price, "price_unit": unit,
            "observed_on": DAY, **extra}
    return call("/v1/forecast", body)


results = {
    "quote_frozen": call("/v1/market-quote", {"crop_id": "cabbage", "market_id": "第三市場"}),
    "forecast_frozen": forecast("cabbage", price=32),
    "quote_catalog": call("/v1/market-quote", {"crop_id": "taichung_40", "market_id": "第三市場"}),
    "forecast_catalog": forecast("taichung_40"),
    "forecast_catalog_kg": forecast("taichung_06", market="第五市場", price=120, unit="NTD_per_kg"),
    "forecast_catalog_no_date": call("/v1/forecast", {"crop_id": "taichung_40", "market_id": "第三市場",
                                                       "current_price": 50, "price_unit": "NTD_per_taiwan_jin"}),
    "forecast_no_public_price": forecast("taichung_25"),
    "forecast_unknown_item": forecast("enoki_mushroom"),
    "forecast_b_field": forecast("taichung_40", previous_price=40),
    "forecast_unknown_market": forecast("taichung_40", market="建國市場"),
    "forecast_future_date": forecast("taichung_40", observed_on="2099-01-01"),
    "forecast_bad_price": forecast("taichung_40", price=-5),
    "forecast_no_auth": call("/v1/forecast", {"crop_id": "taichung_40", "market_id": "第三市場",
                                              "current_price": 50, "price_unit": "NTD_per_taiwan_jin"}, auth=False),
    # The frozen path must give exactly what the unextended adapter gives.
    "frozen_direct_results": api.execute_tool(
        "post_forecast", {"crop_id": "cabbage", "market_id": "第三市場", "current_price": 32,
                          "price_unit": "NTD_per_taiwan_jin", "observed_on": DAY},
        api.RELEASE)["engine_result"]["results"],
    "routes": sorted(getattr(r, "path", "") for r in ext.app.routes),
    "patched": [api._validate.__module__, api._call_native.__module__],
}
print(json.dumps(results, ensure_ascii=False))
