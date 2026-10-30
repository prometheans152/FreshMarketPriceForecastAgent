"""Run real requests against the served app in-process and print the results as JSON.

Started by test_rolling_history.py in a fresh interpreter whose PYTHONPATH
points at one code base (the deployed v1.0.0 image sources). PROBE_APP picks
the app: "rolling" (D48, reads $FMPA_ROLLING_DIR) or "v1ext" (D47, frozen
history only), so the two can be compared. With PROBE_SWAP_SOURCE set, the
probe publishes that download while running and checks that the switch waits
for the single inference lock.
"""
import json
import os
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import forecastengine_api as api

ROLLING = os.environ["PROBE_APP"] == "rolling"
if ROLLING:
    import rolling_runtime as served
else:
    import v1_full_catalog as served
import oracle_web_site

TOKEN = os.environ["PROBE_TOKEN"]
DAYS = {"day": os.environ["PROBE_DAY"], "parity": os.environ["PROBE_PARITY_DAY"]}
client = TestClient(served.app)


def call(path, body=None):
    api._timestamps.clear()
    if body is None:
        response = client.get(path)
    else:
        response = client.post(path, json=body, headers={"Authorization": "Bearer " + TOKEN})
    return {"status": response.status_code, "body": response.json()}


def forecast(crop, day, market="第三市場", price=50):
    return call("/v1/forecast", {"crop_id": crop, "market_id": market, "current_price": price,
                                 "price_unit": "NTD_per_taiwan_jin", "observed_on": day})


def website(crop, day, market="第三市場", price=50):
    body = {"crop_id": crop, "market_id": market, "current_price": price,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": day + "T12:00:00+08:00",
            "mode": "without_last_week"}
    return oracle_web_site._native_forecast(body)


results = {"health": call("/healthz")}
if os.environ.get("PROBE_SWAP_SOURCE"):
    import rolling_update

    results["before_swap"] = served.status()
    code, published = rolling_update.run(
        Path(os.environ["FMPA_ROLLING_DIR"]), source_file=Path(os.environ["PROBE_SWAP_SOURCE"]),
        today=date.fromisoformat(os.environ["PROBE_TODAY"]), accept_shorter=False)
    results["swap_publish"] = {"code": code, **published}
    api._busy.acquire()          # an inference is running
    served.refresh()
    results["while_busy"] = served.status()
    api._busy.release()
    results["after_idle"] = call("/healthz")["body"]["public_history"]

for name, day in DAYS.items():
    results[name] = {
        "quote_frozen": call("/v1/market-quote", {"crop_id": "cabbage", "market_id": "第三市場"}),
        "quote_catalog": call("/v1/market-quote", {"crop_id": "taichung_40", "market_id": "第三市場"}),
        "forecast_frozen": forecast("cabbage", day, price=32),
        "forecast_catalog": forecast("taichung_40", day),
        "forecast_catalog_2": forecast("taichung_06", day, market="第五市場", price=120),
        "web_frozen": website("bok_choy", day, market="第五市場", price=45),
        "web_catalog": website("taichung_04", day, market="中義市場", price=25),
    }
results["patched"] = [api._validate.__module__, api._call_native.__module__,
                      api._ready_metadata.__module__]
try:
    import psutil
    results["rss_mb"] = round(psutil.Process().memory_info().rss / 2**20, 1)
except ImportError:
    results["rss_mb"] = None
print(json.dumps(results, ensure_ascii=False))
