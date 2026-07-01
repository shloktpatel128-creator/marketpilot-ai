"""MarketPilot AI — Bot Control Panel."""

from __future__ import annotations

import streamlit as st

from config import MODE, REAL_TRADING_ENABLED
from core.bot_runner import BotRunner
from core.engine import TradingEngine
from core.event_log import EVENT_LOG
from core.logger import setup_logging
from core.state import STATE
from notifications import discord_notifier
from storage.database import fetch_decisions_filtered, init_db
from ui.agents_view import render_agents_view
from ui.analytics_charts import confidence_gauge, drawdown_chart, equity_curve, sentiment_gauge, trade_distribution, volatility_gauge
from ui.app_session import init_app_session
from ui.bot_control import render_command_center
from ui.broker_dashboard import render_broker_dashboard
from ui.components import render_top_bar
from ui.health_monitor import render_health_monitor
from ui.journal_view import render_journal_view
from ui.reports_view import render_reports_view
from ui.risk_dashboard import render_risk_dashboard
from ui.settings import render_settings
from ui.system_logs import render_system_logs
from ui.theme import inject_custom_css


@st.cache_resource
def get_engine() -> TradingEngine:
    setup_logging()
    init_db()
    EVENT_LOG.info("Startup", "MarketPilot AI institutional platform loaded")
    discord_notifier.notify("Bot Startup", f"Dashboard loaded — mode {MODE}", "info")
    engine = TradingEngine()
    BotRunner.get().attach_engine(engine)
    return engine


def _render_analytics_panel(engine: TradingEngine) -> None:
    rows = fetch_decisions_filtered(limit=100)
    latest = rows[0] if rows else {}
    conf = float(latest.get("confidence", 0) or 0)
    snap = latest.get("indicator_snapshot") or {}
    vol = float(snap.get("Volatility_20", 0) or 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(confidence_gauge(conf), use_container_width=True)
    with c2:
        news_score = 0.0
        if STATE.agent_outputs.get("NewsAnalyst"):
            out = STATE.agent_outputs["NewsAnalyst"].get("output", "")
            news_score = 0.3 if "bullish" in out.lower() else -0.3 if "bearish" in out.lower() else 0
        st.plotly_chart(sentiment_gauge(news_score), use_container_width=True)
    with c3:
        st.plotly_chart(volatility_gauge(vol), use_container_width=True)

    c4, c5 = st.columns(2)
    with c4:
        st.plotly_chart(equity_curve(rows), use_container_width=True)
    with c5:
        st.plotly_chart(trade_distribution(rows), use_container_width=True)
    st.plotly_chart(drawdown_chart(rows), use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="MarketPilot AI", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
    st.markdown(inject_custom_css(), unsafe_allow_html=True)
    init_app_session()

    engine = get_engine()
    STATE.sync_from_brokers(engine.router)
    status = engine.router.status()
    alp = status["alpaca_paper"]
    market_open = alp.get("health", {}).get("market_open", False) if alp["connected"] else False

    with st.sidebar:
        st.markdown("### MarketPilot AI")
        st.caption("Institutional AI Trading Platform")
        st.markdown(f"**Status:** {STATE.status_label()}")
        st.markdown(f"**Mode:** {MODE}")
        st.markdown(f"**Equity:** ${STATE.account_equity:,.2f}" if STATE.account_equity else "**Equity:** —")
        if REAL_TRADING_ENABLED:
            st.error("Live trading blocked")
        st.markdown("---")
        fs = status["futures_simulator"]
        st.write(f"Futures: ${fs['equity']:,.0f} | Alpaca: {'✅' if alp['connected'] else '❌'}")
        render_system_logs()

    render_top_bar(market_open=market_open, paper_mode=True)

    tabs = st.tabs([
        "Command Center", "Analytics", "Brokers", "Risk Engine",
        "AI Agents", "Trade Journal", "Reports", "Health Monitor", "Settings",
    ])

    with tabs[0]:
        render_command_center(engine)

    with tabs[1]:
        st.subheader("Portfolio Analytics")
        _render_analytics_panel(engine)

    with tabs[2]:
        render_broker_dashboard(engine)

    with tabs[3]:
        render_risk_dashboard(engine)

    with tabs[4]:
        render_agents_view(engine)

    with tabs[5]:
        render_journal_view()

    with tabs[6]:
        render_reports_view()

    with tabs[7]:
        render_health_monitor(engine)

    with tabs[8]:
        render_settings()
