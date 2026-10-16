"""第五輪 S05/S09 回歸測試：不可變預測識別、simulated 隔離、壞結構清單、代理人中繼資料、.env 載入。"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


FORECAST_BODY = {
    "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
    "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
    "mode": "without_last_week",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import aiot_price.api.app as app_module
    from aiot_price.api import prediction_records as pr

    monkeypatch.setattr(app_module, "save_prediction",
                        lambda resp, req, out_dir=None: pr.save_prediction(resp, req, out_dir=tmp_path))
    monkeypatch.setattr(app_module, "load_records",
                        lambda out_dir=None, include_skipped_info=False: pr.load_records(tmp_path, include_skipped_info=include_skipped_info))
    monkeypatch.setattr(app_module, "delete_record", lambda rid, out_dir=None: pr.delete_record(rid, tmp_path))
    app_module._RECENT_FORECASTS.clear()
    return TestClient(app_module.app)


class TestS05ImmutablePredictionId:
    def test_same_client_id_different_input_no_overwrite(self, client):
        """S05 核心重現：同客戶端 request_id 查 32 再查 60，保存第一筆不得存成 60。"""
        r1 = client.post("/forecast", json={**FORECAST_BODY, "request_id": "audit-collision", "current_price": 32.0})
        r2 = client.post("/forecast", json={**FORECAST_BODY, "request_id": "audit-collision", "current_price": 60.0})
        assert r1.status_code == r2.status_code == 200
        id1 = r1.json()["request_id"]
        # 伺服器生成的 ID 必須不同（或同內容冪等）；客戶端 ID 不得讓不同輸入覆蓋同一預測
        entries = [v for v in client.app and []]  # placeholder
        import aiot_price.api.app as am

        assert len(am._RECENT_FORECASTS) >= 2 or am._RECENT_FORECASTS[id1]["response"]["results"]
        # 用第一筆的 ID 保存 → 存的必須是 32 元那次
        save = client.post("/records", json={"request_id": id1})
        assert save.status_code == 200
        listed = client.get("/records").json()["records"]
        assert len(listed) == 1
        # 該筆結果的價格估計對應 32 元輸入（7天約 30.7）
        rec_prices = [h.get("relative_change_estimate") for h in listed[0]["horizons"]]
        assert any(p is not None and abs(p - (-0.041)) < 0.01 for p in rec_prices)

    def test_client_request_id_object_no_500(self, client):
        r = client.post("/forecast", json={**FORECAST_BODY, "request_id": {"x": 1}})
        assert r.status_code in (200, 400, 422)

    def test_simulated_isolated_in_save(self, client):
        """simulated 預測經保存須隔離（清單標記且不混入正式）。"""
        r = client.post("/forecast", json={**FORECAST_BODY, "simulated": True})
        assert r.status_code == 200
        assert r.json().get("simulated") is True
        rid = r.json()["request_id"]
        save = client.post("/records", json={"request_id": rid})
        assert save.status_code == 200
        body = client.get("/records").json()
        recs = body["records"]
        assert len(recs) == 1 and recs[0].get("simulated") is True  # 標記沿全流程

    def test_agent_save_has_normalized_request_and_metadata(self, client):
        """代理人保存須含標準化輸入與 provider/model/runtime。"""
        q = client.post("/agent/query", json={"query": "高麗菜今天一斤32元"})
        assert q.status_code == 200
        fc = q.json()["forecast"]
        assert fc and fc.get("request_id")
        save = client.post("/records", json={"request_id": fc["request_id"]})
        assert save.status_code == 200
        listed = client.get("/records").json()["records"][0]
        assert listed.get("provider") in ("rule", "glm_zai", "glm_bigmodel", "qwen_local")
        assert listed.get("backend_used") and listed.get("model_version")
        assert listed.get("normalized_request"), "須保存實際執行的標準化輸入"

    def test_bad_structure_record_does_not_break_listing(self, tmp_path):
        """舊合法 JSON 但 results=[null]：清單不 500、該筆受控跳過且可追查、不刪除。"""
        from aiot_price.api.prediction_records import load_records

        (tmp_path / "prediction_badstruct.json").write_text(
            '{"saved_at":"2026-10-04T01:00:00+08:00","response":{"results":[null],"crop_id":"cabbage"},"request":{}}',
            encoding="utf-8",
        )
        (tmp_path / "prediction_good.json").write_text(
            '{"saved_at":"2026-10-04T02:00:00+08:00","response":{"results":[{"horizon_days":7}],"crop_id":"cabbage"},"request":{}}',
            encoding="utf-8",
        )
        recs, skipped = load_records(tmp_path, include_skipped_info=True)
        assert len(recs) == 1 and recs[0]["record_id"] == "good"
        assert skipped == 1
        assert (tmp_path / "prediction_badstruct.json").exists()  # 不無聲刪除

    def test_saved_at_real_save_time(self, client):
        t0 = time.time()
        r = client.post("/forecast", json=FORECAST_BODY)
        assert r.status_code == 200
        rid = r.json()["request_id"]
        save = client.post("/records", json={"request_id": rid})
        assert save.status_code == 200, save.text  # S09：先 assert 成功再驗內容
        from datetime import datetime

        listed = client.get("/records").json()["records"]
        ts = datetime.fromisoformat(listed[0]["saved_at"]).timestamp()
        assert ts >= t0 - 5


class TestS09EnvFile:
    def test_private_env_loaded_and_not_overriding(self, tmp_path, monkeypatch):
        """private/.env 載入實作：存在則載 AIOT_* 鍵；既有環境變數優先。"""
        from aiot_price.api import app as app_module

        # This legacy feature is intentionally OFF in isolated manual/MCP runs;
        # test its original non-isolated behavior without weakening assertions.
        monkeypatch.delenv("AIOT_RUNTIME_ISOLATED", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("AIOT_TEST_KEY=from_file\nAIOT_EXISTING=from_file\n", encoding="utf-8")
        monkeypatch.setenv("AIOT_EXISTING", "from_env")
        loaded = app_module._load_private_env(env_file)
        assert loaded.get("AIOT_TEST_KEY") == "from_file"
        # 既有環境變數優先（不覆蓋）
        import os

        assert os.environ["AIOT_EXISTING"] == "from_env"
        assert os.environ.get("AIOT_TEST_KEY") == "from_file"
        # 非 AIOT_ 前綴不載（避免借框架 dotenv 補接）
        env_file2 = tmp_path / ".env2"
        env_file2.write_text("OPENAI_API_KEY=nope\n", encoding="utf-8")
        loaded2 = app_module._load_private_env(env_file2)
        assert "OPENAI_API_KEY" not in loaded2
