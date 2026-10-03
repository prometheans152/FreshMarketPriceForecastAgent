"""T26 代理人工具測試：解析確定性、工具行為、呼叫限制。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.tools import (
    AgentTools,
    ToolCallLimiter,
    parse_query,
)

TODAY = date(2026, 10, 2)


class TestParseQuery:
    def test_basic_price_with_jin_unit(self):
        pq = parse_query("高麗菜今天一斤32元", today=TODAY)
        assert pq.crop_id == "cabbage"
        assert pq.current_price == 32
        assert pq.price_unit == "NTD_per_taiwan_jin"

    def test_kg_unit(self):
        pq = parse_query("絲瓜一公斤80元", today=TODAY)
        assert pq.crop_id == "sponge_gourd"
        assert pq.price_unit == "NTD_per_kg"
        assert pq.current_price == 80

    def test_alias_bok_choy(self):
        pq = parse_query("青江菜一台斤45", today=TODAY)
        assert pq.crop_id == "bok_choy"

    def test_market_extraction(self):
        pq = parse_query("霧峰市場的高麗菜一斤30元", today=TODAY)
        assert pq.market_id == "霧峰市場"

    def test_previous_week_price(self):
        pq = parse_query("高麗菜一斤32，上週是28元", today=TODAY)
        assert pq.current_price == 32
        assert pq.previous_price == 28
        req = pq.to_forecast_request()
        assert req["mode"] == "both"
        assert req["previous_observed_at"].startswith("2026-09-25")

    def test_missing_fields_asked_not_guessed(self):
        pq = parse_query("這個菜會漲嗎", today=TODAY)
        assert "品項" in pq.missing and "今天價格" in pq.missing
        assert pq.to_forecast_request() is None

    def test_non_comparable_unit_flagged(self):
        pq = parse_query("高麗菜一顆30元", today=TODAY)
        assert pq.unit_non_comparable is True
        req = pq.to_forecast_request()
        assert req is None  # 不可比單位不組請求

    def test_no_price_invented(self):
        pq = parse_query("高麗菜多少錢", today=TODAY)
        assert pq.current_price is None  # 絕不猜價格
        assert "今天價格" in pq.missing


class TestToolLimiter:
    def test_max_calls(self):
        lim = ToolCallLimiter(max_calls=3)
        assert all(lim.check() for _ in range(3))
        assert lim.check() is False


class TestAgentToolsIntegration:
    @pytest.fixture(scope="class")
    def engine(self):
        release = Path("models/releases/0.1.0")
        if not (release / "manifest.json").exists():
            pytest.skip("模型包未打包")
        from aiot_price.models.predict import ForecastEngine

        return ForecastEngine(release)

    def test_get_market_quote(self, engine):
        tools = AgentTools(engine)
        q = tools.get_market_quote("cabbage", "中義市場")
        assert q["ok"] is True
        assert q["price"] > 0
        assert q["unit"] == "NTD_per_taiwan_jin"

    def test_get_market_quote_unavailable(self, engine):
        tools = AgentTools(engine)
        q = tools.get_market_quote("cabbage", "南屯市場")
        assert q["ok"] is False

    def test_post_forecast_same_as_api(self, engine):
        tools = AgentTools(engine)
        resp = tools.post_forecast(
            {
                "crop_id": "cabbage",
                "market_id": "中義市場",
                "current_price": 32.0,
                "price_unit": "NTD_per_taiwan_jin",
                "observed_at": "2026-10-02T10:00:00+08:00",
                "mode": "without_last_week",
            }
        )
        assert resp["error"] is None
        assert {r["horizon_days"] for r in resp["results"]} == {7, 14}
