from datetime import datetime
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


def test_news_sentiment_distribution_uses_full_feed(monkeypatch):
    _reset_cache()

    feed = []
    for i in range(25):
        label = "Bullish" if i < 15 else "Bearish"
        score = 0.6 if i < 15 else -0.6
        feed.append(
            {
                "title": f"article-{i}",
                "url": f"https://example.com/{i}",
                "source": "example",
                "time_published": datetime(2024, 1, 1, 12, 0, 0).strftime("%Y%m%dT%H%M%S"),
                "ticker_sentiment": [
                    {
                        "ticker": "LAZR",
                        "ticker_sentiment_label": label,
                        "ticker_sentiment_score": score,
                        "relevance_score": "0.8",
                    }
                ],
            }
        )

    payload = {"feed": feed}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(md, "_pick_env_value", lambda key: "demo")
    monkeypatch.setattr(md, "urlopen", lambda *args, **kwargs: _Resp())

    result = md.get_news_sentiment("LAZR")

    assert result["available"] is True
    assert result["total_articles"] == 25
    assert len(result["articles"]) == 20
    assert result["distribution"]["Bullish"] == 15
    assert result["distribution"]["Bearish"] == 10


def test_get_ath_analysis_computes_metrics(monkeypatch):
    _reset_cache()

    class FakeTicker:
        def history(self, period="max"):
            return pd.DataFrame(
                {"Close": [10.0, 20.0, 5.0, 15.0]},
                index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            )

    monkeypatch.setattr(md.yf, "Ticker", lambda ticker: FakeTicker())
    monkeypatch.setattr(md, "_run_with_timeout", lambda fn, timeout_seconds=10: fn())

    result = md.get_ath_analysis("TEST")

    assert result["all_time_high"] == 20.0
    assert result["all_time_low"] == 5.0
    assert result["current_price"] == 15.0
    assert result["ath_date"] == "2024-01-02"
    assert result["atl_date"] == "2024-01-03"
    assert result["down_from_ath_pct"] == 25.0
    assert result["up_from_atl_pct"] == 200.0
    assert result["range_position"] == 66.6667


def test_get_eps_trend_computes_yoy(monkeypatch):
    _reset_cache()

    class FakeTicker:
        @property
        def income_stmt(self):
            return pd.DataFrame(
                {
                    pd.Timestamp("2024-12-31"): {"Diluted EPS": -6.0},
                    pd.Timestamp("2023-12-31"): {"Diluted EPS": -8.0},
                    pd.Timestamp("2022-12-31"): {"Diluted EPS": -10.0},
                }
            )

        @property
        def financials(self):
            return pd.DataFrame()

    monkeypatch.setattr(md.yf, "Ticker", lambda ticker: FakeTicker())
    monkeypatch.setattr(md, "_run_with_timeout", lambda fn, timeout_seconds=10: fn())

    result = md.get_eps_trend("TEST")

    assert result["earliest_year"] == "2022"
    assert result["latest_year"] == "2024"
    assert [row["year"] for row in result["eps_history"]] == ["2022", "2023", "2024"]
    assert result["eps_history"][0]["yoy_change"] is None
    assert result["eps_history"][1]["yoy_change"] == 0.2
    assert result["eps_history"][2]["yoy_change"] == 0.25
