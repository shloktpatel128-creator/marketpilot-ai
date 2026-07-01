"""Breakout — 20-bar range expansion with volume."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from strategies.helpers import _f, build_signal, hold_signal, min_bars
from storage.schemas import StrategySignal


class BreakoutStrategy(BaseStrategy):
    name = "breakout"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        debug = []
        if not min_bars(df, 25):
            return hold_signal(self.name, 0, "Need 25+ bars", ["bars<25"])

        lookback = df.iloc[-21:-1]
        row = df.iloc[-1]
        close = _f(row, "Close")
        high20 = float(lookback["High"].max())
        low20 = float(lookback["Low"].min())
        vol_ratio = _f(row, "Volume_Ratio", 1.0)
        range_pct = (high20 - low20) / low20 * 100 if low20 else 0

        debug.append(f"close={close:.2f} high20={high20:.2f} low20={low20:.2f} vol={vol_ratio:.2f}x range={range_pct:.1f}%")

        near_high = close >= high20 * 0.995
        near_low = close <= low20 * 1.005
        vol_ok = vol_ratio >= 0.9

        if near_high and vol_ok and close >= lookback["Close"].mean():
            entry = close
            stop = low20
            if entry - stop <= 0:
                stop = entry * 0.97
            target = entry + (entry - stop) * 2.0
            conf = 60 + min(25, vol_ratio * 10) + (10 if close > high20 else 5)
            return build_signal(
                self.name, "BUY", entry, stop, target,
                f"Breakout {'above' if close > high20 else 'near'} 20-bar high ({high20:.2f}), volume {vol_ratio:.1f}x",
                ["Donchian_High", "Volume_Ratio"], conf, invalidation=low20, debug=debug,
            )

        if near_low and vol_ok and close <= lookback["Close"].mean():
            entry = close
            stop = high20
            if stop - entry <= 0:
                stop = entry * 1.03
            target = entry - (stop - entry) * 2.0
            conf = 60 + min(25, vol_ratio * 10) + (10 if close < low20 else 5)
            return build_signal(
                self.name, "SELL", entry, stop, target,
                f"Breakdown {'below' if close < low20 else 'near'} 20-bar low ({low20:.2f})",
                ["Donchian_Low", "Volume_Ratio"], conf, invalidation=high20, debug=debug,
            )

        debug.append(f"near_high={near_high} near_low={near_low} vol_ok={vol_ok}")
        return hold_signal(self.name, close, "No breakout/breakdown setup", debug)
