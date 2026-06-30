"""VWAP momentum strategy."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from storage.schemas import StrategySignal


class VWAPMomentumStrategy(BaseStrategy):
    name = "vwap_momentum"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        if len(df) < 30 or "VWAP" not in df.columns:
            return StrategySignal(False, "HOLD", None, None, None, 0, "Insufficient data", [], self.name)
        row = df.iloc[-1]
        close = float(row["Close"])
        vwap = float(row["VWAP"]) if pd.notna(row["VWAP"]) else close
        mom = float(row.get("Momentum_10", 0) or 0)
        vol_ratio = float(row.get("Volume_Ratio", 1) or 1)

        if close > vwap and mom > 1 and vol_ratio > 1.0:
            entry = close
            stop = entry * 0.98
            target = entry * 1.04
            rr = (target - entry) / (entry - stop) if entry > stop else 0
            return StrategySignal(
                True, "BUY", entry, stop, target, round(rr, 2),
                f"Price above VWAP with positive momentum ({mom:.1f}%) and volume confirmation.",
                ["VWAP", "Momentum_10", "Volume_Ratio"], self.name,
            )
        if close < vwap and mom < -1 and vol_ratio > 1.0:
            entry = close
            stop = entry * 1.02
            target = entry * 0.96
            rr = (entry - target) / (stop - entry) if stop > entry else 0
            return StrategySignal(
                True, "SELL", entry, stop, target, round(rr, 2),
                f"Price below VWAP with negative momentum ({mom:.1f}%).",
                ["VWAP", "Momentum_10", "Volume_Ratio"], self.name,
            )
        return StrategySignal(False, "HOLD", close, None, None, 0, "No VWAP momentum setup.", ["VWAP"], self.name)
