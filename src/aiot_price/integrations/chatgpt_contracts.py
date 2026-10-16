"""Strict personal MCP contracts: two read-only tools, no caller-controlled paths."""
from __future__ import annotations
import math
import json
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
CROP_IDS = ("cabbage", "bok_choy", "sponge_gourd")
# Numeric worker checks against models.predict.KNOWN_MARKETS.
MARKETS = (
    "中義市場", "南屯市場", "合作市場", "大甲第二市場", "東光市場", "梧棲第一市場",
    "沙鹿市場", "清水第一市場", "第三市場", "第二市場", "第五市場", "豐原第一市場", "霧峰市場",
)
UNITS = ("NTD_per_taiwan_jin", "NTD_per_kg")
TOOL_NAMES = ("get_market_quote", "post_forecast")
MAX_ARGUMENT_FIELDS = 5
MAX_ARGUMENT_KEY_BYTES = 64
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}

class ContractError(ValueError):
    """Tool validation failed closed."""


def strict_json_loads(value: str | bytes):
    """Internal worker protocol: disallow duplicate keys and non-JSON constants."""
    def unique_pairs(pairs):
        result = {}
        for key, val in pairs:
            if key in result:
                raise ContractError("JSON 工具訊息有重複欄位，已拒絕。")
            result[key] = val
        return result

    def invalid_constant(token):
        raise ContractError("JSON 工具訊息不得含 NaN／Infinity。")

    return json.loads(value, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)

def _enum(values):
    return {"type": "string", "enum": list(values)}

TOOL_SCHEMAS = {
    "get_market_quote": {
        "type": "object", "additionalProperties": False,
        "required": ["crop_id", "market_id"],
        "properties": {"crop_id": _enum(CROP_IDS), "market_id": _enum(MARKETS)},
    },
    "post_forecast": {
        "type": "object", "additionalProperties": False,
        "required": ["crop_id", "market_id", "current_price", "price_unit"],
        "properties": {
            "crop_id": _enum(CROP_IDS), "market_id": _enum(MARKETS),
            "current_price": {"type": "number", "exclusiveMinimum": 0},
            "price_unit": _enum(UNITS),
            "observed_on": {"type": "string", "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
        },
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["tool", "input_echo", "query_date", "engine_result", "limits"],
    "properties": {
        "tool": {"type": "string", "enum": list(TOOL_NAMES)},
        "input_echo": {"type": "object"},
        "normalized_request": {"type": ["object", "null"]},
        "query_date": {"type": "string"},
        "engine_result": {"type": "object"},
        "limits": {"type": "array", "items": {"type": "string"}},
        "price_age_days_at_query": {"type": ["integer", "null"]},
    },
    "additionalProperties": True,
}
TOOL_DESCRIPTIONS = {
    "get_market_quote": "查臺中政府快照公開市場均價（非即時店價），需指定品項和市場。",
    "post_forecast": "以當日店價做 A 模式 7／14 天推估，不支援 B／保存，未經同店驗證。",
}
OBSERVED_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

def taipei_today(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(TAIPEI).date()

def validate_arguments(name, arguments, *, today=None):
    if name not in TOOL_NAMES:
        raise ContractError("不支援此工具；第一版只有查行情與 A 預測。")
    if not isinstance(arguments, dict):
        raise ContractError("工具參數必須是 JSON 物件。")
    # Check length before enumerating, sorting or formatting caller-owned keys.
    if len(arguments) > MAX_ARGUMENT_FIELDS:
        raise ContractError("工具參數欄位超過上限，已拒絕。")
    for key in arguments:
        if not isinstance(key, str) or len(key) > MAX_ARGUMENT_KEY_BYTES:
            raise ContractError("工具參數欄名無效或超過上限，已拒絕。")
        try:
            key_bytes = key.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContractError("工具參數欄名不是有效 UTF-8，已拒絕。") from exc
        if len(key_bytes) > MAX_ARGUMENT_KEY_BYTES:
            raise ContractError("工具參數欄名超過上限，已拒絕。")
    schema = TOOL_SCHEMAS[name]
    missing = sorted(set(schema["required"]) - set(arguments))
    if missing:
        raise ContractError("缺少必要欄位：" + "、".join(missing) + "；請先詢問使用者。")
    if any(key not in schema["properties"] for key in arguments):
        raise ContractError("不允許額外欄位（B、保存及任意執行均不支援）。")
    crop, market = arguments["crop_id"], arguments["market_id"]
    if not isinstance(crop, str) or crop not in CROP_IDS:
        raise ContractError("品項僅支援 cabbage／bok_choy／sponge_gourd。")
    if not isinstance(market, str) or market not in MARKETS:
        raise ContractError("請從支援的臺中市場中選擇。")
    cleaned = {"crop_id": crop, "market_id": market}
    if name == "post_forecast":
        raw = arguments["current_price"]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw) or raw <= 0:
            raise ContractError("current_price 須為大於零的有限數值（非布林）。")
        unit = arguments["price_unit"]
        if not isinstance(unit, str) or unit not in UNITS:
            raise ContractError("單位僅支援元／台斤或元／公斤。")
        value = arguments.get("observed_on")
        if "observed_on" in arguments:
            if not isinstance(value, str) or not OBSERVED_PATTERN.fullmatch(value):
                raise ContractError("observed_on 必須是嚴格 YYYY-MM-DD。")
            try:
                day = date.fromisoformat(value)
            except ValueError as e:
                raise ContractError("observed_on 不是有效日曆日。") from e
        else:
            day = today or taipei_today()
        if day > (today or taipei_today()):
            raise ContractError("不允許未來觀測日。")
        cleaned.update(current_price=float(raw), price_unit=unit, observed_on=day.isoformat())
    return cleaned

def normalized_forecast_request(cleaned):
    return {
        "crop_id": cleaned["crop_id"], "market_id": cleaned["market_id"],
        "current_price": cleaned["current_price"], "price_unit": cleaned["price_unit"],
        "observed_at": cleaned["observed_on"] + "T12:00:00+08:00",
        "mode": "without_last_week", "store_id": None,
    }
