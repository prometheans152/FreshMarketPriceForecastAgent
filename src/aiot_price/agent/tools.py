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

# 價格兩種形式：「32元」與單位詞後裸數字「一斤32」
_PRICE_WITH_UNIT_RE = re.compile(r"(?:元|塊)(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|塊)")
_PRICE_BARE_RE = re.compile(r"(?:斤|公斤)\s*[:：]?\s*(\d{1,4}(?:\.\d+)?)")
# 公斤必須先於台斤檢查，且台斤不得匹配「公斤」中的斤
_UNIT_PATTERNS = [
    (re.compile(r"公斤|/kg|\/公斤"), "NTD_per_kg"),
    (re.compile(r"(?<!公)(?<!公 )台?斤|(?<!公)/斤"), "NTD_per_taiwan_jin"),
    (re.compile(r"(?:一|1)?\s*(?:顆|粒|把|根)"), "per_piece_or_bunch"),
]
_PREV_HINTS = re.compile(r"上(?:週|周|禮拜|次)")
_TODAY_HINTS = re.compile(r"今(?:天|日|日價|天價)")


@dataclass
class ParsedQuery:
    """自然語言查詢的確定性解析結果；missing 列出待補欄位。"""

    crop_id: str | None = None
    crop_text: str | None = None
    current_price: float | None = None
    price_unit: str | None = None
    market_id: str | None = None
    previous_price: float | None = None
    previous_price_unit: str | None = None
    days_ago_previous: int | None = None
    today: date = field(default_factory=lambda: datetime.now().astimezone().date())
    unit_non_comparable: bool = False
    missing: list[str] = field(default_factory=list)

    def to_forecast_request(self, store_id: str | None = None) -> dict | None:
        """組 ForecastRequest；必要欄位缺或單位不可比時回 None（missing 已填）。"""
        self.missing = []
        if self.crop_id is None:
            self.missing.append("品項")
        if self.current_price is None:
            self.missing.append("今天價格")
        if self.price_unit in (None, "per_piece_or_bunch"):
            self.missing.append("計價單位（元/台斤或元/公斤）")
        if self.missing:
            return None
        req = {
            "crop_id": self.crop_id,
            "market_id": self.market_id or "中義市場",  # 未指名市場的保守預設；回應中明示
            "current_price": self.current_price,
            "price_unit": self.price_unit,
            "observed_at": f"{self.today.isoformat()}T12:00:00+08:00",
            "mode": "without_last_week",
            "store_id": store_id,
        }
        if self.previous_price is not None and self.previous_price_unit not in (None, "per_piece_or_bunch"):
            req["previous_price"] = self.previous_price
            req["previous_price_unit"] = self.previous_price_unit
            ago = self.days_ago_previous or 7
            prev_day = self.today - timedelta(days=ago)
            req["previous_observed_at"] = f"{prev_day.isoformat()}T12:00:00+08:00"
            req["mode"] = "both"
        return req


def parse_query(text: str, today: date | None = None) -> ParsedQuery:
    """從中文查詢提取品項/價格/單位/市場/上週價。規則確定性、可單測。"""
    pq = ParsedQuery(today=today or datetime.now().astimezone().date())
    if not text or not text.strip():
        pq.missing = ["品項", "今天價格", "計價單位（元/台斤或元/公斤）"]
        return pq

    # 品項：最長別名優先
    for alias, cid in _ALIAS_PATTERNS:
        if alias and alias in text:
            pq.crop_id, pq.crop_text = cid, alias
            break

    # 單位
    for pat, unit in _UNIT_PATTERNS:
        if pat.search(text):
            if unit == "per_piece_or_bunch":
                pq.unit_non_comparable = True
            else:
                pq.price_unit = unit
            break

    # 價格：所有價格候選（帶單位元／塊，與「一斤32」式裸數字）
    prices: list[tuple[int, float]] = []
    for m in _PRICE_WITH_UNIT_RE.finditer(text):
        val = m.group(1) or m.group(2)
        # 取數字起始位置（group2 在後；group1 是「元32」形式）
        pos = m.start(1) if m.group(1) else m.start(2)
        prices.append((pos, float(val)))
    for m in _PRICE_BARE_RE.finditer(text):
        prices.append((m.start(1), float(m.group(1))))
    prices = sorted(set(prices))
    if prices:
        # 上週價：出現在上週提示詞之後最近的價格
        prev_price = None
        m_hint = _PREV_HINTS.search(text)
        if m_hint:
            after = [(pos, p) for pos, p in prices if pos > m_hint.start()]
            if after:
                prev_price = after[0][1]
        # 今天價：非上週價的第一個價格；若只有一個價格且無上週提示，就是今天價
        today_candidates = [(pos, p) for pos, p in prices]
        if prev_price is not None:
            prev_pos = next(pos for pos, p in prices if p == prev_price and pos > m_hint.start())
            today_candidates = [(pos, p) for pos, p in prices if pos != prev_pos]
        if today_candidates:
            pq.current_price = today_candidates[0][1]
        if prev_price is not None:
            pq.previous_price = prev_price
            pq.previous_price_unit = pq.price_unit
            pq.days_ago_previous = 7  # 預設整整 7 天前；實際日期由使用者更正

    # 市場：逐字掃描已知市場名
    for market in KNOWN_MARKETS:
        if market in text:
            pq.market_id = market
            break

    # 觸發 missing 計算（不含副作用）
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
