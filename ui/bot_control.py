"""Command Center — bot status and controls."""

from __future__ import annotations

import streamlit as st

from config import (
    AI_CAN_PLACE_TRADES,
    DEFAULT_FUTURES_SYMBOLS,
    DEFAULT_STOCK_SYMBOLS,
    EVALUATION_MODE,
    MODE,
    PAPER_TRADING_ONLY,
    REAL_TRADING_ENABLED,
)
from core.engine import TradingEngine
from core.state import STATE
from models.model_registry import ModelRegistry
from storage.database import count_today
from ui.components import _html


def render_command_center(engine: TradingEngine) -> None:
    STATE.sync_from_brokers(engine.router)
    counts = count_today()
    registry = ModelRegistry()

    _html("""
<div class="mp-logo">MarketPilot AI</div>
<div class="mp-logo-title">Trading Bot Command Center</div>
""")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bot Status", STATE.status_label())
    c2.metric("Mode", MODE)
    c3.metric("Evaluation ID", STATE.evaluation_id)
    c4.metric("Model", registry.get_active())

    if EVALUATION_MODE:
        st.info(f"Evaluation Mode — Day {STATE.evaluation_day} / {STATE.evaluation_days_total}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Setups Today", counts["setups"])
    c6.metric("Trades Today", counts["trades"])
    c7.metric("Rejections Today", counts["rejected"])
    c8.metric("Daily P/L", f"${STATE.daily_pnl:,.2f}")

    st.caption(f"Last scan: {STATE.last_scan_time or 'Never'} | Stocks: {', '.join(DEFAULT_STOCK_SYMBOLS[:3])} | Futures: {', '.join(DEFAULT_FUTURES_SYMBOLS[:2])}")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("▶ Start Bot", type="primary", use_container_width=True):
            STATE.start()
            st.success("Bot started (paused scans until you run one).")
    with col_b:
        if st.button("⏸ Pause Bot", use_container_width=True):
            STATE.pause()
            st.warning("Bot paused.")
    with col_c:
        if st.button("🔍 Run One Scan", use_container_width=True):
            with st.spinner("Running full scan pipeline…"):
                results = engine.run_full_scan()
            st.success(f"Scan complete — {len(results)} symbol/broker evaluations.")
            for r in results:
                icon = "✅" if r.risk.approved else "🛑"
                st.write(f"{icon} **{r.symbol}** ({r.broker}) — {r.strategy_signal.direction} conf={r.confidence.confidence:.0f}%")

    with st.expander("Safety Configuration"):
        st.write({
            "MODE": MODE,
            "REAL_TRADING_ENABLED": REAL_TRADING_ENABLED,
            "PAPER_TRADING_ONLY": PAPER_TRADING_ONLY,
            "AI_CAN_PLACE_TRADES": AI_CAN_PLACE_TRADES,
            "Active Brokers": STATE.active_brokers,
        })
