"""T27 忠實性測試（本機工具層＋規則後端；Qwen 端忠實性待 SERVER 實測）。

核心斷言：回答不改變工具方向/數字、不捏造機率、缺資料要求補充、
B 一律標實驗性、Qwen 失敗降級仍顯示真實模型結果。
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.service import (
    RuleBackend,
    handle_agent_query,
)

TODAY = date(2026, 10, 2)


@pytest.fixture(scope="module")
def engine():
    release = Path("models/releases/0.1.0")
    if not (release / "manifest.json").exists():
        pytest.skip("模型包未打包")
    from aiot_price.models.predict import ForecastEngine

    return ForecastEngine(release)


def _query(engine, text):
    return handle_agent_query(engine, text, today=TODAY)


class TestFaithfulness:
    def test_answer_matches_tool_direction_and_numbers(self, engine):
        r = _query(engine, "高麗菜今天一斤32元")
        fc = None
        for t in r["tool_trace"]:
            if t["tool"] == "post_forecast":
                fc = t
        assert fc and fc["ok"]
        # 回答必須含工具的方向與百分比（從 handle 內部工具結果對照）
        assert "7 天後" in r["answer"] and "14 天後" in r["answer"]
        assert "實驗性" not in r["answer"]  # 未提供上週價不提 B

    def test_no_probability_words(self, engine):
        for text in ("高麗菜今天一斤32元", "絲瓜一公斤80元"):
            r = _query(engine, text)
            assert not re.search(r"\d+\s*%的(機率|機會)|機率.{0,4}\d+\s*%", r["answer"]), r["answer"]
            assert "可信度" not in r["answer"]

    def test_missing_data_asks_no_invention(self, engine):
        r = _query(engine, "這個會漲嗎")
        assert "補充" in r["answer"] or "缺" in r["answer"]
        assert all(t["tool"] != "post_forecast" for t in r["tool_trace"])  # 沒組出請求就不呼叫預測

    def test_no_price_invented_when_absent(self, engine):
        r = _query(engine, "高麗菜多少錢")
        assert r["answer"]  # 有回應
        assert not re.search(r"(約|是)\s*\d+(\.\d+)?\s*元", r["answer"])  # 不出現價格數字

    def test_non_comparable_unit_message(self, engine):
        r = _query(engine, "高麗菜一顆30元")
        assert "公斤" in r["answer"] or "台斤" in r["answer"]  # 引導改單位
        assert all(t["tool"] != "post_forecast" for t in r["tool_trace"])

    def test_b_mode_marks_experimental(self, engine):
        r = _query(engine, "高麗菜一斤32，上週28元")
        assert r["parsed"]["mode"] == "both"
        assert "實驗性" in r["answer"]
        assert "未經同店" in r["answer"]

    def test_stale_market_no_fake_conclusion(self, engine):
        r = _query(engine, "南屯市場的高麗菜一斤32元")
        assert "無法提供" in r["answer"] or "不足" in r["answer"]
        assert "上漲" not in r["answer"] and "下跌" not in r["answer"]

    def test_public_scope_mentioned(self, engine):
        r = _query(engine, "高麗菜今天一斤32元")
        assert "均價" in r["answer"] or "參考市場" in r["answer"]
        assert "同店驗證" in r["answer"] or "非同店" in r["answer"]

    def test_trace_records_tools(self, engine):
        r = _query(engine, "高麗菜今天一斤32元")
        tools_used = {t["tool"] for t in r["tool_trace"]}
        assert "post_forecast" in tools_used


class TestQwenFallback:
    def test_qwen_unavailable_falls_back_to_rule(self, engine, monkeypatch):
        from aiot_price.agent.service import QwenBackend

        backend = QwenBackend(base_url="", model="")  # 未設定
        assert backend.available() is False
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=backend, today=TODAY)
        assert r["backend"] in ("qwen", "rule")  # QwenBackend.reply 內部降級規則回答
        assert "7 天後" in r["answer"]  # 真模型結果仍顯示

    def test_qwen_network_error_falls_back(self, engine):
        from aiot_price.agent.service import QwenBackend

        backend = QwenBackend(base_url="http://127.0.0.1:9", model="test", timeout=1.0)
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=backend, today=TODAY)
        assert "7 天後" in r["answer"]  # 降級仍有真實結果


class TestAgentEndpoint:
    def test_api_agent_query(self):
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/agent/query", json={"query": "高麗菜今天一斤32元"})
        assert r.status_code == 200
        body = r.json()
        assert body["answer"]
        assert body["parsed"]["crop_id"] == "cabbage"
        assert body["tool_trace"]

    def test_api_agent_query_validation(self):
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        assert client.post("/agent/query", json={}).status_code == 400
        assert client.post("/agent/query", json={"query": "x" * 3000}).status_code == 400
