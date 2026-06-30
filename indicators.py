"""
Technical indicator calculations.

Uses the `ta` library when available; falls back to manual pandas
implementations so the app still runs without it.
"""

from __future__ import annotations

import pandas as pd

from config import (
    BB_PERIOD,
    BB_STD,
    EMA_FAST,
    EMA_SLOW,
    MACD_SIGNAL,
    RSI_PERIOD,
    SMA_PERIODS,
)

try:
    from ta.trend import EMAIndicator, MACD, SMAIndicator
    from ta.momentum import RSIIndicator
    from ta.volatility import BollingerBands

    _HAS_TA = True
except ImportError:
    _HAS_TA = False


def _sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series: pd.Series, length: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _macd(
    close: pd.Series,
    fast: int = EMA_FAST,
    slow: int = EMA_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(
    close: pd.Series,
    length: int = BB_PERIOD,
    std: float = BB_STD,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = _sma(close, length)
    rolling_std = close.rolling(window=length, min_periods=length).std()
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    return upper, mid, lower


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to an OHLCV DataFrame.

    Expects columns: Open, High, Low, Close, Volume.
    Returns a new DataFrame with indicator columns appended.
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    close = out["Close"]
    volume = out["Volume"]

    # --- Moving averages ---
    if _HAS_TA:
        for period in SMA_PERIODS:
            out[f"SMA_{period}"] = SMAIndicator(close, window=period).sma_indicator()
        out[f"EMA_{EMA_FAST}"] = EMAIndicator(close, window=EMA_FAST).ema_indicator()
        out[f"EMA_{EMA_SLOW}"] = EMAIndicator(close, window=EMA_SLOW).ema_indicator()

        macd_ind = MACD(close, window_slow=EMA_SLOW, window_fast=EMA_FAST, window_sign=MACD_SIGNAL)
        out["MACD"] = macd_ind.macd()
        out["MACD_Signal"] = macd_ind.macd_signal()
        out["MACD_Hist"] = macd_ind.macd_diff()

        out["RSI"] = RSIIndicator(close, window=RSI_PERIOD).rsi()

        bb_ind = BollingerBands(close, window=BB_PERIOD, window_dev=BB_STD)
        out["BB_Upper"] = bb_ind.bollinger_hband()
        out["BB_Mid"] = bb_ind.bollinger_mavg()
        out["BB_Lower"] = bb_ind.bollinger_lband()
    else:
        for period in SMA_PERIODS:
            out[f"SMA_{period}"] = _sma(close, period)
        out[f"EMA_{EMA_FAST}"] = _ema(close, EMA_FAST)
        out[f"EMA_{EMA_SLOW}"] = _ema(close, EMA_SLOW)

        macd_line, signal_line, histogram = _macd(close)
        out["MACD"] = macd_line
        out["MACD_Signal"] = signal_line
        out["MACD_Hist"] = histogram

        out["RSI"] = _rsi(close, RSI_PERIOD)

        upper, mid, lower = _bollinger(close)
        out["BB_Upper"] = upper
        out["BB_Mid"] = mid
        out["BB_Lower"] = lower

    # --- Volume trend: current volume vs 20-day average ---
    vol_sma = volume.rolling(window=20, min_periods=20).mean()
    out["Volume_SMA20"] = vol_sma
    out["Volume_Ratio"] = volume / vol_sma.replace(0, float("nan"))

    # --- Price momentum: % change over 10 bars ---
    out["Momentum_10"] = close.pct_change(periods=10) * 100

    # --- Trend direction: price above/below SMA 50 ---
    if "SMA_50" in out.columns:
        out["Above_SMA50"] = (close > out["SMA_50"]).astype(int)
    else:
        out["Above_SMA50"] = 0

    return out


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Return latest indicator values as a plain dict for display."""
    if df.empty:
        return {}

    row = df.iloc[-1]
    keys = [
        "Close", "SMA_20", "SMA_50", "SMA_200",
        f"EMA_{EMA_FAST}", f"EMA_{EMA_SLOW}",
        "MACD", "MACD_Signal", "MACD_Hist",
        "RSI", "BB_Upper", "BB_Mid", "BB_Lower",
        "Volume_Ratio", "Momentum_10",
    ]
    summary = {}
    for key in keys:
        if key in df.columns and pd.notna(row.get(key)):
            summary[key] = float(row[key])
    return summary


def get_trend_interpretation(df: pd.DataFrame) -> str:
    """Plain-English trend summary from latest indicators."""
    if df.empty or len(df) < 2:
        return "Insufficient data for trend interpretation."

    row = df.iloc[-1]
    parts = []

    close = row.get("Close")
    sma20, sma50, sma200 = row.get("SMA_20"), row.get("SMA_50"), row.get("SMA_200")
    rsi = row.get("RSI")
    mom = row.get("Momentum_10")

    if pd.notna(sma20) and pd.notna(sma50):
        if sma20 > sma50:
            parts.append("Short-term trend is **bullish** (SMA 20 above SMA 50).")
        else:
            parts.append("Short-term trend is **bearish** (SMA 20 below SMA 50).")

    if pd.notna(close) and pd.notna(sma200):
        if close > sma200:
            parts.append("Price trades **above** the 200-day average — long-term uptrend intact.")
        else:
            parts.append("Price trades **below** the 200-day average — long-term pressure.")

    if pd.notna(rsi):
        if rsi >= 70:
            parts.append(f"RSI at **{rsi:.0f}** suggests overbought conditions.")
        elif rsi <= 30:
            parts.append(f"RSI at **{rsi:.0f}** suggests oversold conditions.")
        else:
            parts.append(f"RSI at **{rsi:.0f}** is in neutral territory.")

    if pd.notna(mom):
        direction = "positive" if mom > 0 else "negative"
        parts.append(f"10-period momentum is **{direction}** ({mom:+.1f}%).")

    return " ".join(parts) if parts else "Trend data unavailable."
