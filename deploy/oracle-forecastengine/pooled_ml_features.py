"""Leakage-free daily as-of features for new TW01 pooled-crop ML models.

Training and inference call the SAME functions. Input observations must be
positive public market means with calendar-day dates, NOT shop price records.
At forecast origin t, every feature is computed from dates <= t-1 calendar day.
"""
from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd

FEATURES = (
    "last_price_log",
    "last_price_age",
    "ma7_ratio",
    "ma14_ratio",
    "ma28_ratio",
    "std14_ratio",
    "range14_ratio",
    "ret7",
    "ret14",
    "n7",
    "n14",
    "dow",
    "month",
)
VISIBLE_DELAY_DAYS = 1
SEED = 42
FROZEN_CROPS = frozenset(("cabbage", "bok_choy", "sponge_gourd"))
HORIZONS = (7, 14)
EPS = 1e-9


def quotes_as_arrays(quotes: list[list]) -> tuple[np.ndarray, np.ndarray]:
    """Return sorted day ordinal ints and finite positive market means."""
    if not quotes:
        return np.empty(0, np.int32), np.empty(0, np.float64)
    days = np.asarray([date.fromisoformat(row[0]).toordinal() for row in quotes], dtype=np.int32)
    values = np.asarray([float(row[1]) for row in quotes], dtype=np.float64)
    if (np.diff(days) <= 0).any():
        raise ValueError("Public market history dates must be strictly increasing")
    if (not np.isfinite(values).all()) or (values <= 0).any():
        raise ValueError("Public market history must contain only positive prices")
    return days, values


def features_at(
    obs_days: np.ndarray, obs_prices: np.ndarray, origin_days: np.ndarray,
    *, crop_id: str, market_id: str,
) -> pd.DataFrame:
    """Vectorized features for t, using as-of t-1 and NEVER t or beyond."""
    origin_days = np.asarray(origin_days, dtype=np.int32)
    if not len(origin_days):
        return pd.DataFrame(columns=[*FEATURES, "crop_id", "market_id"])
    if len(obs_days) != len(obs_prices) or not len(obs_days):
        raise ValueError("No positive training history")
    visible = origin_days - VISIBLE_DELAY_DAYS
    last_idx = np.searchsorted(obs_days, visible, side="right") - 1
    valid_last = last_idx >= 0
    last_price = np.where(valid_last, obs_prices[np.maximum(last_idx, 0)], np.nan)
    last_date = np.where(valid_last, obs_days[np.maximum(last_idx, 0)], -10000)
    age = np.where(valid_last, origin_days - last_date, np.nan)
    prefix_sum = np.r_[0.0, np.cumsum(obs_prices)]
    prefix_sq = np.r_[0.0, np.cumsum(obs_prices ** 2)]
    end = np.searchsorted(obs_days, visible, side="right")

    def window(days: int):
        start = np.searchsorted(obs_days, visible - days + 1, side="left")
        n = end - start
        s = prefix_sum[end] - prefix_sum[start]
        m = np.divide(s, n, out=np.full(len(n), np.nan), where=n > 0)
        variance = np.divide(
            prefix_sq[end] - prefix_sq[start], n, out=np.full(len(n), np.nan), where=n > 0
        ) - m ** 2
        variance = np.maximum(variance, 0)
        return n, m, np.sqrt(variance)

    n7, ma7, _ = window(7)
    n14, ma14, std14 = window(14)
    _, ma28, _ = window(28)
    # A lag is observable only if the last quote at that time is <=7 days old.
    # Purely historical as-of lookups: never use t's or future prices.
    lags = {}
    for delta in (7, 14):
        lag_asof = visible - delta
        ix = np.searchsorted(obs_days, lag_asof, side="right") - 1
        good = ix >= 0
        lag_price = np.where(good, obs_prices[np.maximum(ix, 0)], np.nan)
        lag_age = np.where(good, lag_asof - obs_days[np.maximum(ix, 0)], np.nan)
        lag_price = np.where(lag_age <= 7, lag_price, np.nan)
        lags[delta] = last_price / lag_price - 1

    dates = pd.to_datetime([date.fromordinal(int(i)) for i in origin_days])
    with np.errstate(divide="ignore", invalid="ignore"):
        frame = pd.DataFrame({
            "last_price_log": np.log1p(last_price),
            "last_price_age": age,
            "ma7_ratio": ma7 / last_price - 1,
            "ma14_ratio": ma14 / last_price - 1,
            "ma28_ratio": ma28 / last_price - 1,
            "std14_ratio": std14 / last_price,
            "range14_ratio": np.abs(ma7 - ma14) / last_price,
            "ret7": lags[7],
            "ret14": lags[14],
            "n7": n7,
            "n14": n14,
            "dow": dates.dayofweek.to_numpy(),
            "month": dates.month.to_numpy(),
        })
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame["crop_id"] = crop_id
    frame["market_id"] = market_id
    return frame


def design_matrix(features: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    base = features.loc[:, [*FEATURES, "crop_id", "market_id"]]
    X = pd.get_dummies(
        base, columns=["crop_id", "market_id"], dtype=np.float32
    ).astype(np.float32)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0)
    return X


def training_rows(history: dict, *, excluded: set[str] | frozenset[str] = FROZEN_CROPS):
    """Yield training records from actual public origin-date and target-date pairs.

    Every t in this set has an observed positive public mean at t, but
    features_at() categorically hides that t quote (and anything later).
    Exact calendar t+h label, no next-trading-day interpolation.
    """
    frames = []
    targets = {7: [], 14: []}
    metadata = []
    for crop_id, markets in sorted(history.items()):
        if crop_id in excluded:
            continue
        for market_id, records in sorted(markets.items()):
            days, prices = quotes_as_arrays(records)
            if len(days) < 25:
                continue
            f = features_at(days, prices, days, crop_id=crop_id, market_id=market_id)
            start = len(metadata)
            for day in days:
                metadata.append((crop_id, market_id, int(day)))
            frames.append(f)
            for h in HORIZONS:
                future = days + h
                ix = np.searchsorted(days, future)
                good = ix < len(days)
                matching = np.zeros(len(days), dtype=bool)
                matching[good] = days[ix[good]] == future[good]
                out = np.full(len(days), np.nan)
                out[matching] = np.log(prices[ix[matching]] / prices[matching])
                targets[h].extend(out)
    if not frames:
        raise ValueError("No training rows from public history")
    X_df = pd.concat(frames, ignore_index=True)
    for h in HORIZONS:
        if len(targets[h]) != len(metadata):
            raise AssertionError("Bad feature/label join")
    return X_df, metadata, {h: np.asarray(targets[h]) for h in HORIZONS}
