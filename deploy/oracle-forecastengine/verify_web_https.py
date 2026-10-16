"""Live HTTPS browser-form acceptance, including server-side login isolation.

Run on the authorized Oracle VPS as root; reads ONLY separate web-login.txt.
It does not read, print, reuse, store, or transmit the ForecastEngine origin
Bearer token. Saved evidence contains statuses, booleans and model fields, not
the web password or HTTP Authorization headers.
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import ssl
import sys
from pathlib import Path

HOST = "161.33.19.220"
BODY = {
    "crop_id": "cabbage",
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}
SITE_ORIGIN = "https://" + HOST


def web_auth_header() -> str:
    # No secrets in CLI args, process environment, logs or report contents.
    pairs = dict(line.split(": ", 1) for line in Path(
        "/etc/fresh-market-price-agent-forecastengine/web-login.txt"
    ).read_text(encoding="utf-8").splitlines())
    assert pairs["Username"] and len(pairs["Password"]) >= 28
    encoded = base64.b64encode(
        (pairs["Username"] + ":" + pairs["Password"]).encode("utf-8")
    ).decode("ascii")
    return "Basic " + encoded


def check(name, method, path, *, authorized=False, payload=None, origin=SITE_ORIGIN,
          expected=200, expected_code=None, tls=True):
    conn = (
        http.client.HTTPSConnection(HOST, context=ssl.create_default_context(), timeout=28)
        if tls else http.client.HTTPConnection(HOST, timeout=20)
    )
    headers = {"Accept": "application/json"}
    if authorized:
        headers["Authorization"] = web_auth_header()
    if payload is not None:
        headers.update({
            "Content-Type": "application/json",
            "Origin": origin,
            "Referer": SITE_ORIGIN + "/web/",
            "Sec-Fetch-Site": "same-origin" if origin == SITE_ORIGIN else "cross-site",
        })
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    else:
        body = None
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        content = response.read(500_000)
        status = response.status
        location = response.getheader("Location", "")
        try:
            obj = json.loads(content)
        except (ValueError, UnicodeError):
            obj = None
        text = content.decode("utf-8", "replace")
        error = obj.get("error") if isinstance(obj, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        passed = status == expected and (expected_code is None or code == expected_code)
        details = {"case": name, "status": status, "expected": expected,
                   "error_code": code, "pass": passed}
        if path == "/" and not tls and status == 301:
            details["pass"] &= location == SITE_ORIGIN + "/web/"
        if name == "https_root_redirect":
            details["pass"] &= location in ("/web/", SITE_ORIGIN + "/web/")
        if name == "protected_web_html" and status == 200:
            details["pass"] &= all(x in text for x in (
                "predictForm", "hasLastWeek", "saveRecordBtn", "recordsPanel",
                "瀏覽器", "A／B"
            ))
            details["pass"] &= "private" not in (response.getheader("Cache-Control", ""))
        if name == "protected_web_js" and status == 200:
            details["pass"] &= all(x in text for x in (
                "function readBrowserRecords()", "function exportBrowserRecords",
                "const API_FORECAST = 'forecast'"
            ))
            details["pass"] &= "fetchJson(API_RECORDS" not in text
        if name in ("web_a_forecast", "web_b_forecast") and status == 200:
            details["model_version"] = obj.get("model_version")
            details["data_version"] = obj.get("data_version")
            details["executed_mode"] = obj.get("mode_executed")
            details["target_dates"] = [x.get("target_date") for x in (
                obj.get("results_without_last_week") or obj.get("results") or []
            )]
            details["b_horizons"] = [x.get("horizon_days") for x in obj.get(
                "results_with_last_week", []
            )]
            details["pass"] &= (
                obj.get("model_version") == "0.1.0"
                and obj.get("data_version") == "172dffc76e82"
                and details["target_dates"] == ["2026-10-21", "2026-10-28"]
                and obj.get("store_id") is None
            )
            if name == "web_b_forecast":
                details["pass"] &= obj["mode_executed"] == "both"
                details["pass"] &= details["b_horizons"] == [7, 14]
            else:
                details["pass"] &= obj["mode_executed"] == "without_last_week"
                details["pass"] &= not details["b_horizons"]
        if name == "healthz" and status == 200:
            details["pass"] &= obj.get("status") == "ready"
        print(("PASS " if details["pass"] else "FAIL ") + name + " HTTP " + str(status))
        return details
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("refuse overwrite of web acceptance evidence")
    b = {**BODY, "mode": "both", "previous_price": 30,
         "previous_price_unit": "NTD_per_taiwan_jin",
         "previous_observed_at": "2026-10-07T12:00:00+08:00"}
    cases = [
        ("http_root_redirect", "GET", "/", dict(tls=False, expected=301)),
        ("http_api_denied", "POST", "/v1/forecast",
         dict(payload=BODY, expected=404, tls=False)),
        ("https_root_redirect", "GET", "/", dict(expected=302)),
        ("anonymous_web_requires_login", "GET", "/web/", dict(expected=401)),
        ("anonymous_script_requires_login", "GET", "/web/app.js", dict(expected=401)),
        ("anonymous_forecast_requires_login", "POST", "/web/forecast",
         dict(payload=BODY, expected=401)),
        ("protected_web_html", "GET", "/web/", dict(authorized=True)),
        ("protected_web_js", "GET", "/web/app.js", dict(authorized=True)),
        ("protected_web_css", "GET", "/web/style.css", dict(authorized=True)),
        ("web_a_forecast", "POST", "/web/forecast", dict(authorized=True, payload=BODY)),
        ("web_b_forecast", "POST", "/web/forecast", dict(authorized=True, payload=b)),
        ("cross_origin_denied", "POST", "/web/forecast", dict(
            authorized=True, payload=BODY, origin="https://other.example",
            expected=403, expected_code="origin_not_allowed"
        )),
        ("bad_unit_rejected", "POST", "/web/forecast", dict(
            authorized=True, payload={**BODY, "price_unit": "per_box"},
            expected=422, expected_code="non_comparable_unit"
        )),
        ("private_id_rejected", "POST", "/web/forecast", dict(
            authorized=True, payload={**BODY, "store_id": "private"},
            expected=422, expected_code="unsupported_field"
        )),
        ("website_server_records_absent", "GET", "/web/records",
         dict(authorized=True, expected=404)),
        ("oracle_api_bearer_preserved", "POST", "/v1/forecast",
         dict(authorized=False, payload=BODY, expected=401)),
        ("healthz", "GET", "/healthz", dict()),
    ]
    outcomes = []
    for name, method, path, opts in cases:
        try:
            outcomes.append(check(name, method, path, **opts))
        except Exception as err:
            outcomes.append({"case": name, "pass": False,
                             "error_type": type(err).__name__})
            print("FAIL", name, type(err).__name__)
    result = {"total": len(outcomes),
              "passed": sum(x["pass"] for x in outcomes),
              "results": outcomes,
              "origin_api_token_accessed": False,
              "web_password_recorded": False}
    result["failed"] = result["total"] - result["passed"]
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT", result["passed"], "/", result["total"])
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
