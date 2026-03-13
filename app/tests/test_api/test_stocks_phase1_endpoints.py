from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402
import backend.routers.stocks as stocks_router  # noqa: E402


def test_sentiment_contract_includes_distribution(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        "get_news_sentiment",
        lambda ticker: {
            "ticker": ticker,
            "available": True,
            "overall_sentiment": "Neutral",
            "overall_score": 0.12,
            "distribution": {
                "Bullish": 15,
                "Somewhat-Bullish": 0,
                "Neutral": 0,
                "Somewhat-Bearish": 0,
                "Bearish": 10,
            },
            "total_articles": 25,
            "articles": [{"title": "A"}],
        },
    )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/LAZR/sentiment")

    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["total_articles"] == 25
    assert body["distribution"]["Bullish"] == 15
    assert body["distribution"]["Bearish"] == 10


def test_ath_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        "get_ath_analysis",
        lambda ticker: {
            "ticker": ticker,
            "all_time_high": 20.0,
            "ath_date": "2024-01-02",
            "all_time_low": 5.0,
            "atl_date": "2023-01-02",
            "current_price": 15.0,
            "down_from_ath_pct": 25.0,
            "up_from_atl_pct": 200.0,
            "range_position": 66.6667,
        },
    )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/LAZR/ath")

    assert resp.status_code == 200
    body = resp.json()
    assert body["all_time_high"] == 20.0
    assert body["down_from_ath_pct"] == 25.0


def test_ath_endpoint_returns_404_when_no_data(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        "get_ath_analysis",
        lambda ticker: {
            "ticker": ticker,
            "all_time_high": None,
            "error": "No historical close data",
        },
    )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/LAZR/ath")

    assert resp.status_code == 404
    assert "ATH data" in resp.json()["detail"]


def test_eps_trend_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        "get_eps_trend",
        lambda ticker: {
            "ticker": ticker,
            "eps_history": [
                {"year": "2022", "eps": -10.0, "yoy_change": None},
                {"year": "2023", "eps": -8.0, "yoy_change": 0.2},
            ],
            "earliest_year": "2022",
            "latest_year": "2023",
        },
    )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/LAZR/eps-trend")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["eps_history"]) == 2
    assert body["latest_year"] == "2023"


def test_eps_trend_endpoint_returns_404_when_no_data(monkeypatch):
    monkeypatch.setattr(
        stocks_router,
        "get_eps_trend",
        lambda ticker: {
            "ticker": ticker,
            "eps_history": [],
            "error": "No annual EPS data",
        },
    )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/LAZR/eps-trend")

    assert resp.status_code == 404
    assert "EPS trend" in resp.json()["detail"]
