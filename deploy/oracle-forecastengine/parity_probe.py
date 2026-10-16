"""Collect full native result objects for strict Windows/Oracle parity.

Only a top-level timestamp-derived request_id is excluded from the comparison,
and its unmodified original is kept separately in each evidence JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import date
from pathlib import Path

from aiot_price.agent.tools import AgentTools
from aiot_price.integrations.chatgpt_adapter import verify_frozen_release
from aiot_price.integrations.chatgpt_contracts import normalized_forecast_request, validate_arguments
from aiot_price.models.predict import ForecastEngine


def run(release: Path) -> dict:
    verify_frozen_release(release)
    engine = ForecastEngine(release)
    tools = AgentTools(engine)
    inputs = [
        {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
         "price_unit": "NTD_per_taiwan_jin", "observed_on": "2026-10-14"},
        {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 65,
         "price_unit": "NTD_per_kg", "observed_on": "2026-10-14"},
        {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
         "price_unit": "NTD_per_taiwan_jin", "observed_on": "2026-09-30"},
        {"crop_id": "bok_choy", "market_id": "中義市場", "current_price": 50,
         "price_unit": "NTD_per_taiwan_jin", "observed_on": "2026-10-14"},
        {"crop_id": "sponge_gourd", "market_id": "中義市場", "current_price": 40,
         "price_unit": "NTD_per_taiwan_jin", "observed_on": "2026-10-14"},
        {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
         "price_unit": "NTD_per_taiwan_jin"},
    ]
    cases = []
    for request in inputs:
        normalized = validate_arguments("post_forecast", request)
        native_request = normalized_forecast_request(normalized)
        raw = tools.post_forecast(native_request)
        assert raw["error"] is None, raw["error"]
        assert len(raw["results"]) == 2
        cases.append({"input": request, "normalized_request": native_request,
                      "native_result": raw})
    quotes = []
    for crop in ("cabbage", "bok_choy", "sponge_gourd"):
        input_obj = {"crop_id": crop, "market_id": "中義市場"}
        quotes.append({"input": input_obj, "native_result": tools.get_market_quote(**input_obj)})
    return {
        "platform": {"os": platform.platform(), "python": sys.version.split()[0]},
        "model_version": engine.manifest["model_version"],
        "data_version": engine.manifest["source"]["json_sha256"][:12],
        "public_data_cutoff": str(engine.public_cutoff.date()),
        "cases": cases,
        "quotes": quotes,
    }


def compare(a: dict, b: dict) -> dict:
    failures = []
    if len(a["cases"]) != len(b["cases"]) or len(a["quotes"]) != len(b["quotes"]):
        return {"pass": False, "mismatches": ["case or quote count differs"]}
    for name in ("model_version", "data_version", "public_data_cutoff", "quotes"):
        if a[name] != b[name]:
            failures.append(name)
    for index, (left, right) in enumerate(zip(a["cases"], b["cases"])):
        if left["input"] != right["input"] or left["normalized_request"] != right["normalized_request"]:
            failures.append(f"case_{index}_request")
        x = dict(left["native_result"])
        y = dict(right["native_result"])
        assert "request_id" in x and "request_id" in y
        x.pop("request_id")
        y.pop("request_id")
        if x != y:
            failures.append(f"case_{index}_native_output")
    return {"pass": not failures, "comparisons": len(a["cases"]) + len(a["quotes"]),
            "mismatches": failures,
            "request_ids_preserved_in_input_evidence": True,
            "ignored_for_comparison_only": ["native_result.request_id"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--compare", type=Path, nargs=2, metavar=("WINDOWS", "ORACLE"))
    args = ap.parse_args()
    if args.compare:
        files = [json.loads(path.read_text(encoding="utf-8-sig")) for path in args.compare]
        outcome = compare(*files)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        sys.exit(0 if outcome["pass"] else 1)
    if args.release is None or args.output is None:
        ap.error("--release and --output are required except when --compare is used")
    results = run(args.release)
    if args.output.exists():
        ap.error("output already exists; refuse overwriting parity evidence")
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"native parity evidence: {len(results['cases'])} forecasts / {len(results['quotes'])} market quotes")
