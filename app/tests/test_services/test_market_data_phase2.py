import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.services.market_data as md  # noqa: E402


def _reset_cache():
    md._cache.clear()


def test_get_earnings_estimates_parses_frames(monkeypatch):
    _reset_cache()

    class FakeTicker:
        @property
        def earnings_estimate(self):
            return pd.DataFrame(
                {
                    'avg': [-0.25, -0.18],
                    'low': [-0.35, -0.25],
                    'high': [-0.12, -0.10],
                    'yearAgoEps': [-0.42, -0.30],
                    'numberOfAnalysts': [8, 7],
                    'growth': [0.2, 0.15],
                },
                index=['0q', '+1q'],
            )

        @property
        def revenue_estimate(self):
            return pd.DataFrame(
                {
                    'avg': [45.2, 51.0],
                    'low': [43.0, 48.0],
                    'high': [47.0, 54.0],
                    'numberOfAnalysts': [6, 5],
                    'growth': [0.12, 0.10],
                },
                index=['0q', '+1q'],
            )

    monkeypatch.setattr(md.yf, 'Ticker', lambda ticker: FakeTicker())
    monkeypatch.setattr(md, '_run_with_timeout', lambda fn, timeout_seconds=10: fn())

    result = md.get_earnings_estimates('LAZR')

    assert result['ticker'] == 'LAZR'
    assert len(result['earnings_estimates']) == 2
    assert result['earnings_estimates'][0]['period'] == '0q'
    assert result['earnings_estimates'][0]['years_ago_eps'] == -0.42
    assert result['revenue_estimates'][0]['avg'] == 45.2


def test_get_fred_series_parses_and_downsamples(monkeypatch):
    _reset_cache()

    class _Resp:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self.payload).encode('utf-8')

    observations = []
    for i in range(600):
        observations.append({'date': f'2024-01-{(i % 28) + 1:02d}', 'value': f'{5.0 + i * 0.001:.3f}'})

    meta_payload = {'seriess': [{'title': 'Federal Funds Effective Rate'}]}
    obs_payload = {'observations': observations}

    def fake_urlopen(url, timeout=10):
        if 'series/observations' in url:
            return _Resp(obs_payload)
        return _Resp(meta_payload)

    monkeypatch.setattr(md, '_pick_any_env_value', lambda keys: 'demo')
    monkeypatch.setattr(md, 'urlopen', fake_urlopen)
    monkeypatch.setattr(md, '_run_with_timeout', lambda fn, timeout_seconds=10: fn())

    result = md.get_fred_series('DFF', '5y')

    assert result['available'] is True
    assert result['title'] == 'Federal Funds Effective Rate'
    assert len(result['data']) <= 521
    assert 'date' in result['data'][0]
    assert 'value' in result['data'][0]


def test_get_google_trends_parses_interest_over_time(monkeypatch):
    _reset_cache()

    class FakeTrendReq:
        def __init__(self, hl='en-US', tz=0):
            self.keywords = []

        def build_payload(self, keywords, timeframe='today 12-m'):
            self.keywords = keywords

        def interest_over_time(self):
            return pd.DataFrame(
                {
                    'Luminar Technologies': [50, 55, 53],
                    'Ouster': [20, 22, 21],
                    'isPartial': [False, False, False],
                },
                index=pd.to_datetime(['2024-01-01', '2024-01-08', '2024-01-15']),
            )

    monkeypatch.setattr(md, 'TrendReq', FakeTrendReq)
    monkeypatch.setattr(md, '_run_with_timeout', lambda fn, timeout_seconds=10: fn())

    result = md.get_google_trends(['Luminar Technologies', 'Ouster'], 'today 12-m')

    assert result['available'] is True
    assert result['keywords'] == ['Luminar Technologies', 'Ouster']
    assert len(result['data']) == 3
    assert result['data'][0]['Luminar Technologies'] == 50
