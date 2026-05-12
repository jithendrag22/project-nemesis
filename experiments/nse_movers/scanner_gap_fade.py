"""
Gap Fade Morning Scanner
========================
Runs at 9:16 AM IST. Fetches opening prices, identifies gap stocks,
ranks them, and outputs the top trade pick with entry/SL/target.

Usage:
    python scanner_gap_fade.py              # Run live scan
    python scanner_gap_fade.py --test       # Test with yesterday's data
"""

import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date, timedelta
import argparse
import json

# ── Config ─────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
UNIVERSE_FILE = PROJECT_DIR / "data" / "universe" / "fo_stocks.csv"
UNIVERSE_EXTRA = PROJECT_DIR / "data" / "universe" / "nifty200_extra.csv"
BHAVCOPY_DIR = Path(__file__).parent / "bhavcopy_data"

# Strategy parameters (from backtest results)
MIN_GAP_PCT = 2.0           # Minimum absolute gap to consider
MAX_GAP_PCT = 15.0          # Skip extreme gaps (likely circuits)
SL_PCT = 0.5                # Stop loss % from entry
TARGET_PCT = 1.0            # Target % from entry
CAPITAL = 100000            # Capital per trade
MIN_PRICE = 50              # Skip penny stocks
MAX_PRICE = 5000            # Skip very expensive stocks


def load_universe() -> list[str]:
    """Load the F&O stock universe."""
    base = pd.read_csv(UNIVERSE_FILE)
    symbols = base["symbol"].tolist()

    if UNIVERSE_EXTRA.exists():
        extra = pd.read_csv(UNIVERSE_EXTRA)
        extra_syms = extra["symbol"].tolist()
        symbols = list(set(symbols + extra_syms))

    return sorted(symbols)


def get_previous_close_from_bhavcopy(target_date: date | None = None) -> dict[str, float]:
    """Get previous close prices from the most recent bhavcopy."""
    files = sorted(BHAVCOPY_DIR.glob("bhav_*.csv"))
    if not files:
        return {}

    if target_date:
        # Find the bhavcopy for the date before target_date
        target_files = []
        for f in files:
            date_str = f.stem.replace("bhav_", "")
            dt = pd.to_datetime(date_str, format="%d%m%Y").date()
            if dt < target_date:
                target_files.append((dt, f))
        if target_files:
            target_files.sort()
            _, bhav_file = target_files[-1]
        else:
            bhav_file = files[-1]
    else:
        bhav_file = files[-1]

    df = pd.read_csv(bhav_file)
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    eq = df[df["SERIES"].isin(["EQ", "BE", "BZ"])]

    date_str = bhav_file.stem.replace("bhav_", "")
    bhav_date = pd.to_datetime(date_str, format="%d%m%Y").date()

    print(f"  Using bhavcopy from: {bhav_date}")

    return dict(zip(eq["SYMBOL"], eq["CLOSE_PRICE"]))


def get_opening_prices_live(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch current/today's opening prices via yfinance.
    Returns {symbol: {open, price, volume, prev_close}}
    """
    # Convert to yfinance format
    yf_symbols = [s.replace("&", "%26") for s in symbols]
    # yfinance can handle batches
    result = {}

    # Process in batches of 50
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        yf_batch = " ".join(batch)

        try:
            tickers = yf.Tickers(yf_batch)
            for symbol in batch:
                try:
                    info = tickers.tickers[symbol].info
                    result[symbol.replace(".NS", "")] = {
                        "open": info.get("open", 0),
                        "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                        "prev_close": info.get("previousClose", info.get("regularMarketPreviousClose", 0)),
                        "volume": info.get("volume", 0),
                    }
                except Exception:
                    pass
        except Exception as e:
            print(f"  Batch error: {e}")

    return result


def get_opening_prices_from_bhavcopy(target_date: date) -> dict[str, dict]:
    """Get opening prices from a specific date's bhavcopy (for testing)."""
    date_str = target_date.strftime("%d%m%Y")
    bhav_file = BHAVCOPY_DIR / f"bhav_{date_str}.csv"

    if not bhav_file.exists():
        print(f"  No bhavcopy for {target_date}")
        return {}

    df = pd.read_csv(bhav_file)
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    eq = df[df["SERIES"].isin(["EQ", "BE", "BZ"])]

    result = {}
    for _, row in eq.iterrows():
        result[row["SYMBOL"]] = {
            "open": row["OPEN_PRICE"],
            "close": row["CLOSE_PRICE"],
            "high": row["HIGH_PRICE"],
            "low": row["LOW_PRICE"],
            "prev_close": row["PREV_CLOSE"],
            "turnover": row.get("TURNOVER_LACS", 0),
        }

    return result


def find_gap_candidates(
    prev_closes: dict[str, float],
    today_data: dict[str, dict],
    fo_symbols: list[str],
) -> pd.DataFrame:
    """Find and rank gap-fade candidates."""
    candidates = []

    for symbol, data in today_data.items():
        open_price = data.get("open", 0)
        prev_close = prev_closes.get(symbol, data.get("prev_close", 0))

        if not open_price or not prev_close or open_price <= 0 or prev_close <= 0:
            continue

        if open_price < MIN_PRICE or open_price > MAX_PRICE:
            continue

        gap_pct = ((open_price - prev_close) / prev_close) * 100
        abs_gap = abs(gap_pct)

        if abs_gap < MIN_GAP_PCT or abs_gap > MAX_GAP_PCT:
            continue

        # Direction: fade the gap
        if gap_pct > 0:
            direction = "SHORT"
            sl_price = open_price * (1 + SL_PCT / 100)
            target_price = open_price * (1 - TARGET_PCT / 100)
        else:
            direction = "LONG"
            sl_price = open_price * (1 - SL_PCT / 100)
            target_price = open_price * (1 + TARGET_PCT / 100)

        # Position sizing
        shares = int(CAPITAL / open_price)
        risk_rs = abs(open_price - sl_price) * shares
        reward_rs = abs(target_price - open_price) * shares

        # Check if it's an F&O stock (preferred)
        is_fo = symbol in fo_symbols or f"{symbol}.NS" in fo_symbols

        candidates.append({
            "symbol": symbol,
            "open": round(open_price, 2),
            "prev_close": round(prev_close, 2),
            "gap_pct": round(gap_pct, 2),
            "abs_gap": round(abs_gap, 2),
            "direction": direction,
            "sl_price": round(sl_price, 2),
            "target_price": round(target_price, 2),
            "shares": shares,
            "risk_rs": round(risk_rs, 2),
            "reward_rs": round(reward_rs, 2),
            "is_fo": is_fo,
            "turnover": data.get("turnover", 0),
        })

    if not candidates:
        return pd.DataFrame()

    df = pd.DataFrame(candidates)

    # Rank by:
    # 1. F&O stocks preferred (more liquid, can short easily)
    # 2. Gap size in sweet spot (3-7% is ideal from backtest)
    # 3. Higher turnover preferred
    df["gap_score"] = df["abs_gap"].apply(lambda x: 10 - abs(x - 4) if 2 <= x <= 7 else 5 - abs(x - 4))
    df["rank_score"] = (
        df["is_fo"].astype(int) * 5
        + df["gap_score"]
        + np.log1p(df["turnover"]) * 0.5
    )
    df = df.sort_values("rank_score", ascending=False)

    return df


def format_alert(pick: pd.Series, rank: int = 1) -> str:
    """Format a trade alert for display."""
    direction_emoji = "📈" if pick["direction"] == "LONG" else "📉"
    direction_label = "LONG (Gap Down → Buy Dip)" if pick["direction"] == "LONG" else "SHORT (Gap Up → Fade)"

    alert = f"""
{'='*55}
{direction_emoji} GAP FADE SIGNAL #{rank} — {direction_label}
{'='*55}

Stock    : {pick['symbol']} (NSE)
Gap      : {pick['gap_pct']:+.1f}% (opened ₹{pick['open']:,.2f} vs prev close ₹{pick['prev_close']:,.2f})

Entry    : ₹{pick['open']:,.2f} (at market open)
Stop     : ₹{pick['sl_price']:,.2f} ({'-' if pick['direction']=='LONG' else '+'}{SL_PCT}% from entry)
Target   : ₹{pick['target_price']:,.2f} ({'+' if pick['direction']=='LONG' else '-'}{TARGET_PCT}% from entry)

Shares   : {pick['shares']}
Capital  : ₹{pick['shares'] * pick['open']:,.0f}
Risk     : ₹{pick['risk_rs']:,.0f}
Reward   : ₹{pick['reward_rs']:,.0f}
R:R      : 1:{pick['reward_rs']/pick['risk_rs']:.1f}

F&O Stock: {'✓ Yes' if pick['is_fo'] else '✗ No (cash only)'}
{'='*55}
"""
    return alert


def run_scanner(test_mode: bool = False, test_date: date | None = None):
    """Main scanner function."""
    print("=" * 55)
    print("  GAP FADE MORNING SCANNER")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print()

    # Load F&O universe
    fo_universe = load_universe()
    fo_symbols_clean = [s.replace(".NS", "") for s in fo_universe]
    print(f"  F&O universe: {len(fo_symbols_clean)} stocks")

    if test_mode:
        # Use bhavcopy data for testing
        if test_date is None:
            # Find the most recent trading day
            files = sorted(BHAVCOPY_DIR.glob("bhav_*.csv"))
            if not files:
                print("  No bhavcopy data available for testing!")
                return
            last_file = files[-1]
            date_str = last_file.stem.replace("bhav_", "")
            test_date = pd.to_datetime(date_str, format="%d%m%Y").date()

        print(f"  TEST MODE — Using data from: {test_date}")
        print()

        # Get previous closes
        prev_closes = get_previous_close_from_bhavcopy(test_date)
        # Get today's data
        today_data = get_opening_prices_from_bhavcopy(test_date)

        if not today_data:
            print("  No data for test date!")
            return
    else:
        print("  LIVE MODE")
        print()
        # Get previous closes from most recent bhavcopy
        prev_closes = get_previous_close_from_bhavcopy()
        # Get live opening prices
        today_data = get_opening_prices_live(fo_universe)

    print(f"  Previous closes: {len(prev_closes)} stocks")
    print(f"  Today's data: {len(today_data)} stocks")
    print()

    # Find candidates
    candidates = find_gap_candidates(prev_closes, today_data, fo_symbols_clean)

    if candidates.empty:
        print("  ⚠️ No gap candidates found today (gap < 2% for all stocks)")
        return

    print(f"  Found {len(candidates)} gap candidates (≥{MIN_GAP_PCT}% gap)")
    print()

    # Show top 5
    print("-" * 55)
    print("  TOP 5 CANDIDATES (ranked by quality)")
    print("-" * 55)
    for i, (_, pick) in enumerate(candidates.head(5).iterrows()):
        print(format_alert(pick, rank=i + 1))

    # Show if test mode — what actually happened
    if test_mode and "close" in today_data.get(candidates.iloc[0]["symbol"], {}):
        print()
        print("=" * 55)
        print("  ACTUAL RESULTS (what happened that day)")
        print("=" * 55)
        for _, pick in candidates.head(5).iterrows():
            sym = pick["symbol"]
            if sym in today_data and "close" in today_data[sym]:
                actual = today_data[sym]
                if pick["direction"] == "LONG":
                    # Check if target or SL was hit
                    target_hit = actual["high"] >= pick["target_price"]
                    sl_hit = actual["low"] <= pick["sl_price"]
                    close_pnl = ((actual["close"] - pick["open"]) / pick["open"]) * 100
                else:
                    target_hit = actual["low"] <= pick["target_price"]
                    sl_hit = actual["high"] >= pick["sl_price"]
                    close_pnl = ((pick["open"] - actual["close"]) / pick["open"]) * 100

                if target_hit and not sl_hit:
                    outcome = "✅ WIN"
                elif sl_hit and not target_hit:
                    outcome = "❌ LOSS"
                elif target_hit and sl_hit:
                    outcome = "⚠️ AMBIGUOUS"
                else:
                    outcome = f"➡️ FLAT ({close_pnl:+.1f}%)"

                print(f"  {sym:<15} Gap {pick['gap_pct']:+.1f}% | {pick['direction']:5} | {outcome}")

    # Show summary table
    print()
    print("-" * 80)
    print(f"{'Symbol':<12} {'Gap%':>7} {'Dir':>6} {'Entry':>10} {'SL':>10} {'Target':>10} {'F&O':>5}")
    print("-" * 80)
    for _, c in candidates.head(15).iterrows():
        print(f"{c['symbol']:<12} {c['gap_pct']:>+6.1f}% {c['direction']:>6} "
              f"₹{c['open']:>8,.2f} ₹{c['sl_price']:>8,.2f} ₹{c['target_price']:>8,.2f} "
              f"{'  ✓' if c['is_fo'] else '  ✗'}")
    print("-" * 80)

    return candidates


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gap Fade Morning Scanner")
    parser.add_argument("--test", action="store_true", help="Run in test mode with bhavcopy data")
    parser.add_argument("--date", type=str, help="Test date (YYYY-MM-DD)", default=None)
    args = parser.parse_args()

    test_date = None
    if args.date:
        test_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    run_scanner(test_mode=args.test or args.date is not None, test_date=test_date)
