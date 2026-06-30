"""Feature engineering for strategies and models."""

from __future__ import annotations

import pandas as pd

from config import BB_PERIOD, BB_STD, EMA_FAST, EMA_SLOW, MACD_SIGNAL, RSI_PERIOD, SMA_PERIODS

try:
    from ta.momentum import RSIIndicator
    from ta.trend import EMAIndicator, MACD, SMAIndicator
    from ta.volatility import BollingerBands
    _HAS_TA = True
except ImportError:
    _HAS_TA = False


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical features used by strategies and confidence model."""
    if df.empty:
        return df.copy()
    out = df.copy()
    close = out["Close"]
    volume = out["Volume"]

    if _HAS_TA:
        for p in SMA_PERIODS:
            out[f"SMA_{p}"] = SMAIndicator(close, window=p).sma_indicator()
        out[f"EMA_{EMA_FAST}"] = EMAIndicator(close, window=EMA_FAST).ema_indicator()
        out[f"EMA_{EMA_SLOW}"] = EMAIndicator(close, window=EMA_SLOW).ema_indicator()
        macd = MACD(close, window_slow=EMA_SLOW, window_fast=EMA_FAST, window_sign=MACD_SIGNAL)
        out["MACD"] = macd.macd()
        out["MACD_Signal"] = macd.macd_signal()
        out["MACD_Hist"] = macd.macd_diff()
        out["RSI"] = RSIIndicator(close, window=RSI_PERIOD).rsi()
        bb = BollingerBands(close, window=BB_PERIOD, window_dev=BB_STD)
        out["BB_Upper"] = bb.bollinger_hband()
        out["BB_Mid"] = bb.bollinger_mavg()
        out["BB_Lower"] = bb.bollinger_lband()
    else:
        for p in SMA_PERIODS:
            out[f"SMA_{p}"] = _sma(close, p)
        out[f"EMA_{EMA_FAST}"] = _ema(close, EMA_FAST)
        out[f"EMA_{EMA_SLOW}"] = _ema(close, EMA_SLOW)
        out["RSI"] = close.diff().pipe(lambda d: 100 - 100 / (1 + d.clip(lower=0).ewm(span=RSI_PERIOD).mean() / (-d.clip(upper=0).ewm(span=RSI_PERIOD).mean().replace(0, 1e-9))))

    # VWAP approximation (daily cumulative)
    typical = (out["High"] + out["Low"] + out["Close"]) / 3
    out["VWAP"] = (typical * volume).cumsum() / volume.cumsum().replace(0, float("nan"))
    out["Volume_SMA20"] = volume.rolling(20, min_periods=20).mean()
    out["Volume_Ratio"] = volume / out["Volume_SMA20"].replace(0, float("nan"))
    out["Momentum_10"] = close.pct_change(10) * 100
    out["ATR_14"] = (out["High"] - out["Low"]).rolling(14).mean()
    out["Above_VWAP"] = (close > out["VWAP"]).astype(int)
    return out
