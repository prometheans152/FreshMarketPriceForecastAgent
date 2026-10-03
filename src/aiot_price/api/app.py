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

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aiot_price.data.schema import CROP_MAPPINGS, supported_crops
from aiot_price.models.predict import KNOWN_MARKETS, ForecastEngine

RELEASE_DIR = os.environ.get("AIOT_RELEASE_DIR", "models/releases/0.1.0")

app = FastAPI(title="AIoT 菜價 7/14 天預測 API", version="0.1.0")

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
        body = await request.json()
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


# 手機頁面（T21 web/）同源服務；目錄不存在時跳過
_web_dir = Path(__file__).resolve().parents[3] / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
