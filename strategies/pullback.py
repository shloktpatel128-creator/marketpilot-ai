"""Pullback strategy."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from storage.schemas import StrategySignal


class PullbackStrategy(BaseStrategy):
    name = "pullback"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        if len(df) < 50 or "SMA_50" not in df.columns:
            return StrategySignal(False, "HOLD", None, None, None, 0, "Insufficient data", [], self.name)
        row = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(row["Close"])
        sma50 = float(row["SMA_50"])
        rsi = float(row.get("RSI", 50) or 50)

        uptrend = close > sma50 and float(prev["SMA_20"]) > float(prev["SMA_50"]) if "SMA_20" in df.columns else close > sma50
        if uptrend and 35 <= rsi <= 45:
            entry = close
            stop = sma50 * 0.99
            target = entry * 1.03
            rr = (target - entry) / (entry - stop) if entry > stop else 0
            return StrategySignal(
                True, "BUY", entry, stop, target, round(rr, 2),
                f"Pullback to support in uptrend (RSI {rsi:.0f}).",
                ["SMA_50", "RSI"], self.name,
            )
        downtrend = close < sma50
        if downtrend and 55 <= rsi <= 65:
            entry = close
            stop = sma50 * 1.01
            target = entry * 0.97
            rr = (entry - target) / (stop - entry) if stop > entry else 0
            return StrategySignal(
                True, "SELL", entry, stop, target, round(rr, 2),
                f"Pullback rally in downtrend (RSI {rsi:.0f}).",
                ["SMA_50", "RSI"], self.name,
            )
        return StrategySignal(False, "HOLD", close, None, None, 0, "No pullback setup.", ["SMA_50", "RSI"], self.name)
