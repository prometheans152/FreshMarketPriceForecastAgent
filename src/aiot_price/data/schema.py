"""品項／單位標準化 schema（T09）。

責任：
- crop_id ↔ 臺中來源原始欄位名／市面別名映射；未知品項拒絕（不猜品種）。
- 單位換算：元/台斤 ↔ 元/公斤（1 臺斤＝0.6 公斤，標準檢驗局衡器規範）。
- 不可比單位（顆/把/袋、未知重量）攔截：不得換算或併入每斤資料。
映射表來源 configs/project.yaml；修改需同步 T02 schema 與 DECISIONS.md。
"""

from __future__ import annotations

from dataclasses import dataclass


class UnitError(ValueError):
    """單位不可比或未知：呼叫端須回使用者可懂錯誤，不得默默換算。"""


COMPARABLE_UNITS = ("NTD_per_taiwan_jin", "NTD_per_kg")
NON_COMPARABLE_UNITS = ("per_piece", "per_bunch", "per_bag", "per_pack", "unknown")
TAIWAN_JIN_TO_KG = 0.6


@dataclass(frozen=True)
class CropMapping:
    crop_id: str
    display_name: str
    source_column: str
    aliases: tuple


# 與 configs/project.yaml crops.first_version 同步
CROP_MAPPINGS: dict[str, CropMapping] = {
    "cabbage": CropMapping("cabbage", "甘藍（平地高麗菜）", "甘藍（平地高麗菜）", ("高麗菜", "甘藍", "啦啦")),
    "bok_choy": CropMapping("bok_choy", "青江白菜", "青江白菜", ("青江菜", "小青江")),
    "sponge_gourd": CropMapping("sponge_gourd", "絲瓜", "絲瓜", ("菜瓜", "角瓜")),
}

_SOURCE_TO_ID = {m.source_column: cid for cid, m in CROP_MAPPINGS.items()}
_ALIAS_TO_ID = {a: cid for cid, m in CROP_MAPPINGS.items() for a in m.aliases}


def resolve_crop(text: str) -> str:
    """把使用者輸入或來源欄名解析成 crop_id；未知丟 KeyError（呼叫端回 unsupported_crop）。"""
    t = (text or "").strip()
    if t in CROP_MAPPINGS:
        return t
    if t in _SOURCE_TO_ID:
        return _SOURCE_TO_ID[t]
    if t in _ALIAS_TO_ID:
        return _ALIAS_TO_ID[t]
    raise KeyError(f"unsupported crop: {t!r}")


def to_taiwan_jin(price: float, unit: str) -> float:
    """把可換算單位價格統一為元/台斤；不可比單位丟 UnitError。"""
    if unit == "NTD_per_taiwan_jin":
        return float(price)
    if unit == "NTD_per_kg":
        # 每公斤價 × 0.6 ＝ 每台斤價（1 臺斤 = 0.6 kg）
        return float(price) * TAIWAN_JIN_TO_KG
    raise UnitError(
        f"單位 {unit!r} 無重量資訊，無法與每斤均價比較；請改輸入元/台斤或元/公斤"
    )


def supported_crops() -> dict[str, str]:
    return {cid: m.display_name for cid, m in CROP_MAPPINGS.items()}
