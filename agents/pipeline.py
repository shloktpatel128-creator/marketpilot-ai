"""AI agent pipeline — multi-agent analysis with CIO final decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from config import AI_CAN_PLACE_TRADES
from services.macro import MacroAnalysis
from services.multitimeframe import MultiTimeframeResult
from services.news import NewsAnalysis
from services.regime import MarketRegime
from services.trade_plan import TradePlan
from storage.schemas import StrategySignal


@dataclass
class AgentVote:
    agent: str
    recommendation: str  # BUY | SELL | HOLD | NO_TRADE
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CIODecision:
    final_action: str  # BUY | SELL | HOLD | NO_TRADE
    confidence: float
    votes: List[AgentVote]
    consensus_summary: str
    trade_plan: Optional[TradePlan] = None
    can_execute: bool = False  # always False for agents


class AgentPipeline:
    """Runs independent agents then CIO synthesis. Agents NEVER execute trades."""

    def __init__(self) -> None:
        assert not AI_CAN_PLACE_TRADES

    def _technical(self, df: pd.DataFrame, signal: StrategySignal) -> AgentVote:
        row = df.iloc[-1] if not df.empty else None
        rec, conf, reasons = "HOLD", 40.0, []
        if row is not None:
            rsi = float(row.get("RSI", 50) or 50)
            st_dir = float(row.get("SuperTrend_Dir", 0) or 0)
            macd_h = float(row.get("MACD_Hist", 0) or 0)
            if st_dir > 0 and macd_h > 0 and rsi < 70:
                rec, conf = "BUY", 70
                reasons.append("SuperTrend bullish + MACD positive")
            elif st_dir < 0 and macd_h < 0 and rsi > 30:
                rec, conf = "SELL", 70
                reasons.append("SuperTrend bearish + MACD negative")
            if signal.setup_detected:
                conf += 10
                reasons.append(f"Strategy setup: {signal.reason[:80]}")
        return AgentVote("TechnicalAnalyst", rec, conf, "; ".join(reasons) or "No clear technical edge")

    def _news(self, news: NewsAnalysis, direction_hint: str) -> AgentVote:
        if not news.items:
            return AgentVote("NewsAnalyst", "HOLD", 45, "No news data")
        rec = "HOLD"
        conf = 50 + abs(news.sentiment_score) * 30
        if news.overall_sentiment == "bullish":
            rec = "BUY"
        elif news.overall_sentiment == "bearish":
            rec = "SELL"
        return AgentVote("NewsAnalyst", rec, conf, news.summary)

    def _macro(self, macro: MacroAnalysis) -> AgentVote:
        rec = "HOLD"
        conf = 60 - macro.risk_adjustment
        if macro.high_impact_soon or macro.earnings_soon:
            rec = "NO_TRADE"
            conf = 30
        return AgentVote("MacroAnalyst", rec, conf, macro.summary)

    def _momentum(self, df: pd.DataFrame) -> AgentVote:
        if df.empty:
            return AgentVote("MomentumAnalyst", "HOLD", 40, "No data")
        m10 = float(df.iloc[-1].get("Momentum_10", 0) or 0)
        rec = "BUY" if m10 > 2 else "SELL" if m10 < -2 else "HOLD"
        conf = min(85, 50 + abs(m10) * 5)
        return AgentVote("MomentumAnalyst", rec, conf, f"10-day momentum {m10:.1f}%")

    def _risk_manager(self, plan: TradePlan, portfolio_heat: float) -> AgentVote:
        if plan.direction == "NO_TRADE":
            return AgentVote("RiskManager", "NO_TRADE", 90, "No valid trade plan")
        if portfolio_heat > 75:
            return AgentVote("RiskManager", "NO_TRADE", 85, f"Portfolio heat too high ({portfolio_heat:.0f}%)")
        if plan.reward_risk < 1.5:
            return AgentVote("RiskManager", "NO_TRADE", 80, f"R:R {plan.reward_risk} below threshold")
        return AgentVote("RiskManager", plan.direction, 75, f"Risk acceptable — R:R {plan.reward_risk}, heat {portfolio_heat:.0f}%")

    def _portfolio_manager(self, open_positions: int, max_positions: int) -> AgentVote:
        if open_positions >= max_positions:
            return AgentVote("PortfolioManager", "NO_TRADE", 90, f"Max positions ({max_positions}) reached")
        return AgentVote("PortfolioManager", "HOLD", 60, f"{open_positions}/{max_positions} positions open")

    def _trade_critic(self, signal: StrategySignal, mtf: MultiTimeframeResult) -> AgentVote:
        issues = []
        if not signal.setup_detected:
            issues.append("No strategy setup")
        if mtf.dominant_trend == "bearish" and signal.direction == "BUY":
            issues.append("MTF bearish conflicts with BUY")
        if mtf.dominant_trend == "bullish" and signal.direction == "SELL":
            issues.append("MTF bullish conflicts with SELL")
        if issues:
            return AgentVote("TradeCritic", "NO_TRADE", 70, "; ".join(issues))
        return AgentVote("TradeCritic", signal.direction if signal.setup_detected else "HOLD", 65, "Setup passes initial critique")

    def _execution_manager(self, broker_connected: bool, market_open: bool) -> AgentVote:
        if not broker_connected:
            return AgentVote("ExecutionManager", "NO_TRADE", 95, "Broker not connected")
        if not market_open:
            return AgentVote("ExecutionManager", "HOLD", 70, "Market closed — queue for open")
        return AgentVote("ExecutionManager", "HOLD", 55, "Execution infrastructure ready")

    def _confidence_scorer(self, votes: List[AgentVote]) -> AgentVote:
        buy = sum(1 for v in votes if v.recommendation == "BUY")
        sell = sum(1 for v in votes if v.recommendation == "SELL")
        no_trade = sum(1 for v in votes if v.recommendation == "NO_TRADE")
        avg_conf = sum(v.confidence for v in votes) / len(votes) if votes else 0
        if no_trade >= 3:
            rec = "NO_TRADE"
        elif buy > sell:
            rec = "BUY"
        elif sell > buy:
            rec = "SELL"
        else:
            rec = "HOLD"
        return AgentVote("ConfidenceScorer", rec, avg_conf, f"Vote tally: {buy}B/{sell}S/{no_trade}NT — avg conf {avg_conf:.0f}")

    def _cio(self, votes: List[AgentVote], plan: TradePlan) -> CIODecision:
        """Chief Investment Officer — final decision. Does NOT execute."""
        action_weights = {"BUY": 0, "SELL": 0, "HOLD": 0, "NO_TRADE": 0}
        conf_sum = {k: 0.0 for k in action_weights}
        for v in votes:
            action_weights[v.recommendation] = action_weights.get(v.recommendation, 0) + 1
            conf_sum[v.recommendation] = conf_sum.get(v.recommendation, 0) + v.confidence

        if action_weights["NO_TRADE"] >= 2:
            final = "NO_TRADE"
        elif action_weights["BUY"] > action_weights["SELL"] and action_weights["BUY"] >= 3:
            final = "BUY"
        elif action_weights["SELL"] > action_weights["BUY"] and action_weights["SELL"] >= 3:
            final = "SELL"
        elif plan.direction not in ("NO_TRADE", "HOLD") and plan.reward_risk >= 1.5:
            final = plan.direction
        else:
            final = "HOLD"

        n = action_weights.get(final, 1) or 1
        conf = conf_sum.get(final, 50) / n

        summary = f"CIO decision: {final} (confidence {conf:.0f}) — "
        summary += ", ".join(f"{v.agent}:{v.recommendation}" for v in votes[:5])

        return CIODecision(
            final_action=final, confidence=conf, votes=votes,
            consensus_summary=summary, trade_plan=plan, can_execute=False,
        )

    def run(
        self,
        df: pd.DataFrame,
        signal: StrategySignal,
        mtf: MultiTimeframeResult,
        news: NewsAnalysis,
        macro: MacroAnalysis,
        regime: MarketRegime,
        plan: TradePlan,
        open_positions: int = 0,
        max_positions: int = 5,
        portfolio_heat: float = 0,
        broker_connected: bool = True,
        market_open: bool = True,
    ) -> CIODecision:
        votes = [
            self._technical(df, signal),
            self._news(news, signal.direction),
            self._macro(macro),
            self._momentum(df),
            self._risk_manager(plan, portfolio_heat),
            self._portfolio_manager(open_positions, max_positions),
            self._trade_critic(signal, mtf),
            self._execution_manager(broker_connected, market_open),
            self._confidence_scorer([]),
        ]
        votes[-1] = self._confidence_scorer(votes[:-1])
        return self._cio(votes, plan)

    def votes_to_context(self, decision: CIODecision) -> Dict[str, str]:
        ctx = {"cio_decision": decision.consensus_summary}
        for v in decision.votes:
            ctx[v.agent] = f"{v.recommendation} ({v.confidence:.0f}): {v.reasoning}"
        return ctx
