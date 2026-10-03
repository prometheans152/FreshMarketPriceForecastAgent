"""Hermes Agent 整合層（第四輪 D41：NousResearch hermes-agent 0.19.0）。

依 docs/research/HERMES_INTEGRATION_PROBE.md 的實測 API：
- import 名是 ``run_agent``（套件名 hermes-agent）：``from run_agent import AIAgent``。
- 工具註冊：``registry.register(name, toolset, schema, handler)`` ＋
  ``enabled_toolsets`` 白名單——只開本案兩個菜價工具，排除 terminal/browser 等 28 個內建。
- provider：GLM 用 ``zai``；自架 Qwen 用 OpenAI 相容 ``base_url``。
- 安全（探測事故教訓）：HERMES_HOME 固定到專案隔離目錄、quiet_mode、skip_memory、
  skip_context_files；本層不做任何終端互動、不使用 hermes-agent CLI entry point。

本層只負責「框架執行」；菜價計算仍由 AgentTools/ForecastEngine 提供，
最終輸出仍經 validate_qwen_answer 真值防線（與規則/GLM 直達路徑同一標準）。
"""

from __future__ import annotations

import os
from pathlib import Path

from .providers import ProviderProfile
from .service import RuleBackend, load_system_prompt, validate_qwen_answer
from .tools import AgentTools, parse_query

HERMES_TOOLSET = "aiot_price"
HERMES_HOME_DEFAULT = Path(__file__).resolve().parents[3] / "private" / "hermes_home"


def _register_aiot_tools(engine) -> bool:
    """把 get_market_quote／post_forecast 註冊到 Hermes 工具 registry（冪等）。"""
    from model_tools import registry as hermes_registry

    if getattr(hermes_registry, "_aiot_registered", False):
        return True
    tools = AgentTools(engine)

    def _get_market_quote(crop_id: str, market_id: str) -> dict:
        return tools.get_market_quote(crop_id, market_id)

    def _post_forecast(**kwargs) -> dict:
        return tools.post_forecast(kwargs)

    from .providers import TOOL_SCHEMAS

    for schema in TOOL_SCHEMAS:
        fn = schema["function"]
        handler = _get_market_quote if fn["name"] == "get_market_quote" else _post_forecast
        hermes_registry.register(fn["name"], HERMES_TOOLSET, fn, handler)
    hermes_registry._aiot_registered = True
    return True


def _isolated_env_for_hermes(profile: ProviderProfile) -> dict:
    """建構 Hermes 用的乾淨環境：隔離 HERMES_HOME、只帶明確的 key 映射。

    探測事故顯示 Hermes 會自動讀使用者全域環境的金鑰（GLM_API_KEY 等備援鏈）；
    本層只把「我們 profile 指定的 key_env」映射過去，其餘供應商變數一律移除，
    避免框架偷偷連上未授權的雲端或輔助端點。
    """
    import os as _os

    env = dict(_os.environ)
    home = Path(env.get("AIOT_HERMES_HOME", HERMES_HOME_DEFAULT))
    home.mkdir(parents=True, exist_ok=True)
    env["HERMES_HOME"] = str(home)
    # 移除 Hermes 會自動探測的供應商金鑰，僅保留本案 profile 指定者（映射為 GLM_API_KEY）
    for var in ("GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY", "OPENAI_API_KEY",
                "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "NOUS_API_KEY"):
        env.pop(var, None)
    if profile.api_key_env:
        key = _os.environ.get(profile.api_key_env, "")
        if key:
            env["GLM_API_KEY"] = key
    return env


def run_hermes_agent(
    engine,
    query: str,
    profile: ProviderProfile,
    store_id: str | None = None,
    today=None,
) -> dict:
    """以官方 Hermes Agent 框架執行代理人流程。

    回傳格式與 run_agent_loop 相容，另附 framework/runtime 版本。
    離線可測部分：工具註冊與建構參數；真 LLM 呼叫需有效 key（未設→明確降級）。
    """
    import importlib.metadata as md

    base = {
        "provider": profile.name,
        "model": profile.model,
        "framework": "hermes-agent",
        "runtime": f"hermes {md.version('hermes-agent')}",
        "backend_used": "hermes",
        "degraded": False,
        "degraded_reason": None,
    }

    parsed = parse_query(query, today=today)
    # R01 同標準：缺必要輸入不進框架（省資源且防捏造）
    if parsed.missing or parsed.unit_non_comparable:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "missing_input_skip_framework"}

    key = os.environ.get(profile.api_key_env, "") if profile.api_key_env else ""
    if not profile.model or (profile.api_key_env and not key):
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": "Hermes 後端配置不完整（缺 model ID 或金鑰環境變數）；請改用 AIOT_AGENT_PROFILE=rule 或補齊設定。",
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "hermes_profile_incomplete"}

    _register_aiot_tools(engine)
    from run_agent import AIAgent

    system = load_system_prompt(strict=True)
    env = _isolated_env_for_hermes(profile)

    agent = AIAgent(
        model=profile.model,
        provider="zai" if profile.name.startswith("glm") else None,
        api_key=key or "dummy",
        base_url=None if profile.name.startswith("glm") else profile.base_url,
        system_prompt=system,
        enabled_toolsets=[HERMES_TOOLSET],  # 白名單：只開菜價工具集
        quiet_mode=True,
        skip_memory=True,
        skip_context_files=True,
        save_trajectories=False,
        _env=env,
    )
    forecast_result = None

    def _capture(**kwargs):  # post_forecast handler 已閉包於 registry；改為事後取最近結果
        return AgentTools(engine).post_forecast(kwargs)

    try:
        answer = agent.chat(query)
    except TypeError:
        # 某些版本不支援 _env/system_prompt 關鍵字：退回最小參數建構
        try:
            agent = AIAgent(
                model=profile.model,
                provider="zai" if profile.name.startswith("glm") else None,
                api_key=key or "dummy",
                base_url=None if profile.name.startswith("glm") else profile.base_url,
                enabled_toolsets=[HERMES_TOOLSET],
                quiet_mode=True,
                skip_memory=True,
                skip_context_files=True,
                save_trajectories=False,
            )
            answer = agent.chat(query)
        except Exception as e:
            return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                    "answer": f"Hermes 框架執行失敗（{type(e).__name__}）；請改用 rule 或 openai_compat 路徑。",
                    "backend_used": "rule", "degraded": True,
                    "degraded_reason": f"hermes_error:{type(e).__name__}"}
    except Exception as e:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": f"Hermes 框架執行失敗（{type(e).__name__}）；請改用 rule 或 openai_compat 路徑。",
                "backend_used": "rule", "degraded": True,
                "degraded_reason": f"hermes_error:{type(e).__name__}"}

    if not isinstance(answer, str) or not answer.strip():
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "hermes_empty_answer"}

    # 工具真值：Hermes 內部已執行 registry 工具；重新以相同輸入取得可驗證真值
    req = parsed.to_forecast_request(store_id=store_id)
    if req is not None:
        forecast_result = AgentTools(engine).post_forecast(req)

    tool_ok = bool(forecast_result and forecast_result.get("results") and not forecast_result.get("error"))
    if not tool_ok:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": forecast_result,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "no_tool_result_skip_framework"}

    ok, why = validate_qwen_answer(answer, {"forecast": forecast_result})
    if not ok:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": forecast_result,
                "answer": RuleBackend().reply(parsed, {"forecast": forecast_result}),
                "backend_used": "rule", "degraded": True,
                "degraded_reason": f"hermes_output_rejected:{why}"}

    return {**base, "parsed": _pd(parsed), "tool_trace": [{"tool": "hermes_internal", "args": None, "ok": True}],
            "forecast": forecast_result, "answer": answer}


def _pd(parsed) -> dict:
    return {
        "crop_id": parsed.crop_id, "current_price": parsed.current_price,
        "price_unit": parsed.price_unit, "market_id": parsed.market_id,
        "previous_price": parsed.previous_price,
        "mode": (parsed.to_forecast_request() or {}).get("mode"),
        "missing": parsed.missing, "unit_non_comparable": parsed.unit_non_comparable,
    }
