"""Negative-path and surface checks against the LIVE public HTTPS endpoint.

Supply a root-only credential through the OS service environment. Never echo,
print or serialize that secret. Requests use the system's validating TLS trust
store, not an insecure connection.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse overwrite of previous evidence")
    # FMPA_* wins; legacy TW01_* is read only while the new name is absent.
    secret = os.environ.get("FMPA_ORIGIN_API_TOKEN", os.environ.get("TW01_ORIGIN_API_TOKEN", ""))
    assert len(secret) >= 32
    base = {"crop_id": "cabbage", "market_id": "中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on": "2026-10-14"}
    raw = lambda obj: json.dumps(obj, ensure_ascii=False).encode("utf-8")
    cases = [
        ("missing_token", "POST", "/v1/forecast", raw(base), "", "application/json", 401, "unauthorized"),
        ("incorrect_token", "POST", "/v1/forecast", raw(base), "wrong", "application/json", 401, "unauthorized"),
        ("incorrect_scheme", "POST", "/v1/forecast", raw(base), "basic", "application/json", 401, "unauthorized"),
        ("health_no_token", "GET", "/healthz", None, "", None, 200, None),
        ("missing_price", "POST", "/v1/forecast",
         raw({k: v for k, v in base.items() if k != "current_price"}), "good", "application/json", 400, "bad_request"),
        ("duplicate_json_keys", "POST", "/v1/forecast",
         b'{"crop_id":"cabbage","crop_id":"unknown","market_id":"x"}', "good", "application/json", 400, "bad_request"),
        ("nan_json", "POST", "/v1/forecast",
         b'{"crop_id":"cabbage","market_id":"x","current_price":NaN}', "good", "application/json", 400, "bad_request"),
        ("malformed_json", "POST", "/v1/forecast",
         b'{"crop_id":', "good", "application/json", 400, "bad_request"),
        ("wrong_media_type", "POST", "/v1/forecast",
         raw(base), "good", "text/plain", 415, "unsupported_media_type"),
        ("boolean_price", "POST", "/v1/forecast",
         raw(dict(base, current_price=True)), "good", "application/json", 422, "invalid_price"),
        ("no_box_weight", "POST", "/v1/forecast",
         raw(dict(base, price_unit="NTD_per_box")), "good", "application/json", 422, "non_comparable_unit"),
        ("extra_private_data", "POST", "/v1/forecast",
         raw(dict(base, store_id="store1")), "good", "application/json", 422, "unsupported_field"),
        ("extra_network_url", "POST", "/v1/forecast",
         raw(dict(base, url="http://127.0.0.1/")), "good", "application/json", 422, "unsupported_field"),
        ("body_over_4096", "POST", "/v1/forecast",
         b"{" + b" " * 4096 + b"}", "good", "application/json", 413, "payload_too_large"),
        ("records_not_exposed", "GET", "/records", None, "", None, 404, None),
        ("agent_not_exposed", "GET", "/agent/query", None, "", None, 404, None),
        ("swagger_not_exposed", "GET", "/docs", None, "", None, 404, None),
        ("openapi_not_exposed", "GET", "/openapi.json", None, "", None, 404, None),
    ]
    outcomes = []
    for label, method, path, payload, mode, content_type, expected_status, expected_code in cases:
        headers = {}
        if mode == "good":
            headers["Authorization"] = "Bearer " + secret
        if mode == "wrong":
            headers["Authorization"] = "Bearer wrong_key"
        if mode == "basic":
            headers["Authorization"] = "Basic wrong_key"
        if content_type:
            headers["Content-Type"] = content_type
        conn = http.client.HTTPSConnection(args.host, timeout=20, context=ssl.create_default_context())
        try:
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            status = response.status
            body = response.read()
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                parsed = {}
            code = parsed.get("error", {}).get("code") if isinstance(parsed, dict) else None
            safe = secret.encode("utf-8") not in body
            good = (status == expected_status and safe and
                    (expected_code is None or code == expected_code))
            if label == "health_no_token":
                good = good and parsed.get("status") == "ready"
            row = {"case": label, "expected_status": expected_status,
                   "actual_status": status, "expected_error_code": expected_code,
                   "actual_error_code": code, "secret_not_in_response": safe, "pass": bool(good)}
        except Exception as exc:
            row = {"case": label, "pass": False, "connection_error_type": type(exc).__name__}
        finally:
            conn.close()
        outcomes.append(row)
        print(("PASS" if row["pass"] else "FAIL") + " " + label +
              " " + str(row.get("actual_status", "CONNECT_ERROR")))
    report = {"total": len(outcomes), "passed": sum(int(row["pass"]) for row in outcomes),
              "results": outcomes, "token_written_to_evidence": False,
              "tls_verified": True}
    report["failed"] = report["total"] - report["passed"]
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("RESULT", report["passed"], "/", report["total"])
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
