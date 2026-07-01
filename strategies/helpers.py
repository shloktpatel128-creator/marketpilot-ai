"""Shared strategy utilities — ATR stops, R:R, signal builders."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd

from storage.schemas import StrategySignal


def _f(row, key: str, default: float = 0.0) -> float:
    v = row.get(key, default)
    if pd.isna(v):
        return default
    return float(v)


def atr_stop(df: pd.DataFrame, direction: str, entry: float, mult: float = 1.5) -> float:
    atr = _f(df.iloc[-1], "ATR_14", entry * 0.02)
    if direction == "BUY":
        swing = float(df["Low"].iloc[-5:].min())
        return min(entry - atr * mult, swing * 0.998)
    swing = float(df["High"].iloc[-5:].max())
    return max(entry + atr * mult, swing * 1.002)


def reward_risk(entry: float, stop: float, target: float, direction: str) -> float:
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def build_signal(
    strategy_name: str,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    reason: str,
    features: List[str],
    setup_confidence: float,
    invalidation: Optional[float] = None,
    debug: Optional[List[str]] = None,
) -> StrategySignal:
    rr = reward_risk(entry, stop, target, direction)
    inv = invalidation if invalidation is not None else stop
    return StrategySignal(
        setup_detected=True,
        direction=direction,
        entry=round(entry, 4),
        stop_loss=round(stop, 4),
        take_profit=round(target, 4),
        reward_risk=rr,
        reason=reason,
        features_used=features,
        strategy_name=strategy_name,
        invalidation_level=round(inv, 4),
        setup_confidence=round(min(100, max(0, setup_confidence)), 1),
        debug_notes=debug or [],
    )


def hold_signal(
    strategy_name: str,
    close: float,
    reason: str,
    debug: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
) -> StrategySignal:
    return StrategySignal(
        setup_detected=False,
        direction="HOLD",
        entry=close,
        stop_loss=None,
        take_profit=None,
        reward_risk=0.0,
        reason=reason,
        features_used=features or [],
        strategy_name=strategy_name,
        invalidation_level=None,
        setup_confidence=0.0,
        debug_notes=debug or [reason],
    )


def min_bars(df: pd.DataFrame, n: int) -> bool:
    return df is not None and len(df) >= n
