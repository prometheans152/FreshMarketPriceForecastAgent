"""第四輪驗證 C/D：同一 ASGI 應用、同事件迴圈的併發 HTTP；無 Content-Length 的串流超限。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.api.app import app


@pytest.fixture()
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


FORECAST_BODY = {
    "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
    "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
    "mode": "without_last_week",
}


class TestConcurrencySameLoop:
    @pytest.mark.asyncio
    async def test_health_not_blocked_by_slow_agent(self, async_client, monkeypatch):
        """同 ASGI app、同事件迴圈：慢 LLM（0.5s）不阻塞 health（審查重現的阻塞情境）。"""
        import urllib.request

        from aiot_price.agent.providers import ProviderProfile, run_agent_loop
        from aiot_price.models.predict import ForecastEngine

        def fake_urlopen(req, timeout=None):
            time.sleep(0.5)
            raise OSError("simulated slow LLM")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        release = Path("models/releases/0.1.0")
        if not (release / "manifest.json").exists():
            pytest.skip("模型包未打包")
        engine = ForecastEngine(release)
        profile = ProviderProfile(name="slow", kind="openai_compat", base_url="http://x/v1",
                                  model="m", max_retries=0, timeout=5)

        async def call_agent():
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: run_agent_loop(engine, "高麗菜今天一斤32元", profile)
            )

        agent_task = asyncio.create_task(call_agent())
        await asyncio.sleep(0.05)  # 讓 agent 先進入等待
        t0 = time.perf_counter()
        r = await async_client.get("/health")
        health_elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert health_elapsed < 0.4, f"health 被慢 LLM 阻塞：{health_elapsed:.3f}s"
        await agent_task

    @pytest.mark.asyncio
    async def test_parallel_forecasts(self, async_client):
        """10 個並發 /forecast 全部成功（threadpool 不互相阻塞）。"""
        bodies = [{**FORECAST_BODY, "current_price": 20.0 + i} for i in range(10)]

        async def one(b):
            r = await async_client.post("/forecast", json=b)
            return r.status_code

        results = await asyncio.gather(*[one(b) for b in bodies])
        assert results == [200] * 10


class TestStreamingLimit:
    @pytest.mark.asyncio
    async def test_chunked_oversized_body_413(self, async_client):
        """無 Content-Length 的 chunked 超限 body → 413（審查 9,198B 情境）。"""
        payload = json.dumps({"query": "x" * 9100}).encode("utf-8")

        async def gen():
            for i in range(0, len(payload), 512):
                yield payload[i : i + 512]

        r = await async_client.post(
            "/agent/query",
            content=gen(),
            headers={"Content-Type": "application/json", "Transfer-Encoding": "chunked"},
        )
        assert r.status_code == 413

    @pytest.mark.asyncio
    async def test_chunked_normal_body_ok(self, async_client):
        payload = json.dumps({"query": "高麗菜今天一斤32元"}).encode("utf-8")

        async def gen():
            yield payload[:10]
            yield payload[10:]

        r = await async_client.post(
            "/agent/query",
            content=gen(),
            headers={"Content-Type": "application/json", "Transfer-Encoding": "chunked"},
        )
        assert r.status_code == 200
        assert r.json()["answer"]
