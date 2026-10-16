"""Mock LLM transport, real tool/guard/API paths; no external model calls."""
from datetime import date
from pathlib import Path
import json

import pytest

from aiot_price.agent import providers as p
from aiot_price.agent.tools import AgentTools
from aiot_price.models.predict import ForecastEngine

TODAY = date(2026, 10, 4)
PROFILE = p.ProviderProfile(name="scripted-r2", kind="openai_compat", base_url="http://127.0.0.1:9/v1", model="mock")


@pytest.fixture(scope="module")
def engine():
    return ForecastEngine(Path("models/releases/0.1.0"))


def scripted(monkeypatch, tool, args, answer):
    responses = [p.ProviderResponse(tool_calls=[{"id": "r2-call", "name": tool, "arguments": args}]),
                 p.ProviderResponse(content=answer)]
    monkeypatch.setattr(p.OpenAICompatProvider, "chat", lambda *a, **k: responses.pop(0))


def test_quote_without_shop_price_reaches_real_tool(engine, monkeypatch):
    scripted(monkeypatch, "get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
             "中義市場最新公開行情為30元／台斤（觀測日2026-10-02）；市場均價不是個店真值。")
    result = p.run_agent_loop(engine, "請查中義市場高麗菜最新公開市場行情", PROFILE, today=TODAY)
    assert result["forecast"] is None
    assert not result["degraded"]
    assert result["tool_trace"][0]["validation"] == "accepted"
    assert result["tool_trace"][0]["ok"] is True
    assert "30元" in result["answer"]


def test_save_only_uses_confirmed_id_without_new_price(engine, monkeypatch):
    saved = []
    def saver(rid):
        saved.append(rid)
        return {"ok": True, "record_id": "isolated-record"}
    scripted(monkeypatch, "save_record", {"request_id": "server-rid"}, "已確認保存，供到期核對。")
    result = p.run_agent_loop(engine, "請保存剛才那筆預測", PROFILE, today=TODAY,
                              save_gate={"request_id": "server-rid", "confirmed": True, "saver": saver})
    assert saved == ["server-rid"]
    assert result["forecast"] is None and not result["degraded"]
    assert result["tool_trace"][0]["ok"] is True


def test_save_success_remains_visible_when_llm_price_is_rejected(engine, monkeypatch):
    scripted(monkeypatch, "save_record", {"request_id": "server-rid"}, "已保存。7天後會漲到一百元。")
    result = p.run_agent_loop(engine, "請保存剛才那筆預測", PROFILE, today=TODAY,
                              save_gate={"request_id": "server-rid", "confirmed": True,
                                         "saver": lambda rid: {"ok": True}})
    assert result["degraded"] and result["tool_trace"][0]["ok"]
    assert "保存" in result["answer"] and "一百元" not in result["answer"]
    assert "今天價格" not in result["answer"]


def test_quote_success_has_tool_truth_fallback_after_llm_future_price_rejected(engine, monkeypatch):
    scripted(monkeypatch, "get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, "明天菜價一百元。")
    result = p.run_agent_loop(engine, "請查中義市場高麗菜最新公開市场行情", PROFILE, today=TODAY)
    assert result["degraded"] and result["tool_trace"][0]["ok"]
    assert "30" in result["answer"] and "2026-10-02" in result["answer"]
    assert "一百元" not in result["answer"] and "今天價格" not in result["answer"]


@pytest.mark.parametrize("query", ["請查中義市場高麗菜最新行情", "高麗菜今天32元，預測7天後價格",
                                  "高麗菜2026-02-30一台斤32元，查中義市場行情"])
def test_open_preflight_does_not_allow_llm_invent_prediction_inputs(engine, monkeypatch, query):
    args = {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T12:00:00+08:00", "mode": "without_last_week"}
    scripted(monkeypatch, "post_forecast", args, "7天後價格30.7元。")
    result = p.run_agent_loop(engine, query, PROFILE, today=TODAY)
    assert result["forecast"] is None and result["degraded"]
    assert all(not event["ok"] for event in result["tool_trace"])


def test_quote_missing_or_ambiguous_identity_cannot_execute(engine, monkeypatch):
    for query in ["請查最新行情", "請查中義市場高麗菜與絲瓜最新行情"]:
        scripted(monkeypatch, "get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, "行情27.5元。")
        result = p.run_agent_loop(engine, query, PROFILE, today=TODAY)
        assert result["degraded"] and not result["tool_trace"]


@pytest.mark.parametrize("tool,args,result,query", [
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
     {"ok": False, "reason": "本市場無可用資料"}, "高麗菜今天一台斤32元，查中義市場行情"),
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
     {"ok": "false", "reason": "本市場無可用資料"}, "高麗菜今天一台斤32元，查中義市場行情"),
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
     {}, "高麗菜今天一台斤32元，查中義市場行情"),
    ("post_forecast", {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
                      "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T12:00:00+08:00", "mode": "without_last_week"},
     {"ok": False, "reason": "模型暫無資料", "results": []}, "高麗菜今天一台斤32元，預測7天後")])
def test_execution_failure_separate_from_accepted_arguments(engine, monkeypatch, tool, args, result, query):
    monkeypatch.setattr(AgentTools, tool, lambda *a, **k: result)
    scripted(monkeypatch, tool, args, "資料不足。")
    response = p.run_agent_loop(engine, query, PROFILE, today=TODAY)
    event = response["tool_trace"][0]
    assert event["validation"] == "accepted"
    assert event["ok"] is False and event["error"]
    assert response["forecast"] is None and response["degraded"]


@pytest.mark.parametrize("tool,args,budget", [
    ("get_market_quote", {"crop_id": "sk-FAKE123456", "market_id": "中義市場"}, 4),
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場", "sk-FAKE123456": "x"}, 4),
    ("sk-FAKE123456", {}, 4),
    ("get_market_quote", {"crop_id": "sk-FAKE123456", "market_id": "中義市場"}, 0)])
def test_direct_trace_masks_rejected_values_names_ids_and_budget_calls(engine, monkeypatch, tool, args, budget):
    responses = [p.ProviderResponse(tool_calls=[{"id": "call-sk-FAKE123456", "name": tool, "arguments": args}]),
                 p.ProviderResponse(content="資料不足。")]
    monkeypatch.setattr(p.OpenAICompatProvider, "chat", lambda *a, **k: responses.pop(0))
    profile = p.ProviderProfile(name="scripted-r2", kind="openai_compat", base_url="http://127.0.0.1:9/v1", model="mock", max_tool_calls=budget)
    response = p.run_agent_loop(engine, "高麗菜今天一台斤32元，查中義市場行情", profile, today=TODAY)
    assert response["tool_trace"] and not response["tool_trace"][0]["ok"]
    assert "sk-FAKE123456" not in json.dumps(response["tool_trace"], ensure_ascii=False)


def test_api_save_only_uses_real_server_forecast_and_temporary_record_path(engine, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from aiot_price.api import app as api
    forecast = AgentTools(engine).post_forecast({"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32,
                "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T12:00:00+08:00", "mode": "without_last_week"})
    api.register_recent_forecast(forecast, {"store_id": "r2-test"})
    original_save = api.save_prediction
    monkeypatch.setattr(api, "save_prediction", lambda fc, query: original_save(fc, query, out_dir=tmp_path))
    monkeypatch.setattr(p, "resolve_active_profile", lambda: (PROFILE, ""))
    monkeypatch.setenv("AIOT_AGENT_FRAMEWORK", "direct")
    scripted(monkeypatch, "save_record", {"request_id": forecast["request_id"]}, "已確認保存，供到期核對。")
    response = TestClient(api.app).post("/agent/query", json={"query": "請保存剛才那筆預測", "store_id": "r2-test",
                                "save_confirmation": {"request_id": forecast["request_id"], "confirmed": True}})
    assert response.status_code == 200
    body = response.json()
    assert not body["degraded"] and body["tool_trace"][0]["ok"]
    paths = list(tmp_path.glob("prediction_*.json"))
    assert len(paths) == 1
    assert json.loads(paths[0].read_text(encoding="utf-8"))["response"]["request_id"] == forecast["request_id"]
