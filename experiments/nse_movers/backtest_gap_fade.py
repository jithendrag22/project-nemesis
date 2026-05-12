"""
Gap Fade Strategy — Intraday Backtest Engine
=============================================
Uses intraday candle data to simulate gap-fade trades with precise
SL/target resolution (determines which level gets hit FIRST).

Strategy:
- Gap UP at open → SHORT (fade the gap, expecting pullback)
- Gap DOWN at open → LONG (buy the dip, expecting bounce)
- SL = X% against trade direction
- Target = Y% in trade direction (gap-fill direction)
- Walk through candles to determine outcome
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
from dataclasses import dataclass, field
from typing import Literal

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
INTRADAY_1H_DIR = PROJECT_DIR / "data" / "intraday_1h"
INTRADAY_5M_DIR = Path(__file__).parent / "intraday_5m"
BHAVCOPY_DIR = Path(__file__).parent / "bhavcopy_data"
RESULTS_DIR = Path(__file__).parent / "backtest_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Data Classes ───────────────────────────────────────────────────────
@dataclass
class TradeResult:
    date: str
    symbol: str
    gap_pct: float
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    sl_price: float
    target_price: float
    outcome: Literal["WIN", "LOSS", "FLAT"]
    exit_price: float
    pnl_pct: float
    pnl_rs: float  # P&L in Rs on 1L capital
    exit_time: str
    candle_idx: int  # which candle resolved the trade (0-based)


@dataclass
class BacktestConfig:
    gap_threshold_pct: float = 2.0       # Minimum gap to trigger a trade
    sl_pct: float = 0.5                  # Stop loss % from entry
    target_pct: float = 1.0              # Target % from entry (gap fill direction)
    capital: float = 100000              # Capital per trade
    max_gap_pct: float = 20.0            # Skip gaps larger than this (likely circuit/error)
    avoid_last_hour: bool = True         # Don't enter if resolved in last candle only
    data_source: str = "1h"              # "1h" or "5m"
    min_turnover_filter: bool = False    # If True, only trade liquid stocks
    direction_filter: str = "both"       # "long", "short", or "both"


# ── Core Engine ────────────────────────────────────────────────────────

def load_intraday_data(symbol: str, source: str = "1h") -> pd.DataFrame | None:
    """Load intraday data for a symbol."""
    if source == "1h":
        data_dir = INTRADAY_1H_DIR
    elif source == "5m":
        data_dir = INTRADAY_5M_DIR
    else:
        raise ValueError(f"Unknown source: {source}")

    safe_name = symbol.replace(".", "_").replace("&", "AND")
    file = data_dir / f"{safe_name}.csv"
    if not file.exists():
        # Try with _NS suffix
        file = data_dir / f"{safe_name}_NS.csv"
    if not file.exists():
        return None

    df = pd.read_csv(file, index_col=0, parse_dates=True)
    # Ensure columns are clean
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.strip() for c in df.columns]
    return df


def get_previous_closes_from_bhavcopy() -> dict[str, dict]:
    """
    Build a lookup: {date_str: {symbol: prev_close}} from bhavcopy data.
    This gives us accurate previous close for ALL NSE stocks.
    """
    files = sorted(BHAVCOPY_DIR.glob("bhav_*.csv"))
    prev_closes = {}

    for f in files:
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()
        eq = df[df["SERIES"].isin(["EQ", "BE", "BZ"])].copy()

        date_str = f.stem.replace("bhav_", "")
        dt = pd.to_datetime(date_str, format="%d%m%Y")
        date_key = dt.strftime("%Y-%m-%d")

        prev_closes[date_key] = {}
        for _, row in eq.iterrows():
            prev_closes[date_key][row["SYMBOL"]] = {
                "prev_close": row["PREV_CLOSE"],
                "close": row["CLOSE_PRICE"],
                "open": row["OPEN_PRICE"],
            }

    return prev_closes


def simulate_trade(
    candles: pd.DataFrame,
    direction: str,
    entry_price: float,
    sl_price: float,
    target_price: float,
    avoid_last_hour: bool = True,
) -> tuple[str, float, str, int]:
    """
    Walk through intraday candles and determine trade outcome.

    Returns: (outcome, exit_price, exit_time, candle_idx)
    """
    for idx, (ts, candle) in enumerate(candles.iterrows()):
        high = candle["High"]
        low = candle["Low"]
        close_price = candle["Close"]

        if direction == "LONG":
            sl_hit = low <= sl_price
            target_hit = high >= target_price
        else:  # SHORT
            sl_hit = high >= sl_price
            target_hit = low <= target_price

        if sl_hit and target_hit:
            # Both hit in same candle — conservative: count as LOSS
            exit_price = sl_price
            exit_time = str(ts)
            return ("LOSS", exit_price, exit_time, idx)
        elif target_hit:
            exit_price = target_price
            exit_time = str(ts)
            return ("WIN", exit_price, exit_time, idx)
        elif sl_hit:
            exit_price = sl_price
            exit_time = str(ts)
            return ("LOSS", exit_price, exit_time, idx)

    # Neither hit by end of day — close at last candle's close
    last_candle = candles.iloc[-1]
    exit_price = last_candle["Close"]
    exit_time = str(candles.index[-1])
    return ("FLAT", exit_price, exit_time, len(candles) - 1)


def run_backtest(config: BacktestConfig) -> list[TradeResult]:
    """
    Run the full gap-fade backtest.
    """
    source = config.data_source
    if source == "1h":
        data_dir = INTRADAY_1H_DIR
    else:
        data_dir = INTRADAY_5M_DIR

    # Get list of available symbols
    files = list(data_dir.glob("*.csv"))
    symbols = [f.stem.replace("_NS", "").replace("_", ".") for f in files if f.stem != "^NSEI"]
    # Also keep the original filenames for loading
    symbol_map = {}
    for f in files:
        if f.stem == "^NSEI":
            continue
        sym = f.stem.replace("_NS", "")
        symbol_map[sym] = f.stem

    print(f"Backtest Config:")
    print(f"  Data source: {source}")
    print(f"  Gap threshold: {config.gap_threshold_pct}%")
    print(f"  SL: {config.sl_pct}% | Target: {config.target_pct}%")
    print(f"  Direction: {config.direction_filter}")
    print(f"  Stocks available: {len(symbol_map)}")
    print()

    results = []
    total_trades = 0
    symbols_processed = 0

    for sym_key, file_stem in sorted(symbol_map.items()):
        # Load intraday data
        file_path = data_dir / f"{file_stem}.csv"
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.strip() for c in df.columns]

        if len(df) < 14:  # Need at least 2 days
            continue

        symbols_processed += 1

        # Group by trading day
        df["trade_date"] = df.index.date
        daily_groups = df.groupby("trade_date")

        prev_close = None
        for trade_date, day_candles in daily_groups:
            if prev_close is None:
                # Use last candle of first day as prev_close reference
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            if len(day_candles) < 2:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            # Opening price = first candle's Open
            open_price = day_candles.iloc[0]["Open"]
            if open_price <= 0 or prev_close <= 0:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            # Calculate gap
            gap_pct = ((open_price - prev_close) / prev_close) * 100

            # Check if gap meets threshold
            abs_gap = abs(gap_pct)
            if abs_gap < config.gap_threshold_pct or abs_gap > config.max_gap_pct:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            # Determine direction (fade the gap)
            if gap_pct > 0:
                direction = "SHORT"  # Gap up → short
            else:
                direction = "LONG"   # Gap down → long

            # Apply direction filter
            if config.direction_filter == "long" and direction != "LONG":
                prev_close = day_candles.iloc[-1]["Close"]
                continue
            if config.direction_filter == "short" and direction != "SHORT":
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            # Calculate entry, SL, target
            entry_price = open_price
            if direction == "LONG":
                sl_price = entry_price * (1 - config.sl_pct / 100)
                target_price = entry_price * (1 + config.target_pct / 100)
            else:  # SHORT
                sl_price = entry_price * (1 + config.sl_pct / 100)
                target_price = entry_price * (1 - config.target_pct / 100)

            # Skip first candle (that's our entry candle) — start checking from candle 1
            # Actually, we enter at open of first candle, so we check from first candle onwards
            # The first candle's high/low will tell us if SL/target was hit in the opening hour
            check_candles = day_candles
            if config.avoid_last_hour and len(check_candles) > 1:
                # Remove last candle (3:15 PM candle for 1h data) to avoid square-off zone
                check_candles = check_candles.iloc[:-1]

            # Simulate
            outcome, exit_price, exit_time, candle_idx = simulate_trade(
                check_candles, direction, entry_price, sl_price, target_price,
                config.avoid_last_hour
            )

            # If FLAT after removing last hour, use full day data for exit
            if outcome == "FLAT" and config.avoid_last_hour:
                # Re-run with full candles to check if it resolves
                outcome2, exit_price2, exit_time2, candle_idx2 = simulate_trade(
                    day_candles, direction, entry_price, sl_price, target_price, False
                )
                if outcome2 != "FLAT":
                    outcome = outcome2
                    exit_price = exit_price2
                    exit_time = exit_time2
                    candle_idx = candle_idx2
                else:
                    exit_price = day_candles.iloc[-1]["Close"]
                    exit_time = str(day_candles.index[-1])
                    candle_idx = len(day_candles) - 1

            # Calculate P&L
            if direction == "LONG":
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

            shares = int(config.capital / entry_price)
            if direction == "LONG":
                pnl_rs = (exit_price - entry_price) * shares
            else:
                pnl_rs = (entry_price - exit_price) * shares

            result = TradeResult(
                date=str(trade_date),
                symbol=sym_key,
                gap_pct=round(gap_pct, 2),
                direction=direction,
                entry_price=round(entry_price, 2),
                sl_price=round(sl_price, 2),
                target_price=round(target_price, 2),
                outcome=outcome,
                exit_price=round(exit_price, 2),
                pnl_pct=round(pnl_pct, 2),
                pnl_rs=round(pnl_rs, 2),
                exit_time=exit_time,
                candle_idx=candle_idx,
            )
            results.append(result)
            total_trades += 1

            prev_close = day_candles.iloc[-1]["Close"]

    print(f"Processed {symbols_processed} symbols")
    print(f"Total trades: {total_trades}")
    return results


def analyze_results(results: list[TradeResult], config: BacktestConfig) -> pd.DataFrame:
    """Analyze and print backtest results."""
    if not results:
        print("No trades found!")
        return pd.DataFrame()

    df = pd.DataFrame([vars(r) for r in results])
    df["date"] = pd.to_datetime(df["date"])

    total = len(df)
    wins = len(df[df["outcome"] == "WIN"])
    losses = len(df[df["outcome"] == "LOSS"])
    flats = len(df[df["outcome"] == "FLAT"])

    win_rate = wins / total * 100 if total > 0 else 0
    avg_pnl = df["pnl_rs"].mean()
    total_pnl = df["pnl_rs"].sum()

    avg_win = df[df["outcome"] == "WIN"]["pnl_rs"].mean() if wins > 0 else 0
    avg_loss = df[df["outcome"] == "LOSS"]["pnl_rs"].mean() if losses > 0 else 0

    # Trading days
    unique_days = df["date"].nunique()

    print("=" * 65)
    print(f"BACKTEST RESULTS — Gap Fade Strategy")
    print(f"Gap ≥ {config.gap_threshold_pct}% | SL {config.sl_pct}% | Target {config.target_pct}%")
    print("=" * 65)
    print(f"Total trades:      {total:,}")
    print(f"Trading days:      {unique_days}")
    print(f"Trades/day avg:    {total / unique_days:.1f}" if unique_days > 0 else "")
    print()
    print(f"Wins:              {wins} ({win_rate:.1f}%)")
    print(f"Losses:            {losses} ({losses / total * 100:.1f}%)")
    print(f"Flat/EOD:          {flats} ({flats / total * 100:.1f}%)")
    print()
    print(f"Avg Win:           ₹{avg_win:+,.0f}")
    print(f"Avg Loss:          ₹{avg_loss:+,.0f}")
    print(f"Avg P&L per trade: ₹{avg_pnl:+,.0f}")
    print(f"Total P&L:         ₹{total_pnl:+,.0f}")
    print()

    # By direction
    for direction in ["LONG", "SHORT"]:
        sub = df[df["direction"] == direction]
        if len(sub) > 0:
            d_wins = len(sub[sub["outcome"] == "WIN"])
            d_wr = d_wins / len(sub) * 100
            d_pnl = sub["pnl_rs"].sum()
            print(f"  {direction}: {len(sub)} trades | WR {d_wr:.1f}% | Total P&L ₹{d_pnl:+,.0f}")

    print()

    # Monthly breakdown
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        trades=("outcome", "count"),
        wins=("outcome", lambda x: (x == "WIN").sum()),
        total_pnl=("pnl_rs", "sum"),
    )
    monthly["win_rate"] = (monthly["wins"] / monthly["trades"] * 100).round(1)
    print("Monthly Breakdown:")
    print(monthly.to_string())
    print()

    # By gap size bucket
    df["gap_bucket"] = pd.cut(df["gap_pct"].abs(), bins=[0, 1, 2, 3, 5, 10, 50],
                               labels=["0-1%", "1-2%", "2-3%", "3-5%", "5-10%", "10%+"])
    gap_stats = df.groupby("gap_bucket", observed=True).agg(
        trades=("outcome", "count"),
        wins=("outcome", lambda x: (x == "WIN").sum()),
        total_pnl=("pnl_rs", "sum"),
    )
    gap_stats["win_rate"] = (gap_stats["wins"] / gap_stats["trades"] * 100).round(1)
    print("By Gap Size:")
    print(gap_stats.to_string())
    print()

    # Candle resolution analysis
    print("Trade resolved at candle #:")
    candle_dist = df.groupby("candle_idx").agg(
        count=("outcome", "count"),
        wins=("outcome", lambda x: (x == "WIN").sum()),
    )
    candle_dist["win_rate"] = (candle_dist["wins"] / candle_dist["count"] * 100).round(1)
    print(candle_dist.head(10).to_string())

    # Simulate "pick 1 best trade per day" (largest absolute gap)
    print()
    print("=" * 65)
    print("SIMULATED: If you picked 1 trade/day (largest gap)")
    print("=" * 65)
    best_per_day = df.loc[df.groupby("date")["gap_pct"].apply(lambda x: x.abs().idxmax())]
    bpd_wins = len(best_per_day[best_per_day["outcome"] == "WIN"])
    bpd_total = len(best_per_day)
    bpd_wr = bpd_wins / bpd_total * 100 if bpd_total > 0 else 0
    bpd_pnl = best_per_day["pnl_rs"].sum()
    bpd_monthly = bpd_pnl / max(best_per_day["date"].dt.to_period("M").nunique(), 1)
    print(f"  Total trades: {bpd_total}")
    print(f"  Win rate: {bpd_wr:.1f}%")
    print(f"  Total P&L: ₹{bpd_pnl:+,.0f}")
    print(f"  Avg monthly P&L: ₹{bpd_monthly:+,.0f}")

    return df


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run a grid of configurations on 1h data
    print("=" * 65)
    print("GAP FADE STRATEGY BACKTEST")
    print("Using 1-hour intraday data (73 stocks, ~3 years)")
    print("=" * 65)
    print()

    # First, run the exact user config: SL 0.5%, Target 1.0%, Gap >= 2%
    configs = [
        BacktestConfig(gap_threshold_pct=2.0, sl_pct=0.5, target_pct=1.0, data_source="1h"),
        BacktestConfig(gap_threshold_pct=3.0, sl_pct=0.5, target_pct=1.0, data_source="1h"),
        BacktestConfig(gap_threshold_pct=2.0, sl_pct=0.75, target_pct=1.5, data_source="1h"),
        BacktestConfig(gap_threshold_pct=3.0, sl_pct=0.75, target_pct=1.5, data_source="1h"),
        BacktestConfig(gap_threshold_pct=2.0, sl_pct=0.5, target_pct=1.5, data_source="1h"),
        BacktestConfig(gap_threshold_pct=1.0, sl_pct=0.5, target_pct=1.0, data_source="1h"),
    ]

    all_summaries = []
    for i, config in enumerate(configs):
        print(f"\n{'#' * 65}")
        print(f"# CONFIG {i + 1}: Gap≥{config.gap_threshold_pct}% | SL {config.sl_pct}% | Tgt {config.target_pct}%")
        print(f"{'#' * 65}\n")

        results = run_backtest(config)
        if results:
            df = analyze_results(results, config)

            # Save trades to CSV
            out_file = RESULTS_DIR / f"trades_gap{config.gap_threshold_pct}_sl{config.sl_pct}_tgt{config.target_pct}.csv"
            df.to_csv(out_file, index=False)
            print(f"\nSaved to {out_file}")

            # Summary
            total = len(df)
            wins = len(df[df["outcome"] == "WIN"])
            total_pnl = df["pnl_rs"].sum()
            all_summaries.append({
                "gap_thresh": config.gap_threshold_pct,
                "sl_pct": config.sl_pct,
                "target_pct": config.target_pct,
                "trades": total,
                "win_rate": round(wins / total * 100, 1) if total else 0,
                "total_pnl": round(total_pnl),
                "pnl_per_trade": round(total_pnl / total) if total else 0,
            })

    # Print comparison table
    print(f"\n\n{'=' * 75}")
    print("CONFIGURATION COMPARISON")
    print(f"{'=' * 75}")
    summary_df = pd.DataFrame(all_summaries)
    print(summary_df.to_string(index=False))
