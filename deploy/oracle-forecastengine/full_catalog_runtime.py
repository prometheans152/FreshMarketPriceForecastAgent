"""Opt-in public-market catalog and untrained historical trend baseline.

The original 0.1.0 RF/HGB model is NEVER used on unseen crops. Expanded crops
use a disclosed, untrained momentum *baseline*, not a claimed trained model.
This module is only reachable via the standalone browser website; existing
MCP /v1/forecast and its 3-crop contract are deliberately untouched.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import math
import os
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from aiot_price.data.labels import classify_direction
from aiot_price.models.store_adapter import (
    ALPHA_EXPERIMENTAL,
    check_b_input,
    experimental_b_return,
)

TAIPEI = ZoneInfo("Asia/Taipei")
FROZEN_CROPS = frozenset(("cabbage", "bok_choy", "sponge_gourd"))
CUTOFF_AGE_MAX_DAYS = 45
MIN_HISTORY_OBSERVATIONS = 20
HISTORICAL_ANCHOR_TOLERANCE = 3
HORIZONS = (7, 14)
SCOPE_WARNING = (
    "此品項沒有受訓的 RF/HGB 模型，僅以公開市場最近 7／14 天歷史變化做"
    "「趨勢持續」基準推估；不是訓練好的 AI 預測，未經同店真價驗證。"
)
STORE_PRICE_WARNING = (
    "價格為現場輸入價乘以公開市場歷史變化比例的情境推估，"
    "公開均價不是個別店家的真值。"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def data_bundle():
    root = os.environ.get("TW01_EXTENDED_CATALOG_DIR", "")
    if not root:
        raise RuntimeError("Full catalog not configured")
    folder = Path(root).resolve(strict=True)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    a = folder / "catalog.json"
    b = folder / "public_history.json.gz"
    if (
        manifest.get("catalog_schema") != "1"
        or sha(a) != manifest.get("catalog_sha256")
        or sha(b) != manifest.get("history_sha256")
        or manifest.get("item_count") != 61
    ):
        raise RuntimeError("Expanded public catalog hash validation failed")
    catalog = json.loads(a.read_text(encoding="utf-8"))
    with gzip.open(b, "rt", encoding="utf-8") as file:
        history = json.load(file)
    if (
        catalog["source_sha256"] != manifest["source_sha256"]
        or catalog["source_observation_cutoff"] != manifest["source_cutoff"]
        or len(catalog["items"]) != manifest["item_count"]
        or set(history) != {entry["crop_id"] for entry in catalog["items"]}
        or sorted(manifest["frozen_original_crop_ids"]) != sorted(FROZEN_CROPS)
    ):
        raise RuntimeError("Full catalog source contract mismatch")
    index = {entry["crop_id"]: entry for entry in catalog["items"]}
    if len(index) != 61:
        raise RuntimeError("Duplicate catalog item IDs")
    for original in FROZEN_CROPS:
        if index[original]["method"] != "frozen_rf_hgb_v0.1.0":
            raise RuntimeError("Cannot redefine frozen model coverage")
    return catalog, history, index, manifest


def public_catalog():
    """Return a copy so request handlers cannot mutate cached canonical data."""
    return copy.deepcopy(data_bundle()[0])


def item_supported(item: object) -> bool:
    if not isinstance(item, str):
        return False
    try:
        return item in data_bundle()[2]
    except (OSError, RuntimeError, ValueError, KeyError):
        return item in FROZEN_CROPS


def _closest_past(points: list[tuple[date, float]], anchor: date):
    for day, price in reversed(points):
        diff = (anchor - day).days
        if 0 <= diff <= HISTORICAL_ANCHOR_TOLERANCE:
            return day, price
        if diff > HISTORICAL_ANCHOR_TOLERANCE:
            return None
    return None


def _error(
    req: dict, code: str, message: str, cutoff: date, version: str
) -> dict:
    import pandas as pd
    observed = datetime.fromisoformat(req["observed_at"]).date()
    return {
        "request_id": f"req-{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y%m%d%H%M%S%f')}",
        "client_ref": None,
        "simulated": bool(req.get("simulated")),
        "mode_executed": req["mode"],
        "model_version": "historic-trend-baseline/1.0",
        "data_version": version,
        "forecast_method": "untrained_historical_momentum",
        "input_observed_at": req["observed_at"],
        "public_data_cutoff": cutoff.isoformat(),
        "public_data_age_days": (observed - cutoff).days,
        "crop_id": req["crop_id"],
        "market_id": req["market_id"],
        "store_id": None,
        "results": [],
        "results_without_last_week": [],
        "results_with_last_week": [],
        "b_unavailable_reason": None,
        "warnings": [SCOPE_WARNING],
        "error": {"code": code, "message": message},
    }


def forecast_baseline(request: dict) -> dict:
    """Untrained baseline for NON-frozen public source fields only.

    A horizon is rejected if the 7-/14-day anchor is missing or quote
    provenance is stale. This never fabricates observations, model weights,
    probability, forecast bands, or actual shop validation.
    """
    catalog, history, index, manifest = data_bundle()
    item_id = request["crop_id"]
    if item_id in FROZEN_CROPS:
        raise ValueError("Frozen crops must use original model")
    if item_id not in index:
        raise ValueError("Unknown public market item")
    unit = request["price_unit"]
    if unit not in ("NTD_per_taiwan_jin", "NTD_per_kg"):
        raise ValueError("Noncomparable unit")
    price = float(request["current_price"])
    if not 0 < price <= 1_000_000 or not math.isfinite(price):
        raise ValueError("Invalid present price")
    observed = datetime.fromisoformat(request["observed_at"])
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("Observed time must have a timezone")
    t = observed.date()
    if t > datetime.now(TAIPEI).date():
        raise ValueError("Future date")
    cutoff = date.fromisoformat(catalog["source_observation_cutoff"])
    version = manifest["source_sha256"][:12]
    item = index[item_id]
    market = request["market_id"]
    if market not in catalog["markets"]:
        raise ValueError("Unknown market")
    if not item["has_ever_had_public_price"]:
        return _error(request, "no_public_price",
                      "此品項歷史行情全部缺測，不能提供基準推估。", cutoff, version)
    raw = history.get(item_id, {}).get(market, [])
    # Avoid using the queried day's price as a predictor; give a full calendar
    # day visibility delay and never peek past the frozen source cutoff.
    latest_visible = min(cutoff, t - timedelta(days=1))
    visible = [(date.fromisoformat(day), float(v)) for day, v in raw
               if date.fromisoformat(day) <= latest_visible]
    if len(visible) < MIN_HISTORY_OBSERVATIONS:
        return _error(request, "insufficient_history",
                      "此市場此品項的有效日價不足 20 筆，無法做歷史趨勢推估。", cutoff, version)
    last_day, last_price = visible[-1]
    age = (t - last_day).days
    if age > CUTOFF_AGE_MAX_DAYS:
        return _error(request, "stale_data_unusable",
                      "最近可見行情已超過 45 天，拒絕使用過期價格推估。", cutoff, version)

    baselines = {}
    for horizon in HORIZONS:
        anchor = last_day - timedelta(days=horizon)
        previous = _closest_past(visible, anchor)
        if previous is None:
            return _error(request, "insufficient_history",
                          f"找不到相隔 {horizon} 天（容差 3 天）的有效公開行情，不能提供完整 7／14 天推估。",
                          cutoff, version)
        previous_date, previous_mean = previous
        r = last_price / previous_mean - 1
        if not math.isfinite(r) or abs(r) > 1.5:
            return _error(request, "unstable_public_change",
                          "最近歷史變化異常大，拒絕用持續趨勢基準外推。", cutoff, version)
        baselines[horizon] = (r, previous_date, previous_mean)

    from aiot_price.models.predict import B_EXPERIMENTAL_NOTE
    from aiot_price.data.schema import to_taiwan_jin
    import pandas as pd

    global_warnings = [SCOPE_WARNING, STORE_PRICE_WARNING]
    if (t - cutoff).days > 3:
        global_warnings.append(
            f"公開資料截止 {cutoff}，查詢基準日 {t}，相差 {(t - cutoff).days} 天；"
            "推估日仍從觀察日 t 起算 7／14 個日曆日。"
        )
    a_results = []
    for horizon in HORIZONS:
        r, prior_day, prior_price = baselines[horizon]
        a_results.append({
            "horizon_days": horizon,
            "target_date": (t + timedelta(days=horizon)).isoformat(),
            "direction": classify_direction(r, 0.05),
            "relative_change_estimate": round(r, 4),
            "price_estimate": round(price * (1 + r), 1),
            "price_estimate_unit": unit,
            "target_scope": "store_price_estimate",
            "validation_scope": "unvalidated",
            "probability": None,
            "interval_low": None,
            "interval_high": None,
            "warnings": [SCOPE_WARNING, STORE_PRICE_WARNING],
            "evidence_summary": (
                f"歷史趨勢基準：{market}/{item['display_name']} 公開均價"
                f"{prior_day} 為 {prior_price} 元/臺斤，{last_day} 為 {last_price} 元/臺斤；"
                f"假設過去 {horizon} 天相對變化延續，再以輸入店價錨定；"
                "未訓練此品項模型，也沒有個店到期驗證。"
            ),
        })
    b_results, b_reason = [], None
    if request["mode"] in ("both", "with_last_week"):
        previous_price = request.get("previous_price")
        previous_obs = request.get("previous_observed_at")
        if previous_price is None or previous_obs is None:
            b_reason = "未提供完整、可比較的上週店價與日期，僅顯示 A 模式。"
        else:
            try:
                prev_obs = datetime.fromisoformat(previous_obs)
                if prev_obs.tzinfo is None or prev_obs.utcoffset() is None:
                    raise ValueError("no timezone")
                now_jin = to_taiwan_jin(price, unit)
                comparison = check_b_input(
                    observed,
                    now_jin,
                    previous_price,
                    request.get("previous_price_unit") or unit,
                    prev_obs,
                    specification_consistent=True,
                )
                if not comparison.ok:
                    b_reason = comparison.reason
                else:
                    public_week_change = baselines[7][0]
                    for a in a_results:
                        raw_b = experimental_b_return(
                            a["relative_change_estimate"],
                            comparison.store_week_change,
                            public_week_change,
                        )
                        b_results.append({
                            **a,
                            "direction": classify_direction(raw_b, 0.05),
                            "relative_change_estimate": round(raw_b, 4),
                            "price_estimate": round(price * (1 + raw_b), 1),
                            "warnings": a["warnings"] + [B_EXPERIMENTAL_NOTE],
                            "evidence_summary": (
                                f"實驗性 B（固定係數 {ALPHA_EXPERIMENTAL}）："
                                f"歷史趨勢基準 A，加上同店上週價與公開過去 7 日變化差異；"
                                "未受訓且未經真店驗證。"
                            ),
                        })
            except (TypeError, ValueError, OverflowError, ZeroDivisionError):
                b_reason = "上週價格或日期無效，僅顯示 A 模式。"
    mode = request["mode"]
    executed = "fallback_without_last_week" if mode in ("both", "with_last_week") and not b_results else mode
    if b_reason:
        global_warnings.append("B 模式不可比：" + b_reason)
    if mode == "with_last_week" and b_results:
        single_results = b_results
    else:
        single_results = a_results
    return {
        "request_id": f"req-{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y%m%d%H%M%S%f')}",
        "client_ref": None,
        "simulated": bool(request.get("simulated")),
        "mode_executed": executed,
        "model_version": "historic-trend-baseline/1.0",
        "data_version": version,
        "forecast_method": "untrained_historical_momentum",
        "input_observed_at": request["observed_at"],
        "public_data_cutoff": cutoff.isoformat(),
        "public_data_age_days": (t - cutoff).days,
        "public_last_visible_quote_date": last_day.isoformat(),
        "crop_id": item_id,
        "crop_display_name": item["display_name"],
        "market_id": market,
        "store_id": None,
        "results": single_results,
        "results_without_last_week": a_results if mode in ("both", "with_last_week") else [],
        "results_with_last_week": b_results,
        "b_unavailable_reason": b_reason,
        "warnings": global_warnings,
        "error": None,
    }
