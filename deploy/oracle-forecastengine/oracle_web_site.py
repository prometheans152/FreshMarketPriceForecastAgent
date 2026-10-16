"""Isolated password-protected browser UI for the frozen ForecastEngine.

Web ingress is protected by Nginx Basic Auth. The original /v1 origin API
stays unchanged and still requires its dedicated Bearer token.

This module loads existing API as an ASGI application; no release files,
trained models, market data or Windows records are altered.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import JSONResponse

from aiot_price.integrations.chatgpt_adapter import verified_release_snapshot
from aiot_price.integrations.chatgpt_contracts import CROP_IDS, MARKETS, UNITS
from aiot_price.models.predict import ForecastEngine

import forecastengine_api as api

app = api.app
TAIPEI = ZoneInfo("Asia/Taipei")
PERMITTED = frozenset(
    {"crop_id", "market_id", "current_price", "price_unit", "observed_at",
     "mode", "previous_price", "previous_price_unit", "previous_observed_at"}
)


def _failure(status: int, code: str, message: str):
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message}},
        headers={"Cache-Control": "no-store"},
    )


def _date(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 38:
        raise ValueError("date must be an ISO8601 datetime")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("date must carry a timezone")
    if parsed.utcoffset().total_seconds() != 8 * 3600:
        raise ValueError("web observed time must use Taipei UTC+08:00")
    if parsed.astimezone(TAIPEI).date() > datetime.now(TAIPEI).date():
        raise ValueError("future observed date")
    return parsed


def _number(value: object) -> bool:
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and 0 < value <= 1_000_000
    )


def _valid_payload(body: dict):
    if set(body) - PERMITTED:
        return "unsupported_field", "網頁不支援保存到伺服器、私人店號或額外欄位。"
    mandatory = {"crop_id", "market_id", "current_price", "price_unit", "observed_at", "mode"}
    if mandatory - set(body):
        return "bad_request", "缺少必要的網頁預測欄位。"
    from full_catalog_runtime import item_supported
    if not isinstance(body["crop_id"], str) or not item_supported(body["crop_id"]):
        return "unsupported_crop", "不支援此品項。"
    if not isinstance(body["market_id"], str) or body["market_id"] not in MARKETS:
        return "unsupported_market", "不支援此市場。"
    if not _number(body["current_price"]):
        return "invalid_price", "請提供有限的正數價格。"
    if not isinstance(body["price_unit"], str) or body["price_unit"] not in UNITS:
        return "non_comparable_unit", "僅支援元／台斤或元／公斤。"
    try:
        _date(body["observed_at"])
    except (TypeError, ValueError, OverflowError):
        return "invalid_date", "請提供有效且不在未來、含時區的觀察日期。"
    if body["mode"] not in ("without_last_week", "both"):
        return "bad_request", "此網頁僅支援 A 或 A/B 對照。"
    extra_b = {"previous_price", "previous_price_unit", "previous_observed_at"} & set(body)
    if body["mode"] == "without_last_week" and extra_b:
        return "unsupported_field", "A 模式不接受上週資料。"
    if body["mode"] == "both":
        if extra_b != {"previous_price", "previous_price_unit", "previous_observed_at"}:
            return "bad_request", "A/B 對照需要上週價格、日期及單位。"
        if not _number(body["previous_price"]):
            return "invalid_price", "上週價格須為有限正數。"
        if not isinstance(body["previous_price_unit"], str) or body["previous_price_unit"] not in UNITS:
            return "non_comparable_unit", "上週價格的單位不可比。"
        try:
            _date(body["previous_observed_at"])
        except (TypeError, ValueError, OverflowError):
            return "invalid_date", "上週日期無效或在未來。"
    return None


def _native_forecast(body):
    # Frozen 0.1.0 remains ONLY for the original three supported crops.
    # New public columns are never passed into RF/HGB. Their explicitly
    # disclosed separate trend baseline reads a SHA256-verified catalog.
    if body["crop_id"] not in CROP_IDS:
        from full_catalog_runtime import forecast_baseline
        return forecast_baseline({**body, "store_id": None})
    with verified_release_snapshot(api.RELEASE) as verified:
        return ForecastEngine(verified).forecast({**body, "store_id": None})


@app.post("/site/forecast")
async def browser_forecast(request: Request):
    # Proxy only. Require an exact same-origin browser POST to prevent CSRF
    # that could exploit a cached browser Basic-Auth credential.
    origin = request.headers.get("origin", "")
    referrer = request.headers.get("referer", "")
    site = request.headers.get("sec-fetch-site", "")
    if (
        origin != "https://161.33.19.220"
        or (referrer and not referrer.startswith("https://161.33.19.220/web/"))
        or site not in ("same-origin", "none")
    ):
        return _failure(403, "origin_not_allowed", "僅接受本網頁同源請求。")
    if not api._rate_ok():
        return _failure(429, "rate_limited", "伺服器請求過多，請稍後重試。")
    body, error = await api._read_json(request)
    if error is not None:
        return error
    problem = _valid_payload(body)
    if problem is not None:
        code, message = problem
        return _failure(400 if code == "bad_request" else 422, code, message)
    if not api._busy.acquire(blocking=False):
        return _failure(429, "rate_limited", "系統正在運算，請稍後重試。")
    try:
        task = api._pool.submit(_native_forecast, body)
    except Exception:
        api._busy.release()
        return _failure(503, "not_ready", "目前無法開始運算。")
    task.add_done_callback(lambda _: api._busy.release())
    try:
        result = await asyncio.wait_for(
            asyncio.wrap_future(task), timeout=api.TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return _failure(504, "forecast_timeout", "預測超時，未提供數值。")
    except Exception:
        return _failure(503, "not_ready", "模型暫時無法使用，請稍後再試。")
    status = 200
    if result.get("error"):
        code = result["error"].get("code", "bad_request")
        status = 503 if code in (
            "stale_data_unusable", "insufficient_history",
            "no_public_price", "unstable_public_change",
        ) else 422
    return JSONResponse(
        status_code=status,
        content=result,
        headers={"Cache-Control": "no-store"},
    )
