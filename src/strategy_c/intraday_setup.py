"""
Strategy C — Intraday setup detection (15-min candles).

Pattern: Momentum Pullback to Rising EMA
─────────────────────────────────────────
Stock is already trending (ADX ≥ 25 confirmed by daily filter).
During the day it pulls back 2–10 candles toward the rising 20-period EMA
on LOW volume (buyers stepping aside, not sellers dumping).
When price breaks back above the pullback high → signal fires.

Entry zone  : trigger close  →  trigger close × 1.015  (1.5% wide)
Valid for   : 45 minutes (3 candles) — covers your delay window
Stop        : lowest low of the pullback − 0.25% buffer
Target      : entry + 2 × risk  (2:1 R:R)
Trail       : every morning move stop to previous day's low

Why this works vs Setup S failure:
  Setup S used 0.5×ATR stop → typically 0.75–1.5% → inside intraday noise band.
  This setup uses the actual SWING LOW of the pullback as stop — a real chart level.
  If that level breaks, the pullback has failed. That's a meaningful signal.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import yfinance as yf
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .indicators import ema as calc_ema, rsi as calc_rsi
from .config import PARAMS

IST = pytz.timezone("Asia/Kolkata")


def fetch_intraday(symbol: str) -> pd.DataFrame | None:
    """
    Fetch the last 5 days of 15-min candles for a symbol.
    Returns clean OHLCV DataFrame with IST-aware index, or None on failure.
    """
    try:
        df = yf.download(
            symbol,
            interval=PARAMS["intraday_interval"],
            period="5d",
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty or len(df) < 20:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        # Convert index to IST
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)
        return df
    except Exception:
        return None


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema20"]   = calc_ema(df["Close"], PARAMS["ema_period_intraday"])
    df["rsi14"]   = calc_rsi(df["Close"], PARAMS["rsi_period_intraday"])
    df["vol_avg"] = df["Volume"].rolling(20).mean()
    return df


def detect(df: pd.DataFrame, meta: dict) -> dict | None:
    """
    Detect the pullback-to-EMA pattern on intraday 15-min candles.

    Args:
        df   : 15-min OHLCV DataFrame with IST index (from fetch_intraday)
        meta : candidate dict from daily_filter (symbol, sector, adx, etc.)

    Returns:
        signal dict if pattern is detected, else None.
    """
    p = PARAMS

    if len(df) < p["ema_period_intraday"] + p["pullback_max_candles"] + 5:
        return None

    df = _add_indicators(df)
    df.dropna(inplace=True)
    if len(df) < 25:
        return None

    # ── Isolate today's candles ───────────────────────────────────────────────
    now_ist   = datetime.now(IST)
    today_str = now_ist.date()
    today_df  = df[df.index.date == today_str].copy()

    if len(today_df) < 5:
        return None

    last_idx = len(today_df) - 1
    last     = today_df.iloc[last_idx]

    # ── EMA must be rising on intraday chart ──────────────────────────────────
    ema_now  = float(today_df["ema20"].iloc[-1])
    ema_3ago = float(today_df["ema20"].iloc[max(0, last_idx - 3)])
    if ema_now <= ema_3ago:
        return None  # intraday trend is flat or down

    # ── Scan backwards for pullback ───────────────────────────────────────────
    # A pullback is a run of candles where the Low came NEAR or touched the EMA,
    # and High was declining (downward drift toward EMA).
    # We scan from last_idx - 1 backwards to find when the pullback started.

    pullback_end   = last_idx - 1   # the candle just before the trigger
    pullback_start = None
    touch_found    = False

    for j in range(pullback_end, max(pullback_end - p["pullback_max_candles"], -1), -1):
        if j < 0 or j >= len(today_df):
            break
        candle      = today_df.iloc[j]
        ema_at_j    = float(today_df["ema20"].iloc[j])
        # Check if this candle's Low came within ema_touch_pct of EMA
        proximity   = (float(candle["Low"]) - ema_at_j) / ema_at_j
        if abs(proximity) <= p["ema_touch_pct"]:
            touch_found    = True
            pullback_start = j
            # Keep walking back to find where the pullback actually started
        elif touch_found:
            # We've gone past where the EMA was touched — stop here
            break

    if not touch_found or pullback_start is None:
        return None

    pullback_len = pullback_end - pullback_start + 1
    if pullback_len < p["pullback_min_candles"]:
        return None

    pullback_candles = today_df.iloc[pullback_start: pullback_end + 1]

    # ── Before pullback: price must have been ABOVE EMA ──────────────────────
    # (validates this is a pullback in an uptrend, not a continuation of a downtrend)
    if pullback_start > 0:
        pre_candle  = today_df.iloc[pullback_start - 1]
        ema_pre     = float(today_df["ema20"].iloc[pullback_start - 1])
        if float(pre_candle["Close"]) <= ema_pre:
            return None

    # ── Trigger: last candle closes above the pullback high ───────────────────
    pullback_high = float(pullback_candles["High"].max())
    last_close    = float(last["Close"])
    if last_close <= pullback_high:
        return None   # hasn't broken out of the pullback yet

    # ── Last candle must close above EMA (confirmed bounce) ──────────────────
    if last_close < ema_now:
        return None

    # ── RSI check on PULLBACK candles, not on signal candle ──────────────────
    # Signal candle is a breakout — RSI naturally spikes. Check RSI during the dip.
    pullback_rsi_mean = float(today_df["rsi14"].iloc[pullback_start:pullback_end].mean())
    if not (p["rsi_pullback_min"] <= pullback_rsi_mean <= p["rsi_pullback_max"]):
        return None
    current_rsi = float(last["rsi14"])
    if current_rsi > 80:   # only reject if extremely overbought on signal candle
        return None

    # ── Volume: pullback must have dried up ──────────────────────────────────
    overall_vol_avg = float(df["vol_avg"].iloc[-1])
    pullback_vol    = float(pullback_candles["Volume"].mean())
    if overall_vol_avg > 0 and pullback_vol > p["pullback_vol_ratio_max"] * overall_vol_avg:
        return None   # too much volume during pullback → distribution, not accumulation

    # ── Trigger candle itself should have above-average volume ────────────────
    # (confirms buyers came back, not just a low-volume bounce)
    trigger_vol = float(last["Volume"])
    if overall_vol_avg > 0 and trigger_vol < 0.8 * overall_vol_avg:
        return None   # trigger is also weak volume — not convincing

    # ── Compute entry, stop, target ───────────────────────────────────────────
    entry       = last_close
    swing_low   = float(pullback_candles["Low"].min())
    stop        = swing_low * (1 - p["stop_buffer_pct"])

    risk_pct    = (entry - stop) / entry
    if risk_pct > p["max_stop_pct"]:
        return None   # stop too wide — can't reach 2R in 5 days realistically
    if risk_pct < p["min_stop_pct"]:
        return None   # stop inside noise band — will get stopped by a tick

    risk_per_share  = entry - stop
    target          = entry + p["target_rr"] * risk_per_share
    entry_high      = entry * (1 + p["entry_range_pct"])   # upper bound of entry zone

    # ── Position sizing (same ₹1,000 risk as Strategy A) ─────────────────────
    shares  = int(p["max_risk_inr"] / risk_per_share)
    capital = shares * entry
    if capital > p["max_capital_inr"]:
        shares  = int(p["max_capital_inr"] / entry)
    if shares <= 0:
        return None

    actual_risk = shares * risk_per_share

    return {
        # identity
        "symbol":            meta["symbol"],
        "sector":            meta["sector"],
        "season_score":      meta["season_score"],
        "signal_time":       str(last.name),

        # entry zone (covers the delay window)
        "entry_low":         round(entry, 2),
        "entry_high":        round(entry_high, 2),
        "entry_valid_min":   p["entry_valid_minutes"],

        # risk management
        "stop":              round(stop, 2),
        "swing_low":         round(swing_low, 2),
        "target":            round(target, 2),
        "risk_per_share":    round(risk_per_share, 2),
        "risk_pct":          round(risk_pct * 100, 2),
        "rr_ratio":          p["target_rr"],

        # position
        "shares":            shares,
        "capital_required":  round(shares * entry, 0),
        "actual_risk_inr":   round(actual_risk, 0),

        # context (shown in Telegram alert)
        "ema20_15m":         round(ema_now, 2),
        "rsi14_15m":         round(current_rsi, 1),
        "adx_daily":         round(meta["adx"], 1),
        "rs_3m_pct":         meta["rs_3m_pct"],
        "pullback_candles":  pullback_len,
        "pullback_high":     round(pullback_high, 2),
    }
