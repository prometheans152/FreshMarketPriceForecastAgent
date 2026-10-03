"""T09 特徵流水線測試：向後看、重現、單位攔截。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.data.schema import UnitError, resolve_crop, to_taiwan_jin
from aiot_price.features.build import build_features, perturbation_check


def _long(n_days=40, start="2025-01-01", market="M1", crop="cabbage", base=30.0):
    rows = []
    base_ts = pd.Timestamp(start)
    for i in range(n_days):
        rows.append(
            {
                "market_id": market,
                "date": base_ts + pd.Timedelta(days=i),
                "crop_id": crop,
                "price": base + i * 0.2,
            }
        )
    return pd.DataFrame(rows)


class TestSchema:
    def test_alias_resolution(self):
        assert resolve_crop("高麗菜") == "cabbage"
        assert resolve_crop("甘藍（平地高麗菜）") == "cabbage"
        assert resolve_crop("青江菜") == "bok_choy"
        with pytest.raises(KeyError):
            resolve_crop("萵苣")

    def test_unit_conversion_kg_to_jin(self):
        # 每公斤 50 元 → 每台斤 50×0.6＝30 元
        assert to_taiwan_jin(50.0, "NTD_per_kg") == pytest.approx(30.0)

    def test_non_comparable_unit_rejected(self):
        with pytest.raises(UnitError):
            to_taiwan_jin(10.0, "per_piece")
        with pytest.raises(UnitError):
            to_taiwan_jin(10.0, "unknown")


class TestBuildFeatures:
    def test_future_perturbation_does_not_change_past(self):
        df = _long()
        t = pd.Timestamp("2025-01-25")
        assert perturbation_check(df, t) is True

    def test_visible_delay_hides_today(self):
        # delay=1：t 日特徵不可用 t 日當天觀測價
        df = _long(n_days=30)
        t = pd.Timestamp("2025-01-29")  # 第 29 天；最新可見應為 01-28
        feats = build_features(df, [t], delay_days=1)
        row = feats.loc[("M1", "cabbage", t)]
        assert row["price_last_age_days"] == 1  # t−1 的價
        assert row["price_last"] == pytest.approx(30.0 + 27 * 0.2)

    def test_reproducible_same_input_same_features(self):
        df = _long()
        t_dates = pd.date_range("2025-01-15", periods=5)
        a = build_features(df, t_dates)
        b = build_features(df.copy(), t_dates)
        pd.testing.assert_frame_equal(a, b)

    def test_no_history_gives_nan_price_last(self):
        df = _long(n_days=10, market="M1")
        other = df.copy()
        other["market_id"] = "M2"
        other["price"] = float("nan")  # M2 只有缺測列，無任何可見正價格
        feats = build_features(pd.concat([df, other]), [pd.Timestamp("2025-01-05")])
        assert pd.isna(feats.loc[("M2", "cabbage", pd.Timestamp("2025-01-05")), "price_last"])

    def test_backward_returns_use_only_past(self):
        df = _long(n_days=30)
        t = pd.Timestamp("2025-01-29")
        feats = build_features(df, [t], delay_days=1)
        row = feats.loc[("M1", "cabbage", t)]
        # ret_7d：可見最新價(01-28) vs 7 天前可見價(01-21)
        p28 = 30.0 + 27 * 0.2
        p21 = 30.0 + 20 * 0.2
        assert row["ret_7d"] == pytest.approx(p28 / p21 - 1)
