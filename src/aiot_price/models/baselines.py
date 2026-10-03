"""可比較基線（T11）。

全部基線與候選模型使用相同特徵表、切分與 7/14 天口徑；
比較一律用完全相同的測試列（feature-ready：price_last 非缺）。

基線清單（MODEL_VALIDATION_PLAN §7）：
- flat 不變價：r_hat=0（方向恆 flat；與「一律不漲」同義）
- 持續趨勢：r_hat = 過去同長度變化（h=7 用 ret_7d、h=14 用 ret_14d）
- 歷史平均報酬：訓練集同品項同 h 的平均 r（依訓練區 fit，僅供基線）
錨定假設（現價×市場倍率不改變方向）在 docs/BASELINE_REPORT.md 註記，不另建模型。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aiot_price.features.build import FEATURE_COLUMNS

FLAT_THRESHOLD = 0.05
EPS = 1e-9


def direction_from_return(r: float | np.ndarray, threshold: float = FLAT_THRESHOLD) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    out = np.where(r > threshold + EPS, "up", np.where(r < -threshold - EPS, "down", "flat"))
    out = np.where(np.isnan(r), "insufficient_data", out)
    return out


def feature_ready(df: pd.DataFrame) -> pd.DataFrame:
    """比較用共同列：特徵齊備且有已成熟標籤（direction 非 insufficient_data）。"""
    ok = df["price_last"].notna() & df["direction"].notna() & (df["direction"] != "insufficient_data")
    return df[ok].copy()


class FlatBaseline:
    name = "flat_no_change"

    def fit(self, df: pd.DataFrame) -> None:
        pass

    def predict_return(self, df: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(df))


class MomentumBaseline:
    name = "past_change_continues"

    def fit(self, df: pd.DataFrame) -> None:
        pass

    def predict_return(self, df: pd.DataFrame) -> np.ndarray:
        # h=7 用過去 7 天變化、h=14 用過去 14 天變化；缺值以 0（持平）代
        out = np.where(
            df["horizon_days"] == 7,
            df["ret_7d"].astype(float),
            df["ret_14d"].astype(float),
        )
        return np.nan_to_num(np.asarray(out, dtype=float), nan=0.0)


class TrainMeanReturnBaseline:
    name = "train_mean_return_by_crop"

    def fit(self, df: pd.DataFrame) -> None:
        self.means_ = df.groupby(["crop_id", "horizon_days"])["relative_change"].mean().to_dict()
        self.global_ = df["relative_change"].mean()

    def predict_return(self, df: pd.DataFrame) -> np.ndarray:
        keys = list(zip(df["crop_id"], df["horizon_days"]))
        return np.asarray(
            [self.means_.get(k, self.global_) for k in keys], dtype=float
        )


BASELINES = [FlatBaseline, MomentumBaseline, TrainMeanReturnBaseline]
