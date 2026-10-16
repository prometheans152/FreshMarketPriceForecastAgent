"""True local FMPA Docker end-to-end acceptance; Python standard library only.

Includes public A/B trained ML, original RF/HGB, strict Origin Token API, and
MCP JSON-RPC initialize/tools/list/tools/call. Does NOT print or store tokens,
send data to Oracle, train/retrain, read private records, or change services.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://localhost:8080"
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(path: str, *, method: str = "GET", body=None, headers=None):
    options = dict(headers or {})
    if body is not None:
        options.setdefault("Content-Type", "application/json")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        ORIGIN + path, method=method, data=data,
        headers=options,
    )
    try:
        with DIRECT.open(request, timeout=28) as result:
            status = result.status
            payload = result.read(500_000)
            response_headers = result.headers
    except urllib.error.HTTPError as failure:
        status = failure.code
        payload = failure.read(500_000)
        response_headers = failure.headers
    try:
        parsed = json.loads(payload)
    except (UnicodeError, ValueError):
        parsed = None
    return status, parsed, payload, response_headers


def redact_result(name, passed, *, status=None, extra=None):
    result = {"case": name, "pass": bool(passed)}
    if status is not None:
        result["http_status"] = status
    if extra is not None:
        result["safe_details"] = extra
    print(("PASS" if passed else "FAIL") + " " + name +
          (f" HTTP {status}" if status is not None else ""), flush=True)
    return result


def rpc(method: str, ident: int, *, params=None, token: str | None = None):
    request = {"jsonrpc": "2.0", "id": ident, "method": method}
    if params is not None:
        request["params"] = params
    headers = {"Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-06-18"}
    if token:
        headers["Authorization"] = "Bearer " + token
    return fetch("/mcp", method="POST", body=request, headers=headers)


def run(base: str):
    global ORIGIN
    ORIGIN = base.rstrip("/")
    checks = []

    def add(name, success, status=None, extra=None):
        checks.append(redact_result(name, success, status=status, extra=extra))

    a = {
        "crop_id": "taichung_04", "market_id": "中義市場",
        "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
        "observed_at": "2026-10-14T12:00:00+08:00",
        "mode": "without_last_week",
    }
    browser_headers = {
        "Origin": ORIGIN, "Referer": ORIGIN + "/web/",
        "Sec-Fetch-Site": "same-origin",
    }
    # urllib follows 302, so root GET should return the public HTML page.
    status, _, content, _ = fetch("/")
    add("root_redirects_to_public_web", status == 200 and b"cropSearch" in content, status)
    status, _, content, _ = fetch("/web/")
    html = content.decode("utf-8")
    add("public_website_no_password", status == 200 and
        "<title>菜市場現場價格預測</title>" in html and
        "predictForm" in html and "hasLastWeek" in html, status)
    status, _, js, _ = fetch("/web/app.js")
    text = js.decode("utf-8")
    add("trained_ml_browser_js", status == 200 and
        "trained_pooled_hgb_ml_1.0.0" in text and
        "readBrowserRecords" in text and "真正訓練的 HGB" in text, status)
    status, catalog, _, _ = fetch("/web/catalog.json")
    items = catalog["items"] if isinstance(catalog, dict) else []
    add("official_61_item_catalog", status == 200 and
        len(items) == 61 and
        sum(row["method"] == "trained_pooled_hgb_ml_1.0.0" for row in items) == 57 and
        sum(row["method"] == "frozen_rf_hgb_v0.1.0" for row in items) == 3, status)
    status, health, _, _ = fetch("/healthz")
    add("frozen_release_health", status == 200 and
        health.get("status") == "ready" and health.get("model_version") == "0.1.0", status)

    status, pred, _, _ = fetch("/web/forecast", method="POST", body=a, headers=browser_headers)
    add("new_supervised_ml_h7_and_h14", status == 200 and
        pred.get("model_version") == "multi-crop-ml/1.0.0" and
        pred.get("forecast_method") == "supervised_hgb_pooled" and
        [r["target_date"] for r in pred["results"]] == ["2026-10-21", "2026-10-28"] and
        pred.get("store_id") is None, status)

    body_b = dict(a, mode="both", previous_price=30,
                  previous_price_unit="NTD_per_taiwan_jin",
                  previous_observed_at="2026-10-07T12:00:00+08:00")
    status, pred, _, _ = fetch("/web/forecast", method="POST", body=body_b,
                               headers=browser_headers)
    add("new_trained_ml_A_B_comparison", status == 200 and
        pred.get("mode_executed") == "both" and
        [r["horizon_days"] for r in pred["results_without_last_week"]] == [7, 14] and
        [r["horizon_days"] for r in pred["results_with_last_week"]] == [7, 14],
        status)

    status, pred, _, _ = fetch("/web/forecast", method="POST",
                               body=dict(a, crop_id="cabbage"),
                               headers=browser_headers)
    add("original_RF_HGB_v0_1_0_preserved", status == 200 and
        pred.get("model_version") == "0.1.0" and
        [r["horizon_days"] for r in pred["results"]] == [7, 14], status)
    status, err, _, _ = fetch("/web/forecast", method="POST",
                              body=dict(a, crop_id="taichung_25"),
                              headers=browser_headers)
    add("unpriced_item_fails_closed", status == 503 and
        err.get("error", {}).get("code") == "no_public_price" and
        err.get("results") == [], status)
    status, err, _, _ = fetch("/web/forecast", method="POST",
                              body=a, headers={
                                  **browser_headers, "Origin": "https://evil.example",
                                  "Sec-Fetch-Site": "cross-site",
                              })
    add("web_origin_guard", status == 403 and
        err.get("error", {}).get("code") == "origin_not_allowed", status)
    status, _, _, _ = fetch("/records")
    add("private_records_not_exposed", status == 404, status)

    status, _, _, _ = fetch("/v1/market-quote", method="POST",
                            body={"crop_id":"cabbage","market_id":"中義市場"})
    add("origin_API_requires_separate_bearer", status == 401, status)
    origin_path = ROOT / ".secrets" / "origin_api_token"
    origin_token = origin_path.read_text(encoding="utf-8").strip()
    assert len(origin_token) >= 32
    status, quote, _, _ = fetch("/v1/market-quote", method="POST",
        body={"crop_id":"cabbage","market_id":"中義市場"},
        headers={"Authorization": "Bearer " + origin_token})
    add("origin_API_real_public_quote", status == 200 and
        quote.get("tool") == "get_market_quote" and
        quote["engine_result"].get("unit") == "NTD_per_taiwan_jin", status)

    status, _, _, _ = fetch("/mcp", method="POST",
        body={"jsonrpc":"2.0","id":100,"method":"tools/list","params":{}})
    add("self_hosted_mcp_bearer_required", status == 401, status)
    client_token = (ROOT / ".secrets" / "mcp_client_token").read_text(
        encoding="utf-8").strip()
    assert origin_token != client_token and len(client_token) >= 32
    status, init, _, _ = rpc("initialize", 101, token=client_token,
        params={"protocolVersion":"2025-06-18","capabilities":{},
                "clientInfo":{"name":"fresh-market-price-agent-docker-smoke","version":"1.0"}})
    add("self_hosted_mcp_initialize", status == 200 and
        isinstance(init, dict) and "result" in init, status)
    status, listed, _, _ = rpc("tools/list", 102, token=client_token,
                              params={})
    tools = listed.get("result", {}).get("tools", []) if isinstance(listed, dict) else []
    add("self_hosted_mcp_exact_two_tools", status == 200 and
        {t["name"] for t in tools} == {"get_market_quote", "post_forecast"}, status)
    status, called, _, _ = rpc("tools/call", 103, token=client_token, params={
        "name": "get_market_quote",
        "arguments": {"crop_id":"cabbage","market_id":"中義市場"},
    })
    result = called.get("result", {}) if isinstance(called, dict) else {}
    structured = result.get("structuredContent", {})
    add("self_hosted_mcp_real_quote", status == 200 and
        result.get("isError") is False and
        structured.get("tool") == "get_market_quote", status)
    status, called, _, _ = rpc("tools/call", 104, token=client_token, params={
        "name":"post_forecast",
        "arguments":{"crop_id":"cabbage","market_id":"中義市場",
                     "current_price":32,"price_unit":"NTD_per_taiwan_jin",
                     "observed_on":"2026-10-14"},
    })
    result = called.get("result", {}) if isinstance(called, dict) else {}
    structured = result.get("structuredContent", {})
    rows = structured.get("engine_result", {}).get("results", [])
    add("self_hosted_mcp_real_forecast_A_only", status == 200 and
        result.get("isError") is False and
        structured.get("tool") == "post_forecast" and
        [r["horizon_days"] for r in rows] == [7, 14], status)

    report = {"status":"PASS" if all(e["pass"] for e in checks) else "FAIL",
              "passed":sum(e["pass"] for e in checks), "total":len(checks),
              "base_url":ORIGIN,"model_scope":"57_trained+3_frozen+1_unpriced",
              "origin_token_written":False,"mcp_token_written":False,
              "checks":checks}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=ORIGIN)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "test-results" / "docker_acceptance.json")
    args = parser.parse_args()
    report = run(args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit("Refusing to overwrite old acceptance evidence: " + str(args.output))
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print("DOCKER_REAL_E2E", report["passed"], "/", report["total"], report["status"])
    raise SystemExit(0 if report["status"] == "PASS" else 1)
