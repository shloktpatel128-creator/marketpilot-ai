"""Reversal — RSI extremes with candlestick confirmation at S/R."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from strategies.helpers import _f, atr_stop, build_signal, hold_signal, min_bars
from storage.schemas import StrategySignal


class ReversalStrategy(BaseStrategy):
    name = "reversal"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        debug = []
        if not min_bars(df, 30):
            return hold_signal(self.name, 0, "Need 30+ bars", ["bars<30"])

        row = df.iloc[-1]
        close = _f(row, "Close")
        rsi = _f(row, "RSI", 50)
        support = _f(row, "Support_20", close * 0.95)
        resistance = _f(row, "Resistance_20", close * 1.05)
        hammer = int(_f(row, "Pattern_Hammer", 0))
        engulf = int(_f(row, "Pattern_BullishEngulf", 0))
        shooting = int(_f(row, "Pattern_ShootingStar", 0))

        debug.append(f"rsi={rsi:.0f} support={support:.2f} resistance={resistance:.2f}")

        at_support = close <= support * 1.01
        if rsi <= 35 and (hammer or engulf or at_support):
            entry = close
            stop = min(support * 0.99, atr_stop(df, "BUY", entry, 1.5))
            target = entry + (entry - stop) * 2.5
            conf = 50 + (15 if rsi <= 30 else 8) + (10 if hammer or engulf else 0) + (10 if at_support else 0)
            return build_signal(
                self.name, "BUY", entry, stop, target,
                f"Reversal long — RSI oversold ({rsi:.0f})" + (" + bullish pattern" if hammer or engulf else ""),
                ["RSI", "Support_20", "Pattern_Hammer", "Pattern_BullishEngulf"],
                conf, invalidation=stop, debug=debug,
            )

        at_resistance = close >= resistance * 0.99
        if rsi >= 65 and (shooting or at_resistance):
            entry = close
            stop = max(resistance * 1.01, atr_stop(df, "SELL", entry, 1.5))
            target = entry - (stop - entry) * 2.5
            conf = 50 + (15 if rsi >= 70 else 8) + (10 if shooting else 0) + (10 if at_resistance else 0)
            return build_signal(
                self.name, "SELL", entry, stop, target,
                f"Reversal short — RSI overbought ({rsi:.0f})" + (" + bearish pattern" if shooting else ""),
                ["RSI", "Resistance_20", "Pattern_ShootingStar"],
                conf, invalidation=stop, debug=debug,
            )

        debug.append("No RSI extreme + pattern/S-R confluence")
        return hold_signal(self.name, close, "No reversal setup", debug)
