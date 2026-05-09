"""
Strategy C — 3-year intraday backtest on 1-hour candles (May 2023 – May 2026).

Flow for each trading day D:
  Morning  → update trailing stops to previous day's low
  9:30 AM  → run daily filter → get candidates (Stage 2, RS≥10%, ADX≥25, seasonality)
  Each 1h candle → detect pullback-to-EMA pattern for each candidate
  Signal   → entry at next candle's open (within entry_range_pct, or skip if too extended)
  Exit     → stop hit intraday / target hit / trailing stop / Day 5 hard exit at 15:00

Why 1-hour candles:
  - yfinance provides ~3 years of hourly history (vs 60 days for 15-min)
  - Less noisy than 15-min — fewer false pullback signals
  - Wider entry window (2 hours vs 45 min) — better for delayed manual execution
  - Stop is still chart-based (swing low of pullback), not ATR
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import date, time as dtime, datetime

import numpy as np
import pandas as pd
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.downloader import load_universe, load_stock, load_nifty
from src.filters.market_filter import get_market_state
from src.enhancements.seasonality_boost import score as season_score

from .indicators import ema as calc_ema, rsi as calc_rsi, adx as calc_adx, sma, rs_vs_index
from .data_intraday import load_all_hourly, load_nifty_hourly
from .config import SECTOR_WHITELIST

IST = pytz.timezone("Asia/Kolkata")

# ── Parameters for 1-hour candles ────────────────────────────────────────────
BT = {
    # Daily filters (same validated params)
    "min_rs_pct":            0.10,
    "min_adx_daily":         25,
    "near_52w_high_pct":     20,
    "min_turnover_cr":       10,
    "seasonality_min_score": 45.0,

    # Hourly pattern detection
    "ema_period":            20,      # EMA(20) on 1h = 20 hours ≈ 4 trading days
    "rsi_period":            14,
    "pullback_min_candles":  2,
    "pullback_max_candles":  8,       # 8 hours ≈ 1.5 trading days
    # EMA touch: Low must reach within 0.5% ABOVE EMA or dip below it.
    "ema_touch_upper_pct":   0.005,   # Low <= EMA * 1.005 to count as touch
    "rsi_pb_min":            35,
    "rsi_pb_max":            65,
    "pullback_vol_ratio":    0.80,

    # Path A improvements (research-driven)
    "max_adx_daily":         45,      # cap: ADX > 45 = overextended, pullback → correction
    "signal_vol_min_ratio":  1.5,     # signal candle volume >= 1.5x average (all lit. agrees)
    "pullback_sma50_floor":  True,    # pullback Low must not breach daily 50-SMA
    "sma50_floor_buffer":    0.015,   # allow 1.5% below 50-SMA before rejecting
    # Skip months that are consistently losing across all backtest runs.
    # Jul (monsoon/low-vol chop), Sep (FII outflows/expiry), Dec (year-end illiquidity).
    "skip_months":           {7, 9, 12},

    # Entry and risk
    "stop_buffer_pct":       0.0025,
    "max_stop_pct":          0.06,    # 1h stops: up to 6%
    "min_stop_pct":          0.004,
    "entry_range_pct":       0.015,   # 1.5% entry zone width
    "target_rr":             2.0,
    "max_risk_inr":          1_000,
    "max_capital_inr":       50_000,

    # Trade management
    "hard_exit_days":        5,
    "slippage_pct":          0.001,
    "cost_per_trade":        100,
    "max_gap_pct":           0.015,   # gap at entry candle open
}

MAX_RISK    = BT["max_risk_inr"]
MAX_CAPITAL = BT["max_capital_inr"]


# ── Pre-compute daily filter pass/fail for each stock × day ──────────────────

def _build_daily_filter_cache(
    daily_stocks: dict[str, pd.DataFrame],
    nifty_daily: pd.DataFrame,
    trading_days: list[date],
    sectors: dict[str, str],
) -> dict[str, list[date]]:
    """
    Returns {symbol: [list of dates where it passes all daily filters]}.
    Faster than checking every stock every day inline.
    """
    cache: dict[str, list[date]] = {}

    for symbol, df in daily_stocks.items():
        sector = sectors.get(symbol, "Unknown")
        if sector not in SECTOR_WHITELIST:
            continue

        close = df["Close"]
        high  = df["High"]

        sma50_s    = sma(close, 50)
        sma200_s   = sma(close, 200)
        sma50_20_s = sma50_s.shift(20)
        high52w_s  = high.rolling(252).max()
        turn_s     = (close * df["Volume"]).rolling(20).mean() / 1e7
        nifty_aln  = nifty_daily["Close"].reindex(df.index, method="ffill")
        rs_s       = close.pct_change(63) - nifty_aln.pct_change(63)
        adx_s      = calc_adx(df[["High", "Low", "Close"]], 14)

        df_ind = pd.DataFrame({
            "close": close, "sma50": sma50_s, "sma200": sma200_s,
            "sma50_20": sma50_20_s, "high52w": high52w_s,
            "turnover": turn_s, "rs": rs_s, "adx": adx_s,
        }).dropna()

        passing: list[date] = []

        for d in trading_days:
            ts = pd.Timestamp(d)
            # Use data as-of the previous day's close (no lookahead)
            subset = df_ind[df_ind.index < ts]
            if subset.empty:
                continue
            row = subset.iloc[-1]

            price = float(row["close"])
            if price <= float(row["sma50"]) or price <= float(row["sma200"]):
                continue
            if float(row["sma50"]) <= float(row["sma50_20"]):
                continue
            if price < float(row["high52w"]) * (1 - BT["near_52w_high_pct"] / 100):
                continue
            if float(row["turnover"]) < BT["min_turnover_cr"]:
                continue
            if float(row["rs"]) < BT["min_rs_pct"]:
                continue
            adx_val = float(row["adx"])
            if pd.isna(adx_val) or adx_val < BT["min_adx_daily"]:
                continue
            if adx_val > BT["max_adx_daily"]:   # overextended — pullbacks become corrections
                continue
            ss = season_score(sector, ts.month)
            if ss < BT["seasonality_min_score"]:
                continue

            passing.append(d)

        if passing:
            cache[symbol] = passing

    return cache


# ── Pattern detection on 1-hour candles ──────────────────────────────────────

def _add_indicators_1h(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema20"]   = calc_ema(df["Close"], BT["ema_period"])
    df["rsi14"]   = calc_rsi(df["Close"], BT["rsi_period"])
    df["vol_avg"] = df["Volume"].rolling(20).mean()
    return df


def _detect_1h(df: pd.DataFrame, i: int, daily_sma50: float = 0.0) -> dict | None:
    """
    Detect pullback-to-EMA on 1-hour candles at bar index i.

    Path A improvements applied:
      A1. Signal candle volume >= 1.5x average (Minervini, Weinstein, IBD, Cooper: mandatory)
      A2. Pullback Low must not breach daily 50-SMA (Weinstein: pullback, not breakdown)
      A3. Entry still requires close > FULL pullback high (stronger breakout confirmation
          than Cooper's prior-bar-only trigger, which works on daily but is too loose on 1h)
    """
    p = BT
    if i < p["ema_period"] + p["pullback_max_candles"] + 3:
        return None

    ema_now  = float(df["ema20"].iloc[i])
    ema_3ago = float(df["ema20"].iloc[i - 3])
    vol_avg  = float(df["vol_avg"].iloc[i])
    price    = float(df["Close"].iloc[i])

    if ema_now <= ema_3ago:
        return None

    # ── Find pullback ─────────────────────────────────────────────────────────
    pullback_start  = None
    touch_found     = False
    touch_threshold = 1.0 + p["ema_touch_upper_pct"]

    for j in range(i - 1, max(i - p["pullback_max_candles"] - 1, 0), -1):
        candle   = df.iloc[j]
        ema_at_j = float(df["ema20"].iloc[j])
        if float(candle["Low"]) <= ema_at_j * touch_threshold:
            touch_found    = True
            pullback_start = j
        elif touch_found:
            break

    if not touch_found or pullback_start is None:
        return None

    pullback_len = i - pullback_start
    if pullback_len < p["pullback_min_candles"]:
        return None

    pullback = df.iloc[pullback_start:i]

    # Before pullback: price must have been above EMA (dip, not continuation of downtrend)
    if pullback_start > 0:
        pre_close = float(df["Close"].iloc[pullback_start - 1])
        pre_ema   = float(df["ema20"].iloc[pullback_start - 1])
        if pre_close <= pre_ema:
            return None

    # ── A2: Pullback must not breach daily 50-SMA (Weinstein) ────────────────
    if daily_sma50 > 0 and p["pullback_sma50_floor"]:
        pb_low = float(pullback["Low"].min())
        if pb_low < daily_sma50 * (1 - p["sma50_floor_buffer"]):
            return None

    # RSI during pullback (not on signal candle — breakouts naturally spike RSI)
    pb_rsi = float(df["rsi14"].iloc[pullback_start:i].mean())
    if not (p["rsi_pb_min"] <= pb_rsi <= p["rsi_pb_max"]):
        return None

    if float(df["rsi14"].iloc[i]) > 80:
        return None

    # Volume must dry up during pullback
    if vol_avg > 0:
        pb_vol = float(pullback["Volume"].mean())
        if pb_vol > p["pullback_vol_ratio"] * vol_avg:
            return None

    # ── A1: Signal candle volume >= 1.5x average ─────────────────────────────
    signal_vol = float(df["Volume"].iloc[i])
    if vol_avg > 0 and signal_vol < p["signal_vol_min_ratio"] * vol_avg:
        return None

    # ── A3: Close must break above FULL pullback high AND be above EMA ────────
    pullback_high = float(pullback["High"].max())
    if price <= pullback_high or price < ema_now:
        return None

    # ── Stop and risk ─────────────────────────────────────────────────────────
    swing_low = float(pullback["Low"].min())
    stop      = swing_low * (1 - p["stop_buffer_pct"])
    risk_pct  = (price - stop) / price

    if risk_pct > p["max_stop_pct"] or risk_pct < p["min_stop_pct"]:
        return None

    return {
        "entry_signal":     price,
        "stop":             stop,
        "risk_per_share":   price - stop,
        "risk_pct":         risk_pct,
        "pullback_candles": pullback_len,
        "pullback_high":    pullback_high,
    }


# ── Main backtest ─────────────────────────────────────────────────────────────

def run(verbose: bool = False) -> pd.DataFrame:
    print("Loading data...")

    # Daily data
    universe = load_universe()
    sectors  = {row["symbol"]: row.get("sector", "Unknown") for _, row in universe.iterrows()}

    nifty_daily = load_nifty()
    nifty_daily.index = pd.to_datetime(nifty_daily.index)
    market_states = get_market_state(nifty_daily, version="B")

    daily_stocks: dict[str, pd.DataFrame] = {}
    for _, row in universe.iterrows():
        if row.get("sector", "Unknown") not in SECTOR_WHITELIST:
            continue
        df = load_stock(row["symbol"])
        if df is not None and len(df) >= 260:
            df.index = pd.to_datetime(df.index)
            daily_stocks[row["symbol"]] = df

    # Precompute daily SMA50 series per stock (for pullback floor check in _detect_1h)
    daily_sma50_series: dict[str, pd.Series] = {}
    for sym, df_d in daily_stocks.items():
        if len(df_d) >= 50:
            daily_sma50_series[sym] = sma(df_d["Close"], 50)

    # Hourly data
    hourly_stocks = load_all_hourly()
    nifty_hourly  = load_nifty_hourly()

    if nifty_hourly is None:
        print("ERROR: Nifty hourly data not found. Run download first.")
        return pd.DataFrame()

    # Add indicators to hourly data
    print(f"Adding indicators to {len(hourly_stocks)} stocks...")
    for sym in list(hourly_stocks.keys()):
        hourly_stocks[sym] = _add_indicators_1h(hourly_stocks[sym])

    # Trading days in backtest window
    all_hours   = nifty_hourly.index
    start_date  = all_hours[0].date()
    end_date    = all_hours[-1].date()
    trading_days = sorted({ts.date() for ts in all_hours})

    print(f"Backtest window: {start_date} → {end_date}  ({len(trading_days)} trading days)")

    # Build daily filter cache
    print("Pre-computing daily filter cache...")
    filter_cache = _build_daily_filter_cache(
        daily_stocks, nifty_daily, trading_days, sectors
    )
    total_candidates = sum(len(v) for v in filter_cache.values())
    print(f"  {len(filter_cache)} stocks have at least 1 passing day "
          f"({total_candidates} total stock×day passes)")

    # Build fast lookup: date → set of passing symbols
    date_to_candidates: dict[date, set[str]] = {}
    for sym, days in filter_cache.items():
        if sym not in hourly_stocks:
            continue
        for d in days:
            date_to_candidates.setdefault(d, set()).add(sym)

    # ── Simulation ────────────────────────────────────────────────────────────
    all_trades: list[dict]      = []
    open_trades: dict[str, dict]= {}   # symbol → trade
    pending_entry: dict[str, dict] = {}  # symbol → signal (waiting for next candle)

    prev_day: date | None = None
    prev_day_lows: dict[str, float] = {}

    for ts in all_hours:
        current_date = ts.date()
        current_time = ts.time()

        # ── New day: update trailing stops ────────────────────────────────────
        if current_date != prev_day:
            # Previous day's low for each open trade
            if prev_day is not None:
                for sym, trade in open_trades.items():
                    if sym in hourly_stocks:
                        day_mask = hourly_stocks[sym].index.date == prev_day
                        day_df   = hourly_stocks[sym][day_mask]
                        if not day_df.empty:
                            pd_low = float(day_df["Low"].min())
                            if pd_low > trade["stop"]:
                                trade["stop"] = pd_low
                                trade["trail_updates"] = trade.get("trail_updates", 0) + 1

                # Expire pending entries from yesterday
                for sym in list(pending_entry.keys()):
                    if pending_entry[sym].get("signal_date") != prev_day:
                        del pending_entry[sym]

            # Market state for this day
            day_ts = pd.Timestamp(current_date)
            state  = market_states.reindex([day_ts], method="ffill").iloc[0] \
                     if day_ts in market_states.index or True else "bear"
            try:
                state = market_states.asof(day_ts)
            except Exception:
                state = "bear"

            prev_day = current_date

        # Only scan during market hours (9:15–15:15 IST)
        if not (dtime(9, 15) <= current_time <= dtime(15, 15)):
            continue

        # ── Process pending entries ───────────────────────────────────────────
        for sym in list(pending_entry.keys()):
            sig = pending_entry[sym]
            if sym in open_trades:
                del pending_entry[sym]
                continue

            if sym not in hourly_stocks:
                del pending_entry[sym]
                continue

            hourly_df = hourly_stocks[sym]
            if ts not in hourly_df.index:
                continue

            candle       = hourly_df.loc[ts]
            open_price   = float(candle["Open"])
            entry_high   = sig["entry_signal"] * (1 + BT["entry_range_pct"])

            # Gap check: if today is a new day and open gaps too much
            gap = (open_price - sig["entry_signal"]) / sig["entry_signal"]
            if gap > BT["max_gap_pct"] or open_price > entry_high:
                del pending_entry[sym]   # too extended — skip
                continue

            # Enter trade
            entry_px     = open_price * (1 + BT["slippage_pct"])
            actual_risk  = entry_px - sig["stop"]
            if actual_risk <= 0 or (actual_risk / entry_px) > BT["max_stop_pct"]:
                del pending_entry[sym]
                continue

            shares = int(MAX_RISK / actual_risk)
            if shares * entry_px > MAX_CAPITAL:
                shares = int(MAX_CAPITAL / entry_px)
            if shares <= 0:
                del pending_entry[sym]
                continue

            open_trades[sym] = {
                "symbol":          sym,
                "sector":          sectors.get(sym, "Unknown"),
                "entry_date":      current_date,
                "entry_time":      str(ts),
                "entry":           round(entry_px, 2),
                "stop":            round(sig["stop"], 2),
                "stop_initial":    round(sig["stop"], 2),
                "target":          round(entry_px + BT["target_rr"] * actual_risk, 2),
                "shares":          shares,
                "trading_days":    0,
                "market_state":    sig.get("market_state", "bull"),
                "season_score":    sig.get("season_score", 50.0),
                "rs_vs_nifty":     sig.get("rs_vs_nifty", 0.0),
                "adx_at_signal":   sig.get("adx_at_signal", 0.0),
                "pullback_candles":sig.get("pullback_candles", 2),
                "nifty_entry":     sig.get("nifty_at_signal", 0.0),
                "trail_updates":   0,
                "last_processed_date": current_date,
            }
            del pending_entry[sym]

        # ── Check exits for open trades ───────────────────────────────────────
        for sym in list(open_trades.keys()):
            trade = open_trades[sym]

            # Increment trading_days once per new day
            if trade.get("last_processed_date") != current_date:
                trade["trading_days"] += 1
                trade["last_processed_date"] = current_date

            if sym not in hourly_stocks or ts not in hourly_stocks[sym].index:
                continue

            candle = hourly_stocks[sym].loc[ts]
            lo, hi, op = float(candle["Low"]), float(candle["High"]), float(candle["Open"])

            exit_price = exit_reason = None

            if op <= trade["stop"]:
                exit_price  = op
                exit_reason = "stop_gap_down"
            elif lo <= trade["stop"]:
                exit_price  = trade["stop"]
                exit_reason = "stop"
            elif hi >= trade["target"]:
                exit_price  = trade["target"]
                exit_reason = "target_2r"
            elif trade["trading_days"] >= BT["hard_exit_days"] and current_time >= dtime(15, 0):
                exit_price  = float(candle["Close"])
                exit_reason = "hard_time_exit"

            if exit_price is not None:
                pnl = trade["shares"] * (exit_price - trade["entry"]) - BT["cost_per_trade"]

                nifty_exit = 0.0
                if ts in nifty_hourly.index:
                    nifty_exit = float(nifty_hourly.loc[ts, "Close"])
                nifty_ret = ((nifty_exit - trade["nifty_entry"]) / trade["nifty_entry"]
                             if trade["nifty_entry"] > 0 else 0.0)

                all_trades.append({
                    "symbol":          sym,
                    "sector":          trade["sector"],
                    "entry_date":      trade["entry_date"],
                    "exit_date":       current_date,
                    "entry_time":      trade["entry_time"],
                    "exit_time":       str(ts),
                    "trading_days":    trade["trading_days"],
                    "entry":           trade["entry"],
                    "stop_initial":    trade["stop_initial"],
                    "stop_final":      trade["stop"],
                    "target":          trade["target"],
                    "exit_price":      round(exit_price, 2),
                    "exit_reason":     exit_reason,
                    "shares":          trade["shares"],
                    "pnl":             round(pnl, 2),
                    "r_multiple":      round(pnl / MAX_RISK, 3),
                    "win":             pnl > 0,
                    "market_state":    trade["market_state"],
                    "season_score":    trade["season_score"],
                    "rs_vs_nifty":     trade["rs_vs_nifty"],
                    "adx_at_signal":   trade["adx_at_signal"],
                    "pullback_candles":trade["pullback_candles"],
                    "trail_updates":   trade["trail_updates"],
                    "nifty_return_pct":round(nifty_ret * 100, 2),
                    "nifty_green":     nifty_ret > 0,
                })
                del open_trades[sym]

        # ── Look for new signals ──────────────────────────────────────────────
        candidates = date_to_candidates.get(current_date, set())
        if not candidates:
            continue

        # Skip months with consistent losses (seasonal filter)
        if current_date.month in BT["skip_months"]:
            continue

        # Market state check
        try:
            day_state = market_states.asof(pd.Timestamp(current_date))
        except Exception:
            day_state = "bear"
        if day_state not in ("bull", "neutral"):
            continue

        for sym in candidates:
            if sym in open_trades or sym in pending_entry:
                continue
            if sym not in hourly_stocks:
                continue

            hourly_df = hourly_stocks[sym]
            mask = hourly_df.index <= ts
            h_sub = hourly_df[mask]
            if len(h_sub) < BT["ema_period"] + BT["pullback_max_candles"] + 3:
                continue

            last_i = len(h_sub) - 1

            # Get daily SMA50 for floor check inside _detect_1h
            d_sma50 = 0.0
            if sym in daily_sma50_series:
                s50_lookup = daily_sma50_series[sym]
                s50_sub    = s50_lookup[s50_lookup.index < pd.Timestamp(current_date)]
                if not s50_sub.empty and not pd.isna(s50_sub.iloc[-1]):
                    d_sma50 = float(s50_sub.iloc[-1])

            sig = _detect_1h(h_sub, last_i, daily_sma50=d_sma50)
            if sig is None:
                continue

            # Get Nifty price at signal
            nifty_at_signal = 0.0
            if ts in nifty_hourly.index:
                nifty_at_signal = float(nifty_hourly.loc[ts, "Close"])

            # Get ADX and RS from daily for context
            adx_val = 0.0
            rs_val  = 0.0
            if sym in daily_stocks:
                ddf     = daily_stocks[sym]
                ddf_sub = ddf[ddf.index < pd.Timestamp(current_date)]
                if len(ddf_sub) >= 65:
                    adx_s  = calc_adx(ddf_sub[["High","Low","Close"]], 14)
                    adx_val = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else 0.0
                    nifty_aln = nifty_daily["Close"].reindex(ddf_sub.index, method="ffill")
                    rs_val = float(
                        (ddf_sub["Close"].pct_change(63) - nifty_aln.pct_change(63)).iloc[-1]
                    ) * 100 if len(ddf_sub) >= 65 else 0.0

            ss = season_score(sectors.get(sym, "Unknown"), current_date.month)

            sig.update({
                "signal_date":    current_date,
                "market_state":   day_state,
                "season_score":   round(ss, 1),
                "rs_vs_nifty":    round(rs_val, 1),
                "adx_at_signal":  round(adx_val, 1),
                "nifty_at_signal":nifty_at_signal,
            })
            pending_entry[sym] = sig

            if verbose:
                print(f"  Signal: {sym:<18} {ts}  "
                      f"Entry ≈ ₹{sig['entry_signal']:.0f}  "
                      f"Stop ₹{sig['stop']:.0f}  "
                      f"PB {sig['pullback_candles']}h")

    return pd.DataFrame(all_trades)
