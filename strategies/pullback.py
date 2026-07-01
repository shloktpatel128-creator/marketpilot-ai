"""Pullback — trend pullback to moving-average support/resistance."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from strategies.helpers import _f, atr_stop, build_signal, hold_signal, min_bars
from storage.schemas import StrategySignal


class PullbackStrategy(BaseStrategy):
    name = "pullback"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        debug = []
        if not min_bars(df, 50):
            return hold_signal(self.name, 0, "Need 50+ bars", ["bars<50"])

        row = df.iloc[-1]
        close = _f(row, "Close")
        sma20 = _f(row, "SMA_20", close)
        sma50 = _f(row, "SMA_50", close)
        ema20 = _f(row, "EMA_20", sma20)
        rsi = _f(row, "RSI", 50)
        adx = _f(row, "ADX", 20)

        debug.append(f"close={close:.2f} sma50={sma50:.2f} rsi={rsi:.0f} adx={adx:.0f}")

        uptrend = close > sma50 and sma20 > sma50 * 0.998
        near_support = abs(close - ema20) / ema20 < 0.015 or abs(close - sma20) / sma20 < 0.015

        if uptrend and near_support and 28 <= rsi <= 52:
            entry = close
            stop = min(sma50 * 0.985, atr_stop(df, "BUY", entry, 1.2))
            target = entry + (entry - stop) * 2.0
            conf = 55 + min(20, adx) + (10 if rsi <= 42 else 0)
            return build_signal(
                self.name, "BUY", entry, stop, target,
                f"Pullback buy in uptrend — RSI {rsi:.0f}, near EMA20/SMA20 support",
                ["SMA_50", "SMA_20", "EMA_20", "RSI", "ADX"],
                conf, invalidation=stop, debug=debug,
            )

        downtrend = close < sma50 and sma20 < sma50 * 1.002
        near_resistance = near_support

        if downtrend and near_resistance and 48 <= rsi <= 72:
            entry = close
            stop = max(sma50 * 1.015, atr_stop(df, "SELL", entry, 1.2))
            target = entry - (stop - entry) * 2.0
            conf = 55 + min(20, adx) + (10 if rsi >= 58 else 0)
            return build_signal(
                self.name, "SELL", entry, stop, target,
                f"Pullback sell in downtrend — RSI {rsi:.0f}, near EMA20/SMA20 resistance",
                ["SMA_50", "SMA_20", "EMA_20", "RSI", "ADX"],
                conf, invalidation=stop, debug=debug,
            )

        debug.append(f"uptrend={uptrend} downtrend={downtrend} near_ma={near_support}")
        return hold_signal(self.name, close, "No pullback setup", debug)
