"""
Setup S — Short-term momentum burst (1-5 day hold).

Pattern: 3-5 day tight consolidation → breakout on volume → enter next day.
Stop: 0.5 × ATR14 below entry (≈0.75-1.5% on NSE F&O stocks).
Target: 1.0 × ATR14 above entry → natural 1:2 R:R, reachable in 1-3 days.

Distinct from Setup A (which uses 5-15 day bases and base-low stops that
require weeks to hit 2R). This setup is designed for 1-5 day resolution.
"""

import pandas as pd


def detect(df: pd.DataFrame, idx: int, params: dict) -> dict | None:
    base_min    = params.get("short_base_days_min", 3)
    base_max    = params.get("short_base_days_max", 5)
    depth_max   = params.get("short_base_depth_pct", 5.0) / 100
    vol_min     = params.get("short_vol_ratio_min", 1.5)
    min_day_gain = params.get("short_min_day_gain_pct", 1.5) / 100

    if idx < base_max + 20:
        return None

    today = df.iloc[idx]

    # ── Uptrend: above 50 and 200 SMA ────────────────────────────────────────
    if today["Close"] <= today["sma50"] or today["Close"] <= today["sma200"]:
        return None

    # ── Breakout candle strength: today must be a strong up day ──────────────
    day_gain = (today["Close"] - today["Open"]) / today["Open"]
    if day_gain < min_day_gain:
        return None

    if today["vol_ratio"] < vol_min:
        return None

    # ── ATR-based stop and target ─────────────────────────────────────────────
    atr = today.get("atr14", None)
    if atr is None or atr <= 0:
        return None

    # ── Scan multiple base lengths ────────────────────────────────────────────
    for base_len in range(base_min, base_max + 1):
        base = df.iloc[idx - base_len: idx]

        base_high = base["High"].max()
        base_low  = base["Low"].min()
        depth     = (base_high - base_low) / base_high

        if depth > depth_max:
            continue

        # Must actually break above the base
        if today["Close"] <= base_high:
            continue

        # Volume must be declining inside the base (contracting = accumulation)
        half = max(1, base_len // 2)
        vol_first = base["Volume"].iloc[:half].mean()
        vol_last  = base["Volume"].iloc[half:].mean()
        if vol_last >= vol_first:
            continue

        # ── Signal ───────────────────────────────────────────────────────────
        entry = today["Close"]
        stop  = entry - 0.5 * atr       # tight: ~0.75-1.5% below entry
        risk  = entry - stop

        if risk <= 0:
            continue

        target_1r = entry + risk         # 1:1
        target_2r = entry + 2 * risk    # 1:2

        return {
            "setup":          "S_short_momentum",
            "entry":          round(entry, 2),
            "stop":           round(stop, 2),
            "target_1r":      round(target_1r, 2),
            "target_2r":      round(target_2r, 2),
            "risk_per_share": round(risk, 2),
            "rr_ratio":       2.0,
            "base_days":      base_len,
            "base_depth_pct": round(depth * 100, 2),
            "vol_ratio":      round(today["vol_ratio"], 2),
            "day_gain_pct":   round(day_gain * 100, 2),
            "atr14":          round(atr, 2),
        }

    return None
