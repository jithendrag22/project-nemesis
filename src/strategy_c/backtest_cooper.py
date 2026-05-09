"""
Strategy C-B — Jeff Cooper's 5-Day Momentum Method (daily candles, 2015–2024).

Source: "Hit and Run Trading" + "The 5-Day Momentum Method" by Jeff Cooper.

Setup rules (verbatim from Cooper, adapted for NSE):
  1. Stock in top RS quartile vs Nifty (outperforming over 60 days)
  2. Stage 2 uptrend: price > 50-day MA > 200-day MA, 50-day MA rising
  3. ADX(14) between 25–45 (trend exists, not overextended)
  4. Look back 10 days: stock must have made a 10-day high recently (is in upswing)
  5. Pullback: 3–5 consecutive daily bars of LOWER CLOSES (the dip phase)
     - The pullback low must stay ABOVE the 50-day MA (dip, not breakdown)
     - Volume must dry up during the pullback (buyers stepping aside)
  6. Entry trigger Day N+1: buy if price closes above Day N's HIGH (prior bar's high)
  7. Stop: below Day N's LOW (the final pullback bar's low), with 0.25% buffer
  8. Target: entry + 2 × risk (strict 2:1)
  9. Hard exit: Day 5 at close if neither stop nor target hit

Why daily candles for Cooper:
  - Cooper wrote for daily bars. "Prior day's high" is a full 24-hour resistance level,
    not a 1-hour candle. The translation to hourly bars weakens the signal quality.
  - Daily bars give 9 years of data (vs 3 years hourly).
  - EOD alert → next morning entry: the same workflow as Strategy A.
"""

from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.downloader import load_universe, load_stock, load_nifty
from src.filters.market_filter import get_market_state
from src.enhancements.seasonality_boost import score as season_score

from .indicators import sma, adx as calc_adx, ema as calc_ema
from .config import SECTOR_WHITELIST

# ── Parameters ────────────────────────────────────────────────────────────────
BT = {
    # Universe / daily filters
    "min_rs_pct":            0.05,    # 60-day RS vs Nifty > +5%
    "min_adx":               25,
    "max_adx":               45,      # cap: >45 = overextended
    "near_52w_high_pct":     25,      # within 25% of 52-week high
    "min_turnover_cr":       10,      # ₹10Cr avg daily turnover
    "seasonality_min_score": 45.0,
    "skip_months":           {7, 9, 12},  # Jul, Sep, Dec consistently lose

    # Cooper pullback detection
    "lookback_high_days":    10,      # stock must have made a 10-day high recently
    "pullback_min_bars":     3,       # minimum 3 days of declining closes
    "pullback_max_bars":     5,       # maximum 5 days (Cooper's original window)
    "pullback_vol_ratio":    0.85,    # pullback volume < 85% of 20-day avg

    # Entry / stop / target
    "stop_buffer_pct":       0.0025,
    "max_stop_pct":          0.07,    # up to 7% stop on daily bars
    "min_stop_pct":          0.005,
    "target_rr":             2.0,
    "max_risk_inr":          1_000,
    "max_capital_inr":       50_000,

    # Trade management
    "hard_exit_days":        5,
    "slippage_pct":          0.001,
    "cost_per_trade":        100,
    "max_gap_pct":           0.02,    # reject if next-day gap > 2%
}

MAX_RISK    = BT["max_risk_inr"]
MAX_CAPITAL = BT["max_capital_inr"]


# ── Pattern detection ─────────────────────────────────────────────────────────

def _detect_cooper(df: pd.DataFrame, i: int) -> dict | None:
    """
    Detect Cooper 5-Day Momentum pullback at bar index i (the ENTRY TRIGGER day).

    Bar i = the first bar that closes ABOVE bar (i-1)'s HIGH after the pullback.
    The pullback ended at bar i-1 (lowest close in the pullback sequence).
    """
    p = BT

    if i < 50:
        return None

    # ── 1. Stock must have made a 10-day high recently (is in an upswing) ────
    lookback_window = df["High"].iloc[max(0, i - p["lookback_high_days"] - p["pullback_max_bars"]): i]
    if len(lookback_window) < p["lookback_high_days"]:
        return None
    recent_high = float(lookback_window.max())
    # The pre-pullback price should have been within 5% of that recent high
    pre_pullback_high = float(df["High"].iloc[i - p["pullback_max_bars"] - 1] if i > p["pullback_max_bars"] else df["High"].iloc[0])
    if pre_pullback_high < recent_high * 0.95:
        return None  # stock wasn't near its swing high before the pullback

    # ── 2. Find the pullback: scan backward for consecutive lower closes ──────
    pullback_end   = i - 1   # last pullback bar (the bar whose high we're breaking)
    pullback_start = None

    # Walk backward from (i-1) looking for consecutive lower closes
    # Stop when closes stop declining
    cur_close = float(df["Close"].iloc[pullback_end])
    pb_len    = 1

    for j in range(pullback_end - 1, max(pullback_end - p["pullback_max_bars"], -1), -1):
        prev_close = float(df["Close"].iloc[j])
        if prev_close > cur_close:
            break  # closes stopped declining — pullback started at j+1
        cur_close = prev_close
        pb_len   += 1

    pullback_start = pullback_end - pb_len + 1

    if pb_len < p["pullback_min_bars"]:
        return None

    pullback = df.iloc[pullback_start: pullback_end + 1]

    # ── 3. Entry trigger: close above the final pullback bar's HIGH ───────────
    # This is Cooper's exact trigger: "buy above the high of the last pullback bar"
    trigger_high = float(df["High"].iloc[pullback_end])
    entry_signal = float(df["Close"].iloc[i])   # today's close must be above trigger
    if entry_signal <= trigger_high:
        return None

    # ── 4. Pullback must stay above 50-day SMA (dip, not breakdown) ──────────
    sma50_at_pb = float(df["sma50"].iloc[pullback_end])
    pb_low      = float(pullback["Low"].min())
    if pb_low < sma50_at_pb * 0.985:
        return None

    # ── 5. Before pullback: price must have been ABOVE 50-day SMA ────────────
    if pullback_start > 0:
        pre_close = float(df["Close"].iloc[pullback_start - 1])
        pre_sma50 = float(df["sma50"].iloc[pullback_start - 1])
        if pre_close <= pre_sma50:
            return None

    # ── 6. Volume dries up during pullback ────────────────────────────────────
    vol_ma20   = float(df["vol_ma20"].iloc[i])
    pb_vol_avg = float(pullback["Volume"].mean())
    if vol_ma20 > 0 and pb_vol_avg > p["pullback_vol_ratio"] * vol_ma20:
        return None

    # ── 7. Stop and risk ──────────────────────────────────────────────────────
    stop    = pb_low * (1 - p["stop_buffer_pct"])
    risk_px = entry_signal - stop
    risk_pct = risk_px / entry_signal

    if risk_pct > p["max_stop_pct"] or risk_pct < p["min_stop_pct"]:
        return None

    return {
        "entry_signal":    round(entry_signal, 2),
        "trigger_high":    round(trigger_high, 2),
        "stop":            round(stop, 2),
        "risk_per_share":  round(risk_px, 2),
        "risk_pct":        round(risk_pct * 100, 2),
        "pullback_bars":   pb_len,
        "pullback_low":    round(pb_low, 2),
        "pullback_high":   round(float(pullback["High"].max()), 2),
    }


# ── Main backtest loop ────────────────────────────────────────────────────────

def run(
    start:   str  = "2015-01-01",
    end:     str  = "2024-12-31",
    verbose: bool = False,
) -> pd.DataFrame:

    universe = load_universe()
    nifty_df = load_nifty()
    nifty_df.index = pd.to_datetime(nifty_df.index)
    market_states  = get_market_state(nifty_df, version="B")

    all_trades: list[dict] = []
    skipped = 0

    for _, urow in universe.iterrows():
        sector = urow.get("sector", "Unknown")
        symbol = urow["symbol"]

        if sector not in SECTOR_WHITELIST:
            continue

        df = load_stock(symbol)
        if df is None or len(df) < 260:
            skipped += 1
            continue

        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= start) & (df.index <= end)].copy()
        if len(df) < 100:
            skipped += 1
            continue

        # ── Indicators ────────────────────────────────────────────────────────
        close = df["Close"]
        df["sma50"]        = sma(close, 50)
        df["sma200"]       = sma(close, 200)
        df["sma50_20ago"]  = sma(close, 50).shift(20)
        df["ema20"]        = calc_ema(close, 20)
        df["adx14"]        = calc_adx(df[["High","Low","Close"]], 14)
        df["high_52w"]     = df["High"].rolling(252).max()
        df["vol_ma20"]     = df["Volume"].rolling(20).mean()
        df["turnover_ma20"]= (close * df["Volume"]).rolling(20).mean()

        nifty_aln  = nifty_df["Close"].reindex(df.index, method="ffill")
        df["rs_60d"]      = close.pct_change(60) - nifty_aln.pct_change(60)
        df["nifty_close"] = nifty_aln

        df.dropna(
            subset=["sma50","sma200","adx14","rs_60d","vol_ma20","ema20"],
            inplace=True,
        )
        if len(df) < 50:
            continue

        ms = market_states.reindex(df.index, method="ffill")

        open_trade: dict | None = None

        for i in range(len(df)):
            date  = df.index[i]
            today = df.iloc[i]
            state = ms.iloc[i] if i < len(ms) else "bear"

            # ── Manage open trade ─────────────────────────────────────────────
            if open_trade is not None:
                td = open_trade["trading_days"] + 1
                open_trade["trading_days"] = td

                # Trail stop: each day, move stop to previous day's LOW (only upward)
                if i > 0:
                    prev_low = float(df.iloc[i - 1]["Low"])
                    if prev_low > open_trade["stop"]:
                        open_trade["stop"] = prev_low

                exit_price = exit_reason = None

                if float(today["Open"]) <= open_trade["stop"]:
                    exit_price  = float(today["Open"])
                    exit_reason = "stop_gap_down"
                elif float(today["Low"]) <= open_trade["stop"]:
                    exit_price  = open_trade["stop"]
                    exit_reason = "stop"
                elif float(today["High"]) >= open_trade["target"]:
                    exit_price  = open_trade["target"]
                    exit_reason = "target_2r"
                elif td >= BT["hard_exit_days"]:
                    exit_price  = float(today["Close"])
                    exit_reason = "hard_time_exit"

                if exit_price is not None:
                    pnl = (
                        open_trade["shares"] * (exit_price - open_trade["entry"])
                        - BT["cost_per_trade"]
                    )
                    nifty_entry = open_trade["nifty_entry"]
                    nifty_exit  = float(today["nifty_close"])
                    nifty_ret   = (
                        (nifty_exit - nifty_entry) / nifty_entry if nifty_entry else 0
                    )

                    all_trades.append({
                        "symbol":           symbol,
                        "sector":           sector,
                        "entry_date":       open_trade["entry_date"],
                        "exit_date":        date,
                        "trading_days":     td,
                        "entry":            open_trade["entry"],
                        "stop_initial":     open_trade["stop_initial"],
                        "stop_final":       open_trade["stop"],
                        "target":           open_trade["target"],
                        "exit_price":       round(exit_price, 2),
                        "exit_reason":      exit_reason,
                        "shares":           open_trade["shares"],
                        "pnl":              round(pnl, 2),
                        "r_multiple":       round(pnl / MAX_RISK, 3),
                        "win":              pnl > 0,
                        "market_state":     open_trade["market_state"],
                        "season_score":     open_trade["season_score"],
                        "rs_vs_nifty":      open_trade["rs_vs_nifty"],
                        "adx_at_entry":     open_trade["adx_at_entry"],
                        "pullback_candles": open_trade["pullback_bars"],
                        "nifty_return_pct": round(nifty_ret * 100, 2),
                        "nifty_green":      nifty_ret > 0,
                    })
                    open_trade = None

            # ── Skip bad months ───────────────────────────────────────────────
            if date.month in BT["skip_months"]:
                continue

            # ── Look for new signal ───────────────────────────────────────────
            if open_trade is None and state in ("bull", "neutral"):
                price = float(today["Close"])

                # Stage 2: price > SMA50 > SMA200, SMA50 rising
                if price <= float(today["sma50"]) or price <= float(today["sma200"]):
                    continue
                if float(today["sma50"]) <= float(today["sma50_20ago"]):
                    continue

                # ADX window
                adx_val = float(today["adx14"])
                if pd.isna(adx_val) or adx_val < BT["min_adx"] or adx_val > BT["max_adx"]:
                    continue

                # Near 52-week high
                h52 = float(today["high_52w"])
                if price < h52 * (1 - BT["near_52w_high_pct"] / 100):
                    continue

                # Liquidity
                if float(today["turnover_ma20"]) / 1e7 < BT["min_turnover_cr"]:
                    continue

                # RS vs Nifty (60-day)
                if float(today["rs_60d"]) < BT["min_rs_pct"]:
                    continue

                # Seasonality
                ss = season_score(sector, date.month)
                if ss < BT["seasonality_min_score"]:
                    continue

                # Cooper pattern
                signal = _detect_cooper(df, i)
                if signal is None:
                    continue

                # Entry = next day's open + slippage (EOD alert → morning entry)
                if i + 1 >= len(df):
                    continue
                next_day = df.iloc[i + 1]
                entry_px = float(next_day["Open"]) * (1 + BT["slippage_pct"])

                # Gap filter
                gap = (float(next_day["Open"]) - price) / price
                if abs(gap) > BT["max_gap_pct"]:
                    continue

                # Recalculate risk from actual entry
                actual_risk = entry_px - signal["stop"]
                if actual_risk <= 0:
                    continue
                risk_pct_actual = actual_risk / entry_px
                if risk_pct_actual > BT["max_stop_pct"]:
                    continue

                shares = int(MAX_RISK / actual_risk)
                if shares * entry_px > MAX_CAPITAL:
                    shares = int(MAX_CAPITAL / entry_px)
                if shares <= 0:
                    continue

                open_trade = {
                    "entry_date":    df.index[i + 1],
                    "entry":         round(entry_px, 2),
                    "stop":          round(signal["stop"], 2),
                    "stop_initial":  round(signal["stop"], 2),
                    "target":        round(entry_px + BT["target_rr"] * actual_risk, 2),
                    "shares":        shares,
                    "trading_days":  0,
                    "market_state":  state,
                    "season_score":  round(ss, 1),
                    "rs_vs_nifty":   round(float(today["rs_60d"]) * 100, 1),
                    "adx_at_entry":  round(adx_val, 1),
                    "pullback_bars": signal["pullback_bars"],
                    "nifty_entry":   float(today["nifty_close"]),
                }

                if verbose:
                    print(
                        f"  Cooper | {symbol:<18} {date.date()}  "
                        f"PB {signal['pullback_bars']}d  "
                        f"Entry ₹{entry_px:.0f}  Stop ₹{signal['stop']:.0f}  "
                        f"Target ₹{entry_px + BT['target_rr'] * actual_risk:.0f}  "
                        f"ADX {adx_val:.0f}"
                    )

    if verbose:
        print(f"\nSkipped (no data): {skipped}")

    return pd.DataFrame(all_trades)
