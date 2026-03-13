from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd

from ..database import get_db
from ..models import Holding
from ..services.market_data import get_portfolio_returns, get_multiple_prices

router = APIRouter()

TRADING_DAYS = 252
RISK_FREE_RATE = 0.05 / TRADING_DAYS  # Daily risk-free rate


@router.get("/portfolio-risk")
def portfolio_risk(db: Session = Depends(get_db)):
    holdings = db.query(Holding).filter(
        Holding.asset_type.in_(["STOCK", "ETF"])
    ).all()
    if not holdings:
        return {"error": "No stock/ETF holdings found"}

    tickers = list({h.ticker for h in holdings})
    returns_df = get_portfolio_returns(tickers, period="1y")

    if returns_df is None or returns_df.empty or len(returns_df) < 30:
        return {"error": "Insufficient price history"}

    # Drop tickers with too many NaNs
    returns_df = returns_df.dropna(axis=1, thresh=int(len(returns_df) * 0.8))
    returns_df = returns_df.fillna(0)

    # Weights by cost basis
    total_cost = sum(h.shares * h.avg_price for h in holdings if h.ticker in returns_df.columns)
    weights = {
        h.ticker: (h.shares * h.avg_price) / total_cost
        for h in holdings if h.ticker in returns_df.columns and total_cost > 0
    }
    tickers_in_df = [t for t in returns_df.columns if t in weights]
    returns_df = returns_df[tickers_in_df]

    w_total = sum(weights[t] for t in tickers_in_df)
    w_array = np.array([weights[t] / w_total for t in tickers_in_df])

    port_returns = returns_df.values @ w_array

    # Portfolio-level metrics
    var_95 = float(np.percentile(port_returns, 5))
    var_99 = float(np.percentile(port_returns, 1))
    excess = port_returns - RISK_FREE_RATE
    sharpe = float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS)) if excess.std() > 0 else 0
    cum = np.cumprod(1 + port_returns)
    rolling_max = np.maximum.accumulate(cum)
    max_dd = float(np.min((cum - rolling_max) / rolling_max))
    annual_return = float((1 + port_returns.mean()) ** TRADING_DAYS - 1)
    annual_vol = float(port_returns.std() * np.sqrt(TRADING_DAYS))

    # Per-stock metrics
    stock_metrics = {}
    for ticker in tickers_in_df:
        r = returns_df[ticker].values
        cum_s = np.cumprod(1 + r)
        rm_s = np.maximum.accumulate(cum_s)
        stock_metrics[ticker] = {
            "annual_return": round(float((1 + r.mean()) ** TRADING_DAYS - 1) * 100, 2),
            "annual_vol": round(float(r.std() * np.sqrt(TRADING_DAYS)) * 100, 2),
            "sharpe": round(
                float((r.mean() - RISK_FREE_RATE) / r.std() * np.sqrt(TRADING_DAYS))
                if r.std() > 0 else 0, 2
            ),
            "max_drawdown": round(float(np.min((cum_s - rm_s) / rm_s)) * 100, 2),
            "var_95": round(float(np.percentile(r, 5)) * 100, 2),
            "weight": round(weights[ticker] / w_total * 100, 2),
        }

    # Correlation matrix
    corr = returns_df.corr().round(3)
    correlation = {
        col: {row: corr.loc[row, col] for row in corr.index}
        for col in corr.columns
    }

    return {
        "portfolio": {
            "var_95_daily": round(var_95 * 100, 2),
            "var_99_daily": round(var_99 * 100, 2),
            "sharpe": round(sharpe, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "annual_return": round(annual_return * 100, 2),
            "annual_volatility": round(annual_vol * 100, 2),
        },
        "stocks": stock_metrics,
        "correlation": correlation,
        "tickers": tickers_in_df,
    }


@router.get("/performance")
def portfolio_performance(db: Session = Depends(get_db)):
    holdings = db.query(Holding).all()
    if not holdings:
        return {"data": []}

    relevant = [h for h in holdings if h.asset_type in ("STOCK", "ETF")]
    if not relevant:
        return {"data": []}

    from ..services.market_data import get_price_history
    price_lookup: dict = {}
    for h in relevant:
        history = get_price_history(h.ticker, period="1y")
        if history:
            price_lookup[h.ticker] = {d["date"]: d["close"] for d in history}

    if not price_lookup:
        return {"data": []}

    all_dates = sorted({d for prices in price_lookup.values() for d in prices})
    result = []
    for date in all_dates:
        total_value = 0.0
        total_cost = sum(h.shares * h.avg_price for h in relevant)
        for h in relevant:
            if h.ticker in price_lookup:
                available = [d for d in sorted(price_lookup[h.ticker]) if d <= date]
                if available:
                    total_value += h.shares * price_lookup[h.ticker][available[-1]]
        if total_cost > 0:
            result.append({
                "date": date,
                "value": round(total_value, 2),
                "cost": round(total_cost, 2),
                "return_pct": round((total_value - total_cost) / total_cost * 100, 2),
            })

    # Downsample to ~100 points if needed
    step = max(1, len(result) // 100)
    return {"data": result[::step]}
