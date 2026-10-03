"""第四輪 R01–R05 回歸測試（先紅後修）。對應第三輪獨立審查 REVIEW_44dabe3.md。"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.service import handle_agent_query, validate_qwen_answer
from aiot_price.agent.tools import parse_query
from aiot_price.models.predict import ForecastEngine

TODAY = date(2026, 10, 4)
RELEASE = Path("models/releases/0.1.0")


@pytest.fixture(scope="module")
def engine():
    if not (RELEASE / "manifest.json").exists():
        pytest.skip("模型包未打包")
    return ForecastEngine(RELEASE)


def _fake_qwen(monkeypatch, reply_text=None, content=None, fail=False):
    """模擬 GLM/Qwen OpenAI 相容回應（僅測應用層防線）。"""
    from aiot_price.agent.service import QwenBackend

    qb = QwenBackend(base_url="http://127.0.0.1:9", model="test", timeout=2.0)

    def fake_urlopen(req, timeout=None):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                if fail:
                    raise OSError("simulated failure")
                msg_content = reply_text if content is None else content
                return json.dumps(
                    {"choices": [{"message": {"content": msg_content}}]}
                ).encode("utf-8")

        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return qb


# ================= R01：工具失敗／缺輸入不得放行捏造回答 =================


class TestR01ToolFailure:
    def test_stale_market_fabricated_answer_rejected(self, engine, monkeypatch):
        """審查重現：南屯市場（stale_data_unusable）＋模擬捏造回答→不得以 qwen 成功呈現。"""
        qb = _fake_qwen(monkeypatch, reply_text="7天後必定上漲99%，售價999元；已驗證。")
        r = handle_agent_query(engine, "南屯市場高麗菜今天一斤32元", backend=qb, today=TODAY)
        assert r["backend_used"] != "qwen" or "999" not in r["answer"], "捏造數字不得以 Qwen 成功呈現"
        # 更強：工具錯誤時不應產生任何預測成功外觀的回答
        assert "無法" in r["answer"] or "不足" in r["answer"] or "999" not in r["answer"]

    def test_missing_input_fabricated_answer_rejected(self, engine, monkeypatch):
        """缺必要輸入＋模擬「下週會大漲，已通過同店實測」→不得通過。"""
        qb = _fake_qwen(monkeypatch, reply_text="下週會大漲，已通過同店實測。")
        r = handle_agent_query(engine, "請問菜價", backend=qb, today=TODAY)
        assert r["backend_used"] != "qwen"
        assert "大漲" not in r["answer"]
        assert "補充" in r["answer"] or "缺" in r["answer"]

    def test_validator_rejects_prediction_claim_without_tool_results(self):
        """驗證器本身：forecast.error 時對預測主張 return True 是缺陷（審查點名的根因）。"""
        tools = {"forecast": {"error": {"code": "stale_data_unusable"}, "results": []}}
        ok, _ = validate_qwen_answer("7天後必定上漲99%，售價999元；已驗證。", tools)
        assert ok is False, "工具錯誤時的預測主張必須被拒，不得 return True"


# ================= R02：數字必須綁定期限／模式／單位 =================

_TOOLS_OK = {
    "forecast": {
        "results": [
            {"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
             "relative_change_estimate": -0.041, "price_estimate": 30.7, "price_estimate_unit": "NTD_per_taiwan_jin"},
            {"horizon_days": 14, "target_date": "2026-10-18", "direction": "flat",
             "relative_change_estimate": -0.009, "price_estimate": 31.7, "price_estimate_unit": "NTD_per_taiwan_jin"},
        ],
        "results_with_last_week": [
            {"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
             "relative_change_estimate": 0.002, "price_estimate": 32.1, "price_estimate_unit": "NTD_per_taiwan_jin"},
        ],
        "public_data_cutoff": "2026-10-02",
        "input_observed_at": "2026-10-04T12:00:00+08:00",
        "error": None,
    }
}


class TestR02NumberBinding:
    def test_horizon_swapped_numbers_rejected(self):
        """審查重現：7/14 數字交換後仍通過是缺陷。"""
        swapped = "7 天後（2026-10-11）大致持平（-0.9%，約 31.7 元）；14 天後（2026-10-18）大致持平（-4.1%，約 30.7 元）。"
        ok, why = validate_qwen_answer(swapped, _TOOLS_OK)
        assert ok is False, f"期限與數字交換必須被拒：{why}"

    def test_cross_mode_numbers_rejected(self):
        """A 結果句子中引用 B 的數字（32.1）必須被拒。"""
        mixed = "7 天後（2026-10-11）大致持平（+0.2%，約 32.1 元）。"
        ok, _ = validate_qwen_answer(mixed, _TOOLS_OK)
        # B 數字出現在未標示 B 模式的句子中：至少需擋下或標示；本測試要求拒絕
        assert ok is False

    def test_chinese_horizon_direction_conflict_rejected(self):
        """審查重現：「一週後會大漲，兩週後也會大漲」繞過阿拉伯數字比對。"""
        bad = "一週後會大漲，兩週後也會大漲。"
        ok, _ = validate_qwen_answer(bad, _TOOLS_OK)
        assert ok is False

    def test_null_content_rejected_not_stringified(self, engine, monkeypatch):
        """審查重現：content=null 被轉成字串 "None" 當正常回答。"""
        qb = _fake_qwen(monkeypatch, content=None)
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=qb, today=TODAY)
        assert r["backend_used"] == "rule"  # null 內容必須降級
        assert "None" not in r["answer"]

    def test_unit_binding_price_with_wrong_unit(self):
        """30.7 元／公斤（工具是台斤）必須被拒——單位綁定。"""
        bad = "7 天後（2026-10-11）大致持平（-4.1%，約 30.7 元／公斤）。"
        ok, _ = validate_qwen_answer(bad, _TOOLS_OK)
        assert ok is False

    def test_faithful_answer_still_passes(self):
        good = (
            "高麗菜從今天 2026-10-04 起算：7 天後（2026-10-11）大致持平（-4.1%，約 30.7 元／台斤）；"
            "14 天後（2026-10-18）大致持平（-0.9%，約 31.7 元／台斤）。公開行情截止 2026-10-02；未經同店驗證。"
        )
        ok, why = validate_qwen_answer(good, _TOOLS_OK)
        assert ok is True, f"正確回答被誤擋：{why}"


# ================= R03：商品／日期／正負號／數量不得默默改寫 =================


class TestR03ParserIntegrity:
    def test_different_crop_previous_rejected(self):
        pq = parse_query("高麗菜今天一斤32元，上週絲瓜一斤28元", today=TODAY)
        assert pq.b_reject_reason and "品項" in pq.b_reject_reason, "跨品項上週價必須拒 B"
        req = pq.to_forecast_request()
        assert req is None or req.get("mode") != "both"

    def test_invalid_explicit_date_not_silently_defaulted(self):
        pq = parse_query("高麗菜今天一斤32元，上週2026-02-30一斤28元", today=TODAY)
        # 無效日期不等於未提供：不得補 t-7
        assert pq.previous_date != date(2026, 9, 27)
        assert pq.b_reject_reason or pq.previous_date is None

    def test_month_day_format_recognized_or_asked(self):
        pq = parse_query("高麗菜今天一斤32元，上週9/1一斤28元", today=TODAY)
        # 9/1 要嘛解析成 2026-09-01，要嘛要求補充；不得默默用 09-27
        assert (pq.previous_date == date(2026, 9, 1)) or (pq.b_reject_reason and pq.previous_date is None)
        assert pq.previous_date != date(2026, 9, 27)

    def test_negative_price_preserved_rejected(self):
        pq = parse_query("高麗菜今天一斤-32元", today=TODAY)
        # 負號不得消失成 32
        assert pq.current_price != 32
        assert pq.missing or pq.current_price is None

    def test_two_jin_total_not_unit_price(self):
        pq = parse_query("高麗菜今天兩斤32元", today=TODAY)
        # 兩斤32是總價：不可當每斤32。可換算16或要求確認。
        if pq.current_price is not None:
            assert pq.current_price == 16, "兩斤總價要嘛換算單價16，要嘛要求確認；不得直接當32"
        else:
            assert pq.missing  # 要求補充也算合格行為


# ================= R04：保存防偽與結構 =================


class TestR04RecordsIntegrity:
    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        import aiot_price.api.app as app_module
        from aiot_price.api import prediction_records as pr

        monkeypatch.setattr(app_module, "save_prediction",
                            lambda resp, req, out_dir=None: pr.save_prediction(resp, req, out_dir=tmp_path))
        monkeypatch.setattr(app_module, "load_records", lambda out_dir=None: pr.load_records(tmp_path))
        monkeypatch.setattr(app_module, "delete_record", lambda rid, out_dir=None: pr.delete_record(rid, tmp_path))
        return TestClient(app_module.app)

    def test_forged_prediction_rejected(self, client):
        """偽造模型版本/request_id/999元/simulated → 拒絕保存。"""
        r = client.post("/records", json={
            "forecast_response": {"model_version": "9.9.9-forged", "request_id": "never-existed",
                                  "results": [{"horizon_days": 7, "direction": "up", "price_estimate": 999}],
                                  "simulated": True, "error": None},
            "request": {"crop_id": "cabbage", "simulated": True},
        })
        assert r.status_code in (401, 403, 404, 422), f"偽造結果不得保存：{r.status_code}"

    def test_results_null_rejected(self, client):
        r = client.post("/records", json={"forecast_response": {"results": [None]}, "request": {}})
        assert 400 <= r.status_code < 500, "results=[null] 須受控拒絕"

    def test_top_level_array_rejected(self, client):
        r = client.post("/records", content=b"[]", headers={"Content-Type": "application/json"})
        assert 400 <= r.status_code < 500, "頂層 [] 須受控 4xx 不 500"

    def test_bad_record_does_not_break_listing(self, tmp_path):
        from aiot_price.api.prediction_records import load_records

        (tmp_path / "prediction_broken.json").write_text("{not json", encoding="utf-8")
        (tmp_path / "prediction_good.json").write_text(
            json.dumps({"saved_at": "2026-10-04T01:00:00+08:00",
                        "response": {"crop_id": "cabbage", "results": [{"horizon_days": 7, "direction": "flat"}]},
                        "request": {}}),
            encoding="utf-8",
        )
        recs = load_records(tmp_path)
        assert len(recs) == 1 and recs[0]["record_id"] == "good"  # 壞檔跳過但不拖垮、不刪除
        assert (tmp_path / "prediction_broken.json").exists()

    def test_saved_at_is_real_save_time(self, client):
        t0 = time.time()
        r = client.post("/records", json={
            "forecast_response": {"crop_id": "cabbage", "results": [], "error": None},
            "request": {"crop_id": "cabbage"},
        })
        # 本測試聚焦 saved_at 語意：POST 回應與 GET 清單的 saved_at 應為伺服器保存時刻（≥ t0）
        if r.status_code == 200:
            listed = client.get("/records").json()["records"]
            from datetime import datetime

            ts = datetime.fromisoformat(listed[0]["saved_at"]).timestamp()
            assert ts >= t0 - 5, "saved_at 應為真實保存時間，不是報價時間"


# ================= R05：選填欄位組合與 store_id 驗證 =================


class TestR05OptionalFieldCombos:
    def _base(self, **kw):
        req = {
            "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
            "mode": "both",
        }
        req.update(kw)
        return req

    def test_previous_date_without_price_no_500(self, engine):
        """審查重現：有 previous_observed_at、缺 previous_price → 500。"""
        resp = engine.forecast(self._base(previous_observed_at="2026-09-27T10:00:00+08:00"))
        assert resp.get("error") is None or resp["error"]["code"] in ("bad_request", "invalid_price", "invalid_date")
        assert len(resp.get("results") or []) >= 0  # 不丟例外

    @pytest.mark.parametrize("prev_price,prev_obs,expect_no_crash", [
        (None, None, True),
        (None, "2026-09-27T10:00:00+08:00", True),
        (28.0, None, True),
        ("28", "2026-09-27T10:00:00+08:00", True),
        (28.0, "not-a-date", True),
        (True, "2026-09-27T10:00:00+08:00", True),
        (float("inf"), "2026-09-27T10:00:00+08:00", True),
    ])
    def test_combos(self, engine, prev_price, prev_obs, expect_no_crash):
        resp = engine.forecast(self._base(previous_price=prev_price, previous_observed_at=prev_obs))
        assert resp is not None and "error" in resp  # 受控回應（不丟例外）

    def test_store_id_object_rejected(self):
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/forecast", json=self._base(store_id={"a": 1}))
        assert 400 <= r.status_code < 500

    def test_store_id_nonanonymous_rejected(self):
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/forecast", json=self._base(store_id="我家巷口的菜店"))
        assert 400 <= r.status_code < 500
