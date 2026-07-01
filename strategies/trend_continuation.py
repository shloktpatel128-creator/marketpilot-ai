"""Trend continuation — ADX trend with EMA pullback and resumption."""

from __future__ import annotations

import pandas as pd

from strategies.base import BaseStrategy
from strategies.helpers import _f, atr_stop, build_signal, hold_signal, min_bars
from storage.schemas import StrategySignal


class TrendContinuationStrategy(BaseStrategy):
    name = "trend_continuation"

    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        debug = []
        if not min_bars(df, 50):
            return hold_signal(self.name, 0, "Need 50+ bars", ["bars<50"])

        row = df.iloc[-1]
        prev = df.iloc[-2]
        close = _f(row, "Close")
        sma50 = _f(row, "SMA_50", close)
        sma200 = _f(row, "SMA_200", close)
        ema20 = _f(row, "EMA_20", close)
        adx = _f(row, "ADX", 20)
        di_plus = _f(row, "DI_Plus", 0)
        di_minus = _f(row, "DI_Minus", 0)
        st_dir = _f(row, "SuperTrend_Dir", 0)
        prev_close = _f(prev, "Close")

        debug.append(f"adx={adx:.0f} st={st_dir:.0f} close={close:.2f} ema20={ema20:.2f}")

        bull_trend = adx >= 18 and close > sma50 and sma50 >= sma200 * 0.995 and di_plus > di_minus
        touched_ema = prev_close <= ema20 * 1.005 and close > ema20 and close > prev_close

        if bull_trend and (touched_ema or (st_dir > 0 and close > ema20)):
            entry = close
            stop = min(ema20 * 0.985, sma50 * 0.98, atr_stop(df, "BUY", entry, 1.5))
            target = entry + (entry - stop) * 2.0
            conf = 55 + min(25, adx) + (10 if touched_ema else 5)
            return build_signal(
                self.name, "BUY", entry, stop, target,
                f"Trend continuation long — ADX {adx:.0f}, price resuming above EMA20",
                ["ADX", "EMA_20", "SMA_50", "SuperTrend_Dir", "DI_Plus"],
                conf, invalidation=stop, debug=debug,
            )

        bear_trend = adx >= 18 and close < sma50 and sma50 <= sma200 * 1.005 and di_minus > di_plus
        touch_ema_bear = prev_close >= ema20 * 0.995 and close < ema20 and close < prev_close

        if bear_trend and (touch_ema_bear or (st_dir < 0 and close < ema20)):
            entry = close
            stop = max(ema20 * 1.015, sma50 * 1.02, atr_stop(df, "SELL", entry, 1.5))
            target = entry - (stop - entry) * 2.0
            conf = 55 + min(25, adx) + (10 if touch_ema_bear else 5)
            return build_signal(
                self.name, "SELL", entry, stop, target,
                f"Trend continuation short — ADX {adx:.0f}, price resuming below EMA20",
                ["ADX", "EMA_20", "SMA_50", "SuperTrend_Dir", "DI_Minus"],
                conf, invalidation=stop, debug=debug,
            )

        debug.append(f"bull_trend={bull_trend} bear_trend={bear_trend} touched_ema={touched_ema}")
        return hold_signal(self.name, close, "No trend continuation setup", debug)
