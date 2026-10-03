"""菜價 HTTP API（T20）。

端點：
- GET  /health    就緒狀態與版本（不含秘密）
- GET  /metadata  可用品項／市場／單位／模式與支援狀態
- POST /forecast  ForecastRequest → ForecastResponse（重用 T19 推論引擎，不另造轉換）

啟動（本機）：
  PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn aiot_price.api.app:app --host 127.0.0.1 --port 8000
環境變數：AIOT_RELEASE_DIR（預設 models/releases/0.1.0）。
部署時同時 serve web/（若存在）作為手機頁面。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aiot_price.data.schema import CROP_MAPPINGS, supported_crops
from aiot_price.models.predict import KNOWN_MARKETS, ForecastEngine

RELEASE_DIR = os.environ.get("AIOT_RELEASE_DIR", "models/releases/0.1.0")

app = FastAPI(title="AIoT 菜價 7/14 天預測 API", version="0.1.0")

# ---------- 存取限制（T28；SERVER 對外開放的基本防線）----------

MAX_BODY_BYTES = 8 * 1024  # 預測請求遠小於此；超過視為濫用
RATE_LIMIT_PER_MINUTE = 30  # 每客戶端 IP 每分鐘請求數（記憶體版，單進程）
_rate_buckets: dict[str, list[float]] = {}


class BodyTooLarge(Exception):
    """實際讀取位元組超限（F06：不看 Content-Length 也不放行）。"""


async def read_limited_json(request: Request, max_bytes: int = MAX_BODY_BYTES) -> dict:
    """串流讀取 body 並在超限時立即中止（涵蓋 chunked／無 Content-Length）。"""
    buf = bytearray()
    async for chunk in request.stream():
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise BodyTooLarge()
    if not buf:
        raise ValueError("empty body")
    return json.loads(bytes(buf).decode("utf-8"))


@app.middleware("http")
async def access_limits(request: Request, call_next):
    # 請求大小：Content-Length 超限直接拒絕（快速路徑）；實際位元組在
    # read_limited_json 串流層再守一次（chunked 無標頭也攔得住）。
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "payload_too_large", "message": "請求內容過大。"}},
        )
    # 速率限制：滑動窗口 per client IP（僅記路徑與狀態，不記錄 body——隱私）
    import time as _time

    client_ip = request.client.host if request.client else "unknown"
    now = _time.time()
    window = _rate_buckets.setdefault(client_ip, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "rate_limited", "message": "查詢太頻繁，請稍後再試。"}},
        )
    window.append(now)
    response = await call_next(request)
    return response

_engine: ForecastEngine | None = None


def get_engine() -> ForecastEngine:
    global _engine
    if _engine is None:
        _engine = ForecastEngine(RELEASE_DIR)
    return _engine


@app.get("/health")
def health() -> dict:
    try:
        engine = get_engine()
        return {
            "status": "ready",
            "model_version": engine.manifest["model_version"],
            "data_version": engine.manifest["source"]["json_sha256"][:12],
            "public_data_cutoff": str(engine.public_cutoff.date()),
            "modes": engine.manifest["capability"]["modes"],
        }
    except Exception as e:  # 模型包損毀/缺檔時明確降級，不假裝就緒
        return {"status": "not_ready", "reason": str(e)[:200]}


@app.get("/metadata")
def metadata() -> dict:
    return {
        "crops": supported_crops(),
        "aliases": {cid: list(m.aliases) for cid, m in CROP_MAPPINGS.items()},
        "markets": KNOWN_MARKETS,
        "accepted_units": ["NTD_per_taiwan_jin", "NTD_per_kg"],
        "non_comparable_units": ["per_piece", "per_bunch", "per_bag", "per_pack", "unknown"],
        "modes": ["without_last_week", "with_last_week", "both"],
        "horizons_days": [7, 14],
        "capability_notes": {
            "target_scope": ["market_mean", "store_price_estimate"],
            "store_estimate_validation": "unvalidated（現價錨定推估，非同店驗證）",
            "b_mode": "experimental rule（未經同店資料訓練）",
            "probability_output": False,
        },
        "source": {
            "dataset_id": "data.gov.tw/84539",
            "license": "政府資料開放授權條款第1版",
            "unit": "NTD_per_taiwan_jin",
        },
    }


@app.post("/forecast")
async def forecast(request: Request) -> JSONResponse:
    try:
        body = await read_limited_json(request)
    except BodyTooLarge:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "payload_too_large", "message": "請求內容過大。"}},
        )
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "請求本文須為 JSON。"}},
        )
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "請求本文須為 JSON 物件。"}},
        )
    # 基本必要欄位（詳細語意驗證由引擎處理，錯誤代碼一致）
    required = ["crop_id", "market_id", "current_price", "price_unit", "observed_at"]
    missing = [k for k in required if k not in body]
    if missing:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "bad_request",
                    "message": f"缺少必要欄位：{', '.join(missing)}。",
                }
            },
        )
    engine = get_engine()
    response = engine.forecast(body)
    status = 200
    if response.get("error"):
        code = response["error"].get("code")
        status = 422 if code in ("unsupported_crop", "unsupported_market", "non_comparable_unit", "invalid_price", "invalid_date") else 400
        if code == "stale_data_unusable":
            status = 503
    return JSONResponse(status_code=status, content=response)


# ---------- 代理人端點（T26）----------

from aiot_price.agent.service import QwenBackend, RuleBackend, handle_agent_query  # noqa: E402


@app.post("/agent/query")
async def agent_query(request: Request) -> JSONResponse:
    """自然語言菜價查詢：確定性解析 → 有限工具 → 忠實回答。

    QwenBackend 需環境變數 AIOT_QWEN_BASE_URL／AIOT_QWEN_MODEL（SERVER 部署）；
    未設定時使用規則後端（與工具同源，回答只引用工具數字）。
    """
    try:
        body = await read_limited_json(request)
    except BodyTooLarge:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "payload_too_large", "message": "請求內容過大。"}},
        )
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "請求本文須為 JSON（{\"query\": \"...\"}）。"}},
        )
    query = body.get("query") if isinstance(body, dict) else None
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "請提供 1–2000 字的查詢文字。"}},
        )
    store_id = body.get("store_id")
    if store_id is not None and (not isinstance(store_id, str) or len(store_id) > 32):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "store_id 須為短字串（匿名店號）。"}},
        )
    engine = get_engine()
    qwen = QwenBackend()
    backend = qwen if qwen.available() else RuleBackend()
    # F03：同步推論（含 Qwen 網路等待）丟執行緒池，事件迴圈不被阻塞，
    # 其他請求（health/forecast）可並行服務。
    result = await run_in_threadpool(handle_agent_query, engine, query, store_id, backend)
    return JSONResponse(status_code=200, content=result)


# ---------- 預測保存流程（F08/T22：使用者自願保存／匯出／刪除） ----------

import re as _re_id

from aiot_price.api.prediction_records import (
    delete_record,
    load_records,
    save_prediction,
)

_RECORD_ID_RE = _re_id.compile(r"^[A-Za-z0-9_-]+$")


@app.post("/records")
async def save_record(request: Request) -> JSONResponse:
    """保存一次預測（使用者自願）：body={forecast_response, request}。"""
    try:
        body = await read_limited_json(request)
    except BodyTooLarge:
        return JSONResponse(status_code=413, content={"error": {"code": "payload_too_large", "message": "內容過大。"}})
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "請求本文須為 JSON。"}})
    resp_obj, req_obj = body.get("forecast_response"), body.get("request")
    if not isinstance(resp_obj, dict) or not isinstance(req_obj, dict):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "需要 forecast_response 與 request 兩個 JSON 物件。"}},
        )
    try:
        path = await run_in_threadpool(save_prediction, resp_obj, req_obj)
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": {"code": "bad_request", "message": str(e)}})
    return JSONResponse(status_code=200, content={"ok": True, "record_id": path.stem.replace("prediction_", ""), "saved_at": resp_obj.get("input_observed_at")})


@app.get("/records")
async def list_records() -> JSONResponse:
    """已保存預測的匿名摘要清單（供到期核對）。"""
    records = await run_in_threadpool(load_records)
    items = []
    for rec in records:
        resp = rec.get("response") or {}
        items.append(
            {
                "record_id": rec.get("record_id"),
                "saved_at": rec.get("saved_at"),
                "crop_id": resp.get("crop_id"),
                "market_id": resp.get("market_id"),
                "mode_executed": resp.get("mode_executed"),
                "model_version": resp.get("model_version"),
                "horizons": [
                    {k: r.get(k) for k in ("horizon_days", "target_date", "direction", "relative_change_estimate")}
                    for r in (resp.get("results") or [])
                ],
            }
        )
    return JSONResponse(status_code=200, content={"records": items})


@app.get("/records/export")
async def export_records() -> JSONResponse:
    """匯出全部已保存預測（完整內容，供手機下載保存）。"""
    records = await run_in_threadpool(load_records)
    return JSONResponse(status_code=200, content={"records": records})


@app.delete("/records/{record_id}")
async def remove_record(record_id: str) -> JSONResponse:
    if not _RECORD_ID_RE.match(record_id):
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "無效的紀錄 ID。"}})
    ok = await run_in_threadpool(delete_record, record_id)
    if not ok:
        return JSONResponse(status_code=404, content={"error": {"code": "bad_request", "message": "找不到此紀錄。"}})
    return JSONResponse(status_code=200, content={"ok": True})


# 手機頁面（T21 web/）同源服務；mount 必須在所有 API 路由之後註冊，避免攔截 API 路徑
_web_dir = Path(__file__).resolve().parents[3] / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
