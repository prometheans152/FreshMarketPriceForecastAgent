"""臺中公有零售市場每日蔬果價格：原始 JSON 載入與長表化。

資料特性（見 docs/DATA_CARD.md）：
- 欄位「市場名稱」「訪價日期」(YYYYMMDD 字串)＋61 個品項價格欄（數字字串，元/台斤）。
- 0 代表「該日該品項無價格」＝缺測，不是零元；一律轉 NaN。
- 市場均價非單店真值；(停) 前綴市場為停用狀態，由品質分析決定排除與否。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

KEY_MARKET = "市場名稱"
KEY_DATE = "訪價日期"


@dataclass
class LoadReport:
    """載入統計：異常列必須保留證據，不可靜默丟棄。"""

    source_path: str = ""
    n_rows_raw: int = 0
    n_rows_long: int = 0
    n_zero_as_missing: int = 0
    n_parse_failed: dict = field(default_factory=dict)  # crop -> 次數（無法轉數字）
    n_negative: dict = field(default_factory=dict)  # crop -> 次數（負值，視為異常缺測）
    markets: list = field(default_factory=list)
    date_min: str = ""
    date_max: str = ""

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "n_rows_raw": self.n_rows_raw,
            "n_rows_long": self.n_rows_long,
            "n_zero_as_missing": self.n_zero_as_missing,
            "n_parse_failed": self.n_parse_failed,
            "n_negative": self.n_negative,
            "markets": self.markets,
            "date_min": self.date_min,
            "date_max": self.date_max,
        }


def load_taichung_long(json_path: str | Path, crop_columns: list[str] | None = None) -> tuple[pd.DataFrame, LoadReport]:
    """讀原始 JSON 轉長表。

    回傳 (long_df, report)。long_df 欄位：
    - market_id（原文市場名稱，含 (停) 前綴，由上層決定排除）
    - date（datetime，訪價日）
    - crop_raw（原始品項欄名；crop_id 標準化映射在 features/schema 處理）
    - price（float；0/負值/解析失敗 → NaN，計入 report）
    """
    json_path = Path(json_path)
    with open(json_path, encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        raise ValueError(f"預期 JSON 為列陣列，取得 {type(rows)}")

    report = LoadReport(source_path=str(json_path), n_rows_raw=len(rows))
    if crop_columns is None:
        crop_columns = [k for k in rows[0].keys() if k not in (KEY_MARKET, KEY_DATE)]

    records = []
    for r in rows:
        market = r.get(KEY_MARKET, "")
        date_str = str(r.get(KEY_DATE, ""))
        try:
            date = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            report.n_parse_failed.setdefault(KEY_DATE, 0)
            report.n_parse_failed[KEY_DATE] += 1
            continue
        for crop in crop_columns:
            raw = r.get(crop)
            if raw is None or str(raw).strip() == "":
                continue  # 欄位缺席＝缺測，不產生列
            try:
                price = float(str(raw).strip())
            except ValueError:
                report.n_parse_failed.setdefault(crop, 0)
                report.n_parse_failed[crop] += 1
                price = float("nan")
            else:
                if price == 0:
                    report.n_zero_as_missing += 1
                    price = float("nan")
                elif price < 0:
                    report.n_negative.setdefault(crop, 0)
                    report.n_negative[crop] += 1
                    price = float("nan")
            records.append(
                {"market_id": market, "date": date, "crop_raw": crop, "price": price}
            )

    long_df = pd.DataFrame.from_records(records, columns=["market_id", "date", "crop_raw", "price"])
    report.n_rows_long = len(long_df)
    if len(long_df):
        report.markets = sorted(long_df["market_id"].unique().tolist())
        report.date_min = long_df["date"].min().strftime("%Y-%m-%d")
        report.date_max = long_df["date"].max().strftime("%Y-%m-%d")
    return long_df, report
