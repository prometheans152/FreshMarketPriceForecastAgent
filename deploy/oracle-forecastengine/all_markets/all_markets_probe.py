"""Real D49 model probe on either portable-image or repo sources.

The rolling version is a SYNTHETIC test fixture: one extra day built from the
last available frozen public quote for each market. It tests D48's verified
parquet/catalog switch, never claims to be a fresh government publication.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import tempfile
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import forecastengine_api as api
import full_catalog_runtime
import rolling_store as store

TOKEN = os.environ["PROBE_TOKEN"]
DAY = "2026-10-16"
RELEASE = Path(os.environ.get("TW01_RELEASE_DIR", os.environ.get("FMPA_RELEASE_DIR", "")))


def make_rolling(directory: Path) -> dict:
    bundle = full_catalog_runtime.data_bundle()
    base = store.load_frozen_base(RELEASE, bundle)
    source = []
    for market in base.markets:
        row = {store.MARKET: market, store.OBS_DATE: "20261003"}
        for crop_id, column in zip(base.crop_ids, base.columns):
            points = bundle[1][crop_id].get(market, [])
            row[column] = str(points[-1][1]) if points else "0"
        source.append(row)
    raw = store.canonical(source)
    download = store.parse_download(raw, base, date(2026, 10, 16))
    result = store.publish(directory, base, bundle[1], None, download, raw,
                           retrieved_at="2026-10-16T00:00:00+00:00",
                           accept_shorter=True)
    assert result["outcome"] == "switched" and result["cutoff"] == "2026-10-03", result
    return result


def call(client: TestClient, path: str, body: dict) -> dict:
    api._timestamps.clear()
    result = client.post(path, json=body, headers={"Authorization": "Bearer " + TOKEN})
    return {"status": result.status_code, "body": result.json()}


def forecast_body(crop, market="all_markets"):
    return {"crop_id": crop, "market_id": market, "current_price": 50,
            "price_unit": "NTD_per_taiwan_jin", "observed_on": DAY}


def checked_medians(envelope: dict):
    raw = envelope["body"]["engine_result"]
    assert raw["valid_market_count"] == len(raw["market_predictions"])
    assert raw["valid_market_count"] >= 3
    for i, horizon in enumerate((7, 14)):
        series = [r["results"][i]["relative_change_estimate"] for r in raw["market_predictions"]]
        row = raw["results"][i]
        assert row["horizon_days"] == horizon
        assert abs(row["relative_change_estimate"] - statistics.median(series)) <= 0.00005, (
            f"median mismatch: horizon={horizon} got={row['relative_change_estimate']} "
            f"want={statistics.median(series)}")
        assert row["relative_change_min"] == min(series)
        assert row["relative_change_max"] == max(series)
        assert row["price_estimate"] == round(50 * (1 + row["relative_change_estimate"]), 1)
    return {"market_count": raw["valid_market_count"], "model": raw["model_version"],
            "cutoff": raw["public_data_cutoff"]}


def main():
    with tempfile.TemporaryDirectory(prefix="d49-rolling-", dir=Path(__file__).resolve().parent) as folder:
        rolling_dir = Path(folder)
        published = make_rolling(rolling_dir)
        os.environ["FMPA_ROLLING_DIR"] = str(rolling_dir)
        import all_markets_runtime as served
        if os.environ.get("PROBE_FORCE_MEAN") == "1":
            served.median = statistics.mean  # deliberate mutation: tests must reject it
        client = TestClient(served.app)
        health = client.get("/healthz").json()
        assert health["public_history"]["source"] == "rolling"
        assert health["public_data_cutoff"] == "2026-10-03"
        assert served.app is api.app

        results = {"source_prefix": os.environ["PROBE_SOURCE_PREFIX"],
                   "rolling_cutoff": health["public_data_cutoff"],
                   "published": published["outcome"],
                   "patched": [api._validate.__module__, api._call_native.__module__],
                   "cases": {}}
        for crop, key in (("cabbage", "frozen"), ("taichung_40", "pooled")):
            responses = []
            timings = []
            for _ in range(3):
                begin = time.perf_counter()
                response = call(client, "/v1/forecast", forecast_body(crop))
                timings.append(round(time.perf_counter() - begin, 4))
                assert response["status"] == 200, response
                responses.append(checked_medians(response))
                all_limits = " ".join(response["body"]["limits"])
                if key == "frozen":
                    assert "RF（7 天）" in all_limits and "57 品項" not in all_limits
                else:
                    assert "57 品項" in all_limits
            assert len(set(r["market_count"] for r in responses)) == 1
            results["cases"][key] = {
                **responses[0],
                "elapsed_seconds": timings,
                "mean_seconds": round(statistics.mean(timings), 4),
                "max_seconds": round(max(timings), 4),
                "envelope": response,
            }

        # A single D49 frozen request must enter D48's verified snapshot
        # exactly once despite attempting all 13 markets.
        original_snapshot = served.chatgpt_adapter.verified_release_snapshot
        snapshot_count = [0]

        @contextmanager
        def counted_snapshot(release):
            snapshot_count[0] += 1
            with original_snapshot(release) as path:
                yield path

        served.chatgpt_adapter.verified_release_snapshot = counted_snapshot
        try:
            counted_response = call(client, "/v1/forecast", forecast_body("cabbage"))
        finally:
            served.chatgpt_adapter.verified_release_snapshot = original_snapshot
        assert counted_response["status"] == 200
        assert snapshot_count[0] == 1, "one request must verify/copy frozen release only once"
        results["snapshot_verifications_per_frozen_request"] = snapshot_count[0]

        result = call(client, "/v1/market-quote", {
            "crop_id": "cabbage", "market_id": "all_markets"})
        results["quote_all"] = {"status": result["status"], "code": result["body"]["error"]["code"]}
        assert results["quote_all"] == {"status": 422, "code": "unsupported_market"}

        original_tools = served.AgentTools

        class OnlyTwoMarkets:
            def __init__(self, engine):
                self.delegate = original_tools(engine)

            def post_forecast(self, req):
                if req["market_id"] not in served.MARKETS[:2]:
                    return {"error": {"code": "stale_data_unusable", "message": "synthetic missing market"}}
                return self.delegate.post_forecast(req)

        served.AgentTools = OnlyTwoMarkets
        try:
            refused = call(client, "/v1/forecast", forecast_body("cabbage"))
        finally:
            served.AgentTools = original_tools
        assert refused["status"] == 503 and "engine_result" not in refused["body"], refused
        results["insufficient"] = {
            "status": refused["status"],
            "code": refused["body"]["error"]["code"],
        }

        market_request = forecast_body("cabbage", "第三市場")

        async def same_single_market():
            original = await served._previous_call_native("post_forecast", market_request)
            patched = await api._call_native("post_forecast", market_request)
            return json.loads(original.body), json.loads(patched.body)

        before, after = asyncio.run(same_single_market())
        # An original ForecastEngine request_id includes clock microseconds even
        # when the same original function is called twice. Exclude only that
        # intentionally non-deterministic value; every other field must match.
        for response in (before, after):
            response["engine_result"].pop("request_id", None)
        assert before == after, "a named-market response changed after D49 patch"
        results["named_market_parity"] = "all deterministic fields identical"

        # The negative-control property checks real model output. A change from
        # median to mean must fail for at least one model/horizon in this probe.
        source = results["cases"]["frozen"]["envelope"]["body"]["engine_result"]
        series = [
            [r["results"][i]["relative_change_estimate"] for r in source["market_predictions"]]
            for i in range(2)
        ]
        results["negative_mean_control"] = any(
            abs(round(statistics.mean(v), 4) - round(statistics.median(v), 4)) > 0.00005
            for v in series
        )
        print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
