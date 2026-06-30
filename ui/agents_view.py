"""AI Agents dashboard — shadow mode, analysis only."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

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
from config import AI_CAN_PLACE_TRADES, NEWS_AGENTS_SHADOW_MODE
from core.engine import TradingEngine
from core.state import STATE
from models.model_registry import ModelRegistry
from storage.database import count_today

AGENT_CLASSES = [
    NewsAgent, MacroNewsAgent, TradeAnalysisAgent, TradeJournalAgent,
    ReportAgent, RiskExplainerAgent, ModelReviewAgent, BacktestCriticAgent,
    StrategyResearchAgent, DataQualityAgent, ModelDriftAgent,
]


def render_agents_view(engine: TradingEngine) -> None:
    st.subheader("AI Agents")
    st.caption("Shadow mode — agents analyze and explain only. They never execute trades.")
    st.info(f"AI_CAN_PLACE_TRADES = {AI_CAN_PLACE_TRADES} | Shadow mode = {NEWS_AGENTS_SHADOW_MODE}")

    if st.button("Refresh All Agents", key="refresh_agents"):
        counts = count_today()
        ctx = {
            "symbol": "SPY",
            "version": ModelRegistry().get_active(),
            "stats": counts,
            "approved": False,
            "reasons": ["Sample context"],
        }
        for cls in AGENT_CLASSES:
            agent = cls()
            assert agent.can_place_trades is False
            output = agent.run(**ctx)
            STATE.agent_outputs[agent.name] = {
                "output": output,
                "last_run": datetime.utcnow().isoformat(),
                "active": True,
            }
        st.success("All agents refreshed.")
        st.rerun()

    for cls in AGENT_CLASSES:
        agent = cls()
        stored = STATE.agent_outputs.get(agent.name, {})
        last_run = stored.get("last_run", "Never")
        output = stored.get("output", "No output yet — run a scan or refresh agents.")
        active = stored.get("active", False)

        with st.expander(f"{'🟢' if active else '⚪'} {agent.name}", expanded=False):
            c1, c2 = st.columns(2)
            c1.write(f"**Status:** {'Active' if active else 'Idle'}")
            c2.write(f"**Last run:** {last_run}")
            c1.write(f"**Can place trades:** {agent.can_place_trades}")
            st.markdown(f"**Latest output:** {output}")
