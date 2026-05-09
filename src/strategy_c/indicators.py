"""
Standalone indicators for Strategy C intraday candles.
Separate from src/indicators/calculator.py (which is daily-data only).
All functions accept pd.Series or pd.DataFrame and return pd.Series.
"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    ADX — Average Directional Index.
    df must have columns: High, Low, Close.
    High ADX (≥25) = stock is trending strongly (up or down).
    """
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    prev_close = close.shift(1)
    prev_high  = high.shift(1)
    prev_low   = low.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    up_move   = high - prev_high
    down_move = prev_low - low

    plus_dm  = np.where((up_move > down_move)   & (up_move > 0),   up_move,   0.0)
    minus_dm = np.where((down_move > up_move)   & (down_move > 0), down_move, 0.0)

    alpha = 1.0 / period
    atr_smooth    = pd.Series(tr).ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    plus_di_s     = pd.Series(plus_dm,  index=df.index).ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    minus_di_s    = pd.Series(minus_dm, index=df.index).ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    plus_di  = 100 * plus_di_s  / atr_smooth.replace(0, np.nan)
    minus_di = 100 * minus_di_s / atr_smooth.replace(0, np.nan)

    di_sum  = (plus_di + minus_di).replace(0, np.nan)
    dx      = 100 * (plus_di - minus_di).abs() / di_sum
    adx_val = dx.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    adx_val.index = df.index
    return adx_val


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def rs_vs_index(stock_close: pd.Series, index_close: pd.Series, days: int = 63) -> float:
    """
    % excess return of stock vs index over `days` periods.
    Positive = stock outperformed Nifty.
    """
    if len(stock_close) < days or len(index_close) < days:
        return 0.0
    s   = stock_close.iloc[-days:]
    idx = index_close.reindex(s.index, method="ffill")
    if idx.iloc[0] == 0 or s.iloc[0] == 0:
        return 0.0
    return float((s.iloc[-1] / s.iloc[0]) - (idx.iloc[-1] / idx.iloc[0]))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()
