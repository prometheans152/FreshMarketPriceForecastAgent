"""第四輪：供應商無關代理人迴圈的離線協議測試（mock 傳輸；真 ForecastEngine）。

標示：這些測試用模擬的 OpenAI 相容回應驗證「應用層迴圈」——
tool_calls 解析、白名單、參數驗證、工具執行、結果回送、輸出防線、降級。
不是真 GLM/Qwen 品質驗證。
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.providers import (
    ALLOWED_ARG_KEYS,
    OpenAICompatProvider,
    ProviderProfile,
    TOOL_NAMES,
    _execute_tool,
    load_profiles,
    resolve_active_profile,
    run_agent_loop,
)
from aiot_price.agent.tools import AgentTools
from aiot_price.models.predict import ForecastEngine

TODAY = date(2026, 10, 4)
RELEASE = Path("models/releases/0.1.0")


@pytest.fixture(scope="module")
def engine():
    if not (RELEASE / "manifest.json").exists():
        pytest.skip("模型包未打包")
    return ForecastEngine(RELEASE)


def _ok_forecast_answer() -> str:
    return (
        "高麗菜從今天 2026-10-04 起算：7 天後（2026-10-11）大致持平（-4.1%，約 30.7 元／台斤）；"
        "14 天後（2026-10-18）大致持平（-0.9%，約 31.7 元／台斤）。公開行情截止 2026-10-02；未經同店驗證。"
    )


class _MockTransport:
    """依序回放預設回應的模擬 OpenAI 相容伺服器。"""

    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.received: list[dict] = []

    def install(self, monkeypatch):
        transport = self

        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            transport.received.append(body)
            if not transport.responses:
                raise OSError("no more mock responses")

            class _Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps(transport.responses.pop(0)).encode("utf-8")

            return _Resp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


def _tool_call_resp(calls: list[dict], content=None) -> dict:
    return {"choices": [{"message": {"content": content, "tool_calls": calls}, "finish_reason": "tool_calls"}]}


def _text_resp(text: str) -> dict:
    return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}


def _call(name: str, args: dict, cid="c1") -> dict:
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


PROFILE = ProviderProfile(
    name="mock_openai", kind="openai_compat", base_url="http://mock/v1",
    model="mock-model", timeout=2, max_turns=4, max_tool_calls=4, max_retries=0,
)


class TestProfileResolution:
    def test_profiles_loaded(self):
        ps = load_profiles()
        assert set(ps) >= {"rule", "glm_zai", "glm_bigmodel", "qwen_local"}

    def test_default_is_rule(self):
        prof, reason = resolve_active_profile()
        assert prof is not None and prof.name == "rule"

    def test_glm_without_key_reports_missing(self, monkeypatch):
        monkeypatch.delenv("AIOT_GLM_API_KEY", raising=False)
        monkeypatch.setenv("AIOT_AGENT_PROFILE", "glm_zai")
        prof, reason = resolve_active_profile()
        assert prof is not None and prof.name == "glm_zai"
        # 配置不完整被如實報告（model 空→profile_model_missing；補 model 後→api_key_missing）
        assert reason and ("api_key_missing" in reason or "profile_model_missing" in reason or "profile_base_url_missing" in reason)

    def test_unknown_profile(self, monkeypatch):
        monkeypatch.setenv("AIOT_AGENT_PROFILE", "nope")
        prof, reason = resolve_active_profile()
        assert prof is None and "unknown_profile" in reason

    def test_qwen_local_no_cloud_fallback_default(self):
        ps = load_profiles()
        assert ps["qwen_local"].cloud_fallback is False


def _CTX(**kw):
    from aiot_price.agent.providers import TrustedContext
    ctx = TrustedContext(crop_id="cabbage", market_id="中義市場", current_price_jin=32.0,
                         price_unit="NTD_per_taiwan_jin", observed_date="2026-10-04",
                         allowed_modes=("without_last_week",))
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


class TestToolContract:
    def test_whitelist_three_tools_phase2(self):
        # 第二階段（獲授權規格變更）：save_record 加入白名單（AGENT_DESIGN §4.2；
        # 執行仍需客戶端 save_confirmation，見 test_phase2_agent.py）。
        assert TOOL_NAMES == {"get_market_quote", "post_forecast", "save_record"}

    def test_unknown_tool_rejected(self, engine):
        tools = AgentTools(engine)
        r = _execute_tool(tools, "run_shell", {"cmd": "dir"}, _CTX())
        assert r["ok"] is False and "unknown_tool" in r["error"]

    def test_extra_argument_keys_rejected(self, engine):
        tools = AgentTools(engine)
        r = _execute_tool(tools, "post_forecast", {"crop_id": "cabbage", "__import": True}, _CTX())
        assert r["ok"] is False and "invalid_argument_keys" in r["error"]

    def test_invalid_json_arguments_rejected(self, engine):
        tools = AgentTools(engine)
        r = _execute_tool(tools, "post_forecast", None, _CTX())
        assert r["ok"] is False and "invalid_arguments" in r["error"]

    def test_real_tool_executes_via_engine_semantics(self, engine):
        tools = AgentTools(engine)
        r = _execute_tool(tools, "post_forecast", {
            "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
            "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
            "mode": "without_last_week",
        }, _CTX())
        assert not r.get("error")
        assert {x["horizon_days"] for x in r["results"]} == {7, 14}


class TestAgentLoop:
    def test_full_toolcall_roundtrip(self, engine, monkeypatch):
        """mock LLM 提出 post_forecast tool_call → 真引擎執行 → 結果回送 → 忠實回答。"""
        t = _MockTransport([
            _tool_call_resp([_call("post_forecast", {
                "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
                "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
                "mode": "without_last_week",
            })]),
            _text_resp(_ok_forecast_answer()),
        ])
        t.install(monkeypatch)
        r = run_agent_loop(engine, "高麗菜今天一斤32元", PROFILE, today=TODAY)
        assert r["backend_used"] == "mock_openai"
        assert r["degraded"] is False
        assert r["forecast"] and not r["forecast"]["error"]
        assert [x["tool"] for x in r["tool_trace"]] == ["post_forecast"]
        # 驗證結果回送：第二個請求的 messages 含 tool 角色訊息（真工具結果）
        msgs = t.received[1]["messages"]
        assert any(m.get("role") == "tool" for m in msgs)

    def test_fabricated_final_answer_degraded(self, engine, monkeypatch):
        t = _MockTransport([
            _tool_call_resp([_call("post_forecast", {
                "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
                "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
                "mode": "without_last_week",
            })]),
            _text_resp("7天後必定上漲99%，售價999元；已驗證。"),
        ])
        t.install(monkeypatch)
        r = run_agent_loop(engine, "高麗菜今天一斤32元", PROFILE, today=TODAY)
        assert r["backend_used"] == "rule"
        assert r["degraded"] is True and "rejected" in r["degraded_reason"]
        assert "999" not in r["answer"]

    def test_missing_input_skips_llm_entirely(self, engine, monkeypatch):
        t = _MockTransport([])
        t.install(monkeypatch)
        r = run_agent_loop(engine, "請問菜價", PROFILE, today=TODAY)
        assert r["backend_used"] == "rule" and r["degraded"]
        assert t.received == []  # 完全沒發 LLM 請求
        assert "補充" in r["answer"] or "缺" in r["answer"]

    def test_provider_failure_keeps_tool_result_no_cloud_switch(self, engine, monkeypatch):
        """provider 在第二輪失敗：已取得的真工具結果仍回；不切雲端。"""
        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            if not any(m.get("role") == "tool" for m in body["messages"]):
                return _MockTransport([_tool_call_resp([_call("post_forecast", {
                    "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
                    "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
                    "mode": "without_last_week",
                })])]).responses[0] and _fake_resp(_tool_call_resp([_call("post_forecast", {
                    "crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
                    "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T10:00:00+08:00",
                    "mode": "without_last_week",
                })]))
            raise OSError("simulated provider down")

        def _fake_resp(payload):
            class _Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps(payload).encode("utf-8")

            return _Resp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        r = run_agent_loop(engine, "高麗菜今天一斤32元", PROFILE, today=TODAY)
        assert r["degraded"] is True
        assert r["forecast"] is not None  # 已取得的工具真值仍在
        assert "7 天後" in r["answer"] or "持平" in r["answer"]  # 規則化真結果

    def test_no_tool_result_never_claims_prediction(self, engine, monkeypatch):
        """LLM 不呼叫工具直接回答預測 → 無有效工具結果 → 規則化不採用。"""
        t = _MockTransport([_text_resp("7 天後會上漲 5%，14 天後上漲 8%。")])
        t.install(monkeypatch)
        r = run_agent_loop(engine, "高麗菜今天一斤32元", PROFILE, today=TODAY)
        assert r["backend_used"] == "rule"
        assert r["degraded"] is True
        assert "上漲 5%" not in r["answer"]

    def test_max_turns_enforced(self, engine, monkeypatch):
        """無限 tool_call 迴圈被 max_turns 截止（不觸發更多請求）。"""
        call = _call("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場"}, cid="loop")
        t = _MockTransport([_tool_call_resp([call])] * 10)
        t.install(monkeypatch)
        r = run_agent_loop(engine, "高麗菜今天一斤32元", PROFILE, today=TODAY)
        assert len(t.received) <= PROFILE.max_turns


class TestEndpointWithProfiles:
    def test_endpoint_rule_default(self):
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/agent/query", json={"query": "高麗菜今天一斤32元"})
        assert r.status_code == 200
        body = r.json()
        assert body["backend_used"] == "rule"

    def test_endpoint_invalid_profile_503(self, monkeypatch):
        monkeypatch.setenv("AIOT_AGENT_PROFILE", "nope")
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/agent/query", json={"query": "高麗菜今天一斤32元"})
        assert r.status_code == 503

    def test_endpoint_glm_without_key_503(self, monkeypatch):
        monkeypatch.delenv("AIOT_GLM_API_KEY", raising=False)
        monkeypatch.setenv("AIOT_AGENT_PROFILE", "glm_zai")
        from fastapi.testclient import TestClient

        from aiot_price.api.app import app

        client = TestClient(app)
        r = client.post("/agent/query", json={"query": "高麗菜今天一斤32元"})
        assert r.status_code == 503
        msg = r.json()["error"]["message"]
        assert "配置不完整" in msg and any(k in msg for k in ("api_key_missing", "profile_model_missing", "profile_base_url_missing"))
