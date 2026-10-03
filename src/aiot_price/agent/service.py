"""代理人服務（T26）：自然語言查詢 → 確定性解析 → 有限工具 → 忠實回答。

後端可插換：
- RuleBackend：本機規則模板（無 LLM；回答只引用工具結果數字）。
- QwenBackend：SERVER 上的 Qwen（OpenAI 相容 chat API）。LLM 只負責「解釋」，
  工具參數由規則解析產生、工具結果直接放入訊息；系統提示（configs/agent_prompt.md）
  禁止編造數字/機率/原因。Qwen 不可用時自動降級 RuleBackend（T27 降級要求）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .tools import AgentTools, ParsedQuery, ToolCallLimiter, parse_query

# F02 修正：service.py 在 src/aiot_price/agent/ 下，專案根是 parents[3]
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[3] / "configs" / "agent_prompt.md"


class PromptUnavailable(RuntimeError):
    """提示檔缺失或不完整：QwenBackend 不得以空提示上線。"""


def load_system_prompt(path: str | Path = DEFAULT_PROMPT_PATH, *, strict: bool = False) -> str:
    """載入系統提示；strict=True 時缺失／空檔丟 PromptUnavailable（不默空）。"""
    p = Path(path)
    if not p.exists():
        if strict:
            raise PromptUnavailable(f"代理人系統提示檔不存在：{p}")
        return ""
    text = p.read_text(encoding="utf-8").strip()
    if strict and len(text) < 100:
        raise PromptUnavailable(f"代理人系統提示過短（{len(text)} 字），拒絕以空提示運作")
    return text


# ---------- F02：Qwen 輸出真值對照驗證（提示不能代替輸出驗證） ----------

import re as _re

_EXAGGERATION_RE = _re.compile(r"必定|保證|絕對會|機率是|的機率|可信度|準確率|已驗證|已經驗證|一定會")
_PCT_RE = _re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_DATE_RE = _re.compile(r"\d{4}-\d{2}-\d{2}")
_PRICE_RE = _re.compile(r"(\d+(?:\.\d+)?)\s*元")
_DIRECTION_WORDS = {
    "up": ("上漲", "漲"),
    "down": ("下跌", "跌"),
    "flat": ("持平", "平"),
}
_OPPOSITE = {
    "up": ("下跌", "跌"),
    "down": ("上漲", "漲"),
    # 工具說持平的期限，講「漲」或「跌」都是方向衝突
    "flat": ("上漲", "漲", "下跌", "跌"),
}


def validate_qwen_answer(answer: str, tool_outputs: dict) -> tuple[bool, str]:
    """對照工具真值驗證 Qwen 文字。回 (ok, reason)；失敗即丟棄改用規則回答。

    檢查：誇大詞黑名單、百分比/日期/價格必須來自工具結果、
    各期限句中不得出現與工具相反的方向詞。
    """
    if not answer or not answer.strip():
        return False, "empty_answer"
    forecast = tool_outputs.get("forecast") or {}
    if forecast.get("error"):
        return True, ""  # 工具失敗情境由規則回答處理，不經 Qwen

    if _EXAGGERATION_RE.search(answer):
        return False, "exaggeration_or_probability_claim"

    # 允許數字集合：各結果的相對變化(%)、價格估計、公開截止年月日
    allowed_pct: set[float] = set()
    allowed_price: set[float] = set()
    allowed_dates: set[str] = set()
    horizon_dir: dict[int, str] = {}
    for key in ("results", "results_without_last_week", "results_with_last_week"):
        for r in forecast.get(key) or []:
            pct = r.get("relative_change_estimate")
            if isinstance(pct, (int, float)):
                allowed_pct.add(round(pct * 100, 1))
            pe = r.get("price_estimate")
            if isinstance(pe, (int, float)):
                allowed_price.add(round(float(pe), 1))
            allowed_dates.add(str(r.get("target_date")))
            h = r.get("horizon_days")
            if h and key == "results":
                horizon_dir[int(h)] = r.get("direction")
    for d in (forecast.get("public_data_cutoff"),):
        if d:
            allowed_dates.add(str(d))
    # 觀察起點日（含日期部分的字串）也允許出現在解釋文字
    ioa = forecast.get("input_observed_at")
    if ioa:
        allowed_dates.add(str(ioa)[:10])

    for m in _PCT_RE.finditer(answer):
        v = round(float(m.group(1)), 1)
        # 與任一允許值相差 <=0.15 視為同一數字的排版差
        if not any(abs(v - a) <= 0.15 for a in allowed_pct):
            return False, f"unverified_percentage:{v}"
    for m in _DATE_RE.finditer(answer):
        if m.group(0) not in allowed_dates:
            return False, f"unverified_date:{m.group(0)}"
    for m in _PRICE_RE.finditer(answer):
        v = round(float(m.group(1)), 1)
        if not any(abs(v - a) <= 0.15 for a in allowed_price):
            return False, f"unverified_price:{v}"

    # 方向一致性：含「N 天」的句子不得使用與工具相反的方向詞
    for sent in _re.split(r"[。\n；;]", answer):
        for h, d in horizon_dir.items():
            if f"{h} 天" in sent or f"{h}天" in sent:
                for opp in _OPPOSITE.get(d, ()):
                    if opp in sent:
                        return False, f"direction_conflict_h{h}"
    return True, ""


class AgentBackend(Protocol):
    name: str

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str: ...


class RuleBackend:
    """規則模板回答：逐字引用工具結果，不生成任何工具外的數字或原因。"""

    name = "rule"

    _DIRECTION_TEXT = {"up": "可能上漲", "flat": "大致持平", "down": "可能下跌", "insufficient_data": "資料不足"}

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str:
        if parsed.missing:
            need = "、".join(parsed.missing)
            hint = "（例：高麗菜 一斤32）" if "計價單位" in need or "今天價格" in need else ""
            return f"還缺必要資訊：{need}。請補充品項、今天價格與計價單位{hint}。"
        if parsed.unit_non_comparable:
            return "「一顆／一把」這類計價沒有重量資訊，無法和市場每斤均價比較。請改輸入每台斤或每公斤價格。"

        forecast = tool_outputs.get("forecast")
        if not forecast or forecast.get("error"):
            err = (forecast or {}).get("error") or {}
            return f"目前無法提供預測：{err.get('message', '工具呼叫失敗')}。請確認品項與市場，或稍後再試。"

        crop_name = parsed.crop_text or parsed.crop_id
        lines = []
        # F01：解析層已判定 B 不可比時，把原因與補充提示講清楚（明確回 A＋如何補）
        if parsed.b_reject_reason:
            lines.append(f"（{parsed.b_reject_reason}）")
        lines.append(
            f"{crop_name}（參考市場：{forecast['market_id']}），從今天 {forecast['input_observed_at'][:10]} 起算："
        )
        results = forecast.get("results") or []
        ab = forecast.get("results_with_last_week") or []
        for r in results:
            pct = r.get("relative_change_estimate")
            pct_text = f"{pct:+.1%}" if isinstance(pct, (int, float)) else "—"
            est = r.get("price_estimate")
            est_text = f"，約 {est:g} 元" if isinstance(est, (int, float)) else ""
            lines.append(
                f"• {r['horizon_days']} 天後（{r['target_date']}）：{self._DIRECTION_TEXT.get(r['direction'], r['direction'])}（{pct_text}{est_text}）"
            )
        if ab:
            lines.append("有上週價格的對照（B，實驗性規則、未經同店驗證）：")
            for r in ab:
                pct = r.get("relative_change_estimate")
                pct_text = f"{pct:+.1%}" if isinstance(pct, (int, float)) else "—"
                lines.append(f"• {r['horizon_days']} 天後：{self._DIRECTION_TEXT.get(r['direction'], r['direction'])}（{pct_text}）")
        lines.append(
            f"（公開行情截止 {forecast['public_data_cutoff']}；模型 {forecast['model_version']}；點估計僅供參考，非同店驗證）"
        )
        return "\n".join(lines)


@dataclass
class BackendResult:
    """一次回覆的實際執行狀態（F07：規則結果不得標為 Qwen 成功）。"""

    answer: str
    backend_used: str  # "qwen" | "rule"——實際產出文字的後端
    degraded: bool = False
    degraded_reason: str | None = None


class QwenBackend:
    """SERVER Qwen 後端：OpenAI 相容 /chat/completions；只做解釋層。

    F02/F07 修正：
    - 提示檔缺失／過短 → 不上線（available()=False，安全降級規則後端），不默空提示。
    - Qwen 文字經 validate_qwen_answer() 對照工具真值；驗證失敗丟棄並降級。
    - 降級時 BackendResult 明示 backend_used="rule" 與原因。
    """

    name = "qwen"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "AIOT_QWEN_API_KEY",
        timeout: float = 10.0,
        prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    ):
        self.base_url = base_url or os.environ.get("AIOT_QWEN_BASE_URL", "")
        self.model = model or os.environ.get("AIOT_QWEN_MODEL", "")
        self.api_key_env = api_key_env
        self.timeout = timeout
        try:
            self.system_prompt = load_system_prompt(prompt_path, strict=True)
        except PromptUnavailable:
            self.system_prompt = ""

    def available(self) -> bool:
        # F02：連線設定與提示檔都就緒才算可用
        return bool(self.base_url and self.model and self.system_prompt)

    def reply_result(self, parsed: ParsedQuery, tool_outputs: dict) -> BackendResult:
        if not self.available():
            reason = "qwen_not_configured" if not (self.base_url and self.model) else "qwen_prompt_unavailable"
            return BackendResult(RuleBackend().reply(parsed, tool_outputs), "rule", True, reason)
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        "使用者問題與工具結果如下。請依系統規則回答，只能引用工具結果的數字。\n\n"
                        f"工具結果（JSON）：\n{json.dumps(tool_outputs, ensure_ascii=False, default=str)}"
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        key = os.environ.get(self.api_key_env)
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            answer = str(data["choices"][0]["message"]["content"]).strip()
        except Exception as e:
            return BackendResult(
                RuleBackend().reply(parsed, tool_outputs), "rule", True, f"qwen_request_failed:{type(e).__name__}"
            )
        ok, why = validate_qwen_answer(answer, tool_outputs)
        if not ok:
            return BackendResult(
                RuleBackend().reply(parsed, tool_outputs), "rule", True, f"qwen_output_rejected:{why}"
            )
        return BackendResult(answer, "qwen", False, None)

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str:
        return self.reply_result(parsed, tool_outputs).answer


def handle_agent_query(
    engine,
    query: str,
    store_id: str | None = None,
    backend: AgentBackend | None = None,
    today=None,
) -> dict:
    """完整代理人流程：解析→工具→回答；回傳含匿名追蹤紀錄（T26 驗收）。"""
    backend = backend or RuleBackend()
    parsed = parse_query(query, today=today)
    tools = AgentTools(engine)
    limiter = ToolCallLimiter()
    trace: list[dict] = []

    tool_outputs: dict = {}
    # 工具1：若有品項，先查最新行情（供回答引用；失敗不阻斷）
    if parsed.crop_id and parsed.market_id and limiter.check():
        quote = tools.get_market_quote(parsed.crop_id, parsed.market_id)
        tool_outputs["market_quote"] = quote
        trace.append({"tool": "get_market_quote", "args": {"crop_id": parsed.crop_id, "market_id": parsed.market_id}, "ok": quote.get("ok", False)})
    elif parsed.crop_id and not parsed.market_id and limiter.check():
        quote = tools.get_market_quote(parsed.crop_id, "中義市場")
        tool_outputs["market_quote"] = quote
        trace.append({"tool": "get_market_quote", "args": {"crop_id": parsed.crop_id, "market_id": "中義市場（預設）"}, "ok": quote.get("ok", False)})

    # 工具2：預測（必要欄位齊才呼叫）
    req = parsed.to_forecast_request(store_id=store_id)
    if req is not None and limiter.check():
        forecast = tools.post_forecast(req)
        tool_outputs["forecast"] = forecast
        trace.append({"tool": "post_forecast", "args": {k: req.get(k) for k in ("crop_id", "market_id", "current_price", "price_unit", "mode")}, "ok": not forecast.get("error")})
    else:
        tool_outputs["forecast"] = None

    # F02/F07：實際執行的後端與降級狀態；結構化 forecast 真值獨立回傳給前端
    if hasattr(backend, "reply_result"):
        br = backend.reply_result(parsed, tool_outputs)
    else:
        br = BackendResult(backend.reply(parsed, tool_outputs), getattr(backend, "name", "rule"))
    return {
        "backend": getattr(backend, "name", "unknown"),
        "backend_used": br.backend_used,
        "degraded": br.degraded,
        "degraded_reason": br.degraded_reason,
        "forecast": tool_outputs.get("forecast"),
        "parsed": {
            "crop_id": parsed.crop_id,
            "current_price": parsed.current_price,
            "price_unit": parsed.price_unit,
            "market_id": parsed.market_id,
            "previous_price": parsed.previous_price,
            "mode": (req or {}).get("mode"),
            "missing": parsed.missing,
            "unit_non_comparable": parsed.unit_non_comparable,
        },
        "tool_trace": trace,
        "answer": br.answer,
    }
