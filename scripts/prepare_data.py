"""資料整備主流程：載入→排除→標籤→特徵→切分→凍結。

執行（專案根目錄）：
  PYTHONPATH=src .venv/Scripts/python.exe scripts/prepare_data.py \
      --json data/raw/taichung/retail_prices_20261003.json

產出：
  data/processed/features_labels.parquet   特徵+標籤（含 split）
  outputs/splits/split_list.csv＋meta      凍結切分清單（SHA-256）
  outputs/data_quality/prepare_summary.json 排除與計數摘要
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiot_price.data.labels import LabelConfig, build_labels, label_summary
from aiot_price.data.load import load_taichung_long
from aiot_price.data.schema import CROP_MAPPINGS
from aiot_price.data.splits import SplitConfig, assign_splits, freeze_split_list, split_stats
from aiot_price.features.build import build_features

# T06 品質決策：排除 (停) 前綴市場（停用＋沿用價密集）；低覆蓋組合由特徵不足自然處理
EXCLUDED_MARKET_PATTERN = "(停)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True)
    parser.add_argument("--flat-threshold", type=float, default=0.05)
    parser.add_argument("--publish-delay-days", type=int, default=1)
    args = parser.parse_args()

    crop_cols = [m.source_column for m in CROP_MAPPINGS.values()]
    long_df, load_report = load_taichung_long(args.json, crop_columns=crop_cols)

    n_before = len(long_df)
    excluded = long_df[long_df["market_id"].str.contains(EXCLUDED_MARKET_PATTERN, regex=False)]
    keep_mask = ~long_df["market_id"].str.contains(EXCLUDED_MARKET_PATTERN, regex=False)
    df = long_df[keep_mask].copy()
    # 標準化 crop_id
    df["crop_id"] = df["crop_raw"].map({m.source_column: cid for cid, m in CROP_MAPPINGS.items()})

    # 標籤（T07）
    labels = build_labels(df, LabelConfig(flat_threshold=args.flat_threshold, publish_delay_days=args.publish_delay_days))
    labels["crop_id"] = labels["crop_raw"].map(
        {m.source_column: cid for cid, m in CROP_MAPPINGS.items()}
    )

    # 特徵（T09）：t 集合＝標籤的 t（只有這些日期需要推論）
    t_dates = pd.DatetimeIndex(sorted(labels["t"].unique()))
    feats = build_features(df, t_dates, delay_days=args.publish_delay_days)
    feats = feats.reset_index()

    # 合併：特徵+標籤（內連接 on market/crop/t）
    merged = labels.merge(feats, on=["market_id", "crop_id", "t"], how="left")
    # 市場類別保留原名供 one-hot；crop 已是 id
    merged["market_id"] = merged["market_id"]

    # 切分（T08）
    assigned = assign_splits(merged, SplitConfig())
    stats = split_stats(assigned)

    # 產出
    out_processed = ROOT / "data" / "processed"
    out_processed.mkdir(parents=True, exist_ok=True)
    merged_path = out_processed / "features_labels.parquet"
    assigned.to_parquet(merged_path, index=False)

    out_splits = ROOT / "outputs" / "splits"
    meta = freeze_split_list(assigned, out_splits)

    summary = {
        "source_json": args.json,
        "load": load_report.to_dict(),
        "excluded_markets": {
            "pattern": EXCLUDED_MARKET_PATTERN,
            "rows_excluded": int(n_before - len(df)),
            "markets": sorted(excluded["market_id"].unique().tolist()),
            "reason": "停用市場且沿用價密集（T06 品質報告），排除規則凍結於本腳本",
        },
        "label_config": {"flat_threshold": args.flat_threshold, "publish_delay_days": args.publish_delay_days},
        "label_summary": label_summary(assigned),
        "split_stats": stats,
        "frozen_split": meta,
        "features_labels_parquet": str(merged_path),
        "rows": int(len(assigned)),
    }
    out_q = ROOT / "outputs" / "data_quality"
    out_q.mkdir(parents=True, exist_ok=True)
    with open(out_q / "prepare_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({k: summary[k] for k in ("excluded_markets", "label_summary", "split_stats", "frozen_split")}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
