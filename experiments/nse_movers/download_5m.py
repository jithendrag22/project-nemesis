"""
Download 5-minute intraday data for F&O stocks using yfinance.
yfinance provides last 60 days of 5-minute data.
"""
import yfinance as yf
import pandas as pd
from pathlib import Path
import time

INTRADAY_5M_DIR = Path(__file__).parent / "intraday_5m"
INTRADAY_5M_DIR.mkdir(parents=True, exist_ok=True)

# Load universe from Project Nemesis
UNIVERSE_FILE = Path(__file__).parent.parent.parent / "data" / "universe" / "fo_stocks.csv"


def download_5m_data():
    universe = pd.read_csv(UNIVERSE_FILE)
    symbols = universe["symbol"].tolist()
    total = len(symbols)
    failed = []

    print(f"Downloading 5-minute data for {total} F&O stocks (last 60 days)...")
    print()

    for i, symbol in enumerate(symbols):
        safe_name = symbol.replace(".", "_").replace("&", "AND")
        out_file = INTRADAY_5M_DIR / f"{safe_name}.csv"

        if out_file.exists():
            print(f"  [{i+1}/{total}] {symbol} — already exists, skipping")
            continue

        print(f"  [{i+1}/{total}] {symbol} — downloading...", end=" ")
        try:
            df = yf.download(symbol, period="60d", interval="5m", progress=False, auto_adjust=True)
            if df.empty or len(df) < 50:
                print("✗ no data")
                failed.append(symbol)
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.dropna(inplace=True)
            df.to_csv(out_file)
            print(f"✓ {len(df)} candles")
        except Exception as e:
            print(f"✗ error: {e}")
            failed.append(symbol)

        time.sleep(0.3)

    print(f"\nDone. Failed: {len(failed)}")
    if failed:
        print(f"Failed: {failed[:20]}...")


if __name__ == "__main__":
    download_5m_data()
