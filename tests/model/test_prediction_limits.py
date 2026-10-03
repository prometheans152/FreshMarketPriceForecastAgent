"""T17 能力邊界測試：來源過期不退回起點、單位不明、超範圍價、B 不可比回 A。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.models.predict import ForecastEngine

RELEASE = Path("models/releases/0.1.0")
BASE = {
    "crop_id": "cabbage",
    "market_id": "中義市場",
    "current_price": 32.0,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-02T10:00:00+08:00",
    "mode": "without_last_week",
}


@pytest.fixture(scope="module")
def engine():
    if not (RELEASE / "manifest.json").exists():
        pytest.skip("模型包未打包")
    return ForecastEngine(RELEASE)


class TestStaleData:
    def test_stale_history_does_not_shift_origin(self, engine):
        """公開歷史截短到 09-25，查詢日仍 10-02：target_date 必須從 10-02 起算。"""
        old_history = engine.history.copy()
        try:
            engine.history = old_history[old_history["date"] <= pd.Timestamp("2026-09-25")].copy()
            resp = engine.forecast(BASE)
            assert resp["public_data_cutoff"] == "2026-09-25"
            assert resp["public_data_age_days"] == 7
            targets = {r["horizon_days"]: r["target_date"] for r in resp["results"]}
            assert targets[7] == "2026-10-09"  # 從使用者今天，不是 09-25+7
            assert targets[14] == "2026-10-16"
            assert any("7 天" in w for w in resp["warnings"])
        finally:
            engine.history = old_history

    def test_insufficient_market_keeps_error(self, engine):
        resp = engine.forecast({**BASE, "market_id": "南屯市場"})
        assert resp["error"]["code"] == "stale_data_unusable"


class TestInputEdges:
    def test_non_comparable_unit_error(self, engine):
        resp = engine.forecast({**BASE, "price_unit": "per_piece"})
        assert resp["error"]["code"] == "non_comparable_unit"

    def test_zero_price_rejected(self, engine):
        resp = engine.forecast({**BASE, "current_price": 0})
        assert resp["error"]["code"] == "invalid_price"

    def test_historical_observed_at_uses_asof_features(self, engine):
        # 歷史日期查詢（5/1，公開資料到 10/2 較新）：age 為負屬合法；
        # 特徵仍 as-of 只用 5/1 前可見資料，target 從 5/1 起算不回退。
        resp = engine.forecast({**BASE, "observed_at": "2026-05-01T10:00:00+08:00"})
        assert resp["public_data_age_days"] < 0
        targets = {r["horizon_days"]: r["target_date"] for r in resp["results"]}
        assert targets[7] == "2026-05-08"
        assert targets[14] == "2026-05-15"

    def test_out_of_sanity_range_warns_not_rejects(self, engine):
        resp = engine.forecast({**BASE, "current_price": 500.0})  # 甘藍 500 元/斤遠超 85
        assert resp["error"] is None
        assert any("偏離歷史常見範圍" in w for w in resp["warnings"])

    def test_b_fallback_keeps_a(self, engine):
        resp = engine.forecast(
            {
                **BASE,
                "mode": "with_last_week",
                "previous_price": 30.0,
                "previous_observed_at": "2026-08-01T10:00:00+08:00",
            }
        )
        assert resp["mode_executed"] == "fallback_without_last_week"
        assert len(resp["results"]) == 2
        assert resp["b_unavailable_reason"]

    def test_b_marks_experimental(self, engine):
        resp = engine.forecast(
            {
                **BASE,
                "mode": "both",
                "previous_price": 30.0,
                "previous_observed_at": "2026-09-25T10:00:00+08:00",
            }
        )
        for item in resp["results_with_last_week"]:
            assert any("實驗性" in w for w in item["warnings"])
            assert item["validation_scope"] == "unvalidated"

    def test_no_probability_output(self, engine):
        resp = engine.forecast(BASE)
        for item in resp["results"]:
            assert item["probability"] is None
            assert item["interval_low"] is None and item["interval_high"] is None
