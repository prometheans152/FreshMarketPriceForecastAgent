"""T22 預測紀錄測試：保存/讀回/匿名匯出/模擬拒收。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.api.prediction_records import (
    export_anonymous_summary,
    load_records,
    save_prediction,
)

RESP = {
    "request_id": "r1",
    "mode_executed": "both",
    "model_version": "0.1.0",
    "data_version": "172dffc76e82",
    "public_data_cutoff": "2026-10-02",
    "crop_id": "cabbage",
    "market_id": "中義市場",
    "results": [{"horizon_days": 7, "target_date": "2026-10-09", "direction": "flat"}],
    "results_without_last_week": [],
    "results_with_last_week": [],
    "warnings": [],
    "error": None,
}

REQ = {
    "crop_id": "cabbage",
    "market_id": "中義市場",
    "current_price": 32,
    "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-02T10:00:00+08:00",
    "mode": "both",
    "store_id": "store-a",
}


def test_save_and_load_roundtrip(tmp_path):
    path, saved_at = save_prediction(RESP, REQ, out_dir=tmp_path)
    assert path.exists()
    assert saved_at  # R04：真實保存時間一併回傳
    records = load_records(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["response"]["model_version"] == "0.1.0"
    assert rec["request"]["store_id"] == "store-a"
    # 版本/日期/單位完整保留
    assert rec["response"]["public_data_cutoff"] == "2026-10-02"
    assert rec["request"]["price_unit"] == "NTD_per_taiwan_jin"


def test_simulated_rejected(tmp_path):
    with pytest.raises(ValueError):
        save_prediction(RESP, REQ, out_dir=tmp_path, simulated=True)
    assert load_records(tmp_path) == []


def test_bad_results_structure_rejected_before_save(tmp_path):
    """R04：results=[null] 等壞結構由 API 層驗證擋下；底層保存仍可防禦非 dict 結果。"""
    bad = {**RESP, "results": [None]}
    # 底層不做深驗證（API 層職責），但保存後讀回必須不讓清單崩潰
    path, _ = save_prediction(bad, REQ, out_dir=tmp_path)
    recs = load_records(tmp_path)
    assert len(recs) == 1


def test_export_anonymous(tmp_path):
    save_prediction(RESP, REQ, out_dir=tmp_path)
    out = export_anonymous_summary(tmp_path / "summary.json", out_dir=tmp_path)
    rows = json.loads(Path(out).read_text(encoding="utf-8"))
    assert rows[0]["crop_id"] == "cabbage"
    assert "request" not in rows[0]  # 匿名匯出不含原始輸入
    assert "current_price" not in json.dumps(rows)


def test_load_empty_dir(tmp_path):
    assert load_records(tmp_path / "nope") == []
