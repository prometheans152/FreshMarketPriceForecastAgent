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

_EXAGGERATION_RE = _re.compile(r"必定|保證|絕對會|機率是|的機率|可信度|準確率|已驗證|已經驗證|一定會|已通過")
_PCT_RE = _re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_DATE_RE = _re.compile(r"\d{4}-\d{2}-\d{2}")
_PRICE_RE = _re.compile(r"(\d+(?:\.\d+)?)\s*元")
# 期限詞（含口語「下週」；14 天系列先列，避免「兩週」被「週」類誤配）
_HORIZON_WORDS = [
    (14, _re.compile(r"14\s*天|十四\s*天|兩週|两周|二週|二周|兩個禮拜|二個禮拜|兩禮拜|下下週|下下周")),
    (7, _re.compile(r"7\s*天|七\s*天|一週|一周|一個禮拜|一禮拜|下週|下周")),
]
_OPPOSITE = {
    "up": ("下跌", "跌", "大跌"),
    "down": ("上漲", "漲", "大漲"),
    "flat": ("上漲", "漲", "大漲", "下跌", "跌", "大跌", "大漲"),
}
_B_MARK_RE = _re.compile(r"B\s*模式|實驗性|使用上週|加上上週|有上週")
_A_MARK_RE = _re.compile(r"A\s*模式|未使用上週|不含上週")
_KG_MARK_RE = _re.compile(r"元\s*[/／]\s*公斤|每公斤|元每公斤")
_JIN_MARK_RE = _re.compile(r"元\s*[/／]\s*台斤|每台斤|元每台斤|元\s*[/／]\s*斤")


def _collect_facts(forecast: dict) -> dict:
    """S04：事實以 (mode, horizon, field, unit) 分離——百分比與價格不同集合，A/B 不聯集。"""
    a = {7: {"pct": set(), "price": {}, "dates": set(), "direction": None},
         14: {"pct": set(), "price": {}, "dates": set(), "direction": None}}
    b = {7: {"pct": set(), "price": {}, "dates": set(), "direction": None},
         14: {"pct": set(), "price": {}, "dates": set(), "direction": None}}
    all_dates = set()

    def _put(bucket, r):
        h = r.get("horizon_days")
        if h not in bucket:
            return
        pct = r.get("relative_change_estimate")
        if isinstance(pct, (int, float)):
            bucket[h]["pct"].add(round(pct * 100, 1))
        pe = r.get("price_estimate")
        if isinstance(pe, (int, float)):
            unit = r.get("price_estimate_unit") or ""
            bucket[h]["price"].setdefault(unit, set()).add(round(float(pe), 1))
        if r.get("target_date"):
            bucket[h]["dates"].add(str(r["target_date"]))

    for r in forecast.get("results") or []:
        _put(a, r)
        _put(a, r)  # results_without_last_week 語意同 A
    for r in forecast.get("results_without_last_week") or []:
        _put(a, r)
    for r in forecast.get("results_with_last_week") or []:
        _put(b, r)
    for bucket in (a, b):
        for h in (7, 14):
            d = (bucket[h]["direction"])
    # 方向
    for r in forecast.get("results") or []:
        if r.get("horizon_days") in a:
            a[r["horizon_days"]]["direction"] = r.get("direction")
    for r in forecast.get("results_with_last_week") or []:
        if r.get("horizon_days") in b:
            b[r["horizon_days"]]["direction"] = r.get("direction")
    for bucket in (a, b):
        for h in (7, 14):
            all_dates |= bucket[h]["dates"]
    if forecast.get("public_data_cutoff"):
        all_dates.add(str(forecast["public_data_cutoff"]))
    ioa = forecast.get("input_observed_at")
    if ioa:
        all_dates.add(str(ioa)[:10])
    return {"a": a, "b": b, "all_dates": all_dates}


def _horizon_spans(text: str) -> list[tuple[int, int, int]]:
    """句內期限詞定位：回 [(start, end, h)]（依位置排序；重疊取先匹配）。"""
    spans = []
    for h, pat in _HORIZON_WORDS:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end(), h))
    spans.sort()
    # 去重疊（同位置取 14 優先已由排序保證：14 的 pattern 在清單前面）
    out = []
    last_end = -1
    for st, en, h in spans:
        if st >= last_end:
            out.append((st, en, h))
            last_end = en
    return out


def _segments(sentence: str) -> list[tuple[str, int | None]]:
    """把句子切成 (子段, horizon)——每個期限詞管到下一個期限詞之前。"""
    spans = _horizon_spans(sentence)
    if not spans:
        return [(sentence, None)]
    segs = []
    if spans[0][0] > 0:
        segs.append((sentence[: spans[0][0]], None))
    for i, (st, en, h) in enumerate(spans):
        nxt = spans[i + 1][0] if i + 1 < len(spans) else len(sentence)
        segs.append((sentence[st:nxt], h))
    return segs


def _near(v: float, allowed: set) -> bool:
    return any(abs(v - a) <= 0.15 for a in allowed)


def validate_qwen_answer(answer, tool_outputs: dict) -> tuple[bool, str]:
    """S04 版：期限詞定位分段 → 各段以 (mode,horizon,field,unit) 檢查。

    - 百分比與價格為不同型別集合；B 價格不能當百分比（反之亦然）。
    - 只標 B 的段落只准引用 B 事實；A/B 對照段（同時標示）可用聯集；未標示→A。
    - 各期限的目標日期只准該期限的日期（交換日期即拒）。
    """
    if not isinstance(answer, str) or not answer.strip():
        return False, "empty_or_non_string_answer"

    forecast = tool_outputs.get("forecast") or {}
    has_valid_results = bool(forecast.get("results")) and not forecast.get("error")

    if _EXAGGERATION_RE.search(answer):
        return False, "exaggeration_or_probability_claim"

    sentences = [x for x in _re.split(r"[。\n；;]", answer) if x.strip()]

    if not has_valid_results:
        for sent in sentences:
            if _horizon_spans(sent):
                return False, "prediction_claim_without_tool_results"
        return True, ""

    facts = _collect_facts(forecast)

    # 非目標日期（觀察起點日／公開行情截止日）：只做全域存在檢查，不參與期限配對
    non_target_dates = set()
    ioa = forecast.get("input_observed_at")
    if ioa:
        non_target_dates.add(str(ioa)[:10])
    if forecast.get("public_data_cutoff"):
        non_target_dates.add(str(forecast["public_data_cutoff"]))

    # 日期：每個日期配對「就近期限」（同句最近的前後期限詞）
    for sent in sentences:
        spans = _horizon_spans(sent)
        for m in _DATE_RE.finditer(sent):
            d = m.group(0)
            if d not in facts["all_dates"]:
                return False, f"unverified_date:{d}"
            if d in non_target_dates:
                continue  # 起點／行情日不是任何期限的目標日
            if spans:
                near_h = min(spans, key=lambda sp: abs(sp[0] - m.start()))[2]
                if d not in (facts["a"][near_h]["dates"] | facts["b"][near_h]["dates"]):
                    return False, f"date_horizon_mismatch_h{near_h}:{d}"

    for sent in sentences:
        for seg, h in _segments(sent):
            # 模式標示可能在期限詞「之前」（如「B 模式 7 天後…」）：
            # 判定用文字包含期限詞前 10 字元的上下文。
            seg_start = sent.index(seg) if seg and seg in sent else 0
            ctx = sent[max(0, seg_start - 10): seg_start + len(seg)]
            is_b = bool(_B_MARK_RE.search(ctx))
            is_a_marked = bool(_A_MARK_RE.search(ctx))
            use_b = is_b
            use_a = (not is_b) or is_a_marked  # A/B 對照段兩者皆可；純 B 段只有 B

            if h is None:
                # 無期限段：任一期限的對應 mode 事實皆可（型別仍分離）
                a_pcts = set().union(*[facts["a"][x]["pct"] for x in (7, 14)]) if use_a else set()
                b_pcts = set().union(*[facts["b"][x]["pct"] for x in (7, 14)]) if use_b else set()
                a_prices = set()
                b_prices = set()
                for x in (7, 14):
                    if use_a:
                        for vs in facts["a"][x]["price"].values():
                            a_prices |= vs
                    if use_b:
                        for vs in facts["b"][x]["price"].values():
                            b_prices |= vs
            else:
                a_pcts = facts["a"][h]["pct"] if use_a else set()
                b_pcts = facts["b"][h]["pct"] if use_b else set()
                a_prices = set()
                b_prices = set()
                if use_a:
                    for vs in facts["a"][h]["price"].values():
                        a_prices |= vs
                if use_b:
                    for vs in facts["b"][h]["price"].values():
                        b_prices |= vs

            for m in _PCT_RE.finditer(seg):
                v = round(float(m.group(1)), 1)
                if not _near(v, a_pcts | b_pcts):
                    return False, f"unverified_pct_h{h or 0}:{v}"
            for m in _PRICE_RE.finditer(seg):
                v = round(float(m.group(1)), 1)
                if not _near(v, a_prices | b_prices):
                    return False, f"unverified_price_h{h or 0}:{v}"

            # 單位標示 vs 該段允許單位
            if h is not None:
                units = set()
                if use_a:
                    units |= set(facts["a"][h]["price"].keys())
                if use_b:
                    units |= set(facts["b"][h]["price"].keys())
                has_jin = "NTD_per_taiwan_jin" in units
                has_kg = "NTD_per_kg" in units
                if _KG_MARK_RE.search(seg) and has_jin and not has_kg:
                    return False, f"unit_mismatch_h{h}"
                if _JIN_MARK_RE.search(seg) and has_kg and not has_jin:
                    return False, f"unit_mismatch_h{h}"

            # 方向衝突（以該段期限的工具方向為準；A 優先，無 A 用 B）
            if h is not None:
                d = facts["a"][h]["direction"] or facts["b"][h]["direction"]
                if d:
                    for opp in _OPPOSITE.get(d, ()):
                        if opp in seg:
                            return False, f"direction_conflict_h{h}"
    return True, ""


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
            raw_content = data["choices"][0]["message"]["content"]
            if not isinstance(raw_content, str):
                raise ValueError(f"non-string content: {type(raw_content).__name__}")
            answer = raw_content.strip()
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

    # R01：缺必要輸入或工具無有效結果時，不把請求送 LLM——直接由規則層
    # 回「要求補充／無法預測」；LLM 只在有事實可解釋時參與。
    fc = tool_outputs.get("forecast")
    tool_ok = bool(fc and not fc.get("error") and fc.get("results"))
    if parsed.missing or parsed.unit_non_comparable or not tool_ok:
        rule_answer = RuleBackend().reply(parsed, tool_outputs)
        br = BackendResult(rule_answer, "rule", True, "no_tool_result_skip_llm" if not parsed.missing and not parsed.unit_non_comparable else "missing_input_skip_llm")
    # F02/F07：實際執行的後端與降級狀態；結構化 forecast 真值獨立回傳給前端
    elif hasattr(backend, "reply_result"):
        br = backend.reply_result(parsed, tool_outputs)
    else:
        br = BackendResult(backend.reply(parsed, tool_outputs), getattr(backend, "name", "rule"))
    return {
        "backend": getattr(backend, "name", "unknown"),
        "backend_used": br.backend_used,
        "provider": "rule",  # 與 providers 迴圈一致的中繼資料（rule 無 LLM）
        "model": None,
        "runtime": "rule",
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
