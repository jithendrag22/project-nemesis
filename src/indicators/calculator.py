import pandas as pd
import numpy as np


def add_all(df: pd.DataFrame, nifty: pd.DataFrame) -> pd.DataFrame:
    """Add all required indicators to a stock dataframe."""
    df = df.copy()

    # --- Moving averages ---
    df["ema20"]  = df["Close"].ewm(span=20,  adjust=False).mean()
    df["ema50"]  = df["Close"].ewm(span=50,  adjust=False).mean()
    df["ema150"] = df["Close"].ewm(span=150, adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["sma50"]  = df["Close"].rolling(50).mean()
    df["sma200"] = df["Close"].rolling(200).mean()

    # --- ATR (14-day) ---
    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()

    # --- Volume indicators ---
    df["vol_ma20"] = df["Volume"].rolling(20).mean()
    df["vol_ratio"] = df["Volume"] / df["vol_ma20"]  # today's vol ÷ 20-day avg

    # --- 52-week high (rolling 252 trading days) ---
    df["high_52w"] = df["High"].rolling(252).max()
    df["pct_from_52w_high"] = (df["Close"] - df["high_52w"]) / df["high_52w"] * 100

    # --- Daily turnover (Close × Volume, proxy in rupees) ---
    df["turnover"] = df["Close"] * df["Volume"]

    # --- 20-day turnover average ---
    df["turnover_ma20"] = df["turnover"].rolling(20).mean()

    # --- Relative Strength vs Nifty (63 trading days ≈ 3 months) ---
    nifty_aligned = nifty["Close"].reindex(df.index, method="ffill")
    stock_ret = df["Close"].pct_change(63)
    nifty_ret = nifty_aligned.pct_change(63)
    df["rs_vs_nifty_3m"] = stock_ret - nifty_ret  # positive = outperforming

    # --- SMA50 trend: is it rising? (compare to 20 days ago) ---
    df["sma50_rising"] = df["sma50"] > df["sma50"].shift(20)

    return df
