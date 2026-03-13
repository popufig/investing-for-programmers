from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "investing.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _seed_demo_data()


def _seed_demo_data():
    from .models import Holding, Portfolio, PeerGroup, ScreenerTicker
    db = SessionLocal()
    try:
        if db.query(Portfolio).count() == 0:
            db.add_all([
                Portfolio(name="Tech", description="Technology growth stocks"),
                Portfolio(name="Index", description="Passive index funds"),
                Portfolio(name="Income", description="Dividend & income stocks"),
            ])
        if db.query(Holding).count() == 0:
            db.add_all([
                Holding(ticker="AAPL", name="Apple Inc.", shares=10, avg_price=150.0,
                        currency="USD", asset_type="STOCK", portfolio="Tech", exchange="NASDAQ"),
                Holding(ticker="MSFT", name="Microsoft Corp", shares=5, avg_price=280.0,
                        currency="USD", asset_type="STOCK", portfolio="Tech", exchange="NASDAQ"),
                Holding(ticker="NVDA", name="NVIDIA Corp", shares=3, avg_price=400.0,
                        currency="USD", asset_type="STOCK", portfolio="Tech", exchange="NASDAQ"),
                Holding(ticker="SPY", name="SPDR S&P 500 ETF", shares=8, avg_price=430.0,
                        currency="USD", asset_type="ETF", portfolio="Index", exchange="ARCA"),
                Holding(ticker="VOO", name="Vanguard S&P 500 ETF", shares=5, avg_price=380.0,
                        currency="USD", asset_type="ETF", portfolio="Index", exchange="BATS"),
                Holding(ticker="JNJ", name="Johnson & Johnson", shares=15, avg_price=155.0,
                        currency="USD", asset_type="STOCK", portfolio="Income", exchange="NYSE"),
            ])
        if db.query(ScreenerTicker).count() == 0:
            from .services.market_data import SCREENER_UNIVERSE
            db.add_all([ScreenerTicker(ticker=t) for t in SCREENER_UNIVERSE])
        if db.query(PeerGroup).count() == 0:
            defaults = {
                "AAPL": ["MSFT", "GOOGL", "META", "AMZN"],
                "MSFT": ["AAPL", "GOOGL", "AMZN", "META"],
                "GOOGL": ["MSFT", "META", "AAPL", "AMZN"],
                "META": ["GOOGL", "SNAP", "PINS", "AAPL"],
                "AMZN": ["WMT", "COST", "AAPL", "MSFT"],
                "NVDA": ["AMD", "INTC", "TSM", "AVGO"],
                "TSLA": ["RIVN", "F", "GM", "NIO"],
            }
            rows = []
            for ticker, peers in defaults.items():
                for rank, peer in enumerate(peers, start=1):
                    rows.append(PeerGroup(ticker=ticker, peer_ticker=peer, rank=rank))
            db.add_all(rows)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
