"""Phase 2 r2 Hermes regression tests: real framework/dispatch, local SDK responses.

No external model call, private record write, or deployment is performed here.
"""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import pytest

hermes = pytest.importorskip("aiot_price.agent.hermes_runner")
from aiot_price.agent.providers import ProviderProfile

TODAY = date(2026, 10, 4)
PROFILE = ProviderProfile(
    name="hermes-local-r2", kind="openai_compat", base_url="http://127.0.0.1:9/v1",
    model="local-sdk-fixture", api_key_env="", max_turns=6,
)


def _forecast_args(crop="cabbage", price=32):
    return {"crop_id": crop, "market_id": "中義市場", "current_price": price,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T12:00:00+08:00",
            "mode": "without_last_week"}


class LocalEngine:
    """Controlled local tool boundary; records real AgentTools forecast requests."""
    def __init__(self, rid):
        self.rid = rid
        self.seen = []
        self.history = pd.DataFrame([
            {"crop_id": "cabbage", "market_id": "中義市場", "date": "2026-10-02", "price": 27.5},
            {"crop_id": "bok_choy", "market_id": "中義市場", "date": "2026-10-02", "price": 30.0},
        ])
        self.history["date"] = pd.to_datetime(self.history["date"])
        self.public_cutoff = pd.Timestamp("2026-10-02")

    def forecast(self, args):
        self.seen.append(dict(args))
        return {"request_id": self.rid, "error": None, "mode_executed": "without_last_week",
                "input_observed_at": args["observed_at"], "public_data_cutoff": "2026-10-02",
                "results": [{"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
                             "relative_change_estimate": 0.0, "price_estimate": args["current_price"],
                             "price_estimate_unit": "NTD_per_taiwan_jin"}]}


def _completion(step):
    from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
    from openai.types.chat.chat_completion_message_tool_call import Function
    if isinstance(step, str):
        message = ChatCompletionMessage(role="assistant", content=step)
        reason = "stop"
    else:
        name, args, call_id = step
        message = ChatCompletionMessage(
            role="assistant", content=None,
            tool_calls=[ChatCompletionMessageToolCall(
                id=call_id, type="function",
                function=Function(name=name, arguments=json.dumps(args, ensure_ascii=False)))],
        )
        reason = "tool_calls"
    return ChatCompletion(id="chatcmpl-local", created=1, model=PROFILE.model, object="chat.completion",
                          choices=[{"index": 0, "finish_reason": reason, "message": message}])


def _install_sdk(monkeypatch, scripts, on_create=None):
    import openai
    indices = {label: 0 for label in scripts}
    indices_lock = threading.Lock()

    class Completions:
        def create(self, **kw):
            # Hermes may construct a fresh client on its API worker thread
            # each turn; derive request identity from the actual user message.
            user = next((m.get("content", "") for m in kw.get("messages", [])
                         if isinstance(m, dict) and m.get("role") == "user"), "")
            label = "main" if "main" in scripts else ("B" if "40元" in user else "A")
            with indices_lock:
                index = indices[label]
                indices[label] += 1
            if on_create:
                on_create(label, index)
            step = scripts[label][index]
            return _completion(step)

    class Client:
        def __init__(self, *a, **kw):
            self.chat = type("Chat", (), {"completions": Completions()})()

    monkeypatch.setattr(openai, "OpenAI", Client)
    # Hermes resolves and caches the lazy OpenAI name separately from the SDK.
    monkeypatch.setattr(hermes.run_agent, "OpenAI", Client)


@pytest.fixture(autouse=True)
def isolated_hermes_home(tmp_path, monkeypatch):
    import agent.context_compressor
    import socket

    monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path / "hermes"))
    hermes._apply_isolation_once()
    # Endpoint context-length discovery is network I/O, outside these tests.
    monkeypatch.setattr(agent.context_compressor, "get_model_context_length", lambda *a, **kw: 131072)
    def deny_network(*a, **kw):
        raise AssertionError("Hermes offline regression attempted network I/O")
    monkeypatch.setattr(socket, "create_connection", deny_network)


@pytest.mark.parametrize("name,args,result", [
    ("post_forecast", {"crop_id": "cabbage", "api_key": "sk-FAKE123456"},
     {"ok": False, "error": "input_fidelity_rejected:invalid_argument_keys", "body": "raw-server-body"}),
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "Bearer FAKE123456"},
     {"ok": False, "reason": "provider body sk-FAKE123456", "body": "raw-server-body"}),
    ("save_record", {"request_id": "sk-FAKE123456", "token": "another-secret"},
     {"ok": False, "error": "arbitrary-server-body sk-FAKE123456", "body": "raw-server-body"}),
    ("sk-FAKE123456", {"anything": "sk-FAKE123456"}, "raw-server-body sk-FAKE123456"),
    ("post_forecast", {"crop_id": "cabbage"},
     {"ok": False, "error": {"body": ["raw-server-body", "sk-FAKE123456"]}}),
    ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
     ["raw-server-body", {"api_key": "sk-FAKE123456"}]),
])
def test_callback_never_exposes_unknown_args_or_upstream_error_body(name, args, result):
    recorder = hermes._ToolCallRecorder()
    recorder("call-sk-FAKE123456", name, args, json.dumps(result) if isinstance(result, dict) else result)
    event = recorder.events[0]
    serialized = json.dumps(event, ensure_ascii=False)
    assert "sk-FAKE123456" not in serialized
    assert "Bearer FAKE123456" not in serialized
    assert "raw-server-body" not in serialized
    assert "arbitrary-server-body" not in serialized
    assert "api_key" not in event["args"] and "token" not in event["args"] and "anything" not in event["args"]


@pytest.mark.parametrize("result", [
    {"ok": False, "reason": "本市場無可用資料"},
    {"ok": False, "error": None, "reason": "本市場無可用資料"},
    {"body": "untrusted callback body"},
    {"ok": "false", "reason": "invalid success flag"},
    "invalid JSON reply",
])
def test_callback_marks_failed_and_malformed_execution_unsuccessful(result):
    recorder = hermes._ToolCallRecorder()
    recorder("call-failed", "get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"},
             json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else result)
    assert recorder.events[0]["ok"] is False
    assert recorder.events[0].get("error")


def test_real_dispatch_rejected_args_remain_rejected_and_secret_free(monkeypatch):
    args = {**_forecast_args(), "api_key": "sk-FAKE123456"}
    _install_sdk(monkeypatch, {"main": [("post_forecast", args, "call-invalid"), "無法取得資料。"]})
    engine = LocalEngine("req-A")
    result = hermes.run_hermes_agent(engine, "高麗菜今天一台斤32元", PROFILE, today=TODAY)
    trace = result["tool_trace"][0]
    assert engine.seen == []
    assert trace["ok"] is False and trace["validation"].startswith("rejected:")
    assert "sk-FAKE123456" not in json.dumps(result, ensure_ascii=False)


def test_quote_only_enters_real_framework_without_current_store_price(monkeypatch):
    _install_sdk(monkeypatch, {"main": [
        ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, "call-quote"),
        "中義市場高麗菜公開行情為 27.5 元／台斤（觀測日 2026-10-02）。市場均價不是個店真值，僅供市場參考。",
    ]})
    engine = LocalEngine("req-A")
    result = hermes.run_hermes_agent(engine, "請查中義市場高麗菜最新公開市場行情", PROFILE, today=TODAY)
    assert result["degraded"] is False and result["backend_used"] == "hermes", result
    assert result["forecast"] is None and engine.seen == []
    assert result["tool_trace"][0]["validation"] == "accepted"
    assert result["tool_trace"][0]["ok"] is True


def test_save_only_enters_real_framework_without_refilling_store_price(monkeypatch):
    saved = []
    gate = {"request_id": "req-prior", "confirmed": True,
            "saver": lambda rid: saved.append(rid) or {"ok": True, "record_id": "record-local"}}
    _install_sdk(monkeypatch, {"main": [
        ("save_record", {"request_id": "req-prior"}, "call-save"), "已確認保存，供後續核對。",
    ]})
    result = hermes.run_hermes_agent(LocalEngine("unused"), "請保存剛才那筆預測", PROFILE,
                                     today=TODAY, save_gate=gate)
    assert saved == ["req-prior"]
    assert result["degraded"] is False and result["forecast"] is None, result
    assert result["tool_trace"][0]["validation"] == "accepted" and result["tool_trace"][0]["ok"]


def test_quote_preflight_does_not_authorize_forecast_with_invented_price(monkeypatch):
    _install_sdk(monkeypatch, {"main": [("post_forecast", _forecast_args(), "call-invented"), "無資料。"]})
    engine = LocalEngine("unused")
    result = hermes.run_hermes_agent(engine, "請查中義市場高麗菜最新公開市場行情", PROFILE, today=TODAY)
    assert engine.seen == [] and result["forecast"] is None
    assert result["degraded"] is True
    assert result["tool_trace"][0]["validation"].startswith("rejected:")


def test_quote_execution_failure_is_distinct_from_accepted_arguments(monkeypatch):
    monkeypatch.setattr(hermes.AgentTools, "get_market_quote", lambda *a: {"ok": False, "reason": "本市場無可用資料"})
    _install_sdk(monkeypatch, {"main": [
        ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, "call-quote"), "已查詢。",
    ]})
    result = hermes.run_hermes_agent(LocalEngine("unused"), "高麗菜今天一台斤32元", PROFILE, today=TODAY)
    trace = result["tool_trace"][0]
    assert trace["validation"] == "accepted"
    assert trace["ok"] is False and trace["error"]
    assert result["degraded"] is True


@pytest.mark.parametrize("b_crop,b_query", [
    ("cabbage", "高麗菜今天一台斤40元，請保存。"),
    ("bok_choy", "青江菜今天一台斤40元，請保存。"),
])
def test_overlapping_real_framework_requests_keep_prices_crops_and_save_ids_isolated(monkeypatch, b_crop, b_query):
    a_waiting = threading.Event()
    b_submitted = threading.Event()
    b_inside_sdk = threading.Event()
    a_engine, b_engine = LocalEngine("req-A"), LocalEngine("req-B")
    saved = {"A": [], "B": []}

    def on_create(label, index):
        if label == "A" and index == 1:
            a_waiting.set()
            assert b_submitted.wait(15)
            # On r1 B registers during A's lifecycle; serialized r2 deliberately
            # leaves this event unset until A completes. A proceeds in either case.
            b_inside_sdk.wait(0.5)
        elif label == "B":
            b_inside_sdk.set()

    scripts = {
        "A": [("post_forecast", _forecast_args(), "a-first"),
              ("post_forecast", _forecast_args(), "a-second"),
              ("save_record", {"request_id": "req-A"}, "a-save"), "已完成工具查詢並保存。"],
        "B": [("post_forecast", _forecast_args(b_crop, 40), "b-first"),
              ("post_forecast", _forecast_args(b_crop, 40), "b-second"),
              ("save_record", {"request_id": "req-B"}, "b-save"), "已完成工具查詢並保存。"],
    }
    _install_sdk(monkeypatch, scripts, on_create)

    def request(label, engine, query):
        threading.current_thread().name = label
        if label == "B":
            b_submitted.set()
        gate = {"request_id": f"req-{label}", "confirmed": True,
                "saver": lambda rid: saved[label].append(rid) or {"ok": True, "record_id": f"record-{label}"}}
        return hermes.run_hermes_agent(engine, query, PROFILE, store_id=f"store-{label}", today=TODAY, save_gate=gate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(request, "A", a_engine, "高麗菜今天一台斤32元，請保存。")
        assert a_waiting.wait(30)
        b = pool.submit(request, "B", b_engine, b_query)
        results = [a.result(timeout=30), b.result(timeout=30)]

    assert [row["current_price"] for row in a_engine.seen] == [32, 32]
    assert [row["crop_id"] for row in a_engine.seen] == ["cabbage", "cabbage"]
    assert [row["store_id"] for row in a_engine.seen] == ["store-A", "store-A"]
    assert [row["current_price"] for row in b_engine.seen] == [40, 40]
    assert [row["crop_id"] for row in b_engine.seen] == [b_crop, b_crop]
    assert [row["store_id"] for row in b_engine.seen] == ["store-B", "store-B"]
    assert saved == {"A": ["req-A"], "B": ["req-B"]}
    assert [r["forecast"]["request_id"] for r in results] == ["req-A", "req-B"]
    assert all(not r["degraded"] and all(e["ok"] for e in r["tool_trace"]) for r in results), results


@pytest.mark.parametrize("confirmed,args", [
    (False, {"request_id": "req-prior"}),
    (True, {"request_id": "req-other"}),
    (True, {"request_id": "req-prior", "token": "sk-FAKE123456"}),
])
def test_real_save_dispatch_cannot_bypass_confirmation_id_or_arg_allowlist(monkeypatch, confirmed, args):
    saved = []
    gate = {"request_id": "req-prior", "confirmed": confirmed,
            "saver": lambda rid: saved.append(rid) or {"ok": True, "record_id": "record-local"}}
    _install_sdk(monkeypatch, {"main": [("save_record", args, "call-save-invalid"), "無法保存。"]})
    result = hermes.run_hermes_agent(LocalEngine("unused"), "高麗菜今天一台斤32元，請保存。",
                                     PROFILE, today=TODAY, save_gate=gate)
    assert saved == []
    assert result["degraded"] is True and result["forecast"] is None
    assert result["tool_trace"][0]["validation"].startswith("rejected:")
    assert result["tool_trace"][0]["ok"] is False
    assert "sk-FAKE123456" not in json.dumps(result, ensure_ascii=False)


def test_rejected_save_only_answer_preserves_successful_save_confirmation(monkeypatch):
    saved = []
    gate = {"request_id": "req-prior", "confirmed": True,
            "saver": lambda rid: saved.append(rid) or {"ok": True, "record_id": "record-local"}}
    _install_sdk(monkeypatch, {"main": [
        ("save_record", {"request_id": "req-prior"}, "call-save"), "已保存，7天後會漲到一百元。",
    ]})
    result = hermes.run_hermes_agent(LocalEngine("unused"), "請保存剛才那筆預測", PROFILE,
                                     today=TODAY, save_gate=gate)
    assert saved == ["req-prior"] and result["forecast"] is None
    assert result["degraded"] and "rejected" in result["degraded_reason"]
    assert "保存" in result["answer"] and "還缺" not in result["answer"]
    assert "一百" not in result["answer"]


def test_rejected_quote_only_answer_falls_back_to_real_quote_without_refilling_price(monkeypatch):
    _install_sdk(monkeypatch, {"main": [
        ("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, "call-quote"),
        "7天後會漲到一百元。",
    ]})
    result = hermes.run_hermes_agent(LocalEngine("unused"), "請查中義市場高麗菜最新公開市場行情",
                                     PROFILE, today=TODAY)
    assert result["forecast"] is None and result["degraded"]
    assert "rejected" in result["degraded_reason"]
    assert "27.5" in result["answer"] and "2026-10-02" in result["answer"]
    assert "還缺" not in result["answer"] and "一百" not in result["answer"]
