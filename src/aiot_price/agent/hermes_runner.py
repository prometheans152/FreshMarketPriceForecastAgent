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
import math
import os
import re
import threading
import time
from functools import wraps
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
    ALLOWED_ARG_KEYS,
    TOOL_SCHEMAS,
    TOOL_NAMES,
    ProviderProfile,
    TrustedContext,
    _execute_tool,
    _fallback_answer,
    agent_preflight_missing,
    mask_secrets,
    tool_result_status,
    validate_args_against_context,
)
from .service import RuleBackend, load_system_prompt, validate_qwen_answer  # noqa: E402
from .tools import AgentTools, ToolCallLimiter, parse_query  # noqa: E402
from aiot_price.data.schema import CROP_MAPPINGS  # noqa: E402
from aiot_price.models.predict import KNOWN_MARKETS  # noqa: E402


_HERMES_LIFECYCLE_LOCK = threading.RLock()


def _serialized_lifecycle(fn):
    """Hermes uses a process-wide registry: protect registration through return.

    Registration-only locking would still let B replace handlers during A.chat.
    Handlers themselves do not acquire this lock, so framework worker threads
    can finish while the request thread holds the complete lifecycle lock.
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with _HERMES_LIFECYCLE_LOCK:
            return fn(*args, **kwargs)
    return wrapped


def _trace_value(value):
    """Only bounded primitive values are eligible for the client trace."""
    if isinstance(value, str):
        return mask_secrets(value)[:128]
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return None


def _trace_error(error, tool: str) -> str | None:
    """Expose contract codes, never arbitrary third-party error bodies."""
    if not error:
        return None
    if not isinstance(error, str):
        return "tool_execution_failed"
    if isinstance(error, str) and error.startswith("input_fidelity_rejected:"):
        reason = error.split(":", 2)[1]
        allowed = {
            "invalid_arguments", "invalid_argument_keys", "invalid_request_id",
            "crop_mismatch_with_user_input", "market_mismatch_with_user_input",
            "mode_not_allowed_by_user_input", "observed_date_mismatch_with_user_input",
            "current_price_not_comparable", "current_price_mismatch_with_user_input",
            "previous_price_not_provided_by_user", "previous_price_not_comparable",
            "previous_price_mismatch_with_user_input", "previous_date_mismatch_with_user_input",
            "forecast_input_missing_or_invalid",
        }
        return f"input_fidelity_rejected:{reason if reason in allowed else 'invalid_arguments'}"
    if error in {
        "save_requires_user_confirmation", "save_request_id_not_confirmed_by_user",
        "save_saver_unavailable", "save_saver_invalid_result", "tool_result_invalid",
        "tool_budget_exceeded",
    }:
        return error
    if tool == "get_market_quote":
        return "market_quote_unavailable"
    return "tool_execution_failed"


class _ToolCallRecorder:
    """Record real callbacks; retain trusted results separately from safe trace."""

    def __init__(self, ctx: TrustedContext | None = None):
        self.events: list[dict] = []
        self.ctx = ctx
        self.tool_outputs = {"forecast": None, "market_quote": None, "save_ok": False}

    def __call__(self, tool_call_id, name, display_args, function_result):
        result = function_result
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = None
        if not isinstance(result, dict):
            result = {"ok": False, "error": "tool_result_invalid"}
        tool = name if isinstance(name, str) and name in TOOL_NAMES else "unknown_tool"
        ok, error = tool_result_status(result, tool=tool)
        error = _trace_error(error, tool)
        if tool == "unknown_tool":
            validation = "rejected:not_whitelisted"
            ok, error = False, "not_whitelisted"
        elif self.ctx is not None:
            valid, why, _ = validate_args_against_context(
                tool, display_args if isinstance(display_args, dict) else None, self.ctx)
            validation = "accepted" if valid else f"rejected:{_trace_error('input_fidelity_rejected:' + why, tool)}"
            if not valid:
                ok = False
                error = _trace_error("input_fidelity_rejected:" + why, tool)
            elif error in {"save_requires_user_confirmation", "save_request_id_not_confirmed_by_user", "save_saver_unavailable"}:
                validation = f"rejected:{error}"
        else:
            validation = "not_checked"

        # No raw args/result/error body is stored in events. A rejected call
        # needs only its reason, even if the rejected values are allowed keys.
        args = {}
        if not validation.startswith("rejected:") and isinstance(display_args, dict):
            args = {key: _trace_value(value) for key, value in display_args.items()
                    if key in ALLOWED_ARG_KEYS.get(tool, set())}
        summary = {"ok": ok}
        if error:
            summary["error"] = error
        if ok:
            for key in ("request_id", "record_id", "price", "unit", "observed_date"):
                if key in result:
                    summary[key] = _trace_value(result[key])
            if tool == "post_forecast" and result.get("results"):
                # The wire payload omits a null error for Hermes classification;
                # restore the ForecastEngine response shape at the API boundary.
                self.tool_outputs["forecast"] = {**result, "error": None}
            elif tool == "get_market_quote":
                self.tool_outputs["market_quote"] = {
                    key: result[key] for key in ("ok", "price", "unit", "observed_date", "crop_id", "market_id")
                    if key in result}
            elif tool == "save_record":
                self.tool_outputs["save_ok"] = True
        self.events.append({
            "tool": tool,
            "tool_call_id": _trace_value(tool_call_id),
            "args": args,
            "validation": validation,
            "ok": ok,
            "error": error,
            "result": summary,
        })


@_serialized_lifecycle
def _register_aiot_tools(engine, ctx: TrustedContext, save_gate: dict | None = None, max_calls: int = 4) -> None:
    """註冊菜價工具（handler 簽名=registry 慣例 ``handler(args, **kwargs)``）。

    呼叫者 run_hermes_agent 必須持有完整生命週期鎖，直到 chat 與驗證結束。
    此函式自身的鎖也阻止其他執行緒於活動請求中直接重註冊。
    第二階段對稱防線：與 direct 迴圈相同，quote/forecast 參數一律經
    ``validate_args_against_context``（TrustedContext）——hermes 模式下 LLM
    同樣不可改價/改日期/換品項/無中生有上週價。save_record 同一確認門。
    """
    tools = AgentTools(engine)
    limiter = ToolCallLimiter(max_calls=max_calls)
    limiter_lock = threading.Lock()

    def _dump(result: dict) -> str:
        # S01：registry 的 _normalize_handler_result 只接受 str；dict 回傳會被拒
        # （"unsupported result type: dict"）——一律序列化為 JSON 字串。
        # Installed Hermes mistakes the literal key "error" for an error even
        # when its value is null, then appends non-JSON loop warnings. Omit only
        # that null key on successful wire results, keeping engine data intact.
        payload = result
        if isinstance(result, dict) and "error" in result and result["error"] is None and tool_result_status(result)[0]:
            payload = {key: value for key, value in result.items() if key != "error"}
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _limited_execute(name: str, args):
        # All three handlers share one query budget, including rejected calls.
        # Hermes may run multiple handlers concurrently within one SDK turn.
        with limiter_lock:
            allowed = limiter.check()
        if not allowed:
            return _dump({"ok": False, "error": "tool_budget_exceeded"})
        return _dump(_execute_tool(tools, name, args if isinstance(args, dict) else None, ctx, save_gate))

    def _quote_handler(args: dict, **kwargs):
        return _limited_execute("get_market_quote", args)

    def _forecast_handler(args: dict, **kwargs):
        return _limited_execute("post_forecast", args)

    def _save_handler(args: dict, **kwargs):
        return _limited_execute("save_record", args)

    handlers = {
        "get_market_quote": _quote_handler,
        "post_forecast": _forecast_handler,
        "save_record": _save_handler,
    }
    for schema in TOOL_SCHEMAS:
        fn = schema["function"]
        hermes_registry.register(fn["name"], HERMES_TOOLSET, fn, handlers[fn["name"]], override=True)


def _validate_answer_source(answer: str, tool_outputs: dict, ctx: TrustedContext) -> tuple[bool, str]:
    """Bind any named market/crop to the actual tool context.

    Shared Qwen validation remains untouched; this additional Web contract
    prevents a stale quote being presented without its date or under a wrong
    market/crop label. Forecast replies may omit these labels, but cannot
    attribute the same correctly validated numbers to another source.
    """
    quote = tool_outputs.get("market_quote")
    forecast = tool_outputs.get("forecast")
    quote_only = not forecast and isinstance(quote, dict) and quote.get("ok") is True
    if not forecast and not quote_only:
        return True, ""
    prefix = "quote" if quote_only else "forecast"
    if quote_only:
        observed = quote.get("observed_date")
        if not isinstance(observed, str) or observed not in answer:
            return False, "quote_observed_date_missing"
    # Match longest names first: 大甲第二市場 contains 第二市場 but is one source.
    market_pattern = "|".join(re.escape(name) for name in sorted(KNOWN_MARKETS, key=len, reverse=True))
    markets = {match.group(0) for match in re.finditer(market_pattern, answer)}
    market = quote.get("market_id") if quote_only else ctx.market_id
    if markets - {market}:
        return False, f"{prefix}_market_mismatch"
    if quote_only and market not in markets:
        return False, "quote_market_missing"
    names_to_crop = {}
    for crop_id, crop in CROP_MAPPINGS.items():
        for name in (crop.display_name, crop.source_column, *crop.aliases):
            names_to_crop[name] = crop_id
    crop_pattern = "|".join(re.escape(name) for name in sorted(names_to_crop, key=len, reverse=True))
    crops = {names_to_crop[match.group(0)] for match in re.finditer(crop_pattern, answer)}
    crop = quote.get("crop_id") if quote_only else ctx.crop_id
    if crops - {crop}:
        return False, f"{prefix}_crop_mismatch"
    if quote_only and crop not in crops:
        return False, "quote_crop_missing"
    return True, ""


@_serialized_lifecycle
def run_hermes_agent(
    engine,
    query: str,
    profile: ProviderProfile,
    store_id: str | None = None,
    today=None,
    save_gate: dict | None = None,
) -> dict:
    """官方 Hermes 框架執行；真追蹤來自 tool_complete_callback（S01）。"""
    import importlib.metadata as md

    started = time.monotonic()
    runtime_version = md.version('hermes-agent')
    base = {
        "provider": profile.name, "model": profile.model,
        "framework": "hermes-agent",
        "runtime": f"hermes {runtime_version}",
        "backend_used": "hermes", "degraded": False, "degraded_reason": None,
    }

    parsed = parse_query(query, today=today)
    ctx = TrustedContext.from_parsed(parsed, store_id, today=today) if today else TrustedContext.from_parsed(parsed, store_id, today=parsed.today)

    if agent_preflight_missing(parsed, save_gate):
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

    # Retry controls below are private SDK features audited in this version.
    # A changed SDK must be checked before a Web request can reach its API.
    if runtime_version != "0.19.0":
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": "Hermes 執行版本尚未核對；請先使用表單查詢。",
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "hermes_runtime_contract_unsupported"}

    _register_aiot_tools(engine, ctx=ctx, save_gate=save_gate, max_calls=profile.max_tool_calls)
    recorder = _ToolCallRecorder(ctx)
    crop_label = {"cabbage": "高麗菜", "bok_choy": "青江菜", "sponge_gourd": "絲瓜"}.get(ctx.crop_id, ctx.crop_id)

    system = load_system_prompt(strict=True) + (
        f"\n\n本次查詢可信資訊（不得修改）：品項 {CROP_MAPPINGS[ctx.crop_id].display_name if ctx.crop_id in CROP_MAPPINGS else ctx.crop_id}（{ctx.crop_id}）、市場 {ctx.market_id}、"
        f"今天 {parsed.current_price} {parsed.price_unit}、報價日 {ctx.observed_date}（Asia/Taipei）。"
        + (f" 上週價 {parsed.previous_price} {parsed.previous_price_unit}（{ctx.previous_date}）。"
           if ctx.previous_price_jin is not None else
           " 使用者未提供上週價：不得自行填入任何 previous 欄位。")
        + " 工具僅 get_market_quote、post_forecast、save_record；save_record 需使用者已於介面確認保存，回答只能引用工具結果的數字。"
        + f" post_forecast 的 observed_at 必須使用完整 ISO 8601 日期與時區：{ctx.observed_date}T00:00:00+08:00。"
        + (f" previous_observed_at 亦須使用完整日期與時區：{ctx.previous_date}T00:00:00+08:00。"
           if ctx.previous_price_jin is not None else "")
        + f" 本次允許 mode：{', '.join(ctx.allowed_modes)}，不得改成其他模式。"
        + " 最終回答使用純文字，不加編號、項目符號、表格、Markdown 或模型版本數字。"
        + " 所有價格、日期、期限及方向只複述成功工具結果；不自行算百分比，未要求時不要輸出百分比。"
        + " 回答提到市場或品項時，名稱亦須與本次成功工具的來源相符，不可反串其他市場或品項。"
        + " 預測每個期限各寫一段：期限、target_date、方向、price_estimate 與工具價格單位；不得交換期限。"
        + " 若有 A、B 對照，每段先寫清楚 A 模式或 B 模式，再寫該模式該期限的數字，不得混用。"
        + "\n\n最終回答只用以下固定模板，優先於前述一般回覆建議；不得另加任何句子。"
        + f" 品項只寫短名 {crop_label}；單位按成功工具 NTD_per_taiwan_jin 寫台斤、NTD_per_kg 寫公斤。"
        + " 價格及日期空位逐字填成功工具對應欄位，不保留尖括號，不自行計算。"
        + "\n行情固定兩句（只查行情時 ONLY 這兩句，日期已有完整明示）："
        + f"\n{ctx.market_id}{crop_label}公開行情為 <price> 元／<單位>（觀測日 <observed_date>）。"
        + "\n市場均價不是個店真值，僅供市場參考。"
        + "\n預測固定模板：每個 mode／期限只寫一行，direction 的 up／down／flat 分別寫上漲／下跌／大致持平。"
        + " without_last_week／fallback_without_last_week 用 A，with_last_week 用 B，both 分別填 A 與 B 的工具結果，按下列格式各寫兩行："
        + "\n<模式 A 或 B> 模式7天後（<該模式 horizon_days=7 的 target_date>）：<direction>，預估店價 <price_estimate> 元／<price_estimate_unit 對應單位>。"
        + "\n<模式 A 或 B> 模式14天後（<該模式 horizon_days=14 的 target_date>）：<direction>，預估店價 <price_estimate> 元／<price_estimate_unit 對應單位>。"
        + "\n市場均價不是個店真值；未經同店驗證，僅供參考。"
        + "\n有 B 時只再加：B 模式為實驗性，未經同店驗證。其餘解釋或資訊不列入最終回答。"
    )
    if isinstance(save_gate, dict) and save_gate.get("confirmed") is True and save_gate.get("request_id"):
        system += f"\n使用者已在介面確認保存先前預測 request_id={save_gate['request_id']}；保存時只能使用此 id。"

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
            request_overrides={"timeout": profile.timeout},
            tool_delay=0.0,
            tool_complete_callback=recorder,
        )
    except Exception as e:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": f"Hermes 建構失敗（{type(e).__name__}）；請改用 rule 或 direct。",
                "backend_used": "rule", "degraded": True, "degraded_reason": f"hermes_construct_error:{type(e).__name__}"}

    retry_contract = (
        isinstance(getattr(agent, "_api_max_retries", None), int)
        and callable(getattr(agent, "_try_recover_primary_transport", None))
        and callable(getattr(agent, "_try_activate_fallback", None))
        and callable(getattr(agent, "interrupt", None))
    )
    if not retry_contract:
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": "Hermes 執行介面尚未核對；請先使用表單查詢。",
                "backend_used": "rule", "degraded": True,
                "degraded_reason": "hermes_runtime_contract_unsupported"}
    # In 0.19.0 this count is attempts, not additional retries. The SDK's
    # OpenAI request-local clients already use max_retries=0. Disable hidden
    # primary-recovery and provider-fallback cycles without replacing API I/O.
    agent._api_max_retries = max(1, profile.max_retries + 1)
    agent._try_recover_primary_transport = lambda *args, **kwargs: False
    agent._try_activate_fallback = lambda *args, **kwargs: False
    # Web returns a complete JSON answer. Hermes otherwise streams even with
    # no callback and overwrites request_overrides.timeout in that path. Its
    # audited native non-streaming branch honors the profile timeout/retries.
    agent._disable_streaming = True

    deadline_reached = threading.Event()
    def interrupt_at_deadline():
        deadline_reached.set()
        try:
            agent.interrupt()
        except Exception:
            # A cancellation failure cannot authorize a late success or expose
            # an SDK/provider exception body to the browser.
            pass

    remaining = profile.total_timeout - (time.monotonic() - started)
    chat_failed = False
    answer = None
    if remaining <= 0:
        deadline_reached.set()
    else:
        deadline_timer = threading.Timer(remaining, interrupt_at_deadline)
        deadline_timer.daemon = True
        deadline_timer.start()
        try:
            # The synchronous chat keeps the lifecycle lock until it unwinds;
            # this is cooperative interruption, not a hard thread kill. The
            # SDK's own HTTP workers may finish later at their request timeout.
            answer = agent.chat(query)
        except Exception:
            chat_failed = True
        finally:
            deadline_timer.cancel()
            deadline_timer.join()

    if deadline_reached.is_set() or time.monotonic() - started >= profile.total_timeout:
        forecast_exec = recorder.tool_outputs["forecast"]
        return {**base, "parsed": _pd(parsed), "tool_trace": recorder.events,
                "forecast": forecast_exec,
                "answer": _fallback_answer(parsed, forecast_exec, "hermes_total_timeout", recorder.tool_outputs),
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_total_timeout"}

    if chat_failed:
        # S06：例外訊息不外流上游 body
        return {**base, "parsed": _pd(parsed), "tool_trace": recorder.events,
                "forecast": None,
                "answer": "Hermes 執行失敗；請稍後再試或改用 rule／direct。",
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_error"}

    # S01：追蹤以 recorder（真實執行）為準；沒有任何工具執行 → 不得產生成功狀態
    trace = recorder.events
    tool_outputs = recorder.tool_outputs
    forecast_exec = tool_outputs["forecast"]
    if not (forecast_exec or tool_outputs["market_quote"] or tool_outputs["save_ok"]):
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": None,
                "answer": _fallback_answer(parsed, None, "no_tool_execution_observed", tool_outputs),
                "backend_used": "rule", "degraded": True, "degraded_reason": "no_tool_execution_observed"}

    if not isinstance(answer, str) or not answer.strip():
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_exec,
                "answer": _fallback_answer(parsed, forecast_exec, "hermes_empty_answer", tool_outputs),
                "backend_used": "rule", "degraded": True, "degraded_reason": "hermes_empty_answer"}

    ok, why = validate_qwen_answer(answer, tool_outputs)
    if ok:
        ok, why = _validate_answer_source(answer, tool_outputs, ctx)
    if not ok:
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_exec,
                "answer": _fallback_answer(parsed, forecast_exec, why, tool_outputs),
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
