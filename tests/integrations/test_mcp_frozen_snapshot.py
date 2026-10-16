"""Local release file replacement between checksum preflight and joblib.load.

Only mutate a pytest temporary COPY; never touch the actual frozen release.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from aiot_price.integrations.chatgpt_adapter import execute_tool
from aiot_price.models.predict import ForecastEngine

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "models" / "releases" / "0.1.0"
FIVE = ("manifest.json", "fixtures.json", "model_h7.joblib",
        "model_h14.joblib", "public_history.parquet")


def test_shared_release_replaced_after_verification_does_not_affect_loaded_model(
    monkeypatch, tmp_path
):
    copied_release = tmp_path / "shared_release"
    copied_release.mkdir()
    for name in FIVE:
        (copied_release / name).write_bytes((ORIGINAL / name).read_bytes())
    home = tmp_path / "isolated_home"
    home.mkdir()
    monkeypatch.setenv("AIOT_MCP_SNAPSHOT_DIR", str(home))
    original_init = ForecastEngine.__init__
    changed = {"once": False}

    def simulated_concurrent_write(self, release_dir):
        if not changed["once"]:
            changed["once"] = True
            (copied_release / "model_h7.joblib").write_bytes(b"untrusted replacement")
        return original_init(self, release_dir)

    monkeypatch.setattr(ForecastEngine, "__init__", simulated_concurrent_write)
    result = execute_tool(
        "get_market_quote",
        {"crop_id": "cabbage", "market_id": "中義市場"},
        copied_release,
        today=date(2026, 10, 13),
    )
    assert changed["once"], "The replacement did not happen between check and engine load"
    assert result["engine_result"]["ok"] is True
    assert result["engine_result"]["price"] > 0
    assert (copied_release / "model_h7.joblib").read_bytes() == b"untrusted replacement"
