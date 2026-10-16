"""Reproducible FULL 61-column Taichung market catalog from the frozen source.

It does NOT modify source data, release 0.1.0, selected RF/HGB weights,
chatgpt MCP schemas, Windows Web or private price records.
Official zeros are missing (never a free/zero-price entry).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/taichung/retail_prices_20261003.json"
MARKET = "\u5e02\u5834\u540d\u7a31"
OBS_DATE = "\u8a2a\u50f9\u65e5\u671f"
FROZEN_BY_COLUMN = {
    1: "sponge_gourd",
    8: "bok_choy",
    10: "cabbage",
}
ALIASES = {
    1: ["菜瓜", "角瓜"],
    2: ["小黃瓜", "花胡瓜"],
    3: ["大白菜", "山東白菜", "結球白菜"],
    4: ["白蘿蔔", "菜頭"],
    5: ["紅蘿蔔"],
    6: ["蔥", "香蔥"],
    7: ["大黃瓜"],
    8: ["青江菜", "小青江"],
    9: ["空心菜", "蕹菜"],
    10: ["高麗菜", "甘藍"],
    17: ["番木瓜"],
    38: ["玉女番茄", "小番茄"],
    39: ["聖女番茄", "小番茄"],
    40: ["花菜", "青花菜"],
    41: ["洋蔥"],
    42: ["大蒜", "蒜"],
    56: ["蛋", "雞蛋"],
}

CATEGORIES = [
    {"id": "vegetable", "label": "蔬菜", "order": 0},
    {"id": "fruit", "label": "水果", "order": 1},
    {"id": "seafood", "label": "魚與海鮮", "order": 2},
    {"id": "meat", "label": "肉類", "order": 3},
    {"id": "egg", "label": "蛋類", "order": 4},
]


def category(index: int) -> str:
    if index <= 10 or 38 <= index <= 42:
        return "vegetable"
    if 11 <= index <= 37:
        return "fruit"
    if 43 <= index <= 49:
        return "seafood"
    if 56 <= index <= 57:
        return "egg"
    return "meat"


def _price(value: object) -> float | None:
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Output exists; refuse to replace a prior catalog")
    rows = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows or len(rows[0]) != 63:
        raise ValueError("Expected frozen Taichung 63-field retail JSON")
    price_fields = [name for name in rows[0] if name not in (MARKET, OBS_DATE)]
    if len(price_fields) != 61:
        raise ValueError("Expected 61 public source price columns")
    if [price_fields[i - 1] for i in (1, 8, 10)] != [
        "\u7d72\u74dc", "\u9752\u6c5f\u767d\u83dc", "\u7518\u85cd\uff08\u5e73\u5730\u9ad8\u9e97\u83dc\uff09"
    ]:
        raise ValueError("Frozen first-version crops no longer match source column order")

    active = [r for r in rows if isinstance(r, dict) and
              isinstance(r.get(MARKET), str) and not r[MARKET].startswith("(停)") and
              isinstance(r.get(OBS_DATE), str) and len(r[OBS_DATE]) == 8]
    markets = sorted({r[MARKET] for r in active})
    if len(markets) != 13:
        raise ValueError("Expected exactly 13 supported active markets")
    source_cutoff = max(
        datetime.strptime(r[OBS_DATE], "%Y%m%d").date() for r in active
    ).isoformat()
    history: dict[str, dict[str, dict[str, float]]] = {}
    zeros = collections.Counter()
    for idx, name in enumerate(price_fields, start=1):
        crop_id = FROZEN_BY_COLUMN.get(idx, f"taichung_{idx:02d}")
        by_market: dict[str, dict[str, float]] = {}
        for row in active:
            market = row[MARKET]
            observed = datetime.strptime(row[OBS_DATE], "%Y%m%d").date().isoformat()
            value = _price(row.get(name))
            if value is None:
                if str(row.get(name)).strip() == "0":
                    zeros[crop_id] += 1
                continue
            dates = by_market.setdefault(market, {})
            if observed in dates and dates[observed] != value:
                raise ValueError(f"Conflicting same-market/date quote: {crop_id}")
            dates[observed] = value
        history[crop_id] = by_market

    entries = []
    for idx, field in enumerate(price_fields, 1):
        crop_id = FROZEN_BY_COLUMN.get(idx, f"taichung_{idx:02d}")
        groups = history[crop_id]
        market_stats = {}
        for market in markets:
            data = groups.get(market, {})
            if data:
                last_date = max(data)
                market_stats[market] = {
                    "observations": len(data),
                    "latest_observed_date": last_date,
                    "latest_public_market_mean": data[last_date],
                }
            else:
                market_stats[market] = {
                    "observations": 0, "latest_observed_date": None,
                    "latest_public_market_mean": None
                }
        entries.append({
            "crop_id": crop_id,
            "display_name": field,
            "category": category(idx),
            "source_column_index": idx,
            "aliases": ALIASES.get(idx, []),
            "method": "frozen_rf_hgb_v0.1.0" if idx in FROZEN_BY_COLUMN else "historical_momentum_baseline",
            "has_ever_had_public_price": any(stat["observations"] > 0 for stat in market_stats.values()),
            "total_nonzero_observations": sum(s["observations"] for s in market_stats.values()),
            "missing_zeros": zeros[crop_id],
            "markets": market_stats,
        })
    # Match first-version exactly. The approved frozen model must remain on
    # its own pinned three-crop data and MCP contract, not be retrained here.
    assert len(entries) == 61
    assert sum(e["category"] == "vegetable" for e in entries) == 15
    assert sum(e["category"] == "fruit" for e in entries) == 27
    assert sum(e["has_ever_had_public_price"] for e in entries) == 60

    structured = {
        "schema_version": "1",
        "source_dataset": "data.gov.tw/84539",
        "source_sha256": _sha(source),
        "source_observation_cutoff": source_cutoff,
        "source_mean_unit": "NTD_per_taiwan_jin",
        "source_zero_means_missing": True,
        "markets": markets,
        "categories": CATEGORIES,
        "items": entries,
        "scope_warning": "61 公開來源價格欄不等於全臺所有蔬菜；內含水果及魚肉蛋。",
        "model_warning": "只有原三種使用凍結 RF/HGB；其他有資料者採未訓練且未經真店驗證的歷史趨勢基準，資料不足時不預測。",
        "no_price_crop_count": 1,
    }
    # Minimal history storage: exact date, real positive market mean,
    # sorted by date. All zeros/missing were excluded; no synthetic prices.
    compact = {
        crop: {market: [[day, price] for day, price in sorted(dates.items())]
               for market, dates in groups.items()}
        for crop, groups in history.items()
    }
    output.mkdir(parents=True)
    catalog_file = output / "catalog.json"
    history_file = output / "public_history.json.gz"
    catalog_file.write_text(json.dumps(structured, ensure_ascii=False, separators=(",", ":")),
                            encoding="utf-8")
    with gzip.open(history_file, "wt", encoding="utf-8", compresslevel=9) as stream:
        json.dump(compact, stream, ensure_ascii=False, separators=(",", ":"))
    manifest = {
        "catalog_schema": "1",
        "built_from_existing_source_only": True,
        "source_sha256": _sha(source),
        "source_cutoff": source_cutoff,
        "catalog_sha256": _sha(catalog_file),
        "history_sha256": _sha(history_file),
        "item_count": len(entries),
        "with_data": sum(x["has_ever_had_public_price"] for x in entries),
        "category_counts": dict(collections.Counter(x["category"] for x in entries)),
        "frozen_original_crop_ids": sorted(FROZEN_BY_COLUMN.values()),
        "unchanged_origin_mcp_contract": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(SOURCE, args.output), indent=2, ensure_ascii=False))
