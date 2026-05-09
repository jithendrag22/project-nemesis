import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.downloader import load_universe, load_stock, load_nifty
from indicators.calculator import add_all
from filters.market_filter import get_market_state
from filters.stage2_filter import passes_stage2
from setups.setup_a import detect as detect_a
from setups.setup_b import detect as detect_b

MAX_RISK       = 1_000      # ₹ per trade
MAX_CAPITAL    = 50_000     # max ₹ deployed per trade
SLIPPAGE_PCT   = 0.001      # 0.1% slippage on entry
COST_PER_TRADE = 100        # ₹ round-trip cost (brokerage + STT)
MAX_GAP_PCT    = 0.03       # skip if stock gaps up >3% at open
MAX_EXTENDED   = 0.05       # skip if price >5% above signal entry
TIME_STOP_DAYS = 15         # exit if no +2% move by this day (data: breakouts need ~2 weeks)
HARD_STOP_DAYS = 30         # force exit on day 30 (median natural hold = 16 days)
MIN_MOVE_PCT   = 0.02       # required move for time stop check


DEFAULT_PARAMS = {
    # market filter
    "market_filter_version": "B",
    # stage 2
    "near_52w_high_pct": 15,
    "min_turnover_cr": 10,
    # setup A
    "base_days_min": 5,
    "base_days_max": 15,
    "base_depth_pct": 8.0,
    "vol_ratio_min": 2.0,   # data: 2.0 outperforms 1.5 and 2.5
    # setup B
    "ema_proximity_pct": 1.0,
    "prior_advance_pct": 15.0,
    "pullback_lookback": 5,
}


def run_backtest(params: dict = None, start: str = "2015-01-01", end: str = "2024-12-31",
                 verbose: bool = False) -> pd.DataFrame:
    """
    Run the full backtest. Returns a DataFrame of all trades.
    """
    if params is None:
        params = DEFAULT_PARAMS.copy()
    else:
        p = DEFAULT_PARAMS.copy()
        p.update(params)
        params = p

    universe = load_universe()
    nifty    = load_nifty()
    nifty.index = pd.to_datetime(nifty.index)

    # Market state for every trading day
    market_states = get_market_state(nifty, version=params["market_filter_version"])

    all_trades = []
    skipped_stocks = 0

    for _, row in universe.iterrows():
        symbol = row["symbol"]
        df = load_stock(symbol)

        if df is None or len(df) < 252:
            skipped_stocks += 1
            continue

        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= start) & (df.index <= end)]

        if len(df) < 252:
            skipped_stocks += 1
            continue

        # Add indicators
        df = add_all(df, nifty)

        # Drop rows with NaN indicators (warmup period)
        df.dropna(subset=["sma200", "ema20", "vol_ma20", "high_52w", "rs_vs_nifty_3m"], inplace=True)

        if len(df) < 50:
            continue

        # Align market state to this stock's trading dates
        ms = market_states.reindex(df.index, method="ffill")

        open_trade = None  # tracks the currently open trade

        for i in range(len(df)):
            date  = df.index[i]
            today = df.iloc[i]
            state = ms.iloc[i] if i < len(ms) else "bear"

            # ── Manage open trade ──────────────────────────────────────────
            if open_trade is not None:
                day_in_trade = (date - open_trade["entry_date"]).days
                trading_day  = open_trade["trading_days"] + 1
                open_trade["trading_days"] = trading_day

                exit_price  = None
                exit_reason = None

                # Gap down past stop at open
                if today["Open"] <= open_trade["stop"]:
                    exit_price  = today["Open"]
                    exit_reason = "stop_gap_down"

                # Stop hit during day
                elif today["Low"] <= open_trade["stop"]:
                    exit_price  = open_trade["stop"]
                    exit_reason = "stop"

                # 1:1 target hit — sell half, move stop to breakeven
                elif not open_trade.get("half_exited") and today["High"] >= open_trade["target_1r"]:
                    open_trade["half_exited"]     = True
                    open_trade["half_exit_price"] = open_trade["target_1r"]
                    open_trade["half_exit_date"]  = date
                    open_trade["stop"]            = open_trade["entry"]  # breakeven

                # 2:1 target hit — exit remaining
                elif open_trade.get("half_exited") and today["High"] >= open_trade["target_2r"]:
                    exit_price  = open_trade["target_2r"]
                    exit_reason = "target_2r"

                # Hard exit: day 5 — must come BEFORE time stop check (higher priority)
                elif trading_day >= HARD_STOP_DAYS:
                    exit_price  = today["Close"]
                    exit_reason = "hard_time_exit"

                # Time stop: no +2% move by day 3
                elif trading_day >= TIME_STOP_DAYS:
                    pct_move = (today["Close"] - open_trade["entry"]) / open_trade["entry"]
                    if pct_move < MIN_MOVE_PCT and not open_trade.get("half_exited"):
                        exit_price  = today["Close"]
                        exit_reason = "time_stop"

                if exit_price is not None:
                    # Calculate P&L
                    shares         = open_trade["shares"]
                    half_exited    = open_trade.get("half_exited", False)
                    half_exit_px   = open_trade.get("half_exit_price", 0)

                    if half_exited:
                        half_shares  = shares // 2
                        rest_shares  = shares - half_shares
                        pnl = (half_shares * (half_exit_px - open_trade["entry"]) +
                               rest_shares * (exit_price   - open_trade["entry"]) -
                               COST_PER_TRADE)
                    else:
                        pnl = shares * (exit_price - open_trade["entry"]) - COST_PER_TRADE

                    r_multiple = pnl / MAX_RISK

                    all_trades.append({
                        "symbol":       symbol,
                        "sector":       row.get("sector", "Unknown"),
                        "setup":        open_trade["setup"],
                        "entry_date":   open_trade["entry_date"],
                        "exit_date":    date,
                        "trading_days": trading_day,
                        "entry":        open_trade["entry"],
                        "stop":         open_trade["original_stop"],
                        "target_2r":    open_trade["target_2r"],
                        "exit_price":   exit_price,
                        "exit_reason":  exit_reason,
                        "shares":       shares,
                        "pnl":          round(pnl, 2),
                        "r_multiple":   round(r_multiple, 3),
                        "win":          pnl > 0,
                        "market_state": open_trade["market_state"],
                    })

                    open_trade = None

            # ── Look for new signal (only if no open trade on this stock) ──
            if open_trade is None and state in ("bull", "neutral"):
                stage2_pass, _ = passes_stage2(today, params)
                if not stage2_pass:
                    continue

                signal = detect_a(df, i, params) or detect_b(df, i, params)

                if signal is None:
                    continue

                # Position sizing
                risk_per_share = signal["risk_per_share"]
                if risk_per_share <= 0:
                    continue

                shares       = int(MAX_RISK / risk_per_share)
                capital_used = shares * signal["entry"]

                if capital_used > MAX_CAPITAL:
                    shares       = int(MAX_CAPITAL / signal["entry"])
                    capital_used = shares * signal["entry"]

                if shares <= 0:
                    continue

                # Simulate next-day execution
                if i + 1 >= len(df):
                    continue

                next_day  = df.iloc[i + 1]
                entry_px  = next_day["Open"] * (1 + SLIPPAGE_PCT)

                # Skip if gap up > 3%
                gap = (next_day["Open"] - today["Close"]) / today["Close"]
                if gap > MAX_GAP_PCT:
                    continue

                # Skip if already extended >5% from signal entry
                if (entry_px - signal["entry"]) / signal["entry"] > MAX_EXTENDED:
                    continue

                # Recalculate stop and targets from actual entry
                actual_risk    = entry_px - signal["stop"]
                if actual_risk <= 0:
                    continue

                open_trade = {
                    "setup":         signal["setup"],
                    "entry_date":    df.index[i + 1],
                    "entry":         round(entry_px, 2),
                    "stop":          round(signal["stop"], 2),
                    "original_stop": round(signal["stop"], 2),
                    "target_1r":     round(entry_px + actual_risk, 2),
                    "target_2r":     round(entry_px + 2 * actual_risk, 2),
                    "shares":        shares,
                    "trading_days":  0,
                    "half_exited":   False,
                    "market_state":  state,
                }

                if verbose:
                    print(f"  SIGNAL {signal['setup']} | {symbol} | {date.date()} | "
                          f"Entry ₹{entry_px:.0f} | Stop ₹{signal['stop']:.0f} | "
                          f"Target ₹{open_trade['target_2r']:.0f}")

    if verbose:
        print(f"\nSkipped stocks (insufficient data): {skipped_stocks}")

    return pd.DataFrame(all_trades)
