"""公開市場模型訓練（T12）與評估指標（T15 共用）。

候選（與資料量相稱的輕量模型，全部 CPU 可訓）：
- 回歸（預測相對變化 r_h）：Ridge、HistGradientBoostingRegressor
- 方向分類（up/flat/down）：DummyMajority、HistGradientBoostingClassifier
7／14 天分開訓練；種子、版本與資料 hash 固定記錄。
方向由回歸輸出 r 經同一 ±5% 門檻導出；分類另訓比較。
特徵不含 market_id（未見市場須可推論）；crop_id one-hot。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import classification_report, confusion_matrix, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from aiot_price.features.build import FEATURE_COLUMNS
from .baselines import BASELINES, FLAT_THRESHOLD, direction_from_return, feature_ready

SEED = 42
NUMERIC_FEATURES = FEATURE_COLUMNS  # 全數值
CATEGORICAL_FEATURES = ["crop_id"]


def build_design_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """特徵矩陣：數值特徵 + crop_id one-hot。推論共用同一轉換。"""
    return pd.get_dummies(df[NUMERIC_FEATURES + CATEGORICAL_FEATURES], columns=CATEGORICAL_FEATURES, dtype=float)


def make_preprocessor() -> Pipeline:
    # 設計矩陣已由 build_design_matrix 統一展開為數值欄（crop one-hot），
    # Ridge 僅需標準化；hgb/rf 樹模型直接吃數值矩陣，不需要縮放。
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])


def regression_candidates() -> dict:
    return {
        "ridge": Pipeline(
            [
                ("prep", make_preprocessor()),
                ("model", Ridge(alpha=1.0, random_state=SEED)),
            ]
        ),
        "hgb_reg": HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_depth=None, random_state=SEED
        ),
        "rf_reg": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=5, random_state=SEED, n_jobs=-1
        ),
    }


def classification_candidates() -> dict:
    return {
        "dummy_majority": DummyClassifier(strategy="most_frequent"),
        "hgb_clf": HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, random_state=SEED
        ),
    }


def evaluate_direction(y_true: pd.Series, y_pred: np.ndarray, labels=None) -> dict:
    labels = labels or ["down", "flat", "up"]
    present = [l for l in labels if l in set(y_true) | set(y_pred)]
    report = classification_report(y_true, y_pred, labels=present, output_dict=True, zero_division=0)
    return {
        "accuracy": float((y_true == y_pred).mean()),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "per_class": {k: v for k, v in report.items() if k in present},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=present).tolist(),
        "confusion_labels": present,
    }


def evaluate_predictions(
    df_eval: pd.DataFrame, pred_return: np.ndarray, threshold: float = FLAT_THRESHOLD
) -> dict:
    """回歸路線統一評估：r 的 MAE／偏差＋導出方向指標。"""
    y_true_r = df_eval["relative_change"].to_numpy()
    y_true_d = df_eval["direction"].to_numpy()
    y_pred_d = direction_from_return(pred_return, threshold)
    return {
        "n": int(len(df_eval)),
        "return_mae": float(mean_absolute_error(y_true_r, pred_return)),
        "return_bias": float(np.mean(pred_return - y_true_r)),
        "direction": evaluate_direction(y_true_d, y_pred_d),
    }


def run_training(
    parquet_path: str | Path,
    out_dir: str | Path = "outputs/training",
    models_dir: str | Path = "models/candidates",
    seed: int = SEED,
) -> dict:
    """訓練全部候選（7/14 分開），在驗證集出指標；最終測試另由 evaluate.py 一次性套用。"""
    import joblib

    df = pd.read_parquet(parquet_path)
    ready = feature_ready(df)
    train = ready[ready["split"] == "train"]
    val = ready[ready["split"] == "validation"]

    out_dir, models_dir = Path(out_dir), Path(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {"seed": seed, "threshold": FLAT_THRESHOLD, "horizons": {}}

    for h in (7, 14):
        tr, va = train[train["horizon_days"] == h], val[val["horizon_days"] == h]
        X_tr = build_design_matrix(tr)
        X_va = build_design_matrix(va).reindex(columns=X_tr.columns, fill_value=0.0)
        y_tr_r = tr["relative_change"].to_numpy()
        y_tr_c = tr["direction"].to_numpy()

        h_res: dict = {"train_n": int(len(tr)), "val_n": int(len(va)), "baselines": {}, "regression": {}, "classification": {}}

        # 基線（相同驗證列）
        for baseline_cls in BASELINES:
            b = baseline_cls()
            b.fit(tr)
            pred_r = b.predict_return(va)
            h_res["baselines"][b.name] = evaluate_predictions(va, pred_r)

        # 回歸候選
        for name, model in regression_candidates().items():
            t0 = time.time()
            model.fit(X_tr, y_tr_r)
            fit_s = round(time.time() - t0, 2)
            pred_r = model.predict(X_va)
            h_res["regression"][name] = {**evaluate_predictions(va, pred_r), "fit_seconds": fit_s}
            joblib.dump(model, models_dir / f"{name}_h{h}.joblib", compress=3)

        # 分類候選（直接預測方向）
        for name, model in classification_candidates().items():
            model.fit(X_tr, y_tr_c)
            pred_c = model.predict(X_va)
            h_res["classification"][name] = {
                "n": int(len(va)),
                **evaluate_direction(va["direction"].to_numpy(), pred_c),
            }
            joblib.dump(model, models_dir / f"{name}_h{h}.joblib", compress=3)

        results["horizons"][f"h={h}"] = h_res

    with open(out_dir / "training_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="訓練公開市場候選模型（T12）")
    parser.add_argument("--parquet", default="data/processed/features_labels.parquet")
    parser.add_argument("--out-dir", default="outputs/training")
    parser.add_argument("--models-dir", default="models/candidates")
    args = parser.parse_args()
    res = run_training(args.parquet, args.out_dir, args.models_dir)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:4000])
