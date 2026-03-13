from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    name = Column(String(200))
    shares = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    asset_type = Column(String(20), nullable=False)  # STOCK, ETF, BOND, FUND
    portfolio = Column(String(100))
    exchange = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, unique=True)
    name = Column(String(200))
    notes = Column(Text)
    target_price = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class ScreenerTicker(Base):
    __tablename__ = "screener_tickers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False)


class PeerGroup(Base):
    __tablename__ = "peer_group"
    __table_args__ = (
        UniqueConstraint("ticker", "peer_ticker", name="uq_peer_group_pair"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    peer_ticker = Column(String(20), nullable=False)
    rank = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())


class InvestmentThesis(Base):
    __tablename__ = "investment_theses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    summary = Column(Text)
    category = Column(String(50))
    target_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    tickers = relationship("ThesisTicker", back_populates="thesis", cascade="all, delete-orphan")
    checkpoints = relationship("ThesisCheckpoint", back_populates="thesis", cascade="all, delete-orphan")


class ThesisTicker(Base):
    __tablename__ = "thesis_tickers"
    __table_args__ = (
        UniqueConstraint("thesis_id", "ticker", name="uq_thesis_ticker"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    thesis_id = Column(Integer, ForeignKey("investment_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), nullable=False)
    baseline_price = Column(Float)

    thesis = relationship("InvestmentThesis", back_populates="tickers")


class ThesisCheckpoint(Base):
    __tablename__ = "thesis_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thesis_id = Column(Integer, ForeignKey("investment_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    note = Column(Text, nullable=False)
    status_at_check = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    thesis = relationship("InvestmentThesis", back_populates="checkpoints")
