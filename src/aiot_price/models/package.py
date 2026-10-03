"""可攜模型版本封裝（T18）。

打包內容（models/releases/<version>/）：
- manifest.json（符合 contracts/model-manifest.schema.json）
- model_h7.joblib / model_h14.joblib（含前處理 pipeline）
- public_history.parquet（推論用公開市場歷史，來源同訓練資料）
- fixtures.json（固定輸入→預期輸出，跨主機 parity 用）
- predictions.csv 摘要指標
載入端（T19/T24）驗 artifact sha256 與依賴後才可標 ready。
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from aiot_price.data.load import load_taichung_long
from aiot_price.data.schema import CROP_MAPPINGS
from .select import SELECTION_RULE


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MODEL_PARAMS = {
    "rf_reg": {"n_estimators": 300, "min_samples_leaf": 5, "seed": 42},
    "hgb_reg": {"max_iter": 200, "learning_rate": 0.05, "seed": 42},
}


def package(
    version: str = "0.1.0",
    source_json: str | Path = "data/raw/taichung/retail_prices_20261003.json",
    models_dir: str | Path = "models/candidates",
    processed_parquet: str | Path = "data/processed/features_labels.parquet",
    out_root: str | Path = "models/releases",
) -> Path:
    out_dir = Path(out_root) / version
    out_dir.mkdir(parents=True, exist_ok=True)
    source_json = Path(source_json)

    # 公開歷史（推論端特徵來源）：排除 (停) 市場，與訓練前處理一致
    crop_cols = [m.source_column for m in CROP_MAPPINGS.values()]
    long_df, _ = load_taichung_long(source_json, crop_columns=crop_cols)
    long_df = long_df[~long_df["market_id"].str.contains("(停)", regex=False)]
    long_df["crop_id"] = long_df["crop_raw"].map(
        {m.source_column: cid for cid, m in CROP_MAPPINGS.items()}
    )
    hist_path = out_dir / "public_history.parquet"
    long_df[["market_id", "date", "crop_id", "price"]].to_parquet(hist_path, index=False)

    # 模型檔＋hash
    chosen = SELECTION_RULE["chosen"]
    model_entries = []
    for h, name in chosen.items():
        h_int = int(h.split("=")[1])
        src = Path(models_dir) / f"{name}_h{h_int}.joblib"
        dst = out_dir / f"model_h{h_int}.joblib"
        shutil.copyfile(src, dst)
        model_entries.append(
            {
                "name": name,
                "horizon_days": h_int,
                "file": dst.name,
                "sha256": _sha256(dst),
                "kind": "regression_of_relative_change",
                "params": MODEL_PARAMS.get(name, {}),
                "seed": 42,
            }
        )

    # 切分與訓練資訊（由準備摘要回填）
    with open("outputs/data_quality/prepare_summary.json", encoding="utf-8") as f:
        prep = json.load(f)
    with open("outputs/training/model_selection.json", encoding="utf-8") as f:
        selection = json.load(f)
    with open("outputs/evaluation/public/public_test_results.json", encoding="utf-8") as f:
        eval_results = json.load(f)

    from aiot_price.features.build import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, VISIBLE_DELAY_DAYS

    manifest = {
        "manifest_version": "1",
        "model_version": version,
        "created_at": pd.Timestamp.now(tz="Asia/Taipei").isoformat(),
        "source": {
            "dataset_id": "data.gov.tw/84539",
            "json_sha256": _sha256(source_json),
            "observation_start": prep["load"]["date_min"],
            "observation_end": prep["load"]["date_max"],
            "license": "政府資料開放授權條款第1版",
            "unit": "NTD_per_taiwan_jin（市場均價，元/台斤）",
            "zero_means": "0＝該日該品項無價格，轉缺測",
            "excluded_markets": prep["excluded_markets"]["markets"],
        },
        "labels": {
            "horizons_days": [7, 14],
            "target": "relative_change r_h = m(t+h)/m(t)-1；方向 ±5% 門檻",
            "flat_threshold": 0.05,
            "publish_delay_days": 1,
            "contract_doc": "docs/LABEL_CONTRACT.md",
        },
        "splits": {
            "train_end": "2026-05-08",
            "val_end": "2026-07-21",
            "test_end": "2026-10-02",
            "frozen_list_sha256": prep["frozen_split"]["sha256"],
            "config": {"train_frac": 0.6, "val_frac": 0.2, "purge_days": 15},
        },
        "features": {
            "numeric_columns": FEATURE_COLUMNS,
            "categorical_columns": CATEGORICAL_COLUMNS,
            "visible_delay_days": VISIBLE_DELAY_DAYS,
            "module": "aiot_price.features.build.build_features",
        },
        "models": model_entries,
        "evaluation": {
            "report_doc": "docs/PUBLIC_MODEL_EVALUATION.md",
            "results_file": "outputs/evaluation/public/public_test_results.json",
            "public_test": {
                f"h={h}": {
                    "model": eval_results["horizons"][f"h={h}"]["selected_model"],
                    "n": eval_results["horizons"][f"h={h}"]["n"],
                    "macro_f1": eval_results["horizons"][f"h={h}"]["selected"]["direction"]["macro_f1"],
                    "accuracy": eval_results["horizons"][f"h={h}"]["selected"]["direction"]["accuracy"],
                    "return_mae": eval_results["horizons"][f"h={h}"]["selected"]["return_mae"],
                }
                for h in (7, 14)
            },
        },
        "capability": {
            "modes": ["market_mean", "store_price_estimate_A", "store_price_estimate_B_experimental"],
            "validated_scope": "public_market_test（臺中市場均價方向 macro-F1 優於持平基線；點 MAE 未優於不變價基線）",
            "not_validated": [
                "同店真值 A/B 增益（缺私人到期價，T16 HOLD）",
                "上漲類召回率（驗證集 h=7 約 2.7%）",
                "跨年度/颱風/其他城市泛化",
                "機率與區間輸出（未校準）",
            ],
            "probability_output": False,
        },
        "price_sanity_jin": {
            "cabbage": [14, 85],
            "bok_choy": [20, 80],
            "sponge_gourd": [23, 72],
            "policy": "超出上下界不拒絕，回應附警示（全期1/99百分位，DATA_QUALITY_REPORT）",
        },
        "dependencies": {
            "python": platform.python_version(),
            "packages": {"scikit-learn": sklearn.__version__, "pandas": pd.__version__, "joblib": joblib.__version__},
        },
    }

    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # fixtures：固定輸入（T19 產生預期輸出後回填 expected；先建輸入殼）
    fixtures = {
        "description": "跨主機 parity：固定輸入與預期輸出；由 scripts/predict_local.py --update-fixtures 產生 expected",
        "requests": [
            {
                "request_id": "fixture-001",
                "crop_id": "cabbage",
                "market_id": "中義市場",
                "store_id": "fixture-store",
                "current_price": 32.0,
                "price_unit": "NTD_per_taiwan_jin",
                "observed_at": "2026-10-02T10:00:00+08:00",
                "previous_price": None,
                "previous_observed_at": None,
                "mode": "without_last_week",
                "specification": None,
                "promotion": None,
            },
            {
                "request_id": "fixture-002",
                "crop_id": "sponge_gourd",
                "market_id": "第五市場",
                "store_id": "fixture-store",
                "current_price": 55.0,
                "price_unit": "NTD_per_kg",
                "observed_at": "2026-10-02T10:00:00+08:00",
                "previous_price": 50.0,
                "previous_observed_at": "2026-09-26T10:00:00+08:00",
                "mode": "both",
                "specification": None,
                "promotion": None,
            },
            {
                "request_id": "fixture-003",
                "crop_id": "bok_choy",
                "market_id": "霧峰市場",
                "store_id": "fixture-store",
                "current_price": 45.0,
                "price_unit": "NTD_per_taiwan_jin",
                "observed_at": "2026-10-02T10:00:00+08:00",
                "previous_price": None,
                "previous_observed_at": None,
                "mode": "without_last_week",
                "specification": None,
                "promotion": None,
            },
        ],
        "expected": None,
    }
    with open(out_dir / "fixtures.json", "w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)

    return out_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="封裝可攜模型版本（T18）")
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    out = package(args.version)
    print("packaged:", out)
    print(json.dumps(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["evaluation"], ensure_ascii=False, indent=2))
