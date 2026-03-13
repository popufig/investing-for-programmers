from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402
import backend.routers.macro as macro_router  # noqa: E402
import backend.routers.stocks as stocks_router  # noqa: E402


def test_earnings_estimates_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        'get_earnings_estimates',
        lambda ticker: {
            'ticker': ticker,
            'earnings_estimates': [{'period': '0q', 'avg': -0.2}],
            'revenue_estimates': [],
        },
    )

    with TestClient(app) as client:
        resp = client.get('/api/stocks/LAZR/earnings-estimates')

    assert resp.status_code == 200
    body = resp.json()
    assert body['ticker'] == 'LAZR'
    assert len(body['earnings_estimates']) == 1


def test_earnings_estimates_endpoint_returns_404(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        'get_earnings_estimates',
        lambda ticker: {
            'ticker': ticker,
            'earnings_estimates': [],
            'revenue_estimates': [],
            'error': 'No earnings estimate data',
        },
    )

    with TestClient(app) as client:
        resp = client.get('/api/stocks/LAZR/earnings-estimates')

    assert resp.status_code == 404


def test_google_trends_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        'get_google_trends',
        lambda keywords, timeframe: {
            'keywords': keywords,
            'timeframe': timeframe,
            'available': True,
            'data': [{'date': '2024-01-01', keywords[0]: 50}],
        },
    )

    with TestClient(app) as client:
        resp = client.get('/api/stocks/trends', params={'keywords': 'Luminar Technologies,Ouster', 'timeframe': 'today 12-m'})

    assert resp.status_code == 200
    body = resp.json()
    assert body['available'] is True
    assert body['keywords'][0] == 'Luminar Technologies'


def test_google_trends_endpoint_rejects_too_many_keywords():
    with TestClient(app) as client:
        resp = client.get('/api/stocks/trends', params={'keywords': 'a,b,c,d,e,f'})

    assert resp.status_code == 400
    assert 'At most 5 keywords' in resp.json()['detail']


def test_macro_fred_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        macro_router,
        'get_fred_series',
        lambda series_id, period: {
            'series_id': series_id,
            'period': period,
            'title': 'Federal Funds Effective Rate',
            'available': True,
            'data': [{'date': '2024-01-01', 'value': 5.33}],
        },
    )

    with TestClient(app) as client:
        resp = client.get('/api/macro/fred/DFF', params={'period': '5y'})

    assert resp.status_code == 200
    body = resp.json()
    assert body['series_id'] == 'DFF'
    assert body['available'] is True
