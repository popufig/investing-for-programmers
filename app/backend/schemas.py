from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PortfolioResponse(PortfolioCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class HoldingCreate(BaseModel):
    ticker: str
    name: Optional[str] = None
    shares: float
    avg_price: float
    currency: str = "USD"
    asset_type: str
    portfolio: Optional[str] = None
    exchange: Optional[str] = None
    notes: Optional[str] = None


class HoldingUpdate(BaseModel):
    name: Optional[str] = None
    shares: Optional[float] = None
    avg_price: Optional[float] = None
    currency: Optional[str] = None
    asset_type: Optional[str] = None
    portfolio: Optional[str] = None
    exchange: Optional[str] = None
    notes: Optional[str] = None


class HoldingResponse(HoldingCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class HoldingEnriched(HoldingResponse):
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_usd: Optional[float] = None
    cost_basis: float = 0
    current_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_pct: Optional[float] = None


class WatchlistCreate(BaseModel):
    ticker: str
    notes: Optional[str] = None
    target_price: Optional[float] = None


class WatchlistUpdate(BaseModel):
    notes: Optional[str] = None
    target_price: Optional[float] = None


class WatchlistResponse(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    notes: Optional[str] = None
    target_price: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistEnriched(WatchlistResponse):
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None


class WatchlistConvertPayload(BaseModel):
    shares: float
    avg_price: float
    portfolio: Optional[str] = None


class WatchlistConvertResponse(BaseModel):
    holding_id: int
    ticker: str
    message: str


class TickerSignal(BaseModel):
    ticker: str
    close: Optional[float] = None
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None
    trend: Optional[str] = None
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    macd_hist: Optional[float] = None
    macd_trend: Optional[str] = None


class PeerGroupPayload(BaseModel):
    peers: List[str]


class PeerGroupResponse(BaseModel):
    ticker: str
    peers: List[str]


class ThesisTickerPayload(BaseModel):
    ticker: str


class ThesisTickerResponse(BaseModel):
    ticker: str
    baseline_price: Optional[float] = None


class ThesisCreate(BaseModel):
    title: str
    summary: Optional[str] = None
    tickers: List[str]
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    status: str = "active"


class ThesisUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    tickers: Optional[List[str]] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None


class CheckpointCreate(BaseModel):
    note: str
    status_at_check: Optional[str] = None


class CheckpointResponse(BaseModel):
    id: int
    note: str
    status_at_check: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ThesisResponse(BaseModel):
    id: int
    title: str
    status: str
    summary: Optional[str] = None
    tickers: List[ThesisTickerResponse] = []
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThesisDetailResponse(ThesisResponse):
    checkpoints: List[CheckpointResponse] = []
