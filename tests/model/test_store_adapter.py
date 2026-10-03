"""T14 店價適配測試：A/B 兩路徑、可比性檢查、誠實標示。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.models.store_adapter import (
    ALPHA_EXPERIMENTAL,
    check_b_input,
    experimental_b_return,
)


T = datetime(2026, 10, 2, 10, 0)


class TestCheckBInput:
    def test_valid_exactly_7_days(self):
        r = check_b_input(T, 32.0, 30.0, "NTD_per_taiwan_jin", datetime(2026, 9, 25, 10, 0))
        assert r.ok
        assert r.store_week_change == pytest.approx(32 / 30 - 1)
        assert r.actual_interval_days == 7

    def test_within_tolerance_5_and_9_days(self):
        for d in (5, 9):
            prev = T - __import__("datetime").timedelta(days=d)
            r = check_b_input(T, 32.0, 30.0, "NTD_per_taiwan_jin", prev)
            assert r.ok, f"間隔 {d} 天應在 7±2 內"

    def test_out_of_window_rejected(self):
        r = check_b_input(T, 32.0, 30.0, "NTD_per_taiwan_jin", datetime(2026, 9, 20, 10, 0))
        assert not r.ok
        assert "7±2" in r.reason

    def test_missing_previous_rejected(self):
        r = check_b_input(T, 32.0, None, None, None)
        assert not r.ok
        assert r.reason

    def test_non_comparable_unit_rejected(self):
        r = check_b_input(T, 32.0, 10.0, "per_bunch", datetime(2026, 9, 25, 10, 0))
        assert not r.ok
        assert "不可比" in r.reason

    def test_kg_converted_before_compare(self):
        # 上週 50 元/公斤 = 30 元/台斤；今 32 元/台斤 → 變化 32/30-1
        r = check_b_input(T, 32.0, 50.0, "NTD_per_kg", datetime(2026, 9, 25, 10, 0))
        assert r.ok
        assert r.store_week_change == pytest.approx(32 / 30 - 1)

    def test_inconsistent_spec_rejected(self):
        r = check_b_input(T, 32.0, 30.0, "NTD_per_taiwan_jin", datetime(2026, 9, 25, 10, 0), specification_consistent=False)
        assert not r.ok
        assert "規格" in r.reason


class TestExperimentalBReturn:
    def test_rule_direction(self):
        # r_A=+2%, 店價週變化+10%, 公開同期+2% → r_B = 2% + 0.3×8% = 4.4%
        r_b = experimental_b_return(0.02, 0.10, 0.02)
        assert r_b == pytest.approx(0.02 + ALPHA_EXPERIMENTAL * 0.08)

    def test_no_public_comparison_falls_back_to_a(self):
        assert experimental_b_return(0.03, 0.10, None) == pytest.approx(0.03)

    def test_alpha_is_explicit_constant(self):
        assert ALPHA_EXPERIMENTAL == 0.3  # 未經同店驗證的實驗係數，見 STORE_ADAPTATION_METHOD
