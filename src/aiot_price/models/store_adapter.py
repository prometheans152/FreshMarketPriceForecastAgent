"""店價適配：有／無上週店價兩種路徑（T14）。

誠實邊界（MODEL_VALIDATION_PLAN §4）：
- A（無上週）：公開模型 r × 今天店價＝現價錨定店價估計；方向＝公開市場方向。
  正價格錨定不改變方向 → 不得宣稱「現價輸入改善方向」。
- B（有上週）：**實驗性規則原型**（未經同店資料訓練/驗證）：
  r_B = r_A + ALPHA × (店價一週變化 − 公開同期一週變化)。
  ALPHA=0.3 為開發期固定係數；輸出一律標 experimental、validation_scope=unvalidated。
- B 可比性檢查：previous_observed_at 需在 [t−9, t−5]（7±2 天）、單位可比（kg↔斤換算後比較）、
  品項/規格同（specification 不一致時拒 B 保 A）。
- 禁止：以 0 或公開均價代填上週價；把公開 t−7 欄位改名的資料當 B 的私人增益證據。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

ALPHA_EXPERIMENTAL = 0.3
TOLERANCE_DAYS = 2  # configs/project.yaml mode_b.previous_week_tolerance_days

B_REJECT_OUT_OF_WINDOW = "previous_observed_at 距今超過 7±2 天，B 不可用"
B_REJECT_NON_COMPARABLE = "上週價單位不可比（無重量資訊），B 不可用"
B_REJECT_MISSING = "缺少上週價格或日期，B 不可用"


@dataclass
class BInputCheck:
    ok: bool
    reason: str | None = None
    store_week_change: float | None = None  # 店價 p(t-7)→p(t) 相對變化（斤標準化）
    actual_interval_days: int | None = None


def check_b_input(
    t: datetime,
    current_price_jin: float,
    previous_price: float | None,
    previous_price_unit: str | None,
    previous_observed_at: datetime | None,
    specification_consistent: bool = True,
) -> BInputCheck:
    """驗證 B 輸入可比性；回傳店價一週變化（元/台斤口徑）。"""
    from aiot_price.data.schema import UnitError, to_taiwan_jin

    if previous_price is None or previous_observed_at is None:
        return BInputCheck(False, B_REJECT_MISSING)
    if not specification_consistent:
        return BInputCheck(False, "規格/品項標示不一致，B 不可比")
    interval = (t.date() - previous_observed_at.date()).days
    if not (7 - TOLERANCE_DAYS <= interval <= 7 + TOLERANCE_DAYS):
        return BInputCheck(False, B_REJECT_OUT_OF_WINDOW, None, interval)
    try:
        prev_jin = to_taiwan_jin(previous_price, previous_price_unit or "unknown")
    except UnitError:
        return BInputCheck(False, B_REJECT_NON_COMPARABLE, None, interval)
    if prev_jin <= 0 or current_price_jin <= 0:
        return BInputCheck(False, "價格須為正數", None, interval)
    change = current_price_jin / prev_jin - 1
    return BInputCheck(True, None, change, interval)


def experimental_b_return(r_public: float, store_week_change: float, public_week_change: float | None) -> float:
    """實驗性 B 規則：r_B = r_A + ALPHA×(店價週變化 − 公開同期週變化)。

    public_week_change 缺（該市場無同期公開資料）時退回 r_A，並由呼叫端標警示。
    """
    if public_week_change is None:
        return r_public
    return r_public + ALPHA_EXPERIMENTAL * (store_week_change - public_week_change)
