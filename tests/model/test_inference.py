"""T19 推論測試：fixtures 一致性與同輸入重現。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.models.predict import ForecastEngine

RELEASE = Path("models/releases/0.1.0")


@pytest.fixture(scope="module")
def engine():
    if not (RELEASE / "manifest.json").exists():
        pytest.skip("模型包未打包")
    return ForecastEngine(RELEASE)


class TestFixtures:
    def test_fixtures_reproduce(self, engine):
        fixtures = json.loads((RELEASE / "fixtures.json").read_text(encoding="utf-8"))
        assert fixtures.get("expected"), "fixtures 缺 expected"
        for case in fixtures["expected"]:
            req = next(r for r in fixtures["requests"] if r["request_id"] == case["request_id"])
            got = engine.forecast(req)
            assert got == case["response"], f"fixture {case['request_id']} 不一致"

    def test_manifest_hashes_verified_on_load(self, engine):
        # ForecastEngine 建構時已驗模型檔 hash；再確認 manifest 記錄存在
        for entry in engine.manifest["models"]:
            assert len(entry["sha256"]) == 64

    def test_same_input_same_output(self, engine):
        req = {
            "crop_id": "cabbage",
            "market_id": "中義市場",
            "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin",
            "observed_at": "2026-10-02T10:00:00+08:00",
            "mode": "without_last_week",
        }
        a = engine.forecast(dict(req))
        b = engine.forecast(dict(req))
        a.pop("request_id"); b.pop("request_id")  # 僅時間戳識別不同
        assert a == b  # 推論確定性（無隨機性）

    def test_corrupted_model_hash_rejected(self, tmp_path):
        import hashlib
        import shutil

        if not (RELEASE / "manifest.json").exists():
            pytest.skip("模型包未打包")
        bad_dir = tmp_path / "release"
        shutil.copytree(RELEASE, bad_dir)
        model_file = bad_dir / "model_h7.joblib"
        data = bytearray(model_file.read_bytes())
        data[-1] ^= 0xFF  # 竄改最後一位元組
        model_file.write_bytes(bytes(data))
        with pytest.raises(RuntimeError, match="hash"):
            ForecastEngine(bad_dir)
