"""Market regime detection."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MarketRegime:
    regime: str  # bull_trend | bear_trend | range | high_volatility | low_volatility
    confidence: float
    adx: float
    volatility_pct: float
    trend_strength: float
    recommended_strategies: list
    summary: str


def detect_regime(df: pd.DataFrame) -> MarketRegime:
    if df.empty or len(df) < 50:
        return MarketRegime("range", 0, 0, 0, 0, ["vwap_momentum"], "Insufficient data for regime detection")

    row = df.iloc[-1]
    close = float(row["Close"])
    adx = float(row.get("ADX", 20) or 20)
    vol = float(row.get("Volatility_20", 15) or 15)
    trend = float(row.get("Trend_Strength", 0) or 0)
    sma50 = float(row.get("SMA_50", close) or close)
    sma200 = float(row.get("SMA_200", close) or close)

    if vol > 35:
        regime = "high_volatility"
        strategies = ["breakout", "pullback"]
    elif vol < 12:
        regime = "low_volatility"
        strategies = ["vwap_momentum", "pullback"]
    elif adx > 25 and close > sma50 > sma200:
        regime = "bull_trend"
        strategies = ["vwap_momentum", "breakout"]
    elif adx > 25 and close < sma50 < sma200:
        regime = "bear_trend"
        strategies = ["breakout", "pullback"]
    else:
        regime = "range"
        strategies = ["pullback", "vwap_momentum"]

    conf = min(100, adx * 2 + abs(trend))
    return MarketRegime(
        regime=regime, confidence=conf, adx=adx, volatility_pct=vol,
        trend_strength=trend, recommended_strategies=strategies,
        summary=f"Regime: {regime} (ADX={adx:.0f}, vol={vol:.1f}%, trend={trend:.1f}%)",
    )
