"""TW01 independent 57-item SUPERVISED ML website extension.

The original Oracle origin API is imported, not forked. For the old three
crops the frozen RF/HGB logic is identical. For 57 new public crop IDs,
the same protected website request validation/concurrency limits now invokes
genuinely trained models from the independently signed pooled ML release.
No change to the /v1/* MCP Bearer routes or browser private records.
"""
from __future__ import annotations

from aiot_price.integrations.chatgpt_contracts import CROP_IDS
import oracle_web_site
from pooled_ml_runtime import check_ml_release_integrity, forecast_ml

# Startup readiness must verify model/source hashes before serving any forecast.
ML_READY = check_ml_release_integrity()
_frozen_original = oracle_web_site._native_forecast


def _web_forecast_with_trained_pooled_ml(body: dict):
    if body["crop_id"] in CROP_IDS:
        return _frozen_original(body)
    return forecast_ml({**body, "store_id": None})


oracle_web_site._native_forecast = _web_forecast_with_trained_pooled_ml
app = oracle_web_site.app
