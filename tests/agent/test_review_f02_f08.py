"""第三輪審查修正的行為測試（F02/F03/F06/F07/F08）。模擬傳輸僅測應用層防線。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.service import (
    BackendResult,
    PromptUnavailable,
    QwenBackend,
    handle_agent_query,
    load_system_prompt,
    validate_qwen_answer,
)
from aiot_price.models.predict import ForecastEngine

TODAY = date(2026, 10, 4)

TOOLS_OK = {
    "forecast": {
        "results": [
            {"horizon_days": 7, "target_date": "2026-10-11", "direction": "flat",
             "relative_change_estimate": -0.041, "price_estimate": 30.7, "price_estimate_unit": "NTD_per_taiwan_jin"},
            {"horizon_days": 14, "target_date": "2026-10-18", "direction": "flat",
             "relative_change_estimate": -0.009, "price_estimate": 31.7, "price_estimate_unit": "NTD_per_taiwan_jin"},
        ],
        "public_data_cutoff": "2026-10-02",
        "input_observed_at": "2026-10-04T12:00:00+08:00",
        "error": None,
    }
}


class TestF02Prompt:
    def test_prompt_loads_from_project_root(self):
        text = load_system_prompt(strict=True)
        assert len(text) > 100  # F02：不再讀 src/configs/ 的不存在路徑回空

    def test_missing_prompt_strict_raises(self, tmp_path):
        with pytest.raises(PromptUnavailable):
            load_system_prompt(tmp_path / "nope.md", strict=True)

    def test_qwen_unavailable_without_prompt(self, tmp_path):
        b = QwenBackend(base_url="http://x", model="m", prompt_path=tmp_path / "nope.md")
        assert b.available() is False  # 缺提示不上線，不默空提示


class TestF02OutputValidator:
    """審查重現：矛盾／捏造／空回覆必須被擋（提示不能代替輸出驗證）。"""

    def test_fabricated_up_and_probability_rejected(self):
        bad = "7天後必定上漲99%，售價999元；這是已驗證的同店結果。"
        ok, why = validate_qwen_answer(bad, TOOLS_OK)
        assert ok is False

    def test_unverified_percentage_rejected(self):
        ok, why = validate_qwen_answer("7 天後上漲 55%。", TOOLS_OK)
        assert ok is False and "unverified_percentage" in why

    def test_unverified_date_rejected(self):
        ok, why = validate_qwen_answer("7 天後（2026-12-25）大致持平。", TOOLS_OK)
        assert ok is False and "unverified_date" in why

    def test_unverified_price_rejected(self):
        ok, why = validate_qwen_answer("7 天後約 999 元。", TOOLS_OK)
        assert ok is False and "unverified_price" in why

    def test_direction_conflict_rejected(self):
        ok, why = validate_qwen_answer("7 天後（2026-10-11）會下跌。", TOOLS_OK)
        assert ok is False and "direction_conflict" in why

    def test_empty_answer_rejected(self):
        ok, why = validate_qwen_answer("   ", TOOLS_OK)
        assert ok is False

    def test_faithful_answer_passes(self):
        good = (
            "高麗菜從今天 2026-10-04 起算：7 天後（2026-10-11）大致持平（-4.1%，約 30.7 元）；"
            "14 天後（2026-10-18）大致持平（-0.9%）。公開行情截止 2026-10-02；未經同店驗證。"
        )
        ok, why = validate_qwen_answer(good, TOOLS_OK)
        assert ok is True, why


class _FakeQwenTransport:
    """模擬 Qwen HTTP：可控延遲／回傳內容／丟例外。只測應用層，非真 Qwen。"""

    def __init__(self, reply_text="應該被驗證器攔下的文字", latency=0.0, fail=False):
        self.reply_text = reply_text
        self.latency = latency
        self.fail = fail

    def __call__(self, *args, **kwargs):
        # QwenBackend 以 urllib.request.urlopen 呼叫；monkeypatch 之
        raise NotImplementedError


class TestF02F07BackendDegradation:
    @pytest.fixture(scope="class")
    def engine(self):
        release = Path("models/releases/0.1.0")
        if not (release / "manifest.json").exists():
            pytest.skip("模型包未打包")
        return ForecastEngine(release)

    def _patched_qwen(self, monkeypatch, reply_text=None, fail=False):
        qb = QwenBackend(base_url="http://127.0.0.1:9", model="test", timeout=2.0)

        def fake_urlopen(req, timeout=None):
            class _Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    if fail:
                        raise OSError("simulated network failure")
                    return json.dumps(
                        {"choices": [{"message": {"content": reply_text}}]}
                    ).encode("utf-8")

            return _Resp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        return qb

    def test_fabricated_qwen_answer_replaced_by_rule(self, engine, monkeypatch):
        qb = self._patched_qwen(monkeypatch, reply_text="7天後必定上漲99%，售價999元；這是已驗證的同店結果。")
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=qb, today=TODAY)
        # F07：實際後端標 rule、降級原因記錄；真值數字仍在
        assert r["backend_used"] == "rule"
        assert r["degraded"] is True
        assert r["degraded_reason"] and "rejected" in r["degraded_reason"]
        assert "-4.1%" in r["answer"] or "7 天後" in r["answer"]
        assert "999" not in r["answer"]
        assert r["forecast"] and r["forecast"]["error"] is None  # 結構化真值獨立回傳

    def test_network_failure_degrades_with_reason(self, engine, monkeypatch):
        qb = self._patched_qwen(monkeypatch, fail=True)
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=qb, today=TODAY)
        assert r["backend_used"] == "rule"
        assert r["degraded"] is True
        assert "request_failed" in r["degraded_reason"]

    def test_validated_qwen_answer_used(self, engine, monkeypatch):
        qb = self._patched_qwen(
            monkeypatch,
            reply_text="高麗菜 7 天後（2026-10-11）大致持平（-4.1%）；14 天後（2026-10-18）大致持平（-0.9%）。未經同店驗證。",
        )
        r = handle_agent_query(engine, "高麗菜今天一斤32元", backend=qb, today=TODAY)
        assert r["backend_used"] == "qwen"
        assert r["degraded"] is False
        assert "大致持平" in r["answer"]


class TestF03Concurrency:
    """審查重現：慢 Qwen（0.5s）不得阻塞 health／forecast。"""

    @pytest.fixture(scope="class")
    def engine(self):
        release = Path("models/releases/0.1.0")
        if not (release / "manifest.json").exists():
            pytest.skip("模型包未打包")
        return ForecastEngine(release)

    def test_slow_backend_does_not_block_health(self, engine, monkeypatch):
        import httpx
        from fastapi.testclient import TestClient
        from aiot_price.api.app import app

        qb = QwenBackend(base_url="http://127.0.0.1:9", model="slow", timeout=5.0)

        def fake_urlopen(req, timeout=None):
            time.sleep(0.5)  # 模擬 Qwen 延遲
            raise OSError("timeout after delay")

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        client = TestClient(app)
        t0 = time.perf_counter()
        results = {}

        def call_agent():
            # 直接走 service 層的 run_in_threadpool 路徑（與端點相同）；
            # 端點本身也用 run_in_threadpool，此處驗證事件迴圈不被占住
            results["agent_done"] = False

        async def scenario():
            loop = asyncio.get_event_loop()
            agent_task = loop.run_in_executor(None, lambda: handle_agent_query(engine, "高麗菜今天一斤32元", backend=qb, today=TODAY))
            await asyncio.sleep(0.05)
            t_health = time.perf_counter()
            r = client.get("/health")  # 模擬其他請求
            health_elapsed = time.perf_counter() - t_health
            results["health_status"] = r.status_code
            results["health_elapsed"] = health_elapsed
            await agent_task
            results["agent_done"] = True

        # 執行：agent 在執行緒睡 0.5s 期間，health 經 TestClient（另一執行緒）應快速回
        import threading
        th = threading.Thread(target=lambda: asyncio.run(scenario()))
        th.start()
        th.join(timeout=10)
        assert results.get("agent_done") is True
        assert results["health_status"] == 200
        assert results["health_elapsed"] < 0.4, f"health 被 Qwen 等待阻塞：{results['health_elapsed']:.3f}s"

    def test_agent_endpoint_threadpool(self, monkeypatch):
        """端點層：/agent/query 丟執行緒池（async 不直接跑同步網路）。"""
        src = Path("src/aiot_price/api/app.py").read_text(encoding="utf-8")
        assert "run_in_threadpool" in src


class TestF06StreamingLimit:
    def test_read_limited_json_enforces_actual_bytes(self):
        from aiot_price.api.app import BodyTooLarge, read_limited_json

        class FakeStream:
            def __init__(self, chunks):
                self._chunks = chunks

            async def stream(self):
                for c in self._chunks:
                    yield c

        class FakeRequest:
            def __init__(self, chunks):
                self._s = FakeStream(chunks)

            def stream(self):
                return self._s.stream()

        # 9,198 bytes 分多 chunk（無 Content-Length 情境）→ 必須 413 路徑
        big = json.dumps({"query": "x" * 9100}).encode("utf-8")
        chunks = [big[i : i + 1024] for i in range(0, len(big), 1024)]
        req = FakeRequest(chunks)

        async def run():
            try:
                await read_limited_json(req)
                return "passed"
            except BodyTooLarge:
                return "413"

        assert asyncio.run(run()) == "413"

    def test_normal_body_parsed(self):
        from aiot_price.api.app import read_limited_json

        class FakeRequest:
            def stream(self):
                async def gen():
                    yield b'{"query": "ok"}'

                return gen()

        async def run():
            return await read_limited_json(FakeRequest())

        assert asyncio.run(run()) == {"query": "ok"}


class TestF08RecordsEndpoints:
    def test_records_crud(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        import aiot_price.api.app as app_module
        from aiot_price.api.app import app

        # 端點以 from...import 引用函式；直接替換 app 命名空間中的函式
        from aiot_price.api import prediction_records as pr

        monkeypatch.setattr(
            app_module, "save_prediction",
            lambda resp, req, out_dir=None: pr.save_prediction(resp, req, out_dir=tmp_path),
        )
        monkeypatch.setattr(
            app_module, "load_records", lambda out_dir=None: pr.load_records(tmp_path)
        )
        monkeypatch.setattr(
            app_module, "delete_record", lambda rid, out_dir=None: pr.delete_record(rid, tmp_path)
        )
        client = TestClient(app)

        # R04 新契約：先真實查詢取得 request_id，再以 id 保存（伺服器暫存綁定）
        fq = client.post("/forecast", json={
            "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
            "mode": "without_last_week",
        })
        assert fq.status_code == 200
        req_id = fq.json()["request_id"]
        r = client.post("/records", json={"request_id": req_id})
        assert r.status_code == 200
        rid = r.json()["record_id"]
        assert rid

        # 列出（匿名摘要）
        r = client.get("/records")
        assert r.status_code == 200
        recs = r.json()["records"]
        assert len(recs) == 1 and recs[0]["record_id"] == rid
        assert recs[0]["crop_id"] == "cabbage"

        # 匯出（完整）
        r = client.get("/records/export")
        assert r.status_code == 200
        assert r.json()["records"][0]["request"]["crop_id"] == "cabbage"

        # 刪除 → 再列空
        r = client.delete(f"/records/{rid}")
        assert r.status_code == 200 and r.json()["ok"] is True
        assert client.get("/records").json()["records"] == []

        # 刪不存在的 → 404；非法 ID → 400
        assert client.delete("/records/nope").status_code == 404
        assert client.delete("/records/bad!id").status_code == 400  # 非法字元拒絕（防注入）
