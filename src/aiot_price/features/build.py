"""特徵流水線（T09）：只使用當時已公布資料。

核心防洩漏規則：
- 推論時點 t 可見的最新觀測日 = t − visible_delay_days（發布延遲假設 1 日，
  與 LABEL_CONTRACT.md publish_delay_days 一致）。
- 所有滾動統計只向後看（merge_asof backward）；未來資料擾動不得改變過去特徵。
- 本模組不做任何「全域 fit」；無需訓練集擬合的縮放／填補，模型端自帶（T12）。
- 訓練與推論共用 build_features()：同一輸入→同一特徵。
"""

from __future__ import annotations

import pandas as pd

VISIBLE_DELAY_DAYS = 1  # 觀測日 +1 才可見；實測發布延遲後更新並記錄

FEATURE_COLUMNS = [
    "price_last",
    "price_last_age_days",
    "ma7",
    "ma14",
    "ma28",
    "std14",
    "ret_7d",
    "ret_14d",
    "min14",
    "max14",
    "dow",
    "month",
]

CATEGORICAL_COLUMNS = ["crop_id", "market_id"]


def visible_asof_date(t: pd.Timestamp, delay_days: int = VISIBLE_DELAY_DAYS) -> pd.Timestamp:
    """t 時點可見的最新觀測日：t−delay（含當日無法見）。"""
    return t - pd.Timedelta(days=delay_days)


def _asof_by_group(
    left: pd.DataFrame, right: pd.DataFrame, left_on: str, right_on: str
) -> pd.DataFrame:
    """依 (market_id, crop_id) 分組做 merge_asof；規避 pandas 要求 on 鍵全域排序的限制。"""
    parts = []
    right_by = dict(tuple(right.groupby(["market_id", "crop_id"])))
    for key, lg in left.groupby(["market_id", "crop_id"], sort=False):
        rg = right_by.get(key)
        if rg is None or len(rg) == 0:
            parts.append(lg)
            continue
        merged = pd.merge_asof(
            lg.sort_values(left_on),
            rg.sort_values(right_on),
            left_on=left_on,
            right_on=right_on,
            direction="backward",
            suffixes=("", "_right"),
        )
        # by 鍵會以 _right 後綴重複帶入（market_id_right 等），丟棄避免欄名重複
        merged = merged.drop(
            columns=[c for c in merged.columns if c.endswith("_right")], errors="ignore"
        )
        parts.append(merged)
    out = pd.concat(parts, ignore_index=True)
    return out


def build_features(
    long_df: pd.DataFrame,
    t_dates: pd.DatetimeIndex | list,
    delay_days: int = VISIBLE_DELAY_DAYS,
) -> pd.DataFrame:
    """對每個 (market_id, crop_id, t) 產生只用當時可見資料的特徵。

    long_df：market_id, date, crop_raw(已映射為 crop_id), price（元/台斤，正價或 NaN）
    回傳：index (market_id, crop_id, t)，欄位 FEATURE_COLUMNS。
    該組合在 t 前完全無可見價格 → price_last NaN（上層轉 insufficient_data）。
    """
    df = long_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if "crop_id" not in df.columns:
        df["crop_id"] = df["crop_raw"]

    # 建立目標格：markets × crops × t_dates
    # 組合取自「dropna 前」：無歷史價格的組合仍須產生 price_last=NaN 的列，
    # 推論端才能回 insufficient_data 而不是查無此列。
    markets = sorted(df["market_id"].unique())
    crops = sorted(df["crop_id"].unique())
    df = df.dropna(subset=["price"]).sort_values("date")

    if df.empty:
        # 連一筆正價格都沒有：回全 NaN 特徵（推論端轉 insufficient_data）
        grid = pd.MultiIndex.from_product(
            [markets, crops, pd.DatetimeIndex(t_dates)], names=["market_id", "crop_id", "t"]
        ).to_frame(index=False)
        for col in FEATURE_COLUMNS:
            grid[col] = float("nan")
        return grid.set_index(["market_id", "crop_id", "t"]).sort_index()
    grid = pd.MultiIndex.from_product(
        [markets, crops, pd.DatetimeIndex(t_dates)], names=["market_id", "crop_id", "t"]
    ).to_frame(index=False)

    grid["visible_asof"] = grid["t"] - pd.Timedelta(days=delay_days)

    # 最新可見價：每 (market, crop) 序列 as-of backward
    hist = df.rename(columns={"date": "obs_date"})[["market_id", "crop_id", "obs_date", "price"]]
    grid = _asof_by_group(grid, hist, left_on="visible_asof", right_on="obs_date").rename(
        columns={"price": "price_last", "obs_date": "last_obs_date"}
    )
    # 市場有列但價格全 NaN（如南屯市場甘藍）：merge 後無 hist 欄，補 NaN 保持列存在
    if "price_last" not in grid.columns:
        grid["price_last"] = float("nan")
    if "last_obs_date" not in grid.columns:
        grid["last_obs_date"] = pd.NaT
    grid["price_last_age_days"] = (grid["t"] - grid["last_obs_date"]).dt.days

    # 滾動統計：對每 (market, crop) 日曆窗口（min_periods=1）
    hist_idx = df.set_index("date").sort_index()
    roll_frames = []
    for (market, crop), g in hist_idx.groupby(["market_id", "crop_id"]):
        g = g[~g.index.duplicated(keep="last")]
        w7 = g["price"].rolling("7D", min_periods=1).mean()
        w14 = g["price"].rolling("14D", min_periods=1)
        w28 = g["price"].rolling("28D", min_periods=1).mean()
        roll_frames.append(
            pd.DataFrame(
                {
                    "market_id": market,
                    "crop_id": crop,
                    "obs_date": g.index,
                    "ma7": w7.values,
                    "ma14": w14.mean().values,
                    "ma28": w28.values,
                    "std14": w14.std().values,
                    "min14": w14.min().values,
                    "max14": w14.max().values,
                }
            )
        )
    roll = pd.concat(roll_frames, ignore_index=True)
    grid = _asof_by_group(grid, roll, left_on="visible_asof", right_on="obs_date")

    # 7/14 天報酬：可見最新價相對 7/14 天前可見價的變化（向後看）
    grid = _add_backward_returns(grid, hist, delay_days)

    grid["dow"] = grid["t"].dt.dayofweek
    grid["month"] = grid["t"].dt.month

    keep = ["market_id", "crop_id", "t"] + FEATURE_COLUMNS
    return grid[keep].set_index(["market_id", "crop_id", "t"]).sort_index()


def _add_backward_returns(grid: pd.DataFrame, hist: pd.DataFrame, delay_days: int) -> pd.DataFrame:
    """ret_7d/ret_14d：可見最新價相對 7/14 天前可見價的變化。"""
    out_frames = []
    hist_sorted = hist.sort_values(["market_id", "crop_id", "obs_date"])
    for (market, crop), g in hist_sorted.groupby(["market_id", "crop_id"]):
        g = g.set_index("obs_date")
        g = g[~g.index.duplicated(keep="last")]
        s = g["price"]
        # reindex 到完整日曆日，向後填最新可見價（只用過去）
        cal = pd.date_range(s.index.min(), s.index.max(), freq="D")
        filled = s.reindex(cal).ffill()
        ret7 = (filled / filled.shift(7) - 1).rename("ret_7d")
        ret14 = (filled / filled.shift(14) - 1).rename("ret_14d")
        frame = pd.concat([filled.rename("price_filled"), ret7, ret14], axis=1)
        frame["market_id"] = market
        frame["crop_id"] = crop
        frame["obs_date"] = frame.index
        out_frames.append(frame.reset_index(drop=True))
    rets = pd.concat(out_frames, ignore_index=True)
    grid = _asof_by_group(
        grid,
        rets[["market_id", "crop_id", "obs_date", "ret_7d", "ret_14d"]],
        left_on="visible_asof",
        right_on="obs_date",
    )
    return grid


def perturbation_check(
    long_df: pd.DataFrame, t: pd.Timestamp, delay_days: int = VISIBLE_DELAY_DAYS
) -> bool:
    """驗收用：把 t（含）之後的資料亂改，特徵不得變化。"""
    import numpy as np

    before = build_features(long_df, [t], delay_days=delay_days)
    perturbed = long_df.copy()
    mask = pd.to_datetime(perturbed["date"]) >= t
    rng = np.random.default_rng(0)
    perturbed.loc[mask, "price"] = perturbed.loc[mask, "price"] * rng.uniform(
        5, 10, size=int(mask.sum())
    )
    after = build_features(perturbed, [t], delay_days=delay_days)
    cols = [c for c in FEATURE_COLUMNS if c in before.columns and c in after.columns]
    return before[cols].equals(after[cols])
