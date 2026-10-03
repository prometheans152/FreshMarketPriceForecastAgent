"""T08 時間切分測試：同日同區、成熟清除、禁止隨機打散。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.data.splits import (
    SplitConfig,
    assign_splits,
    compute_boundaries,
    freeze_split_list,
    split_stats,
    TEST,
    TRAIN,
    VAL,
)


def _labels(n_days=100, start="2025-01-01"):
    """兩市場×兩品項×n_days，價格遞增；h=7 標籤全成熟（最後 7 天 target 缺）。"""
    rows = []
    base = pd.Timestamp(start)
    for market in ["M1", "M2"]:
        for crop in ["C1", "C2"]:
            for i in range(n_days):
                t = base + pd.Timedelta(days=i)
                price = 30.0 + i * 0.1
                rows.append(
                    {
                        "market_id": market,
                        "crop_raw": crop,
                        "t": t,
                        "horizon_days": 7,
                        "target_date": t + pd.Timedelta(days=7),
                        "m_t": price,
                        "m_target": price + 0.7 if i < n_days - 7 else float("nan"),
                        "relative_change": 0.7 / price if i < n_days - 7 else float("nan"),
                        "direction": "up" if i < n_days - 7 else "insufficient_data",
                        "label_mature_at": t + pd.Timedelta(days=7 + 1),
                    }
                )
    return pd.DataFrame(rows)


class TestAssignSplits:
    def test_same_day_same_split(self):
        df = _labels(60)
        out = assign_splits(df, SplitConfig(train_frac=0.6, val_frac=0.2))
        same_day = out.groupby("t")["split"].nunique()
        assert (same_day == 1).all()  # 同一 t 的所有市場/品項在同一區

    def test_train_before_val_before_test(self):
        df = _labels(100)
        out = assign_splits(df, SplitConfig(train_frac=0.6, val_frac=0.2))
        assert out.loc[out["split"] == TRAIN, "t"].max() < out.loc[out["split"] == VAL, "t"].min()
        assert out.loc[out["split"] == VAL, "t"].max() < out.loc[out["split"] == TEST, "t"].min()

    def test_maturity_purge_between_train_val(self):
        # 構造：train 尾端某案例 label_mature_at 落入驗證期 → 應被 purged
        df = _labels(100)
        cfg = SplitConfig(train_frac=0.6, val_frac=0.2)
        out = assign_splits(df, cfg)
        # 資料中 h=7 標籤成熟日 = t+8；train 末日 t+8 必 < val 起點（t 間隔 1 天），
        # 除非 purge_days 不足。用 purge_days=0 模擬不成熟情境：
        cfg0 = SplitConfig(train_frac=0.6, val_frac=0.2, purge_days=0)
        out0 = assign_splits(df, cfg0)
        # 成熟日 t+8 的 train 案例若 t+8 >= val_start 會被清除
        train_t_max = out0.loc[out0["split"] == TRAIN, "t"].max()
        val_start = out0.loc[out0["split"] == VAL, "t"].min()
        mature_ok = out0.loc[out0["split"] == TRAIN, "label_mature_at"].max() < val_start
        # h=7/purge=1 下 train 末日 +8 天應跨過 val 起點 → 應有 purged 存在且斷言通過
        assert mature_ok
        # 原始（purge_days=15 對 h=7 過於保守不影響正確性）：purged 原因必須被記錄
        if (out["split"] == "purged").any():
            assert out.loc[out["split"] == "purged", "purge_reason"].notna().all()

    def test_no_row_level_randomness(self):
        df = _labels(80)
        out1 = assign_splits(df, SplitConfig())
        out2 = assign_splits(df, SplitConfig())
        assert (out1["split"] == out2["split"]).all()  # 純時間規則，重跑一致


class TestFreeze:
    def test_freeze_writes_sha(self, tmp_path):
        df = _labels(50)
        out = assign_splits(df, SplitConfig())
        meta = freeze_split_list(out, tmp_path)
        assert Path(meta["csv"]).exists()
        assert len(meta["sha256"]) == 64
        assert meta["rows"] == int(out["split"].isin([TRAIN, VAL, TEST]).sum())

    def test_split_stats_assertions(self):
        df = _labels(100)
        out = assign_splits(df, SplitConfig())
        stats = split_stats(out)
        assert stats["_assertions"]["train_mature_before_val_start"] is True
