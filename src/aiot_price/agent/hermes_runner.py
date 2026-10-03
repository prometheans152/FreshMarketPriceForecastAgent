"""Hermes Agent 整合層（第五輪重寫：S01/S02/S07）。

依實際安裝版 0.19.0 原始碼（非猜測）：
- ``AIAgent.__init__`` 支援 ``base_url/api_key/provider/model/max_iterations/
  max_tokens/enabled_toolsets/quiet_mode/skip_memory/skip_context_files/
  save_trajectories/ephemeral_system_prompt/tool_complete_callback``；
  **沒有** ``system_prompt``/``_env`` 參數。
- ``registry.dispatch(name, args)`` 以 ``handler(args, **kwargs)`` 呼叫——
  handler 簽名必須是 ``def handler(args: dict)``。
- ``tool_complete_callback(tool_call_id, name, display_args, function_result)``：
  真實工具執行的權威追蹤來源（不由事後重算補造）。
- zai provider 在有 key 時會 probe 端點；一律顯式 ``base_url`` 防止探測。

S02 隔離：本模組在 **import run_agent 之前**執行環境整理（模組載入一次）——
把 Hermes 備援金鑰鏈（GLM_API_KEY/ZAI/…/OPENAI/OPENROUTER/…）從本程序移除、
HERMES_HOME 指到專案隔離目錄；run_agent 匯入時的 dotenv 因此只會看到隔離家目錄。
GLM key 以 ``AIOT_GLM_API_KEY`` 為唯一來源，需要時顯式傳給 AIAgent。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
HERMES_HOME_DEFAULT = _PROJECT_ROOT / "private" / "hermes_home"
HERMES_TOOLSET = "aiot_price"

# ---------- S02：import 前的環境隔離（模組載入時執行一次） ----------

_HERMES_PROVIDER_ENV_VARS = (
    "GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY", "GLM_BASE_URL",
    "OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
    "NOUS_API_KEY", "KIMI_API_KEY", "MINIMAX_API_KEY",
)


def _apply_isolation_once() -> Path:
    """在 import run_agent 前整理本程序環境（冪等）。

    - 若使用者只設了 GLM_API_KEY（未設 AIOT_GLM_API_KEY），先映射到 AIOT_GLM_API_KEY。
    - 移除 Hermes 備援金鑰鏈，避免框架自動探測/借用全域供應商憑證。
    - HERMES_HOME 固定專案隔離目錄（不存在則建空目錄）。
    """
    home = Path(os.environ.get("AIOT_HERMES_HOME", HERMES_HOME_DEFAULT))
    if not home.is_absolute():
        home = (_PROJECT_ROOT / home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HERMES_HOME"] = str(home)
    if os.environ.get("GLM_API_KEY") and not os.environ.get("AIOT_GLM_API_KEY"):
        os.environ["AIOT_GLM_API_KEY"] = os.environ["GLM_API_KEY"]
    for var in _HERMES_PROVIDER_ENV_VARS:
        os.environ.pop(var, None)
    return home


_apply_isolation_once()

# 隔離完成後才 import 框架（run_agent 在 import 時讀 dotenv）
import run_agent  # noqa: E402
from model_tools import registry as hermes_registry  # noqa: E402

from .providers import (  # noqa: E402
    TOOL_SCHEMAS,
    ProviderProfile,
    TrustedContext,
)
from .service import RuleBackend, load_system_prompt, validate_qwen_answer  # noqa: E402
from .tools import AgentTools, parse_query  # noqa: E402


class _ToolCallRecorder:
    """S01：以 tool_complete_callback 記錄真實執行（權威來源，非事後補算）。"""

    def __init__(self):
        self.events: list[dict] = []

    def __call__(self, tool_call_id, name, display_args, function_result):
        result = function_result
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"raw": result}
        if not isinstance(result, dict):
            result = {"raw": str(result)}
        ok = not result.get("error")
        self.events.append({
            "tool": name,
            "tool_call_id": tool_call_id,
            "args": display_args if isinstance(display_args, dict) else {},
            "ok": ok,
            "result": result,
        })


def _register_aiot_tools(engine) -> None:
    """註冊菜價工具（handler 簽名=registry 慣例 ``handler(args, **kwargs)``）。

    每請求以 override 重註冊，綁定當前 engine（不因全域閉包綁舊引擎）。
    """
    tools = AgentTools(engine)

    def _dump(result: dict) -> str:
        # S01：registry 的 _normalize_handler_result 只接受 str；dict 回傳會被拒
        # （"unsupported result type: dict"）——一律序列化為 JSON 字串。
        return json.dumps(result, ensure_ascii=False, default=str)

    def _quote_handler(args: dict, **kwargs):
        if not isinstance(args, dict):
            return _dump({"error": "invalid_arguments"})
        return _dump(tools.get_market_quote(args.get("crop_id"), args.get("market_id")))

    def _forecast_handler(args: dict, **kwargs):
        if not isinstance(args, dict):
            return _dump({"error": "invalid_arguments"})
        return _dump(tools.post_forecast(args))

    for schema in TOOL_SCHEMAS:
        fn = schema["function"]
        handler = _quote_handler if fn["name"] == "get_market_quote" else _forecast_handler
        hermes_registry.register(fn["name"], HERMES_TOOLSET, fn, handler, override=True)


def run_hermes_agent(
    engine,
    query: str,
    profile: ProviderProfile,
    store_id: str | None = None,
    today=None,
) -> dict:
    """官方 Hermes 框架執行；真追蹤來自 tool_complete_callback（S01）。"""
    import importlib.metadata as md

    base = {
        "provider": profile.name, "model": profile.model,
        "framework": "hermes-agent",
        "runtime": f"hermes {md.version('hermes-agent')}",
        "backend_used": "hermes", "degraded": False, "degraded_reason": None,
    }

    parsed = parse_query(query, today=today)
    ctx = TrustedContext.from_parsed(parsed, store_id, today=today) if today else TrustedContext.from_parsed(parsed, store_id, today=parsed.today)

    if parsed.missing or parsed.unit_non_comparable:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True, "degraded_reason": "missing_input_skip_framework"}

    if not profile.model or not profile.base_url:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": "Hermes 後端配置不完整（缺 model 或 base_url）；請補齊或改用 rule。",
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_profile_incomplete"}

    key = os.environ.get(profile.api_key_env, "") if profile.api_key_env else ""
    if profile.api_key_env and not key:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": "Hermes 後端缺 API 金鑰環境變數；請設定後重試或改用 rule。",
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_api_key_missing"}

    _register_aiot_tools(engine)
    recorder = _ToolCallRecorder()

    system = load_system_prompt(strict=True) + (
        f"\n\n本次查詢可信資訊（不得修改）：品項 {ctx.crop_id}、市場 {ctx.market_id}、"
        f"今天 {parsed.current_price} {parsed.price_unit}、報價日 {ctx.observed_date}（Asia/Taipei）。"
        + (f" 上週價 {parsed.previous_price} {parsed.previous_price_unit}（{ctx.previous_date}）。"
           if ctx.previous_price_jin is not None else
           " 使用者未提供上週價：不得自行填入任何 previous 欄位。")
    )

    # S01/S07：僅使用安裝版實際支援的參數；max_iterations/max_tokens 由 profile 映射
    try:
        agent = run_agent.AIAgent(
            model=profile.model,
            provider=None,  # 顯式 base_url 的 OpenAI 相容端點；不讓框架自動探測平台
            api_key=key or "dummy",
            base_url=profile.base_url,
            ephemeral_system_prompt=system,
            enabled_toolsets=[HERMES_TOOLSET],
            quiet_mode=True,
            skip_memory=True,
            skip_context_files=True,
            save_trajectories=False,
            max_iterations=max(1, profile.max_turns),
            max_tokens=profile.max_tokens,
            tool_delay=0.0,
            tool_complete_callback=recorder,
        )
    except Exception as e:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": f"Hermes 建構失敗（{type(e).__name__}）；請改用 rule 或 direct。",
                "backend_used": "rule", "degraded": True, "degraded_reason": f"hermes_construct_error:{type(e).__name__}"}

    try:
        answer = agent.chat(query)
    except Exception:
        # S06：例外訊息不外流上游 body
        return {**base, "parsed": _pd(parsed), "tool_trace": recorder.events,
                "forecast": None,
                "answer": "Hermes 執行失敗；請稍後再試或改用 rule／direct。",
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_error"}

    # S01：追蹤以 recorder（真實執行）為準；沒有任何工具執行 → 不得產生成功狀態
    trace = recorder.events
    forecast_exec = None
    for ev in trace:
        if ev["tool"] == "post_forecast" and ev["ok"]:
            r = ev["result"]
            if isinstance(r, dict) and r.get("results") and not r.get("error"):
                forecast_exec = r
    if forecast_exec is None:
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": None,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True, "degraded_reason": "no_tool_execution_observed"}

    if not isinstance(answer, str) or not answer.strip():
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_exec,
                "answer": RuleBackend().reply(parsed, {"forecast": forecast_exec}),
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_empty_answer"}

    ok, why = validate_qwen_answer(answer, {"forecast": forecast_exec})
    if not ok:
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_exec,
                "answer": RuleBackend().reply(parsed, {"forecast": forecast_exec}),
                "backend_used": "rule", "degraded": True, "degraded_reason": f"hermes_output_rejected:{why}"}

    return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_exec, "answer": answer}


def _pd(parsed) -> dict:
    return {
        "crop_id": parsed.crop_id, "current_price": parsed.current_price,
        "price_unit": parsed.price_unit, "market_id": parsed.market_id,
        "previous_price": parsed.previous_price,
        "mode": (parsed.to_forecast_request() or {}).get("mode"),
        "missing": parsed.missing, "unit_non_comparable": parsed.unit_non_comparable,
    }
