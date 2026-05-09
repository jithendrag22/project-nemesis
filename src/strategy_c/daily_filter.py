"""
Strategy C — Daily pre-market filter.
Runs once at ~9:00 AM IST. Produces a candidate list for intraday scanning.

Filters applied (all from validated Strategy A insights, NOT the Strategy A code):
  1. Sector whitelist (16 sectors with positive expectancy)
  2. Seasonality score ≥ 45  (skip Very Weak sector-months)
  3. Price > SMA50 AND > SMA200  (Stage 2 — stock is in an uptrend)
  4. SMA50 is rising  (trend is accelerating, not topping)
  5. Price within 20% of 52-week high  (near the leading edge)
  6. Avg daily turnover ≥ ₹10Cr  (F&O liquidity, can execute ₹50k easily)
  7. RS vs Nifty ≥ +10% over 63 days  (stock outperforming the market)
  8. ADX(14) ≥ 25  (trend has real strength, not sideways chop)
  9. Stock up ≥ 1% in last 5 days  (already in motion, not stalled)
"""

from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.downloader import load_universe, load_stock, load_nifty
from src.enhancements.seasonality_boost import score as season_score

from .indicators import sma, adx as calc_adx, rs_vs_index
from .config import SECTOR_WHITELIST, PARAMS


def screen_universe(
    as_of_date: pd.Timestamp | None = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Screen the F&O universe. Returns candidate list for intraday scanner.
    Each candidate is a dict with symbol, sector, and pre-computed daily values.
    """
    if as_of_date is None:
        import pytz
        from datetime import datetime
        as_of_date = pd.Timestamp(datetime.now(pytz.timezone("Asia/Kolkata")).date())

    universe = load_universe()
    nifty_df = load_nifty()
    nifty_df.index = pd.to_datetime(nifty_df.index)

    candidates = []
    skipped    = {"no_data": 0, "sector": 0, "season": 0, "stage2": 0,
                  "rs": 0, "adx": 0, "motion": 0, "liquidity": 0}

    for _, row in universe.iterrows():
        sector = row.get("sector", "Unknown")
        symbol = row["symbol"]

        # ── 1. Sector whitelist ───────────────────────────────────────────────
        if sector not in SECTOR_WHITELIST:
            skipped["sector"] += 1
            continue

        # ── 2. Seasonality ───────────────────────────────────────────────────
        ss = season_score(sector, as_of_date.month)
        if ss < PARAMS["seasonality_min_score"]:
            skipped["season"] += 1
            continue

        # ── Load daily data ──────────────────────────────────────────────────
        df = load_stock(symbol)
        if df is None or len(df) < 260:
            skipped["no_data"] += 1
            continue
        df.index = pd.to_datetime(df.index)
        df = df[df.index <= as_of_date]
        if len(df) < 200:
            skipped["no_data"] += 1
            continue

        close = df["Close"]
        high  = df["High"]
        price = float(close.iloc[-1])

        # ── 3 & 4. Stage 2 ───────────────────────────────────────────────────
        sma50_s  = sma(close, 50)
        sma200_s = sma(close, 200)
        sma50_now  = float(sma50_s.iloc[-1])
        sma200_now = float(sma200_s.iloc[-1])

        if price <= sma50_now or price <= sma200_now:
            skipped["stage2"] += 1
            continue
        if sma50_now <= float(sma50_s.iloc[-21]):   # SMA50 must be rising vs 20 days ago
            skipped["stage2"] += 1
            continue

        # ── 5. Near 52-week high ─────────────────────────────────────────────
        high_52w = float(high.rolling(252).max().iloc[-1])
        if price < high_52w * (1 - PARAMS["near_52w_high_pct"] / 100):
            skipped["stage2"] += 1
            continue

        # ── 6. Liquidity ─────────────────────────────────────────────────────
        avg_turnover_cr = float((close * df["Volume"]).rolling(20).mean().iloc[-1]) / 1e7
        if avg_turnover_cr < PARAMS["min_turnover_cr"]:
            skipped["liquidity"] += 1
            continue

        # ── 7. RS vs Nifty ───────────────────────────────────────────────────
        rs = rs_vs_index(close, nifty_df["Close"], days=63)
        if rs < PARAMS["min_rs_pct"]:
            skipped["rs"] += 1
            continue

        # ── 8. ADX ───────────────────────────────────────────────────────────
        adx_series = calc_adx(df[["High", "Low", "Close"]], period=14)
        adx_val    = float(adx_series.iloc[-1])
        if pd.isna(adx_val) or adx_val < PARAMS["min_adx_daily"]:
            skipped["adx"] += 1
            continue

        # ── 9. In motion — up ≥1% in last 5 days ────────────────────────────
        if len(close) < 6:
            skipped["motion"] += 1
            continue
        recent_move = (price - float(close.iloc[-6])) / float(close.iloc[-6])
        if recent_move < PARAMS["min_recent_move_pct"]:
            skipped["motion"] += 1
            continue

        candidates.append({
            "symbol":        symbol,
            "sector":        sector,
            "price":         round(price, 2),
            "sma50":         round(sma50_now, 2),
            "sma200":        round(sma200_now, 2),
            "high_52w":      round(high_52w, 2),
            "rs_3m_pct":     round(rs * 100, 1),
            "adx":           round(adx_val, 1),
            "season_score":  round(ss, 1),
            "recent_move_pct": round(recent_move * 100, 1),
            "turnover_cr":   round(avg_turnover_cr, 1),
        })

    if verbose:
        total = len(universe)
        print(f"\n{'─'*55}")
        print(f"Daily pre-filter  —  {as_of_date.date()}")
        print(f"{'─'*55}")
        print(f"Universe         : {total} stocks")
        print(f"Sector excluded  : {skipped['sector']}")
        print(f"Season weak      : {skipped['season']}")
        print(f"No/short data    : {skipped['no_data']}")
        print(f"Stage 2 fail     : {skipped['stage2']}")
        print(f"Liquidity fail   : {skipped['liquidity']}")
        print(f"RS fail          : {skipped['rs']}")
        print(f"ADX fail         : {skipped['adx']}")
        print(f"Not in motion    : {skipped['motion']}")
        print(f"{'─'*55}")
        print(f"Candidates today : {len(candidates)}")
        print(f"{'─'*55}")
        if candidates:
            print(f"\n{'Symbol':<22} {'Sector':<22} {'ADX':>5} {'RS%':>6} {'Season':>7} {'Move%':>6}")
            print(f"{'─'*70}")
            for c in sorted(candidates, key=lambda x: x["adx"], reverse=True):
                print(f"{c['symbol']:<22} {c['sector']:<22} {c['adx']:>5.1f} "
                      f"{c['rs_3m_pct']:>+6.1f} {c['season_score']:>6.0f}% "
                      f"{c['recent_move_pct']:>+5.1f}%")

    return candidates
