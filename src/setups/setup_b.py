import pandas as pd


def detect(df: pd.DataFrame, idx: int, params: dict) -> dict | None:
    """
    Setup B — Pullback to 20 EMA in uptrend.
    Returns a signal dict if valid, None otherwise.

    params:
        ema_proximity_pct : float (default 1.0) — how close to EMA counts as "touch"
        prior_advance_pct : float (default 15.0) — min % rise before pullback
        pullback_lookback : int   (default 5)   — days to look back for the pullback
    """
    ema_prox  = params.get("ema_proximity_pct", 1.0) / 100
    min_adv   = params.get("prior_advance_pct", 15.0) / 100
    lookback  = params.get("pullback_lookback", 5)

    if idx < 60:  # need enough history for prior advance check
        return None

    today     = df.iloc[idx]
    yesterday = df.iloc[idx - 1]

    # --- Uptrend: price above 50-day and 200-day SMA ---
    if today["Close"] <= today["sma50"] or today["Close"] <= today["sma200"]:
        return None

    # --- Today bounced: close above EMA20 and above yesterday's close ---
    if today["Close"] <= today["ema20"]:
        return None
    if today["Close"] <= yesterday["Close"]:
        return None

    # --- Pullback: within the last `lookback` days, price touched EMA20 ---
    pullback_window = df.iloc[idx - lookback: idx + 1]
    ema20_vals      = pullback_window["ema20"]
    low_vals        = pullback_window["Low"]

    touched_ema = any(
        abs(low - ema) / ema <= ema_prox
        for low, ema in zip(low_vals, ema20_vals)
    )

    if not touched_ema:
        return None

    # --- Volume declining during pullback ---
    pullback_vol     = pullback_window["Volume"].iloc[:-1]  # exclude today
    vol_ma           = today["vol_ma20"]
    avg_pullback_vol = pullback_vol.mean()
    vol_declining    = avg_pullback_vol < vol_ma

    if not vol_declining:
        return None

    # --- Prior advance: stock rose at least X% before this pullback ---
    # Find the low of the pullback window and compare to 20 days before that
    pre_pullback_start = df.iloc[idx - lookback - 20: idx - lookback]
    if pre_pullback_start.empty:
        return None
    prior_low  = pre_pullback_start["Low"].min()
    pullback_low = pullback_window["Low"].min()
    prior_advance = (pullback_low - prior_low) / prior_low

    if prior_advance < min_adv:
        return None

    # --- Entry, stop, target ---
    entry = today["Close"]
    # Stop below the reversal candle's low or EMA20 - 1%, whichever is lower
    stop_candidate_1 = today["Low"]
    stop_candidate_2 = today["ema20"] * (1 - ema_prox)
    stop  = min(stop_candidate_1, stop_candidate_2)
    risk  = entry - stop

    if risk <= 0:
        return None

    target_1r = entry + risk
    target_2r = entry + (2 * risk)

    return {
        "setup":          "B_ema_pullback",
        "entry":          round(entry, 2),
        "stop":           round(stop, 2),
        "target_1r":      round(target_1r, 2),
        "target_2r":      round(target_2r, 2),
        "risk_per_share": round(risk, 2),
        "rr_ratio":       2.0,
        "prior_advance_pct": round(prior_advance * 100, 2),
        "vol_ratio":      round(today["vol_ratio"], 2),
    }
