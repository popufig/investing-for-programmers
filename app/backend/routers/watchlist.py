from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Holding, Watchlist
from ..schemas import (
    WatchlistConvertPayload,
    WatchlistConvertResponse,
    WatchlistCreate,
    WatchlistEnriched,
    WatchlistResponse,
    WatchlistUpdate,
)
from ..services.market_data import get_multiple_quotes, get_ticker_info

router = APIRouter()


def _infer_asset_type(info: dict) -> str:
    qt = (info.get("quote_type") or "").upper()
    if qt == "ETF":
        return "ETF"
    if qt == "MUTUALFUND":
        return "FUND"
    if qt in ("BOND", "FIXED_INCOME"):
        return "BOND"
    return "STOCK"


@router.get("/", response_model=List[WatchlistEnriched])
def list_watchlist(db: Session = Depends(get_db)):
    rows = db.query(Watchlist).order_by(Watchlist.created_at.desc(), Watchlist.id.desc()).all()
    if not rows:
        return []

    tickers = [row.ticker for row in rows]
    quotes = get_multiple_quotes(tickers)
    info_map = {ticker: get_ticker_info(ticker) for ticker in sorted(set(tickers))}

    result: List[WatchlistEnriched] = []
    for row in rows:
        quote = quotes.get(row.ticker, {})
        info = info_map.get(row.ticker, {})
        result.append(
            WatchlistEnriched(
                id=row.id,
                ticker=row.ticker,
                name=row.name,
                notes=row.notes,
                target_price=row.target_price,
                created_at=row.created_at,
                current_price=quote.get("current_price"),
                change_pct=quote.get("change_pct"),
                sector=info.get("sector"),
                market_cap=info.get("market_cap_usd") or info.get("market_cap"),
            )
        )
    return result


@router.post("/", response_model=WatchlistResponse, status_code=201)
def add_watchlist_item(data: WatchlistCreate, db: Session = Depends(get_db)):
    ticker = data.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    existing = db.query(Watchlist).filter(Watchlist.ticker == ticker).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"{ticker} is already in watchlist")

    info = get_ticker_info(ticker)
    if "error" in info and not info.get("name"):
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

    row = Watchlist(
        ticker=ticker,
        name=info.get("name") or ticker,
        notes=data.notes,
        target_price=data.target_price,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{item_id}", response_model=WatchlistResponse)
def update_watchlist_item(item_id: int, data: WatchlistUpdate, db: Session = Depends(get_db)):
    row = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(row)
    db.commit()
    return {"message": "Deleted"}


@router.post("/{item_id}/convert", response_model=WatchlistConvertResponse)
def convert_watchlist_to_holding(
    item_id: int,
    data: WatchlistConvertPayload,
    db: Session = Depends(get_db),
):
    row = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    if data.shares <= 0 or data.avg_price <= 0:
        raise HTTPException(status_code=400, detail="shares and avg_price must be positive")

    info = get_ticker_info(row.ticker)
    asset_type = _infer_asset_type(info)
    currency = info.get("currency") or "USD"
    exchange = info.get("exchange")

    try:
        holding = Holding(
            ticker=row.ticker,
            name=row.name or info.get("name") or row.ticker,
            shares=data.shares,
            avg_price=data.avg_price,
            currency=currency,
            asset_type=asset_type,
            portfolio=data.portfolio,
            exchange=exchange,
            notes=row.notes,
        )
        db.add(holding)
        db.flush()
        holding_id = holding.id
        db.delete(row)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to convert watchlist item: {e}")

    return WatchlistConvertResponse(
        holding_id=holding_id,
        ticker=holding.ticker,
        message="Converted to holding",
    )
