"""T07 標籤契約測試：手算例子與程式輸出必須一致。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.data.labels import LabelConfig, build_labels, classify_direction, label_summary


def _long(rows):
    """rows: (market, date_str, crop, price)"""
    return pd.DataFrame(
        [
            {
                "market_id": m,
                "date": datetime.strptime(d, "%Y-%m-%d"),
                "crop_raw": c,
                "price": (float(p) if p is not None else float("nan")),
            }
            for m, d, c, p in rows
        ]
    )


class TestClassifyDirection:
    def test_hand_e1_down(self):
        # E1: 25/27 - 1 = -0.0741 → down
        assert classify_direction(25 / 27 - 1, 0.05) == "down"

    def test_hand_e2_flat_boundary_inclusive(self):
        # E2: r = +0.05 恰在門檻 → flat（含）
        assert classify_direction(31.5 / 30 - 1, 0.05) == "flat"

    def test_hand_e3_just_above(self):
        # E3: 42.1/40 - 1 = +0.0525 → up
        assert classify_direction(42.1 / 40 - 1, 0.05) == "up"

    def test_missing_is_insufficient_not_flat(self):
        assert classify_direction(None, 0.05) == "insufficient_data"
        assert classify_direction(float("nan"), 0.05) == "insufficient_data"


class TestBuildLabels:
    def _df(self):
        # 中義市場甘藍：10-04 起連續 15 天
        rows = []
        base = datetime(2025, 10, 4)
        prices = {
            0: 27.0, 1: 28.0, 2: 28.0, 3: 29.0, 4: 30.0, 5: 30.0, 6: 31.0,
            7: 25.0, 8: 26.0, 9: 27.0, 10: 28.0, 11: 29.0, 12: 30.0, 13: 31.0,
        }
        for offset, price in prices.items():
            rows.append(("中義市場", (base + pd.Timedelta(days=offset)).strftime("%Y-%m-%d"), "甘藍", price))
        return _long(rows)

    def test_h7_hand_e1(self):
        labels = build_labels(self._df(), LabelConfig(horizons=(7,)))
        row = labels[(labels["t"] == datetime(2025, 10, 4)) & (labels["horizon_days"] == 7)].iloc[0]
        assert row["m_t"] == 27.0
        assert row["m_target"] == 25.0
        assert row["relative_change"] == pytest.approx(25 / 27 - 1)
        assert row["direction"] == "down"
        assert row["target_date"] == datetime(2025, 10, 11)

    def test_zero_target_is_insufficient(self):
        df = self._df()
        # 把 10-11 改成 0（無價）→ NaN
        df.loc[df["date"] == datetime(2025, 10, 11), "price"] = float("nan")
        labels = build_labels(df, LabelConfig(horizons=(7,)))
        row = labels[(labels["t"] == datetime(2025, 10, 4)) & (labels["horizon_days"] == 7)].iloc[0]
        assert row["direction"] == "insufficient_data"
        assert pd.isna(row["relative_change"])

    def test_target_beyond_data_is_insufficient(self):
        labels = build_labels(self._df(), LabelConfig(horizons=(14,)))
        # 最後可用 t = 10-04+13 之內；t=10-05 的 t+14=10-19 不存在
        row = labels[(labels["t"] == datetime(2025, 10, 5)) & (labels["horizon_days"] == 14)].iloc[0]
        assert row["direction"] == "insufficient_data"

    def test_label_mature_at_uses_publish_delay(self):
        labels = build_labels(self._df(), LabelConfig(horizons=(7,), publish_delay_days=1))
        row = labels[(labels["t"] == datetime(2025, 10, 4)) & (labels["horizon_days"] == 7)].iloc[0]
        assert row["label_mature_at"] == datetime(2025, 10, 12)

    def test_exact_calendar_day_no_substitution(self):
        # 刪掉 t+7 的前一天（10-10），確認配對不會拿 10-10 或 10-12 代替 10-11
        df = self._df()
        df = df[df["date"] != datetime(2025, 10, 10)]
        labels = build_labels(df, LabelConfig(horizons=(7,)))
        row = labels[(labels["t"] == datetime(2025, 10, 4)) & (labels["horizon_days"] == 7)].iloc[0]
        assert row["m_target"] == 25.0  # 仍是 10-11 的價

    def test_summary_counts(self):
        labels = build_labels(self._df(), LabelConfig(horizons=(7, 14)))
        summary = label_summary(labels)
        assert "h=7" in summary and "h=14" in summary
        total7 = summary["h=7"]["total_cases"]
        assert total7 == len(labels[labels["horizon_days"] == 7])
