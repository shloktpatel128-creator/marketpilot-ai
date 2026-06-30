"""Breakout strategy."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from storage.schemas import StrategySignal


class BreakoutStrategy(BaseStrategy):
    name = "breakout"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        if len(df) < 25:
            return StrategySignal(False, "HOLD", None, None, None, 0, "Insufficient data", [], self.name)
        lookback = df.iloc[-21:-1]
        row = df.iloc[-1]
        close = float(row["Close"])
        high20 = float(lookback["High"].max())
        low20 = float(lookback["Low"].min())
        vol_ratio = float(row.get("Volume_Ratio", 1) or 1)

        if close >= high20 and vol_ratio >= 1.2:
            entry = close
            stop = low20
            target = entry + (entry - stop) * 1.5
            rr = (target - entry) / (entry - stop) if entry > stop else 0
            return StrategySignal(
                True, "BUY", entry, stop, target, round(rr, 2),
                f"Breakout above 20-bar high ({high20:.2f}) with volume.",
                ["High_20", "Volume_Ratio"], self.name,
            )
        if close <= low20 and vol_ratio >= 1.2:
            entry = close
            stop = high20
            target = entry - (stop - entry) * 1.5
            rr = (entry - target) / (stop - entry) if stop > entry else 0
            return StrategySignal(
                True, "SELL", entry, stop, target, round(rr, 2),
                f"Breakdown below 20-bar low ({low20:.2f}).",
                ["Low_20", "Volume_Ratio"], self.name,
            )
        return StrategySignal(False, "HOLD", close, None, None, 0, "No breakout setup.", ["High_20", "Low_20"], self.name)
