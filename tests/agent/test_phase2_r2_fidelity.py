"""Phase2 r2 P2-01/P2-02: fail closed and preserve mode/field attribution.

Only the provider transport is scripted; validation, AgentTools and the frozen
ForecastEngine run normally. No private records or model artifacts are written.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from aiot_price.agent.providers import ProviderProfile, ProviderResponse, run_agent_loop
from aiot_price.agent.service import validate_qwen_answer
from aiot_price.agent.tools import AgentTools
from aiot_price.models.predict import ForecastEngine


A = [
    {"horizon_days": 7, "target_date": "2026-10-11", "direction": "down",
     "relative_change_estimate": -0.031, "price_estimate": 31.0,
     "price_estimate_unit": "NTD_per_taiwan_jin"},
    {"horizon_days": 14, "target_date": "2026-10-18", "direction": "down",
     "relative_change_estimate": -0.062, "price_estimate": 33.0,
     "price_estimate_unit": "NTD_per_taiwan_jin"},
]
B = [
    {"horizon_days": 7, "target_date": "2026-10-11", "direction": "up",
     "relative_change_estimate": 0.047, "price_estimate": 99.0,
     "price_estimate_unit": "NTD_per_kg"},
    {"horizon_days": 14, "target_date": "2026-10-18", "direction": "up",
     "relative_change_estimate": 0.089, "price_estimate": 101.0,
     "price_estimate_unit": "NTD_per_kg"},
]


def forecast(mode):
    # Reflect the engine contract: results selects B only for with_last_week.
    return {"error": None, "mode_executed": mode,
            "results": deepcopy(B if mode == "with_last_week" else A),
            "results_without_last_week": deepcopy(A if mode in ("both", "with_last_week") else []),
            "results_with_last_week": deepcopy(B if mode in ("both", "with_last_week") else []),
            "input_observed_at": "2026-10-04T12:00:00+08:00",
            "public_data_cutoff": "2026-10-02"}


@pytest.mark.parametrize("answer", [
    "已確認保存。7天後菜價會漲到一百元。",
    "已確認保存。下週菜價會上漲。",
    "已確認保存。未來價格是32元。",
    "已確認保存。7天後菜價是32元。",
    "已確認保存。預估價格是三十二塊。",
    "已確認保存。未來會變貴。",
])
def test_save_without_forecast_rejects_prediction_claims(answer):
    assert validate_qwen_answer(answer, {"forecast": None, "save_ok": True})[0] is False


@pytest.mark.parametrize("answer", [
    "中義市場最新行情是一百元。", "行情是兩百五十塊。",
    "行情是壹佰元。", "行情是1e2元。", "行情是1/2元。",
    "行情是one hundred元。", "行情是1,027.5元。",
    "行情是27.5億元。", "行情是NT$100。", "行情是100 NTD。",
    "行情是二十七點元。", "行情是32。",
])
def test_quote_rejects_fabricated_or_unsupported_amount_forms(answer):
    quote = {"ok": True, "price": 27.5, "observed_date": "2026-10-02"}
    assert validate_qwen_answer(answer, {"forecast": None, "market_quote": quote})[0] is False


@pytest.mark.parametrize("answer", [
    "2026-10-02 的最新公開行情為27.5元。",
    "最新行情是二十七點五元。", "最新行情是２７．５塊。",
])
def test_quote_accepts_supported_truthful_amounts(answer):
    quote = {"ok": True, "price": 27.5, "observed_date": "2026-10-02"}
    ok, why = validate_qwen_answer(answer, {"forecast": None, "market_quote": quote})
    assert ok is True, why


@pytest.mark.parametrize("answer", [
    "已查詢公開行情，僅供市場參考。",
    "中義市場最新公開行情為27.5元／台斤（觀測日2026-10-02）；市場均價不是個店真值。",
])
def test_safe_quote_completion_and_scope_disclosure_are_supported(answer):
    quote = {"ok": True, "price": 27.5, "unit": "NTD_per_taiwan_jin", "observed_date": "2026-10-02"}
    ok, why = validate_qwen_answer(answer, {"market_quote": quote})
    assert ok is True, why


@pytest.mark.parametrize("answer", [
    "已確認保存。", "已保存，供7天後核對。",
    "已確認保存，供到期核對。",
    "已確認保存，供後續核對。",
    "已依您的確認保存剛才的預測，供7／14天後到期核對。",
])
def test_save_confirmation_without_predictions_remains_valid(answer):
    assert validate_qwen_answer(answer, {"forecast": None, "save_ok": True})[0] is True


@pytest.mark.parametrize("answer", ["7天後行情是27.5元。", "未來價格是27.5元。", "菜價將持平。"])
def test_quote_does_not_authorize_future_price_or_direction(answer):
    quote = {"ok": True, "price": 27.5, "observed_date": "2026-10-02"}
    assert validate_qwen_answer(answer, {"forecast": None, "market_quote": quote})[0] is False


@pytest.mark.parametrize("answer", ["已保存。7天後價格會升高。", "已保存。菜價趨勢將轉弱。"])
def test_save_output_only_authorizes_confirmation_and_reconciliation(answer):
    assert validate_qwen_answer(answer, {"save_ok": True})[0] is False


def test_quote_unit_must_match_actual_tool_unit():
    quote = {"ok": True, "price": 27.5, "price_unit": "NTD_per_taiwan_jin", "observed_date": "2026-10-02"}
    assert validate_qwen_answer("最新行情27.5元/公斤。", {"market_quote": quote})[0] is False
    assert validate_qwen_answer("最新行情27.5元/台斤。", {"market_quote": quote})[0] is True


@pytest.mark.parametrize("unit", ["磅", "kg", "英斤"])
def test_unrecognized_price_unit_fails_closed(unit):
    quote = {"ok": True, "price": 27.5, "unit": "NTD_per_taiwan_jin"}
    assert validate_qwen_answer(f"最新行情27.5元/{unit}。", {"market_quote": quote})[0] is False
    assert validate_qwen_answer(f"A模式7天後31元/{unit}。", {"forecast": forecast("both")})[0] is False


@pytest.mark.parametrize("answer", ["最新行情為數十元。", "最新行情為幾十元。", "最新行情是數十塊。"])
def test_amount_cannot_be_a_suffix_of_an_unsupported_quantity(answer):
    assert validate_qwen_answer(answer, {"market_quote": {"ok": True, "price": 10.0}})[0] is False


@pytest.mark.parametrize("answer", ["最新行情是 thirty bucks。", "最新行情是 one hundred。", "最新行情很便宜。"])
def test_quote_claim_requires_supported_numeric_price_statement(answer):
    assert validate_qwen_answer(answer, {"market_quote": {"ok": True, "price": 27.5}})[0] is False


@pytest.mark.parametrize("answer", ["99元是A模式7天後預估店價。", "A模式預估店價為33元（7天後）。"])
def test_numbers_before_mode_or_horizon_cannot_use_default_truth_union(answer):
    assert validate_qwen_answer(answer, {"forecast": forecast("with_last_week")})[0] is False


def test_mode_heading_binds_following_numeric_sentence():
    assert validate_qwen_answer("B模式：\n7天後99元。", {"forecast": forecast("both")})[0] is True
    assert validate_qwen_answer("B模式：\n7天後31元。", {"forecast": forecast("both")})[0] is False


@pytest.mark.parametrize("answer", ["明天最新公開行情27.5元。", "明年價格仍27.5元。", "明日菜價走高。", "最新行情即將走高。"])
def test_quote_only_rejects_unknown_future_statements(answer):
    assert validate_qwen_answer(answer, {"market_quote": {"ok": True, "price": 27.5}})[0] is False


@pytest.mark.parametrize("answer", ["A模式7天後價格會持平。", "A模式7天後价格不變。", "A模式7天後菜價走低。"])
def test_up_direction_cannot_be_changed_or_rephrased_to_unknown_direction(answer):
    fc = forecast("both")
    fc["results"][0]["direction"] = "up"
    fc["results_without_last_week"][0]["direction"] = "up"
    assert validate_qwen_answer(answer, {"forecast": fc})[0] is False


@pytest.mark.parametrize("answer", ["A模式7天後公斤價31元。", "A模式7天後31元（公斤）。"])
def test_unit_is_validated_before_amount_and_in_parentheses(answer):
    assert validate_qwen_answer(answer, {"forecast": forecast("both")})[0] is False


def test_mode_is_preserved_across_sentence_boundary():
    assert validate_qwen_answer("A模式7天後31元。14天後101元。", {"forecast": forecast("with_last_week")})[0] is False
    assert validate_qwen_answer("A模式7天後31元。14天後33元。", {"forecast": forecast("with_last_week")})[0] is True


@pytest.mark.parametrize("day", ["2026-10-04", "2026-10-02"])
def test_start_and_cutoff_dates_cannot_be_used_as_horizon_target(day):
    assert validate_qwen_answer(f"A模式7天後（{day}）31元。", {"forecast": forecast("both")})[0] is False


def test_explicit_start_and_cutoff_metadata_remains_supported():
    answer = "從今天2026-10-04起算，A模式7天後（2026-10-11）31元。公開行情截止2026-10-02。"
    ok, why = validate_qwen_answer(answer, {"forecast": forecast("both")})
    assert ok is True, why


@pytest.mark.parametrize("answer", [
    "A模式7天後31元是B模式7天後預估店價。",
    "A模式7天後31元為B模式7天後店價。",
    "A模式7天後31元為14天後店價。",
    "A模式7天後31元（B模式7天後店價）。",
])
def test_completed_number_cannot_be_reassigned_by_a_following_marker(answer):
    assert validate_qwen_answer(answer, {"forecast": forecast("with_last_week")})[0] is False


@pytest.mark.parametrize("answer", ["A模式7天後預估店價是-3.1%。", "B模式7天後預估店價為4.7%。"])
def test_price_field_label_cannot_authorize_a_percentage_value(answer):
    assert validate_qwen_answer(answer, {"forecast": forecast("both")})[0] is False


@pytest.mark.parametrize("mode,answer", [
    ("without_last_week", "A模式7天後可能下跌（-3.1%，31元/台斤）。"),
    ("with_last_week", "B模式7天後可能上漲（+4.7%，99元/公斤）。"),
    ("with_last_week", "7天後可能上漲（+4.7%，99元/公斤）。"),
    ("both", "A模式7天後31元/台斤，B模式7天後99元/公斤。"),
    ("both", "7天後A模式31元/台斤，B模式99元/公斤。"),
    ("fallback_without_last_week", "A模式7天後31元/台斤。"),
    ("both", "A模式7天後三十一元/台斤，14天後三十三元/台斤。"),
])
def test_truthful_mode_horizon_field_unit_combinations(mode, answer):
    ok, why = validate_qwen_answer(answer, {"forecast": forecast(mode)})
    assert ok is True, why


@pytest.mark.parametrize("mode,answer", [
    ("with_last_week", "A模式7天後99元。"),
    ("with_last_week", "B模式7天後31元。"),
    ("both", "A模式7天後99元，B模式7天後31元。"),
    ("both", "7天後A模式99元，B模式31元。"),
    ("without_last_week", "B模式7天後31元。"),
    ("fallback_without_last_week", "B模式7天後31元。"),
    ("both", "A模式7天後33元，14天後31元。"),
    ("both", "B模式7天後101元，14天後99元。"),
    ("both", "A模式7天後31%。"),
    ("both", "B模式7天後4.7元。"),
    ("both", "A模式7天後31元/公斤。"),
    ("both", "B模式7天後99元/台斤。"),
    ("both", "A模式7天後（2026-10-18）31元。"),
    ("both", "B模式14天後（2026-10-11）101元。"),
    ("with_last_week", "B模式7天後可能下跌。"),
    ("with_last_week", "A模式7天後可能上漲。"),
])
def test_cross_mode_horizon_field_unit_and_date_claims_rejected(mode, answer):
    ok, why = validate_qwen_answer(answer, {"forecast": forecast(mode)})
    assert ok is False, (answer, why)


def test_b_only_primary_results_do_not_become_a_when_named_lists_missing():
    fc = forecast("with_last_week")
    fc["results_without_last_week"] = []
    fc["results_with_last_week"] = []
    assert validate_qwen_answer("B模式7天後99元。", {"forecast": fc})[0] is True
    assert validate_qwen_answer("A模式7天後99元。", {"forecast": fc})[0] is False


def test_explicit_named_a_results_do_not_union_conflicting_primary_b_values():
    fc = forecast("both")
    fc["results"] = deepcopy(B)
    assert validate_qwen_answer("A模式7天後99元。", {"forecast": fc})[0] is False


def test_fallback_ignores_unexecuted_stale_b_list():
    fc = forecast("fallback_without_last_week")
    fc["results_with_last_week"] = deepcopy(B)
    assert validate_qwen_answer("B模式7天後99元。", {"forecast": fc})[0] is False


def test_loop_saved_record_cannot_authorize_chinese_price(monkeypatch):
    replies = iter([
        ProviderResponse(tool_calls=[{"id": "save-call", "name": "save_record",
                                      "arguments": {"request_id": "fidelity-test"}}]),
        ProviderResponse(content="已保存。7天後會漲到一百元。"),
    ])
    monkeypatch.setattr("aiot_price.agent.providers.OpenAICompatProvider.chat", lambda *a, **kw: next(replies))
    profile = ProviderProfile(name="fidelity-script", kind="openai_compat", base_url="http://127.0.0.1:9/v1",
                              model="local-test", api_key_env="", max_turns=3, max_tool_calls=3)
    saved = []

    def save(rid):
        saved.append(rid)
        return {"ok": True, "record_id": "isolated-test"}

    result = run_agent_loop(object(), "高麗菜今天一台斤32元，請保存之前的預測。", profile,
                            today=date(2026, 10, 4), store_id="s1",
                            save_gate={"request_id": "fidelity-test", "confirmed": True, "saver": save})
    assert saved == ["fidelity-test"]
    assert result["forecast"] is None
    assert result["degraded"] is True and result["backend_used"] == "rule"
    assert "一百元" not in result["answer"]


@pytest.fixture(scope="module")
def frozen_engine():
    release = Path(__file__).resolve().parents[2] / "models/releases/0.1.0"
    assert (release / "manifest.json").is_file(), "Required frozen engine artifact is missing"
    return ForecastEngine(release)


@pytest.mark.parametrize("mode", ["without_last_week", "with_last_week", "both", "fallback_without_last_week"])
def test_real_forecast_engine_values_keep_mode_attribution(frozen_engine, mode):
    request = {"crop_id": "cabbage", "market_id": "中義市場", "current_price": 32.0,
               "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-04T12:00:00+08:00",
               "mode": "both" if mode == "fallback_without_last_week" else mode,
               "previous_price": 28.0, "previous_price_unit": "NTD_per_taiwan_jin",
               "previous_observed_at": "2026-08-01T12:00:00+08:00" if mode == "fallback_without_last_week"
                                       else "2026-09-27T12:00:00+08:00"}
    fc = AgentTools(frozen_engine).post_forecast(request)
    assert fc["error"] is None and fc["mode_executed"] == mode
    if mode in ("both", "with_last_week"):
        a7, b7 = fc["results_without_last_week"][0], fc["results_with_last_week"][0]
        assert a7["price_estimate"] == 30.7 and b7["price_estimate"] == 32.1
        assert validate_qwen_answer("A模式7天後32.1元。", {"forecast": fc})[0] is False
        assert validate_qwen_answer("B模式7天後30.7元。", {"forecast": fc})[0] is False
        assert validate_qwen_answer("A模式7天後30.7元，B模式7天後32.1元。", {"forecast": fc})[0] is True
    else:
        assert fc["results"][0]["price_estimate"] == 30.7
        assert validate_qwen_answer("A模式7天後30.7元。", {"forecast": fc})[0] is True
        assert validate_qwen_answer("B模式7天後30.7元。", {"forecast": fc})[0] is False
