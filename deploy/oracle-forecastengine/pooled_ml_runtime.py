"""New, independently trained pooled ML inference for 57 additional items.

Never feeds unseen items to the frozen 0.1.0 RF/HGB. The existing website
keeps its proven public quote/data-sufficiency guardrails and B comparability
rule, but 7/14 changes now come from real supervised ML estimators.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from aiot_price.data.labels import classify_direction
from aiot_price.data.schema import to_taiwan_jin
from aiot_price.models.store_adapter import ALPHA_EXPERIMENTAL
from full_catalog_runtime import (
    FROZEN_CROPS, STORE_PRICE_WARNING, _env, data_bundle, forecast_baseline,
)
from pooled_ml_features import (
    FEATURES, design_matrix, features_at, quotes_as_arrays,
)

ML_WARNING = (
    "此品項已採用以 57 種公開市場品項歷史資料訓練的 HGB 監督式 ML 模型"
    "，分別推估 7／14 天相對變化；尚無同店到期真價驗證。"
)
QUALITY_WARNING = (
    "時間序列留出測試中，新增品項 HGB 7／14 天平均相對變化 MAE "
    "均未勝過不變價基準。模型已訓練≠預測比簡單基準更準，僅供實驗參考。"
)
B_NOTE = (
    "B 為未經同店到期驗證的實驗性規則；以 ML 的 A 估計、同店上週價變化"
    f"以及公開歷史同期變化進行固定 α={ALPHA_EXPERIMENTAL} 調整，"
    "不是單獨訓練出的 B 模型。"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def ml_release():
    directory = _env("POOLED_ML_DIR")
    if not directory:
        raise RuntimeError("Pooled ML release is not configured")
    location = Path(directory).resolve(strict=True)
    manifest = json.loads((location / "manifest.json").read_text(encoding="utf-8"))
    catalog, history, idx, public_manifest = data_bundle()
    if (
        manifest.get("schema_version") != "1"
        or manifest.get("model_version") != "multi-crop-ml/1.0.0"
        or manifest.get("method") != "real_supervised_pooled_regression"
        or manifest.get("source_sha256") != public_manifest["source_sha256"]
        or manifest.get("source_cutoff") != public_manifest["source_cutoff"]
        or manifest.get("features") != list(FEATURES)
        or len(manifest.get("trained_crop_ids", [])) != 57
        or len(manifest.get("models", [])) != 2
        or {entry["horizon_days"] for entry in manifest["models"]} != {7, 14}
        or any(item in FROZEN_CROPS for item in manifest["trained_crop_ids"])
    ):
        raise RuntimeError("Pooled ML artifact not compatible with frozen public source")
    report_path = location / manifest["evaluation_file"]
    if sha(report_path) != manifest.get("evaluation_sha256"):
        raise RuntimeError("Pooled ML evaluation integrity failure")
    evaluation = json.loads(report_path.read_text(encoding="utf-8"))
    if evaluation.get("version") != manifest["model_version"]:
        raise RuntimeError("Evaluation metadata version mismatch")
    models = {}
    for info in manifest["models"]:
        p = location / info["file"]
        if p.name != info["file"] or p.suffix != ".joblib":
            raise RuntimeError("Invalid ML release model filename")
        if sha(p) != info["sha256"]:
            raise RuntimeError("Pooled ML model hash mismatch")
        models[info["horizon_days"]] = joblib.load(p)
    return manifest, evaluation, models


def check_ml_release_integrity() -> dict:
    manifest, report, models = ml_release()
    folder = Path(_env("POOLED_ML_DIR")).resolve(strict=True)
    for item in manifest["models"]:
        if sha(folder / item["file"]) != item["sha256"]:
            raise RuntimeError("Pooled ML release changed after loading")
    return {
        "model_version": manifest["model_version"],
        "models": {str(i["horizon_days"]): i["algorithm"] for i in manifest["models"]},
        "trained_crops": len(manifest["trained_crop_ids"]),
        "source_cutoff": manifest["source_cutoff"],
    }


def _stamp_result_error(result, code, message):
    result["model_version"] = "multi-crop-ml/1.0.0"
    result["forecast_method"] = "supervised_hgb_pooled"
    result["ml_training_scope"] = "57_new_public_market_crops"
    result["warnings"] = [ML_WARNING, QUALITY_WARNING, STORE_PRICE_WARNING]
    result["error"] = {"code": code, "message": message}
    result["results"] = []
    result["results_without_last_week"] = []
    result["results_with_last_week"] = []
    return result


def _rework_horizon(a, pred_r, *, current_price, crop_name, market, asof, horizon, score):
    delta = float(pred_r)
    if not math.isfinite(delta) or delta <= -1 or delta > 1.5:
        raise ValueError("Model output outside bounded physical return")
    result = dict(a)
    result.update({
        "relative_change_estimate": round(delta, 4),
        "direction": classify_direction(delta, 0.05),
        "price_estimate": round(current_price * (1 + delta), 1),
        "warnings": [ML_WARNING, QUALITY_WARNING, STORE_PRICE_WARNING],
        "evidence_summary": (
            f"以 {crop_name}／{market} 在 {asof} 前可見的官方市場日價"
            f"建立回溯特徵，由跨 57 品項訓練的 HGB(h={horizon}) 真正推論；"
            f"模型時間留出測試相對變化 MAE={score['ml']['mae_relative_change']:.4f}、"
            f"不變價基準 MAE={score['flat_baseline']['mae_relative_change']:.4f}。"
            "店價是輸入店價錨定推估，非同店真實驗證。"
        ),
    })
    return result


def forecast_ml(request: dict) -> dict:
    """Retain native guardrails, replace *only* the new-crop A/B method with ML."""
    if request["crop_id"] in FROZEN_CROPS:
        raise ValueError("Original three crops must not use pooled ML")
    manifest, evaluation, models = ml_release()
    item_id = request["crop_id"]
    if item_id not in manifest["trained_crop_ids"]:
        catalog, _, index, _ = data_bundle()
        if item_id in index and not index[item_id]["has_ever_had_public_price"]:
            response = forecast_baseline(request)
            return _stamp_result_error(
                response, "no_public_price",
                "官方公開歷史全部缺測，無法訓練此品項，也不得產生假的 ML 估計。",
            )
        raise ValueError("Unknown or untrained item")
    # Reuses existing quote/date sufficiency and 7/14 pairing behavior.
    # Do not replace this by a fabricated universal model for no-data crops.
    base = forecast_baseline(request)
    base["model_version"] = manifest["model_version"]
    base["forecast_method"] = "supervised_hgb_pooled"
    base["ml_training_scope"] = "57_new_public_market_crops"
    if base["error"] is not None:
        base["warnings"] = [ML_WARNING, QUALITY_WARNING, STORE_PRICE_WARNING]
        base["error"]["message"] = base["error"]["message"].replace(
            "歷史趨勢推估", "ML 估計"
        ).replace("基準推估", "ML 估計")
        return base

    catalog, history, index, _ = data_bundle()
    records = history.get(item_id, {}).get(request["market_id"], [])
    days, prices = quotes_as_arrays(records)
    t = date.fromisoformat(request["observed_at"][:10])
    t_ordinal = t.toordinal()
    X = features_at(
        days, prices, np.asarray([t_ordinal], dtype=np.int32),
        crop_id=item_id, market_id=request["market_id"],
    )
    ml_features = design_matrix(X, manifest["feature_columns"])
    asof = base["public_last_visible_quote_date"]
    originals = base["results_without_last_week"] or base["results"]
    public_old_week = originals[0]["relative_change_estimate"]
    predictions = {}
    for horizon in (7, 14):
        score = evaluation["horizons"][str(horizon)]["test"]
        pred_log = float(models[horizon].predict(ml_features)[0])
        pred_log = float(np.clip(pred_log, -manifest["target_clip_log"],
                                 manifest["target_clip_log"]))
        delta = math.expm1(pred_log)
        if not math.isfinite(delta) or delta <= -1 or delta > 1.5:
            return _stamp_result_error(
                base, "unstable_model_output", "ML 模型輸出異常，拒絕提供估計。"
            )
        old = next(r for r in originals if r["horizon_days"] == horizon)
        # Inference must use the user's original positive price as the anchor,
        # not a rounded old baseline estimate.
        newer = _rework_horizon(
            old, delta, current_price=request["current_price"],
            crop_name=index[item_id]["display_name"],
            market=request["market_id"], asof=asof,
            horizon=horizon, score=score,
        )
        predictions[horizon] = newer

    a_results = [predictions[7], predictions[14]]
    previous_b = base["results_with_last_week"]
    b_results = []
    if previous_b:
        try:
            current_jin = to_taiwan_jin(
                request["current_price"], request["price_unit"]
            )
            previous_jin = to_taiwan_jin(
                request["previous_price"], request["previous_price_unit"]
            )
            week_change = current_jin / previous_jin - 1
            # Same fixed alpha formula as old native and public-data baseline
            # adapters, but its base A is now a TRAINED ML inference.
            for row in a_results:
                raw_b = row["relative_change_estimate"] + ALPHA_EXPERIMENTAL * (
                    week_change - public_old_week
                )
                if not math.isfinite(raw_b) or raw_b <= -1 or raw_b > 1.5:
                    raise ValueError("B experimental result out of range")
                b_results.append({
                    **row,
                    "relative_change_estimate": round(raw_b, 4),
                    "direction": classify_direction(raw_b, 0.05),
                    "price_estimate": round(request["current_price"] * (1 + raw_b), 1),
                    "warnings": row["warnings"] + [B_NOTE],
                    "evidence_summary": (
                        row["evidence_summary"] +
                        f" B：使用相同凍結 α={ALPHA_EXPERIMENTAL} 的"
                        "同店上週變化對比公開一週變化實驗規則，非 B 重新訓練模型。"
                    ),
                })
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            b_results = []
            base["b_unavailable_reason"] = "上週價格或實驗調整不合法，已退回 ML A 結果。"

    if request["mode"] == "both":
        base["results"] = a_results
        base["results_without_last_week"] = a_results
        base["results_with_last_week"] = b_results
    else:
        base["results"] = a_results
        base["results_without_last_week"] = []
        base["results_with_last_week"] = []
    if request["mode"] == "both" and not b_results:
        base["mode_executed"] = "fallback_without_last_week"

    original_other_warnings = [
        warning for warning in base["warnings"]
        if ("資料截止" in warning or "B 模式不可比" in warning)
        and "未訓練" not in warning
    ]
    base["warnings"] = [
        ML_WARNING, QUALITY_WARNING, STORE_PRICE_WARNING,
        *original_other_warnings,
    ]
    base["ml_holdout_evaluation"] = {
        str(h): {
            "ml_mae_relative_change":
                evaluation["horizons"][str(h)]["test"]["ml"]["mae_relative_change"],
            "flat_mae_relative_change":
                evaluation["horizons"][str(h)]["test"]["flat_baseline"]["mae_relative_change"],
            "direction_macro_f1":
                evaluation["horizons"][str(h)]["test"]["ml"]["macro_f1_direction"],
        }
        for h in (7, 14)
    }
    return base
