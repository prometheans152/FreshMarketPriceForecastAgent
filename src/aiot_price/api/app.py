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
import re
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
MANUAL_WEB = os.environ.get("AIOT_MANUAL_WEB") == "1"
RECORDS_DIR = Path(os.environ.get("AIOT_RECORDS_DIR", "private/predictions"))

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
    if MANUAL_WEB:
        # A loopback bind alone is insufficient protection from DNS rebinding
        # and browser requests originating at unrelated sites. Apply the check
        # before any GET, /records mutation, /forecast, or agent dispatch.
        # This is manual-only; legacy API/provider routes remain unchanged.
        from urllib.parse import urlsplit

        client_host = request.client.host if request.client else ""
        hostname = request.url.hostname
        if client_host == "testclient":
            # Starlette's in-process TestClient virtual transport, not a
            # network peer. A real TCP peer cannot acquire this client IP.
            allowed = hostname == "testserver"
        else:
            allowed = (
                client_host in {"127.0.0.1", "::1"}
                and hostname in {"127.0.0.1", "::1", "localhost"}
            )

        scheme, netloc = request.url.scheme, request.url.netloc
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        fetch_site = request.headers.get("sec-fetch-site")
        if fetch_site is not None and fetch_site.lower() not in {"same-origin", "none"}:
            allowed = False
        if origin is not None:
            try:
                parsed = urlsplit(origin)
                allowed = allowed and (
                    parsed.scheme == scheme and parsed.netloc == netloc
                    and not parsed.username and not parsed.password
                    and parsed.path in {"", "/"}
                    and not parsed.query and not parsed.fragment
                )
            except ValueError:
                allowed = False
        if referer is not None:
            try:
                parsed = urlsplit(referer)
                allowed = allowed and (
                    parsed.scheme == scheme and parsed.netloc == netloc
                    and not parsed.username and not parsed.password
                )
            except ValueError:
                allowed = False
        if not allowed:
            return JSONResponse(status_code=403, content={"error": {
                "code": "manual_local_origin_only",
                "message": "此手動網頁只接受同一台電腦與同源網站的請求。",
            }})
    if os.environ.get("AIOT_LOCAL_HERMES_DEMO") == "1":
        # The personal demonstration is never served to other hosts/origins.
        from urllib.parse import urlsplit

        client_host = request.client.host if request.client else ""
        host = request.url.hostname
        origin = request.headers.get("origin")
        allowed = client_host in {"127.0.0.1", "::1"} and host in {"127.0.0.1", "localhost", "::1"}
        if origin:
            try:
                parsed_origin = urlsplit(origin)
                allowed = allowed and parsed_origin.scheme == request.url.scheme and parsed_origin.netloc == request.url.netloc
            except ValueError:
                allowed = False
        if not allowed:
            return JSONResponse(status_code=403, content={"error": {
                "code": "local_demo_only", "message": "此 Hermes 試用僅供本機同一網頁操作。"
            }})
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
    if MANUAL_WEB:
        # The manual interface uses an observed price, not a hypothetical
        # future store observation. Keep this gate out of legacy/API paths.
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZoneInfo

        try:
            observed_raw = body["observed_at"]
            if not isinstance(observed_raw, str):
                raise ValueError("observed_at must be a timestamp")
            observed_date = _dt.fromisoformat(observed_raw)
            if observed_date.tzinfo is None or observed_date.utcoffset() is None:
                raise ValueError("observed_at must include a timezone")
            if observed_date.astimezone(_ZoneInfo("Asia/Taipei")).date() > _dt.now(
                _ZoneInfo("Asia/Taipei")
            ).date():
                raise ValueError("future observation")
        except (TypeError, ValueError, OverflowError):
            return JSONResponse(
                status_code=422,
                content={"error": {
                    "code": "invalid_date", "message": "請填寫有效且不在未來的觀察日期與時區。"
                }},
            )
    engine = get_engine()
    response = engine.forecast(body)
    if not response.get("error"):
        register_recent_forecast(response, body)
    status = 200
    if response.get("error"):
        code = response["error"].get("code")
        status = 422 if code in ("unsupported_crop", "unsupported_market", "non_comparable_unit", "invalid_price", "invalid_date") else 400
        if code == "stale_data_unusable":
            status = 503
    return JSONResponse(status_code=status, content=response)


# ---------- 代理人端點（T26）----------

# Manual launcher must not import any agent backend, even while registering routes.
# The legacy path retains the previous module-level symbols for existing callers/tests.
if not MANUAL_WEB:
    from aiot_price.agent.service import QwenBackend, RuleBackend, handle_agent_query  # noqa: E402


@app.get("/agent/status")
def agent_status() -> dict:
    """Configuration metadata only; no model request or connection-success claim."""
    if MANUAL_WEB:
        return {"provider": None, "model": None, "runtime": "manual", "configured": False,
                "reason": "chat_disabled", "local_demo": False}
    from aiot_price.agent.providers import resolve_active_profile

    try:
        profile, reason = resolve_active_profile()
    except Exception:
        profile, reason = None, "profile_config_unavailable"
    return {
        "provider": profile.name if profile else None,
        "model": profile.model if profile else None,
        "runtime": os.environ.get("AIOT_AGENT_FRAMEWORK", "direct"),
        "configured": profile is not None and not reason,
        "reason": reason or None,
        "local_demo": os.environ.get("AIOT_LOCAL_HERMES_DEMO") == "1",
    }


@app.post("/agent/query")
async def agent_query(request: Request) -> JSONResponse:
    """自然語言菜價查詢：確定性解析 → 有限工具 → 忠實回答。

    QwenBackend 需環境變數 AIOT_QWEN_BASE_URL／AIOT_QWEN_MODEL（SERVER 部署）；
    未設定時使用規則後端（與工具同源，回答只引用工具數字）。
    """
    if MANUAL_WEB:
        return JSONResponse(status_code=403, content={"error": {
            "code": "chat_disabled", "message": "手動表單模式已停用聊天；請直接使用菜價表單。"
        }})
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
    # 第二階段：save_record 工具的使用者確認門——僅當客戶端（介面按鈕）明確帶
    # save_confirmation={"request_id":..., "confirmed": true} 時才組裝 save_gate。
    # LLM 自行呼叫 save_record 而無此確認 → 工具回 save_requires_user_confirmation。
    sc = body.get("save_confirmation")
    save_gate = None
    if sc is not None:
        if not isinstance(sc, dict) or sc.get("confirmed") is not True or not isinstance(sc.get("request_id"), str):
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "bad_request", "message": "save_confirmation 須為 {request_id: 字串, confirmed: true}。"}},
            )
        if not re.match(r"^[A-Za-z0-9_-]+$", sc["request_id"] or ""):
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "bad_request", "message": "save_confirmation.request_id 格式無效。"}},
            )
        save_gate = {"request_id": sc["request_id"], "confirmed": True, "saver": _save_record_by_request_id}
    engine = get_engine()
    # 第四輪 D41：供應商可切換（AIOT_AGENT_PROFILE：rule|glm_zai|glm_bigmodel|qwen_local）
    from aiot_price.agent.providers import resolve_active_profile, run_agent_loop

    profile, prof_reason = resolve_active_profile()
    if profile is None or prof_reason:
        # 配置不完整（未知 profile／缺金鑰）：明確 503，不靜默降級成別的後端冒充執行
        hints = {
            "api_key_missing": "金鑰未設：請設定對應環境變數（如 AIOT_GLM_API_KEY）",
            "profile_model_missing": "model ID 未設：請在 configs/agent_model.yaml 的對應 profile 填入 model",
            "profile_base_url_missing": "base_url 未設：請檢查 configs/agent_model.yaml",
            "unknown_profile": "無此 profile：可用 rule／glm_zai／glm_bigmodel／qwen_local",
        }
        hint = next((v for k, v in hints.items() if k in prof_reason), "設定無效")
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "bad_request", "message": f"代理人後端配置不完整（{prof_reason}；{hint}）。請補齊設定或改用 AIOT_AGENT_PROFILE=rule。"}},
        )
    framework = os.environ.get("AIOT_AGENT_FRAMEWORK", "direct")  # direct | hermes
    if profile.kind == "openai_compat" and framework == "hermes":
        from aiot_price.agent.hermes_runner import run_hermes_agent

        result = await run_in_threadpool(run_hermes_agent, engine, query, profile, store_id, None, save_gate)
    elif profile.kind == "openai_compat":
        result = await run_in_threadpool(run_agent_loop, engine, query, profile, store_id, None, save_gate)
    elif profile.name == "rule":
        qwen = QwenBackend()
        backend = qwen if qwen.available() else RuleBackend()
        result = await run_in_threadpool(handle_agent_query, engine, query, store_id, backend)
    fc = result.get("forecast")
    if isinstance(fc, dict) and not fc.get("error"):
        # S05：代理人預測註冊時附「實際執行的標準化輸入＋後端中繼資料」
        register_recent_forecast(
            fc,
            {
                "query": query,
                "store_id": store_id,
                "normalized_request": result.get("parsed"),
                "provider": result.get("provider"),
                "backend_used": result.get("backend_used"),
                "runtime": result.get("runtime"),
                "framework": result.get("framework"),
            },
        )
    return JSONResponse(status_code=200, content=result)


# ---------- 伺服器預測暫存（R04：POST /records 只收 request_id，不信任客戶端結果） ----------

import time as _time

_RECENT_FORECASTS: dict = {}  # request_id -> {"response":..., "request":..., "created_at":...}


def _load_private_env(env_path: Path | None = None) -> dict:
    """S09：載入 private/.env（僅 AIOT_ 前綴鍵；既有環境變數優先；不載其他前綴）。

    回傳本函式新載入的鍵值；檔不存在回空 dict。
    """
    import re as _re

    if os.environ.get("AIOT_RUNTIME_ISOLATED") == "1":
        return {}
    path = env_path or (Path(__file__).resolve().parents[3] / "private" / ".env")
    if not path.exists():
        return {}
    loaded = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _re.match(r"^(AIOT_[A-Z0-9_]+)=(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
        if not os.environ.get(key):  # 既有環境變數優先
            os.environ[key] = val
            loaded[key] = val
    return loaded


_load_private_env()  # 服務啟動時載入一次（冪等：只補缺）
_RECENT_CAP = 500


def register_recent_forecast(response: dict, request_obj: dict | None) -> None:
    """每次 /forecast 或 /agent/query 的真實推論結果註冊（LRU 上限）。"""
    rid = response.get("request_id")
    if not rid:
        return
    if len(_RECENT_FORECASTS) >= _RECENT_CAP:
        oldest = min(_RECENT_FORECASTS.items(), key=lambda kv: kv[1]["created_at"])[0]
        _RECENT_FORECASTS.pop(oldest, None)
    _RECENT_FORECASTS[rid] = {
        "response": response,
        "request": request_obj,
        "created_at": _time.time(),
    }


def _valid_forecast_structure(resp: dict) -> bool:
    """保存前的結構驗證（R04：results=[null] 等壞結構不得入庫）。"""
    if not isinstance(resp, dict):
        return False
    results = resp.get("results")
    if not isinstance(results, list):
        return False
    for r in results:
        if not isinstance(r, dict):
            return False
    if resp.get("error") is not None and not isinstance(resp.get("error"), dict):
        return False
    return True


# ---------- 預測保存流程（F08/T22：使用者自願保存／匯出／刪除） ----------

import re as _re_id

from aiot_price.api.prediction_records import (
    delete_record,
    load_records,
    save_prediction,
)
from aiot_price.integrations.manual_records import load_manual_records

_RECORD_ID_RE = _re_id.compile(r"^[A-Za-z0-9_-]+$")


@app.post("/records")
async def save_record(request: Request) -> JSONResponse:
    """保存一次預測（使用者自願）。

    R04 契約：只接受 {"request_id": "..."}——保存內容由伺服器暫存的本伺服器推論結果
    綁定，不接受客戶端提交的任意完整結果（偽造版本/金額/simulated 一律拒）。
    暫存為記憶體 LRU（重啟後清空）：過期或未知 id 回 404「請重新查詢後再保存」。
    """
    try:
        body = await read_limited_json(request)
    except BodyTooLarge:
        return JSONResponse(status_code=413, content={"error": {"code": "payload_too_large", "message": "內容過大。"}})
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "請求本文須為 JSON。"}})
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "本文須為 JSON 物件。"}})
    if "request_id" not in body:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "bad_request", "message": "請提供 request_id 欄位（字串）；不接受客戶端提交完整預測結果。"}},
        )
    if set(body) != {"request_id"}:
        return JSONResponse(status_code=400, content={"error": {
            "code": "bad_request", "message": "僅允許 request_id，不接受保存路徑或客戶端結果。"
        }})
    rid = body.get("request_id")
    if not isinstance(rid, str) or not re.match(r"^[A-Za-z0-9_-]+$", rid or ""):
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "無效的 request_id。"}})
    result = _save_record_by_request_id(rid)
    status = {True: 200}.get(result.get("ok"), result.get("_status", 422))
    return JSONResponse(status_code=status, content={k: v for k, v in result.items() if k != "_status"})


def _save_record_by_request_id(rid: str):
    """共用保存核心（POST /records 與 Agent save_record 工具同一路徑）。

    只吃 request_id；內容取自伺服器暫存的本伺服器推論結果（R04）。
    回傳 dict：成功 {"ok": True, "record_id", "saved_at"}；失敗含 "_status" 供 HTTP 層。
    """
    entry = _RECENT_FORECASTS.get(rid)
    if entry is None:
        return {"ok": False, "error": "record_not_found", "_status": 404,
                "message": "找不到此預測（可能已過期或服務已重啟）；請重新查詢後再保存。"}
    resp_obj, req_obj = entry["response"], entry["request"]
    if not _valid_forecast_structure(resp_obj):
        return {"ok": False, "error": "invalid_forecast_structure", "_status": 422,
                "message": "預測結構無效，無法保存。"}
    if req_obj.get("simulated") or resp_obj.get("simulated"):
        resp_obj = {**resp_obj, "simulated": True}
    try:
        if MANUAL_WEB:
            # Explicitly sandbox all manual records, never use legacy defaults.
            path, saved_at = save_prediction(resp_obj, req_obj, out_dir=RECORDS_DIR)
        else:
            # Preserve existing legacy call signature (also used by previous tests).
            path, saved_at = save_prediction(resp_obj, req_obj)
    except ValueError as e:
        return {"ok": False, "error": "save_rejected", "_status": 422, "message": str(e)}
    return {"ok": True, "record_id": path.stem.replace("prediction_", ""), "saved_at": saved_at}


@app.get("/records")
async def list_records() -> JSONResponse:
    """已保存預測的匿名摘要清單（供到期核對）。"""
    loader = load_manual_records if MANUAL_WEB else load_records
    records, skipped = await run_in_threadpool(lambda: loader(out_dir=RECORDS_DIR, include_skipped_info=True))
    items = []
    for rec in records:
        resp = rec.get("response") or {}
        req_meta = rec.get("request") or {}
        items.append(
            {
                "record_id": rec.get("record_id"),
                "saved_at": rec.get("saved_at"),
                "simulated": bool(rec.get("simulated")),
                "provider": req_meta.get("provider"),
                "backend_used": req_meta.get("backend_used"),
                "runtime": req_meta.get("runtime"),
                "normalized_request": req_meta.get("normalized_request"),
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
    return JSONResponse(status_code=200, content={"records": items, "skipped_bad_records": skipped})


@app.get("/records/export")
async def export_records() -> JSONResponse:
    """匯出全部已保存預測（完整內容，供手機下載保存）。"""
    loader = load_manual_records if MANUAL_WEB else load_records
    records = await run_in_threadpool(loader, RECORDS_DIR)
    return JSONResponse(status_code=200, content={"records": records})


@app.delete("/records/{record_id}")
async def remove_record(record_id: str) -> JSONResponse:
    if not _RECORD_ID_RE.match(record_id):
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "無效的紀錄 ID。"}})
    ok = await run_in_threadpool(delete_record, record_id, RECORDS_DIR)
    if not ok:
        return JSONResponse(status_code=404, content={"error": {"code": "bad_request", "message": "找不到此紀錄。"}})
    return JSONResponse(status_code=200, content={"ok": True})


# 手機頁面（T21 web/）同源服務；mount 必須在所有 API 路由之後註冊，避免攔截 API 路徑
_web_dir = Path(__file__).resolve().parents[3] / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
