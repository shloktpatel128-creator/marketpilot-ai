"""MarketPilot AI — Bot Control Panel Dashboard."""

from __future__ import annotations

import streamlit as st

from agents import run_all_agents
from config import AI_CAN_PLACE_TRADES, MODE, REAL_TRADING_ENABLED
from core.engine import TradingEngine
from core.logger import setup_logging
from core.state import STATE
from models.model_registry import ModelRegistry
from notifications import discord_notifier
from storage.database import init_db
from ui.bot_control import render_command_center
from ui.components import render_top_bar
from ui.journal_view import render_journal_view
from ui.reports_view import render_reports_view
from ui.risk_dashboard import render_risk_dashboard
from ui.theme import inject_custom_css


@st.cache_resource
def get_engine() -> TradingEngine:
    setup_logging()
    init_db()
    discord_notifier.notify("Bot Startup", f"MarketPilot AI dashboard loaded — mode {MODE}", "info")
    return TradingEngine()


def main() -> None:
    st.set_page_config(
        page_title="MarketPilot AI — Bot Control Panel",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(inject_custom_css(), unsafe_allow_html=True)

    engine = get_engine()
    STATE.sync_from_brokers(engine.router)
    status = engine.router.status()

    with st.sidebar:
        st.markdown("### MarketPilot AI")
        st.caption("Automated AI-Assisted Trading Bot")
        st.markdown(f"**Status:** {STATE.status_label()}")
        st.markdown(f"**Mode:** {MODE}")
        if REAL_TRADING_ENABLED:
            st.error("⚠️ REAL TRADING FLAG ON — blocked by architecture")
        st.markdown("---")
        st.markdown("**Brokers**")
        st.write(f"• Dry Run: ✅")
        st.write(f"• Futures Sim: ✅ (${status['futures_simulator']['equity']:,.0f})")
        alp = status["alpaca_paper"]
        alp_icon = "✅" if alp["connected"] else "❌"
        st.write(f"• Alpaca Paper: {alp_icon}")
        if alp.get("error"):
            st.caption(alp["error"])

    render_top_bar(market_open=True, paper_mode=True)

    tabs = st.tabs([
        "Command Center",
        "Futures Simulator",
        "Alpaca Paper",
        "Risk Engine",
        "AI Agents",
        "Trade Journal",
        "Reports",
        "Model Performance",
        "Settings",
    ])

    with tabs[0]:
        render_command_center(engine)

    with tabs[1]:
        st.subheader("Futures Simulator")
        fs = status["futures_simulator"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Equity", f"${fs['equity']:,.2f}")
        c2.metric("Open Positions", fs["positions"])
        c3.metric("Daily P/L", f"${fs['daily_pnl']:,.2f}")
        sym = st.selectbox("Symbol", ["MES", "MNQ", "MGC", "MCL", "MYM", "M2K"])
        if st.button("Run Futures Scan", key="fut_scan"):
            with st.spinner(f"Scanning {sym}…"):
                r = engine.scan_symbol(sym, "futures_simulator")
            status = engine.router.status()
            st.json({
                "setup": r.strategy_signal.setup_detected,
                "direction": r.strategy_signal.direction,
                "approved": r.risk.approved,
                "confidence": r.confidence.confidence,
                "reasons": r.risk.rejection_reasons,
                "order": r.order.message if r.order else None,
                "evaluation_id": r.evaluation_id,
            })
            st.caption(f"Futures equity: ${status['futures_simulator']['equity']:,.2f}")

    with tabs[2]:
        st.subheader("Alpaca Paper Trading")
        alp = status["alpaca_paper"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Connected", "Yes" if alp["connected"] else "No")
        c2.metric("Equity", f"${alp['equity']:,.2f}")
        c3.metric("Positions", alp["positions"])
        if alp.get("error"):
            st.warning(alp["error"])
        sym = st.text_input("Stock symbol", "AAPL")
        if st.button("Run Alpaca Scan", key="alp_scan"):
            with st.spinner(f"Scanning {sym}…"):
                r = engine.scan_symbol(sym.upper(), "alpaca_paper")
            status = engine.router.status()
            st.json({
                "setup": r.strategy_signal.setup_detected,
                "approved": r.risk.approved,
                "confidence": r.confidence.confidence,
                "reasons": r.risk.rejection_reasons,
                "evaluation_id": r.evaluation_id,
            })
            alp = status["alpaca_paper"]
            if not alp["connected"]:
                st.warning(alp.get("error") or "Alpaca paper requires API keys in .env")

    with tabs[3]:
        render_risk_dashboard()

    with tabs[4]:
        st.subheader("AI Agents (Shadow Mode)")
        st.caption("Agents provide context only — they never place trades.")
        st.write(f"AI_CAN_PLACE_TRADES = {AI_CAN_PLACE_TRADES}")
        if st.button("Run Agent Context Scan"):
            ctx = {"symbol": "SPY", "version": ModelRegistry().get_active()}
            out = run_all_agents(ctx)
            for name, text in out.items():
                st.markdown(f"**{name}** — {text}")

    with tabs[5]:
        render_journal_view()

    with tabs[6]:
        render_reports_view()

    with tabs[7]:
        st.subheader("Model Performance")
        reg = ModelRegistry()
        st.write(f"Active model: **{reg.get_active()}**")
        st.info("Model training and walk-forward validation scaffolding ready. Auto-promotion disabled.")

    with tabs[8]:
        st.subheader("Settings")
        st.json({
            "MODE": MODE,
            "REAL_TRADING_ENABLED": REAL_TRADING_ENABLED,
            "AI_CAN_PLACE_TRADES": AI_CAN_PLACE_TRADES,
            "evaluation_id": STATE.evaluation_id,
            "evaluation_mode": STATE.evaluation_mode,
        })
