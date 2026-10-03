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
        """環境隔離：未授權供應商金鑄被移除；HERMES_HOME 指到專案隔離目錄。"""
        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-should-be-removed")
        monkeypatch.setenv("AIOT_GLM_API_KEY", "sk-ours")
        env = hermes_runner._isolated_env_for_hermes(HERMES_PROFILE)
        assert env.get("OPENAI_API_KEY") is None
        assert env.get("GLM_API_KEY") == "sk-ours"
        assert env["HERMES_HOME"] == str(tmp_path)

    def test_output_guardrail_rejects_fabrication(self, engine, tmp_path, monkeypatch):
        """防線測試：模擬 Hermes 回捏造文字 → 降級規則（不因框架不同而放寬）。"""
        monkeypatch.setenv("AIOT_HERMES_HOME", str(tmp_path))
        monkeypatch.setenv("AIOT_GLM_API_KEY", "sk-test")

        class FakeAgent:
            def __init__(self, *a, **kw):
                pass

            def chat(self, q):
                return "7天後必定上漲99%，售價999元；已驗證。"

        monkeypatch.setattr(run_agent, "AIAgent", FakeAgent)
        r = hermes_runner.run_hermes_agent(engine, "高麗菜今天一斤32元", HERMES_PROFILE, today=TODAY)
        assert r["backend_used"] == "rule"
        assert r["degraded"] is True and "rejected" in r["degraded_reason"]
        assert "999" not in r["answer"]
