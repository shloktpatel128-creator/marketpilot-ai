"""Portfolio-level risk management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import MAX_DAILY_LOSS_USD, MAX_OPEN_POSITIONS, MAX_POSITION_SIZE_USD


@dataclass
class PortfolioRiskState:
    total_equity: float
    daily_pnl: float
    open_positions: int
    portfolio_heat_pct: float
    daily_loss_remaining: float
    max_position_usd: float
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    correlated_pairs: List[str] = field(default_factory=list)
    kelly_fraction: Optional[float] = None
    volatility_adjusted_size: float = 0.0
    warnings: List[str] = field(default_factory=list)


def compute_portfolio_heat(daily_pnl: float, equity: float) -> float:
    if equity <= 0:
        return 0.0
    loss = abs(min(0, daily_pnl))
    return min(100, (loss / MAX_DAILY_LOSS_USD) * 100)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    if avg_loss <= 0 or win_rate <= 0:
        return 0.0
    b = avg_win / avg_loss
    f = (win_rate * b - (1 - win_rate)) / b
    return max(0, min(0.25, f))  # cap at 25%


def volatility_adjusted_size(base_size: float, volatility_pct: float, target_vol: float = 20.0) -> float:
    if volatility_pct <= 0:
        return base_size
    return base_size * (target_vol / volatility_pct)


def assess_portfolio(
    equity: float,
    daily_pnl: float,
    open_positions: int,
    positions: List[Dict],
    win_rate: float = 0.5,
    avg_win: float = 100,
    avg_loss: float = 50,
    volatility_pct: float = 20,
    base_size: float = 1000,
) -> PortfolioRiskState:
    heat = compute_portfolio_heat(daily_pnl, equity)
    loss_remaining = max(0, MAX_DAILY_LOSS_USD + min(0, daily_pnl))
    warnings = []

    if open_positions >= MAX_OPEN_POSITIONS:
        warnings.append(f"At max open positions ({MAX_OPEN_POSITIONS})")
    if heat > 80:
        warnings.append(f"Portfolio heat critical ({heat:.0f}%)")
    if daily_pnl <= -MAX_DAILY_LOSS_USD:
        warnings.append("Daily loss limit breached")

    kelly = kelly_criterion(win_rate, avg_win, avg_loss)
    vol_adj = volatility_adjusted_size(base_size, volatility_pct)

    return PortfolioRiskState(
        total_equity=equity, daily_pnl=daily_pnl, open_positions=open_positions,
        portfolio_heat_pct=heat, daily_loss_remaining=loss_remaining,
        max_position_usd=min(MAX_POSITION_SIZE_USD, equity * 0.1),
        kelly_fraction=kelly, volatility_adjusted_size=vol_adj, warnings=warnings,
    )
