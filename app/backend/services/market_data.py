import calendar
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import math
import os
import re
import time
from datetime import date, datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import dotenv_values
try:
    from pytrends.request import TrendReq
except Exception:  # pragma: no cover - optional dependency fallback
    TrendReq = None

# Simple in-memory TTL cache
_cache: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 minutes
_TIMEOUT_EXECUTOR = ThreadPoolExecutor(max_workers=6)

TUSHARE_API_URL = "https://api.tushare.pro"
HK_TICKER_PATTERN = re.compile(r"^(\d{1,5})\.HK$")
US_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]*$")

DEFAULT_PEER_GROUP: Dict[str, List[str]] = {
    "AAPL": ["MSFT", "GOOGL", "META", "AMZN"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "META"],
    "GOOGL": ["MSFT", "META", "AAPL", "AMZN"],
    "META": ["GOOGL", "SNAP", "PINS", "AAPL"],
    "AMZN": ["WMT", "COST", "AAPL", "MSFT"],
    "NVDA": ["AMD", "INTC", "TSM", "AVGO"],
    "TSLA": ["RIVN", "F", "GM", "NIO"],
}

FX_FALLBACK_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.74,
    "AUD": 0.65,
    "NZD": 0.61,
    "CHF": 1.12,
    "SEK": 0.095,
    "NOK": 0.094,
    "DKK": 0.145,
    "JPY": 0.0068,
    "CNY": 0.14,
    "HKD": 0.128,
    "SGD": 0.74,
    "TWD": 0.031,
    "KRW": 0.00076,
    "INR": 0.012,
    "BRL": 0.20,
    "MXN": 0.058,
}

FX_TICKERS: Dict[str, Tuple[str, bool]] = {
    # tuple: (ticker, invert). invert=True means quote is USD/CUR and needs 1/x.
    "EUR": ("EURUSD=X", False),
    "GBP": ("GBPUSD=X", False),
    "AUD": ("AUDUSD=X", False),
    "NZD": ("NZDUSD=X", False),
    "CAD": ("CADUSD=X", False),
    "CHF": ("CHFUSD=X", False),
    "JPY": ("JPY=X", True),
    "CNY": ("CNY=X", True),
    "HKD": ("HKD=X", True),
    "SGD": ("SGD=X", True),
    "INR": ("INR=X", True),
    "KRW": ("KRW=X", True),
    "TWD": ("TWD=X", True),
}

PEER_AUTOREC_UNIVERSE: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "BRK-B", "JPM", "V", "MA", "XOM", "CVX", "LLY", "UNH", "JNJ",
    "PG", "KO", "PEP", "WMT", "COST", "HD", "MCD", "NKE", "DIS",
    "ADBE", "CRM", "ORCL", "INTC", "AMD", "AVGO", "QCOM", "TXN",
    "CSCO", "IBM", "NFLX", "PFE", "MRK", "ABBV", "TMO", "ABT",
    "BAC", "WFC", "GS", "MS", "BLK", "SPGI", "SCHW", "C", "AXP",
]

SCREENER_UNIVERSE: List[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "AVGO", "JPM",
    "LLY", "V", "XOM", "UNH", "WMT", "MA", "JNJ", "PG", "ORCL", "HD",
    "COST", "BAC", "ABBV", "KO", "AMD", "MRK", "PEP", "CVX", "CRM", "ADBE",
    "TMO", "NFLX", "MCD", "ACN", "CSCO", "LIN", "ABT", "WFC", "INTU", "QCOM",
    "TXN", "MS", "PM", "IBM", "GE", "CAT", "SPGI", "AMGN", "DIS", "RTX",
    "GS", "PLD", "ISRG", "BKNG", "BLK", "NOW", "AMAT", "PGR", "NEE", "ELV",
    "SYK", "AXP", "SCHW", "GILD", "ADP", "MDT", "TMUS", "LMT", "MO", "C",
    "TJX", "VRTX", "MMC", "REGN", "ETN", "NKE", "DE", "CB", "CI", "DUK",
    "SO", "D", "AEP", "EOG", "COP", "SLB", "PANW", "SNPS", "ANET", "MU",
    "SHOP", "UBER", "INTC", "PYPL", "SBUX", "BA", "BMY", "PFE", "CVS", "GM",
    "F", "NVO", "SAP", "ASML", "TSM", "SONY", "BABA", "TCEHY", "RHHBY", "NVS",
]

ECONOMIC_PHASES: List[str] = ["Early Cycle", "Mid Cycle", "Late Cycle", "Recession"]

SECTOR_CYCLE_PROFILE: Dict[str, Dict[str, str]] = {
    "Technology": {
        "Early Cycle": "favored",
        "Mid Cycle": "favored",
        "Late Cycle": "neutral",
        "Recession": "stressed",
    },
    "Communication Services": {
        "Early Cycle": "favored",
        "Mid Cycle": "favored",
        "Late Cycle": "neutral",
        "Recession": "stressed",
    },
    "Consumer Cyclical": {
        "Early Cycle": "favored",
        "Mid Cycle": "favored",
        "Late Cycle": "stressed",
        "Recession": "stressed",
    },
    "Financial Services": {
        "Early Cycle": "neutral",
        "Mid Cycle": "favored",
        "Late Cycle": "stressed",
        "Recession": "stressed",
    },
    "Industrials": {
        "Early Cycle": "favored",
        "Mid Cycle": "favored",
        "Late Cycle": "neutral",
        "Recession": "stressed",
    },
    "Basic Materials": {
        "Early Cycle": "favored",
        "Mid Cycle": "favored",
        "Late Cycle": "stressed",
        "Recession": "stressed",
    },
    "Energy": {
        "Early Cycle": "neutral",
        "Mid Cycle": "favored",
        "Late Cycle": "favored",
        "Recession": "stressed",
    },
    "Real Estate": {
        "Early Cycle": "stressed",
        "Mid Cycle": "neutral",
        "Late Cycle": "neutral",
        "Recession": "favored",
    },
    "Utilities": {
        "Early Cycle": "stressed",
        "Mid Cycle": "neutral",
        "Late Cycle": "favored",
        "Recession": "favored",
    },
    "Consumer Defensive": {
        "Early Cycle": "stressed",
        "Mid Cycle": "neutral",
        "Late Cycle": "favored",
        "Recession": "favored",
    },
    "Healthcare": {
        "Early Cycle": "neutral",
        "Mid Cycle": "neutral",
        "Late Cycle": "favored",
        "Recession": "favored",
    },
}


def _get_cached(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _get_cached_ttl(key: str, ttl: int):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _set_cached(key: str, data):
    _cache[key] = (data, time.time())


def _drop_cache_prefix(prefix: str):
    for key in list(_cache.keys()):
        if key.startswith(prefix):
            del _cache[key]


def _run_with_timeout(fn, timeout_seconds: int = 10):
    future = _TIMEOUT_EXECUTOR.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        future.cancel()
        raise TimeoutError(f"Request timed out after {timeout_seconds} seconds")


def _normalize_ticker(ticker: str) -> str:
    return (ticker or "").upper().strip()


def _to_float(value: Any) -> Optional[float]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def _first_non_null(value: Any) -> Any:
    if isinstance(value, pd.Series):
        for item in value.tolist():
            if not pd.isna(item):
                return item
        return None
    return value


def _safe_float(value: Any) -> Optional[float]:
    value = _first_non_null(value)
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def _safe_int(value: Any) -> Optional[int]:
    num = _safe_float(value)
    if num is None:
        return None
    return int(round(num))


def _safe_str(value: Any) -> Optional[str]:
    value = _first_non_null(value)
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text or None


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _format_date_label(value: Any) -> Optional[str]:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def _pick_env_value(key: str) -> Optional[str]:
    direct = _safe_str(os.getenv(key))
    if direct:
        return direct

    candidate_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    ]
    for path in candidate_paths:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            continue
        try:
            values = dotenv_values(path)
            val = _safe_str(values.get(key))
            if val:
                return val
        except Exception:
            continue
    return None


def _pick_any_env_value(keys: List[str]) -> Optional[str]:
    for key in keys:
        value = _pick_env_value(key)
        if value:
            return value
    return None


def _period_to_date_range(period: str) -> Tuple[str, str]:
    p = (period or "1y").strip().lower()
    end = date.today()
    if p == "1mo":
        start = end - timedelta(days=31)
    elif p == "3mo":
        start = end - timedelta(days=92)
    elif p == "6mo":
        start = end - timedelta(days=183)
    elif p == "1y":
        start = end - timedelta(days=366)
    elif p == "2y":
        start = end - timedelta(days=731)
    elif p == "5y":
        start = end - timedelta(days=1827)
    elif p == "ytd":
        start = date(end.year, 1, 1)
    elif p == "max":
        start = end - timedelta(days=365 * 20)
    else:
        start = end - timedelta(days=366)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _period_to_observation_start(period: str) -> str:
    start_raw, _ = _period_to_date_range(period)
    return f"{start_raw[0:4]}-{start_raw[4:6]}-{start_raw[6:8]}"


def _safe_growth_value(value: Any) -> Optional[float]:
    num = _safe_float(value)
    if num is not None:
        return num

    text = _safe_str(value)
    if not text:
        return None
    cleaned = text.replace("%", "").replace(",", "").strip()
    parsed = _safe_float(cleaned)
    if parsed is None:
        return None
    return parsed / 100.0


def _downsample_time_series(rows: List[Dict[str, Any]], max_points: int = 520) -> List[Dict[str, Any]]:
    if len(rows) <= max_points:
        return rows
    step = max(1, math.ceil(len(rows) / max_points))
    sampled = rows[::step]
    if sampled and rows and sampled[-1] != rows[-1]:
        sampled.append(rows[-1])
    return sampled


def _parse_estimate_frame(df: Optional[pd.DataFrame], include_prior: bool) -> List[Dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    work = df.copy()
    lower_cols = {str(c).strip().lower(): c for c in work.columns}
    if "avg" not in lower_cols and "mean" not in lower_cols:
        lower_idx = {str(i).strip().lower() for i in work.index}
        if "avg" in lower_idx or "mean" in lower_idx:
            work = work.transpose()
            lower_cols = {str(c).strip().lower(): c for c in work.columns}

    lower_cols = {str(c).strip().lower(): c for c in work.columns}

    def _col(*aliases: str) -> Optional[str]:
        for alias in aliases:
            if alias in lower_cols:
                return lower_cols[alias]
        return None

    avg_col = _col("avg", "mean")
    low_col = _col("low")
    high_col = _col("high")
    growth_col = _col("growth", "salesgrowth", "revenuegrowth")
    analysts_col = _col("numberofanalysts", "numofanalysts", "analysts")
    prior_col = _col("yearagoeps", "yearsagoeps", "yearagosales", "yearagorevenue")

    if avg_col is None and low_col is None and high_col is None:
        return []

    period_rank = {
        "-1q": 0,
        "0q": 1,
        "+1q": 2,
        "+2q": 3,
        "+3q": 4,
        "0y": 10,
        "+1y": 11,
        "+2y": 12,
        "+3y": 13,
    }

    rows: List[Dict[str, Any]] = []
    for idx, row in work.iterrows():
        period = _safe_str(idx)
        if not period:
            continue
        avg = _safe_float(row.get(avg_col)) if avg_col else None
        low = _safe_float(row.get(low_col)) if low_col else None
        high = _safe_float(row.get(high_col)) if high_col else None
        growth = _safe_growth_value(row.get(growth_col)) if growth_col else None
        analysts = _safe_int(row.get(analysts_col)) if analysts_col else None
        prior = _safe_float(row.get(prior_col)) if prior_col and include_prior else None
        rows.append({
            "period": period,
            "avg": round(avg, 4) if avg is not None else None,
            "low": round(low, 4) if low is not None else None,
            "high": round(high, 4) if high is not None else None,
            "years_ago_eps": round(prior, 4) if prior is not None and include_prior else None,
            "num_analysts": analysts,
            "growth": round(growth, 4) if growth is not None else None,
            "_rank": period_rank.get(period.lower(), 999),
        })

    rows.sort(key=lambda item: (item.get("_rank", 999), item.get("period", "")))
    for row in rows:
        row.pop("_rank", None)
        if not include_prior:
            row.pop("years_ago_eps", None)
    return rows


def _ticker_to_tushare_code(ticker: str) -> Tuple[Optional[str], Optional[str]]:
    norm = _normalize_ticker(ticker)

    hk_match = HK_TICKER_PATTERN.match(norm)
    if hk_match:
        return "hk", f"{hk_match.group(1).zfill(5)}.HK"

    if norm.startswith("^"):
        return None, None
    if not US_TICKER_PATTERN.match(norm):
        return None, None
    if "." in norm:
        suffix = norm.rsplit(".", 1)[1]
        # US classes like BRK.B should pass, exchange suffixes like .SZ/.SS should not.
        if len(suffix) >= 2:
            return None, None
    return "us", norm


def _market_defaults(ticker: str) -> Tuple[Optional[str], Optional[str]]:
    market, _ = _ticker_to_tushare_code(ticker)
    if market == "hk":
        return "HKD", "HKG"
    if market == "us":
        return "USD", "US"
    return None, None


def _tushare_call(api_name: str, params: Dict[str, Any], fields: List[str]) -> List[Dict[str, Any]]:
    token = _pick_any_env_value([
        "datasource.tushare.token",
        "datasource.tushare.secret",
        "tushare.token",
        "TUSHARE_TOKEN",
    ])
    if not token:
        return []

    payload = {
        "api_name": api_name,
        "token": token,
        "params": params,
        "fields": ",".join(fields),
    }

    try:
        req = Request(
            TUSHARE_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=12) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    if raw.get("code") != 0:
        return []

    data = raw.get("data")
    if not isinstance(data, dict):
        return []
    data_fields = data.get("fields")
    items = data.get("items")
    if not isinstance(data_fields, list) or not isinstance(items, list):
        return []

    rows: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, list):
            continue
        row = {}
        for idx, field in enumerate(data_fields):
            row[field] = item[idx] if idx < len(item) else None
        rows.append(row)
    return rows


def _format_trade_date(raw: Any) -> Optional[str]:
    text = _safe_str(raw)
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    if len(text) >= 10:
        return text[:10]
    return None


def _rows_to_history(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted: List[Dict[str, Any]] = []
    for row in rows:
        trade_date = _format_trade_date(row.get("trade_date"))
        close = _safe_float(row.get("close"))
        if trade_date is None or close is None:
            continue

        opened = _safe_float(row.get("open"))
        high = _safe_float(row.get("high"))
        low = _safe_float(row.get("low"))
        vol = _safe_float(row.get("vol"))

        opened = close if opened is None else opened
        high = close if high is None else high
        low = close if low is None else low

        formatted.append({
            "date": trade_date,
            "open": round(opened, 4),
            "high": round(high, 4),
            "low": round(low, 4),
            "close": round(close, 4),
            "volume": int(round(vol)) if vol is not None else 0,
        })

    formatted.sort(key=lambda x: x["date"])
    return formatted


def _get_tushare_price_history(ticker: str, period: str) -> List[dict]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"tushare_hist_{ticker}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    market, ts_code = _ticker_to_tushare_code(ticker)
    if market is None or ts_code is None:
        _set_cached(cache_key, [])
        return []

    start_date, end_date = _period_to_date_range(period)
    fields = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
    for api_name in (f"{market}_daily_adj", f"{market}_daily"):
        rows = _tushare_call(
            api_name=api_name,
            params={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
            fields=fields,
        )
        history = _rows_to_history(rows)
        if history:
            _set_cached(cache_key, history)
            return history

    _set_cached(cache_key, [])
    return []


def _get_tushare_latest_quote(ticker: str) -> Dict[str, Optional[float]]:
    cache_key = f"tushare_quote_{_normalize_ticker(ticker)}"
    cached = _get_cached_ttl(cache_key, 120)
    if cached is not None:
        return cached

    history = _get_tushare_price_history(ticker, period="1mo")
    if not history:
        quote = {"current_price": None, "change_pct": None}
        _set_cached(cache_key, quote)
        return quote

    current = _safe_float(history[-1].get("close"))
    prev = _safe_float(history[-2].get("close")) if len(history) > 1 else None
    change = None
    if current is not None and prev not in (None, 0):
        change = (current / prev - 1.0) * 100

    quote = {
        "current_price": current,
        "change_pct": round(change, 4) if change is not None else None,
    }
    _set_cached(cache_key, quote)
    return quote


def _hk_ts_to_yahoo_ticker(ts_code: str) -> str:
    norm = _normalize_ticker(ts_code)
    if not norm.endswith(".HK"):
        return norm
    raw = norm.split(".")[0]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return norm
    stripped = digits.lstrip("0") or "0"
    yahoo_code = stripped.zfill(4) if len(stripped) <= 4 else stripped.zfill(5)
    return f"{yahoo_code}.HK"


def _get_tushare_symbol_index() -> Dict[str, Any]:
    cache_key = "tushare_symbol_index"
    cached = _get_cached_ttl(cache_key, 86400)
    if cached is not None:
        return cached

    symbols: Dict[str, Dict[str, str]] = {}
    names_exact: Dict[str, Dict[str, str]] = {}
    name_items: List[Dict[str, str]] = []

    hk_rows = _tushare_call("hk_basic", {"list_status": "L"}, ["ts_code", "name", "enname", "fullname"])
    for row in hk_rows:
        ts_code = _safe_str(row.get("ts_code"))
        name = _safe_str(row.get("name"))
        enname = _safe_str(row.get("enname"))
        fullname = _safe_str(row.get("fullname"))
        names = [n for n in [name, enname, fullname] if n]
        if not ts_code:
            continue
        ticker = _hk_ts_to_yahoo_ticker(ts_code)
        display_name = enname or name or fullname or ticker
        entry = {"ticker": ticker, "name": display_name}

        ts_norm = _normalize_ticker(ts_code)
        code = ts_norm.split(".")[0]
        stripped = code.lstrip("0") or "0"
        keys = {
            ts_norm,
            ticker,
            code,
            stripped,
            stripped.zfill(4) if len(stripped) <= 4 else stripped.zfill(5),
        }
        for key in keys:
            symbols[_normalize_ticker(key)] = entry
        for n in names:
            upper_name = n.upper()
            names_exact[upper_name] = entry
            name_items.append({"name_upper": upper_name, "ticker": ticker, "name": display_name})

    us_rows = _tushare_call("us_basic", {}, ["ts_code", "name", "enname"])
    for row in us_rows:
        ts_code = _safe_str(row.get("ts_code"))
        name = _safe_str(row.get("name"))
        enname = _safe_str(row.get("enname"))
        names = [n for n in [name, enname] if n]
        if not ts_code:
            continue
        ticker = _normalize_ticker(ts_code)
        display_name = enname or name or ticker
        entry = {"ticker": ticker, "name": display_name}
        symbols[ticker] = entry
        for n in names:
            upper_name = n.upper()
            names_exact[upper_name] = entry
            name_items.append({"name_upper": upper_name, "ticker": ticker, "name": display_name})

    payload = {
        "symbols": symbols,
        "names_exact": names_exact,
        "name_items": name_items,
    }
    _set_cached(cache_key, payload)
    return payload


def _resolve_yfinance_search(query: str) -> Optional[Dict[str, str]]:
    cache_key = f"yf_search_{_normalize_ticker(query)}"
    cached = _get_cached_ttl(cache_key, 900)
    if cached is not None:
        return cached

    try:
        search = yf.Search(query=query, max_results=8)
        quotes = getattr(search, "quotes", None)
        if not isinstance(quotes, list):
            _set_cached(cache_key, None)
            return None
        for item in quotes:
            if not isinstance(item, dict):
                continue
            symbol = _safe_str(item.get("symbol"))
            if not symbol:
                continue
            symbol = _normalize_ticker(symbol)
            market, _ = _ticker_to_tushare_code(symbol)
            if market not in ("us", "hk"):
                continue
            name = _safe_str(item.get("longname")) or _safe_str(item.get("shortname")) or symbol
            result = {"ticker": symbol, "name": name}
            _set_cached(cache_key, result)
            return result
    except Exception:
        pass

    _set_cached(cache_key, None)
    return None


def resolve_search_ticker(query: str) -> Optional[Dict[str, str]]:
    q = _safe_str(query)
    if not q:
        return None

    norm = _normalize_ticker(q)
    index = _get_tushare_symbol_index()
    symbols = index.get("symbols", {})
    names_exact = index.get("names_exact", {})
    name_items = index.get("name_items", [])

    hk_match = re.fullmatch(r"(\d{1,5})(?:\.HK)?", norm)
    if hk_match:
        numeric = hk_match.group(1).lstrip("0") or "0"
        yahoo_code = numeric.zfill(4) if len(numeric) <= 4 else numeric.zfill(5)
        ticker = f"{yahoo_code}.HK"
        return {"ticker": ticker, "name": ticker}

    if norm in symbols:
        return symbols[norm]
    if norm in names_exact:
        return names_exact[norm]

    if len(norm) >= 2:
        for item in name_items:
            if norm in item.get("name_upper", ""):
                return {"ticker": item.get("ticker", ""), "name": item.get("name", "")}

    yf_match = _resolve_yfinance_search(q)
    if yf_match:
        return yf_match

    if _ticker_to_tushare_code(norm)[0] == "us":
        return {"ticker": norm, "name": norm}
    return None


def _fetch_close_price(ticker: str) -> Optional[float]:
    cache_key = f"fx_hist_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            _set_cached(cache_key, None)
            return None
        close = _to_float(hist["Close"].dropna().iloc[-1])
        _set_cached(cache_key, close)
        return close
    except Exception:
        _set_cached(cache_key, None)
        return None


def get_fx_to_usd(currency: Optional[str]) -> Optional[float]:
    cur = (currency or "USD").upper().strip()
    cache_key = f"fx_to_usd_{cur}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if cur == "USD":
        _set_cached(cache_key, 1.0)
        return 1.0

    pair = FX_TICKERS.get(cur)
    if pair:
        ticker, invert = pair
        px = _fetch_close_price(ticker)
        if px and px != 0:
            rate = (1.0 / px) if invert else px
            if rate > 0:
                _set_cached(cache_key, rate)
                return rate

    fallback = FX_FALLBACK_TO_USD.get(cur)
    if fallback:
        _set_cached(cache_key, fallback)
        return fallback

    _set_cached(cache_key, None)
    return None


def _parse_fiscal_year_end(info: Dict[str, Any]) -> Tuple[int, int]:
    raw = info.get("fiscalYearEnd")
    if isinstance(raw, (int, float)):
        iv = int(raw)
        # Yahoo commonly returns values like 930 / 1231 for fiscalYearEnd.
        if 101 <= iv <= 1231:
            month = max(1, min(12, iv // 100))
            day = max(1, min(31, iv % 100))
            return month, day
    return 12, 31


def _fiscal_period_label(period_end: pd.Timestamp, fiscal_end_month: int, fiscal_end_day: int) -> str:
    dt = period_end.date()
    max_day = calendar.monthrange(dt.year, fiscal_end_month)[1]
    fy_end_this_year = date(dt.year, fiscal_end_month, min(fiscal_end_day, max_day))
    fiscal_year = dt.year if dt <= fy_end_this_year else dt.year + 1

    fiscal_start_month = fiscal_end_month % 12 + 1
    month_offset = (dt.month - fiscal_start_month) % 12
    quarter = month_offset // 3 + 1
    return f"{fiscal_year}-Q{quarter}"


def _prepare_statement_df(df: Optional[pd.DataFrame], max_cols: int = 8) -> Tuple[Optional[pd.DataFrame], List[pd.Timestamp]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None, []

    col_map: Dict[Any, pd.Timestamp] = {}
    for col in df.columns:
        ts = pd.to_datetime(col, errors="coerce")
        if pd.isna(ts):
            continue
        col_map[col] = ts

    if not col_map:
        return None, []

    prepared = df.loc[:, list(col_map.keys())].copy()
    prepared.columns = [col_map[c] for c in col_map]
    prepared = prepared.loc[:, ~prepared.columns.duplicated()]

    latest = sorted(prepared.columns, reverse=True)[:max_cols]
    selected_cols = sorted(latest)
    return prepared, selected_cols


def _statement_value(df: pd.DataFrame, col: pd.Timestamp, candidates: List[str]) -> Optional[float]:
    for name in candidates:
        if name in df.index:
            return _safe_float(df.at[name, col])
    return None


def _extract_income_statement(df: Optional[pd.DataFrame], fiscal_end: Tuple[int, int]) -> List[dict]:
    prepared, cols = _prepare_statement_df(df)
    if prepared is None:
        return []

    rows: List[dict] = []
    for col in cols:
        rows.append({
            "period": _fiscal_period_label(col, fiscal_end[0], fiscal_end[1]),
            "period_end": col.strftime("%Y-%m-%d"),
            "total_revenue": _statement_value(prepared, col, ["Total Revenue"]),
            "gross_profit": _statement_value(prepared, col, ["Gross Profit"]),
            "operating_income": _statement_value(prepared, col, ["Operating Income"]),
            "net_income": _statement_value(prepared, col, ["Net Income"]),
            "research_and_development": _statement_value(prepared, col, ["Research And Development", "Research Development"]),
            "ebitda": _statement_value(prepared, col, ["EBITDA"]),
            "diluted_eps": _statement_value(prepared, col, ["Diluted EPS"]),
        })
    return rows


def _extract_balance_sheet(df: Optional[pd.DataFrame], fiscal_end: Tuple[int, int]) -> List[dict]:
    prepared, cols = _prepare_statement_df(df)
    if prepared is None:
        return []

    rows: List[dict] = []
    for col in cols:
        working_capital = _statement_value(prepared, col, ["Working Capital"])
        if working_capital is None:
            current_assets = _statement_value(prepared, col, ["Current Assets"])
            current_liabilities = _statement_value(prepared, col, ["Current Liabilities"])
            if current_assets is not None and current_liabilities is not None:
                working_capital = current_assets - current_liabilities

        rows.append({
            "period": _fiscal_period_label(col, fiscal_end[0], fiscal_end[1]),
            "period_end": col.strftime("%Y-%m-%d"),
            "total_assets": _statement_value(prepared, col, ["Total Assets"]),
            "total_liabilities": _statement_value(prepared, col, ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
            "stockholders_equity": _statement_value(prepared, col, ["Stockholders Equity", "Total Equity Gross Minority Interest"]),
            "total_debt": _statement_value(prepared, col, ["Total Debt", "Long Term Debt And Capital Lease Obligation"]),
            "cash": _statement_value(prepared, col, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]),
            "working_capital": working_capital,
        })
    return rows


def _extract_cash_flow(df: Optional[pd.DataFrame], fiscal_end: Tuple[int, int]) -> List[dict]:
    prepared, cols = _prepare_statement_df(df)
    if prepared is None:
        return []

    rows: List[dict] = []
    for col in cols:
        operating_cash_flow = _statement_value(prepared, col, [
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
        ])
        capital_expenditure = _statement_value(prepared, col, ["Capital Expenditure"])
        free_cash_flow = _statement_value(prepared, col, ["Free Cash Flow"])
        if free_cash_flow is None and operating_cash_flow is not None and capital_expenditure is not None:
            free_cash_flow = operating_cash_flow + capital_expenditure

        rows.append({
            "period": _fiscal_period_label(col, fiscal_end[0], fiscal_end[1]),
            "period_end": col.strftime("%Y-%m-%d"),
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditure": capital_expenditure,
            "free_cash_flow": free_cash_flow,
        })
    return rows


def get_ticker_info(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"info_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info
        default_currency, default_exchange = _market_defaults(ticker)
        currency = (info.get("currency") or default_currency or "USD").upper()
        market_cap = _safe_float(info.get("marketCap"))
        fx_to_usd = get_fx_to_usd(currency)
        market_cap_usd = market_cap * fx_to_usd if market_cap is not None and fx_to_usd else None

        result = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "current_price": _safe_float(info.get("currentPrice")) or _safe_float(info.get("regularMarketPrice")),
            "currency": currency,
            "exchange": info.get("exchange", default_exchange or ""),
            "quote_type": info.get("quoteType", "EQUITY"),
            "market_cap": market_cap,
            "market_cap_usd": market_cap_usd,
            "fx_to_usd": fx_to_usd,
            "country": info.get("country"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": (info.get("longBusinessSummary", "") or "")[:600],
            # Valuation
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            # Profitability
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "gross_margin": info.get("grossMargins"),
            "net_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            # Growth
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "eps": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            # Debt
            "debt_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            # Price info
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "week_52_change": info.get("52WeekChange") or info.get("fiftyTwoWeekChange"),
            "target_price": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "recommendation": info.get("recommendationKey"),
            "num_analyst_opinions": info.get("numberOfAnalystOpinions"),
            # Risk
            "beta": info.get("beta"),
            "institutional_ownership": info.get("institutionPercentHeld"),
            "insider_ownership": info.get("insiderPercentHeld"),
        }
        if result["current_price"] is None:
            quote = _get_tushare_latest_quote(ticker)
            result["current_price"] = quote.get("current_price")
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        quote = _get_tushare_latest_quote(ticker)
        if quote.get("current_price") is not None:
            currency, exchange = _market_defaults(ticker)
            result = {
                "ticker": ticker,
                "name": ticker,
                "current_price": quote.get("current_price"),
                "currency": currency or "USD",
                "exchange": exchange or "",
                "quote_type": "EQUITY",
                "market_cap": None,
                "market_cap_usd": None,
                "fx_to_usd": get_fx_to_usd(currency or "USD"),
                "week_52_change": None,
            }
            _set_cached(cache_key, result)
            return result
        return {"ticker": ticker, "error": str(e)}


def get_financials(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"financials_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result = {
        "ticker": ticker,
        "income_statement": [],
        "balance_sheet": [],
        "cash_flow": [],
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info if hasattr(t, "info") else {}
        fiscal_end = _parse_fiscal_year_end(info if isinstance(info, dict) else {})

        result["income_statement"] = _extract_income_statement(t.quarterly_income_stmt, fiscal_end)
        result["balance_sheet"] = _extract_balance_sheet(t.quarterly_balance_sheet, fiscal_end)
        result["cash_flow"] = _extract_cash_flow(t.quarterly_cashflow, fiscal_end)
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def _normalize_peer_list(main_ticker: str, peers: List[str], max_count: int = 5) -> List[str]:
    deduped: List[str] = []
    seen = {main_ticker}
    for peer in peers:
        norm = _normalize_ticker(peer)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(norm)
    return deduped[:max_count]


def get_db_peer_group(main_ticker: str) -> List[str]:
    ticker = _normalize_ticker(main_ticker)
    cache_key = f"peer_group_db_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    peers: List[str] = []
    try:
        from ..database import SessionLocal
        from ..models import PeerGroup

        db = SessionLocal()
        try:
            rows = (
                db.query(PeerGroup)
                .filter(PeerGroup.ticker == ticker)
                .order_by(PeerGroup.rank.asc(), PeerGroup.id.asc())
                .all()
            )
            peers = [r.peer_ticker for r in rows]
        finally:
            db.close()
    except Exception:
        peers = []

    peers = _normalize_peer_list(ticker, peers, max_count=5)
    _set_cached(cache_key, peers)
    return peers


def set_db_peer_group(main_ticker: str, peers: List[str]) -> List[str]:
    ticker = _normalize_ticker(main_ticker)
    normalized = _normalize_peer_list(ticker, peers, max_count=5)

    try:
        from ..database import SessionLocal
        from ..models import PeerGroup

        db = SessionLocal()
        try:
            db.query(PeerGroup).filter(PeerGroup.ticker == ticker).delete(synchronize_session=False)
            for rank, peer in enumerate(normalized, start=1):
                db.add(PeerGroup(ticker=ticker, peer_ticker=peer, rank=rank))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception:
        return []

    _drop_cache_prefix(f"peer_group_db_{ticker}")
    _drop_cache_prefix(f"peers_{ticker}_")
    _drop_cache_prefix(f"peer_auto_{ticker}_")
    return normalized


def _market_cap_for_peer_match(info: Dict[str, Any]) -> Optional[float]:
    return _safe_float(info.get("market_cap_usd")) or _safe_float(info.get("market_cap"))


def _auto_recommend_peers(main_ticker: str, max_count: int = 5) -> List[str]:
    cache_key = f"peer_auto_{main_ticker}_{max_count}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    main_info = get_ticker_info(main_ticker)
    main_sector = _safe_str(main_info.get("sector"))
    main_industry = _safe_str(main_info.get("industry"))
    main_cap = _market_cap_for_peer_match(main_info)

    scored: List[Tuple[Tuple[int, float, str], str]] = []
    for candidate in PEER_AUTOREC_UNIVERSE:
        if candidate == main_ticker:
            continue
        info = get_ticker_info(candidate)
        if "error" in info and not info.get("name"):
            continue

        sector = _safe_str(info.get("sector"))
        industry = _safe_str(info.get("industry"))

        if main_sector and sector and main_sector != sector:
            continue

        industry_rank = 2
        if main_industry and industry:
            if industry == main_industry:
                industry_rank = 0
            elif main_industry.lower() in industry.lower() or industry.lower() in main_industry.lower():
                industry_rank = 1

        cap = _market_cap_for_peer_match(info)
        cap_gap = 10.0
        if main_cap and cap and main_cap > 0 and cap > 0:
            cap_gap = abs(math.log10(cap / main_cap))

        scored.append(((industry_rank, cap_gap, candidate), candidate))

    scored.sort(key=lambda x: x[0])
    picks = [ticker for _, ticker in scored[:max_count]]
    _set_cached(cache_key, picks)
    return picks


def _clean_peer_tickers(main_ticker: str, tickers: Optional[str]) -> List[str]:
    if tickers:
        raw = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        raw = get_db_peer_group(main_ticker)
        if not raw:
            raw = DEFAULT_PEER_GROUP.get(main_ticker, [])
        if not raw:
            raw = _auto_recommend_peers(main_ticker, max_count=5)
    return _normalize_peer_list(main_ticker, raw, max_count=5)


def _peer_row_from_info(ticker: str, info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "name": info.get("name") or ticker,
        "market_cap": _safe_float(info.get("market_cap_usd")) or _safe_float(info.get("market_cap")),
        "pe_ratio": _safe_float(info.get("pe_ratio")),
        "pb_ratio": _safe_float(info.get("pb_ratio")),
        "roe": _safe_float(info.get("roe")),
        "net_margin": _safe_float(info.get("net_margin")),
        "revenue_growth": _safe_float(info.get("revenue_growth")),
        "dividend_yield": _safe_float(info.get("dividend_yield")),
    }


def get_peer_comparison(ticker: str, tickers: Optional[str] = None) -> Dict[str, Any]:
    main_ticker = _normalize_ticker(ticker)
    peer_list = _clean_peer_tickers(main_ticker, tickers)
    cache_suffix = ",".join(peer_list) if tickers else "default"
    cache_key = f"peers_{main_ticker}_{cache_suffix}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result = {"skipped": [], "peers": []}

    main_info = get_ticker_info(main_ticker)
    if "error" in main_info and not main_info.get("name"):
        result["error"] = main_info["error"]
        _set_cached(cache_key, result)
        return result

    result["peers"].append(_peer_row_from_info(main_ticker, main_info))

    for peer_ticker in peer_list:
        info = get_ticker_info(peer_ticker)
        if "error" in info and not info.get("name"):
            result["skipped"].append(peer_ticker)
            continue
        result["peers"].append(_peer_row_from_info(peer_ticker, info))

    _set_cached(cache_key, result)
    return result


def _get_market_cycle_proxy() -> Dict[str, Any]:
    cache_key = "cycle_proxy_market"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    proxy = {
        "phase": "Unknown",
        "signal": {
            "sp500_above_200d": None,
            "yield_curve_spread": None,
        },
    }
    try:
        spx = yf.Ticker("^GSPC").history(period="1y")
        irx = yf.Ticker("^IRX").history(period="1mo")
        tnx = yf.Ticker("^TNX").history(period="1mo")
        if not spx.empty and len(spx) >= 200:
            close = _to_float(spx["Close"].dropna().iloc[-1])
            sma200 = _to_float(spx["Close"].rolling(200).mean().dropna().iloc[-1])
            if close is not None and sma200 is not None:
                proxy["signal"]["sp500_above_200d"] = close > sma200
        if not irx.empty and not tnx.empty:
            short_yield = _to_float(irx["Close"].dropna().iloc[-1])
            long_yield = _to_float(tnx["Close"].dropna().iloc[-1])
            if short_yield is not None and long_yield is not None:
                spread = round(long_yield - short_yield, 3)
                proxy["signal"]["yield_curve_spread"] = spread
    except Exception:
        pass

    trend_up = proxy["signal"]["sp500_above_200d"]
    spread = proxy["signal"]["yield_curve_spread"]
    if trend_up is True and spread is not None and spread > 0:
        proxy["phase"] = "Mid Cycle"
    elif trend_up is True and spread is not None and spread <= 0:
        proxy["phase"] = "Late Cycle"
    elif trend_up is False and spread is not None and spread <= 0:
        proxy["phase"] = "Recession"
    elif trend_up is False and spread is not None and spread > 0:
        proxy["phase"] = "Early Cycle"

    _set_cached(cache_key, proxy)
    return proxy


def get_economic_cycle_context(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"cycle_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    info = get_ticker_info(ticker)
    sector = _safe_str(info.get("sector")) or "Unknown"
    industry = _safe_str(info.get("industry"))
    profile = SECTOR_CYCLE_PROFILE.get(sector, {})
    matrix = [
        {
            "phase": phase,
            "status": profile.get(phase, "neutral"),
        }
        for phase in ECONOMIC_PHASES
    ]

    phase_explanations = {
        "Early Cycle": "Recovery improves risk appetite and growth expectations.",
        "Mid Cycle": "Broad expansion supports earnings and cyclical demand.",
        "Late Cycle": "Tighter liquidity usually favors quality and defensives.",
        "Recession": "Capital preservation and defensive cash flows dominate.",
    }

    result = {
        "ticker": ticker,
        "sector": sector,
        "industry": industry,
        "cycle_proxy": _get_market_cycle_proxy(),
        "sector_cycle_matrix": matrix,
        "phase_explanations": phase_explanations,
    }
    _set_cached(cache_key, result)
    return result


def _extract_rating_distribution(df: Optional[pd.DataFrame]) -> Optional[Dict[str, int]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    lower_to_actual = {str(col).strip().lower(): col for col in df.columns}
    aliases = {
        "strong_buy": ["strongbuy", "strong_buy", "strong buy"],
        "buy": ["buy"],
        "hold": ["hold"],
        "sell": ["sell"],
        "strong_sell": ["strongsell", "strong_sell", "strong sell"],
    }

    row = None
    period_col = lower_to_actual.get("period")
    if period_col is not None:
        mask = df[period_col].astype(str).str.lower() == "0m"
        if mask.any():
            row = df[mask].iloc[0]
    if row is None:
        row = df.iloc[0]

    found_any = False
    distribution: Dict[str, int] = {}
    for key, keys in aliases.items():
        actual = next((lower_to_actual[k] for k in keys if k in lower_to_actual), None)
        if actual is None:
            distribution[key] = 0
            continue
        found_any = True
        distribution[key] = _safe_int(row.get(actual)) or 0

    return distribution if found_any else None


def _extract_recent_changes(df: Optional[pd.DataFrame], max_rows: int = 10) -> List[dict]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    work = df.copy()
    if isinstance(work.index, pd.DatetimeIndex):
        work = work.sort_index(ascending=False)

    rows = []
    for idx, row in work.head(max_rows).iterrows():
        ts = pd.to_datetime(idx, errors="coerce")
        price_target = _safe_float(row.get("PriceTarget"))
        if price_target is None:
            price_target = _safe_float(row.get("priorPriceTarget"))

        rows.append({
            "date": ts.strftime("%Y-%m-%d") if not pd.isna(ts) else None,
            "firm": _safe_str(row.get("Firm")),
            "from_grade": _safe_str(row.get("FromGrade")),
            "to_grade": _safe_str(row.get("ToGrade")),
            "action": _safe_str(row.get("Action")),
            "price_target": price_target,
        })
    return rows


def get_analyst_data(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"analyst_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "recommendation_mean": None,
        "recommendation_key": None,
        "num_analysts": None,
        "rating_distribution": None,
        "target_high": None,
        "target_low": None,
        "target_mean": None,
        "current_price": None,
        "upside_pct": None,
        "recent_changes": [],
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info if hasattr(t, "info") else {}
        info = info if isinstance(info, dict) else {}

        result["recommendation_mean"] = _safe_float(info.get("recommendationMean"))
        result["recommendation_key"] = _safe_str(info.get("recommendationKey"))
        result["num_analysts"] = _safe_int(info.get("numberOfAnalystOpinions"))
        result["target_high"] = _safe_float(info.get("targetHighPrice"))
        result["target_low"] = _safe_float(info.get("targetLowPrice"))
        result["target_mean"] = _safe_float(info.get("targetMeanPrice"))
        result["current_price"] = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))

        if result["target_mean"] is not None and result["current_price"] not in (None, 0):
            result["upside_pct"] = round(
                (result["target_mean"] - result["current_price"]) / result["current_price"] * 100,
                2,
            )

        try:
            result["rating_distribution"] = _extract_rating_distribution(t.recommendations)
        except Exception:
            result["rating_distribution"] = None

        try:
            result["recent_changes"] = _extract_recent_changes(t.upgrades_downgrades)
        except Exception:
            result["recent_changes"] = []
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def _extract_sustainability_value(df: pd.DataFrame, key: str) -> Any:
    if key in df.index:
        value = df.loc[key]
        if isinstance(value, pd.Series):
            if "Value" in value.index:
                return value["Value"]
            return _first_non_null(value)
        return value
    if key in df.columns:
        return _first_non_null(df[key])
    return None


def get_esg(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"esg_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "available": False,
        "total_score": None,
        "environment_score": None,
        "social_score": None,
        "governance_score": None,
        "performance": None,
    }

    try:
        t = yf.Ticker(ticker)
        df = t.sustainability
        if isinstance(df, pd.DataFrame) and not df.empty:
            result["total_score"] = _safe_float(_extract_sustainability_value(df, "totalEsg"))
            result["environment_score"] = _safe_float(_extract_sustainability_value(df, "environmentScore"))
            result["social_score"] = _safe_float(_extract_sustainability_value(df, "socialScore"))
            result["governance_score"] = _safe_float(_extract_sustainability_value(df, "governanceScore"))
            result["performance"] = _safe_str(_extract_sustainability_value(df, "esgPerformance"))
            result["available"] = any(
                value is not None
                for value in [
                    result["total_score"],
                    result["environment_score"],
                    result["social_score"],
                    result["governance_score"],
                    result["performance"],
                ]
            )
    except Exception:
        pass

    _set_cached(cache_key, result)
    return result


def get_price_history(ticker: str, period: str = "1y", interval: str = "1d") -> List[dict]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"hist_{ticker}_{period}_{interval}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    if interval == "1d":
        tushare_history = _get_tushare_price_history(ticker, period)
        if tushare_history:
            _set_cached(cache_key, tushare_history)
            return tushare_history

    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            return []

        df.index = pd.to_datetime(df.index)
        result = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            }
            for idx, row in df.iterrows()
        ]
        _set_cached(cache_key, result)
        return result
    except Exception:
        return []


def _compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_technicals(ticker: str, period: str = "1y") -> List[dict]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"tech_{ticker}_{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d")
        if df.empty or len(df) < 20:
            return []

        close = df["Close"]

        df["sma20"] = close.rolling(20).mean()
        df["sma50"] = close.rolling(50).mean()
        df["sma200"] = close.rolling(200).mean()
        df["ema12"] = close.ewm(span=12, adjust=False).mean()
        df["ema26"] = close.ewm(span=26, adjust=False).mean()
        df["macd"] = df["ema12"] - df["ema26"]
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        df["rsi"] = _compute_rsi(close, 14)
        df["bb_middle"] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std

        def safe(v):
            if pd.isna(v):
                return None
            return round(float(v), 4)

        result = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": safe(row["Close"]),
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                "sma20": safe(row["sma20"]),
                "sma50": safe(row["sma50"]),
                "sma200": safe(row["sma200"]),
                "macd": safe(row["macd"]),
                "macd_signal": safe(row["macd_signal"]),
                "macd_hist": safe(row["macd_hist"]),
                "rsi": safe(row["rsi"]),
                "bb_upper": safe(row["bb_upper"]),
                "bb_middle": safe(row["bb_middle"]),
                "bb_lower": safe(row["bb_lower"]),
            }
            for idx, row in df.iterrows()
        ]
        _set_cached(cache_key, result)
        return result
    except Exception:
        return []


def _normalize_ticker_list(tickers: List[str], max_count: int = 6) -> List[str]:
    out: List[str] = []
    seen = set()
    for ticker in tickers:
        norm = _normalize_ticker(ticker)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= max_count:
            break
    return out


def get_normalized_comparison(tickers: List[str], period: str = "1y") -> Dict[str, Any]:
    period = (period or "1y").strip().lower()
    allowed_periods = {"3mo", "6mo", "1y", "2y", "5y"}
    if period not in allowed_periods:
        period = "1y"

    normalized = _normalize_ticker_list(tickers, max_count=6)
    if len(normalized) < 2:
        return {
            "period": period,
            "tickers": normalized,
            "skipped": [],
            "data": [],
            "error": "At least 2 valid tickers are required",
        }

    cache_key = f"compare_{period}_{','.join(normalized)}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "period": period,
        "tickers": [],
        "skipped": [],
        "data": [],
    }

    try:
        series_map: Dict[str, pd.Series] = {}
        valid_tickers: List[str] = []
        for ticker in normalized:
            history = get_price_history(ticker, period=period, interval="1d")
            if not history:
                result["skipped"].append(ticker)
                continue
            series = pd.Series(
                data=[_safe_float(item.get("close")) for item in history],
                index=[item.get("date") for item in history],
                dtype="float64",
            ).dropna()
            if series.empty:
                result["skipped"].append(ticker)
                continue
            series_map[ticker] = series
            valid_tickers.append(ticker)

        if len(valid_tickers) < 2:
            result["skipped"] = sorted(list(set(result["skipped"] + normalized)))
            _set_cached(cache_key, result)
            return result

        aligned = pd.DataFrame({ticker: series_map[ticker] for ticker in valid_tickers})
        aligned.index = pd.to_datetime(aligned.index)
        aligned = aligned.sort_index().ffill().dropna(how="all")

        normalized_df = pd.DataFrame(index=aligned.index)
        for ticker in valid_tickers:
            series = aligned[ticker]
            first = _safe_float(series.dropna().iloc[0]) if not series.dropna().empty else None
            if first in (None, 0):
                normalized_df[ticker] = np.nan
            else:
                normalized_df[ticker] = (series / first) * 100

        rows: List[dict] = []
        for idx, row in normalized_df.iterrows():
            item: Dict[str, Any] = {"date": idx.strftime("%Y-%m-%d")}
            for ticker in valid_tickers:
                val = _safe_float(row.get(ticker))
                item[ticker] = round(val, 4) if val is not None else None
            rows.append(item)

        result["tickers"] = valid_tickers
        result["data"] = rows
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def get_return_analysis(ticker: str, period: str = "1y") -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    period = (period or "1y").strip().lower()
    allowed_periods = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
    if period not in allowed_periods:
        period = "1y"

    cache_key = f"returns_{ticker}_{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "period": period,
        "stats": {
            "mean": None,
            "std": None,
            "var": None,
            "annual_return": None,
            "annual_volatility": None,
            "skewness": None,
            "kurtosis": None,
        },
        "histogram": [],
        "daily_returns": [],
    }

    try:
        history = get_price_history(ticker, period=period, interval="1d")
        if not history:
            result["error"] = "No historical close data"
            _set_cached(cache_key, result)
            return result

        close = pd.Series(
            data=[_safe_float(item.get("close")) for item in history],
            index=pd.to_datetime([item.get("date") for item in history]),
            dtype="float64",
        ).dropna()
        if len(close) < 3:
            result["error"] = "Not enough data points"
            _set_cached(cache_key, result)
            return result

        simple_returns = close.pct_change().dropna()
        log_returns = np.log(close / close.shift(1)).dropna()

        mean = _safe_float(log_returns.mean())
        std = _safe_float(log_returns.std())
        var = _safe_float(log_returns.var())
        annual_return = (math.exp(mean * 252) - 1) if mean is not None else None
        annual_vol = (std * math.sqrt(252)) if std is not None else None
        skewness = _safe_float(log_returns.skew())
        kurtosis = _safe_float(log_returns.kurt())

        result["stats"] = {
            "mean": round(mean, 6) if mean is not None else None,
            "std": round(std, 6) if std is not None else None,
            "var": round(var, 6) if var is not None else None,
            "annual_return": round(annual_return, 6) if annual_return is not None else None,
            "annual_volatility": round(annual_vol, 6) if annual_vol is not None else None,
            "skewness": round(skewness, 6) if skewness is not None else None,
            "kurtosis": round(kurtosis, 6) if kurtosis is not None else None,
        }

        counts, edges = np.histogram(log_returns.values, bins=35)
        histogram = []
        for i in range(len(counts)):
            histogram.append({
                "bin_start": round(float(edges[i]), 6),
                "bin_end": round(float(edges[i + 1]), 6),
                "count": int(counts[i]),
            })
        result["histogram"] = histogram

        joined = pd.DataFrame({"simple": simple_returns, "log": log_returns}).dropna(how="all")
        daily_rows = []
        for idx, row in joined.iterrows():
            simple = _safe_float(row.get("simple"))
            logv = _safe_float(row.get("log"))
            daily_rows.append({
                "date": pd.to_datetime(idx).strftime("%Y-%m-%d"),
                "simple": round(simple, 6) if simple is not None else None,
                "log": round(logv, 6) if logv is not None else None,
            })
        result["daily_returns"] = daily_rows
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def get_ath_analysis(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"ath_{ticker}"
    cached = _get_cached_ttl(cache_key, 3600)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "all_time_high": None,
        "ath_date": None,
        "all_time_low": None,
        "atl_date": None,
        "current_price": None,
        "down_from_ath_pct": None,
        "up_from_atl_pct": None,
        "range_position": None,
    }

    def _load() -> Dict[str, Any]:
        history = yf.Ticker(ticker).history(period="max")
        if not isinstance(history, pd.DataFrame) or history.empty or "Close" not in history.columns:
            return {}

        close = history["Close"].dropna()
        if close.empty:
            return {}

        ath = _safe_float(close.max())
        atl = _safe_float(close.min())
        current = _safe_float(close.iloc[-1])
        if ath is None or atl is None or current is None:
            return {}

        ath_idx = close.idxmax()
        atl_idx = close.idxmin()

        down_pct = ((ath - current) / ath * 100.0) if ath not in (None, 0) else None
        up_pct = ((current - atl) / atl * 100.0) if atl not in (None, 0) else None
        span = ath - atl
        range_position = ((current - atl) / span * 100.0) if span != 0 else None

        return {
            "all_time_high": round(ath, 4),
            "ath_date": _format_date_label(ath_idx),
            "all_time_low": round(atl, 4),
            "atl_date": _format_date_label(atl_idx),
            "current_price": round(current, 4),
            "down_from_ath_pct": round(down_pct, 4) if down_pct is not None else None,
            "up_from_atl_pct": round(up_pct, 4) if up_pct is not None else None,
            "range_position": round(range_position, 4) if range_position is not None else None,
        }

    try:
        payload = _run_with_timeout(_load, timeout_seconds=10)
        if not payload:
            result["error"] = "No historical close data"
            _set_cached(cache_key, result)
            return result
        result.update(payload)
    except TimeoutError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def _extract_annual_eps(df: Optional[pd.DataFrame]) -> List[Tuple[str, float]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    preferred_rows = [
        "Diluted EPS",
        "Basic EPS",
        "EPS Diluted",
    ]
    row = None
    for name in preferred_rows:
        if name in df.index:
            row = df.loc[name]
            break

    if row is None:
        lower_to_actual = {str(idx).strip().lower(): idx for idx in df.index}
        fuzzy = next(
            (lower_to_actual[key] for key in lower_to_actual if "diluted eps" in key or key == "basic eps"),
            None,
        )
        if fuzzy is not None:
            row = df.loc[fuzzy]

    if row is None:
        return []

    # Parse date-like columns to annual EPS values and deduplicate per year.
    annual: Dict[str, float] = {}
    for col, value in row.items():
        eps = _safe_float(value)
        if eps is None:
            continue
        ts = pd.to_datetime(col, errors="coerce")
        if pd.isna(ts):
            continue
        annual[str(ts.year)] = eps

    return sorted(annual.items(), key=lambda x: x[0])


def get_eps_trend(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"eps_trend_{ticker}"
    cached = _get_cached_ttl(cache_key, 86400)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "eps_history": [],
        "earliest_year": None,
        "latest_year": None,
    }

    def _load() -> List[Tuple[str, float]]:
        t = yf.Ticker(ticker)
        for frame in (
            getattr(t, "income_stmt", None),
            getattr(t, "financials", None),
        ):
            annual = _extract_annual_eps(frame)
            if annual:
                return annual
        return []

    try:
        annual_eps = _run_with_timeout(_load, timeout_seconds=10)
        if not annual_eps:
            result["error"] = "No annual EPS data"
            _set_cached(cache_key, result)
            return result

        rows = []
        for idx, (year, eps) in enumerate(annual_eps):
            prev = annual_eps[idx - 1][1] if idx > 0 else None
            yoy_change = None
            if prev not in (None, 0):
                yoy_change = (eps - prev) / abs(prev)
            rows.append({
                "year": year,
                "eps": round(eps, 4),
                "yoy_change": round(yoy_change, 4) if yoy_change is not None else None,
            })

        result["eps_history"] = rows
        result["earliest_year"] = rows[0]["year"]
        result["latest_year"] = rows[-1]["year"]
    except TimeoutError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def get_earnings_estimates(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"earnings_est_{ticker}"
    cached = _get_cached_ttl(cache_key, 3600)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "earnings_estimates": [],
        "revenue_estimates": [],
    }

    def _load() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        t = yf.Ticker(ticker)
        earnings_df = getattr(t, "earnings_estimate", None)
        revenue_df = getattr(t, "revenue_estimate", None)
        earnings_rows = _parse_estimate_frame(earnings_df, include_prior=True)
        revenue_rows = _parse_estimate_frame(revenue_df, include_prior=False)
        return earnings_rows, revenue_rows

    try:
        earnings_rows, revenue_rows = _run_with_timeout(_load, timeout_seconds=10)
        result["earnings_estimates"] = earnings_rows
        result["revenue_estimates"] = revenue_rows
        if not earnings_rows and not revenue_rows:
            result["error"] = "No earnings estimate data"
    except TimeoutError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def get_fred_series(series_id: str = "DFF", period: str = "5y") -> Dict[str, Any]:
    sid = _normalize_ticker(series_id) if series_id else "DFF"
    p = (period or "5y").strip().lower()
    cache_key = f"fred_{sid}_{p}"
    cached = _get_cached_ttl(cache_key, 3600)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "series_id": sid,
        "period": p,
        "title": sid,
        "available": False,
        "data": [],
        "message": "FRED API key not configured",
    }

    api_key = _pick_any_env_value([
        "datasource.fred.key",
        "fred.api_key",
        "FRED_API_KEY",
    ])
    if not api_key:
        _set_cached(cache_key, result)
        return result

    start_date = _period_to_observation_start(p)
    params = {
        "series_id": sid,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc",
    }
    obs_url = f"https://api.stlouisfed.org/fred/series/observations?{urlencode(params)}"
    meta_url = f"https://api.stlouisfed.org/fred/series?{urlencode({'series_id': sid, 'api_key': api_key, 'file_type': 'json'})}"

    def _load() -> Tuple[str, List[Dict[str, Any]]]:
        title = sid
        with urlopen(meta_url, timeout=10) as response:
            meta_payload = json.loads(response.read().decode("utf-8"))
        series_list = meta_payload.get("seriess")
        if isinstance(series_list, list) and series_list:
            title = _safe_str(series_list[0].get("title")) or sid

        with urlopen(obs_url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        rows: List[Dict[str, Any]] = []
        observations = payload.get("observations")
        if isinstance(observations, list):
            for item in observations:
                if not isinstance(item, dict):
                    continue
                date_value = _safe_str(item.get("date"))
                value_raw = _safe_str(item.get("value"))
                if not date_value or value_raw in (None, "."):
                    continue
                value = _safe_float(value_raw)
                if value is None:
                    continue
                rows.append({
                    "date": date_value,
                    "value": round(value, 4),
                })

        rows = _downsample_time_series(rows, max_points=520)
        return title, rows

    try:
        title, rows = _run_with_timeout(_load, timeout_seconds=10)
        result["title"] = title
        result["data"] = rows
        if rows:
            result["available"] = True
            result["message"] = None
        else:
            result["message"] = "No FRED data available"
    except TimeoutError as e:
        result["message"] = str(e)
    except URLError:
        result["message"] = "Failed to fetch FRED data"
    except Exception as e:
        result["message"] = f"FRED request failed: {e}"

    _set_cached(cache_key, result)
    return result


def get_google_trends(keywords: List[str], timeframe: str = "today 12-m") -> Dict[str, Any]:
    cleaned_keywords = [_safe_str(k) for k in (keywords or [])]
    cleaned_keywords = [k for k in cleaned_keywords if k]
    if len(cleaned_keywords) > 5:
        cleaned_keywords = cleaned_keywords[:5]

    result: Dict[str, Any] = {
        "keywords": cleaned_keywords,
        "timeframe": timeframe,
        "available": False,
        "data": [],
        "message": None,
    }

    if not cleaned_keywords:
        result["message"] = "At least one keyword is required"
        return result

    cache_key = f"gtrends_{timeframe}_{'|'.join(cleaned_keywords)}"
    cached = _get_cached_ttl(cache_key, 3600)
    if cached is not None:
        return cached

    if TrendReq is None:
        result["message"] = "Google Trends client not installed"
        _set_cached(cache_key, result)
        return result

    def _load() -> List[Dict[str, Any]]:
        trends = TrendReq(hl="en-US", tz=0)
        trends.build_payload(cleaned_keywords, timeframe=timeframe)
        df = trends.interest_over_time()
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        work = df.copy()
        if "isPartial" in work.columns:
            work = work.drop(columns=["isPartial"])

        rows: List[Dict[str, Any]] = []
        for idx, row in work.iterrows():
            item: Dict[str, Any] = {"date": _format_date_label(idx)}
            for keyword in cleaned_keywords:
                val = _safe_int(row.get(keyword))
                item[keyword] = val if val is not None else 0
            if item["date"]:
                rows.append(item)
        return rows

    try:
        rows = _run_with_timeout(_load, timeout_seconds=10)
        result["data"] = rows
        if rows:
            result["available"] = True
        else:
            result["message"] = "No Google Trends data available"
    except TimeoutError as e:
        result["message"] = str(e)
    except Exception:
        result["message"] = "Google Trends temporarily unavailable"

    _set_cached(cache_key, result)
    return result


def get_ratio_trends(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"ratio_trends_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "periods": [],
        "ratios": {
            "debt_to_equity": [],
            "current_ratio": [],
            "roe": [],
            "profit_margin": [],
            "roa": [],
            "asset_turnover": [],
        },
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info if hasattr(t, "info") and isinstance(t.info, dict) else {}
        fiscal_end = _parse_fiscal_year_end(info)

        income_df, income_cols = _prepare_statement_df(t.quarterly_income_stmt)
        balance_df, balance_cols = _prepare_statement_df(t.quarterly_balance_sheet)
        all_cols = sorted(set(income_cols + balance_cols), reverse=True)[:8]
        cols = sorted(all_cols)

        if not cols:
            _set_cached(cache_key, result)
            return result

        for col in cols:
            result["periods"].append(_fiscal_period_label(col, fiscal_end[0], fiscal_end[1]))

            net_income = _statement_value(income_df, col, ["Net Income"]) if income_df is not None and col in income_df.columns else None
            total_revenue = _statement_value(income_df, col, ["Total Revenue"]) if income_df is not None and col in income_df.columns else None

            stockholders_equity = _statement_value(
                balance_df,
                col,
                ["Stockholders Equity", "Total Equity Gross Minority Interest"],
            ) if balance_df is not None and col in balance_df.columns else None
            total_debt = _statement_value(
                balance_df,
                col,
                ["Total Debt", "Long Term Debt And Capital Lease Obligation"],
            ) if balance_df is not None and col in balance_df.columns else None
            total_assets = _statement_value(balance_df, col, ["Total Assets"]) if balance_df is not None and col in balance_df.columns else None
            current_assets = _statement_value(balance_df, col, ["Current Assets", "Total Current Assets"]) if balance_df is not None and col in balance_df.columns else None
            current_liabilities = _statement_value(balance_df, col, ["Current Liabilities", "Total Current Liabilities"]) if balance_df is not None and col in balance_df.columns else None

            ratios = {
                "debt_to_equity": _safe_div(total_debt, stockholders_equity),
                "current_ratio": _safe_div(current_assets, current_liabilities),
                "roe": _safe_div(net_income, stockholders_equity),
                "profit_margin": _safe_div(net_income, total_revenue),
                "roa": _safe_div(net_income, total_assets),
                "asset_turnover": _safe_div(total_revenue, total_assets),
            }

            for key, value in ratios.items():
                result["ratios"][key].append(round(value, 4) if value is not None else None)
    except Exception as e:
        result["error"] = str(e)

    _set_cached(cache_key, result)
    return result


def invalidate_screener_cache():
    _cache.pop("screener_snapshot", None)
    _cache.pop("screen_options", None)


def get_screener_snapshot(tickers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    universe = tickers if tickers is not None else SCREENER_UNIVERSE
    cache_key = "screener_snapshot"
    cached = _get_cached_ttl(cache_key, 1800)  # 30 minutes
    if cached is not None:
        return cached

    snapshot: List[Dict[str, Any]] = []
    for ticker in universe:
        info = get_ticker_info(ticker)
        if "error" in info and not info.get("name"):
            continue
        snapshot.append({
            "ticker": ticker,
            "name": info.get("name") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "market_cap": _safe_float(info.get("market_cap_usd")) or _safe_float(info.get("market_cap")),
            "pe_ratio": _safe_float(info.get("pe_ratio")),
            "dividend_yield": _safe_float(info.get("dividend_yield")),
            "price": _safe_float(info.get("current_price")),
            "change_52w": _safe_float(info.get("week_52_change")),
        })

    _set_cached(cache_key, snapshot)
    return snapshot


def get_screen_options(tickers: Optional[List[str]] = None) -> Dict[str, List[str]]:
    cache_key = "screen_options"
    cached = _get_cached_ttl(cache_key, 1800)
    if cached is not None:
        return cached
    snapshot = get_screener_snapshot(tickers)
    sectors = sorted({r["sector"] for r in snapshot if r.get("sector")})
    industries = sorted({r["industry"] for r in snapshot if r.get("industry")})
    countries = sorted({r["country"] for r in snapshot if r.get("country")})
    result = {"sectors": sectors, "industries": industries, "countries": countries}
    _set_cached(cache_key, result)
    return result


def screen_stocks(filters: Dict[str, Any], tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    snapshot = get_screener_snapshot(tickers)
    filtered = []

    def _parse_multi(val) -> Optional[set]:
        if not val:
            return None
        parts = {s.strip().lower() for s in str(val).split(",") if s.strip()}
        return parts if parts else None

    sectors = _parse_multi(filters.get("sector"))
    industries = _parse_multi(filters.get("industry"))
    countries = _parse_multi(filters.get("country"))
    market_cap_min = _safe_float(filters.get("market_cap_min"))
    market_cap_max = _safe_float(filters.get("market_cap_max"))
    pe_min = _safe_float(filters.get("pe_min"))
    pe_max = _safe_float(filters.get("pe_max"))
    dividend_yield_min = _safe_float(filters.get("dividend_yield_min"))
    change_52w_min = _safe_float(filters.get("change_52w_min"))

    for row in snapshot:
        if sectors and (_safe_str(row.get("sector")) or "").lower() not in sectors:
            continue
        if industries and (_safe_str(row.get("industry")) or "").lower() not in industries:
            continue
        if countries and (_safe_str(row.get("country")) or "").lower() not in countries:
            continue

        market_cap = _safe_float(row.get("market_cap"))
        pe = _safe_float(row.get("pe_ratio"))
        dividend = _safe_float(row.get("dividend_yield"))
        change_52w = _safe_float(row.get("change_52w"))

        if market_cap_min is not None and (market_cap is None or market_cap < market_cap_min):
            continue
        if market_cap_max is not None and (market_cap is None or market_cap > market_cap_max):
            continue
        if pe_min is not None and (pe is None or pe < pe_min):
            continue
        if pe_max is not None and (pe is None or pe > pe_max):
            continue
        if dividend_yield_min is not None and (dividend is None or dividend < dividend_yield_min):
            continue
        if change_52w_min is not None and (change_52w is None or change_52w < change_52w_min):
            continue

        filtered.append(row)

    filtered.sort(key=lambda x: _safe_float(x.get("market_cap")) or 0, reverse=True)
    filters_applied = {k: v for k, v in filters.items() if v not in (None, "", [])}
    return {
        "total": len(filtered),
        "filters_applied": filters_applied,
        "results": filtered,
    }


def _sentiment_label_from_score(score: float) -> str:
    if score < -0.35:
        return "Bearish"
    if score < -0.15:
        return "Somewhat-Bearish"
    if score <= 0.15:
        return "Neutral"
    if score <= 0.35:
        return "Somewhat-Bullish"
    return "Bullish"


def _parse_alpha_published(raw: Any) -> Optional[str]:
    text = _safe_str(raw)
    if not text:
        return None
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return text


def get_news_sentiment(ticker: str) -> Dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    cache_key = f"sentiment_{ticker}"
    cached = _get_cached_ttl(cache_key, 900)  # 15 minutes
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "ticker": ticker,
        "available": False,
        "message": "Alpha Vantage API key not configured",
    }

    api_key = _pick_env_value("datasource.alphavantage.secret")
    if not api_key:
        _set_cached(cache_key, result)
        return result

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "apikey": api_key,
    }
    url = f"https://www.alphavantage.co/query?{urlencode(params)}"

    try:
        with urlopen(url, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))

        feed = payload.get("feed")
        if not isinstance(feed, list):
            message = _safe_str(payload.get("Note")) or "No sentiment data available"
            result["message"] = message
            _set_cached(cache_key, result)
            return result

        articles = []
        scores: List[float] = []
        for item in feed:
            if not isinstance(item, dict):
                continue
            ticker_sentiments = item.get("ticker_sentiment")
            if not isinstance(ticker_sentiments, list):
                continue
            matched = None
            for ts in ticker_sentiments:
                if not isinstance(ts, dict):
                    continue
                if _normalize_ticker(ts.get("ticker")) == ticker:
                    matched = ts
                    break
            if matched is None:
                continue

            score = _safe_float(matched.get("ticker_sentiment_score"))
            if score is not None:
                scores.append(score)

            sentiment_label = _safe_str(matched.get("ticker_sentiment_label"))
            if not sentiment_label and score is not None:
                sentiment_label = _sentiment_label_from_score(score)

            articles.append({
                "title": _safe_str(item.get("title")),
                "url": _safe_str(item.get("url")),
                "source": _safe_str(item.get("source")),
                "published": _parse_alpha_published(item.get("time_published")),
                "sentiment_score": round(score, 4) if score is not None else None,
                "sentiment_label": sentiment_label,
                "relevance_score": _safe_float(matched.get("relevance_score")),
            })

        if not articles:
            result["message"] = "No ticker-specific sentiment articles found"
            _set_cached(cache_key, result)
            return result

        sentiment_order = ["Bullish", "Somewhat-Bullish", "Neutral", "Somewhat-Bearish", "Bearish"]
        sentiment_counts = Counter(
            _safe_str(article.get("sentiment_label"))
            for article in articles
            if _safe_str(article.get("sentiment_label")) in sentiment_order
        )
        distribution = {label: int(sentiment_counts.get(label, 0)) for label in sentiment_order}
        total_articles = len(articles)

        articles = sorted(articles, key=lambda x: x.get("published") or "", reverse=True)[:20]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        result = {
            "ticker": ticker,
            "available": True,
            "overall_sentiment": _sentiment_label_from_score(overall_score),
            "overall_score": round(overall_score, 4),
            "distribution": distribution,
            "total_articles": total_articles,
            "articles": articles,
        }
    except URLError:
        result["message"] = "Failed to fetch sentiment data from Alpha Vantage"
    except Exception as e:
        result["message"] = f"Sentiment request failed: {e}"

    _set_cached(cache_key, result)
    return result


def get_multiple_prices(tickers: List[str]) -> Dict[str, float]:
    quotes = get_multiple_quotes(tickers)
    return {
        ticker: float(quote["current_price"])
        for ticker, quote in quotes.items()
        if quote.get("current_price") is not None
    }


def get_multiple_quotes(tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    if not tickers:
        return {}

    unique: List[str] = []
    seen = set()
    for raw in tickers:
        ticker = _normalize_ticker(raw)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        unique.append(ticker)

    quotes: Dict[str, Dict[str, Optional[float]]] = {t: {"current_price": None, "change_pct": None} for t in unique}

    # Primary source for US/HK: Tushare
    for ticker in unique:
        market, _ = _ticker_to_tushare_code(ticker)
        if market not in ("us", "hk"):
            continue
        quote = _get_tushare_latest_quote(ticker)
        if quote.get("current_price") is not None:
            quotes[ticker] = quote

    missing = [t for t in unique if quotes[t]["current_price"] is None]
    if not missing:
        return quotes

    # Fallback source: yfinance batch
    try:
        data = yf.download(missing, period="5d", progress=False, auto_adjust=True)
        close = data.get("Close", data)
        if isinstance(close, pd.Series) and len(missing) == 1:
            close = close.to_frame(name=missing[0])

        if isinstance(close, pd.DataFrame):
            for ticker in missing:
                if ticker not in close.columns:
                    continue
                series = close[ticker].dropna()
                if series.empty:
                    continue
                current = _safe_float(series.iloc[-1])
                prev = _safe_float(series.iloc[-2]) if len(series) > 1 else None
                change = None
                if current is not None and prev not in (None, 0):
                    change = (current / prev - 1.0) * 100
                quotes[ticker] = {
                    "current_price": current,
                    "change_pct": round(change, 4) if change is not None else None,
                }
    except Exception:
        pass

    # Fallback for any still-missing tickers: yfinance single requests
    for ticker in missing:
        if quotes[ticker]["current_price"] is not None:
            continue
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist.empty or "Close" not in hist:
                continue
            series = hist["Close"].dropna()
            if series.empty:
                continue
            current = _safe_float(series.iloc[-1])
            prev = _safe_float(series.iloc[-2]) if len(series) > 1 else None
            change = None
            if current is not None and prev not in (None, 0):
                change = (current / prev - 1.0) * 100
            quotes[ticker] = {
                "current_price": current,
                "change_pct": round(change, 4) if change is not None else None,
            }
        except Exception:
            continue

    return quotes


def get_portfolio_returns(tickers: List[str], period: str = "1y") -> Optional[pd.DataFrame]:
    if not tickers:
        return None
    price_data = {}
    for ticker in tickers:
        history = get_price_history(ticker, period=period)
        if history:
            s = pd.Series(
                {d["date"]: d["close"] for d in history},
                dtype=float,
            )
            price_data[ticker] = s
    if not price_data:
        return None
    prices = pd.DataFrame(price_data)
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index().dropna(how="all")
    returns = prices.pct_change().dropna(how="all")
    return returns
