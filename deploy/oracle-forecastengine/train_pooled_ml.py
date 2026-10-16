"""Train and evaluate two NEW pooled-crop ML models, preserving 0.1.0.

Train+validation -> model selection using chronologically purged validation.
Final model refits on train+validation labels which matured before test start.
One untouched future calendar holdout is used exactly once for evaluation.
No existing 0.1.0 model, source file or private record is mutated.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import f1_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pooled_ml_features import (
    FEATURES, FROZEN_CROPS, HORIZONS, SEED, design_matrix,
    features_at, quotes_as_arrays, training_rows,
)

TRAIN_END = date(2026, 5, 8).toordinal()
VALIDATION_END = date(2026, 7, 21).toordinal()
VAL_START = TRAIN_END + 1
TEST_START = VALIDATION_END + 1
VISIBLE_DELAY_DAYS = 1
PUBLICATION_DELAY_DAYS = 1
TARGET_CLIP_LOG = 1.25
THRESHOLD = 0.05
MODEL_VERSION = "multi-crop-ml/1.0.0"


def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def candidate(name: str):
    if name == "ridge":
        return Pipeline([
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=50.0, random_state=SEED)),
        ])
    if name == "hgb":
        return HistGradientBoostingRegressor(
            max_iter=130, learning_rate=0.045,
            max_leaf_nodes=23, min_samples_leaf=70,
            l2_regularization=2.0, max_bins=128,
            early_stopping=False, random_state=SEED,
        )
    raise ValueError("Unsupported ML candidate")


def to_return(ylog):
    return np.expm1(np.clip(np.asarray(ylog, dtype=np.float64), -TARGET_CLIP_LOG,
                            TARGET_CLIP_LOG))


def classes(returns):
    ret = np.asarray(returns, dtype=float)
    return np.where(ret > THRESHOLD + 1e-9, "up",
                    np.where(ret < -THRESHOLD - 1e-9, "down", "flat"))


def metrics(truth_log, pred_log):
    true_r = np.expm1(truth_log)
    predicted_r = to_return(pred_log)
    labels = ["down", "flat", "up"]
    return {
        "n": int(len(truth_log)),
        "mae_relative_change": float(mean_absolute_error(true_r, predicted_r)),
        "macro_f1_direction": float(f1_score(
            classes(true_r), classes(predicted_r), labels=labels, average="macro",
            zero_division=0,
        )),
        "direction_accuracy": float(np.mean(classes(true_r) == classes(predicted_r))),
        "class_counts": dict(Counter(classes(true_r).tolist())),
        "prediction_mean_relative_change": float(np.mean(predicted_r)),
    }


def run(catalog_dir: Path, output: Path, max_iter=None):
    if output.exists():
        raise FileExistsError("Refuse to overwrite an existing new ML release")
    manifest = json.loads((catalog_dir / "manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads((catalog_dir / "catalog.json").read_text(encoding="utf-8"))
    if (
        sha(catalog_dir / "catalog.json") != manifest["catalog_sha256"]
        or sha(catalog_dir / "public_history.json.gz") != manifest["history_sha256"]
    ):
        raise RuntimeError("Public history SHA verification failed")
    if manifest["item_count"] != 61 or manifest["with_data"] != 60:
        raise RuntimeError("Data scope changed unexpectedly")
    with gzip.open(catalog_dir / "public_history.json.gz", "rt", encoding="utf-8") as stream:
        history = json.load(stream)

    started = time.monotonic()
    X_features, metadata, targets = training_rows(history)
    X = design_matrix(X_features)
    columns = list(X.columns)
    t_ord = np.asarray([meta[2] for meta in metadata], dtype=np.int32)
    crops = np.asarray([meta[0] for meta in metadata])
    markets = np.asarray([meta[1] for meta in metadata])
    print("PUBLIC_LABELED_ORIGINS", len(metadata), "MATRIX", X.shape,
          "DAYS", len(np.unique(t_ord)), flush=True)
    print("ROWS_BY_CROP_MIN", int(min(Counter(crops).values())), flush=True)
    results = {}
    fit_models = {}
    observed_training_crops = set()
    for horizon in HORIZONS:
        y = targets[horizon]
        # The 1-day assumed publication delay is applied to target visibility.
        # Training validation labels never cross into the next chronological
        # segment. Holdout test labels are exact, already mature in snapshot.
        label_ok = np.isfinite(y) & (t_ord + horizon + PUBLICATION_DELAY_DAYS <=
                                      date(2026, 10, 2).toordinal())
        train = label_ok & (t_ord <= TRAIN_END) & (
            t_ord + horizon + PUBLICATION_DELAY_DAYS < VAL_START
        )
        val = label_ok & (t_ord > TRAIN_END) & (t_ord <= VALIDATION_END) & (
            t_ord + horizon + PUBLICATION_DELAY_DAYS < TEST_START
        )
        test = label_ok & (t_ord > VALIDATION_END)
        if min(int(train.sum()), int(val.sum()), int(test.sum())) < 1000:
            raise RuntimeError("Insufficient chronological train/val/test samples")
        seen = set(crops[train].tolist())
        observed_training_crops |= seen
        if len(seen) != 57:
            raise RuntimeError(
                f"Expected 57 new crops represented in training; got {len(seen)}"
            )
        # Explicitly disallow label/target leakage across segments.
        assert int((t_ord[train] + horizon + PUBLICATION_DELAY_DAYS).max()) < VAL_START
        assert int((t_ord[val] + horizon + PUBLICATION_DELAY_DAYS).max()) < TEST_START
        Xtrain, Xval, Xtest = X.loc[train], X.loc[val], X.loc[test]
        train_y, val_y, test_y = y[train], y[val], y[test]
        candidate_scores = {}
        for name in ("ridge", "hgb"):
            t0 = time.monotonic()
            m = candidate(name)
            m.fit(Xtrain, np.clip(train_y, -TARGET_CLIP_LOG, TARGET_CLIP_LOG))
            predictions = m.predict(Xval)
            score = metrics(val_y, predictions)
            candidate_scores[name] = {**score, "fit_seconds": round(time.monotonic()-t0, 3)}
            print("VAL", horizon, name, score["n"], "MAE",
                  round(score["mae_relative_change"], 6),
                  "macroF1", round(score["macro_f1_direction"], 5),
                  flush=True)
        # Choose only between genuine learned ML estimators; never select flat
        # or momentum as "the ML model". Compare them in the unbiased report.
        chosen = min(candidate_scores, key=lambda n: (
            candidate_scores[n]["mae_relative_change"],
            -candidate_scores[n]["macro_f1_direction"],
        ))
        # Refit using all LABEL-MATURE rows from train and validation.
        trainval = train | val
        fit = candidate(chosen)
        fit.fit(X.loc[trainval], np.clip(y[trainval], -TARGET_CLIP_LOG, TARGET_CLIP_LOG))
        predictions = fit.predict(Xtest)
        true = y[test]
        baseline_momentum = Xtest[f"ret{horizon}"].to_numpy(dtype=float)
        baseline_momentum = np.where(
            np.isfinite(baseline_momentum) & (baseline_momentum > -0.99),
            baseline_momentum, 0,
        )
        baseline_momentum_log = np.log1p(np.clip(baseline_momentum, -0.95, 2.0))
        test_ml = metrics(true, predictions)
        test_flat = metrics(true, np.zeros(len(true)))
        test_momentum = metrics(true, baseline_momentum_log)
        per_crop = {}
        for c in sorted(seen):
            crop_mask = crops[test] == c
            if not crop_mask.any():
                per_crop[c] = {"n": 0, "ml_mae_relative_change": None,
                               "flat_mae_relative_change": None}
                continue
            tm = metrics(true[crop_mask], predictions[crop_mask])
            fm = metrics(true[crop_mask], np.zeros(int(crop_mask.sum())))
            per_crop[c] = {
                "n": int(crop_mask.sum()),
                "ml_mae_relative_change": tm["mae_relative_change"],
                "ml_macro_f1": tm["macro_f1_direction"],
                "flat_mae_relative_change": fm["mae_relative_change"],
                "ml_better_flat_on_mae": (
                    tm["mae_relative_change"] < fm["mae_relative_change"]
                ),
            }
        results[str(horizon)] = {
            "chosen_model": chosen, "validation_candidates": candidate_scores,
            "train_rows": int(train.sum()), "validation_rows": int(val.sum()),
            "refit_rows": int(trainval.sum()), "test_rows": int(test.sum()),
            "train_crops": len(seen),
            "test": {
                "ml": test_ml, "flat_baseline": test_flat,
                "momentum_baseline": test_momentum,
            },
            "per_crop_holdout": per_crop,
            "test_ml_better_flat_on_mae": (
                test_ml["mae_relative_change"] < test_flat["mae_relative_change"]
            ),
            "test_ml_better_momentum_on_mae": (
                test_ml["mae_relative_change"] < test_momentum["mae_relative_change"]
            ),
        }
        fit_models[horizon] = fit
        print("HOLDOUT", horizon, "ML", test_ml["mae_relative_change"],
              "FLAT", test_flat["mae_relative_change"],
              "MOMENTUM", test_momentum["mae_relative_change"],
              "ML_DIRECTION_F1", test_ml["macro_f1_direction"], flush=True)

    output.mkdir(parents=True)
    entries = []
    for horizon, model in fit_models.items():
        path = output / f"pooled_h{horizon}.joblib"
        joblib.dump(model, path, compress=3)
        entries.append({
            "horizon_days": horizon, "file": path.name,
            "sha256": sha(path), "algorithm": results[str(horizon)]["chosen_model"],
            "model_bytes": path.stat().st_size,
        })
    report = {
        "version": MODEL_VERSION,
        "method": "real_supervised_pooled_regression",
        "label": "public_market_price_relative_change_exact_calendar_t_plus_h",
        "target_transform": "log(m(t+h)/m(t)); clip targets to ±1.25 for robust training",
        "model_selection": "validation MAE; no test period used in selection",
        "n_trained_new_crops": len(observed_training_crops),
        "source_sha256": manifest["source_sha256"],
        "source_cutoff": catalog["source_observation_cutoff"],
        "chronological_split": {
            "train_end": date.fromordinal(TRAIN_END).isoformat(),
            "validation_start": date.fromordinal(VAL_START).isoformat(),
            "validation_end": date.fromordinal(VALIDATION_END).isoformat(),
            "test_start": date.fromordinal(TEST_START).isoformat(),
            "purge": "target_date + 1-day assumed publication delay < next segment start",
            "features_latest_visible": "t-1 day",
        },
        "horizons": results,
        "ml_training_seconds_total": round(time.monotonic()-started, 2),
        "evaluation_scope": "held-out chronological public market quotes, not same-store validation",
        "limitations": [
            "Models trained across 57 nonfrozen items with their original public historical price observations.",
            "Original RF/HGB frozen 0.1.0 for three crops is untouched.",
            "No same-store maturity labels, no verified individual shop forecasting accuracy.",
            "No calibrated probabilities, confidence intervals or prediction intervals.",
            "Public snapshot cutoff 2026-10-02; not a live today quote.",
        ],
    }
    (output / "evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    ml_manifest = {
        "schema_version": "1",
        "model_version": MODEL_VERSION,
        "method": report["method"],
        "source_sha256": manifest["source_sha256"],
        "source_cutoff": catalog["source_observation_cutoff"],
        "features": list(FEATURES),
        "feature_columns": columns,
        "trained_crop_ids": sorted(observed_training_crops),
        "models": entries,
        "seed": SEED, "threshold": THRESHOLD,
        "publication_delay_days": PUBLICATION_DELAY_DAYS,
        "target_clip_log": TARGET_CLIP_LOG,
        "train_end": report["chronological_split"]["train_end"],
        "validation_end": report["chronological_split"]["validation_end"],
        "test_start": report["chronological_split"]["test_start"],
        "evaluation_file": "evaluation.json",
        "evaluation_sha256": sha(output / "evaluation.json"),
        "training_dependencies": {
            "sklearn": __import__("sklearn").__version__,
            "numpy": np.__version__, "pandas": __import__("pandas").__version__,
            "joblib": joblib.__version__,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(ml_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report, ml_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report, manifest = run(args.catalog_dir, args.output)
    print("ML_TRAINED=" + str(report["n_trained_new_crops"]), flush=True)
    print("MODEL_VERSION=" + report["version"], flush=True)
    print("MODEL_MANIFEST=" + str(args.output / "manifest.json"), flush=True)
