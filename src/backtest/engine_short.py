"""
Short-term backtest engine — Setup S (1-5 day momentum trades).

Key differences from engine.py (long-term):
- Uses setup_short.detect instead of setup_a/setup_b
- Hard exit on Day 5 (no time-stop — either target or stop should hit in 5 days)
- Full exit at 2:1 target (no partial exit — ATR-based targets are tight enough)
- Sector seasonality soft boost: recorded on every trade, used for ranking alerts
- Same filters: Stage 2, RS≥10%, sector whitelist, Market B
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.downloader import load_universe, load_stock, load_nifty
from indicators.calculator import add_all
from filters.market_filter import get_market_state
from filters.stage2_filter import passes_stage2
from setups.setup_short import detect as detect_short

MAX_RISK       = 1_000
MAX_CAPITAL    = 50_000
SLIPPAGE_PCT   = 0.001
COST_PER_TRADE = 100
MAX_GAP_PCT    = 0.02      # tighter than long-term: 2% gap limit (fast setups gap more)
MAX_EXTENDED   = 0.03      # skip if >3% above signal entry at open
HARD_STOP_DAYS = 5         # force exit day 5 — this is a short-term system

GOOD_SECTORS = {
    "Utilities", "FMCG", "Pharma", "Cement", "Consumer Durables",
    "IT", "Real Estate", "Electronics", "Healthcare", "Consumer",
    "Insurance", "Consumer Electricals", "Mining", "Capital Goods",
    "Auto Ancillary", "Energy",
}

DEFAULT_PARAMS = {
    "market_filter_version": "B",
    "near_52w_high_pct":     15,
    "min_turnover_cr":       10,
    "min_rs_pct":            0.10,
    # short setup
    "short_base_days_min":   3,
    "short_base_days_max":   5,
    "short_base_depth_pct":  5.0,
    "short_vol_ratio_min":   1.5,
    "short_min_day_gain_pct": 1.5,
}


def _load_seasonality() -> pd.DataFrame:
    path = Path(__file__).parent.parent.parent / "data" / "sector_seasonality.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _season_score(seasonality: pd.DataFrame, sector: str, month: int) -> float:
    """Return beat-Nifty % for this sector-month (0–100). 50 = neutral."""
    if seasonality.empty:
        return 50.0
    row = seasonality[(seasonality["sector"] == sector) & (seasonality["month"] == month)]
    if row.empty:
        return 50.0
    return float(row["beat_nifty_pct"].iloc[0])


def run_backtest(
    params: dict = None,
    start: str = "2015-01-01",
    end:   str = "2024-12-31",
    verbose: bool = False,
) -> pd.DataFrame:

    if params is None:
        params = DEFAULT_PARAMS.copy()
    else:
        p = DEFAULT_PARAMS.copy(); p.update(params); params = p

    universe    = load_universe()
    nifty       = load_nifty()
    nifty.index = pd.to_datetime(nifty.index)
    market_states = get_market_state(nifty, version=params["market_filter_version"])
    seasonality   = _load_seasonality()

    all_trades    = []
    skipped       = 0

    for _, row in universe.iterrows():
        sector = row.get("sector", "Unknown")
        if sector not in GOOD_SECTORS:
            continue

        symbol = row["symbol"]
        df = load_stock(symbol)
        if df is None or len(df) < 252:
            skipped += 1; continue

        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= start) & (df.index <= end)]
        if len(df) < 252:
            skipped += 1; continue

        df = add_all(df, nifty)
        df.dropna(
            subset=["sma200","ema20","vol_ma20","high_52w","rs_vs_nifty_3m","atr14"],
            inplace=True,
        )
        if len(df) < 50:
            continue

        ms = market_states.reindex(df.index, method="ffill")
        open_trade = None

        for i in range(len(df)):
            date  = df.index[i]
            today = df.iloc[i]
            state = ms.iloc[i] if i < len(ms) else "bear"

            # ── Manage open trade ─────────────────────────────────────────────
            if open_trade is not None:
                td = open_trade["trading_days"] + 1
                open_trade["trading_days"] = td
                exit_price = exit_reason = None

                # Gap down through stop at open
                if today["Open"] <= open_trade["stop"]:
                    exit_price  = today["Open"]
                    exit_reason = "stop_gap_down"

                # Stop hit intraday
                elif today["Low"] <= open_trade["stop"]:
                    exit_price  = open_trade["stop"]
                    exit_reason = "stop"

                # 2:1 target hit — full exit (no partial in short-term system)
                elif today["High"] >= open_trade["target_2r"]:
                    exit_price  = open_trade["target_2r"]
                    exit_reason = "target_2r"

                # Hard exit: day 5
                elif td >= HARD_STOP_DAYS:
                    exit_price  = today["Close"]
                    exit_reason = "hard_time_exit"

                if exit_price is not None:
                    pnl = (open_trade["shares"] * (exit_price - open_trade["entry"])
                           - COST_PER_TRADE)
                    all_trades.append({
                        "symbol":         symbol,
                        "sector":         sector,
                        "setup":          open_trade["setup"],
                        "entry_date":     open_trade["entry_date"],
                        "exit_date":      date,
                        "trading_days":   td,
                        "entry":          open_trade["entry"],
                        "stop":           open_trade["stop"],
                        "target_2r":      open_trade["target_2r"],
                        "exit_price":     exit_price,
                        "exit_reason":    exit_reason,
                        "shares":         open_trade["shares"],
                        "pnl":            round(pnl, 2),
                        "r_multiple":     round(pnl / MAX_RISK, 3),
                        "win":            pnl > 0,
                        "market_state":   open_trade["market_state"],
                        "season_score":   open_trade["season_score"],
                        "rs_vs_nifty":    open_trade["rs_vs_nifty"],
                    })
                    open_trade = None

            # ── Look for new signal ───────────────────────────────────────────
            if open_trade is None and state in ("bull", "neutral"):
                # Stage 2
                ok, _ = passes_stage2(today, params)
                if not ok:
                    continue

                # RS filter
                if today["rs_vs_nifty_3m"] < params["min_rs_pct"]:
                    continue

                # Detect short-term setup
                signal = detect_short(df, i, params)
                if signal is None:
                    continue

                rps = signal["risk_per_share"]
                if rps <= 0:
                    continue

                shares = int(MAX_RISK / rps)
                if shares * signal["entry"] > MAX_CAPITAL:
                    shares = int(MAX_CAPITAL / signal["entry"])
                if shares <= 0:
                    continue

                if i + 1 >= len(df):
                    continue

                next_day = df.iloc[i + 1]
                entry_px = next_day["Open"] * (1 + SLIPPAGE_PCT)

                gap = (next_day["Open"] - today["Close"]) / today["Close"]
                if gap > MAX_GAP_PCT:
                    continue
                if (entry_px - signal["entry"]) / signal["entry"] > MAX_EXTENDED:
                    continue

                actual_risk = entry_px - signal["stop"]
                if actual_risk <= 0:
                    continue

                season_score = _season_score(seasonality, sector, date.month)

                open_trade = {
                    "setup":       signal["setup"],
                    "entry_date":  df.index[i + 1],
                    "entry":       round(entry_px, 2),
                    "stop":        round(signal["stop"], 2),
                    "target_2r":   round(entry_px + 2 * actual_risk, 2),
                    "shares":      shares,
                    "trading_days": 0,
                    "market_state": state,
                    "season_score": season_score,
                    "rs_vs_nifty":  round(today["rs_vs_nifty_3m"] * 100, 1),
                }

                if verbose:
                    trend = "↑" if season_score >= 60 else ("↓" if season_score <= 40 else "→")
                    print(f"  {signal['setup']} | {symbol} ({sector}) | {date.date()} | "
                          f"Entry ₹{entry_px:.0f} | Stop ₹{signal['stop']:.0f} | "
                          f"Target ₹{open_trade['target_2r']:.0f} | "
                          f"Season {season_score:.0f}% {trend} | RS {open_trade['rs_vs_nifty']}%")

    if verbose:
        print(f"\nSkipped: {skipped}")

    return pd.DataFrame(all_trades)
