"""
Strategy C — Hourly (1h) intraday data downloader and loader.

yfinance gives ~3 years of 1-hour data per stock (60m interval).
Data is saved to data/intraday_1h/ and loaded from disk on subsequent runs.
"""

from __future__ import annotations
import time
from pathlib import Path
import sys

import pandas as pd
import yfinance as yf
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.data.downloader import load_universe
from .config import SECTOR_WHITELIST

INTRADAY_DIR = Path(__file__).parent.parent.parent / "data" / "intraday_1h"
IST = pytz.timezone("Asia/Kolkata")


def _safe(symbol: str) -> str:
    return symbol.replace(".", "_").replace("&", "AND")


def download_one(symbol: str, force: bool = False) -> pd.DataFrame | None:
    out = INTRADAY_DIR / f"{_safe(symbol)}.csv"
    if out.exists() and not force:
        return None   # already downloaded

    try:
        df = yf.download(
            symbol,
            interval="1h",
            period="730d",
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)

        # Convert to IST
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)

        df.to_csv(out)
        return df
    except Exception as e:
        print(f"  Error: {symbol}: {e}")
        return None


def download_all(force: bool = False) -> None:
    INTRADAY_DIR.mkdir(parents=True, exist_ok=True)
    universe = load_universe()
    symbols  = [
        row["symbol"]
        for _, row in universe.iterrows()
        if row.get("sector", "Unknown") in SECTOR_WHITELIST
    ]

    # Also download Nifty
    symbols_all = symbols + ["^NSEI"]
    total = len(symbols_all)
    ok = skip = fail = 0

    print(f"Downloading 1-hour data for {total} symbols...")

    for i, sym in enumerate(symbols_all, 1):
        out = INTRADAY_DIR / f"{_safe(sym)}.csv"
        if out.exists() and not force:
            skip += 1
            if i % 10 == 0:
                print(f"  [{i}/{total}] ... ({skip} cached, {ok} new, {fail} failed)")
            continue

        df = download_one(sym, force=force)
        if df is not None:
            ok += 1
            print(f"  [{i}/{total}] {sym:<20} ✓ {len(df)} candles  "
                  f"[{df.index[0].date()} → {df.index[-1].date()}]")
        else:
            if out.exists():
                skip += 1
            else:
                fail += 1
                print(f"  [{i}/{total}] {sym:<20} ✗ no data")

        time.sleep(0.25)

    print(f"\nDone. New: {ok}  Cached: {skip}  Failed: {fail}")


def load_one(symbol: str) -> pd.DataFrame | None:
    path = INTRADAY_DIR / f"{_safe(symbol)}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize(IST)
    else:
        df.index = df.index.tz_convert(IST)
    return df


def load_nifty_hourly() -> pd.DataFrame | None:
    return load_one("^NSEI")


def load_all_hourly() -> dict[str, pd.DataFrame]:
    """Load all downloaded hourly data into memory. Returns {symbol: df}."""
    universe = load_universe()
    result   = {}
    for _, row in universe.iterrows():
        if row.get("sector", "Unknown") not in SECTOR_WHITELIST:
            continue
        sym = row["symbol"]
        df  = load_one(sym)
        if df is not None and len(df) >= 50:
            result[sym] = df
    return result


if __name__ == "__main__":
    download_all()
