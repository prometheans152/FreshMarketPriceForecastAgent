from types import SimpleNamespace

import pandas as pd

from aiot_price.agent.tools import AgentTools


def engine(rows):
    return SimpleNamespace(history=pd.DataFrame(rows), public_cutoff=pd.Timestamp('2026-10-09'))


def test_quote_date_is_price_observation_not_missing_latest_snapshot():
    data = engine([
        {'date':pd.Timestamp('2026-10-01'), 'market_id':'中義市場', 'crop_id':'cabbage', 'price':30.0},
        {'date':pd.Timestamp('2026-10-09'), 'market_id':'中義市場', 'crop_id':'cabbage', 'price':float('nan')},
    ])
    result = AgentTools(data).get_market_quote('cabbage', '中義市場')
    assert result['ok'] is True and result['price'] == 30.0
    assert result['observed_date'] == '2026-10-01'
    assert result['public_data_cutoff'] == '2026-10-09'
    assert result['price_age_days_at_cutoff'] == 8


def test_quote_no_positive_price_is_unavailable():
    data = engine([{'date':pd.Timestamp('2026-10-09'), 'market_id':'中義市場', 'crop_id':'cabbage', 'price':float('nan')}])
    assert AgentTools(data).get_market_quote('cabbage', '中義市場')['ok'] is False
