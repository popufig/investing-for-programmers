from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Holding, Portfolio
from ..schemas import (
    HoldingCreate, HoldingUpdate, HoldingResponse, HoldingEnriched,
    PortfolioCreate, PortfolioResponse,
)
from ..services.market_data import get_multiple_prices, get_ticker_info

router = APIRouter()


# ── Portfolios ──────────────────────────────────────────────────────────────

@router.get("/portfolios", response_model=List[PortfolioResponse])
def list_portfolios(db: Session = Depends(get_db)):
    return db.query(Portfolio).order_by(Portfolio.name).all()


@router.post("/portfolios", response_model=PortfolioResponse)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    existing = db.query(Portfolio).filter(Portfolio.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Portfolio name already exists")
    p = Portfolio(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(p)
    db.commit()
    return {"message": "Deleted"}


# ── Holdings ────────────────────────────────────────────────────────────────

@router.get("/holdings", response_model=List[HoldingEnriched])
def list_holdings(db: Session = Depends(get_db)):
    holdings = db.query(Holding).order_by(Holding.portfolio, Holding.ticker).all()
    if not holdings:
        return []

    tickers = [h.ticker for h in holdings]
    prices = get_multiple_prices(tickers)
    stock_tickers = sorted({h.ticker for h in holdings if h.asset_type == "STOCK"})
    stock_info = {
        t: get_ticker_info(t)
        for t in stock_tickers
    }

    result = []
    for h in holdings:
        current_price = prices.get(h.ticker)
        cost_basis = round(h.shares * h.avg_price, 2)
        current_value = round(h.shares * current_price, 2) if current_price else None
        gain_loss = round(current_value - cost_basis, 2) if current_value is not None else None
        gain_loss_pct = round(gain_loss / cost_basis * 100, 2) if gain_loss is not None and cost_basis else None

        result.append(HoldingEnriched(
            id=h.id,
            ticker=h.ticker,
            name=h.name or h.ticker,
            shares=h.shares,
            avg_price=h.avg_price,
            currency=h.currency,
            asset_type=h.asset_type,
            portfolio=h.portfolio,
            exchange=h.exchange,
            notes=h.notes,
            created_at=h.created_at,
            current_price=current_price,
            market_cap=stock_info.get(h.ticker, {}).get("market_cap"),
            market_cap_usd=stock_info.get(h.ticker, {}).get("market_cap_usd"),
            cost_basis=cost_basis,
            current_value=current_value,
            gain_loss=gain_loss,
            gain_loss_pct=gain_loss_pct,
        ))
    return result


@router.post("/holdings", response_model=HoldingResponse, status_code=201)
def add_holding(data: HoldingCreate, db: Session = Depends(get_db)):
    ticker = data.ticker.upper().strip()
    name = data.name
    if not name:
        info = get_ticker_info(ticker)
        name = info.get("name", ticker)

    h = Holding(
        ticker=ticker,
        name=name,
        shares=data.shares,
        avg_price=data.avg_price,
        currency=data.currency,
        asset_type=data.asset_type,
        portfolio=data.portfolio,
        exchange=data.exchange,
        notes=data.notes,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.put("/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    h = db.query(Holding).filter(Holding.id == holding_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(h, key, value)
    db.commit()
    db.refresh(h)
    return h


@router.delete("/holdings/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    h = db.query(Holding).filter(Holding.id == holding_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(h)
    db.commit()
    return {"message": "Deleted"}


# ── Summary ──────────────────────────────────────────────────────────────────

@router.get("/summary")
def portfolio_summary(db: Session = Depends(get_db)):
    holdings = db.query(Holding).all()
    if not holdings:
        return {
            "total_value": 0, "total_cost": 0,
            "total_gain_loss": 0, "total_gain_loss_pct": 0,
            "by_type": [], "by_portfolio": [],
        }

    tickers = [h.ticker for h in holdings]
    prices = get_multiple_prices(tickers)

    total_cost = sum(h.shares * h.avg_price for h in holdings)
    total_value = 0.0
    by_type: dict = {}
    by_portfolio: dict = {}

    for h in holdings:
        price = prices.get(h.ticker)
        value = h.shares * price if price else h.shares * h.avg_price
        total_value += value

        by_type[h.asset_type] = by_type.get(h.asset_type, 0) + value
        key = h.portfolio or "Other"
        by_portfolio[key] = by_portfolio.get(key, 0) + value

    gain_loss = total_value - total_cost
    gain_loss_pct = gain_loss / total_cost * 100 if total_cost else 0

    def make_slices(d):
        return [
            {"name": k, "value": round(v, 2),
             "pct": round(v / total_value * 100, 1) if total_value else 0}
            for k, v in sorted(d.items(), key=lambda x: -x[1])
        ]

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain_loss": round(gain_loss, 2),
        "total_gain_loss_pct": round(gain_loss_pct, 2),
        "by_type": make_slices(by_type),
        "by_portfolio": make_slices(by_portfolio),
    }
