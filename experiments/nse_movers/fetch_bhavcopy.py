"""
Fetch NSE Bhavcopy data and identify stocks that moved >1% and >2%.
Data source: NSE official sec_bhavdata_full CSV files.
"""

import requests
import pandas as pd
import io
import time
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "bhavcopy_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}

BASE_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{}.csv"


def download_bhavcopy(dt: date) -> pd.DataFrame | None:
    """Download bhavcopy for a single date. Returns DataFrame or None."""
    date_str = dt.strftime("%d%m%Y")
    file_path = DATA_DIR / f"bhav_{date_str}.csv"

    # Check cache first
    if file_path.exists():
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        return df

    url = BASE_URL.format(date_str)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 500:
            # Save raw file
            file_path.write_bytes(resp.content)
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = df.columns.str.strip()
            return df
        else:
            return None
    except Exception as e:
        print(f"  Error for {dt}: {e}")
        return None


def compute_movers(df: pd.DataFrame, dt: date) -> dict:
    """From a bhavcopy DataFrame, compute the % of stocks that moved >1% and >2%."""
    # Strip whitespace from all string columns (NSE CSVs have leading spaces)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    # Filter to equity series only (EQ, BE, BZ)
    eq = df[df["SERIES"].isin(["EQ", "BE", "BZ"])].copy()

    # Need CLOSE_PRICE and PREV_CLOSE
    required_cols = {"CLOSE_PRICE", "PREV_CLOSE", "SYMBOL"}
    if not required_cols.issubset(set(eq.columns)):
        print(f"  Missing columns for {dt}: {set(eq.columns)}")
        return None

    eq = eq[eq["PREV_CLOSE"] > 0].copy()
    eq["pct_change"] = ((eq["CLOSE_PRICE"] - eq["PREV_CLOSE"]) / eq["PREV_CLOSE"]) * 100

    total = len(eq)
    up_1 = len(eq[eq["pct_change"] > 1])
    up_2 = len(eq[eq["pct_change"] > 2])
    down_1 = len(eq[eq["pct_change"] < -1])
    down_2 = len(eq[eq["pct_change"] < -2])
    moved_1 = len(eq[eq["pct_change"].abs() > 1])
    moved_2 = len(eq[eq["pct_change"].abs() > 2])

    return {
        "date": dt,
        "total_stocks": total,
        "up_gt_1pct": up_1,
        "up_gt_2pct": up_2,
        "down_gt_1pct": down_1,
        "down_gt_2pct": down_2,
        "moved_gt_1pct": moved_1,
        "moved_gt_2pct": moved_2,
        "pct_moved_gt_1pct": round(moved_1 / total * 100, 1) if total else 0,
        "pct_moved_gt_2pct": round(moved_2 / total * 100, 1) if total else 0,
        "pct_up_gt_1pct": round(up_1 / total * 100, 1) if total else 0,
        "pct_up_gt_2pct": round(up_2 / total * 100, 1) if total else 0,
        "pct_down_gt_1pct": round(down_1 / total * 100, 1) if total else 0,
        "pct_down_gt_2pct": round(down_2 / total * 100, 1) if total else 0,
    }


def fetch_range(start_date: date, end_date: date) -> pd.DataFrame:
    """Download bhavcopies for a date range and compute mover stats."""
    results = []
    current = start_date
    consecutive_fails = 0

    while current <= end_date:
        # Skip weekends
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        print(f"  Fetching {current.strftime('%Y-%m-%d')}...", end=" ")
        df = download_bhavcopy(current)

        if df is not None:
            stats = compute_movers(df, current)
            if stats:
                results.append(stats)
                print(f"✓ {stats['total_stocks']} stocks | "
                      f">{1}%: {stats['moved_gt_1pct']} ({stats['pct_moved_gt_1pct']}%) | "
                      f">{2}%: {stats['moved_gt_2pct']} ({stats['pct_moved_gt_2pct']}%)")
                consecutive_fails = 0
            else:
                print("✗ parse error")
                consecutive_fails += 1
        else:
            print("✗ no data (holiday?)")
            consecutive_fails += 1

        # If too many consecutive fails, we might be hitting a wall
        if consecutive_fails >= 10:
            print(f"\n  Too many consecutive failures at {current}. Stopping.")
            break

        current += timedelta(days=1)
        time.sleep(0.5)  # Be polite

    if results:
        return pd.DataFrame(results)
    return pd.DataFrame()


if __name__ == "__main__":
    print("=" * 70)
    print("NSE BHAVCOPY MOVER ANALYSIS")
    print("Fetching all trading days from Jan 2024 to May 2025")
    print("=" * 70)

    start = date(2024, 1, 1)
    end = date(2025, 5, 9)

    results_df = fetch_range(start, end)

    if not results_df.empty:
        out_file = Path(__file__).parent / "nse_daily_movers.csv"
        results_df.to_csv(out_file, index=False)
        print(f"\n{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total trading days fetched: {len(results_df)}")
        print(f"Date range: {results_df['date'].min()} to {results_df['date'].max()}")
        print(f"\nAvg stocks per day: {results_df['total_stocks'].mean():.0f}")
        print(f"\n--- Stocks moving >1% (either direction) ---")
        print(f"  Avg count: {results_df['moved_gt_1pct'].mean():.0f}")
        print(f"  Avg %:     {results_df['pct_moved_gt_1pct'].mean():.1f}%")
        print(f"  Min %:     {results_df['pct_moved_gt_1pct'].min():.1f}%")
        print(f"  Max %:     {results_df['pct_moved_gt_1pct'].max():.1f}%")
        print(f"\n--- Stocks moving >2% (either direction) ---")
        print(f"  Avg count: {results_df['moved_gt_2pct'].mean():.0f}")
        print(f"  Avg %:     {results_df['pct_moved_gt_2pct'].mean():.1f}%")
        print(f"  Min %:     {results_df['pct_moved_gt_2pct'].min():.1f}%")
        print(f"  Max %:     {results_df['pct_moved_gt_2pct'].max():.1f}%")
        print(f"\nSaved to: {out_file}")
    else:
        print("No data fetched.")
