"""Frozen numeric integration: adapter must retain original engine values."""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import pytest

from aiot_price.integrations.chatgpt_adapter import (
    ToolUnavailable, execute_tool, verify_frozen_release,
)
from aiot_price.integrations.chatgpt_contracts import ContractError, normalized_forecast_request
from aiot_price.models.predict import ForecastEngine
from aiot_price.agent.tools import AgentTools

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "models" / "releases" / "0.1.0"
INPUT = dict(crop_id="cabbage", market_id="中義市場", current_price=32,
             price_unit="NTD_per_taiwan_jin", observed_on="2026-10-12")


def test_real_forecast_matches_original_frozen_engine():
    adapter = execute_tool("post_forecast", INPUT, RELEASE, today=date(2026, 10, 13))
    assert adapter["input_echo"]["current_price"] == 32
    assert adapter["normalized_request"]["store_id"] is None
    assert adapter["normalized_request"]["mode"] == "without_last_week"
    original = AgentTools(ForecastEngine(RELEASE)).post_forecast(adapter["normalized_request"])
    for key in ("model_version", "data_version", "public_data_cutoff", "mode_executed",
                "crop_id", "market_id", "store_id", "results", "warnings"):
        assert adapter["engine_result"][key] == original[key], key
    assert [r["target_date"] for r in adapter["engine_result"]["results"]] == [
        "2026-10-19", "2026-10-26"
    ]
    assert all(r["validation_scope"] == "unvalidated" for r in adapter["engine_result"]["results"])


def test_quote_retains_both_ages():
    adapter = execute_tool("get_market_quote", {
        "crop_id": "cabbage", "market_id": "中義市場"
    }, RELEASE, today=date(2026, 10, 13))
    raw = AgentTools(ForecastEngine(RELEASE)).get_market_quote("cabbage", "中義市場")
    assert adapter["engine_result"] == raw
    assert adapter["price_age_days_at_query"] == (
        date(2026, 10, 13) - date.fromisoformat(raw["observed_date"])
    ).days
    assert adapter["price_age_days_at_query"] >= raw["price_age_days_at_cutoff"]


def test_kg_preserves_engine_units_and_history():
    args = {**INPUT, "current_price": 65, "price_unit": "NTD_per_kg",
            "observed_on": "2026-09-30"}
    x = execute_tool("post_forecast", args, RELEASE, today=date(2026, 10, 13))
    assert x["input_echo"] == {**args, "current_price": 65.0}
    assert [r["target_date"] for r in x["engine_result"]["results"]] == [
        "2026-10-07", "2026-10-14"
    ]
    assert all(r["price_estimate_unit"] == "NTD_per_kg" for r in x["engine_result"]["results"])


def test_frozen_release_negative_control(tmp_path):
    for path in RELEASE.iterdir():
        if path.name in {"manifest.json", "fixtures.json", "model_h7.joblib",
                         "model_h14.joblib", "public_history.parquet"}:
            (tmp_path / path.name).write_bytes(path.read_bytes())
    verify_frozen_release(tmp_path)
    p = tmp_path / "fixtures.json"
    content = bytearray(p.read_bytes())
    content[0] ^= 1
    p.write_bytes(content)
    with pytest.raises(ToolUnavailable, match="fixtures.json"):
        verify_frozen_release(tmp_path)


def test_dispatch_rejects_b_and_url():
    for args in ({**INPUT, "previous_price": 30},
                 {**INPUT, "save": True},
                 {**INPUT, "url": "https://example.invalid"}):
        with pytest.raises(ContractError):
            execute_tool("post_forecast", args, RELEASE, today=date(2026, 10, 13))


@pytest.mark.parametrize("poison", [
    "duplicate_7", "wrong_market", "wrong_crop", "wrong_unit",
    "wrong_price", "nonfinite_change", "wrong_scope",
])
def test_wrong_engine_value_rejected_not_exposed(monkeypatch, poison):
    """Genuine AgentTools result with one deliberately corrupted field.

    Do not modify frozen model or source; the tamper lives only in memory.
    """
    original = AgentTools.post_forecast

    def corrupted(self, request):
        result = original(self, request)
        if poison == "duplicate_7":
            result["results"][1] = dict(result["results"][0])
        elif poison == "wrong_market":
            result["market_id"] = "南屯市場"
        elif poison == "wrong_crop":
            result["crop_id"] = "bok_choy"
        elif poison == "wrong_unit":
            result["results"][0]["price_estimate_unit"] = "NTD_per_kg"
        elif poison == "wrong_price":
            result["results"][0]["price_estimate"] += 12.0
        elif poison == "nonfinite_change":
            result["results"][0]["relative_change_estimate"] = float("nan")
        elif poison == "wrong_scope":
            result["results"][0]["validation_scope"] = "store_pilot"
        return result

    monkeypatch.setattr(AgentTools, "post_forecast", corrupted)
    with pytest.raises(ToolUnavailable):
        execute_tool("post_forecast", INPUT, RELEASE, today=date(2026, 10, 13))


@pytest.mark.parametrize("delta,direction,scope", [
    (0.05, "unknown", "unvalidated"),
    (0.05, "down", "unvalidated"),
    (0.05, "insufficient_data", "public_market_test"),
    (-0.05, "up", "unvalidated"),
    (-0.05, "unknown", "unvalidated"),
])
def test_rounded_threshold_does_not_hide_poisoned_direction(
    monkeypatch, delta, direction, scope
):
    """A valid numeric return must never accept an invalid/opposite label.

    The real engine result is poisoned in-memory. The production result is
    rounded to four decimals; a 5% return is precisely the ambiguity boundary.
    No model/release files are modified.
    """
    original = AgentTools.post_forecast

    def corrupted(self, request):
        result = original(self, request)
        result["results"][0].update(
            relative_change_estimate=delta,
            price_estimate=round(INPUT["current_price"] * (1 + delta), 1),
            direction=direction,
            validation_scope=scope,
        )
        return result

    monkeypatch.setattr(AgentTools, "post_forecast", corrupted)
    with pytest.raises(ToolUnavailable, match="方向|驗證範圍"):
        execute_tool("post_forecast", INPUT, RELEASE, today=date(2026, 10, 13))


@pytest.mark.parametrize("delta,direction", [
    (0.05, "flat"),
    (0.05, "up"),
    (-0.05, "flat"),
    (-0.05, "down"),
])
def test_rounded_threshold_allows_only_adjacent_legitimate_directions(
    monkeypatch, delta, direction
):
    """Allow original unrounded RF/HGB classification near the 4-decimal edge."""
    original = AgentTools.post_forecast

    def near_threshold(self, request):
        result = original(self, request)
        result["results"][0].update(
            relative_change_estimate=delta,
            price_estimate=round(INPUT["current_price"] * (1 + delta), 1),
            direction=direction,
            validation_scope="unvalidated",
        )
        return result

    monkeypatch.setattr(AgentTools, "post_forecast", near_threshold)
    result = execute_tool("post_forecast", INPUT, RELEASE, today=date(2026, 10, 13))
    assert result["engine_result"]["results"][0]["direction"] == direction
