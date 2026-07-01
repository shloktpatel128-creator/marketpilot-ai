"""Institutional trade plan generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class TradePlan:
    direction: str  # BUY | SELL | HOLD | NO_TRADE
    entry: float
    stop_loss: float
    take_profit: float
    reward_risk: float
    position_size_usd: float
    position_size_shares: float
    atr: float
    probability_of_success: float
    expected_value: float
    max_drawdown_estimate: float
    reasoning: List[str] = field(default_factory=list)
    partial_targets: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "direction": self.direction, "entry": self.entry,
            "stop_loss": self.stop_loss, "take_profit": self.take_profit,
            "reward_risk": self.reward_risk, "position_size_usd": self.position_size_usd,
            "probability_of_success": self.probability_of_success,
            "expected_value": self.expected_value,
            "max_drawdown_estimate": self.max_drawdown_estimate,
            "reasoning": self.reasoning,
        }


def generate_trade_plan(
    df: pd.DataFrame,
    direction: str,
    confidence: float,
    buying_power: float,
    max_risk_pct: float = 0.01,
    atr_mult_stop: float = 1.5,
    atr_mult_target: float = 3.0,
) -> TradePlan:
    if df.empty or direction in ("HOLD", "NO_TRADE"):
        return TradePlan("NO_TRADE", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ["No trade signal"])

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("ATR_14", entry * 0.02) or entry * 0.02)

    if direction == "BUY":
        stop = entry - atr * atr_mult_stop
        target = entry + atr * atr_mult_target
    else:
        stop = entry + atr * atr_mult_stop
        target = entry - atr * atr_mult_target

    risk_per_share = abs(entry - stop)
    reward = abs(target - entry)
    rr = reward / risk_per_share if risk_per_share > 0 else 0

    risk_budget = buying_power * max_risk_pct
    shares = risk_budget / risk_per_share if risk_per_share > 0 else 0
    position_usd = min(shares * entry, buying_power * 0.1)

    prob = min(0.85, max(0.35, confidence / 100 * 0.7 + rr * 0.05))
    ev = prob * reward - (1 - prob) * risk_per_share
    mdd_est = (risk_per_share / entry) * 100

    reasons = [
        f"ATR-based stop at {atr_mult_stop}x ATR (${atr:.2f})",
        f"Target at {atr_mult_target}x ATR — R:R {rr:.2f}",
        f"Position sized for {max_risk_pct*100:.1f}% account risk",
        f"Probability estimate {prob*100:.0f}% from confidence {confidence:.0f}",
        f"Expected value ${ev:.2f}/share",
    ]

    partials = []
    if direction == "BUY":
        partials = [entry + atr, entry + atr * 2]
    else:
        partials = [entry - atr, entry - atr * 2]

    return TradePlan(
        direction=direction, entry=entry, stop_loss=stop, take_profit=target,
        reward_risk=round(rr, 2), position_size_usd=round(position_usd, 2),
        position_size_shares=round(position_usd / entry, 4) if entry else 0,
        atr=atr, probability_of_success=round(prob, 3),
        expected_value=round(ev, 4), max_drawdown_estimate=round(mdd_est, 2),
        reasoning=reasons, partial_targets=partials,
    )
