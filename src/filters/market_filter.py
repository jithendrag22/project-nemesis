import pandas as pd


def get_market_state(nifty: pd.DataFrame, version: str = "B") -> pd.Series:
    """
    Returns a daily Series with values: 'bull', 'neutral', 'bear'
    for each trading date, based on the chosen filter version.

    version A: Nifty above 50-day SMA
    version B: Nifty above 50-day AND 200-day SMA  (default)
    version C: Nifty above 50, 150, 200-day SMA, all rising
    """
    n = nifty.copy()
    n["sma50"]  = n["Close"].rolling(50).mean()
    n["sma150"] = n["Close"].rolling(150).mean()
    n["sma200"] = n["Close"].rolling(200).mean()
    n["sma200_rising"] = n["sma200"] > n["sma200"].shift(20)

    # Distribution day tracking: close down >0.2% on higher volume
    n["dist_day"] = (
        (n["Close"].pct_change() < -0.002) &
        (n["Volume"] > n["Volume"].shift(1))
    ).astype(int)
    n["dist_days_3w"] = n["dist_day"].rolling(15).sum()  # 15 trading days ≈ 3 weeks

    if version == "A":
        bull_cond = n["Close"] > n["sma50"]
    elif version == "B":
        bull_cond = (n["Close"] > n["sma50"]) & (n["Close"] > n["sma200"])
    elif version == "C":
        bull_cond = (
            (n["Close"] > n["sma50"]) &
            (n["Close"] > n["sma150"]) &
            (n["Close"] > n["sma200"]) &
            n["sma200_rising"]
        )
    else:
        raise ValueError(f"Unknown market filter version: {version}")

    # Distribution day override: 6+ days in 3 weeks → bear regardless
    bear_override = n["dist_days_3w"] >= 6

    # 4-5 distribution days → neutral (apply stricter rules)
    neutral_override = (n["dist_days_3w"] >= 4) & (~bear_override)

    state = pd.Series("bear", index=n.index)
    state[bull_cond] = "bull"
    state[bull_cond & neutral_override] = "neutral"
    state[bear_override] = "bear"

    return state
