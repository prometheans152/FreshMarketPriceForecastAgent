"""7／14 天標籤建立（T07）。

契約（docs/LABEL_CONTRACT.md）：
- 起點 t＝使用者今天（臺灣日曆日）；目標日＝t＋h 日曆日（h∈{7,14}），精確日期配對。
- 標籤 r_h = m(t+h)/m(t) − 1（同市場同品項，兩端皆正價格）。
- 方向：|r_h| ≤ flat_threshold → flat；r_h > 門檻 → up；r_h < −門檻 → down。
- 目標日無正價格 → direction＝insufficient_data（缺標籤不是「未漲」）。
- 標籤成熟：label_mature_at＝目標日＋publish_delay_days（發布延遲假設，實測前保守取值）。
- 公開市場標籤與同店實價標籤分開建立；本模組只做公開市場標籤。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class LabelConfig:
    horizons: tuple = (7, 14)
    flat_threshold: float = 0.05  # 與 configs/project.yaml flat_threshold_relative 一致
    publish_delay_days: int = 1   # 發布延遲假設：觀測日+1 可取得；實測後更新並記錄

    def to_dict(self) -> dict:
        return {
            "horizons": list(self.horizons),
            "flat_threshold": self.flat_threshold,
            "publish_delay_days": self.publish_delay_days,
        }


def classify_direction(r: float | None, threshold: float) -> str:
    # 浮點容差：31.5/30-1 = 0.05000000000000004 須視為持平（契約含邊界）
    eps = 1e-9
    if r is None or pd.isna(r):
        return INSUFFICIENT
    if r > threshold + eps:
        return "up"
    if r < -threshold - eps:
        return "down"
    return "flat"


def build_labels(long_df: pd.DataFrame, config: LabelConfig | None = None) -> pd.DataFrame:
    """由長表建立逐 (market, crop, t, h) 標籤表。

    輸入長表欄位：market_id, date, crop_raw, price（正價格或 NaN）。
    輸出欄位：market_id, crop_raw, t, horizon_days, target_date, m_t, m_target,
    relative_change, direction, label_mature_at。
    只有 m_t 為正價格的列成為候選案例；m_target 缺 → direction=insufficient_data。
    """
    cfg = config or LabelConfig()
    df = long_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot_table(
        index=["market_id", "crop_raw", "date"], values="price", aggfunc="first"
    ).reset_index()

    origin = wide.dropna(subset=["price"])[["market_id", "crop_raw", "date", "price"]]
    origin = origin.rename(columns={"date": "t", "price": "m_t"})

    frames = []
    for h in cfg.horizons:
        target = wide[["market_id", "crop_raw", "date", "price"]].rename(
            columns={"date": "target_date", "price": f"m_target"}
        )
        target["t"] = target["target_date"] - pd.Timedelta(days=h)
        merged = origin.merge(
            target, on=["market_id", "crop_raw", "t"], how="left"
        )
        merged["horizon_days"] = h
        merged["relative_change"] = merged["m_target"] / merged["m_t"] - 1
        frames.append(merged)

    labels = pd.concat(frames, ignore_index=True)
    labels["direction"] = labels["relative_change"].apply(
        lambda r: classify_direction(r, cfg.flat_threshold)
    )
    labels["label_mature_at"] = labels["target_date"] + pd.Timedelta(
        days=cfg.publish_delay_days
    )
    # m_target NaN 的列 relative_change 設 NaN，避免誤導
    labels.loc[labels["m_target"].isna(), "relative_change"] = float("nan")
    return labels[
        [
            "market_id",
            "crop_raw",
            "t",
            "horizon_days",
            "target_date",
            "m_t",
            "m_target",
            "relative_change",
            "direction",
            "label_mature_at",
        ]
    ]


def label_summary(labels: pd.DataFrame) -> dict:
    """標籤分佈摘要：方向計數、不足資料率、品項/市場數。"""
    out = {}
    for (h,), g in labels.groupby(["horizon_days"]):
        counts = g["direction"].value_counts().to_dict()
        total = len(g)
        out[f"h={h}"] = {
            "total_cases": int(total),
            "direction_counts": {k: int(v) for k, v in counts.items()},
            "insufficient_ratio": round(counts.get(INSUFFICIENT, 0) / total, 4) if total else None,
            "n_markets": int(g["market_id"].nunique()),
            "n_crops": int(g["crop_raw"].nunique()),
        }
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="建立 7/14 天公開市場標籤（T07）")
    parser.add_argument("--json", required=True)
    parser.add_argument("--out", default="outputs/labels/labels.parquet")
    parser.add_argument("--crops", nargs="*", default=None)
    args = parser.parse_args()

    from .load import load_taichung_long

    long_df, _ = load_taichung_long(args.json, crop_columns=args.crops)
    labels = build_labels(long_df)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(out_path, index=False)
    print(json.dumps(label_summary(labels), ensure_ascii=False, indent=2))
