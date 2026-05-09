"""
Strategy C — Daily-candle approximation backtest (2015–2024, 9 years).

Why daily candles instead of 15-min:
  yfinance only provides ~2 years of 15-min history.
  We simulate the same pattern (pullback to rising EMA on low volume → bounce)
  on daily OHLC bars to get 9 years of signal history.

What changes vs the live scanner:
  - EMA is the daily EMA20 instead of 15-min EMA20
  - "Pullback" = 2-5 daily candles dipping toward the EMA (not 2-10 candles × 15min)
  - EMA touch threshold widened to 3% (daily swings are larger than 15-min swings)
  - Entry = next day's open + slippage (simulates receiving an EOD alert)
  - Trailing SL: each day, stop moves up to previous day's low

What stays identical:
  - All daily filters: Stage 2, RS ≥10%, ADX ≥25, sector whitelist, seasonality
  - 2:1 R:R, ₹1,000 risk, ₹50k max capital
  - Day 5 hard exit
  - Same market filter (Version B — bull/neutral only)
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

from .indicators import ema as calc_ema, rsi as calc_rsi, adx as calc_adx, sma
from .config import SECTOR_WHITELIST, PARAMS

# ── Params adjusted for daily bars ───────────────────────────────────────────
BT = {
    **PARAMS,
    "ema_touch_pct":          0.030,   # daily: 3% (vs 1.5% on 15-min)
    "pullback_min_candles":   2,
    "pullback_max_candles":   5,       # max 5-day pullback on daily bars
    "pullback_vol_ratio_max": 0.80,
    "max_stop_pct":           0.08,    # allow up to 8% stop on daily bars
    "rsi_pullback_min":       35,
    "rsi_pullback_max":       62,
    "slippage_pct":           0.001,
    "cost_per_trade":         100,
    "max_gap_pct":            0.02,
}

MAX_RISK    = BT["max_risk_inr"]
MAX_CAPITAL = BT["max_capital_inr"]


# ── Pattern detection on daily bars ──────────────────────────────────────────

def _detect(df: pd.DataFrame, i: int) -> dict | None:
    """
    Detect pullback-to-EMA pattern at bar i on daily candles.
    Returns a signal dict or None.
    """
    if i < 35:
        return None

    price     = float(df["Close"].iloc[i])
    ema_now   = float(df["ema20"].iloc[i])
    ema_3ago  = float(df["ema20"].iloc[i - 3])
    vol_avg   = float(df["vol_ma20"].iloc[i])

    # EMA must be rising (uptrend on daily)
    if ema_now <= ema_3ago:
        return None

    # Signal day RSI: allow up to 80 (breakout days naturally have high RSI)
    # The RSI health check is done on the PULLBACK candles below, not here
    rsi_signal = float(df["rsi14"].iloc[i])
    if rsi_signal > 80:   # only skip if extremely overbought
        return None

    # ── Find pullback period ──────────────────────────────────────────────────
    pullback_start = None
    touch_found    = False

    for j in range(i - 1, max(i - BT["pullback_max_candles"] - 1, 0), -1):
        candle    = df.iloc[j]
        ema_at_j  = float(df["ema20"].iloc[j])
        proximity = (float(candle["Low"]) - ema_at_j) / ema_at_j

        if abs(proximity) <= BT["ema_touch_pct"]:
            touch_found    = True
            pullback_start = j
        elif touch_found:
            break

    if not touch_found or pullback_start is None:
        return None

    pullback_len = i - pullback_start
    if pullback_len < BT["pullback_min_candles"]:
        return None

    pullback = df.iloc[pullback_start:i]

    # Before the pullback: price must have been ABOVE EMA (confirms it's a dip, not a downtrend)
    if pullback_start > 0:
        pre_close = float(df["Close"].iloc[pullback_start - 1])
        pre_ema   = float(df["ema20"].iloc[pullback_start - 1])
        if pre_close <= pre_ema:
            return None

    # RSI during the pullback must be in healthy zone (35-62)
    # This is the right place — measures exhaustion DURING the dip, not on the breakout day
    pullback_rsi_mean = float(df["rsi14"].iloc[pullback_start:i].mean())
    if not (BT["rsi_pullback_min"] <= pullback_rsi_mean <= BT["rsi_pullback_max"]):
        return None

    # Volume must dry up during the pullback
    if vol_avg > 0:
        pb_vol = float(pullback["Volume"].mean())
        if pb_vol > BT["pullback_vol_ratio_max"] * vol_avg:
            return None

    # Signal day: close must break above all pullback highs
    pullback_high = float(pullback["High"].max())
    if price <= pullback_high:
        return None

    # Signal day: close must be above EMA (bounce confirmed)
    if price < ema_now:
        return None

    # ── Stop = swing low of pullback ──────────────────────────────────────────
    swing_low = float(pullback["Low"].min())
    stop      = swing_low * (1 - BT["stop_buffer_pct"])

    risk_pct = (price - stop) / price
    if risk_pct > BT["max_stop_pct"] or risk_pct < BT["min_stop_pct"]:
        return None

    return {
        "entry_signal":     round(price, 2),
        "stop":             round(stop, 2),
        "risk_per_share":   round(price - stop, 2),
        "pullback_candles": pullback_len,
        "pullback_high":    round(pullback_high, 2),
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
        df["ema20"]        = calc_ema(close, 20)
        df["sma50"]        = sma(close, 50)
        df["sma200"]       = sma(close, 200)
        df["sma50_20ago"]  = sma(close, 50).shift(20)
        df["rsi14"]        = calc_rsi(close, 14)
        df["adx14"]        = calc_adx(df[["High","Low","Close"]], 14)
        df["high_52w"]     = df["High"].rolling(252).max()
        df["vol_ma20"]     = df["Volume"].rolling(20).mean()
        df["turnover_ma20"]= (close * df["Volume"]).rolling(20).mean()

        nifty_aligned  = nifty_df["Close"].reindex(df.index, method="ffill")
        df["rs_3m"]    = close.pct_change(63) - nifty_aligned.pct_change(63)
        df["nifty_close"] = nifty_aligned

        df.dropna(
            subset=["ema20","sma50","sma200","adx14","rs_3m","rsi14","vol_ma20"],
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

                # Trail stop: each morning move stop to previous day's low (only up)
                if i > 0:
                    prev_low = float(df.iloc[i - 1]["Low"])
                    if prev_low > open_trade["stop"]:
                        open_trade["stop"] = prev_low

                exit_price = exit_reason = None

                # Gap down through stop at open
                if float(today["Open"]) <= open_trade["stop"]:
                    exit_price  = float(today["Open"])
                    exit_reason = "stop_gap_down"

                # Stop hit intraday
                elif float(today["Low"]) <= open_trade["stop"]:
                    exit_price  = open_trade["stop"]
                    exit_reason = "stop"

                # Target hit
                elif float(today["High"]) >= open_trade["target"]:
                    exit_price  = open_trade["target"]
                    exit_reason = "target_2r"

                # Hard exit: Day 5
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
                    nifty_ret   = (nifty_exit - nifty_entry) / nifty_entry if nifty_entry else 0

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
                        "exit_price":       exit_price,
                        "exit_reason":      exit_reason,
                        "shares":           open_trade["shares"],
                        "pnl":              round(pnl, 2),
                        "r_multiple":       round(pnl / MAX_RISK, 3),
                        "win":              pnl > 0,
                        "market_state":     open_trade["market_state"],
                        "season_score":     open_trade["season_score"],
                        "rs_vs_nifty":      open_trade["rs_vs_nifty"],
                        "adx_at_entry":     open_trade["adx_at_entry"],
                        "pullback_candles": open_trade["pullback_candles"],
                        "nifty_return_pct": round(nifty_ret * 100, 2),
                        "nifty_green":      nifty_ret > 0,
                    })
                    open_trade = None

            # ── Look for new signal ───────────────────────────────────────────
            if open_trade is None and state in ("bull", "neutral"):
                price = float(today["Close"])

                # Stage 2: price above SMA50 and SMA200, SMA50 rising
                if price <= float(today["sma50"]) or price <= float(today["sma200"]):
                    continue
                if float(today["sma50"]) <= float(today["sma50_20ago"]):
                    continue

                # Near 52-week high
                h52 = float(today["high_52w"])
                if price < h52 * (1 - BT["near_52w_high_pct"] / 100):
                    continue

                # Liquidity
                if float(today["turnover_ma20"]) / 1e7 < BT["min_turnover_cr"]:
                    continue

                # RS vs Nifty
                if float(today["rs_3m"]) < BT["min_rs_pct"]:
                    continue

                # ADX
                adx_val = float(today["adx14"])
                if pd.isna(adx_val) or adx_val < BT["min_adx_daily"]:
                    continue

                # Seasonality
                ss = season_score(sector, date.month)
                if ss < BT["seasonality_min_score"]:
                    continue

                # Detect pattern
                signal = _detect(df, i)
                if signal is None:
                    continue

                # Entry = next day's open
                if i + 1 >= len(df):
                    continue
                next_day = df.iloc[i + 1]
                entry_px = float(next_day["Open"]) * (1 + BT["slippage_pct"])

                # Gap filter
                gap = (float(next_day["Open"]) - price) / price
                if gap > BT["max_gap_pct"]:
                    continue

                # Recalculate risk from actual entry price
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
                    "entry_date":       df.index[i + 1],
                    "entry":            round(entry_px, 2),
                    "stop":             round(signal["stop"], 2),
                    "stop_initial":     round(signal["stop"], 2),
                    "target":           round(entry_px + 2 * actual_risk, 2),
                    "shares":           shares,
                    "trading_days":     0,
                    "market_state":     state,
                    "season_score":     round(ss, 1),
                    "rs_vs_nifty":      round(float(today["rs_3m"]) * 100, 1),
                    "adx_at_entry":     round(adx_val, 1),
                    "pullback_candles": signal["pullback_candles"],
                    "nifty_entry":      float(today["nifty_close"]),
                }

                if verbose:
                    print(
                        f"  C | {symbol:<18} {date.date()} → "
                        f"Entry ₹{entry_px:.0f}  Stop ₹{signal['stop']:.0f}  "
                        f"Target ₹{entry_px + 2*actual_risk:.0f}  "
                        f"ADX {adx_val:.0f}  Season {ss:.0f}%"
                    )

    if verbose:
        print(f"\nSkipped (no data): {skipped}")

    return pd.DataFrame(all_trades)
