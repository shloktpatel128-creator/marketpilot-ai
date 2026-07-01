"""Strategy optimizer — ranks strategies on historical data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from data.market_data import fetch_ohlcv
from features.feature_engineering import add_features
from services.indicators import compute_institutional_indicators
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.vwap_momentum import VWAPMomentumStrategy


@dataclass
class StrategyRank:
    name: str
    setups: int
    score: float
    avg_reward_risk: float
    summary: str


STRATEGIES = {
    "vwap_momentum": VWAPMomentumStrategy(),
    "breakout": BreakoutStrategy(),
    "pullback": PullbackStrategy(),
}


def rank_strategies(symbol: str = "SPY", period: str = "1y") -> List[StrategyRank]:
    df, _ = fetch_ohlcv(symbol, period=period, interval="1d")
    if df.empty:
        return []
    df = compute_institutional_indicators(add_features(df))
    ranks = []
    for name, strat in STRATEGIES.items():
        setups, rr_sum = 0, 0.0
        for i in range(50, len(df)):
            window = df.iloc[: i + 1]
            sig = strat.evaluate(window, symbol)
            if sig.setup_detected:
                setups += 1
                rr_sum += sig.reward_risk
        avg_rr = rr_sum / setups if setups else 0
        score = setups * 10 + avg_rr * 20
        ranks.append(StrategyRank(
            name=name, setups=setups, score=score, avg_reward_risk=avg_rr,
            summary=f"{setups} setups, avg R:R {avg_rr:.2f}",
        ))
    ranks.sort(key=lambda r: r.score, reverse=True)
    return ranks
