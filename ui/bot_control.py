"""Command Center — live bot control panel."""

from __future__ import annotations

import streamlit as st

from config import MODE
from core.bot_runner import BotRunner
from core.engine import TradingEngine
from core.state import STATE
from models.model_registry import ModelRegistry
from storage.database import count_today
from ui.app_session import clear_scan_log
from ui.components import _html
from ui.empty_state import render_empty_state
from ui.system_logs import make_step_callback, render_system_logs


def _fmt_money(val: float) -> str:
    return f"${val:,.2f}"


def _fmt_pct(val: float) -> str:
    return f"{val:.1f}%"


def render_command_center(engine: TradingEngine) -> None:
    runner = BotRunner.get()
    runner.attach_engine(engine)
    registry = ModelRegistry()
    counts = count_today()
    snap = STATE.snapshot(engine.router, counts, registry.get_active())

    _html("""
<div class="mp-logo">MarketPilot AI</div>
<div class="mp-logo-title">Trading Bot Command Center</div>
""")

    # Row 1 — core status
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bot Status", snap["bot_status"])
    c2.metric("Mode", snap["mode"])
    c3.metric("Current Broker", snap["current_broker"].replace("_", " ").title())
    c4.metric("Evaluation ID", snap["evaluation_id"])

    # Row 2 — model & timing
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Active Model", snap["model_version"])
    c6.metric("Active Strategy", snap["active_strategy"])
    c7.metric("Last Scan", snap["last_scan_time"])
    c8.metric("Next Scheduled Scan", snap["next_scan_time"])

    # Row 3 — performance
    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Trades Today", snap["trades_today"])
    c10.metric("Rejected Today", snap["rejected_today"])
    c11.metric("Daily P/L", _fmt_money(snap["daily_pnl"]))
    c12.metric("Risk Used", _fmt_pct(snap["risk_used_pct"]))

    # Row 4 — account
    c13, c14, c15, c16 = st.columns(4)
    c13.metric("Account Equity", _fmt_money(snap["account_equity"]) if snap["account_equity"] else "—")
    c14.metric("Buying Power", _fmt_money(snap["buying_power"]) if snap["buying_power"] else "—")
    c15.metric("Open Positions", snap["open_positions"])
    c16.metric("Setups Today", snap["setups_today"])

    if snap["account_equity"] == 0 and snap["trades_today"] == 0:
        render_empty_state(
            "No trading activity yet",
            "Press Run One Scan to execute the full pipeline, or Start Bot for scheduled scans.",
            "🤖",
        )

    # Control buttons
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("▶ Start Bot", type="primary", use_container_width=True, key="btn_start"):
            runner.start()
            st.success("Bot started — scheduled scans active.")
            st.rerun()
    with col_b:
        if st.button("⏸ Pause Bot", use_container_width=True, key="btn_pause"):
            runner.pause()
            st.warning("Bot paused.")
            st.rerun()
    with col_c:
        if st.button("🔍 Run One Scan", use_container_width=True, key="btn_scan"):
            clear_scan_log()
            log_box = st.empty()
            engine.set_step_callback(make_step_callback(log_box))
            with st.spinner("Executing pipeline…"):
                results = engine.run_one_scan()
            engine.set_step_callback(None)
            st.success(f"Scan complete — {len(results)} evaluations logged.")
            for r in results:
                icon = "✅" if r.risk.approved else "🛑"
                st.write(
                    f"{icon} **{r.symbol}** ({r.broker}) — {r.strategy_signal.direction} "
                    f"conf={r.confidence.confidence:.0f}% eval={r.evaluation_id}"
                )
            st.rerun()

    # Live scan log
    render_system_logs(expanded=bool(st.session_state.get("scan_log_lines")))

    # Last scan results detail
    if STATE.last_scan_results:
        with st.expander("Last Scan Results"):
            for r in STATE.last_scan_results:
                st.markdown(
                    f"**{r.symbol}** | {r.broker} | setup={r.strategy_signal.setup_detected} "
                    f"| approved={r.risk.approved} | conf={r.confidence.confidence:.0f}"
                )
                if r.risk.rejection_reasons:
                    st.caption("Rejections: " + "; ".join(r.risk.rejection_reasons[:3]))

    st.caption(f"Mode: {MODE} | Scheduler interval: 15 min | Live trading: disabled")
