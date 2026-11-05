"""D49 candidate: median of the existing per-market forecasts for /v1/forecast.

Imported *after* D48. Only the all_markets value for post_forecast is added;
every existing single-market /v1 route still uses its original function.
Neither the Docker image nor the frozen releases are modified.
"""
from __future__ import annotations

import asyncio
import math
from datetime import date, timedelta
from statistics import median

from fastapi.responses import JSONResponse

import forecastengine_api as api
import rolling_runtime
import v1_full_catalog as catalog
from aiot_price.agent.tools import AgentTools
from aiot_price.data.labels import classify_direction
from aiot_price.integrations import chatgpt_adapter
from aiot_price.integrations.chatgpt_contracts import (
    CROP_IDS, MARKETS, normalized_forecast_request, taipei_today,
)
from aiot_price.models.predict import ForecastEngine

app = rolling_runtime.app
ALL_MARKETS = "all_markets"
MIN_VALID_MARKETS = 3
FLAT_THRESHOLD = 0.05
REFERENCE_WARNING = (
    "全臺中參考：13 個公有市場各自預測的中位數；"
    "這種用法沒有經過評估；不是任何市場或店家的真值。"
)
FROZEN_FORECAST_LIMITS = [
    "公開市場均價不等於個別店家真值，也不是即時報價。",
    "店價 A 為現價錨定推估，尚未完成同店到期配對驗證。",
    "原三品項使用凍結 RF（7 天）與 HGB（14 天）模型；"
    "公開方向模型未勝動量基線，點估計 MAE 未勝不變價基線。",
    "第一版不支援 B、保存、讀取私人紀錄、任意程式或 URL。",
]

_previous_validate = api._validate
_previous_call_native = api._call_native


def _validate(name: str, body: dict):
    if name != "post_forecast" or body.get("market_id") != ALL_MARKETS:
        return _previous_validate(name, body)
    # Run exactly the existing validator, including date, amount, unit, crop,
    # field allow-list and future-date checks; substitute only the market.
    return _previous_validate(name, {**body, "market_id": MARKETS[0]})


async def _call_native(name: str, body: dict):
    if name != "post_forecast" or body.get("market_id") != ALL_MARKETS:
        return await _previous_call_native(name, body)
    if not api._busy.acquire(blocking=False):
        return api._error(429, "rate_limited", "推論服務忙碌，請稍後重試。")
    try:
        future = api._pool.submit(execute_all_markets, dict(body))
    except Exception:
        api._busy.release()
        return api._error(503, "not_ready", "無法啟動預測運算。")
    future.add_done_callback(lambda _: api._busy.release())
    try:
        result = await asyncio.wait_for(asyncio.wrap_future(future), timeout=api.TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return api._error(504, "forecast_timeout", "預測運算超時，沒有可用結果。")
    except catalog.CatalogNoData as exc:
        return api._error(503, exc.code, str(exc))
    except chatgpt_adapter.ToolUnavailable:
        return api._error(503, "not_ready", "凍結模型或資料檢驗失敗，沒有可用結果。")
    except Exception:
        return api._error(500, "internal_error", "內部運算錯誤；不提供未驗證數值。")
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def _valid_raw(raw: dict, cleaned: dict, req: dict, expected: dict) -> bool:
    """False means that market has no usable forecast; malformed successes fail closed."""
    if not isinstance(raw, dict):
        raise catalog.CatalogNoData("stale_data_unusable", "市場預測格式不完整。")
    if raw.get("error") is not None:
        return False
    catalog._check_forecast(raw, cleaned, req)
    if (raw.get("model_version") != expected["model_version"]
            or raw.get("data_version") != expected["data_version"]
            or raw.get("public_data_cutoff") != expected["public_data_cutoff"]):
        raise catalog.CatalogNoData("stale_data_unusable", "市場預測混用了不同模型或公開資料版本。")
    return True


def execute_all_markets(body: dict, *, today: date | None = None) -> dict:
    """Compute each supported market on ONE D48 version, then take each median.

    The frozen path verifies and copies a release once, constructs one original
    ForecastEngine/AgentTools pair, then calls its existing post_forecast 13x.
    The pooled path calls the existing HGB forecast_ml for each market.
    """
    query_date = (today or taipei_today()).isoformat()
    cleaned = {key: body[key] for key in ("crop_id", "market_id", "current_price", "price_unit")}
    cleaned["observed_on"] = body.get("observed_on") or query_date
    if cleaned["market_id"] != ALL_MARKETS:
        raise catalog.CatalogNoData("bad_request", "只能使用 all_markets 聚合預測。")
    state = rolling_runtime._current()
    if tuple(state.bundle[0]["markets"]) != tuple(MARKETS):
        raise catalog.CatalogNoData("not_ready", "公開目錄的市場清單不一致。")

    expected = {}
    candidates = []
    if cleaned["crop_id"] in CROP_IDS:
        # D48's verified_release_snapshot checks frozen SHA256 and substitutes
        # the verified rolling parquet inside this ONE private snapshot.
        with chatgpt_adapter.verified_release_snapshot(api.RELEASE) as snapshot:
            engine = ForecastEngine(snapshot)
            tools = AgentTools(engine)
            expected = {
                "model_version": engine.manifest["model_version"],
                "data_version": engine.manifest["source"]["json_sha256"][:12],
                "public_data_cutoff": str(engine.public_cutoff.date()),
            }
            for market in MARKETS:
                local = {**cleaned, "market_id": market}
                req = normalized_forecast_request(local)
                raw = tools.post_forecast(req)
                if _valid_raw(raw, local, req, expected):
                    candidates.append((market, raw))
    else:
        from pooled_ml_runtime import forecast_ml, ml_release

        manifest = ml_release()[0]  # reuses the frozen-verified pooled release
        expected = {
            "model_version": manifest["model_version"],
            "data_version": state.bundle[3]["source_sha256"][:12],
            "public_data_cutoff": state.cutoff,
        }
        for market in MARKETS:
            local = {**cleaned, "market_id": market}
            req = normalized_forecast_request(local)
            try:
                raw = forecast_ml(dict(req))
            except ValueError:  # per-market missing history/insufficient features
                continue
            if _valid_raw(raw, local, req, expected):
                candidates.append((market, raw))
    if len(candidates) < MIN_VALID_MARKETS:
        raise catalog.CatalogNoData(
            "stale_data_unusable",
            f"只有 {len(candidates)} 個市場有有效預測；至少需要 {MIN_VALID_MARKETS} 個。"
        )

    per_market = [
        {"market_id": market, "results": [
            {"horizon_days": row["horizon_days"],
             "relative_change_estimate": row["relative_change_estimate"],
             "direction": row["direction"]}
            for row in raw["results"]
        ]}
        for market, raw in candidates
    ]
    rows = []
    for i, horizon in enumerate((7, 14)):
        changes = [entry["results"][i]["relative_change_estimate"] for entry in per_market]
        mid = round(float(median(changes)), 4)
        if not math.isfinite(mid) or mid <= -1:
            raise catalog.CatalogNoData("stale_data_unusable", "市場相對變化中位數不合法。")
        rows.append({
            "horizon_days": horizon,
            "target_date": (date.fromisoformat(cleaned["observed_on"]) +
                            timedelta(days=horizon)).isoformat(),
            "direction": classify_direction(mid, FLAT_THRESHOLD),
            "relative_change_estimate": mid,
            "price_estimate": round(cleaned["current_price"] * (1 + mid), 1),
            "price_estimate_unit": cleaned["price_unit"],
            "target_scope": "store_price_estimate",
            "validation_scope": "unvalidated",
            "probability": None, "interval_low": None, "interval_high": None,
            "relative_change_min": min(changes),
            "relative_change_max": max(changes),
            "warnings": [REFERENCE_WARNING],
        })
    req = normalized_forecast_request(cleaned)
    raw = {
        "crop_id": cleaned["crop_id"], "market_id": ALL_MARKETS,
        "store_id": None, "mode_executed": "without_last_week",
        "input_observed_at": req["observed_at"],
        **expected,
        "results": rows, "results_with_last_week": [], "error": None,
        "valid_market_count": len(candidates),
        "market_predictions": per_market,
        "warnings": [
            REFERENCE_WARNING,
            f"有效市場 {len(candidates)}/13；以可用市場的 7/14 天相對變化分別取中位數。",
            "店價點估計僅由現價與中位數相乘；模型測試未勝簡單基線，未經同店到期驗證。",
        ],
    }
    catalog._check_forecast(raw, cleaned, req)
    age = (date.fromisoformat(query_date) - date.fromisoformat(expected["public_data_cutoff"])).days
    limits = [REFERENCE_WARNING, *(FROZEN_FORECAST_LIMITS if cleaned["crop_id"] in CROP_IDS
                                   else catalog.FORECAST_LIMITS)]
    structured = {
        "tool": "post_forecast", "input_echo": cleaned,
        "normalized_request": req, "query_date": query_date,
        "engine_result": raw, "price_age_days_at_query": age,
        "limits": limits,
        "fact_text": (
            f"A 模式：{cleaned['crop_id']}／全臺中參考，有效市場 {len(candidates)}/13；"
            f"店價 {cleaned['current_price']} {cleaned['price_unit']}；"
            f"觀測日 {cleaned['observed_on']}，查詢日 {query_date}。"
            + " ".join(
                f"{row['horizon_days']} 天（{row['target_date']}）"
                f"方向 {row['direction']}、中位數相對變化 {row['relative_change_estimate']}、"
                f"店價點估計 {row['price_estimate']} {row['price_estimate_unit']}、"
                f"市場範圍 {row['relative_change_min']}～{row['relative_change_max']}。"
                for row in rows
            )
            + f" 模型 {expected['model_version']}，資料版本 {expected['data_version']}，"
            f"公開截止 {expected['public_data_cutoff']}。"
            + " ".join(limits)
        ),
    }
    return structured


api._validate = _validate
api._call_native = _call_native
