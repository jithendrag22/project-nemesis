import pandas as pd


def detect(df: pd.DataFrame, idx: int, params: dict) -> dict | None:
    """
    Setup A — Flat Base Breakout.
    Checks conditions on the row at position `idx` in the dataframe.
    Returns a signal dict if valid, None otherwise.

    params:
        base_days_min   : int   (default 5)
        base_days_max   : int   (default 15)
        base_depth_pct  : float (default 8.0) — max % range within base
        vol_ratio_min   : float (default 1.5) — breakout vol / 20d avg
    """
    base_min  = params.get("base_days_min", 5)
    base_max  = params.get("base_days_max", 15)
    depth_max = params.get("base_depth_pct", 8.0) / 100
    vol_min   = params.get("vol_ratio_min", 1.5)

    today = df.iloc[idx]

    # Need enough history
    if idx < base_max + 5:
        return None

    # Check multiple lookback windows for a valid base
    for base_len in range(base_min, base_max + 1):
        base = df.iloc[idx - base_len: idx]

        base_high = base["High"].max()
        base_low  = base["Low"].min()
        depth     = (base_high - base_low) / base_high

        if depth > depth_max:
            continue  # base too wide, try next length

        # Volume declining inside base: last half of base avg volume
        # should be lower than first half
        half = base_len // 2
        vol_first_half = base["Volume"].iloc[:half].mean()
        vol_last_half  = base["Volume"].iloc[half:].mean()
        vol_declining  = vol_last_half < vol_first_half

        if not vol_declining:
            continue

        # Today must break above the base high
        breakout = today["Close"] > base_high

        if not breakout:
            continue

        # Volume on breakout must be high enough
        if today["vol_ratio"] < vol_min:
            continue

        # Entry is today's close; stop is the base low
        entry = today["Close"]
        stop  = base_low
        risk  = entry - stop

        if risk <= 0:
            continue

        target_1r = entry + risk       # 1:1
        target_2r = entry + (2 * risk) # 1:2

        return {
            "setup":         "A_flat_base",
            "entry":         round(entry, 2),
            "stop":          round(stop, 2),
            "target_1r":     round(target_1r, 2),
            "target_2r":     round(target_2r, 2),
            "risk_per_share": round(risk, 2),
            "rr_ratio":      round(risk / risk * 2, 1),  # always 2.0 by construction
            "base_days":     base_len,
            "base_depth_pct": round(depth * 100, 2),
            "vol_ratio":     round(today["vol_ratio"], 2),
        }

    return None
