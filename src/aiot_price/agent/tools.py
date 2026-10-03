"""代理人有限工具集（T26）。

設計原則（design.md §5、TASKS T26）：
- 工具只有兩個：get_market_quote（查公開行情）與 post_forecast（菜價預測）。
- 菜名／價格／日期由「確定性規則解析」提取（可解釋、可測試）；Qwen 不決定工具
  參數、不發明店價——LLM 只負責把工具真實結果講清楚（service.py）。
- 每次請求工具呼叫上限與超時受限；不提供任意 URL／shell／模型修改能力。
- 解析不到的必要欄位回「要求補充」，不猜。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from aiot_price.data.schema import CROP_MAPPINGS, resolve_crop
from aiot_price.models.predict import KNOWN_MARKETS

MAX_TOOL_CALLS_PER_QUERY = 3
TOOL_TIMEOUT_SECONDS = 10

# 別名 → crop_id（含官方欄名與 display name 關鍵字）
_ALIAS_PATTERNS: list[tuple[str, str]] = []
for _cid, _m in CROP_MAPPINGS.items():
    names = {_m.display_name, _m.source_column, *_m.aliases}
    # 拿掉規格括號後的短名也納入（甘藍（平地高麗菜）→ 甘藍、平地高麗菜）
    for n in list(names):
        if "（" in n:
            inner = n.split("（", 1)[1].rstrip("）")
            names.add(n.split("（", 1)[0])
            names.add(inner)
    for n in names:
        _ALIAS_PATTERNS.append((n, _cid))
# 長名先配（避免「平地高麗菜」被「甘藍」先吃掉）
_ALIAS_PATTERNS.sort(key=lambda x: -len(x[0]))

# ---------- 子句級解析（F01：每個價格綁定自己的單位/品項/日期/店家線索） ----------

_CLAUSE_SPLIT_RE = re.compile(r"[，,、;；。]")
_DATE_RE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?")
# 月／日寫法（9/1、9月1日）；年用今天年。放在年月日之後嘗試。
_MD_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[/月](\d{1,2})日?(?!\d)")

_DEFAULT_YEAR = (2026,)  # 月/日寫法補年用；parse_query 依 today 覆寫
_UNIT_PATTERNS = [
    (re.compile(r"公斤|/kg"), "NTD_per_kg"),
    (re.compile(r"(?<!公)(?<!公 )台?斤|(?<!公)/斤"), "NTD_per_taiwan_jin"),
    (re.compile(r"(?:一|1|\d+)\s*(?:顆|粒|把|根|袋)"), "per_piece_or_bunch"),
]
_PRICE_NUM_RE = re.compile(r"([+-]?\d{1,5}(?:\.\d+)?)\s*(?:元|塊)|(?:元|塊)\s*([+-]?\d{1,5}(?:\.\d+)?)")
_PRICE_AFTER_UNIT_RE = re.compile(r"(?:斤|公斤)\s*[:：]?\s*([+-]?\d{1,5}(?:\.\d+)?)")
# 數量詞（兩斤32 的「兩斤」）：價格換算用
_QTY_RE = re.compile(r"(兩|二|三|四|五|六|七|八|九|十|[1-9]\d*)\s*(?:台)?斤")
_YESTERDAY_RE = re.compile(r"昨(?:天|日)")
_LAST_WEEK_RE = re.compile(r"上(?:週|周|禮拜)")
_LAST_TIME_RE = re.compile(r"上次")
_DIFF_STORE_RE = re.compile(r"另一(?:家|間)|別家|別間|不同(?:家|間)|換(?:了)?(?:一家|間)")
_DIFF_SPEC_RE = re.compile(r"換(?:了)?規格|不同規格|不同品種|有機")


@dataclass
class PriceMention:
    """單一子句內的價格提及：綁定當下的單位、品項、日期與可比性線索。"""

    value: float
    unit: str | None
    when: str  # today / yesterday / last_week / last_time / dated / last_week_dated
    explicit_date: date | None = None
    crop_id: str | None = None
    crop_text: str | None = None
    different_store: bool = False
    different_spec: bool = False
    quantity: float = 1.0  # 「兩斤32」的數量（總價換算單價用）
    invalid_date: bool = False  # 明示了日期但無法解析（不等於未提供）
    source_text: str = ""


@dataclass
class ParsedQuery:
    """自然語言查詢的確定性解析結果。

    F01 不變量：
    - current_price 綁定其所在子句的單位與品項；不從其他子句借用單位。
    - 明示日期優先；「昨天」如實當昨天（observed_date=t-1），不默默改今天。
    - 「上次」無日期不補 t-7；「上週」無明示日期才以 t-7 為假設並標 assumed。
    - 不同店／不同規格的上週價在解析層即拒 B（回 A）。
    """

    crop_id: str | None = None
    crop_text: str | None = None
    current_price: float | None = None
    price_unit: str | None = None
    market_id: str | None = None
    previous_price: float | None = None
    previous_price_unit: str | None = None
    previous_date: object = None
    previous_date_assumed: bool = False
    days_ago_previous: int | None = None
    observed_date: object = None  # 使用者明示的報價日（昨天/明示日期）；None=今天
    today: date = field(default_factory=lambda: datetime.now().astimezone().date())
    unit_non_comparable: bool = False
    ambiguous_crops: list = field(default_factory=list)
    b_reject_reason: str | None = None
    missing: list = field(default_factory=list)

    def to_forecast_request(self, store_id: str | None = None) -> dict | None:
        """組 ForecastRequest；必要欄位缺或單位不可比回 None（missing 已填）。"""
        self.missing = []
        if self.crop_id is None:
            if self.ambiguous_crops:
                self.missing.append("品項（偵測到多品項，請指定一種）")
            else:
                self.missing.append("品項")
        if self.current_price is None:
            self.missing.append("今天價格")
        if self.price_unit in (None, "per_piece_or_bunch"):
            self.missing.append("計價單位（元/台斤或元/公斤）")
        if self.missing:
            return None
        obs = self.observed_date or self.today
        req = {
            "crop_id": self.crop_id,
            "market_id": self.market_id or "中義市場",
            "current_price": self.current_price,
            "price_unit": self.price_unit,
            "observed_at": f"{obs.isoformat()}T12:00:00+08:00",
            "mode": "without_last_week",
            "store_id": store_id,
        }
        if (
            self.previous_price is not None
            and self.previous_price_unit not in (None, "per_piece_or_bunch")
            and self.previous_date is not None
            and not self.b_reject_reason
        ):
            req["previous_price"] = self.previous_price
            req["previous_price_unit"] = self.previous_price_unit
            req["previous_observed_at"] = f"{self.previous_date.isoformat()}T12:00:00+08:00"
            req["previous_date_assumed"] = self.previous_date_assumed
            req["mode"] = "both"
        return req


def _extract_mentions(text: str) -> list[PriceMention]:
    """逐子句提取價格提及；每個提及只綁定自己子句內的線索。"""
    mentions: list[PriceMention] = []
    for clause in _CLAUSE_SPLIT_RE.split(text):
        clause = clause.strip()
        if not clause:
            continue

        unit = None
        for pat, u in _UNIT_PATTERNS:
            if pat.search(clause):
                unit = u
                break

        explicit = None
        date_invalid = False
        m = _DATE_RE.search(clause)
        if m:
            try:
                explicit = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                # R03：明示但無效（如 2026-02-30）≠ 未提供；標記後續拒 B，不補預設
                date_invalid = True
        if explicit is None and not date_invalid:
            md = _MD_DATE_RE.search(clause)
            if md:
                try:
                    explicit = date(_DEFAULT_YEAR[0], int(md.group(1)), int(md.group(2)))
                except ValueError:
                    date_invalid = True
        if explicit is not None or date_invalid:
            when = "last_week_dated" if (_LAST_WEEK_RE.search(clause) or _LAST_TIME_RE.search(clause)) else "dated"
        elif _YESTERDAY_RE.search(clause):
            when = "yesterday"
        elif _LAST_WEEK_RE.search(clause):
            when = "last_week"
        elif _LAST_TIME_RE.search(clause):
            when = "last_time"
        else:
            when = "today"

        # 數量（兩斤/2斤）→ 價格若為總價則換算單價
        qty = 1.0
        qm = _QTY_RE.search(clause)
        if qm:
            word = qm.group(1)
            qty = {"兩": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}.get(word, None) or (float(word) if word.isdigit() else 1.0)

        crop_id = crop_text = None
        for alias, cid in _ALIAS_PATTERNS:
            if alias and alias in clause:
                crop_id, crop_text = cid, alias
                break

        vals: list[float] = []
        for pm in _PRICE_NUM_RE.finditer(clause):
            v = pm.group(1) or pm.group(2)
            vals.append(float(v))
        for pm in _PRICE_AFTER_UNIT_RE.finditer(clause):
            vals.append(float(pm.group(1)))

        if not vals:
            continue
        for v in vals:
            unit_price = v / qty if qty and qty > 1 and unit in ("NTD_per_taiwan_jin", "NTD_per_kg") else v
            mentions.append(
                PriceMention(
                    unit_price, unit, when, explicit, crop_id, crop_text,
                    bool(_DIFF_STORE_RE.search(clause)),
                    bool(_DIFF_SPEC_RE.search(clause)),
                    qty,
                    date_invalid,
                    clause,
                )
            )
    return mentions


def parse_query(text: str, today: date | None = None) -> ParsedQuery:
    """從中文查詢解析。子句級綁定；無法可靠解讀時要求補充或回 A，不猜。"""
    pq = ParsedQuery(today=today or datetime.now().astimezone().date())
    globals()["_DEFAULT_YEAR"] = (pq.today.year,)
    if not text or not text.strip():
        pq.missing = ["品項", "今天價格", "計價單位（元/台斤或元/公斤）"]
        return pq

    mentions = _extract_mentions(text)
    if not mentions:
        pq.missing = ["品項", "今天價格", "計價單位（元/台斤或元/公斤）"]
        return pq

    for market in KNOWN_MARKETS:
        if market in text:
            pq.market_id = market
            break

    current_candidates = [m for m in mentions if m.when in ("today", "yesterday", "dated")]
    past_candidates = [m for m in mentions if m.when in ("last_week", "last_week_dated", "last_time")]

    usable_current = [
        m for m in current_candidates
        if m.unit in ("NTD_per_taiwan_jin", "NTD_per_kg") and m.value == m.value and m.value > 0
    ]
    non_comparable_today = [m for m in current_candidates if m.unit == "per_piece_or_bunch"]
    crops_seen = sorted({m.crop_id for m in usable_current if m.crop_id})
    if len(crops_seen) > 1:
        pq.ambiguous_crops = crops_seen
    elif usable_current:
        chosen = usable_current[0]
        pq.crop_id = pq.crop_id or chosen.crop_id
        pq.crop_text = chosen.crop_text or pq.crop_text
        pq.current_price = chosen.value
        pq.price_unit = chosen.unit
        if chosen.when == "yesterday":
            pq.observed_date = pq.today - timedelta(days=1)
        elif chosen.when == "dated" and chosen.explicit_date:
            pq.observed_date = chosen.explicit_date
    elif non_comparable_today:
        pq.unit_non_comparable = True
        pq.crop_id = pq.crop_id or non_comparable_today[0].crop_id
        pq.crop_text = pq.crop_text or non_comparable_today[0].crop_text

    # 上週價未明示單位時，繼承今天價的單位（同店同規格同單位是產品預設；
    # 若今天價單位也不明，仍要求補充）
    if pq.price_unit:
        for m in past_candidates:
            if m.unit is None:
                m.unit = pq.price_unit
    past_usable = [
        m for m in past_candidates
        if m.unit in ("NTD_per_taiwan_jin", "NTD_per_kg") and m.value == m.value and m.value > 0
    ]
    # R03：上週品項必須與今天品項相同（或未指明品項），跨品項拒 B
    cross_crop = [m for m in past_usable if m.crop_id and pq.crop_id and m.crop_id != pq.crop_id]
    invalid_date_mentions = [m for m in past_candidates if m.invalid_date]
    if cross_crop:
        other = cross_crop[0]
        pq.b_reject_reason = f"上週價品項是{other.crop_text or '另一種品項'}，與今天的{pq.crop_text or '本品項'}品項不同，不可比，僅提供 A 模式結果"
        past_usable = []
    elif invalid_date_mentions:
        pq.b_reject_reason = "上週日期無法解析（如 2026-02-30 不存在），請提供有效日期後再對照"
        past_usable = []
    if past_usable:
        chosen_past = past_usable[0]
        if chosen_past.different_store:
            pq.b_reject_reason = "上週價格來自另一家店，與本店不可比，僅提供 A 模式結果"
        elif chosen_past.different_spec:
            pq.b_reject_reason = "上週規格／品種不同，不可比，僅提供 A 模式結果"
        elif chosen_past.when == "last_time" and chosen_past.explicit_date is None:
            pq.b_reject_reason = "「上次」未提供實際日期，無法確認與今天相差天數，僅提供 A 模式；補充日期（如：上次 9/26）即可對照"
        elif chosen_past.when == "last_week_dated" and chosen_past.explicit_date is not None:
            pq.previous_price = chosen_past.value
            pq.previous_price_unit = chosen_past.unit
            pq.previous_date = chosen_past.explicit_date
            pq.days_ago_previous = (pq.today - chosen_past.explicit_date).days
        elif chosen_past.when == "last_week":
            pq.previous_price = chosen_past.value
            pq.previous_price_unit = chosen_past.unit
            pq.previous_date = pq.today - timedelta(days=7)
            pq.previous_date_assumed = True
            pq.days_ago_previous = 7

    _ = pq.to_forecast_request()
    return pq


class ToolCallLimiter:
    """單一查詢的工具呼叫次數上限。"""

    def __init__(self, max_calls: int = MAX_TOOL_CALLS_PER_QUERY):
        self.max_calls = max_calls
        self.calls = 0

    def check(self) -> bool:
        if self.calls >= self.max_calls:
            return False
        self.calls += 1
        return True


class AgentTools:
    """兩個有限工具；皆重用 ForecastEngine（與 POST /forecast 同一推論路徑）。"""

    def __init__(self, engine):
        self.engine = engine

    def get_market_quote(self, crop_id: str, market_id: str) -> dict:
        """最新公開行情（觀測日/價格/年齡）；非預測。"""
        from aiot_price.features.build import build_features

        sub = self.engine.history[
            (self.engine.history["crop_id"] == crop_id)
            & (self.engine.history["market_id"] == market_id)
        ]
        if sub.empty:
            return {"ok": False, "reason": f"{market_id} 查無 {crop_id} 公開價格"}
        feats = build_features(sub, [pd.Timestamp(self.engine.public_cutoff)], delay_days=0)
        row = feats.loc[(market_id, crop_id, pd.Timestamp(self.engine.public_cutoff))]
        last = row["price_last"]
        if pd.isna(last):
            return {"ok": False, "reason": f"{market_id} 的 {crop_id} 無可用價格"}
        return {
            "ok": True,
            "market_id": market_id,
            "crop_id": crop_id,
            "price": float(last),
            "unit": "NTD_per_taiwan_jin",
            "observed_date": str(self.engine.public_cutoff.date()),
        }

    def post_forecast(self, request: dict) -> dict:
        """與 HTTP POST /forecast 完全同源的預測（重用引擎）。"""
        return self.engine.forecast(request)
