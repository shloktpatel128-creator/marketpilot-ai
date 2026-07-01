"""AI Agents dashboard — shadow mode, analysis only."""

from __future__ import annotations

import streamlit as st

from config import AI_CAN_PLACE_TRADES, NEWS_AGENTS_SHADOW_MODE
from core.engine import TradingEngine
from core.state import STATE

AGENT_NAMES = [
    "TechnicalAnalyst", "NewsAnalyst", "MacroAnalyst", "MomentumAnalyst",
    "RiskManager", "PortfolioManager", "TradeCritic", "ExecutionManager",
    "ConfidenceScorer", "ChiefInvestmentOfficer",
]


def render_agents_view(engine: TradingEngine) -> None:
    st.subheader("AI Agent Pipeline")
    st.caption("10 independent agents + CIO synthesis. Agents analyze only — never execute trades.")
    st.info(f"AI_CAN_PLACE_TRADES = {AI_CAN_PLACE_TRADES} | Shadow = {NEWS_AGENTS_SHADOW_MODE}")

    for name in AGENT_NAMES:
        stored = STATE.agent_outputs.get(name, {})
        last_run = stored.get("last_run", "Never")
        output = stored.get("output", "Awaiting next scan…")
        rec = stored.get("recommendation", "—")
        active = stored.get("active", False)
        with st.expander(f"{'🟢' if active else '⚪'} {name}", expanded=False):
            st.write(f"**Recommendation:** {rec}")
            st.write(f"**Last run:** {last_run}")
            st.markdown(output)
