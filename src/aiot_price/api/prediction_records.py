"""預測紀錄保存（T22）：凍結當時輸出供日後同店到期核對（T16 用）。

原則（docs/PREDICTION_RECORDS.md / STORE_DATA_PROTOCOL.md）：
- 只在使用者選擇保存時寫入 private/predictions/（git 忽略）。
- 保存當時輸入、A/B、7/14 結果、資料與模型版本——事後不得重算冒充原預測。
- 匯出為匿名 JSON；不強制帳號；拒收 simulated 資料混入真實紀錄。
- 關閉保存不影響查詢功能。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DEFAULT_DIR = "private/predictions"


def save_prediction(response: dict, request: dict, out_dir: str | Path = DEFAULT_DIR, simulated: bool = False) -> Path:
    """把一次預測（請求＋回應）凍結存檔；回傳檔案路徑。"""
    if simulated:
        raise ValueError("模擬預測不得寫入真實紀錄（STORE_DATA_PROTOCOL）")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().astimezone().strftime("%Y%m%d%H%M%S%f")
    record = {
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "request": request,
        "response": response,
        # S05：模擬來源沿全流程保留（請求帶 simulated 或回應含 simulated 都標記）
        "simulated": bool(response.get("simulated") or request.get("simulated")),
    }
    path = out_dir / f"prediction_{ts}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, record["saved_at"]


def _record_structure_ok(rec) -> bool:
    """S05：合法 JSON 但壞結構（如 results=[null]）須受控跳過，不拖垮清單。"""
    resp = rec.get("response")
    if not isinstance(resp, dict):
        return False
    results = resp.get("results")
    if not isinstance(results, list):
        return False
    for r in results:
        if not isinstance(r, dict):
            return False
    return True


def load_records(out_dir: str | Path = DEFAULT_DIR, include_skipped_info: bool = False):
    """讀回預測紀錄；壞 JSON／壞結構跳過但保留原檔（可追查、不無聲刪除）。

    include_skipped_info=True 時回 (records, skipped_count)。
    """
    out_dir = Path(out_dir)
    if not out_dir.exists():
        return ([], 0) if include_skipped_info else []
    records, skipped = [], 0
    for p in sorted(out_dir.glob("prediction_*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            skipped += 1
            continue
        if not _record_structure_ok(rec):
            skipped += 1
            continue
        rec["record_id"] = p.stem.replace("prediction_", "")
        records.append(rec)
    return (records, skipped) if include_skipped_info else records


def delete_record(record_id: str, out_dir: str | Path = DEFAULT_DIR) -> bool:
    """刪除單筆紀錄（F08：使用者刪除權）。ID 僅允許安全字元，防路徑注入。"""
    import re

    if not re.match(r"^[A-Za-z0-9_-]+$", record_id or ""):
        return False
    target = Path(out_dir) / f"prediction_{record_id}.json"
    if not target.exists():
        return False
    target.unlink()
    return True


def export_anonymous_summary(out_path: str | Path, out_dir: str | Path = DEFAULT_DIR) -> Path:
    """匿名彙總（無原始輸入細節），供公開報告引用。"""
    rows = []
    for rec in load_records(out_dir):
        resp = rec["response"]
        rows.append(
            {
                "saved_at": rec["saved_at"],
                "simulated": bool(rec.get("simulated")),
                "crop_id": resp.get("crop_id"),
                "market_id": resp.get("market_id"),
                "mode_executed": resp.get("mode_executed"),
                "model_version": resp.get("model_version"),
                "public_data_cutoff": resp.get("public_data_cutoff"),
                "horizons": [
                    {k: r.get(k) for k in ("horizon_days", "target_date", "direction", "relative_change_estimate")}
                    for r in (resp.get("results") or [])
                ],
            }
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
