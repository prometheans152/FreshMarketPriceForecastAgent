"""供應商無關的代理人後端（第五輪重寫：S03/S06/S07）。

分層不變（AGENT_RUNTIME_DIRECTION §2）；本輪強化：
- S03 TrustedContext：LLM 提出的工具參數必須忠於「可信規則解析的使用者輸入」；
  價格/日期/品項/市場/模式不可改寫，上週價不可無中生有，店號由呼叫端決定。
- S06 遮罩：上游錯誤 body 不進例外/回答/追蹤；對外只用穩定錯誤碼。
- S07 真上限：工具總數/輪數/總時間實際生效；每個宣告的 tool_call_id 都有
  匹配回覆（超預算者回 budget_exceeded），不留懸空 ID。
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .service import RuleBackend, load_system_prompt, validate_qwen_answer
from .tools import AgentTools, parse_query

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "agent_model.yaml"

# ---------- 工具白名單契約 ----------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_quote",
            "description": "查最新公開市場行情（臺中，元/台斤）。非預測；回傳觀測日與價格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"]},
                    "market_id": {"type": "string"},
                },
                "required": ["crop_id", "market_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_forecast",
            "description": "菜價 7/14 天預測。價格/日期/品項必須與使用者輸入一致，不得自行修改。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"]},
                    "market_id": {"type": "string"},
                    "current_price": {"type": "number"},
                    "price_unit": {"type": "string", "enum": ["NTD_per_taiwan_jin", "NTD_per_kg"]},
                    "observed_at": {"type": "string"},
                    "mode": {"type": "string", "enum": ["without_last_week", "with_last_week", "both"]},
                    "previous_price": {"type": "number"},
                    "previous_price_unit": {"type": "string", "enum": ["NTD_per_taiwan_jin", "NTD_per_kg"]},
                    "previous_observed_at": {"type": "string"},
                },
                "required": ["crop_id", "market_id", "current_price", "price_unit", "observed_at", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_record",
            "description": (
                "經使用者明確確認後，保存預測供 7/14 天後到期核對（介面保存按鈕走 /records；對話內保存需客戶端 save_confirmation）。"
                "只有當客戶端已帶 save_confirmation（使用者確認）才會成功；"
                "未確認時呼叫會收到 save_requires_user_confirmation，此時應告知使用者如何保存。"
                "不接受模型自製的任何價格資料；保存內容一律取自伺服器暫存的真實推論結果。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "本次預測的 request_id（來自 post_forecast 結果）"},
                },
                "required": ["request_id"],
            },
        },
    },
]
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SCHEMAS}
# 第二階段（AGENT_DESIGN §4.2）：提案抽象名 → 實際工具的映射層。
# LLM 若以抽象名提出呼叫，伺服端映射到真實工具執行；trace 同時記錄 requested/executed。
TOOL_ALIASES = {
    "get_public_quote": "get_market_quote",
    "call_forecast": "post_forecast",
}
ALLOWED_ARG_KEYS = {
    "get_market_quote": {"crop_id", "market_id"},
    "post_forecast": {
        "crop_id", "market_id", "current_price", "price_unit", "observed_at", "mode",
        "previous_price", "previous_price_unit", "previous_observed_at",
    },
    "save_record": {"request_id"},
}


def resolve_tool_name(name: str) -> str | None:
    """白名單解析（含抽象別名）。回傳實際工具名；未知回 None。"""
    if name in TOOL_NAMES:
        return name
    return TOOL_ALIASES.get(name)

# ---------- S06：秘密遮罩（不能只截短） ----------

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"(?:Bearer|bearer)\s+[A-Za-z0-9_\-\.]{6,}"),
    re.compile(r"(?:api[_-]?key|token|secret)[\"':=]\s*[\"']?[A-Za-z0-9_\-\.]{6,}", re.IGNORECASE),
]


def mask_secrets(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("***", text)
    return text


# ---------- Provider 設定 ----------

@dataclass
class ProviderProfile:
    name: str
    kind: str  # "openai_compat" | "rule"
    base_url: str = ""
    model: str = ""
    api_key_env: str = ""
    timeout: float = 20.0
    max_tokens: int = 800
    temperature: float = 0.2
    max_tool_calls: int = 4
    max_turns: int = 4
    max_retries: int = 2
    total_timeout: float = 90.0
    cloud_fallback: bool = False
    description: str = ""


def load_profiles(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, ProviderProfile]:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    out = {}
    for name, p in (cfg.get("runtime", {}).get("profiles", {}) or {}).items():
        out[name] = ProviderProfile(
            name=name,
            **{k: v for k, v in p.items() if k in ProviderProfile.__dataclass_fields__ and k != "name"},
        )
    return out


def _profile_complete(prof: ProviderProfile) -> str:
    """完整配置驗證（S09）：回空字串=完整；否則回缺項原因碼。"""
    if prof.kind == "rule":
        return ""
    if not prof.base_url:
        return f"profile_base_url_missing:{prof.name}"
    if not prof.model:
        return f"profile_model_missing:{prof.name}"
    if prof.api_key_env and not os.environ.get(prof.api_key_env):
        return f"api_key_missing:{prof.api_key_env}"
    return ""


def resolve_active_profile(config_path: str | Path = DEFAULT_CONFIG) -> tuple[ProviderProfile | None, str]:
    """依 AIOT_AGENT_PROFILE 選 profile；配置不完整回原因（呼叫端須 503，不靜默降級）。"""
    profiles = load_profiles(config_path)
    want = os.environ.get("AIOT_AGENT_PROFILE", "rule")
    # Coding Plan is an explicit, loopback-only personal Hermes demonstration.
    # The regular product profile continues to use the general API endpoint.
    if want == "glm_zai_coding":
        prof = ProviderProfile(
            name=want, kind="openai_compat",
            base_url="https://api.z.ai/api/coding/paas/v4",
            model="glm-5.3-flash", api_key_env="AIOT_GLM_API_KEY",
            timeout=20, max_tokens=800, max_tool_calls=4, max_turns=4,
            max_retries=0, total_timeout=90, cloud_fallback=False,
            description="Local personal Hermes demonstration; not a public product deployment",
        )
        if os.environ.get("AIOT_LOCAL_HERMES_DEMO") != "1" or os.environ.get("AIOT_AGENT_FRAMEWORK") != "hermes":
            return prof, "local_hermes_demo_required"
    else:
        prof = profiles.get(want)
    if prof is None:
        return None, f"unknown_profile:{want}"
    if want in {"glm_zai", "glm_zai_coding"} and os.environ.get("AIOT_GLM_MODEL"):
        model = os.environ["AIOT_GLM_MODEL"].strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
            return prof, "profile_model_invalid"
        prof.model = model
    reason = _profile_complete(prof)
    if reason:
        return prof, reason
    return prof, ""


@dataclass
class ProviderResponse:
    content: str | None = None
    tool_calls: list = field(default_factory=list)
    finish_reason: str = ""


class OpenAICompatProvider:
    """OpenAI 相容 client。S06：上游錯誤 body 只遮罩後留內部，對外穩定碼。"""

    def __init__(self, profile: ProviderProfile):
        self.profile = profile

    def available(self) -> bool:
        return bool(self.profile.base_url and self.profile.model)

    def chat(self, messages: list, tools: list | None = None) -> ProviderResponse:
        payload = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": self.profile.temperature,
            "max_tokens": self.profile.max_tokens,
        }
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            f"{self.profile.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        key = os.environ.get(self.profile.api_key_env, "") if self.profile.api_key_env else ""
        if key:
            req.add_header("Authorization", f"Bearer {key}")

        last_code = None
        for attempt in range(self.profile.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.profile.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return self._parse(data)
            except urllib.error.HTTPError as e:
                # S06：body 僅遮罩後供內部診斷（本地日誌層），絕不進例外文字
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    body = ""
                _internal_note(f"upstream_http_{e.code} body_masked={mask_secrets(body)[:160]}")
                last_code = e.code
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except Exception as e:
                _internal_note(f"upstream_{type(e).__name__}")
                last_code = type(e).__name__
            if attempt < self.profile.max_retries:
                time.sleep(1.5 * (attempt + 1))
        # 對外穩定碼（不含任何上游 body）
        raise RuntimeError(f"provider_http_error:{last_code}" if isinstance(last_code, int) else f"provider_request_failed:{last_code}")

    @staticmethod
    def _parse(data: dict) -> ProviderResponse:
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        content = msg.get("content")
        if content is not None and not isinstance(content, str):
            content = None
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = None
            calls.append({"id": tc.get("id"), "name": fn.get("name"),
                          "arguments": args if isinstance(args, dict) else None})
        return ProviderResponse(content=content, tool_calls=calls,
                                finish_reason=(data.get("choices") or [{}])[0].get("finish_reason", ""))


def _internal_note(note: str) -> None:
    """內部診斷（遮罩後）；只進 stderr，不進回答/追蹤/保存。"""
    import sys
    print(f"[aiot-provider] {note}", file=sys.stderr)


# ---------- S03：可信查詢上下文 ----------

@dataclass
class TrustedContext:
    """由可信規則解析（parse_query）建立；LLM 工具參數必須與此一致。"""

    crop_id: str | None = None
    market_id: str | None = None
    current_price_jin: float | None = None
    price_unit: str | None = None
    observed_date: str | None = None  # YYYY-MM-DD（Asia/Taipei；後端提供）
    store_id: str | None = None       # 呼叫端店號；LLM 不得覆寫
    allowed_modes: tuple = ("without_last_week",)
    previous_price_jin: float | None = None
    previous_date: str | None = None
    forecast_input_valid: bool = True  # 手動建立的 context 相容；解析入口必須明確設值

    @classmethod
    def from_parsed(cls, parsed, store_id: str | None, today) -> "TrustedContext":
        from aiot_price.data.schema import to_taiwan_jin

        req = parsed.to_forecast_request()
        ctx = cls(store_id=store_id, forecast_input_valid=bool(req) and not parsed.unit_non_comparable)
        ctx.crop_id = parsed.crop_id
        ctx.market_id = parsed.market_id or "中義市場"
        if parsed.current_price is not None and parsed.price_unit in ("NTD_per_taiwan_jin", "NTD_per_kg"):
            ctx.current_price_jin = to_taiwan_jin(parsed.current_price, parsed.price_unit)
            ctx.price_unit = parsed.price_unit
        obs = parsed.observed_date or today
        ctx.observed_date = obs.isoformat() if hasattr(obs, "isoformat") else str(obs)
        if (
            parsed.previous_price is not None
            and parsed.previous_price_unit in ("NTD_per_taiwan_jin", "NTD_per_kg")
            and parsed.previous_date is not None
            and not parsed.b_reject_reason
        ):
            ctx.previous_price_jin = to_taiwan_jin(parsed.previous_price, parsed.previous_price_unit)
            ctx.previous_date = parsed.previous_date.isoformat() if hasattr(parsed.previous_date, "isoformat") else str(parsed.previous_date)
            ctx.allowed_modes = ("without_last_week", "with_last_week", "both")
        return ctx


def validate_args_against_context(name: str, args: dict | None, ctx: TrustedContext) -> tuple[bool, str, dict]:
    """S03：工具參數 vs 可信上下文。回 (ok, reason, 執行用參數)。

    允許：等價單位換算（換算成台斤後相等）；店號一律採用呼叫端值。
    拒絕：改價/改日期/換品項/換市場/無中生有上週價/啟用未允許模式。
    """
    if args is None:
        return False, "invalid_arguments", {}
    extra = set(args.keys()) - ALLOWED_ARG_KEYS[name]
    if extra:
        return False, f"invalid_argument_keys:{sorted(extra)[:3]}", {}

    from aiot_price.data.schema import to_taiwan_jin

    def _to_jin(price, unit):
        return to_taiwan_jin(price, unit) if unit in ("NTD_per_taiwan_jin", "NTD_per_kg") else None

    out = dict(args)

    if name == "get_market_quote":
        if args.get("crop_id") != ctx.crop_id:
            return False, "crop_mismatch_with_user_input", {}
        if args.get("market_id") != ctx.market_id:
            return False, "market_mismatch_with_user_input", {}
        return True, "", out

    if name == "save_record":
        rid = args.get("request_id")
        if not isinstance(rid, str) or not rid or len(rid) > 64:
            return False, "invalid_request_id", {}
        return True, "", out

    # quote/save preflight 可開放，但不能讓模型補出缺少的預測輸入。
    if not ctx.forecast_input_valid:
        return False, "forecast_input_missing_or_invalid", {}
    # post_forecast
    if args.get("crop_id") != ctx.crop_id:
        return False, "crop_mismatch_with_user_input", {}
    if args.get("market_id") != ctx.market_id:
        return False, "market_mismatch_with_user_input", {}
    mode = args.get("mode", "without_last_week")
    if mode not in ctx.allowed_modes:
        return False, "mode_not_allowed_by_user_input", {}
    # 日期：日期部分必須等於可信報價日
    obs = str(args.get("observed_at", ""))
    if obs[:10] != (ctx.observed_date or ""):
        return False, "observed_date_mismatch_with_user_input", {}
    # 今天價：換算台斤後必須與可信值一致（容差 0.01；允許合法單位換算）
    try:
        price_jin = _to_jin(args.get("current_price"), args.get("price_unit"))
    except Exception:
        return False, "current_price_not_comparable", {}
    if price_jin is None or ctx.current_price_jin is None or abs(price_jin - ctx.current_price_jin) > 0.01:
        return False, "current_price_mismatch_with_user_input", {}
    # 上週價：僅可信上下文存在時允許；值須一致；不可無中生有
    prev = args.get("previous_price")
    prev_obs = args.get("previous_observed_at")
    if (prev is not None or prev_obs is not None):
        if ctx.previous_price_jin is None or ctx.previous_date is None:
            return False, "previous_price_not_provided_by_user", {}
        try:
            prev_jin = _to_jin(prev, args.get("previous_price_unit"))
        except Exception:
            return False, "previous_price_not_comparable", {}
        if prev_jin is None or abs(prev_jin - ctx.previous_price_jin) > 0.01:
            return False, "previous_price_mismatch_with_user_input", {}
        if str(prev_obs or "")[:10] != ctx.previous_date:
            return False, "previous_date_mismatch_with_user_input", {}
    out.pop("store_id", None)  # 店號由呼叫端決定，不採 LLM 值
    if ctx.store_id:
        out["store_id"] = ctx.store_id
    return True, "", out


# ---------- 代理人迴圈（S03/S07） ----------

def agent_preflight_missing(parsed, save_gate: dict | None = None) -> list[str]:
    """有任一工具的可信輸入便可讓 LLM 選工具；各工具仍各自驗證。"""
    parsed.to_forecast_request()
    confirmed_save = (
        isinstance(save_gate, dict) and save_gate.get("confirmed") is True
        and isinstance(save_gate.get("request_id"), str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", save_gate["request_id"])
        and callable(save_gate.get("saver"))
    )
    if confirmed_save:
        return []
    if parsed.crop_id and not parsed.ambiguous_crops:
        # 未提供價格的行情查詢要求明確市場；已有完整店價沿用既有預設市場。
        if parsed.market_id or (not parsed.missing and not parsed.unit_non_comparable):
            return []
    return list(parsed.missing) or ["品項與參考市場"]


def tool_result_status(result, tool: str | None = None) -> tuple[bool, str | None]:
    """參數驗證之外的工具執行狀態；ok:false 即使無 error 仍是失敗。"""
    if not isinstance(result, dict):
        return False, "invalid_tool_result"
    error = result.get("error")
    explicit_failure = "ok" in result and result["ok"] is not True
    missing_success = tool in ("get_market_quote", "save_record") and result.get("ok") is not True
    missing_forecast = tool == "post_forecast" and not result.get("results")
    if error or explicit_failure or missing_success or missing_forecast:
        reason = error or result.get("reason") or "tool_execution_failed"
        return False, mask_secrets(str(reason))[:160]
    return True, None


def _public_trace(event: dict) -> dict:
    """只處理已選定的 trace 欄位，所有字串值（含拒絕理由與ID）均遮罩。"""
    event = dict(event)
    if str(event.get("validation", "")).startswith("rejected:"):
        # 不需要把被拒的任意欄位值回傳瀏覽器來說明驗證失敗。
        event["args"] = {}
    # 已知拒絕工具仍可定位；未知任意名称只保留安全摘要。
    known_denied = {"run_shell", "read_file", "modify_model", "read_secrets", "nonexistent_tool"}
    requested = event.get("requested")
    if requested and resolve_tool_name(requested) is None and requested not in known_denied:
        event["requested"] = "unknown_tool"
        if str(event.get("error", "")).startswith("unknown_tool:"):
            event["error"] = "unknown_tool"
    def clean(value):
        if isinstance(value, str):
            return mask_secrets(value)[:160]
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return clean(event)

def _execute_tool(tools: AgentTools, name: str, args: dict | None, ctx: TrustedContext, save_gate: dict | None = None) -> dict:
    """白名單執行（含別名解析與 save_record 使用者確認門）。

    save_gate 由 API 層組成：{"request_id": <客戶端確認的 id>, "confirmed": True,
    "saver": callable(request_id)->dict}。模型自訂參數不可繞過——request_id 必須與
    客戶端確認值相符，保存內容由伺服器暫存之真實推論結果決定。
    """
    canonical = resolve_tool_name(name)
    if canonical is None:
        return {"ok": False, "error": f"unknown_tool:{name}"}
    ok, reason, exec_args = validate_args_against_context(canonical, args, ctx)
    if not ok:
        return {"ok": False, "error": f"input_fidelity_rejected:{reason}"}
    try:
        if canonical == "get_market_quote":
            return tools.get_market_quote(exec_args["crop_id"], exec_args["market_id"])
        if canonical == "save_record":
            if not isinstance(save_gate, dict) or save_gate.get("confirmed") is not True:
                return {"ok": False, "error": "save_requires_user_confirmation"}
            if exec_args.get("request_id") != save_gate.get("request_id"):
                return {"ok": False, "error": "save_request_id_not_confirmed_by_user"}
            saver = save_gate.get("saver")
            if not callable(saver):
                return {"ok": False, "error": "save_saver_unavailable"}
            result = saver(exec_args["request_id"])
            return result if isinstance(result, dict) else {"ok": False, "error": "save_saver_invalid_result"}
        return tools.post_forecast(exec_args)
    except Exception as e:
        return {"ok": False, "error": f"tool_execution_error:{type(e).__name__}"}


def _fallback_answer(parsed, forecast_result, err: str, tool_outputs: dict | None = None) -> str:
    if forecast_result:
        return RuleBackend().reply(parsed, {"forecast": forecast_result})
    outputs = tool_outputs or {}
    if outputs.get("save_ok") is True:
        return "已依您的確認保存先前預測，供到期核對。"
    quote = outputs.get("market_quote")
    if isinstance(quote, dict) and quote.get("ok") is True:
        price = quote.get("price")
        unit = {"NTD_per_taiwan_jin": "台斤", "NTD_per_kg": "公斤"}.get(quote.get("unit"))
        observed = quote.get("observed_date")
        if (isinstance(price, (float, int)) and not isinstance(price, bool) and math.isfinite(price)
                and price > 0 and unit and isinstance(observed, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed)):
            return (f"最新公開行情為 {price:g} 元／{unit}（觀測日 {observed}）。"
                    "此為市場均價，非店價。")
    return "代理人後端暫時無法回應，請稍後再試，或直接使用表單查詢菜價預測。"


def run_agent_loop(
    engine,
    query: str,
    profile: ProviderProfile,
    store_id: str | None = None,
    today=None,
    save_gate: dict | None = None,
) -> dict:
    provider = OpenAICompatProvider(profile)
    base = {
        "provider": profile.name, "model": profile.model, "runtime": "openai_compat",
        "backend_used": profile.name, "degraded": False, "degraded_reason": None,
    }
    parsed = parse_query(query, today=today)
    ctx = TrustedContext.from_parsed(parsed, store_id, today=today) if today else TrustedContext.from_parsed(parsed, store_id, today=parsed.today)

    if agent_preflight_missing(parsed, save_gate):
        return {**base, "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": RuleBackend().reply(parsed, {}),
                "backend_used": "rule", "degraded": True, "degraded_reason": "missing_input_skip_llm"}

    if not provider.available():
        return {**base, "backend_used": "rule", "degraded": True, "degraded_reason": "provider_not_configured",
                "parsed": _pd(parsed), "tool_trace": [], "forecast": None,
                "answer": _fallback_answer(parsed, None, "not_configured")}

    system = load_system_prompt(strict=True) + (
        f"\n\n本次查詢可信資訊（不得修改）：品項 {ctx.crop_id}、參考市場 {ctx.market_id}、"
        f"今天價格 {parsed.current_price} {parsed.price_unit}、報價日 {ctx.observed_date}（Asia/Taipei）。"
    )
    if ctx.previous_price_jin is not None:
        system += f" 上週價（可比）{parsed.previous_price} {parsed.previous_price_unit}、日期 {ctx.previous_date}。"
    else:
        system += " 使用者未提供可比的上週價：不得自行填入任何 previous 欄位。"
    system += (
        "\n你只有 get_market_quote、post_forecast 與 save_record 三個工具。需要預測時必須以與上述可信資訊完全一致的參數呼叫 post_forecast，"
        "不得修改任何數值、日期、品項或市場；回答只能引用工具結果的數字。"
        "save_record 僅在使用者已於介面確認保存後才會成功；未確認時請告知使用者以介面的保存按鈕確認。"
    )
    if isinstance(save_gate, dict) and save_gate.get("confirmed") is True and save_gate.get("request_id"):
        # 使用者已於介面確認保存「先前查詢」的預測：注入可信 request_id 供 LLM 引用
        #（值仍由 gate 嚴格比對；LLM 換 id 會被拒）。
        system += f"\n使用者已在介面確認保存先前預測 request_id={save_gate['request_id']}；如要保存，請以該 id 呼叫 save_record。"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]
    trace: list[dict] = []
    forecast_result = None
    quote_result = None
    save_ok = False
    final_text = None
    started = time.monotonic()
    budget_exhausted = False

    try:
        for turn in range(profile.max_turns):
            if time.monotonic() - started > profile.total_timeout:
                budget_exhausted = True
                break
            resp = provider.chat(messages, tools=TOOL_SCHEMAS)
            if not resp.tool_calls:
                final_text = (resp.content or "").strip()
                break
            # S07：assistant 宣告保持模型原樣；每個宣告的 tool_call_id 都會有回覆
            messages.append({
                "role": "assistant",
                "content": resp.content or "",
                "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": json.dumps(c["arguments"] or {}, ensure_ascii=False)}}
                    for c in resp.tool_calls
                ],
            })
            remaining = profile.max_tool_calls - len(trace)
            for i, call in enumerate(resp.tool_calls):
                requested = call["name"]
                canonical = resolve_tool_name(requested)
                if canonical is None:
                    # 不在白名單（含別名）：記錄拒絕、回協議錯誤，絕不執行
                    trace.append(_public_trace({
                        "requested": requested, "tool": canonical, "tool_call_id": call["id"],
                        "args": {}, "validation": "rejected:not_whitelisted",
                        "ok": False, "error": f"unknown_tool:{requested}",
                    }))
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps({"ok": False, "error": f"unknown_tool:{requested}"}, ensure_ascii=False)})
                    continue
                if i >= remaining:
                    # S07：預算耗盡不再執行，但仍回覆協議訊息（不留懸空 ID）
                    trace.append(_public_trace({
                        "requested": requested, "tool": canonical, "tool_call_id": call["id"],
                        "args": {k: (call["arguments"] or {}).get(k) for k in ("crop_id", "market_id", "current_price", "mode", "request_id")},
                        "validation": "rejected:tool_budget_exceeded",
                        "ok": False, "error": "tool_budget_exceeded",
                    }))
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps({"ok": False, "error": "tool_budget_exceeded"}, ensure_ascii=False)})
                    budget_exhausted = True
                    continue
                result = _execute_tool(AgentTools(engine), requested, call["arguments"], ctx, save_gate=save_gate)
                valid, validation_reason, _ = validate_args_against_context(canonical, call["arguments"], ctx)
                executed_ok, err = tool_result_status(result, canonical)
                # 確認門屬授權驗證；引擎、行情或 saver 執行失敗則參數仍可能被接受。
                if valid and err in ("save_requires_user_confirmation", "save_request_id_not_confirmed_by_user", "save_saver_unavailable"):
                    valid, validation_reason = False, err
                trace.append(_public_trace({
                    "requested": requested, "tool": canonical, "tool_call_id": call["id"],
                    "args": {k: (call["arguments"] or {}).get(k) for k in ("crop_id", "market_id", "current_price", "mode", "request_id")},
                    "validation": "accepted" if valid else f"rejected:{validation_reason}",
                    "ok": executed_ok, "error": err,
                }))
                if canonical == "post_forecast" and executed_ok:
                    forecast_result = result
                if canonical == "get_market_quote" and executed_ok and result.get("ok"):
                    quote_result = result
                if canonical == "save_record" and executed_ok and result.get("ok"):
                    save_ok = True
                # S07：完整 JSON 回送，不從中間截斷（上限內的工具結果本就精簡）
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, ensure_ascii=False, default=str)})
            if budget_exhausted:
                break
    except RuntimeError as e:
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_result,
                "backend_used": "rule", "degraded": True, "degraded_reason": str(e)[:80],
                "answer": _fallback_answer(parsed, forecast_result, str(e))}

    tool_outputs = {"forecast": forecast_result, "market_quote": quote_result, "save_ok": save_ok}
    # save-only 對話（已確認保存、無預測主張）也允許回答；數字防線由驗證器把關
    tool_ok = bool(forecast_result and forecast_result.get("results") and not forecast_result.get("error")) or bool(
        quote_result and quote_result.get("ok")
    ) or save_ok
    if not tool_ok:
        reason = "tool_budget_exhausted" if budget_exhausted else "no_tool_result_skip_llm"
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_result,
                "backend_used": "rule", "degraded": True, "degraded_reason": reason,
                "answer": _fallback_answer(parsed, None, reason, tool_outputs)}

    ok, why = validate_qwen_answer(final_text or "", tool_outputs)
    if not ok:
        return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_result,
                "backend_used": "rule", "degraded": True, "degraded_reason": f"llm_output_rejected:{why}",
                "answer": _fallback_answer(parsed, forecast_result, why, tool_outputs)}

    return {**base, "parsed": _pd(parsed), "tool_trace": trace, "forecast": forecast_result, "answer": final_text}


def _pd(parsed) -> dict:
    return {
        "crop_id": parsed.crop_id, "current_price": parsed.current_price,
        "price_unit": parsed.price_unit, "market_id": parsed.market_id,
        "previous_price": parsed.previous_price,
        "mode": (parsed.to_forecast_request() or {}).get("mode"),
        "missing": parsed.missing, "unit_non_comparable": parsed.unit_non_comparable,
    }
