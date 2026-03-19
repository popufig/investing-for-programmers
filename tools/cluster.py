#!/usr/bin/env python3
"""S&P 500 K-means clustering analysis (annualized returns × volatility).

Usage:
    python tools/cluster.py [--period 1y] [--clusters auto|N] [--output research/screening/] [--verbose]
"""

import argparse
import io
import os
import sys
import urllib.request
from datetime import datetime
from math import sqrt

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


def get_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia, clean symbols."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "InvestingTools/1.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read()
    table = pd.read_html(io.BytesIO(html))[0]
    tickers = table["Symbol"].values.tolist()
    tickers = [s.replace("\n", "").replace(" ", "").replace(".", "-") for s in tickers]
    return tickers


def download_prices(tickers, period):
    """Batch download closing prices via yfinance."""
    import yfinance as yf

    data = yf.download(tickers, period=period, progress=False)
    # yfinance may return MultiIndex columns; extract Close
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]
    return prices


def compute_features(prices):
    """Compute annualized return and volatility for each ticker."""
    daily_returns = prices.pct_change()
    ann_return = daily_returns.mean() * 252
    ann_volatility = daily_returns.std() * sqrt(252)

    features = pd.DataFrame({"Returns": ann_return, "Volatility": ann_volatility})
    features = features.dropna()
    # Remove tickers with zero volatility (no trading data)
    features = features[features["Volatility"] > 0]
    return features


def find_optimal_k(data, k_min=2, k_max=15):
    """Use elbow method (second-order difference) to find optimal k."""
    inertias = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(data)
        inertias.append(km.inertia_)

    # Second-order difference to find elbow
    inertias = np.array(inertias)
    if len(inertias) >= 3:
        diffs = np.diff(inertias)
        diffs2 = np.diff(diffs)
        # The elbow is where the second derivative is maximum (largest change in slope)
        optimal_idx = np.argmax(diffs2) + k_min + 1
    else:
        optimal_idx = k_min

    # Clamp to valid range
    optimal_idx = max(k_min, min(optimal_idx, k_max))
    return optimal_idx, inertias


def identify_outliers(features, labels, centers, percentile=90):
    """Identify outliers as points farthest from their cluster center (top percentile)."""
    data = np.column_stack([features["Returns"].values, features["Volatility"].values])
    distances = np.array([
        np.linalg.norm(data[i] - centers[labels[i]]) for i in range(len(data))
    ])
    threshold = np.percentile(distances, percentile)
    outlier_mask = distances >= threshold
    outlier_df = features[outlier_mask].copy()
    outlier_df["Distance"] = distances[outlier_mask]
    outlier_df["Cluster"] = labels[outlier_mask]
    outlier_df = outlier_df.sort_values("Distance", ascending=False)
    return outlier_df


def create_plot(features, labels, output_dir, date_str):
    """Create interactive plotly scatter plot."""
    import plotly.express as px

    df = features.reset_index()
    df.columns = ["Ticker", "Returns", "Volatility"]
    df["Cluster"] = [str(c) for c in labels]

    fig = px.scatter(
        df,
        x="Returns",
        y="Volatility",
        color="Cluster",
        hover_data=["Ticker"],
        title=f"S&P 500 Clustering — Returns × Volatility ({date_str})",
    )
    fig.update_traces(
        marker=dict(size=8, symbol="diamond", line=dict(width=1, color="DarkSlateGrey"))
    )
    fig.update_layout(
        xaxis_title="Annualized Return",
        yaxis_title="Annualized Volatility",
    )

    html_path = os.path.join(output_dir, f"sp500_clusters_{date_str}.html")
    fig.write_html(html_path)
    return html_path


def main():
    parser = argparse.ArgumentParser(description="S&P 500 K-means clustering analysis")
    parser.add_argument("--period", default="1y", help="yfinance period (default: 1y)")
    parser.add_argument("--clusters", default="auto", help="Number of clusters or 'auto' (default: auto)")
    parser.add_argument("--output", default="research/screening/", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Show detailed progress")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    os.makedirs(args.output, exist_ok=True)
    os.makedirs("data/snapshots", exist_ok=True)

    # 1. Get tickers
    if args.verbose:
        print("Fetching S&P 500 tickers from Wikipedia...")
    tickers = get_sp500_tickers()
    if args.verbose:
        print(f"  Found {len(tickers)} tickers")

    # 2. Download prices
    if args.verbose:
        print(f"Downloading price data (period={args.period})...")
    prices = download_prices(tickers, args.period)
    if args.verbose:
        print(f"  Got data for {prices.shape[1]} tickers, {prices.shape[0]} trading days")

    # Save price snapshot
    snapshot_path = f"data/snapshots/sp500_prices_{date_str}.csv"
    prices.to_csv(snapshot_path)
    if args.verbose:
        print(f"  Price snapshot saved to {snapshot_path}")

    # 3. Compute features
    features = compute_features(prices)
    if args.verbose:
        print(f"  Computed features for {len(features)} tickers (after dropping NaN)")

    # 4. Determine k
    data = np.column_stack([features["Returns"].values, features["Volatility"].values])

    if args.clusters == "auto":
        k, inertias = find_optimal_k(data)
        if args.verbose:
            print(f"  Elbow method selected k={k}")
    else:
        k = int(args.clusters)
        if args.verbose:
            print(f"  Using manually specified k={k}")

    # 5. Cluster
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(data)
    centers = kmeans.cluster_centers_

    if args.verbose:
        for i in range(k):
            count = np.sum(labels == i)
            print(f"  Cluster {i}: {count} tickers (center: return={centers[i][0]:.4f}, vol={centers[i][1]:.4f})")

    # 6. Identify outliers
    outliers = identify_outliers(features, labels, centers)

    # 7. Save outputs
    # Outlier CSV
    csv_path = os.path.join(args.output, f"sp500_outliers_{date_str}.csv")
    outliers.to_csv(csv_path)

    # Plotly HTML
    html_path = create_plot(features, labels, args.output, date_str)

    # Markdown summary
    md_lines = [
        f"# S&P 500 Clustering Analysis — {date_str}",
        "",
        "## Parameters",
        f"- Period: {args.period}",
        f"- Clusters (k): {k}" + (" (auto-detected)" if args.clusters == "auto" else ""),
        f"- Tickers analyzed: {len(features)}",
        "",
        "## Cluster Summary",
        "",
        "| Cluster | Count | Avg Return | Avg Volatility |",
        "|---------|-------|------------|----------------|",
    ]
    for i in range(k):
        mask = labels == i
        cluster_features = features[mask]
        md_lines.append(
            f"| {i} | {mask.sum()} | {cluster_features['Returns'].mean():.4f} | {cluster_features['Volatility'].mean():.4f} |"
        )

    md_lines.extend([
        "",
        f"## Outliers (top {len(outliers)})",
        "",
        "| Ticker | Return | Volatility | Cluster | Distance |",
        "|--------|--------|------------|---------|----------|",
    ])
    for ticker, row in outliers.iterrows():
        md_lines.append(
            f"| {ticker} | {row['Returns']:.4f} | {row['Volatility']:.4f} | {int(row['Cluster'])} | {row['Distance']:.4f} |"
        )

    md_lines.extend([
        "",
        "## Files",
        f"- Chart: `{html_path}`",
        f"- Outliers CSV: `{csv_path}`",
        f"- Price snapshot: `{snapshot_path}`",
        "",
        "---",
        "*Clustering reflects historical price statistics only. Outlier status does not imply investment opportunity — fundamental analysis and valuation are required.*",
    ])

    md_content = "\n".join(md_lines) + "\n"
    md_path = os.path.join(args.output, f"sp500_clusters_{date_str}.md")
    with open(md_path, "w") as f:
        f.write(md_content)

    # Print summary to stdout
    print(md_content)

    if args.verbose:
        print(f"\nFiles written:")
        print(f"  {html_path}")
        print(f"  {csv_path}")
        print(f"  {md_path}")
        print(f"  {snapshot_path}")


if __name__ == "__main__":
    main()
