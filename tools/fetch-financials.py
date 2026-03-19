#!/usr/bin/env python3
"""Financial metrics peer comparison for a given ticker.

Usage:
    python tools/fetch-financials.py TICKER [--metrics pe,ps,pb,roe,debt-equity] [--peers INTC,AMD,AVGO] [--output research/companies/] [--verbose]
"""

import argparse
import os
import sys
import time
from datetime import datetime

import pandas as pd
import yfinance as yf

# Metric name → yfinance .info key
METRIC_MAP = {
    "pe": ("trailingPE", "P/E (TTM)"),
    "fwd-pe": ("forwardPE", "P/E (Fwd)"),
    "ps": ("priceToSalesTrailing12Months", "P/S (TTM)"),
    "pb": ("priceToBook", "P/B"),
    "roe": ("returnOnEquity", "ROE"),
    "debt-equity": ("debtToEquity", "Debt/Equity"),
    "dividend-yield": ("dividendYield", "Div Yield"),
    "market-cap": ("marketCap", "Market Cap"),
    "revenue-growth": ("revenueGrowth", "Rev Growth"),
    "profit-margin": ("profitMargins", "Profit Margin"),
}

DEFAULT_METRICS = "pe,ps,pb,roe,debt-equity"


def fetch_info(ticker, verbose=False):
    """Fetch .info dict for a ticker, return empty dict on error."""
    try:
        info = yf.Ticker(ticker).info
        if verbose:
            print(f"  Fetched info for {ticker}")
        return info
    except Exception as e:
        if verbose:
            print(f"  Error fetching {ticker}: {e}")
        return {}


def format_value(key, value):
    """Format a metric value for display."""
    if value is None:
        return "N/A"
    if key in ("roe", "dividend-yield", "revenue-growth", "profit-margin"):
        return f"{value:.2%}" if isinstance(value, (int, float)) else str(value)
    if key == "market-cap":
        if value >= 1e12:
            return f"${value / 1e12:.2f}T"
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        return f"${value / 1e6:.0f}M"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def main():
    parser = argparse.ArgumentParser(description="Financial metrics peer comparison")
    parser.add_argument("ticker", type=str, help="Target stock ticker")
    parser.add_argument("--metrics", default=DEFAULT_METRICS, help=f"Comma-separated metrics (default: {DEFAULT_METRICS})")
    parser.add_argument("--peers", default="", help="Comma-separated peer tickers")
    parser.add_argument("--output", default="research/companies/", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    peers = [p.strip().upper() for p in args.peers.split(",") if p.strip()] if args.peers else []
    all_tickers = [ticker] + peers
    date_str = datetime.now().strftime("%Y%m%d")

    os.makedirs(args.output, exist_ok=True)
    os.makedirs("data/snapshots", exist_ok=True)

    # Validate metrics
    invalid = [m for m in metrics if m not in METRIC_MAP]
    if invalid:
        print(f"Error: Unknown metrics: {', '.join(invalid)}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(METRIC_MAP.keys()))}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Fetching financials for {', '.join(all_tickers)}...")
        print(f"Metrics: {', '.join(metrics)}")

    # Fetch data with rate limiting for many peers
    infos = {}
    for i, t in enumerate(all_tickers):
        infos[t] = fetch_info(t, args.verbose)
        if len(all_tickers) > 5 and i < len(all_tickers) - 1:
            time.sleep(0.5)

    # Build comparison table
    rows = []
    for m in metrics:
        info_key, display_name = METRIC_MAP[m]
        row = {"Metric": display_name}
        for t in all_tickers:
            raw = infos[t].get(info_key)
            row[t] = format_value(m, raw)
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.set_index("Metric")

    # Save CSV snapshot
    csv_path = f"data/snapshots/{ticker}_financials_{date_str}.csv"
    df.to_csv(csv_path)

    # Markdown output
    md_lines = [
        f"# {ticker} — Financial Metrics Comparison ({date_str})",
        "",
    ]
    if peers:
        md_lines.append(f"Peers: {', '.join(peers)}")
        md_lines.append("")

    # Build markdown table
    header = "| Metric | " + " | ".join(all_tickers) + " |"
    separator = "|--------|" + "|".join(["--------"] * len(all_tickers)) + "|"
    md_lines.append(header)
    md_lines.append(separator)
    for _, row in df.iterrows():
        cells = " | ".join(str(row[t]) for t in all_tickers)
        md_lines.append(f"| {row.name} | {cells} |")

    md_lines.extend([
        "",
        "## Files",
        f"- CSV snapshot: `{csv_path}`",
        "",
        "---",
        "*Data source: Yahoo Finance. Values may have slight delays. N/A indicates data unavailable.*",
    ])

    md_content = "\n".join(md_lines) + "\n"
    md_path = os.path.join(args.output, f"{ticker}_financials_{date_str}.md")
    with open(md_path, "w") as f:
        f.write(md_content)

    # Print to stdout
    print(md_content)

    if args.verbose:
        print(f"\nFiles written:")
        print(f"  {md_path}")
        print(f"  {csv_path}")


if __name__ == "__main__":
    main()
