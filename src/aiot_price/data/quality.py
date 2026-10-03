"""資料品質與可用範圍分析（T06）。

檢查面向（TASKS T06）：
- 市場＋日期重複鍵、價格缺測/0、日期斷點、品項覆蓋
- 異常值（訓練區分位數僅作描述；正式 sanity 門檻由本報告凍結後寫入 configs）
- 連續沿用價格（懷疑未更新）、(停) 停用市場、跨市場同日完全相同價格、單位一致性（來源單一元/斤）
輸出量化計數與抽樣原始列，報告不含任何「模型已驗證」宣稱。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .load import load_taichung_long


def analyze_quality(long_df: pd.DataFrame) -> dict:
    """對長表執行品質檢查，回傳可 JSON 化的報告 dict。"""
    df = long_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    report: dict = {}

    # 1. 鍵唯一性：市場×日期×品項
    dup_mask = df.duplicated(subset=["market_id", "date", "crop_raw"], keep=False)
    report["duplicate_keys"] = {
        "n_rows": int(dup_mask.sum()),
        "n_groups": int(df.loc[dup_mask].groupby(["market_id", "date", "crop_raw"]).ngroups),
        "samples": (
            df.loc[dup_mask]
            .head(5)
            .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
            .to_dict("records")
        ),
    }

    # 2. 品項×市場可用性（正價格率）
    per_crop = (
        df.groupby(["crop_raw", "market_id"])["price"]
        .agg(observations="count")
        .reset_index()
    )
    # 觀測格數 = 出現列數（含 NaN）；改以「列數」與「正值數」並列
    per_crop = (
        df.assign(has_price=df["price"].notna())
        .groupby(["crop_raw", "market_id"])
        .agg(rows=("price", "size"), with_price=("has_price", "sum"))
        .reset_index()
    )
    per_crop["coverage"] = (per_crop["with_price"] / per_crop["rows"]).round(4)
    report["per_crop_market_coverage"] = per_crop.to_dict("records")

    # 3. 日期範圍與斷點（全市場合併的觀測日連續性）
    dates = sorted(df["date"].unique())
    date_index = pd.DatetimeIndex(dates)
    gaps = date_index.to_series().diff().dt.days
    big_gaps = gaps[gaps > 1]
    report["observation_dates"] = {
        "n_dates": len(dates),
        "min": date_index.min().strftime("%Y-%m-%d"),
        "max": date_index.max().strftime("%Y-%m-%d"),
        "gaps_over_1_day": [
            {
                "after": (date_index[i - 1]).strftime("%Y-%m-%d"),
                "before": (date_index[i]).strftime("%Y-%m-%d"),
                "gap_days": int(gaps.iloc[i]),
            }
            for i in range(1, len(date_index))
            if gaps.iloc[i] > 1
        ],
    }

    # 4. 連續沿用價格（同市場同品項連續 N 天完全同價）
    df_sorted = df.sort_values(["market_id", "crop_raw", "date"])
    df_sorted["price_same_as_prev"] = (
        df_sorted.groupby(["market_id", "crop_raw"])["price"]
        .transform(lambda s: s.eq(s.shift()) & s.notna())
    )
    runs = []
    for (market, crop), g in df_sorted.groupby(["market_id", "crop_raw"]):
        run = 0
        start = None
        prev_date = None
        for row in g.itertuples():
            if row.price_same_as_prev:
                run += 1
                if run == 1:
                    start = prev_date
            else:
                if run >= 10 and start is not None:  # ≥10 天完全同價視為疑似沿用
                    runs.append(
                        {
                            "market_id": market,
                            "crop_raw": crop,
                            "start": start.strftime("%Y-%m-%d"),
                            "end": prev_date.strftime("%Y-%m-%d"),
                            "days": run + 1,
                        }
                    )
                run = 0
            prev_date = row.date
        if run >= 10 and start is not None:
            runs.append(
                {
                    "market_id": market,
                    "crop_raw": crop,
                    "start": start.strftime("%Y-%m-%d"),
                    "end": prev_date.strftime("%Y-%m-%d"),
                    "days": run + 1,
                }
            )
    report["suspected_carryover_runs_ge10d"] = runs

    # 5. (停) 停用市場概況
    stopped = df[df["market_id"].str.contains("(停)", regex=False)]
    report["stopped_markets"] = (
        stopped.groupby("market_id")
        .agg(rows=("price", "size"), with_price=("price", lambda s: s.notna().sum()),
             date_min=("date", "min"), date_max=("date", "max"))
        .reset_index()
        .assign(
            date_min=lambda x: x["date_min"].dt.strftime("%Y-%m-%d"),
            date_max=lambda x: x["date_max"].dt.strftime("%Y-%m-%d"),
        )
        .to_dict("records")
    )

    # 6. 跨市場同日同品項完全同價（相關性證據，非獨立觀測）
    same_price = (
        df.dropna(subset=["price"])
        .groupby(["crop_raw", "date"])["price"]
        .agg(n_markets_same_day="size", n_distinct_prices="nunique")
        .reset_index()
    )
    identical = same_price[(same_price["n_markets_same_day"] > 1) & (same_price["n_distinct_prices"] == 1)]
    report["cross_market_identical_price"] = {
        "n_crop_date_groups_multi_market": int(
            (same_price["n_markets_same_day"] > 1).sum()
        ),
        "n_groups_all_identical": int(len(identical)),
    }

    # 7. 價格分佈（描述用；正式 sanity 門檻由訓練區決定後另存 configs）
    desc = (
        df.dropna(subset=["price"])
        .groupby("crop_raw")["price"]
        .describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99])
        .round(2)
    )
    report["price_distribution_by_crop"] = json.loads(desc.to_json(orient="index"))

    return report


def run_quality(json_path: str | Path, crop_columns: list[str] | None, out_dir: str | Path) -> dict:
    """載入→分析→寫出 JSON 報告，回傳報告 dict。"""
    long_df, load_report = load_taichung_long(json_path, crop_columns=crop_columns)
    report = analyze_quality(long_df)
    report["load"] = load_report.to_dict()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "quality_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="臺中零售資料品質分析（T06）")
    parser.add_argument("--json", required=True, help="原始 JSON 路徑")
    parser.add_argument("--out-dir", default="outputs/data_quality")
    parser.add_argument("--crops", nargs="*", default=None, help="只分析指定品項欄名")
    args = parser.parse_args()
    rep = run_quality(args.json, args.crops, args.out_dir)
    print(json.dumps({k: rep[k] for k in ("load", "observation_dates", "cross_market_identical_price")}, ensure_ascii=False, indent=2, default=str))
