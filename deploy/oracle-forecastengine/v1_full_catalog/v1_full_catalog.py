"""/v1 full-catalog extension (D47, 2026-10-28).

The Bearer-protected /v1/market-quote and /v1/forecast routes, which the
Cloudflare MCP Worker calls, now serve every catalog item the public website
already forecasts:

- the three original crops keep the untouched frozen RF/HGB v0.1.0 path;
- other catalog items reuse the website's own code: the 61-item public catalog
  (full_catalog_runtime) and the 57-item pooled HGB (pooled_ml_runtime).

Auth, rate limit, the single inference slot, the timeout and the A-mode-only
contract are unchanged; no B, saving or private records. This module replaces
only forecastengine_api._validate and _call_native, the same way
oracle_web_site_ml replaces oracle_web_site._native_forecast.
"""
from __future__ import annotations

import asyncio
import math
from datetime import date

from fastapi.responses import JSONResponse

import forecastengine_api as api
import oracle_web_site_ml  # registers /site/*; verifies the pooled release at import
from aiot_price.data.labels import classify_direction
from aiot_price.integrations.chatgpt_contracts import (
    CROP_IDS, MARKETS, normalized_forecast_request, taipei_today,
)
from full_catalog_runtime import data_bundle
from pooled_ml_runtime import forecast_ml

app = oracle_web_site_ml.app

FLAT_THRESHOLD = 0.05
FROZEN_STAND_IN = "cabbage"
assert FROZEN_STAND_IN in CROP_IDS

_frozen_validate = api._validate
_frozen_call_native = api._call_native

QUOTE_LIMITS = [
    "公開市場均價不等於個別店家真值，也不是即時報價。",
    "第一版不支援 B、保存、讀取私人紀錄、任意程式或 URL。",
]
FORECAST_LIMITS = [
    "公開市場均價不等於個別店家真值，也不是即時報價。",
    "店價 A 為現價錨定推估，尚未完成同店到期配對驗證。",
    "此品項使用 57 品項共同訓練的 HGB 模型；時間留出測試的相對變化 MAE 未勝不變價基準。",
    "第一版不支援 B、保存、讀取私人紀錄、任意程式或 URL。",
]


class CatalogNoData(Exception):
    """Controlled refusal: no verifiable value, so no number is returned."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def catalog_item(crop_id):
    """The catalog entry for a non-frozen item, else None (frozen or unknown)."""
    if not isinstance(crop_id, str) or crop_id in CROP_IDS:
        return None
    try:
        index = data_bundle()[2]
    except (OSError, RuntimeError, ValueError, KeyError):
        return None
    return index.get(crop_id)


def _validate(tool_name: str, body: dict):
    if not isinstance(body, dict) or catalog_item(body.get("crop_id")) is None:
        return _frozen_validate(tool_name, body)
    # Same field, market, price, unit and date rules as the frozen path;
    # only the list of accepted items differs.
    return _frozen_validate(tool_name, {**body, "crop_id": FROZEN_STAND_IN})


async def _call_native(name: str, body: dict):
    if catalog_item(body.get("crop_id")) is None:
        return await _frozen_call_native(name, body)
    if not api._busy.acquire(blocking=False):
        return api._error(429, "rate_limited", "推論服務忙碌，請稍後重試。")
    try:
        future = api._pool.submit(execute_catalog_tool, name, dict(body))
    except Exception:
        api._busy.release()
        return api._error(503, "not_ready", "無法啟動預測運算。")
    future.add_done_callback(lambda _: api._busy.release())
    try:
        result = await asyncio.wait_for(asyncio.wrap_future(future), timeout=api.TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return api._error(504, "forecast_timeout", "預測運算超時，沒有可用結果。")
    except CatalogNoData as exc:
        return api._error(503, exc.code, str(exc))
    except Exception:
        return api._error(500, "internal_error", "內部運算錯誤；不提供未驗證數值。")
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def execute_catalog_tool(name: str, body: dict, *, today: date | None = None) -> dict:
    catalog, history, index, manifest = data_bundle()
    if tuple(catalog["markets"]) != tuple(MARKETS):
        raise CatalogNoData("not_ready", "公開目錄的市場清單與 API 不一致。")
    item = index[body["crop_id"]]
    query_date = (today or taipei_today()).isoformat()
    if name == "get_market_quote":
        return _quote(body, item, catalog, history, manifest, query_date)
    if name == "post_forecast":
        return _forecast(body, item, query_date)
    raise CatalogNoData("bad_request", "未知工具。")


def _quote(body, item, catalog, history, manifest, query_date):
    cleaned = {"crop_id": body["crop_id"], "market_id": body["market_id"]}
    cutoff = catalog["source_observation_cutoff"]
    points = []
    for day, value in history.get(item["crop_id"], {}).get(body["market_id"], []):
        price = float(value)
        if day <= cutoff and math.isfinite(price) and price > 0:
            points.append((day, price))
    if not points:
        raise CatalogNoData("stale_data_unusable", "此市場此品項沒有有效的公開行情。")
    observed, price = max(points)
    raw = {
        "ok": True,
        "crop_id": item["crop_id"],
        "crop_display_name": item["display_name"],
        "market_id": body["market_id"],
        "price": price,
        "unit": "NTD_per_taiwan_jin",
        "observed_date": observed,
        "public_data_cutoff": cutoff,
        "price_age_days_at_cutoff": (date.fromisoformat(cutoff) - date.fromisoformat(observed)).days,
        "data_version": manifest["source_sha256"][:12],
    }
    age = (date.fromisoformat(query_date) - date.fromisoformat(observed)).days
    structured = {
        "tool": "get_market_quote", "input_echo": cleaned, "normalized_request": None,
        "query_date": query_date, "engine_result": raw,
        "price_age_days_at_query": age, "limits": QUOTE_LIMITS,
    }
    structured["fact_text"] = (
        f"公開市場行情：{raw['market_id']}／{item['display_name']}（{item['crop_id']}），"
        f"{price} 元／台斤；實際觀測日 {observed}，快照截止 {cutoff}。"
        f"截至臺北查詢日 {query_date} 已過 {age} 天。" + " ".join(QUOTE_LIMITS)
    )
    return structured


def _forecast(body, item, query_date):
    cleaned = {key: body[key] for key in ("crop_id", "market_id", "current_price", "price_unit")}
    cleaned["observed_on"] = body.get("observed_on") or query_date
    req = normalized_forecast_request(cleaned)
    try:
        raw = forecast_ml(dict(req))
    except ValueError as exc:
        raise CatalogNoData("stale_data_unusable", "此品項沒有可用的模型或公開資料。") from exc
    if raw.get("error"):
        raise CatalogNoData("stale_data_unusable", str(raw["error"].get("message", "預測資料不足。")))
    _check_forecast(raw, cleaned, req)
    structured = {
        "tool": "post_forecast", "input_echo": cleaned, "normalized_request": req,
        "query_date": query_date, "engine_result": raw,
        "price_age_days_at_query": (
            date.fromisoformat(query_date) - date.fromisoformat(raw["public_data_cutoff"])
        ).days,
        "limits": FORECAST_LIMITS,
    }
    facts = [
        f"A 模式：{item['display_name']}（{item['crop_id']}）／{cleaned['market_id']}，"
        f"店價 {cleaned['current_price']} {cleaned['price_unit']}，"
        f"觀測日 {cleaned['observed_on']}（台北中午）／查詢日 {query_date}。",
    ]
    for row in raw["results"]:
        facts.append(
            f"{row['horizon_days']} 天（{row['target_date']}）方向 {row['direction']}，"
            f"相對變化 {row['relative_change_estimate']}，"
            f"店價點估計 {row['price_estimate']} {row['price_estimate_unit']}，"
            f"驗證範圍 {row['validation_scope']}。"
        )
    facts.append(
        f"模型版本 {raw['model_version']}，資料版本 {raw['data_version']}，"
        f"公開資料截止 {raw['public_data_cutoff']}；"
        f"引擎警告：{'；'.join(raw.get('warnings', [])) or '無'}。"
    )
    structured["fact_text"] = " ".join(facts + FORECAST_LIMITS)
    return structured


def _check_forecast(raw: dict, cleaned: dict, req: dict) -> None:
    """Same output checks the frozen adapter applies; any mismatch returns no number."""
    def bad(message):
        raise CatalogNoData("stale_data_unusable", message)

    if raw.get("store_id") is not None or raw.get("mode_executed") != "without_last_week":
        bad("推論結果不是規定的匿名 A 模式。")
    if (raw.get("crop_id") != cleaned["crop_id"] or raw.get("market_id") != cleaned["market_id"]
            or raw.get("input_observed_at") != req["observed_at"]
            or not raw.get("model_version") or not raw.get("data_version")
            or raw.get("results_with_last_week")):
        bad("預測結果的來源、版本、市場或 A 模式資料不一致。")
    rows = raw.get("results")
    if not isinstance(rows, list) or [r.get("horizon_days") for r in rows if isinstance(r, dict)] != [7, 14]:
        bad("必須恰好取得一筆 7 天與一筆 14 天的推估。")
    base = date.fromisoformat(cleaned["observed_on"]).toordinal()
    for row in rows:
        if date.fromisoformat(row["target_date"]).toordinal() != base + row["horizon_days"]:
            bad("回傳的期限不是精確 t+7/t+14 日。")
        if any(row.get(k) is not None for k in ("probability", "interval_low", "interval_high")):
            bad("模型未經校準，不允許機率或區間值。")
        price, delta = row.get("price_estimate"), row.get("relative_change_estimate")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
               for x in (price, delta)):
            bad("回傳非有限價格／相對變化。")
        if price <= 0 or row.get("price_estimate_unit") != cleaned["price_unit"]:
            bad("回傳的店價估計或單位不合法。")
        if row.get("target_scope") != "store_price_estimate" or row.get("validation_scope") != "unvalidated":
            bad("預測目標或驗證範圍與契約不一致。")
        direction = row.get("direction")
        if direction not in ("up", "down", "flat"):
            bad("回傳未知的方向分類。")
        if abs(abs(delta) - FLAT_THRESHOLD) <= 0.000051:
            allowed = ("flat", "up" if delta >= 0 else "down")
            if direction not in allowed:
                bad("方向與相對變化不一致。")
        elif classify_direction(delta, FLAT_THRESHOLD) != direction:
            bad("方向與相對變化不一致。")
        expected = round(cleaned["current_price"] * (1 + delta), 1)
        if abs(price - expected) > 0.11 + cleaned["current_price"] * 0.000051:
            bad("店價點估計與相對變化不一致。")


api._validate = _validate
api._call_native = _call_native
