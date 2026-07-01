"""Strategy performance analytics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from storage.database import fetch_decisions_filtered


@dataclass
class PerformanceMetrics:
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_r_multiple: float = 0.0
    avg_holding_days: float = 0.0
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    rolling_30d_return: float = 0.0


def _max_drawdown(returns: List[float]) -> float:
    if not returns:
        return 0.0
    equity = np.cumprod([1 + r for r in returns])
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(abs(dd.min()) * 100)


def compute_performance(broker: Optional[str] = None, days: int = 365) -> PerformanceMetrics:
    rows = fetch_decisions_filtered(limit=2000, broker=broker)
    trades = [r for r in rows if r.get("approved")]
    pm = PerformanceMetrics(total_trades=len(trades))

    pnls = [float(r.get("pnl") or 0) for r in trades]
    if not pnls:
        # Estimate from confidence for approved trades without PnL
        pnls = [(1 if r.get("approved") else -1) * (r.get("confidence", 50) / 100) for r in trades]

    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    pm.win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    gross_win = sum(wins)
    gross_loss = sum(losses)
    pm.profit_factor = gross_win / gross_loss if gross_loss > 0 else 0
    pm.expectancy = sum(pnls) / len(pnls) if pnls else 0

    if len(pnls) > 1:
        rets = np.array(pnls) / 10000  # normalize
        pm.sharpe_ratio = float(rets.mean() / rets.std() * math.sqrt(252)) if rets.std() > 0 else 0
        downside = rets[rets < 0]
        pm.sortino_ratio = float(rets.mean() / downside.std() * math.sqrt(252)) if len(downside) and downside.std() > 0 else 0
        pm.max_drawdown = _max_drawdown(rets.tolist())

    return pm


def strategy_win_rates() -> Dict[str, float]:
    rows = fetch_decisions_filtered(limit=1000)
    by_strat: Dict[str, List] = {}
    for r in rows:
        s = r.get("strategy", "unknown")
        by_strat.setdefault(s, []).append(r)
    rates = {}
    for s, items in by_strat.items():
        approved = [i for i in items if i.get("approved")]
        rates[s] = len(approved) / len(items) * 100 if items else 50
    return rates
