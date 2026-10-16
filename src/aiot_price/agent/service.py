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
from aiot_price.data.schema import CROP_MAPPINGS
from aiot_price.models.predict import KNOWN_MARKETS

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
import math as _math
import unicodedata as _unicode

_EXAGGERATION_RE = _re.compile(r"必定|保證|絕對會|機率是|的機率|可信度|準確率|已驗證|已經驗證|一定會|已通過")
_NUMBER_TOKEN = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|[零〇一二三四五六七八九十百千兩两]+(?:[點点][零〇一二三四五六七八九]+)?)"
_PCT_RE = _re.compile(rf"({_NUMBER_TOKEN})\s*[%％]|百分之\s*({_NUMBER_TOKEN})")
_DATE_RE = _re.compile(r"\d{4}-\d{2}-\d{2}")
_PRICE_RE = _re.compile(rf"({_NUMBER_TOKEN})\s*[元塊块]")
_MONEY_MARK_RE = _re.compile(r"[元塊块]|NT\$|\b(?:NTD|TWD|dollars?|yuan)\b", _re.IGNORECASE)
_FORECAST_CLAIM_RE = _re.compile(r"漲|跌|持平|變貴|變便宜|預測|預估|估計|未來|將來|以後|之後|forecast|predict|will", _re.IGNORECASE)
_SAVE_CONFIRM_RE = _re.compile(
    r"已(?:依您的確認|確認)?保存(?:剛才的預測|本筆預測|這筆預測)?"
    r"(?:\s*[，,]\s*供\s*(?:(?:7\s*[/／]\s*14|7|14|七|十四)\s*天後\s*)?(?:到期|後續)?核對)?"
)
_REFERENCE_HORIZON_RE = _re.compile(r"7\s*[/／]\s*14\s*天")
_PRICE_UNIT_RE = _re.compile(r"[元塊块]\s*[/／]\s*([^\s,，;；。()（）]*)")
_PRICE_FIELD_RE = _re.compile(r"(?:預估店價|(?:店價|價格|售價|菜價)\s*(?:是|為))\s*(?:是|為)?")
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
_MODE_MARK_RE = _re.compile(r"(?P<a>(?<![a-z])A(?![a-z])\s*(?:模式)?|未使用上週|不含上週)|(?P<b>(?<![a-z])B(?![a-z])\s*(?:模式)?|實驗性|使用上週|加上上週|有上週)", _re.IGNORECASE)
_KG_MARK_RE = _re.compile(r"公斤")
_JIN_MARK_RE = _re.compile(r"台斤|(?<!公)斤")
_DIRECTION_CLAIMS = {"up": _re.compile(r"上漲"), "down": _re.compile(r"下跌"),
                     "flat": _re.compile(r"持平")}

# Only reviewed render vocabulary is admitted. Unknown price/direction prose,
# including English number words, is discarded rather than guessed or parsed.
_QUOTE_WORDS = (
    "最新", "公開行情", "行情", "觀測日", "市場均價", "非店價", "此為", "報價",
    "目前", "價格", "是", "為", "的", "約", "每", "公斤", "台斤", "斤", "價",
    "已查詢", "已完成工具查詢", "已完成工具查詢並保存",
    "僅供市場參考", "市場均價不是個店真值",
)
_FORECAST_WORDS = _QUOTE_WORDS + (
    "依工具結果", "從今天", "今天", "起算", "公開行情截止", "截止", "後",
    "預估店價", "預估", "估計", "店價", "菜價", "售價", "可能上漲", "可能下跌",
    "大致持平", "上漲", "下跌", "持平", "會", "資料不足", "實驗性規則",
    "實驗性", "未經同店驗證", "非同店驗證", "僅供參考", "實驗性規則、未經同店驗證",
    "有上週價格的對照", "使用上週價", "未使用上週價", "不含上週價", "模式",
    "已依您的確認保存本筆預測", "已確認保存", "已保存",
)


def _supported_rendered_prose(text: str, *, forecast: bool) -> bool:
    """A bounded rendering grammar; arbitrary financial prose fails closed."""
    residual = text
    for pattern in (_PRICE_RE, _PCT_RE, _DATE_RE, _MODE_MARK_RE):
        residual = pattern.sub(" ", residual)
    for _, pattern in _HORIZON_WORDS:
        residual = pattern.sub(" ", residual)
    words = set(_FORECAST_WORDS if forecast else _QUOTE_WORDS) | set(KNOWN_MARKETS)
    for crop in CROP_MAPPINGS.values():
        words.update((crop.display_name, crop.source_column, *crop.aliases))
    # Strip complete supported lexemes, then admit punctuation only. A partial
    # number match (e.g. 數十元 -> 十元) leaves unsupported prose and is rejected.
    for word in sorted(words, key=len, reverse=True):
        residual = residual.replace(word, " ")
    return bool(_re.fullmatch(r"[\s,，;；。:：()/／（）\[\]•、—+\-]*", residual))


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
        if isinstance(pct, (int, float)) and not isinstance(pct, bool) and _math.isfinite(pct):
            bucket[h]["pct"].add(round(pct * 100, 1))
        pe = r.get("price_estimate")
        if isinstance(pe, (int, float)) and not isinstance(pe, bool) and _math.isfinite(pe):
            unit = r.get("price_estimate_unit") or ""
            bucket[h]["price"].setdefault(unit, set()).add(round(float(pe), 1))
        if r.get("target_date"):
            bucket[h]["dates"].add(str(r["target_date"]))
        bucket[h]["direction"] = r.get("direction")

    mode = forecast.get("mode_executed")
    primary = forecast.get("results") or []
    named_a = forecast.get("results_without_last_week") or []
    named_b = forecast.get("results_with_last_week") or []
    if mode == "with_last_week":
        rows_a, rows_b = named_a, named_b or primary
    elif mode == "both":
        rows_a, rows_b = named_a or primary, named_b
    elif mode in ("without_last_week", "fallback_without_last_week"):
        rows_a, rows_b = primary, []
    elif mode is None:
        # Legacy callers predate mode_executed; results was explicitly A there.
        rows_a, rows_b = named_a or primary, named_b
    else:
        rows_a, rows_b = [], []  # Unknown execution modes cannot authorize facts.
    for bucket, rows in ((a, rows_a), (b, rows_b)):
        for r in rows:
            _put(bucket, r)
    for bucket in (a, b):
        for h in (7, 14):
            all_dates |= bucket[h]["dates"]
    if forecast.get("public_data_cutoff"):
        all_dates.add(str(forecast["public_data_cutoff"]))
    ioa = forecast.get("input_observed_at")
    if ioa:
        all_dates.add(str(ioa)[:10])
    return {"a": a, "b": b, "all_dates": all_dates,
            "default_mode": "b" if mode == "with_last_week" else "a"}


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


_CJK_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2, "三": 3, "四": 4,
               "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CJK_NONZERO = "一二三四五六七八九兩两"
_CJK_INTEGER_RE = _re.compile(
    rf"(?:[零〇]|[{_CJK_NONZERO}]|[{_CJK_NONZERO}]?十[{_CJK_NONZERO}]?|"
    rf"[{_CJK_NONZERO}]百(?:零[{_CJK_NONZERO}]|[{_CJK_NONZERO}]十[{_CJK_NONZERO}]?)?)"
)


def _cjk_num(s: str) -> float | None:
    """Bounded Chinese decimal grammar; ambiguous shorthand/unknown forms fail closed."""
    parts = _re.split(r"[點点]", s)
    if len(parts) > 2 or not _CJK_INTEGER_RE.fullmatch(parts[0]):
        return None
    integer = parts[0]
    total, num = 0, 0
    for ch in integer:
        if ch in _CJK_DIGITS:
            num = num * 10 + _CJK_DIGITS[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
        else:
            return None
    value = float(total + num)
    if len(parts) == 2:
        if not parts[1] or any(ch not in _CJK_DIGITS for ch in parts[1]):
            return None
        value += float("0." + "".join(str(_CJK_DIGITS[ch]) for ch in parts[1]))
    return value


def _number_value(text: str) -> float | None:
    if _re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", text):
        value = float(text)
        return value if _math.isfinite(value) else None
    sign = -1 if text.startswith("-") else 1
    value = _cjk_num(text.lstrip("+-"))
    return sign * value if value is not None else None


def _pct_value(m) -> float | None:
    """_PCT_RE 各形（99%／％／百分之99／百分之五十）取數值。"""
    return _number_value(m.group(1) or m.group(2))


def _validate_numeric_syntax(text: str) -> str | None:
    """Every numeric glyph and money marker must belong to supported typed syntax.

    This is an allowlist boundary, not a blacklist of possible hallucinations.
    Unknown notation is discarded; callers then render their trusted fallback.
    """
    covered = set()
    prices = list(_PRICE_RE.finditer(text))
    pcts = list(_PCT_RE.finditer(text))
    for m in prices:
        if _number_value(m.group(1)) is None:
            return "unsupported_price_notation"
    for m in _PRICE_UNIT_RE.finditer(text):
        if m.group(1) not in ("公斤", "台斤", "斤"):
            return "unsupported_price_unit"
    for m in pcts:
        if _pct_value(m) is None:
            return "unsupported_pct_notation"
    spans = [(m.start(), m.end()) for m in prices + pcts + list(_DATE_RE.finditer(text))]
    spans += [(m.start(), m.end()) for m in _REFERENCE_HORIZON_RE.finditer(text)]
    spans += [(st, en) for st, en, _ in _horizon_spans(text)]
    for st, en in spans:
        covered.update(range(st, en))
    # Some ordinary domain words contain financial numeral glyphs (參考).
    # Admit only occurrences of reviewed complete phrases, never arbitrary text.
    for word in _FORECAST_WORDS:
        if any(ch.isnumeric() for ch in word):
            for m in _re.finditer(_re.escape(word), text):
                covered.update(range(m.start(), m.end()))
    for m in _MONEY_MARK_RE.finditer(text):
        if not any(p.start() <= m.start() and m.end() <= p.end() for p in prices):
            return "unsupported_price_notation"
    if any(ch.isnumeric() and i not in covered for i, ch in enumerate(text)):
        return "unsupported_numeric_notation"
    return None


def _claim_segments(sentence: str, default_mode: str):
    """Bind each clause to its most recent mode and horizon; never union A/B."""
    boundaries = [(st, en, "horizon", h) for st, en, h in _horizon_spans(sentence)]
    boundaries += [(m.start(), m.end(), "mode", "a" if m.lastgroup == "a" else "b")
                   for m in _MODE_MARK_RE.finditer(sentence)]
    boundaries.sort()
    mode, horizon, pos = default_mode, None, 0
    for st, en, kind, value in boundaries:
        if st > pos:
            yield sentence[pos:st], horizon, mode
        if kind == "mode":
            mode = value
        else:
            horizon = value
        pos = en
    if pos < len(sentence):
        yield sentence[pos:], horizon, mode


def _metadata_date_allowed(text: str, start: int, value: str, forecast: dict) -> bool:
    """Only explicit metadata labels authorize a start/cutoff date."""
    prefix = text[:start].rstrip()
    observed = str(forecast.get("input_observed_at") or "")[:10]
    cutoff = str(forecast.get("public_data_cutoff") or "")[:10]
    return bool(
        (value == observed and _re.search(r"今天\s*$", prefix))
        or (value == cutoff and _re.search(r"公開行情截止\s*$", prefix))
    )


def validate_qwen_answer(answer, tool_outputs: dict) -> tuple[bool, str]:
    """Validate supported numeric syntax against (mode,horizon,field,unit) facts.

    - 百分比與價格為不同型別集合；B 價格不能當百分比（反之亦然）。
    - 每個模式標記各自約束後續主張；A/B 永不聯集，未標示使用實際執行模式。
    - 各期限的目標日期只准該期限的日期（交換日期即拒）。
    """
    if not isinstance(answer, str) or not answer.strip():
        return False, "empty_or_non_string_answer"
    answer = _unicode.normalize("NFKC", answer)

    forecast = tool_outputs.get("forecast") or {}
    has_valid_results = bool(forecast.get("results")) and not forecast.get("error")

    if _EXAGGERATION_RE.search(answer):
        return False, "exaggeration_or_probability_claim"
    syntax_error = _validate_numeric_syntax(answer)
    if syntax_error:
        return False, syntax_error

    sentences = [x for x in _re.split(r"[。\n；;]", answer) if x.strip()]

    if not has_valid_results:
        # 第二階段：無預測但有可信行情（quote-only 回答）——任何期限主張仍拒；
        # 數字與日期必須忠於行情事實（價格 ±0.15；僅行情觀測日允許）。
        # save-only（已確認保存、無任何行情/預測）：允許提及核對期限，
        # 但一切數字/日期仍拒（無可驗事實）。
        save_only = bool(tool_outputs.get("save_ok"))
        quote = tool_outputs.get("market_quote") or {}
        quote_ok = bool(isinstance(quote, dict) and quote.get("ok") and quote.get("price") is not None)
        allowed_prices = set()
        allowed_dates = set()
        if quote_ok:
            try:
                price = float(quote["price"])
                if isinstance(quote["price"], bool) or not _math.isfinite(price) or price <= 0:
                    quote_ok = False
                else:
                    allowed_prices.add(round(price, 1))
            except (TypeError, ValueError):
                quote_ok = False
            if quote.get("observed_date"):
                allowed_dates.add(str(quote["observed_date"])[:10])
        for sent in sentences:
            if not save_only and _horizon_spans(sent):
                return False, "prediction_claim_without_tool_results"
            if _DATE_RE.search(sent):
                if not quote_ok or not all(d in allowed_dates for d in _DATE_RE.findall(sent)):
                    return False, f"unverified_date:{_DATE_RE.search(sent).group(0)}"
            for m in _PCT_RE.finditer(sent):
                return False, f"unverified_pct_quote_only:{_pct_value(m)}"
            for m in _PRICE_RE.finditer(sent):
                v = round(_number_value(m.group(1)), 1)
                if not quote_ok or not _near(v, allowed_prices):
                    return False, f"unverified_price_quote_only:{v}"
            if save_only and _SAVE_CONFIRM_RE.fullmatch(sent.strip()):
                continue  # Referring to the saved forecast is not a new prediction.
            if save_only and not quote_ok:
                return False, "unsupported_save_confirmation"
            if _horizon_spans(sent) or _FORECAST_CLAIM_RE.search(sent):
                return False, "prediction_claim_without_tool_results"
            unit = quote.get("unit") or quote.get("price_unit")
            if unit:
                if _KG_MARK_RE.search(sent) and unit != "NTD_per_kg":
                    return False, "unit_mismatch_quote_only"
                if _JIN_MARK_RE.search(sent) and unit != "NTD_per_taiwan_jin":
                    return False, "unit_mismatch_quote_only"
            if not _supported_rendered_prose(sent, forecast=False):
                return False, "unsupported_quote_statement"
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
            if d in non_target_dates and _metadata_date_allowed(sent, m.start(), d, forecast):
                continue  # 起點／行情日不是任何期限的目標日
            if spans:
                near_h = min(spans, key=lambda sp: abs(sp[0] - m.start()))[2]
                if d not in (facts["a"][near_h]["dates"] | facts["b"][near_h]["dates"]):
                    return False, f"date_horizon_mismatch_h{near_h}:{d}"

    active_mode = facts["default_mode"]
    for sent in sentences:
        mode_marks = list(_MODE_MARK_RE.finditer(sent))
        number_claims = list(_PRICE_RE.finditer(sent)) + list(_PCT_RE.finditer(sent))
        if mode_marks and number_claims and min(m.start() for m in number_claims) < mode_marks[0].start():
            return False, "ambiguous_numeric_mode_attribution"
        # A completed numeric claim may start a new mode/horizon only through
        # an explicit clause delimiter. Units, dates and previous mode labels
        # may precede that transition; free prose cannot reassign the value.
        marker_starts = [m.start() for m in mode_marks] + [st for st, _, _ in _horizon_spans(sent)]
        for start in marker_starts:
            prior = [m for m in number_claims if m.end() <= start]
            if not prior:
                continue
            last = max(prior, key=lambda m: m.end())
            tail = sent[last.end():start]
            if not any(delimiter in tail for delimiter in (",", "，")):
                return False, "numeric_claim_requires_delimited_transition"
            tail = _MODE_MARK_RE.sub(" ", _DATE_RE.sub(" ", tail))
            for unit_word in ("公斤", "台斤", "斤"):
                tail = tail.replace(unit_word, " ")
            if not _re.fullmatch(r"[\s,，()/／（）]*", tail):
                return False, "numeric_claim_cannot_reassign_value"
        for seg, h, mode in _claim_segments(sent, active_mode):
            if h is None and (_PRICE_RE.search(seg) or _PCT_RE.search(seg)):
                return False, "ambiguous_numeric_horizon_attribution"
            buckets = [facts[mode][x] for x in ((h,) if h is not None else (7, 14))]
            pcts = set().union(*(bucket["pct"] for bucket in buckets))
            prices = set().union(*(vs for bucket in buckets for vs in bucket["price"].values()))
            units = set().union(*(set(bucket["price"]) for bucket in buckets))
            dates = set().union(*(bucket["dates"] for bucket in buckets))

            # A price field must be followed by a monetary typed value. The
            # existence of the same number as a change percentage is irrelevant.
            for label in _PRICE_FIELD_RE.finditer(seg):
                values = [(m.start(), "price") for m in _PRICE_RE.finditer(seg) if m.start() >= label.end()]
                values += [(m.start(), "pct") for m in _PCT_RE.finditer(seg) if m.start() >= label.end()]
                if not values or min(values)[1] != "price":
                    return False, "price_field_requires_monetary_value"

            for m in _PCT_RE.finditer(seg):
                v = round(_pct_value(m), 1)
                if not _near(v, pcts):
                    return False, f"unverified_pct_h{h or 0}:{v}"
            for m in _PRICE_RE.finditer(seg):
                v = round(_number_value(m.group(1)), 1)
                if not _near(v, prices):
                    return False, f"unverified_price_h{h or 0}:{v}"

            for m in _DATE_RE.finditer(seg):
                d = m.group(0)
                metadata = d in non_target_dates and _metadata_date_allowed(seg, m.start(), d, forecast)
                if not metadata and d not in dates:
                    return False, f"date_mode_horizon_mismatch_{mode}_h{h or 0}:{d}"

            # 單位標示 vs 該段允許單位
            if _KG_MARK_RE.search(seg) and "NTD_per_kg" not in units:
                return False, f"unit_mismatch_h{h or 0}"
            if _JIN_MARK_RE.search(seg) and "NTD_per_taiwan_jin" not in units:
                return False, f"unit_mismatch_h{h or 0}"

            # Direction belongs to the selected mode, never the other mode.
            if h is not None:
                d = facts[mode][h]["direction"]
                for claimed, pattern in _DIRECTION_CLAIMS.items():
                    if pattern.search(seg) and claimed != d:
                        return False, f"direction_conflict_h{h}"
            elif any(pattern.search(seg) for pattern in _DIRECTION_CLAIMS.values()):
                return False, "ambiguous_direction_horizon_attribution"
        if not _supported_rendered_prose(sent, forecast=True):
            return False, "unsupported_forecast_statement"
        if mode_marks:
            active_mode = "a" if mode_marks[-1].lastgroup == "a" else "b"
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
