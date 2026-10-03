"""第五輪 S04 回歸測試：事實以 (mode, horizon, target_date, field, unit) 分離。

真值：A 7天 −4.1%、30.7 元（10/11）；A 14天 −0.9%、31.7 元（10/18）；
B 7天 +0.2%、32.1 元。全部 flat。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.service import validate_qwen_answer

TOOLS = {
    "forecast": {
        "results": [
            {"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
             "relative_change_estimate": -0.041, "price_estimate": 30.7,
             "price_estimate_unit": "NTD_per_taiwan_jin"},
            {"horizon_days": 14, "target_date": "2026-10-18", "direction": "flat",
             "relative_change_estimate": -0.009, "price_estimate": 31.7,
             "price_estimate_unit": "NTD_per_taiwan_jin"},
        ],
        "results_with_last_week": [
            {"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
             "relative_change_estimate": 0.002, "price_estimate": 32.1,
             "price_estimate_unit": "NTD_per_taiwan_jin"},
        ],
        "public_data_cutoff": "2026-10-02",
        "input_observed_at": "2026-10-04T12:00:00+08:00",
        "error": None,
    }
}


class TestS04Failures:
    def test_swapped_target_dates_rejected(self):
        """7 天配 10/18、14 天配 10/11（交換目標日期）→ 拒。"""
        bad = "7 天後（2026-10-18）大致持平（-4.1%）；14 天後（2026-10-11）大致持平（-0.9%）。"
        ok, why = validate_qwen_answer(bad, TOOLS)
        assert ok is False, f"交換目標日期必須被拒：{why}"

    def test_colloquial_bull_claim_rejected(self):
        """工具持平，寫「下週會大漲」→ 拒（『下週』須辨識為 7 天期限）。"""
        ok, why = validate_qwen_answer("下週會大漲。", TOOLS)
        assert ok is False

    def test_price_as_percentage_rejected(self):
        """「B模式7天後持平（32.1%）」：把 B 的 32.1 元當百分比 → 拒（型別分離）。"""
        ok, why = validate_qwen_answer("B 模式 7 天後持平（32.1%）。", TOOLS)
        assert ok is False

    def test_b_sentence_using_a_numbers_rejected(self):
        """B 句只標 B，引用 A 的 −4.1%、30.7 元 → 拒。"""
        bad = "B 模式（使用上週價）7 天後大致持平（-4.1%，約 30.7 元）。"
        ok, why = validate_qwen_answer(bad, TOOLS)
        assert ok is False

    def test_correct_comma_joined_sentence_not_rejected(self):
        """正確兩期限用逗號連成一句 → 不得誤拒（正向案例）。"""
        good = "7 天後（2026-10-11）大致持平（-4.1%，約 30.7 元），14 天後（2026-10-18）大致持平（-0.9%，約 31.7 元）。"
        ok, why = validate_qwen_answer(good, TOOLS)
        assert ok is True, f"正確逗號連句被誤拒：{why}"

    def test_ab_comparison_sentence_allowed(self):
        """A/B 對照句同時標示兩模式 → 兩邊數字都可引用（正向案例）。"""
        good = "A 模式 7 天後 -4.1%；B 模式（實驗性）7 天後 +0.2%。未經同店驗證。"
        ok, why = validate_qwen_answer(good, TOOLS)
        assert ok is True, f"合法 A/B 對照被誤拒：{why}"

    def test_percentage_as_price_rejected(self):
        """反向型別混淆：把百分比數字當價格（約 -4.1 元）→ 拒。"""
        bad = "7 天後（2026-10-11）大致持平，約 -4.1 元。"
        ok, why = validate_qwen_answer(bad, TOOLS)
        assert ok is False

    def test_b_only_numbers_in_b_sentence_ok(self):
        ok, _ = validate_qwen_answer("B 模式 7 天後大致持平（+0.2%，約 32.1 元）。", TOOLS)
        assert ok is True
