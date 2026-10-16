"""Hermes Web runtime bounds, using the real SDK and offline API responses.

These tests make no GLM request and write no store record. The SDK boundary is
controlled so retries, cancellation and unsafe upstream text are observable.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
import threading
import time
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

# Hermes installs log handlers during import, before fixtures can run. Keep
# their destination inside this task so an offline test cannot append to the
# project's protected historical Hermes logs. Full-suite commands also set
# these variables before process startup, as other test modules import first.
_IMPORT_HOME = Path(__file__).resolve().parents[2] / "outputs" / "quality_runs" / "hermes_glm_web_20261011_01" / "runtime_import_home"
_IMPORT_HOME.mkdir(parents=True, exist_ok=True)
for _home_var in ("AIOT_HERMES_HOME", "HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                  "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
    os.environ[_home_var] = str(_IMPORT_HOME)

hermes = pytest.importorskip("aiot_price.agent.hermes_runner")
from aiot_price.agent.providers import ProviderProfile

TODAY = date(2026, 10, 11)
QUOTE_QUERY = "請查中義市場高麗菜最新公開市場行情"
QUOTE_ANSWER = "中義市場高麗菜公開行情為 30 元／台斤（觀測日 2026-10-09）。市場均價不是個店真值，僅供市場參考。"


class QuoteEngine:
    def __init__(self):
        self.history = pd.DataFrame([
            {"crop_id": "cabbage", "market_id": "中義市場", "date": pd.Timestamp("2026-10-09"), "price": 30.0}
        ])
        self.public_cutoff = pd.Timestamp("2026-10-09")


def profile(**changes):
    return ProviderProfile(**{
        "name": "hermes-web-offline", "kind": "openai_compat", "model": "local-sdk-fixture",
        "base_url": "http://127.0.0.1:9/v1", "api_key_env": "", "timeout": 0.4,
        "max_retries": 0, "max_turns": 4, "total_timeout": 30.0, **changes,
    })


def completion(step):
    from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
    from openai.types.chat.chat_completion_message_tool_call import Function
    if isinstance(step, str):
        message = ChatCompletionMessage(role="assistant", content=step)
        reason = "stop"
    else:
        suffix = step.get("suffix", 0) if isinstance(step, dict) else 0
        message = ChatCompletionMessage(role="assistant", content=None, tool_calls=[
            ChatCompletionMessageToolCall(id=f"call-quote-offline-{suffix}", type="function", function=Function(
                name="get_market_quote", arguments=json.dumps(
                    {"crop_id": "cabbage", "market_id": "中義市場"}, ensure_ascii=False)))])
        reason = "tool_calls"
    return ChatCompletion(id="chatcmpl-offline", created=1, model="local-sdk-fixture", object="chat.completion",
                          choices=[{"index": 0, "finish_reason": reason, "message": message}])


def install_sdk(monkeypatch, respond):
    import openai
    requests = []
    requests_lock = threading.Lock()

    class Completions:
        def create(self, **kwargs):
            with requests_lock:
                index = len(requests)
                requests.append(kwargs)
            return respond(index, kwargs)

    class Client:
        def __init__(self, *args, **kwargs):
            self.chat = type("Chat", (), {"completions": Completions()})()

        def close(self):
            pass

    monkeypatch.setattr(openai, "OpenAI", Client)
    monkeypatch.setattr(hermes.run_agent, "OpenAI", Client)
    return requests


@pytest.fixture(autouse=True)
def offline_home(tmp_path, monkeypatch):
    import agent.context_compressor
    import socket
    monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path / "hermes"))
    hermes._apply_isolation_once()
    monkeypatch.setattr(agent.context_compressor, "get_model_context_length", lambda *a, **kw: 131072)

    def deny_network(*a, **kw):
        raise AssertionError("Offline runtime test attempted network I/O")
    monkeypatch.setattr(socket, "create_connection", deny_network)


def controlled_timers(monkeypatch):
    """Control the clock boundary without racing the SDK's client startup.

    Real SDK API and tool execution stay intact. A timer fires at a chosen API
    boundary so the deadline outcome and post-return cancellation are stable.
    """
    timers = []
    class Timer:
        def __init__(self, interval, callback):
            self.callback = callback
            self.started = False
            self.cancelled = False
            self.daemon = False
            timers.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

        def join(self):
            pass

        def fire(self):
            if self.started and not self.cancelled:
                self.callback()
    monkeypatch.setattr(hermes.threading, "Timer", Timer)
    return timers


def test_each_real_sdk_request_receives_profile_timeout(monkeypatch):
    """Missing request_overrides would leave the provider's long default timeout."""
    requests = install_sdk(monkeypatch, lambda index, kwargs: completion(
        None if index == 0 else QUOTE_ANSWER))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert not result["degraded"], result
    assert len(requests) == 2
    assert all(request.get("timeout") == 0.4 for request in requests)


def test_zero_retries_prevents_primary_transport_recovery_attempt(monkeypatch):
    """A transient failure must not replay the request through hidden recovery."""
    import httpx
    import openai
    import agent.conversation_loop
    monkeypatch.setattr(agent.conversation_loop.time, "sleep", lambda *args: None)

    def failed_request(index, kwargs):
        raise openai.APIConnectionError(request=httpx.Request("POST", "http://127.0.0.1:9/v1/chat/completions"))
    requests = install_sdk(monkeypatch, failed_request)
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert result["degraded"] and result["backend_used"] == "rule"
    assert result["tool_trace"] == []
    assert len(requests) == 1, "profile.max_retries=0 authorizes one attempt, including recovery paths"


def test_total_deadline_never_accepts_a_late_sdk_answer_and_preserves_tool_trace(monkeypatch):
    """A completed tool stays visible, but an answer after the deadline cannot pass."""
    timers = controlled_timers(monkeypatch)
    worker_finished = threading.Event()
    def respond(index, kwargs):
        if index == 0:
            return completion(None)
        try:
            timers[-1].fire()
            return completion(QUOTE_ANSWER)
        finally:
            worker_finished.set()
    requests = install_sdk(monkeypatch, respond)
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    # Hermes cancels cooperatively, not by killing Python worker threads. Keep
    # this controlled transport alive until it finishes before fixture teardown.
    assert worker_finished.wait(5)
    assert len(requests) == 2
    assert result["degraded"] and result["backend_used"] == "rule"
    assert result["degraded_reason"] == "hermes_total_timeout"
    assert result["tool_trace"][0]["ok"] is True
    assert "30" in result["answer"] and "2026-10-09" in result["answer"]


def test_success_cancels_deadline_timer_before_another_request(monkeypatch):
    """An old timer must not interrupt its completed agent during the next query."""
    agents = []
    timers = controlled_timers(monkeypatch)
    real_constructor = hermes.run_agent.AIAgent
    class WatchingAgent(real_constructor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            agents.append(self)
    monkeypatch.setattr(hermes.run_agent, "AIAgent", WatchingAgent)
    install_sdk(monkeypatch, lambda index, kwargs: completion(
        None if index % 2 == 0 else QUOTE_ANSWER))
    first = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert not first["degraded"], first
    timers[0].fire()  # Expiration after return must have been cancelled.
    second = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert not second["degraded"], second
    assert len(agents) == 2 and not agents[0].is_interrupted


def test_upstream_secret_in_completed_answer_falls_back_to_safe_quote(monkeypatch):
    """Successful earlier tools do not authorize exposing a provider credential."""
    monkeypatch.setenv("AIOT_GLM_API_KEY", "sk-offline-runtime-private")
    install_sdk(monkeypatch, lambda index, kwargs: completion(
        None if index == 0 else "公開行情參考。Authorization: Bearer sk-offline-runtime-private"))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert result["degraded"] and result["backend_used"] == "rule"
    assert "sk-offline-runtime-private" not in json.dumps(result, ensure_ascii=False)
    assert "30" in result["answer"] and result["tool_trace"][0]["ok"]


def test_unverified_sdk_version_fails_closed_without_api_request(monkeypatch):
    """Private retry controls cannot be assumed valid on an unreviewed SDK."""
    actual_version = importlib.metadata.version
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.20.0" if name == "hermes-agent" else actual_version(name))
    requests = install_sdk(monkeypatch, lambda *args: completion("沒有工具。"))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert requests == []
    assert result["degraded"] and result["degraded_reason"] == "hermes_runtime_contract_unsupported"


def test_missing_retry_contract_fails_closed_without_api_request(monkeypatch):
    real_constructor = hermes.run_agent.AIAgent
    class MissingContractAgent(real_constructor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            del self._api_max_retries
    monkeypatch.setattr(hermes.run_agent, "AIAgent", MissingContractAgent)
    requests = install_sdk(monkeypatch, lambda *args: completion("沒有工具。"))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert requests == []
    assert result["degraded"] and result["degraded_reason"] == "hermes_runtime_contract_unsupported"


@pytest.mark.parametrize("answer,reason", [
    ("中義市場高麗菜公開行情為 30 元／台斤。市場均價不是個店真值。", "quote_observed_date_missing"),
    ("南屯市場高麗菜公開行情為 30 元／台斤（觀測日 2026-10-09）。市場均價不是個店真值。", "quote_market_mismatch"),
    ("中義市場青江菜公開行情為 30 元／台斤（觀測日 2026-10-09）。市場均價不是個店真值。", "quote_crop_mismatch"),
    ("高麗菜公開行情為 30 元／台斤（觀測日 2026-10-09）。市場均價不是個店真值。", "quote_market_missing"),
    ("中義市場公開行情為 30 元／台斤（觀測日 2026-10-09）。市場均價不是個店真值。", "quote_crop_missing"),
])
def test_quote_guard_rejects_missing_date_or_wrong_market_crop(monkeypatch, answer, reason):
    """Actual quote tool truth cannot authorize a misleading source label."""
    class ScriptedAgent:
        def __init__(self, **kwargs):
            self.callback = kwargs["tool_complete_callback"]
            self._api_max_retries = 3
            self._try_recover_primary_transport = lambda *a, **kw: False
            self._try_activate_fallback = lambda *a, **kw: False

        def interrupt(self):
            pass

        def chat(self, query):
            args = {"crop_id": "cabbage", "market_id": "中義市場"}
            raw = hermes.hermes_registry.dispatch("get_market_quote", args)
            self.callback("call-real-quote", "get_market_quote", args, raw)
            return answer
    monkeypatch.setattr(hermes.run_agent, "AIAgent", ScriptedAgent)
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert result["tool_trace"][0]["ok"] is True
    assert result["degraded"] and result["backend_used"] == "rule"
    assert result["degraded_reason"] == f"hermes_output_rejected:{reason}"
    assert "30" in result["answer"] and "2026-10-09" in result["answer"]


def test_native_sdk_rounds_share_one_tool_budget(monkeypatch):
    """A later native SDK round cannot reset the per-query tool allowance."""
    executed = []
    real_quote = hermes.AgentTools.get_market_quote
    def quote(self, *args, **kwargs):
        executed.append(True)
        return real_quote(self, *args, **kwargs)
    monkeypatch.setattr(hermes.AgentTools, "get_market_quote", quote)
    install_sdk(monkeypatch, lambda index, kwargs: completion({"suffix": index} if index < 2 else QUOTE_ANSWER))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(max_tool_calls=1), today=TODAY)
    assert len(result["tool_trace"]) == 2
    assert len(executed) == 1
    assert sum(event["ok"] for event in result["tool_trace"]) == 1
    assert result["tool_trace"][-1]["error"] == "tool_budget_exceeded"


@pytest.mark.parametrize("label,reason", [
    ("南屯市場高麗菜", "forecast_market_mismatch"),
    ("中義市場青江菜", "forecast_crop_mismatch"),
    ("中義市場高麗菜", None),
])
def test_forecast_labels_must_match_the_user_and_actual_tool_context(monkeypatch, label, reason):
    """Correct forecast numbers cannot be attributed to another market or crop."""
    class Engine(QuoteEngine):
        def forecast(self, args):
            return {"request_id": "request-offline-source", "error": None,
                    "crop_id": "cabbage", "market_id": "中義市場", "model_version": "offline-fixture",
                    "mode_executed": "without_last_week", "input_observed_at": args["observed_at"],
                    "public_data_cutoff": "2026-10-09", "results": [
                        {"horizon_days": 7, "target_date": "2026-10-18", "direction": "flat",
                         "relative_change_estimate": 0.0, "price_estimate": 30.4, "price_estimate_unit": "NTD_per_taiwan_jin"},
                        {"horizon_days": 14, "target_date": "2026-10-25", "direction": "flat",
                         "relative_change_estimate": 0.0, "price_estimate": 28.8, "price_estimate_unit": "NTD_per_taiwan_jin"},
                    ]}

    class ScriptedAgent:
        def __init__(self, **kwargs):
            self.callback = kwargs["tool_complete_callback"]
            self._api_max_retries = 3
            self._try_recover_primary_transport = lambda *a, **kw: False
            self._try_activate_fallback = lambda *a, **kw: False

        def interrupt(self):
            pass

        def chat(self, query):
            args = {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
                    "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-11T00:00:00+08:00",
                    "mode": "without_last_week"}
            raw = hermes.hermes_registry.dispatch("post_forecast", args)
            self.callback("call-actual-forecast", "post_forecast", args, raw)
            return (f"{label}7天後（2026-10-18）：大致持平，預估店價30.4元／台斤。\n"
                    "14天後（2026-10-25）：大致持平，預估店價28.8元／台斤。\n"
                    "市場均價不是個店真值；未經同店驗證，僅供參考。")
    monkeypatch.setattr(hermes.run_agent, "AIAgent", ScriptedAgent)
    result = hermes.run_hermes_agent(Engine(), "高麗菜今天一台斤32元", profile(), today=TODAY)
    assert result["tool_trace"][0]["ok"] is True
    if reason:
        assert result["degraded"] and result["backend_used"] == "rule"
        assert result["degraded_reason"] == f"hermes_output_rejected:{reason}"
        assert label not in result["answer"]
    else:
        assert not result["degraded"] and result["backend_used"] == "hermes", result


def test_real_sdk_prompt_requests_exact_quote_and_forecast_templates(monkeypatch):
    """Do not tell the real model to add prose the original grammar rejects."""
    requests = install_sdk(monkeypatch, lambda index, kwargs: completion(None if index == 0 else QUOTE_ANSWER))
    result = hermes.run_hermes_agent(QuoteEngine(), QUOTE_QUERY, profile(), today=TODAY)
    assert not result["degraded"], result
    system_text = "\n".join(message.get("content", "") for message in requests[0]["messages"]
                            if isinstance(message, dict) and message.get("role") == "system")
    assert "資料落後時如實提醒" not in system_text
    assert "行情固定兩句" in system_text
    assert "預測固定模板" in system_text
    assert "不得另加任何句子" in system_text


def test_exact_quote_template_rejects_the_observed_live_extra_prose():
    """The actual failed live wording stays a negative control, not accepted grammar."""
    quote = {"market_quote": {"ok": True, "price": 30.0, "unit": "NTD_per_taiwan_jin",
                              "observed_date": "2026-10-02", "market_id": "中義市場", "crop_id": "cabbage"}}
    exact = ("中義市場高麗菜公開行情為 30.0 元／台斤（觀測日 2026-10-02）。"
             "市場均價不是個店真值，僅供市場參考。")
    live_failed = ("中義市場甘藍（平地高麗菜）公開行情為 30.0 元／台斤（觀測日 2026-10-02）。"
                   "此為資料落後的觀測值，並非今天即時行情。市場均價不是個店真值，僅供市場參考。")
    assert hermes.validate_qwen_answer(exact, quote) == (True, "")
    assert hermes.validate_qwen_answer(live_failed, quote) == (False, "unsupported_quote_statement")
