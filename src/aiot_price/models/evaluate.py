"""封存測試的一次性評估（T15）。

只做一次：載入 T13 選定模型＋全部基線，在凍結測試清單（outputs/splits/split_list.csv
SHA-256 校驗通過）上評估；輸出逐列預測檔供重算與錯誤分析（T17）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from aiot_price.features.build import FEATURE_COLUMNS
from .baselines import BASELINES, direction_from_return, feature_ready
from .select import SELECTION_RULE
from .train import build_design_matrix, evaluate_direction, evaluate_predictions


def verify_frozen_list(path: str | Path = "outputs/splits/split_list.csv",
                       meta_path: str | Path = "outputs/splits/split_list_meta.json") -> str:
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    if sha != meta["sha256"]:
        raise RuntimeError(f"凍結清單 hash 不符：{sha} != {meta['sha256']}")
    return sha


def run_evaluation(
    parquet_path: str | Path = "data/processed/features_labels.parquet",
    models_dir: str | Path = "models/candidates",
    out_dir: str | Path = "outputs/evaluation/public",
) -> dict:
    split_sha = verify_frozen_list()
    df = pd.read_parquet(parquet_path)
    ready = feature_ready(df)
    test = ready[ready["split"] == "test"].copy()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {"frozen_split_sha256": split_sha, "horizons": {}}
    per_row_frames = []

    for h in (7, 14):
        te = test[test["horizon_days"] == h].copy()
        chosen = SELECTION_RULE["chosen"][f"h={h}"]
        model = joblib.load(Path(models_dir) / f"{chosen}_h{h}.joblib")

        X_te = build_design_matrix(te)
        # 訓練時欄位由 parquet train 段推得；用模型內欄位對齊（Ridge pipeline / 樹模型均為數值矩陣）
        tr_cols = getattr(model, "feature_names_in_", None)
        if tr_cols is not None:
            X_te = X_te.reindex(columns=tr_cols, fill_value=0.0)
        pred_r = model.predict(X_te)
        te["pred_return"] = pred_r
        te["pred_direction"] = direction_from_return(pred_r)
        te["model"] = chosen

        h_res: dict = {"selected_model": chosen, "n": int(len(te)), "baselines": {}, "selected": evaluate_predictions(te, pred_r)}

        # 基線同列比較
        tr = ready[(ready["split"] == "train") & (ready["horizon_days"] == h)]
        for baseline_cls in BASELINES:
            b = baseline_cls()
            b.fit(tr)
            h_res["baselines"][b.name] = evaluate_predictions(te, b.predict_return(te))

        results["horizons"][f"h={h}"] = h_res
        per_row_frames.append(te)

    per_row = pd.concat(per_row_frames)
    cols = ["market_id", "crop_id", "t", "horizon_days", "target_date", "m_t", "m_target",
            "relative_change", "direction", "pred_return", "pred_direction", "model", "split"]
    per_row[cols].to_csv(out_dir / "test_predictions.csv", index=False, encoding="utf-8")

    # 分品項摘要
    by_crop = {}
    for h in (7, 14):
        g = per_row[per_row["horizon_days"] == h]
        for crop, gg in g.groupby("crop_id"):
            by_crop[f"h={h}|{crop}"] = {
                "n": int(len(gg)),
                "accuracy": float((gg["direction"] == gg["pred_direction"]).mean()),
                "macro_f1": evaluate_direction(gg["direction"].to_numpy(), gg["pred_direction"].to_numpy())["macro_f1"],
            }
    results["by_crop"] = by_crop

    with open(out_dir / "public_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="封存測試一次性評估（T15）")
    parser.add_argument("--parquet", default="data/processed/features_labels.parquet")
    args = parser.parse_args()
    res = run_evaluation(args.parquet)
    for h, r in res["horizons"].items():
        print(h, r["selected_model"], "n=", r["n"],
              "acc=", round(r["selected"]["direction"]["accuracy"], 4),
              "macroF1=", round(r["selected"]["direction"]["macro_f1"], 4),
              "MAE=", round(r["selected"]["return_mae"], 4),
              "| flat MAE=", round(r["baselines"]["flat_no_change"]["return_mae"], 4),
              "flat F1=", round(r["baselines"]["flat_no_change"]["direction"]["macro_f1"], 4))
