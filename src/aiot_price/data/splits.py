"""時間切分與防洩漏（T08）。

規則（docs/MODEL_VALIDATION_PLAN.md §6）：
- 以 t 日期為單位切分：同日所有市場/品項進入同一區（train/val/test 依時間先後）。
- 成熟清除（purge）：訓練案例 label_mature_at < 驗證起點；驗證案例 label_mature_at < 測試起點。
- 最終測試封存：凍結清單附 SHA-256；看過測試後改模型需另找新獨立測試。
- 不做隨機逐列切分；滾動統計只向後看。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SPLIT_COL = "split"
TRAIN, VAL, TEST = "train", "validation", "test"


@dataclass(frozen=True)
class SplitConfig:
    train_frac: float = 0.6
    val_frac: float = 0.2  # test_frac = 1 - train - val
    purge_days: int = 15   # 14 天最大期限 + 1 日發布延遲；與 LabelConfig 一致後可調

    def to_dict(self) -> dict:
        return {"train_frac": self.train_frac, "val_frac": self.val_frac, "purge_days": self.purge_days}


def compute_boundaries(labels: pd.DataFrame, cfg: SplitConfig) -> dict:
    """依 t 的唯一日期序列以比例算 train/val/test 邊界（日期字串）。"""
    dates = sorted(labels["t"].dropna().unique())
    n = len(dates)
    train_end = dates[int(n * cfg.train_frac) - 1]
    val_end = dates[int(n * (cfg.train_frac + cfg.val_frac)) - 1]
    return {
        "train_end": pd.Timestamp(train_end).strftime("%Y-%m-%d"),
        "val_end": pd.Timestamp(val_end).strftime("%Y-%m-%d"),
        "n_dates": n,
        "date_min": pd.Timestamp(dates[0]).strftime("%Y-%m-%d"),
        "date_max": pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"),
    }


def assign_splits(labels: pd.DataFrame, cfg: SplitConfig) -> pd.DataFrame:
    """指派 split 並執行成熟清除；被清除列保留 split='purged' 與原因。"""
    boundaries = compute_boundaries(labels, cfg)
    train_end = pd.Timestamp(boundaries["train_end"])
    val_end = pd.Timestamp(boundaries["val_end"])

    df = labels.copy()
    df["t"] = pd.to_datetime(df["t"])
    df[SPLIT_COL] = None
    df.loc[df["t"] <= train_end, SPLIT_COL] = TRAIN
    df.loc[(df["t"] > train_end) & (df["t"] <= val_end), SPLIT_COL] = VAL
    df.loc[df["t"] > val_end, SPLIT_COL] = TEST

    # 成熟清除：訓練案例成熟日須早於驗證起點（train_end+1）；驗證成熟日早於測試起點
    val_start = train_end + pd.Timedelta(days=1)
    test_start = val_end + pd.Timedelta(days=1)
    immature_train = (df[SPLIT_COL] == TRAIN) & (df["label_mature_at"] >= val_start)
    immature_val = (df[SPLIT_COL] == VAL) & (df["label_mature_at"] >= test_start)
    df["purge_reason"] = None
    df.loc[immature_train, "purge_reason"] = "train_label_not_mature_before_val"
    df.loc[immature_val, "purge_reason"] = "val_label_not_mature_before_test"
    df.loc[immature_train | immature_val, SPLIT_COL] = "purged"
    return df


def split_stats(df: pd.DataFrame) -> dict:
    out = {}
    for split_name, g in df.groupby(SPLIT_COL):
        out[split_name] = {
            "rows": int(len(g)),
            "t_min": g["t"].min().strftime("%Y-%m-%d"),
            "t_max": g["t"].max().strftime("%Y-%m-%d"),
            "n_dates": int(g["t"].nunique()),
            "n_markets": int(g["market_id"].nunique()),
            "direction_counts": {k: int(v) for k, v in g["direction"].value_counts().items()},
        }
    # 防洩漏斷言資料
    train_t_max = df.loc[df[SPLIT_COL] == TRAIN, "t"].max()
    val_t_min = df.loc[df[SPLIT_COL] == VAL, "t"].min()
    train_mature_max = df.loc[df[SPLIT_COL] == TRAIN, "label_mature_at"].max()
    val_mature_max = df.loc[df[SPLIT_COL] == VAL, "label_mature_at"].max()
    out["_assertions"] = {
        "train_t_max": str(train_t_max.date()) if pd.notna(train_t_max) else None,
        "val_t_min": str(val_t_min.date()) if pd.notna(val_t_min) else None,
        "train_mature_max": str(train_mature_max.date()) if pd.notna(train_mature_max) else None,
        "val_mature_max": str(val_mature_max.date()) if pd.notna(val_mature_max) else None,
        "train_mature_before_val_start": bool(train_mature_max < val_t_min) if pd.notna(train_mature_max) else None,
    }
    return out


def freeze_split_list(df: pd.DataFrame, out_dir: str | Path, name: str = "split_list") -> dict:
    """凍結切分清單：存 CSV＋SHA-256；最終測試以本清單為準。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = df[df[SPLIT_COL].isin([TRAIN, VAL, TEST])].sort_values(
        ["t", "market_id", "crop_raw", "horizon_days"]
    )
    csv_path = out_dir / f"{name}.csv"
    keep.to_csv(csv_path, index=False, encoding="utf-8")
    sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    meta = {
        "frozen_at": pd.Timestamp.now().isoformat(),
        "csv": str(csv_path),
        "sha256": sha,
        "rows": int(len(keep)),
        "splits": {k: int((keep[SPLIT_COL] == k).sum()) for k in (TRAIN, VAL, TEST)},
    }
    import json

    with open(out_dir / f"{name}_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="指派時間切分並凍結清單（T08）")
    parser.add_argument("--labels", required=True, help="labels parquet（T07 輸出）")
    parser.add_argument("--out-dir", default="outputs/splits")
    args = parser.parse_args()

    labels = pd.read_parquet(args.labels)
    cfg = SplitConfig()
    assigned = assign_splits(labels, cfg)
    stats = split_stats(assigned)
    meta = freeze_split_list(assigned, args.out_dir)
    print(json.dumps({"boundaries": stats, "frozen": meta}, ensure_ascii=False, indent=2, default=str))
