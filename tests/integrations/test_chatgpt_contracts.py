from datetime import date
import pytest
from aiot_price.integrations.chatgpt_contracts import (
    ContractError, TOOL_NAMES, TOOL_SCHEMAS, MARKETS,
    validate_arguments, normalized_forecast_request,
)
BASE = {"crop_id":"cabbage","market_id":"中義市場","current_price":32,
        "price_unit":"NTD_per_taiwan_jin","observed_on":"2026-10-12"}

def test_exact_tools_and_closed_schemas():
    assert TOOL_NAMES == ("get_market_quote", "post_forecast")
    assert all(s["additionalProperties"] is False for s in TOOL_SCHEMAS.values())

def test_a_noon_null_store():
    req = normalized_forecast_request(validate_arguments("post_forecast", BASE, today=date(2026,10,13)))
    assert req["observed_at"] == "2026-10-12T12:00:00+08:00"
    assert req["mode"] == "without_last_week" and req["store_id"] is None

@pytest.mark.parametrize("change", [
    {"crop_id":"other"}, {"market_id":"other"}, {"current_price":True},
    {"current_price":0}, {"current_price":-1}, {"current_price":float("nan")},
    {"current_price":float("inf")}, {"price_unit":"per_piece"},
    {"observed_on":"2026-2-03"}, {"observed_on":"2026-02-30"},
    {"observed_on":"2026-10-14"}, {"observed_on":None},
    {"previous_price":30}, {"mode":"both"}, {"store_id":"x"},
    {"save":True}, {"confirmed":True}, {"url":"https://bad.invalid"},
    {"path":"C:/private"}, {"code":"print(1)"}, {"timeout":200},
    {"release_dir":"other"}, {"records_dir":"../private"},
])
def test_bad_args_fail(change):
    with pytest.raises(ContractError):
        validate_arguments("post_forecast", {**BASE, **change}, today=date(2026,10,13))

@pytest.mark.parametrize("missing", ["crop_id","market_id","current_price","price_unit"])
def test_missing(missing):
    bad = {k:v for k,v in BASE.items() if k!=missing}
    with pytest.raises(ContractError):
        validate_arguments("post_forecast", bad, today=date(2026,10,13))

def test_quote_and_unknown_name():
    assert validate_arguments("get_market_quote", {"crop_id":"cabbage","market_id":MARKETS[0]})
    with pytest.raises(ContractError):
        validate_arguments("get_market_quote", {"crop_id":"cabbage","market_id":MARKETS[0],"save":True})
    with pytest.raises(ContractError):
        validate_arguments("delete_all", {})

def test_taipei_default_day():
    args = {k:v for k,v in BASE.items() if k!="observed_on"}
    assert validate_arguments("post_forecast",args,today=date(2026,10,13))["observed_on"] == "2026-10-13"