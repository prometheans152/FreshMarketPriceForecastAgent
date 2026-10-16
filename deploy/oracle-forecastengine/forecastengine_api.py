"""FMPA public-origin API. A strict, stateless wrapper of the frozen ForecastEngine.

No record storage, training, model mutation, LLMs, user-controlled paths or URLs.
Run behind a publicly trusted HTTPS reverse proxy; never bind this ASGI app publicly.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import math
import os
import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aiot_price.integrations.chatgpt_adapter import (
    ToolUnavailable,
    execute_tool,
    verify_frozen_release,
)
from aiot_price.integrations.chatgpt_contracts import (
    CROP_IDS,
    MARKETS,
    UNITS,
    ContractError,
    strict_json_loads,
    taipei_today,
)

ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    """FMPA_* wins; legacy TW01_* is read only while the new name is absent."""
    return os.environ.get("FMPA_" + name, os.environ.get("TW01_" + name, default))


RELEASE = Path(_env("RELEASE_DIR", str(ROOT / "models" / "releases" / "0.1.0")))
MAX_BODY_BYTES = 4096
TIMEOUT_SECONDS = 15.0
RATE_LIMIT_PER_MINUTE = 30
OBS_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

app = FastAPI(
    title="FMPA ForecastEngine internal origin",
    version="1",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fmpa_frozen_inference")
_busy = threading.Lock()
_rate_lock = threading.Lock()
_timestamps: deque[float] = deque()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _authenticated(req: Request) -> bool:
    """Constant-time comparison; missing origin secret fails closed."""
    configured = _env("ORIGIN_API_TOKEN")
    header = req.headers.get("authorization", "")
    if len(configured) < 32 or len(header) > 256:
        return False
    return hmac.compare_digest(header, "Bearer " + configured)


def _rate_ok() -> bool:
    now = time.monotonic()
    with _rate_lock:
        while _timestamps and now - _timestamps[0] >= 60:
            _timestamps.popleft()
        if len(_timestamps) >= RATE_LIMIT_PER_MINUTE:
            return False
        _timestamps.append(now)
        return True


def _ready_metadata() -> dict:
    # For health, check real frozen bytes, not an old PASS file.
    verify_frozen_release(RELEASE)
    from aiot_price.models.predict import ForecastEngine

    engine = ForecastEngine(RELEASE)
    expected = engine.manifest["source"]["json_sha256"][:12]
    return {
        "status": "ready",
        "model_version": engine.manifest["model_version"],
        "data_version": expected,
        "public_data_cutoff": str(engine.public_cutoff.date()),
        "modes": ["A"],
        "horizons_days": [7, 14],
    }


@app.get("/healthz")
async def healthz():
    if len(_env("ORIGIN_API_TOKEN")) < 32:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": {"code": "not_ready", "message": "服務尚未安全初始化。"}},
        )
    try:
        result = await asyncio.wait_for(asyncio.to_thread(_ready_metadata), timeout=TIMEOUT_SECONDS)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": {"code": "not_ready", "message": "模型或資料不可用。"}},
        )
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def _validate(tool_name: str, body: dict) -> tuple[str, str] | None:
    allowed = {"crop_id", "market_id"}
    if tool_name == "post_forecast":
        allowed |= {"current_price", "price_unit", "observed_on"}
    if set(body) - allowed:
        return "unsupported_field", "有不允許的欄位；此 API 不提供 B、保存或任意執行。"
    if any(key not in body for key in ("crop_id", "market_id")):
        return "bad_request", "缺少 crop_id 或 market_id。"
    if not isinstance(body["crop_id"], str) or body["crop_id"] not in CROP_IDS:
        return "unsupported_crop", "不支援此品項。"
    if not isinstance(body["market_id"], str) or body["market_id"] not in MARKETS:
        return "unsupported_market", "不支援此市場。"
    if tool_name == "get_market_quote":
        return None
    if any(key not in body for key in ("current_price", "price_unit")):
        return "bad_request", "缺少 current_price 或 price_unit。"
    value = body["current_price"]
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0 or value > 1_000_000:
        return "invalid_price", "價格必須是大於零且合理的有限數值。"
    if not isinstance(body["price_unit"], str) or body["price_unit"] not in UNITS:
        return "non_comparable_unit", "計價單位須為元／台斤或元／公斤；未知箱重不可比。"
    if "observed_on" in body:
        s = body["observed_on"]
        if not isinstance(s, str) or not OBS_DATE_RE.fullmatch(s):
            return "invalid_date", "觀測日期格式須為 YYYY-MM-DD。"
        try:
            d = date.fromisoformat(s)
        except (TypeError, ValueError):
            return "invalid_date", "觀測日期不是有效日曆日。"
        if d > taipei_today():
            return "invalid_date", "不得輸入未來的觀測日期。"
    return None


async def _read_json(req: Request):
    media_type = req.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        return None, _error(415, "unsupported_media_type", "Content-Type 必須是 application/json。")
    body = bytearray()
    try:
        async for chunk in req.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY_BYTES:
                return None, _error(413, "payload_too_large", "JSON 本文超過 4096 bytes。")
        parsed = strict_json_loads(bytes(body).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, ValueError, ContractError):
        return None, _error(400, "bad_request", "本文須為有效 JSON 物件，且不得有重複欄位或非 JSON 數值。")
    if not isinstance(parsed, dict):
        return None, _error(400, "bad_request", "本文須為 JSON 物件。")
    return parsed, None


async def _call_native(name: str, body: dict):
    """At most one running inference; deadline does not spawn unbounded workers.

    On timeout, the single native thread may finish later; it retains the lock
    until completion, so no second computation runs before the previous exits.
    """
    if not _busy.acquire(blocking=False):
        return _error(429, "rate_limited", "推論服務忙碌，請稍後重試。")
    try:
        future = _pool.submit(execute_tool, name, body, RELEASE)
    except Exception:
        _busy.release()
        return _error(503, "not_ready", "無法啟動預測運算。")

    def _release_busy(_):
        _busy.release()

    future.add_done_callback(_release_busy)
    try:
        result = await asyncio.wait_for(asyncio.wrap_future(future), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return _error(504, "forecast_timeout", "預測運算超時，沒有可用結果。")
    except ToolUnavailable as exc:
        reason = str(exc)
        if "凍結" in reason or "release" in reason:
            return _error(503, "not_ready", "凍結模型或資料檢驗失敗。")
        return _error(503, "stale_data_unusable", "公開資料不足或無有效行情，無法估計。")
    except ContractError:
        return _error(422, "bad_request", "不合法的工具請求參數。")
    except Exception:
        return _error(500, "internal_error", "內部運算錯誤；不提供未驗證數值。")
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


async def _dispatch(req: Request, name: str):
    if not _authenticated(req):
        return _error(401, "unauthorized", "需要有效的服務端 Bearer Token。")
    if not _rate_ok():
        return _error(429, "rate_limited", "請求過於頻繁，請稍後重試。")
    body, error = await _read_json(req)
    if error is not None:
        return error
    problem = _validate(name, body)
    if problem:
        code, message = problem
        return _error(400 if code == "bad_request" else 422, code, message)
    return await _call_native(name, body)


@app.post("/v1/market-quote")
async def market_quote(req: Request):
    return await _dispatch(req, "get_market_quote")


@app.post("/v1/forecast")
async def forecast(req: Request):
    return await _dispatch(req, "post_forecast")
