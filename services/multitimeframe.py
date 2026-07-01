"""Multi-timeframe analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

from services.indicators import compute_institutional_indicators

TIMEFRAMES = {
    "1m": ("5d", "1m"),
    "5m": ("5d", "5m"),
    "15m": ("5d", "15m"),
    "1h": ("1mo", "1h"),
    "4h": ("3mo", "1h"),  # resampled from 1h
    "1d": ("1y", "1d"),
    "1wk": ("2y", "1wk"),
}


@dataclass
class TimeframeAnalysis:
    timeframe: str
    trend: str  # bullish | bearish | neutral
    rsi: float
    macd_signal: str
    above_vwap: bool
    adx: float
    score: float  # -100 to 100
    summary: str


@dataclass
class MultiTimeframeResult:
    analyses: Dict[str, TimeframeAnalysis] = field(default_factory=dict)
    alignment_score: float = 0.0
    dominant_trend: str = "neutral"
    summary: str = ""


def _fetch_tf(symbol: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[cols].dropna(subset=["Close"])
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


def _resample_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    if df_1h.empty:
        return df_1h
    return df_1h.resample("4h").agg({
        "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
    }).dropna()


def _analyze_df(df: pd.DataFrame, tf: str) -> Optional[TimeframeAnalysis]:
    if df.empty or len(df) < 30:
        return None
    df = compute_institutional_indicators(df)
    row = df.iloc[-1]
    close = float(row["Close"])
    rsi = float(row.get("RSI", 50) or 50)
    adx = float(row.get("ADX", 20) or 20)
    ema9 = float(row.get("EMA_9", close) or close)
    ema50 = float(row.get("EMA_50", close) or close)
    vwap = float(row.get("VWAP", close) or close)
    macd_hist = float(row.get("MACD_Hist", 0) or 0)

    score = 0.0
    if close > ema50:
        score += 25
    if close > ema9:
        score += 15
    if close > vwap:
        score += 15
    if macd_hist > 0:
        score += 20
    if 40 < rsi < 65:
        score += 10
    if adx > 25:
        score += 15
    if close < ema50:
        score -= 25
    if close < vwap:
        score -= 15
    if macd_hist < 0:
        score -= 20
    if rsi > 70:
        score -= 10
    if rsi < 30:
        score += 10

    if score > 20:
        trend = "bullish"
    elif score < -20:
        trend = "bearish"
    else:
        trend = "neutral"

    macd_sig = "bullish" if macd_hist > 0 else "bearish" if macd_hist < 0 else "neutral"
    return TimeframeAnalysis(
        timeframe=tf, trend=trend, rsi=rsi, macd_signal=macd_sig,
        above_vwap=close > vwap, adx=adx, score=max(-100, min(100, score)),
        summary=f"{tf}: {trend.upper()} RSI={rsi:.0f} ADX={adx:.0f}",
    )


def analyze_multitimeframe(symbol: str, timeframes: Optional[List[str]] = None) -> MultiTimeframeResult:
    tfs = timeframes or ["15m", "1h", "1d", "1wk"]
    result = MultiTimeframeResult()
    scores = []

    for tf in tfs:
        cfg = TIMEFRAMES.get(tf)
        if not cfg:
            continue
        period, interval = cfg
        df = _fetch_tf(symbol, period, interval)
        if tf == "4h" and interval == "1h":
            df = _resample_4h(df)
        analysis = _analyze_df(df, tf)
        if analysis:
            result.analyses[tf] = analysis
            scores.append(analysis.score)

    if scores:
        avg = sum(scores) / len(scores)
        result.alignment_score = avg
        bullish = sum(1 for a in result.analyses.values() if a.trend == "bullish")
        bearish = sum(1 for a in result.analyses.values() if a.trend == "bearish")
        if bullish > bearish:
            result.dominant_trend = "bullish"
        elif bearish > bullish:
            result.dominant_trend = "bearish"
        else:
            result.dominant_trend = "neutral"
        result.summary = f"MTF alignment {avg:.0f}/100 — {result.dominant_trend} ({bullish}B/{bearish}S/{len(scores)-bullish-bearish}N)"
    else:
        result.summary = "Insufficient multi-timeframe data"
    return result
