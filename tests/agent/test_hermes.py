"""Hermes 整合層離線測試（無真 LLM 呼叫；只測註冊、建構參數與防線）。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

hermes_runner = pytest.importorskip("aiot_price.agent.hermes_runner", reason="hermes-agent 未安裝")
run_agent = pytest.importorskip("run_agent", reason="hermes-agent 套件未安裝")

from aiot_price.agent.providers import ProviderProfile

TODAY = date(2026, 10, 4)
RELEASE = Path("models/releases/0.1.0")

HERMES_PROFILE = ProviderProfile(
    name="glm_zai", kind="openai_compat", base_url="https://api.z.ai/api/paas/v4",
    model="glm-test", api_key_env="AIOT_GLM_API_KEY", timeout=10,
)


@pytest.fixture(scope="module")
def engine():
    if not (RELEASE / "manifest.json").exists():
        pytest.skip("模型包未打包")
    from aiot_price.models.predict import ForecastEngine
    return ForecastEngine(RELEASE)


class TestHermesOffline:
    def test_tool_registration_whitelist(self, engine, tmp_path, monkeypatch):
        """註冊後 enabled_toolsets=['aiot_price'] 只含兩個菜價工具，terminal/browser 被排除。"""
        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        hermes_runner._register_aiot_tools(engine)
        from model_tools import get_tool_definitions

        defs = get_tool_definitions(enabled_toolsets=[hermes_runner.HERMES_TOOLSET])
        names = {d["function"]["name"] for d in defs}
        assert names == {"get_market_quote", "post_forecast"}, f"白名單外工具外洩：{names}"
        all_names = {d["function"]["name"] for d in get_tool_definitions(enabled_toolsets=None) or []}
        assert "terminal" in all_names or len(all_names) > 5  # 確認內建高危工具存在但未啟用
        assert "terminal" not in names and "browser" not in "".join(names)

    def test_missing_input_skips_framework(self, engine, monkeypatch):
        """R01 同標準：缺輸入不建構 agent、不發請求。"""
        called = {"n": 0}
        real_ai_agent = run_agent.AIAgent

        def spy(*a, **kw):
            called["n"] += 1
            return real_ai_agent(*a, **kw)

        monkeypatch.setattr(run_agent, "AIAgent", spy)
        r = hermes_runner.run_hermes_agent(engine, "請問菜價", HERMES_PROFILE, today=TODAY)
        assert called["n"] == 0
        assert r["backend_used"] == "rule" and "補充" in r["answer"] or "缺" in r["answer"]

    def test_incomplete_profile_degrades_explicitly(self, engine, tmp_path, monkeypatch):
        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        monkeypatch.delenv("AIOT_GLM_API_KEY", raising=False)
        bad = ProviderProfile(name="glm_zai", kind="openai_compat",
                              base_url="https://api.z.ai/api/paas/v4", model="", api_key_env="AIOT_GLM_API_KEY")
        r = hermes_runner.run_hermes_agent(engine, "高麗菜今天一斤32元", bad, today=TODAY)
        assert r["degraded"] is True and "配置不完整" in r["answer"]

    def test_isolated_env_strips_other_provider_keys(self, tmp_path, monkeypatch):
        """S02 環境隔離（產品本身，非測試 wrapper）：import 前的整理冪等且生效。"""
        import os

        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-should-be-removed")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-removed")
        monkeypatch.setenv("GLM_API_KEY", "sk-glm-removed")
        monkeypatch.setenv("AIOT_GLM_API_KEY", "sk-ours")
        home = hermes_runner._apply_isolation_once()
        # 備援金鑰鏈被移除；AIOT_*（本案命名）保留；HERMES_HOME 指隔離目錄
        assert os.environ.get("OPENAI_API_KEY") is None
        assert os.environ.get("OPENROUTER_API_KEY") is None
        assert os.environ.get("GLM_API_KEY") is None
        assert os.environ.get("AIOT_GLM_API_KEY") == "sk-ours"
        assert str(home) == str(tmp_path)
        # 框架實際視角：HERMES_HOME 生效
        assert os.environ["HERMES_HOME"] == str(tmp_path)

    def test_output_guardrail_rejects_fabrication(self, engine, tmp_path, monkeypatch):
        """S01/S09 防線：真 AIAgent＋真 openai SDK 型別的 mock 回應（非 FakeAgent）。

        模型第一輪提出忠實的 post_forecast tool_call（真 dispatch 執行），
        第二輪回捏造文字 → 真值驗證器拒絕 → 降級規則回答。
        """
        import json as _json

        import openai as _openai
        from openai.types.chat import (
            ChatCompletion,
            ChatCompletionMessage,
            ChatCompletionMessageToolCall,
        )
        from openai.types.chat.chat_completion_message_tool_call import Function

        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        monkeypatch.setenv("AIOT_GLM_API_KEY", "sk-test")
        calls = {"n": 0}

        def _tool_call_resp():
            return ChatCompletion(
                id="chatcmpl-1", created=1, model="glm-test", object="chat.completion",
                choices=[{"index": 0, "finish_reason": "tool_calls", "message": ChatCompletionMessage(
                    role="assistant", content=None,
                    tool_calls=[ChatCompletionMessageToolCall(
                        id="call-1", type="function",
                        function=Function(
                            name="post_forecast",
                            arguments=_json.dumps({
                                "crop_id": "cabbage", "market_id": "中義市場",
                                "current_price": 32.0, "price_unit": "NTD_per_taiwan_jin",
                                "observed_at": "2026-10-04T12:00:00+08:00",
                                "mode": "without_last_week",
                            }, ensure_ascii=False),
                        ),
                    )],
                )}],
            )

        def _final_resp():
            return ChatCompletion(
                id="chatcmpl-2", created=1, model="glm-test", object="chat.completion",
                choices=[{"index": 0, "finish_reason": "stop", "message": ChatCompletionMessage(
                    role="assistant", content="7天後必定上漲99%，售價999元；已驗證。",
                )}],
            )

        class _FakeCompletions:
            def create(self, **kw):
                calls["n"] += 1
                msgs = kw.get("messages") or []
                has_tool_result = any(getattr(m, "role", "") == "tool" or (isinstance(m, dict) and m.get("role") == "tool") for m in msgs)
                return _final_resp() if has_tool_result else _tool_call_resp()

        class _FakeOpenAI:
            def __init__(self, *a, **kw):
                self.chat = type("C", (), {"completions": _FakeCompletions()})()

        monkeypatch.setattr(_openai, "OpenAI", _FakeOpenAI)
        r = hermes_runner.run_hermes_agent(engine, "高麗菜今天一斤32元", HERMES_PROFILE, today=TODAY)
        assert calls["n"] >= 2, f"應有工具呼叫＋最終回答兩輪（實際 {calls['n']}）"
        assert any(e["tool"] == "post_forecast" and e["ok"] for e in r["tool_trace"]), "真工具執行應被記錄"
        assert r["degraded"] is True and "rejected" in (r["degraded_reason"] or "")
        assert "999" not in r["answer"]
