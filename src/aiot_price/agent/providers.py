"""供應商無關的代理人後端（第四輪 D41：GLM API 先行、可切換本機 Qwen3.8-27B）。

分層（docs/AGENT_RUNTIME_DIRECTION.md §2）：
- 語言模型供應端：OpenAICompatProvider——GLM（Z.AI/BigModel）與自架 Qwen 推論端點
  共用同一 OpenAI 相容 /chat/completions 協定；差異只在 base_url/model/key_env。
- 代理人執行框架：run_agent_loop()——LLM 生成 tool_calls → 白名單＋參數驗證 →
  真菜價工具執行 → 結果回送 → 受保護的最終回答（validate_qwen_answer）。
- 菜價模型：AgentTools（與 HTTP API 同一 ForecastEngine），本層不含任何菜價計算。

安全邊界：
- 工具白名單只有 get_market_quote 與 post_forecast；未知工具回錯誤訊息給模型，不執行。
- 參數鍵白名單＋語意驗證走 ForecastEngine._validate（與 API 共用）。
- 對話輪數／工具呼叫次數／超時／重試有上限；金鑰只從環境變數讀，絕不進錯誤訊息或追蹤。
- 本機（qwen_local）模式失敗時不自動切換雲端（cloud_fallback 預設關閉）。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .service import RuleBackend, load_system_prompt, validate_qwen_answer
from .tools import AgentTools, parse_query

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "agent_model.yaml"

# ---------- 工具白名單契約（供 LLM function calling；與 Hermes MCP 共用語意） ----------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_quote",
            "description": "查最新公開市場行情（臺中，元/台斤）。非預測；回傳觀測日與價格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"],
                                 "description": "cabbage=甘藍（高麗菜）, bok_choy=青江白菜, sponge_gourd=絲瓜"},
                    "market_id": {"type": "string", "description": "臺中市場名稱，如 中義市場"},
                },
                "required": ["crop_id", "market_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_forecast",
            "description": "菜價 7/14 天預測（A/B 兩模式）。需要今天價格與單位；上週價可選。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"]},
                    "market_id": {"type": "string"},
                    "current_price": {"type": "number", "description": "今天價格（正數）"},
                    "price_unit": {"type": "string", "enum": ["NTD_per_taiwan_jin", "NTD_per_kg"]},
                    "observed_at": {"type": "string", "description": "ISO8601 含時區，如 2026-10-04T10:00:00+08:00"},
                    "mode": {"type": "string", "enum": ["without_last_week", "with_last_week", "both"]},
                    "previous_price": {"type": "number", "description": "上週同店同規格價（選填）"},
                    "previous_price_unit": {"type": "string", "enum": ["NTD_per_taiwan_jin", "NTD_per_kg"]},
                    "previous_observed_at": {"type": "string", "description": "上週實際日期（選填）"},
                },
                "required": ["crop_id", "market_id", "current_price", "price_unit", "observed_at", "mode"],
            },
        },
    },
]
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SCHEMAS}
# 參數鍵白名單（拒絕多餘鍵，避免注入）
ALLOWED_ARG_KEYS = {
    "get_market_quote": {"crop_id", "market_id"},
    "post_forecast": {
        "crop_id", "market_id", "current_price", "price_unit", "observed_at", "mode",
        "previous_price", "previous_price_unit", "previous_observed_at", "store_id",
        "specification", "previous_specification",
    },
}


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
    cloud_fallback: bool = False  # 本機模式預設關閉；未明確啟用不得偷切雲端


def load_profiles(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, ProviderProfile]:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    out = {}
    for name, p in (cfg.get("runtime", {}).get("profiles", {}) or {}).items():
        out[name] = ProviderProfile(name=name, **{k: v for k, v in p.items() if k in ProviderProfile.__dataclass_fields__ and k != "name"})
    return out


def resolve_active_profile(config_path: str | Path = DEFAULT_CONFIG) -> tuple[ProviderProfile | None, str]:
    """依 AIOT_AGENT_PROFILE 環境變數選 profile；預設 rule（無 LLM，安全）。"""
    profiles = load_profiles(config_path)
    want = os.environ.get("AIOT_AGENT_PROFILE", "rule")
    prof = profiles.get(want)
    if prof is None:
        return None, f"unknown_profile:{want}"
    if prof.kind == "openai_compat" and prof.api_key_env and not os.environ.get(prof.api_key_env):
        # 金鑰未設：不硬連（不把缺 key 的 provider 當可用）；回 reason 由呼叫端降級
        return prof, f"api_key_missing:{prof.api_key_env}"
    return prof, ""


@dataclass
class ProviderResponse:
    content: str | None = None
    tool_calls: list = field(default_factory=list)  # [{id, name, arguments(dict)}]
    finish_reason: str = ""
    raw_usage: dict = field(default_factory=dict)


class OpenAICompatProvider:
    """OpenAI 相容 chat/completions 客戶端（GLM 與自架 Qwen 端點共用）。"""

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

        last_err = None
        for attempt in range(self.profile.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.profile.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return self._parse(data)
            except urllib.error.HTTPError as e:
                # 429/5xx 重試；4xx 不重試。錯誤訊息絕不含金鑰。
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")[:200]
                except Exception:
                    pass
                last_err = f"http_{e.code}:{body}"
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except Exception as e:  # timeout 等
                last_err = f"{type(e).__name__}"
            if attempt < self.profile.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"provider_request_failed:{last_err}")

    @staticmethod
    def _parse(data: dict) -> ProviderResponse:
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        content = msg.get("content")
        if content is not None and not isinstance(content, str):
            content = None  # R02：null/非字串不字串化
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = None
            calls.append({"id": tc.get("id"), "name": fn.get("name"), "arguments": args if isinstance(args, dict) else None})
        return ProviderResponse(
            content=content,
            tool_calls=calls,
            finish_reason=(data.get("choices") or [{}])[0].get("finish_reason", ""),
            raw_usage=data.get("usage") or {},
        )


# ---------- 代理人迴圈（真正 tool_calls → 驗證 → 真工具 → 回送） ----------

def _execute_tool(tools: AgentTools, name: str, args: dict | None) -> dict:
    """白名單＋參數驗證後執行真工具；回傳 dict 給 LLM（絕不丟例外出去）。"""
    if name not in TOOL_NAMES:
        return {"ok": False, "error": f"unknown_tool:{name}（白名單外工具不可用）"}
    if args is None:
        return {"ok": False, "error": "invalid_arguments:arguments 不是合法 JSON 物件"}
    extra = set(args.keys()) - ALLOWED_ARG_KEYS[name]
    if extra:
        return {"ok": False, "error": f"invalid_argument_keys:{sorted(extra)[:5]}"}
    try:
        if name == "get_market_quote":
            return tools.get_market_quote(args["crop_id"], args["market_id"])
        # post_forecast：直接交給引擎（_validate 語意驗證與 API 共用；錯誤受控回傳）
        result = tools.post_forecast(args)
        return result
    except Exception as e:
        return {"ok": False, "error": f"tool_execution_error:{type(e).__name__}"}


def run_agent_loop(
    engine,
    query: str,
    profile: ProviderProfile,
    store_id: str | None = None,
    today=None,
) -> dict:
    """真代理人流程。回傳與 handle_agent_query 相容並附加 provider 資訊。

    R01 原則同樣適用：缺必要輸入或無有效工具結果時不產生預測成功回答。
    """
    provider = OpenAICompatProvider(profile)
    base = {
        "provider": profile.name,
        "model": profile.model,
        "runtime": "openai_compat",
        "backend_used": profile.name,
        "degraded": False,
        "degraded_reason": None,
    }
    if not provider.available():
        return {**base, "backend_used": "rule", "degraded": True,
                "degraded_reason": "provider_not_configured"}

    parsed = parse_query(query, today=today)
    tools = AgentTools(engine)

    # R01 短路：缺必要輸入不進 LLM 迴圈（省請求且防捏造）
    if parsed.missing or parsed.unit_non_comparable:
        rule = RuleBackend().reply(parsed, {})
        return {**base, "parsed": _parsed_dict(parsed), "tool_trace": [],
                "forecast": None, "answer": rule,
                "backend_used": "rule", "degraded": True, "degraded_reason": "missing_input_skip_llm"}

    system = load_system_prompt(strict=True)
    messages = [
        {"role": "system", "content": system + "\n\n你只有兩個工具可用：get_market_quote 與 post_forecast。需要預測時必須呼叫 post_forecast 取得真實結果後才能回答；不得自行計算或編造任何數字。"},
        {"role": "user", "content": query},
    ]
    trace: list[dict] = []
    forecast_result = None
    final_text = None

    try:
        for turn in range(profile.max_turns):
            resp = provider.chat(messages, tools=TOOL_SCHEMAS)
            if not resp.tool_calls:
                final_text = (resp.content or "").strip()
                break
            messages.append({
                "role": "assistant",
                "content": resp.content or "",
                "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"],
                                  "arguments": json.dumps(c["arguments"] or {}, ensure_ascii=False)}}
                    for c in resp.tool_calls
                ],
            })
            n_this_turn = 0
            for call in resp.tool_calls[: max(1, profile.max_tool_calls - len(trace))]:
                n_this_turn += 1
                result = _execute_tool(tools, call["name"], call["arguments"])
                trace.append({"tool": call["name"], "args": {k: (call["arguments"] or {}).get(k) for k in ("crop_id", "market_id", "current_price", "mode")}, "ok": not (isinstance(result, dict) and result.get("error"))})
                if call["name"] == "post_forecast" and isinstance(result, dict) and not result.get("error"):
                    forecast_result = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str)[:4000],
                })
    except RuntimeError as e:
        # provider 失敗：本機模式不自動切雲端；回明確錯誤（已取得的工具結果仍可回）
        return {**base, "parsed": _parsed_dict(parsed), "tool_trace": trace,
                "forecast": forecast_result, "backend_used": "rule", "degraded": True,
                "degraded_reason": str(e)[:120],
                "answer": _fallback_answer(parsed, forecast_result, tools, str(e)[:80])}

    # R01：沒有有效工具結果 → 最終文字必須不含預測主張；直接規則化
    tool_ok = bool(forecast_result and forecast_result.get("results"))
    if not tool_ok:
        rule = RuleBackend().reply(parsed, {})
        return {**base, "parsed": _parsed_dict(parsed), "tool_trace": trace,
                "forecast": forecast_result, "backend_used": "rule",
                "degraded": True, "degraded_reason": "no_tool_result_skip_llm",
                "answer": rule}

    ok, why = validate_qwen_answer(final_text or "", {"forecast": forecast_result})
    if not ok:
        rule = RuleBackend().reply(parsed, {"forecast": forecast_result})
        return {**base, "parsed": _parsed_dict(parsed), "tool_trace": trace,
                "forecast": forecast_result, "backend_used": "rule",
                "degraded": True, "degraded_reason": f"llm_output_rejected:{why}",
                "answer": rule}

    return {**base, "parsed": _parsed_dict(parsed), "tool_trace": trace,
            "forecast": forecast_result, "answer": final_text}


def _parsed_dict(parsed) -> dict:
    return {
        "crop_id": parsed.crop_id, "current_price": parsed.current_price,
        "price_unit": parsed.price_unit, "market_id": parsed.market_id,
        "previous_price": parsed.previous_price, "mode": (parsed.to_forecast_request() or {}).get("mode"),
        "missing": parsed.missing, "unit_non_comparable": parsed.unit_non_comparable,
    }


def _fallback_answer(parsed, forecast_result, tools, err: str) -> str:
    if forecast_result:
        return RuleBackend().reply(parsed, {"forecast": forecast_result})
    return f"代理人後端連線失敗（{err}）。請稍後再試，或直接使用表單查詢菜價預測。"
