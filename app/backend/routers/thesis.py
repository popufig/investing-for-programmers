from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import InvestmentThesis, ThesisCheckpoint, ThesisTicker
from ..schemas import (
    CheckpointCreate,
    CheckpointResponse,
    ThesisCreate,
    ThesisDetailResponse,
    ThesisResponse,
    ThesisUpdate,
)
from ..services.market_data import get_multiple_quotes, get_price_history

router = APIRouter()

THESIS_STATUSES = {"active", "validated", "invalidated", "archived"}
CHECKPOINT_STATUSES = {"on_track", "at_risk", "invalidated"}


def _normalize_ticker_list(tickers: List[str]) -> List[str]:
    deduped = []
    seen = set()
    for raw in tickers:
        ticker = (raw or "").upper().strip()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        deduped.append(ticker)
    return deduped


def _baseline_close_price(ticker: str) -> Optional[float]:
    history = get_price_history(ticker=ticker, period="1mo", interval="1d")
    if not history:
        return None
    close = history[-1].get("close")
    try:
        return round(float(close), 4) if close is not None else None
    except (TypeError, ValueError):
        return None


def _serialize_thesis(thesis: InvestmentThesis, include_checkpoints: bool = False) -> dict:
    payload = {
        "id": thesis.id,
        "title": thesis.title,
        "status": thesis.status,
        "summary": thesis.summary,
        "category": thesis.category,
        "target_date": thesis.target_date,
        "created_at": thesis.created_at,
        "updated_at": thesis.updated_at,
        "tickers": [
            {
                "ticker": item.ticker,
                "baseline_price": item.baseline_price,
            }
            for item in sorted(thesis.tickers, key=lambda x: x.ticker)
        ],
    }
    if include_checkpoints:
        payload["checkpoints"] = [
            {
                "id": row.id,
                "note": row.note,
                "status_at_check": row.status_at_check,
                "created_at": row.created_at,
            }
            for row in sorted(thesis.checkpoints, key=lambda x: x.created_at or x.id, reverse=True)
        ]
    return payload


def _get_thesis_or_404(db: Session, thesis_id: int) -> InvestmentThesis:
    row = db.query(InvestmentThesis).filter(InvestmentThesis.id == thesis_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return row


@router.get("", response_model=List[ThesisResponse])
def list_theses(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    q = db.query(InvestmentThesis)
    if status:
        st = status.strip().lower()
        if st not in THESIS_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        q = q.filter(InvestmentThesis.status == st)
    rows = q.order_by(InvestmentThesis.created_at.desc(), InvestmentThesis.id.desc()).all()
    return [_serialize_thesis(row, include_checkpoints=False) for row in rows]


@router.post("", response_model=ThesisResponse, status_code=201)
def create_thesis(payload: ThesisCreate, db: Session = Depends(get_db)):
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    status = (payload.status or "active").strip().lower()
    if status not in THESIS_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid thesis status")

    tickers = _normalize_ticker_list(payload.tickers or [])
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")

    row = InvestmentThesis(
        title=title,
        status=status,
        summary=payload.summary,
        category=payload.category,
        target_date=payload.target_date,
    )
    db.add(row)
    db.flush()

    for ticker in tickers:
        db.add(
            ThesisTicker(
                thesis_id=row.id,
                ticker=ticker,
                baseline_price=_baseline_close_price(ticker),
            )
        )

    db.commit()
    db.refresh(row)
    return _serialize_thesis(row, include_checkpoints=False)


@router.get("/{thesis_id}", response_model=ThesisDetailResponse)
def get_thesis_detail(thesis_id: int, db: Session = Depends(get_db)):
    row = _get_thesis_or_404(db, thesis_id)
    return _serialize_thesis(row, include_checkpoints=True)


@router.put("/{thesis_id}", response_model=ThesisResponse)
def update_thesis(thesis_id: int, payload: ThesisUpdate, db: Session = Depends(get_db)):
    row = _get_thesis_or_404(db, thesis_id)
    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates:
        st = (updates["status"] or "").strip().lower()
        if st not in THESIS_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid thesis status")
        row.status = st

    if "title" in updates:
        title = (updates["title"] or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        row.title = title

    for field in ("summary", "category", "target_date"):
        if field in updates:
            setattr(row, field, updates[field])

    if "tickers" in updates and updates["tickers"] is not None:
        tickers = _normalize_ticker_list(updates["tickers"])
        if not tickers:
            raise HTTPException(status_code=400, detail="At least one ticker is required")

        db.query(ThesisTicker).filter(ThesisTicker.thesis_id == row.id).delete(synchronize_session=False)
        for ticker in tickers:
            db.add(
                ThesisTicker(
                    thesis_id=row.id,
                    ticker=ticker,
                    baseline_price=_baseline_close_price(ticker),
                )
            )

    db.commit()
    db.refresh(row)
    return _serialize_thesis(row, include_checkpoints=False)


@router.delete("/{thesis_id}")
def delete_thesis(thesis_id: int, db: Session = Depends(get_db)):
    row = _get_thesis_or_404(db, thesis_id)
    db.delete(row)
    db.commit()
    return {"message": "Deleted"}


@router.post("/{thesis_id}/checkpoints", response_model=CheckpointResponse, status_code=201)
def add_checkpoint(thesis_id: int, payload: CheckpointCreate, db: Session = Depends(get_db)):
    row = _get_thesis_or_404(db, thesis_id)
    note = (payload.note or "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="note is required")

    status_at_check = payload.status_at_check
    if status_at_check is not None:
        status_at_check = status_at_check.strip().lower()
        if status_at_check not in CHECKPOINT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid checkpoint status")

    checkpoint = ThesisCheckpoint(
        thesis_id=row.id,
        note=note,
        status_at_check=status_at_check,
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


@router.get("/{thesis_id}/snapshot")
def get_thesis_snapshot(thesis_id: int, db: Session = Depends(get_db)):
    row = _get_thesis_or_404(db, thesis_id)
    ticker_rows = sorted(row.tickers, key=lambda x: x.ticker)
    tickers = [item.ticker for item in ticker_rows]
    quotes = get_multiple_quotes(tickers)

    snapshot_rows = []
    for item in ticker_rows:
        quote = quotes.get(item.ticker, {})
        current_price = quote.get("current_price")
        baseline_price = item.baseline_price
        change_abs = None
        change_pct = None
        if current_price is not None and baseline_price not in (None, 0):
            change_abs = round(current_price - baseline_price, 4)
            change_pct = round((current_price - baseline_price) / baseline_price * 100, 4)

        snapshot_rows.append(
            {
                "ticker": item.ticker,
                "baseline_price": baseline_price,
                "current_price": current_price,
                "change_abs": change_abs,
                "change_pct": change_pct,
                "day_change_pct": quote.get("change_pct"),
            }
        )

    return {
        "thesis_id": row.id,
        "title": row.title,
        "status": row.status,
        "created_at": row.created_at,
        "target_date": row.target_date,
        "tickers": snapshot_rows,
    }
