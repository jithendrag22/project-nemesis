import yfinance as yf
import pandas as pd
from pathlib import Path
import time

DATA_DIR = Path(__file__).parent.parent.parent / "data"
UNIVERSE_FILE       = DATA_DIR / "universe" / "fo_stocks.csv"
UNIVERSE_EXTRA_FILE = DATA_DIR / "universe" / "nifty200_extra.csv"
PRICES_DIR = DATA_DIR / "prices"
NIFTY_FILE = DATA_DIR / "nifty50.csv"

BACKTEST_START = "2015-01-01"
BACKTEST_END = "2024-12-31"


def load_universe(expanded: bool = False) -> pd.DataFrame:
    base = pd.read_csv(UNIVERSE_FILE)
    if not expanded:
        return base
    if UNIVERSE_EXTRA_FILE.exists():
        extra = pd.read_csv(UNIVERSE_EXTRA_FILE)
        return pd.concat([base, extra], ignore_index=True).drop_duplicates(subset="symbol")
    return base


def download_stock(symbol: str, start: str = BACKTEST_START, end: str = BACKTEST_END) -> pd.DataFrame | None:
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100:
            return None
        df.index = pd.to_datetime(df.index)
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"  Error downloading {symbol}: {e}")
        return None


def download_all(start: str = BACKTEST_START, end: str = BACKTEST_END):
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    universe = load_universe()
    total = len(universe)
    failed = []

    print(f"Downloading {total} stocks from {start} to {end}...\n")

    for i, row in universe.iterrows():
        symbol = row["symbol"]
        safe_name = symbol.replace(".", "_").replace("&", "AND")
        out_file = PRICES_DIR / f"{safe_name}.csv"

        if out_file.exists():
            print(f"  [{i+1}/{total}] {symbol} — already exists, skipping")
            continue

        print(f"  [{i+1}/{total}] {symbol} — downloading...", end=" ")
        df = download_stock(symbol, start, end)

        if df is not None:
            df.to_csv(out_file)
            print(f"✓ {len(df)} rows")
        else:
            print("✗ failed")
            failed.append(symbol)

        time.sleep(0.3)  # be polite to Yahoo Finance

    print(f"\nDone. Failed: {len(failed)}")
    if failed:
        print("Failed symbols:", failed)


def download_nifty(start: str = BACKTEST_START, end: str = BACKTEST_END):
    print("Downloading Nifty 50...", end=" ")
    df = yf.download("^NSEI", start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    df.to_csv(NIFTY_FILE)
    print(f"✓ {len(df)} rows saved to {NIFTY_FILE}")


def load_stock(symbol: str) -> pd.DataFrame | None:
    safe_name = symbol.replace(".", "_").replace("&", "AND")
    file = PRICES_DIR / f"{safe_name}.csv"
    if not file.exists():
        return None
    df = pd.read_csv(file, index_col=0, parse_dates=True)
    return df


def load_nifty() -> pd.DataFrame:
    df = pd.read_csv(NIFTY_FILE, index_col=0, parse_dates=True)
    return df


if __name__ == "__main__":
    download_nifty()
    download_all()
