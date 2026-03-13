from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ScreenerTicker
from ..schemas import PeerGroupPayload, PeerGroupResponse, TickerSignal
from ..services.market_data import (
    get_ath_analysis,
    get_analyst_data,
    get_db_peer_group,
    get_economic_cycle_context,
    get_earnings_estimates,
    get_eps_trend,
    get_esg,
    get_financials,
    get_google_trends,
    get_news_sentiment,
    get_normalized_comparison,
    get_peer_comparison,
    get_price_history,
    get_ratio_trends,
    get_return_analysis,
    resolve_search_ticker,
    get_screen_options,
    get_technicals,
    get_ticker_info,
    invalidate_screener_cache,
    screen_stocks,
    set_db_peer_group,
)

router = APIRouter()


class UniverseAdd(BaseModel):
    tickers: List[str]


def _get_universe_tickers(db: Session) -> List[str]:
    rows = db.query(ScreenerTicker.ticker).order_by(ScreenerTicker.ticker).all()
    return [r[0] for r in rows] if rows else None  # None → fallback to default

VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
VALID_INTERVALS = {"1d", "1wk", "1mo"}
COMPARE_PERIODS = {"3mo", "6mo", "1y", "2y", "5y"}


def _infer_asset_type(info: dict) -> str:
    qt = (info.get("quote_type") or "").upper()
    if qt == "ETF":
        return "ETF"
    if qt == "MUTUALFUND":
        return "FUND"
    if qt in ("BOND", "FIXED_INCOME"):
        return "BOND"
    return "STOCK"


@router.get("/search")
def search_ticker(q: str = Query(..., min_length=1)):
    resolved = resolve_search_ticker(q)
    ticker = (resolved or {}).get("ticker") or q.upper().strip()
    info = get_ticker_info(ticker)
    if "error" in info or info.get("current_price") is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{q}' not found")
    return {
        "ticker": ticker,
        "name": info.get("name") or (resolved or {}).get("name") or ticker,
        "current_price": info.get("current_price"),
        "currency": info.get("currency", "USD"),
        "asset_type": _infer_asset_type(info),
        "exchange": info.get("exchange", ""),
        "sector": info.get("sector"),
    }


@router.get("/compare")
def compare_stocks(
    tickers: str = Query(..., description="Comma-separated tickers, 2 to 6"),
    period: str = Query("1y", enum=list(COMPARE_PERIODS)),
):
    parsed = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    unique = []
    seen = set()
    for t in parsed:
        if t in seen:
            continue
        seen.add(t)
        unique.append(t)
    if len(unique) < 2:
        raise HTTPException(status_code=400, detail="At least 2 tickers are required")
    if len(unique) > 6:
        raise HTTPException(status_code=400, detail="At most 6 tickers are allowed")
    return get_normalized_comparison(unique, period)


@router.get("/screen")
def screen(
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    pe_min: Optional[float] = None,
    pe_max: Optional[float] = None,
    dividend_yield_min: Optional[float] = None,
    change_52w_min: Optional[float] = None,
    db: Session = Depends(get_db),
):
    filters = {
        "sector": sector,
        "industry": industry,
        "country": country,
        "market_cap_min": market_cap_min,
        "market_cap_max": market_cap_max,
        "pe_min": pe_min,
        "pe_max": pe_max,
        "dividend_yield_min": dividend_yield_min,
        "change_52w_min": change_52w_min,
    }
    universe = _get_universe_tickers(db)
    return screen_stocks(filters, universe)


@router.get("/screen/options")
def screen_options(db: Session = Depends(get_db)):
    universe = _get_universe_tickers(db)
    return get_screen_options(universe)


@router.get("/universe")
def list_universe(db: Session = Depends(get_db)):
    rows = db.query(ScreenerTicker).order_by(ScreenerTicker.ticker).all()
    return [{"id": r.id, "ticker": r.ticker} for r in rows]


@router.post("/universe", status_code=201)
def add_universe_tickers(data: UniverseAdd, db: Session = Depends(get_db)):
    added = []
    for raw in data.tickers:
        ticker = raw.upper().strip()
        if not ticker:
            continue
        exists = db.query(ScreenerTicker).filter(ScreenerTicker.ticker == ticker).first()
        if exists:
            continue
        info = get_ticker_info(ticker)
        if "error" in info and not info.get("name"):
            continue
        row = ScreenerTicker(ticker=ticker)
        db.add(row)
        added.append(ticker)
    db.commit()
    if added:
        invalidate_screener_cache()
    return {"added": added, "total": db.query(ScreenerTicker).count()}


@router.delete("/universe/{ticker}")
def remove_universe_ticker(ticker: str, db: Session = Depends(get_db)):
    row = db.query(ScreenerTicker).filter(ScreenerTicker.ticker == ticker.upper().strip()).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ticker not in universe")
    db.delete(row)
    db.commit()
    invalidate_screener_cache()
    return {"message": f"Removed {ticker.upper().strip()}"}


@router.get("/trends")
def get_trends(
    keywords: str = Query(..., min_length=1, description="Comma-separated keywords, max 5"),
    timeframe: str = Query("today 12-m"),
):
    parsed = [_ for _ in [part.strip() for part in keywords.split(",")] if _]
    if not parsed:
        raise HTTPException(status_code=400, detail="At least one keyword is required")
    if len(parsed) > 5:
        raise HTTPException(status_code=400, detail="At most 5 keywords are allowed")
    return get_google_trends(parsed, timeframe)


def _classify_signal(technicals: list) -> dict:
    """Extract the latest technical signals from a technicals time-series."""
    if not technicals:
        return {}
    latest = technicals[-1]
    close = latest.get("close")
    rsi = latest.get("rsi")
    sma20 = latest.get("sma20")
    sma50 = latest.get("sma50")
    sma200 = latest.get("sma200")
    macd_hist = latest.get("macd_hist")

    # RSI signal
    rsi_signal = "neutral"
    if rsi is not None:
        if rsi >= 70:
            rsi_signal = "overbought"
        elif rsi <= 30:
            rsi_signal = "oversold"

    # Trend based on price vs SMAs
    trend = "neutral"
    if close is not None:
        above_20 = sma20 is not None and close > sma20
        above_50 = sma50 is not None and close > sma50
        below_20 = sma20 is not None and close < sma20
        below_50 = sma50 is not None and close < sma50
        if above_20 and above_50:
            trend = "bullish"
        elif below_20 and below_50:
            trend = "bearish"

    # MACD trend
    macd_trend = "neutral"
    if macd_hist is not None:
        macd_trend = "bullish" if macd_hist > 0 else "bearish"

    return {
        "close": close,
        "rsi": round(rsi, 1) if rsi is not None else None,
        "rsi_signal": rsi_signal,
        "trend": trend,
        "sma20": round(sma20, 2) if sma20 is not None else None,
        "sma50": round(sma50, 2) if sma50 is not None else None,
        "sma200": round(sma200, 2) if sma200 is not None else None,
        "macd_hist": round(macd_hist, 4) if macd_hist is not None else None,
        "macd_trend": macd_trend,
    }


@router.get("/signals", response_model=List[TickerSignal])
def get_batch_signals(
    tickers: str = Query(..., description="Comma-separated tickers, max 20"),
):
    parsed = list(dict.fromkeys(t.strip().upper() for t in tickers.split(",") if t.strip()))
    if not parsed:
        raise HTTPException(status_code=400, detail="At least 1 ticker is required")
    if len(parsed) > 20:
        parsed = parsed[:20]

    def _fetch_one(ticker: str) -> TickerSignal:
        try:
            data = get_technicals(ticker, "3mo")
            sig = _classify_signal(data)
            return TickerSignal(ticker=ticker, **sig)
        except Exception:
            return TickerSignal(ticker=ticker)

    results = []
    with ThreadPoolExecutor(max_workers=min(len(parsed), 8)) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in parsed}
        for future in as_completed(futures):
            results.append(future.result())

    # Preserve input order
    order = {t: i for i, t in enumerate(parsed)}
    results.sort(key=lambda s: order.get(s.ticker, 999))
    return results


@router.get("/{ticker}")
def get_stock(ticker: str):
    info = get_ticker_info(ticker.upper())
    if "error" in info and not info.get("name"):
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return info


@router.get("/{ticker}/history")
def get_history(
    ticker: str,
    period: str = Query("1y", enum=list(VALID_PERIODS)),
    interval: str = Query("1d", enum=list(VALID_INTERVALS)),
):
    data = get_price_history(ticker.upper(), period, interval)
    return {"ticker": ticker.upper(), "period": period, "interval": interval, "data": data}


@router.get("/{ticker}/ath")
def get_stock_ath(ticker: str):
    data = get_ath_analysis(ticker.upper())
    if data.get("error") and data.get("all_time_high") is None:
        raise HTTPException(status_code=404, detail=f"ATH data for '{ticker}' not found")
    return data


@router.get("/{ticker}/eps-trend")
def get_stock_eps_trend(ticker: str):
    data = get_eps_trend(ticker.upper())
    if data.get("error") and not data.get("eps_history"):
        raise HTTPException(status_code=404, detail=f"EPS trend data for '{ticker}' not found")
    return data


@router.get("/{ticker}/earnings-estimates")
def get_stock_earnings_estimates(ticker: str):
    data = get_earnings_estimates(ticker.upper())
    if data.get("error") and not data.get("earnings_estimates") and not data.get("revenue_estimates"):
        raise HTTPException(status_code=404, detail=f"Earnings estimate data for '{ticker}' not found")
    return data


@router.get("/{ticker}/technicals")
def get_tech(
    ticker: str,
    period: str = Query("1y", enum=list(VALID_PERIODS)),
):
    data = get_technicals(ticker.upper(), period)
    return {"ticker": ticker.upper(), "period": period, "data": data}


@router.get("/{ticker}/financials")
def get_stock_financials(ticker: str):
    data = get_financials(ticker.upper())
    if data.get("error") and not any(data.get(key) for key in ("income_statement", "balance_sheet", "cash_flow")):
        raise HTTPException(status_code=404, detail=f"Financial data for '{ticker}' not found")
    return data


@router.get("/{ticker}/returns")
def get_stock_returns(
    ticker: str,
    period: str = Query("1y", enum=list(VALID_PERIODS)),
):
    data = get_return_analysis(ticker.upper(), period)
    if data.get("error") and not data.get("daily_returns"):
        raise HTTPException(status_code=404, detail=f"Return data for '{ticker}' not found")
    return data


@router.get("/{ticker}/ratio-trends")
def get_stock_ratio_trends(ticker: str):
    data = get_ratio_trends(ticker.upper())
    if data.get("error") and not data.get("periods"):
        raise HTTPException(status_code=404, detail=f"Ratio trend data for '{ticker}' not found")
    return data


@router.get("/{ticker}/peers")
def get_stock_peers(
    ticker: str,
    tickers: Optional[str] = Query(None, description="Comma-separated peer tickers, max 5"),
):
    data = get_peer_comparison(ticker.upper(), tickers)
    if data.get("error") and not data.get("peers"):
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return data


@router.get("/{ticker}/peer-group", response_model=PeerGroupResponse)
def get_stock_peer_group(ticker: str):
    main = ticker.upper().strip()
    peers = get_db_peer_group(main)
    return {"ticker": main, "peers": peers}


@router.put("/{ticker}/peer-group", response_model=PeerGroupResponse)
def put_stock_peer_group(ticker: str, payload: PeerGroupPayload):
    main = ticker.upper().strip()
    peers = set_db_peer_group(main, payload.peers)
    if payload.peers and not peers:
        raise HTTPException(status_code=500, detail="Failed to update peer_group")
    return {"ticker": main, "peers": peers}


@router.get("/{ticker}/analyst")
def get_stock_analyst(ticker: str):
    data = get_analyst_data(ticker.upper())
    if data.get("error") and data.get("current_price") is None and data.get("num_analysts") is None:
        raise HTTPException(status_code=404, detail=f"Analyst data for '{ticker}' not found")
    return data


@router.get("/{ticker}/esg")
def get_stock_esg(ticker: str):
    data = get_esg(ticker.upper())
    if data.get("ticker") is None:
        raise HTTPException(status_code=404, detail=f"ESG data for '{ticker}' not found")
    return data


@router.get("/{ticker}/sentiment")
def get_stock_sentiment(ticker: str):
    return get_news_sentiment(ticker.upper())


@router.get("/{ticker}/economic-cycle")
def get_stock_economic_cycle(ticker: str):
    data = get_economic_cycle_context(ticker.upper())
    if data.get("ticker") is None:
        raise HTTPException(status_code=404, detail=f"Economic cycle data for '{ticker}' not found")
    return data
