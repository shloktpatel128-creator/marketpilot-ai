"""AI helper agents — context only, NEVER place trades."""

from __future__ import annotations

from typing import Dict

from agents.backtest_critic_agent import BacktestCriticAgent
from agents.data_quality_agent import DataQualityAgent
from agents.macro_news_agent import MacroNewsAgent
from agents.model_drift_agent import ModelDriftAgent
from agents.model_review_agent import ModelReviewAgent
from agents.news_agent import NewsAgent
from agents.report_agent import ReportAgent
from agents.risk_explainer_agent import RiskExplainerAgent
from agents.strategy_research_agent import StrategyResearchAgent
from agents.trade_analysis_agent import TradeAnalysisAgent
from agents.trade_journal_agent import TradeJournalAgent


def run_all_agents(ctx: Dict) -> Dict[str, str]:
    agents = [
        NewsAgent(), MacroNewsAgent(), RiskExplainerAgent(), TradeAnalysisAgent(),
        ModelReviewAgent(), BacktestCriticAgent(), ModelDriftAgent(),
        StrategyResearchAgent(), DataQualityAgent(),
    ]
    results = {}
    for a in agents:
        try:
            results[a.name] = a.run(**ctx)
        except Exception as exc:
            results[a.name] = f"Agent error: {exc}"
    return results
