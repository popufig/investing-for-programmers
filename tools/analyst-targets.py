#!/usr/bin/env python3
"""Analyst price target visualization for a given ticker.

Usage:
    python tools/analyst-targets.py TICKER [--output research/companies/] [--verbose]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf


def calculate_diff(current, target):
    """Calculate percentage difference with sign prefix."""
    result = round((target - current) / current * 100, 2)
    prefix = "" if result < 0 else "+"
    return f"{prefix}{result}%"


def main():
    parser = argparse.ArgumentParser(description="Analyst price target visualization")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol")
    parser.add_argument("--output", default="research/companies/", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    date_str = datetime.now().strftime("%Y%m%d")
    os.makedirs(args.output, exist_ok=True)
    os.makedirs("data/snapshots", exist_ok=True)

    if args.verbose:
        print(f"Fetching data for {ticker}...")

    stock = yf.Ticker(ticker)

    # Get analyst targets
    try:
        targets = stock.get_analyst_price_targets()
    except Exception as e:
        print(f"Error fetching analyst targets for {ticker}: {e}", file=sys.stderr)
        sys.exit(1)

    if not targets or all(v is None for v in targets.values()):
        print(f"Error: No analyst price targets available for {ticker}", file=sys.stderr)
        sys.exit(1)

    current = targets.get("current")
    high = targets.get("high")
    low = targets.get("low")
    mean = targets.get("mean")
    median = targets.get("median")

    if current is None or mean is None:
        print(f"Error: Incomplete analyst target data for {ticker}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"  Current: {current}")
        print(f"  High: {high}, Mean: {mean}, Median: {median}, Low: {low}")

    # Get historical prices
    hist = stock.history(period="1y")["Close"]
    if hist.empty:
        print(f"Error: No historical price data for {ticker}", file=sys.stderr)
        sys.exit(1)

    # Save snapshot
    snapshot_path = f"data/snapshots/{ticker}_targets_{date_str}.json"
    with open(snapshot_path, "w") as f:
        json.dump(targets, f, indent=2, default=str)

    if args.verbose:
        print(f"  Snapshot saved to {snapshot_path}")

    # Round for display
    high_r = int(round(high, 0)) if high else None
    mean_r = int(round(mean, 0)) if mean else None
    low_r = int(round(low, 0)) if low else None

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(hist.index, hist.values, label="Closing Price", linewidth=2)
    ax.set_title(f"{ticker} — One Year Price Forecast")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")

    # Projection lines from last date to +1 year
    last_date = hist.index[-1]
    future_date = last_date + timedelta(days=365)
    x_proj = [last_date, future_date]

    if high is not None:
        ax.plot(x_proj, [current, high], linestyle=":", linewidth=2, color="green")
        ax.plot(future_date, high, marker="s", color="green",
                label=f"High {calculate_diff(current, high)}")
        ax.annotate(str(high_r), (future_date, high), fontsize=9)

    if mean is not None:
        ax.plot(x_proj, [current, mean], linestyle=":", linewidth=2, color="orange")
        ax.plot(future_date, mean, marker="o", color="orange",
                label=f"Mean {calculate_diff(current, mean)}")
        ax.annotate(str(mean_r), (future_date, mean), fontsize=9)

    if low is not None:
        ax.plot(x_proj, [current, low], linestyle=":", linewidth=2, color="red")
        ax.plot(future_date, low, marker="D", color="red",
                label=f"Low {calculate_diff(current, low)}")
        ax.annotate(str(low_r), (future_date, low), fontsize=9)

    ax.legend()
    ax.grid(True)
    fig.tight_layout()

    png_path = os.path.join(args.output, f"{ticker}_targets_{date_str}.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    # Markdown output
    md_lines = [
        f"# {ticker} — Analyst Price Targets ({date_str})",
        "",
        "| Metric | Value | vs Current |",
        "|--------|-------|------------|",
        f"| Current | {current} | — |",
    ]
    if high is not None:
        md_lines.append(f"| High | {high} | {calculate_diff(current, high)} |")
    if mean is not None:
        md_lines.append(f"| Mean | {mean} | {calculate_diff(current, mean)} |")
    if median is not None:
        md_lines.append(f"| Median | {median} | {calculate_diff(current, median)} |")
    if low is not None:
        md_lines.append(f"| Low | {low} | {calculate_diff(current, low)} |")

    md_lines.extend([
        "",
        "## Files",
        f"- Chart: `{png_path}`",
        f"- Snapshot: `{snapshot_path}`",
        "",
        "---",
        f"*Data source: Yahoo Finance. Analyst targets reflect consensus estimates and may not be current.*",
    ])

    md_content = "\n".join(md_lines) + "\n"
    md_path = os.path.join(args.output, f"{ticker}_targets_{date_str}.md")
    with open(md_path, "w") as f:
        f.write(md_content)

    # Print to stdout
    print(md_content)

    if args.verbose:
        print(f"\nFiles written:")
        print(f"  {png_path}")
        print(f"  {md_path}")
        print(f"  {snapshot_path}")


if __name__ == "__main__":
    main()
