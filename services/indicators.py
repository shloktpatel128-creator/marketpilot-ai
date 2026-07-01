"""Institutional-grade technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from ta.momentum import RSIIndicator, StochRSIIndicator
    from ta.trend import ADXIndicator, EMAIndicator, MACD, SMAIndicator, PSARIndicator
    from ta.volume import ChaikinMoneyFlowIndicator, OnBalanceVolumeIndicator
    from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel
    _HAS_TA = True
except ImportError:
    _HAS_TA = False


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=max(1, n // 2)).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def _supertrend(df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> pd.DataFrame:
    hl2 = (df["High"] + df["Low"]) / 2
    atr = _atr(df["High"], df["Low"], df["Close"], period)
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(1, index=df.index)
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
        st.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]
    out = df.copy()
    out["SuperTrend"] = st
    out["SuperTrend_Dir"] = direction
    return out


def _ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    high, low, close = out["High"], out["Low"], out["Close"]
    out["Ichimoku_Tenkan"] = (high.rolling(9).max() + low.rolling(9).min()) / 2
    out["Ichimoku_Kijun"] = (high.rolling(26).max() + low.rolling(26).min()) / 2
    out["Ichimoku_SpanA"] = ((out["Ichimoku_Tenkan"] + out["Ichimoku_Kijun"]) / 2).shift(26)
    out["Ichimoku_SpanB"] = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    out["Ichimoku_Chikou"] = close.shift(-26)
    return out


def _donchian(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    out = df.copy()
    out["Donchian_High"] = out["High"].rolling(n).max()
    out["Donchian_Low"] = out["Low"].rolling(n).min()
    out["Donchian_Mid"] = (out["Donchian_High"] + out["Donchian_Low"]) / 2
    return out


def _fib_levels(df: pd.DataFrame, lookback: int = 60) -> pd.DataFrame:
    out = df.copy()
    window_high = out["High"].rolling(lookback).max()
    window_low = out["Low"].rolling(lookback).min()
    diff = window_high - window_low
    for level, pct in [("236", 0.236), ("382", 0.382), ("500", 0.5), ("618", 0.618), ("786", 0.786)]:
        out[f"Fib_{level}"] = window_high - diff * pct
    return out


def _pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    h, l, c = out["High"].shift(1), out["Low"].shift(1), out["Close"].shift(1)
    out["Pivot"] = (h + l + c) / 3
    out["Pivot_R1"] = 2 * out["Pivot"] - l
    out["Pivot_S1"] = 2 * out["Pivot"] - h
    out["Pivot_R2"] = out["Pivot"] + (h - l)
    out["Pivot_S2"] = out["Pivot"] - (h - l)
    return out


def _candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    body = (out["Close"] - out["Open"]).abs()
    upper_wick = out["High"] - out[["Open", "Close"]].max(axis=1)
    lower_wick = out[["Open", "Close"]].min(axis=1) - out["Low"]
    out["Pattern_Doji"] = (body / (out["High"] - out["Low"]).replace(0, np.nan) < 0.1).astype(int)
    out["Pattern_Hammer"] = ((lower_wick > 2 * body) & (upper_wick < body)).astype(int)
    out["Pattern_ShootingStar"] = ((upper_wick > 2 * body) & (lower_wick < body)).astype(int)
    out["Pattern_BullishEngulf"] = (
        (out["Close"] > out["Open"]) & (out["Close"].shift() < out["Open"].shift()) &
        (out["Close"] >= out["Open"].shift()) & (out["Open"] <= out["Close"].shift())
    ).astype(int)
    return out


def _anchored_vwap(df: pd.DataFrame, anchor_idx: int = 0) -> pd.Series:
    sub = df.iloc[anchor_idx:]
    typical = (sub["High"] + sub["Low"] + sub["Close"]) / 3
    vol = sub["Volume"].replace(0, np.nan)
    return (typical * vol).cumsum() / vol.cumsum()


def compute_institutional_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add full institutional indicator suite."""
    if df.empty or len(df) < 5:
        return df.copy()
    out = df.copy()
    close, high, low, volume = out["Close"], out["High"], out["Low"], out["Volume"]

    # Moving averages
    for p in [20, 50, 100, 200]:
        out[f"SMA_{p}"] = _sma(close, p)
    for p in [9, 12, 26, 50, 200]:
        out[f"EMA_{p}"] = _ema(close, p)

    # VWAP + anchored VWAP (from start of window)
    typical = (high + low + close) / 3
    out["VWAP"] = (typical * volume).cumsum() / volume.cumsum().replace(0, np.nan)
    avwap = _anchored_vwap(out, 0)
    out["Anchored_VWAP"] = avwap.reindex(out.index)

    if _HAS_TA:
        out["RSI"] = RSIIndicator(close, window=14).rsi()
        out["StochRSI"] = StochRSIIndicator(close, window=14).stochrsi()
        macd = MACD(close, window_slow=26, window_fast=12, window_sign=9)
        out["MACD"] = macd.macd()
        out["MACD_Signal"] = macd.macd_signal()
        out["MACD_Hist"] = macd.macd_diff()
        out["ATR_14"] = AverageTrueRange(high, low, close, window=14).average_true_range()
        bb = BollingerBands(close, window=20, window_dev=2)
        out["BB_Upper"], out["BB_Mid"], out["BB_Lower"] = bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
        adx = ADXIndicator(high, low, close, window=14)
        out["ADX"] = adx.adx()
        out["DI_Plus"] = adx.adx_pos()
        out["DI_Minus"] = adx.adx_neg()
        out["OBV"] = OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        out["CMF"] = ChaikinMoneyFlowIndicator(high, low, close, volume, window=20).chaikin_money_flow()
        kc = KeltnerChannel(high, low, close, window=20)
        out["Keltner_Upper"] = kc.keltner_channel_hband()
        out["Keltner_Lower"] = kc.keltner_channel_lband()
    else:
        out["RSI"] = 100 - 100 / (1 + close.diff().clip(lower=0).ewm(span=14).mean() /
                                   (-close.diff().clip(upper=0).ewm(span=14).mean().replace(0, 1e-9)))
        out["ATR_14"] = _atr(high, low, close, 14)
        out["MACD"] = _ema(close, 12) - _ema(close, 26)
        out["MACD_Signal"] = _ema(out["MACD"], 9)
        out["ADX"] = pd.Series(25.0, index=out.index)

    out = _supertrend(out)
    out = _ichimoku(out)
    out = _donchian(out)
    out = _fib_levels(out)
    out = _pivot_points(out)
    out = _candlestick_patterns(out)

    # Derived metrics
    out["Volume_SMA20"] = volume.rolling(20).mean()
    out["Volume_Ratio"] = volume / out["Volume_SMA20"].replace(0, np.nan)
    out["Momentum_10"] = close.pct_change(10) * 100
    out["Momentum_20"] = close.pct_change(20) * 100
    out["Volatility_20"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    out["Trend_Strength"] = (close - out["SMA_50"]) / out["SMA_50"].replace(0, np.nan) * 100
    out["Above_VWAP"] = (close > out["VWAP"]).astype(int)

    # Support / resistance (recent swing levels)
    out["Resistance_20"] = high.rolling(20).max()
    out["Support_20"] = low.rolling(20).min()

    return out


def latest_indicator_snapshot(df: pd.DataFrame) -> dict:
    """Extract latest indicator values as dict for storage."""
    if df.empty:
        return {}
    row = df.iloc[-1]
    keys = [c for c in df.columns if c not in ("Open", "High", "Low", "Close", "Volume")]
    snap = {}
    for k in keys:
        v = row.get(k)
        if pd.notna(v):
            try:
                snap[k] = float(v)
            except (TypeError, ValueError):
                snap[k] = str(v)
    snap["close"] = float(row["Close"])
    snap["volume"] = float(row.get("Volume", 0))
    return snap
