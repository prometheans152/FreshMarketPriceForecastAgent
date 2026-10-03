"""第三輪審查修正的行為測試（F01/F06）：每個案例對應 review_reproductions.json 的重現。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.service import handle_agent_query
from aiot_price.agent.tools import parse_query
from aiot_price.models.predict import ForecastEngine

TODAY = date(2026, 10, 4)


@pytest.fixture(scope="module")
def engine():
    release = Path("models/releases/0.1.0")
    if not (release / "manifest.json").exists():
        pytest.skip("模型包未打包")
    return ForecastEngine(release)


class TestReviewF01Parser:
    """審查重現的五個解析錯誤案例（固定 today=2026-10-04）。"""

    def test_units_bound_per_clause(self):
        # F01-1：今天32元/台斤、上週50元/公斤——不得把公斤套給今天價
        pq = parse_query("高麗菜今天一斤32元，上週一公斤50元", today=TODAY)
        assert pq.current_price == 32 and pq.price_unit == "NTD_per_taiwan_jin"
        assert pq.previous_price == 50 and pq.previous_price_unit == "NTD_per_kg"

    def test_yesterday_not_silently_today(self):
        # F01-2：昨天報價以昨天為基準（t=10-03）
        pq = parse_query("高麗菜昨天一斤32元", today=TODAY)
        assert pq.observed_date == date(2026, 10, 3)
        req = pq.to_forecast_request()
        assert req["observed_at"].startswith("2026-10-03")

    def test_last_time_without_date_needs_clarification(self):
        # F01-3：「上次」無日期不得補 t-7；回 A＋提示補日期
        pq = parse_query("高麗菜今天一斤32元，上次一斤28元", today=TODAY)
        assert pq.previous_price is None
        assert pq.b_reject_reason and "上次" in pq.b_reject_reason
        req = pq.to_forecast_request()
        assert req and req["mode"] == "without_last_week"  # 不擋 A

    def test_explicit_date_honored_then_range_checked(self):
        # F01-4：明示 09-01 如實使用（引擎 7±2 檢查會拒 B 回 A，不繞過）
        pq = parse_query("高麗菜今天一斤32元，上週2026-09-01一斤28元", today=TODAY)
        assert pq.previous_date == date(2026, 9, 1)
        req = pq.to_forecast_request()
        assert req["previous_observed_at"].startswith("2026-09-01")

    def test_different_store_rejects_b(self):
        # F01-5：另一家店的上週價不可比
        pq = parse_query("高麗菜今天一斤32元，上週另一家店一斤28元", today=TODAY)
        assert pq.previous_price is None
        assert pq.b_reject_reason and "另一家店" in pq.b_reject_reason

    def test_multi_crop_mixed_units(self):
        # 多品項混合顆/斤：高麗菜一顆30 不得當作高麗菜每斤價
        pq = parse_query("高麗菜一顆30元，青江菜一斤45元", today=TODAY)
        assert pq.price_unit == "NTD_per_taiwan_jin" if pq.current_price else True
        # 唯一可比組合是青江菜45/台斤；不得回 cabbage+30/台斤
        assert not (pq.crop_id == "cabbage" and pq.current_price == 30 and pq.price_unit == "NTD_per_taiwan_jin")

    def test_spec_change_rejects_b(self):
        pq = parse_query("高麗菜今天一斤32元，上週換了規格一斤28元", today=TODAY)
        assert pq.b_reject_reason and "規格" in pq.b_reject_reason

    def test_last_week_assumption_flagged(self):
        # 「上週」無日期：假設 t-7 且標 assumed（不冒充明示日期）
        pq = parse_query("高麗菜今天一斤32元，上週一斤28元", today=TODAY)
        assert pq.previous_date == date(2026, 9, 27)
        assert pq.previous_date_assumed is True


class TestReviewF01Engine:
    """引擎端（含 7±2 檢查與受控降級）的行為。"""

    def _base_req(self, **kw):
        req = {
            "crop_id": "cabbage",
            "market_id": "中義市場",
            "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin",
            "observed_at": "2026-10-04T10:00:00+08:00",
            "mode": "both",
        }
        req.update(kw)
        return req

    def test_explicit_far_date_falls_back_to_a(self, engine):
        resp = engine.forecast(self._base_req(
            previous_price=28.0,
            previous_price_unit="NTD_per_taiwan_jin",
            previous_observed_at="2026-09-01T10:00:00+08:00",
        ))
        assert resp["mode_executed"] == "fallback_without_last_week"
        assert resp["b_unavailable_reason"]
        assert len(resp["results"]) == 2  # A 結果仍在

    def test_invalid_previous_date_no_500(self, engine):
        # F06：previous_observed_at="not-a-date" → 受控降級，不丟例外
        resp = engine.forecast(self._base_req(
            previous_price=28.0,
            previous_observed_at="not-a-date",
        ))
        assert resp.get("error") is None
        assert resp["mode_executed"] == "fallback_without_last_week"
        assert resp["b_unavailable_reason"]

    def test_missing_timezone_observed_at_rejected(self, engine):
        # F06：主報價時間缺時區 → invalid_date（受控 422 層）
        resp = engine.forecast(self._base_req(observed_at="2026-10-04T10:00:00"))
        assert resp["error"]["code"] == "invalid_date"

    def test_boolean_price_rejected(self, engine):
        resp = engine.forecast(self._base_req(current_price=True))
        assert resp["error"]["code"] == "invalid_price"

    def test_infinite_price_rejected(self, engine):
        resp = engine.forecast(self._base_req(current_price=float("inf")))
        assert resp["error"]["code"] == "invalid_price"

    def test_negative_previous_price_degrades_b(self, engine):
        resp = engine.forecast(self._base_req(
            previous_price=-5,
            previous_observed_at="2026-09-27T10:00:00+08:00",
        ))
        assert resp.get("error") is None
        assert resp["mode_executed"] == "fallback_without_last_week"

    def test_specification_mismatch_rejects_b(self, engine):
        # 規格可比性接入實際入口：明示規格不同 → B 不可比
        resp = engine.forecast(self._base_req(
            specification="有機",
            previous_specification="一般",
            previous_price=28.0,
            previous_observed_at="2026-09-27T10:00:00+08:00",
        ))
        assert resp["mode_executed"] == "fallback_without_last_week"
        assert "規格" in resp["b_unavailable_reason"]

    def test_assumed_date_warning_present(self, engine):
        resp = engine.forecast(self._base_req(
            previous_price=28.0,
            previous_observed_at="2026-09-27T10:00:00+08:00",
            previous_date_assumed=True,
        ))
        assert any("假設" in w for w in resp["warnings"])


class TestReviewF01AgentFlow:
    def test_agent_flow_far_date_shows_a_with_reason(self, engine):
        r = handle_agent_query(engine, "高麗菜今天一斤32元，上週2026-09-01一斤28元", today=TODAY)
        assert "7 天後" in r["answer"]
        assert r["parsed"]["mode"] in ("without_last_week", "both")

    def test_agent_flow_yesterday_basis(self, engine):
        r = handle_agent_query(engine, "高麗菜昨天一斤32元", today=TODAY)
        assert "2026-10-03" in r["answer"]  # 以昨天為基準如實顯示
