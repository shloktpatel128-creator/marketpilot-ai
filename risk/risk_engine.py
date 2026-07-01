"""RiskEngine — final authority on every trade."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional

from config import (
    MAX_DAILY_LOSS_USD,
    MAX_DRAWDOWN_PCT,
    MAX_OPEN_POSITIONS,
    MAX_POSITION_SIZE_USD,
    MAX_RISK_PER_TRADE_PCT,
    MAX_TRADES_PER_DAY,
    MIN_CONFIDENCE_TO_TRADE,
    MIN_REWARD_RISK,
    REAL_TRADING_ENABLED,
)
from storage.schemas import ConfidenceResult, RiskDecision, StrategySignal


@dataclass
class RiskContext:
    broker: str
    symbol: str
    broker_connected: bool
    data_quality_ok: bool
    daily_pnl: float = 0.0
    trades_today: int = 0
    open_positions: int = 0
    buying_power: float = 100_000.0
    news_restricted: bool = False
    duplicate_order: bool = False
    market_open: bool = True


class RiskEngine:
    """Approves or rejects every trade. No agent can override."""

    def evaluate(
        self,
        signal: StrategySignal,
        confidence: ConfidenceResult,
        ctx: RiskContext,
        position_size_usd: float = 1000.0,
    ) -> RiskDecision:
        reasons: List[str] = []

        if REAL_TRADING_ENABLED:
            reasons.append("REAL_TRADING_ENABLED blocked — live trading forbidden.")

        if not signal.setup_detected:
            reasons.append("No strategy setup detected.")

        if signal.direction == "HOLD":
            reasons.append("Direction is HOLD.")

        if signal.stop_loss is None:
            reasons.append("Missing required stop loss.")

        if signal.entry is None:
            reasons.append("Missing entry price.")

        if confidence.confidence < MIN_CONFIDENCE_TO_TRADE:
            reasons.append(f"Confidence {confidence.confidence:.0f}% below minimum {MIN_CONFIDENCE_TO_TRADE}%.")

        if signal.reward_risk < MIN_REWARD_RISK:
            reasons.append(f"Reward/risk {signal.reward_risk:.2f} below minimum {MIN_REWARD_RISK}.")

        if ctx.trades_today >= MAX_TRADES_PER_DAY:
            reasons.append(f"Max trades per day ({MAX_TRADES_PER_DAY}) reached.")

        if ctx.open_positions >= MAX_OPEN_POSITIONS:
            reasons.append(f"Max open positions ({MAX_OPEN_POSITIONS}) reached.")

        if ctx.daily_pnl <= -MAX_DAILY_LOSS_USD:
            reasons.append(f"Daily loss limit (${MAX_DAILY_LOSS_USD}) breached.")

        if ctx.daily_pnl / max(ctx.buying_power, 1) <= -MAX_DRAWDOWN_PCT:
            reasons.append(f"Max drawdown ({MAX_DRAWDOWN_PCT*100:.0f}%) breached.")

        if not ctx.data_quality_ok:
            reasons.append("Data quality check failed.")

        if not ctx.broker_connected and ctx.broker != "dry_run" and ctx.broker != "futures_simulator":
            reasons.append("Broker not connected.")

        if ctx.news_restricted:
            reasons.append("News event restriction active.")

        if ctx.duplicate_order:
            reasons.append("Duplicate order prevention triggered.")

        if not ctx.market_open and ctx.broker == "alpaca_paper":
            reasons.append("Market closed.")

        if not self._in_trading_hours() and ctx.broker == "alpaca_paper":
            reasons.append("Outside allowed trading hours.")

        adjusted = min(position_size_usd, MAX_POSITION_SIZE_USD, ctx.buying_power * MAX_RISK_PER_TRADE_PCT * 10)
        if adjusted <= 0:
            reasons.append("Insufficient buying power.")

        risk_score = max(0, 100 - len(reasons) * 12)
        approved = len(reasons) == 0

        return RiskDecision(approved=approved, rejection_reasons=reasons, adjusted_size=adjusted if approved else None, risk_score=risk_score)

    @staticmethod
    def _in_trading_hours() -> bool:
        from datetime import datetime, time
        now = datetime.utcnow().time()
        return time(14, 30) <= now <= time(21, 0)
