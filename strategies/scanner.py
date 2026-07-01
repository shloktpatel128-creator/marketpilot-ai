"""Run all strategies and select the best valid setup."""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from storage.schemas import StrategySignal
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.reversal import ReversalStrategy
from strategies.trend_continuation import TrendContinuationStrategy
from strategies.vwap_momentum import VWAPMomentumStrategy

ALL_STRATEGIES = {
    "vwap_momentum": VWAPMomentumStrategy(),
    "breakout": BreakoutStrategy(),
    "pullback": PullbackStrategy(),
    "reversal": ReversalStrategy(),
    "trend_continuation": TrendContinuationStrategy(),
}


def scan_all_strategies(df: pd.DataFrame, symbol: str) -> Tuple[StrategySignal, List[StrategySignal], Dict[str, str]]:
    """
    Evaluate every strategy. Returns (best_signal, all_signals, debug_map).
    Best = highest setup_confidence among valid setups with R:R >= 1.5.
    """
    all_sigs: List[StrategySignal] = []
    debug_map: Dict[str, str] = {}

    for name, strat in ALL_STRATEGIES.items():
        sig = strat.evaluate(df, symbol)
        all_sigs.append(sig)
        status = sig.direction if sig.setup_detected else "HOLD"
        notes = "; ".join(sig.debug_notes[:4]) if sig.debug_notes else sig.reason
        debug_map[name] = (
            f"{status} | conf={sig.setup_confidence:.0f} rr={sig.reward_risk:.2f} | {notes}"
        )

    setups = [s for s in all_sigs if s.setup_detected and s.direction in ("BUY", "SELL")]
    valid = [s for s in setups if s.stop_loss and s.reward_risk >= 1.5]

    if valid:
        best = max(valid, key=lambda s: (s.setup_confidence, s.reward_risk))
        debug_map["_selected"] = f"{best.strategy_name} ({best.direction} conf={best.setup_confidence:.0f})"
        return best, all_sigs, debug_map

    if setups:
        best = max(setups, key=lambda s: (s.setup_confidence, s.reward_risk))
        debug_map["_selected"] = f"{best.strategy_name} (low R:R {best.reward_risk:.2f})"
        return best, all_sigs, debug_map

    debug_map["_selected"] = "NONE — all strategies HOLD"
    close = float(df.iloc[-1]["Close"]) if not df.empty else 0
    return StrategySignal(
        False, "HOLD", close, None, None, 0,
        "No strategy detected a valid setup",
        [], "", None, 0.0, list(debug_map.values()),
    ), all_sigs, debug_map


def format_strategy_debug(debug_map: Dict[str, str]) -> str:
    lines = ["Strategy scan results:"]
    for name in ALL_STRATEGIES:
        if name in debug_map:
            lines.append(f"  {name}: {debug_map[name]}")
    if "_selected" in debug_map:
        lines.append(f"  → Selected: {debug_map['_selected']}")
    return "\n".join(lines)
