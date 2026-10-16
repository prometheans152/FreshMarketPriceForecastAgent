"""Compare actual HTTPS engine_result to native Windows ForecastEngine output.

Keep original server-generated request_id in the evidence; ignore it ONLY for
comparisons, without rounding numbers or dropping any other model fields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(windows: dict, https: dict) -> dict:
    results = {case["case"]: case for case in https["results"]}
    links = {
        "cabbage_32_jin": 0,
        "cabbage_65_kg": 1,
        "cabbage_historical": 2,
        "no_date": 5,
    }
    checks = []
    for label, idx in links.items():
        actual = results[label]["response"]
        expected = windows["cases"][idx]
        original = actual["engine_result"]
        native = expected["native_result"]
        dynamic = {"request_id"}
        # Preserve full objects unchanged in the source evidence.
        expected_comparable = {k: v for k, v in native.items() if k not in dynamic}
        actual_comparable = {k: v for k, v in original.items() if k not in dynamic}
        row = {
            "case": label,
            "input_parity": actual["normalized_request"] == expected["normalized_request"],
            "full_native_parity_except_request_id": expected_comparable == actual_comparable,
            "both_request_ids_preserved": bool(native.get("request_id") and original.get("request_id")),
            "horizons": [v["horizon_days"] for v in original["results"]],
        }
        row["pass"] = all(row[key] for key in (
            "input_parity", "full_native_parity_except_request_id", "both_request_ids_preserved"
        )) and row["horizons"] == [7, 14]
        if not row["full_native_parity_except_request_id"]:
            row["mismatched_fields"] = sorted(
                key for key in expected_comparable.keys() | actual_comparable.keys()
                if expected_comparable.get(key) != actual_comparable.get(key)
            )
        checks.append(row)
    quote = results["quote"]["response"]["engine_result"]
    original_quote = windows["quotes"][0]["native_result"]
    checks.append({
        "case": "quote",
        "pass": quote == original_quote,
        "full_native_quote_parity": quote == original_quote,
    })
    return {
        "comparisons": len(checks),
        "pass_count": sum(int(item["pass"]) for item in checks),
        "fail_count": sum(int(not item["pass"]) for item in checks),
        "dynamic_fields_ignored_for_comparison_only": ["engine_result.request_id"],
        "checks": checks,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--https", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite evidence")
    reference = json.loads(args.windows.read_text(encoding="utf-8-sig"))
    actual = json.loads(args.https.read_text(encoding="utf-8-sig"))
    result = compare(reference, actual)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["fail_count"] == 0 else 1)
