"""VWAP momentum — price vs VWAP with momentum and volume confirmation."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from strategies.helpers import _f, atr_stop, build_signal, hold_signal, min_bars, reward_risk
from storage.schemas import StrategySignal


class VWAPMomentumStrategy(BaseStrategy):
    name = "vwap_momentum"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        debug = []
        if not min_bars(df, 30):
            return hold_signal(self.name, 0, "Need 30+ bars", ["bars<30"])

        row = df.iloc[-1]
        close = _f(row, "Close")
        vwap = _f(row, "VWAP", close)
        mom = _f(row, "Momentum_10")
        vol_ratio = _f(row, "Volume_Ratio", 1.0)
        rsi = _f(row, "RSI", 50)
        macd_h = _f(row, "MACD_Hist", 0)
        vwap_dist = (close - vwap) / vwap * 100 if vwap else 0

        debug.append(f"close={close:.2f} vwap={vwap:.2f} dist={vwap_dist:.2f}% mom={mom:.2f}% vol={vol_ratio:.2f} rsi={rsi:.0f}")

        # BUY: above VWAP, positive momentum, not overbought
        buy_score = 0
        if close > vwap:
            buy_score += 25
            debug.append("price above VWAP (+25)")
        if mom > 0.2:
            buy_score += 20
            debug.append(f"momentum positive (+20)")
        if vol_ratio >= 0.85:
            buy_score += 15
            debug.append(f"volume OK (+15)")
        if macd_h > 0:
            buy_score += 15
            debug.append("MACD histogram bullish (+15)")
        if 40 <= rsi <= 68:
            buy_score += 10
            debug.append(f"RSI in buy zone (+10)")

        if buy_score >= 55 and close > vwap and mom > 0:
            entry = close
            stop = atr_stop(df, "BUY", entry, 1.5)
            risk = entry - stop
            target = entry + risk * 2.0
            conf = min(90, buy_score + 10)
            return build_signal(
                self.name, "BUY", entry, stop, target,
                f"VWAP momentum long: {vwap_dist:.1f}% above VWAP, mom {mom:.1f}%, vol {vol_ratio:.1f}x",
                ["VWAP", "Momentum_10", "Volume_Ratio", "MACD_Hist", "RSI"],
                conf, invalidation=stop, debug=debug,
            )

        # SELL: below VWAP, negative momentum
        sell_score = 0
        if close < vwap:
            sell_score += 25
        if mom < -0.2:
            sell_score += 20
        if vol_ratio >= 0.85:
            sell_score += 15
        if macd_h < 0:
            sell_score += 15
        if 32 <= rsi <= 60:
            sell_score += 10

        if sell_score >= 55 and close < vwap and mom < 0:
            entry = close
            stop = atr_stop(df, "SELL", entry, 1.5)
            risk = stop - entry
            target = entry - risk * 2.0
            conf = min(90, sell_score + 10)
            return build_signal(
                self.name, "SELL", entry, stop, target,
                f"VWAP momentum short: {abs(vwap_dist):.1f}% below VWAP, mom {mom:.1f}%",
                ["VWAP", "Momentum_10", "Volume_Ratio", "MACD_Hist", "RSI"],
                conf, invalidation=stop, debug=debug,
            )

        debug.append(f"buy_score={buy_score} sell_score={sell_score} — thresholds not met")
        return hold_signal(self.name, close, "No VWAP momentum setup", debug)
