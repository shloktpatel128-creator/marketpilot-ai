"""MarketPilot AI — Bot Control Panel (connected to TradingEngine)."""

from __future__ import annotations

import streamlit as st

from config import MODE, REAL_TRADING_ENABLED
from core.bot_runner import BotRunner
from core.engine import TradingEngine
from core.event_log import EVENT_LOG
from core.logger import setup_logging
from core.state import STATE
from notifications import discord_notifier
from storage.database import init_db
from ui.agents_view import render_agents_view
from ui.app_session import init_app_session
from ui.bot_control import render_command_center
from ui.broker_dashboard import render_broker_dashboard
from ui.components import render_top_bar
from ui.health_monitor import render_health_monitor
from ui.journal_view import render_journal_view
from ui.reports_view import render_reports_view
from ui.risk_dashboard import render_risk_dashboard
from ui.system_logs import render_system_logs
from ui.theme import inject_custom_css


@st.cache_resource
def get_engine() -> TradingEngine:
    setup_logging()
    init_db()
    EVENT_LOG.info("Startup", "MarketPilot AI dashboard loaded")
    discord_notifier.notify("Bot Startup", f"Dashboard loaded — mode {MODE}", "info")
    engine = TradingEngine()
    BotRunner.get().attach_engine(engine)
    return engine


def main() -> None:
    st.set_page_config(
        page_title="MarketPilot AI — Bot Control Panel",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(inject_custom_css(), unsafe_allow_html=True)
    init_app_session()

    engine = get_engine()
    STATE.sync_from_brokers(engine.router)
    status = engine.router.status()
    alp = status["alpaca_paper"]
    market_open = alp.get("health", {}).get("market_open", False) if alp["connected"] else False

    with st.sidebar:
        st.markdown("### MarketPilot AI")
        st.caption("Automated AI-Assisted Trading Bot")
        st.markdown(f"**Status:** {STATE.status_label()}")
        st.markdown(f"**Mode:** {MODE}")
        st.markdown(f"**Eval ID:** `{STATE.evaluation_id}`")
        if REAL_TRADING_ENABLED:
            st.error("Live trading blocked")
        st.markdown("---")
        st.markdown("**Brokers**")
        st.write("• Dry Run: ✅")
        fs = status["futures_simulator"]
        st.write(f"• Futures Sim: ✅ (${fs['equity']:,.0f})")
        alp_icon = "✅" if alp["connected"] else "❌"
        st.write(f"• Alpaca Paper: {alp_icon}")
        if alp.get("error") and not alp["connected"]:
            st.caption(alp["error"][:60])
        st.markdown("---")
        render_system_logs()

    render_top_bar(market_open=market_open, paper_mode=True)

    tabs = st.tabs([
        "Command Center",
        "Brokers",
        "Risk Engine",
        "AI Agents",
        "Trade Journal",
        "Reports",
        "Health Monitor",
    ])

    with tabs[0]:
        render_command_center(engine)

    with tabs[1]:
        render_broker_dashboard(engine)

    with tabs[2]:
        render_risk_dashboard(engine)

    with tabs[3]:
        render_agents_view(engine)

    with tabs[4]:
        render_journal_view()

    with tabs[5]:
        render_reports_view()

    with tabs[6]:
        render_health_monitor(engine)
