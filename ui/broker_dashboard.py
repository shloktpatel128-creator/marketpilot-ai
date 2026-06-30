"""Broker dashboards — Alpaca Paper and Futures Simulator (isolated)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import FUTURES_COMMISSION, FUTURES_SLIPPAGE_TICKS, MODE
from core.engine import TradingEngine
from ui.empty_state import render_empty_state


def render_broker_dashboard(engine: TradingEngine) -> None:
    status = engine.router.status()
    tab_alp, tab_fut = st.tabs(["Alpaca Paper", "Futures Simulator"])

    with tab_alp:
        _render_alpaca(engine, status["alpaca_paper"])

    with tab_fut:
        _render_futures(engine, status["futures_simulator"])


def _render_alpaca(engine: TradingEngine, alp: dict) -> None:
    st.subheader("Alpaca Paper Trading")
    st.caption("Stocks/ETFs only — paper account. Completely isolated from futures simulator.")

    connected = alp["connected"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Connection", "Connected" if connected else "Disconnected")
    c2.metric("Equity", f"${alp['equity']:,.2f}" if connected else "—")
    c3.metric("Buying Power", f"${alp.get('buying_power', 0):,.2f}" if connected else "—")
    c4.metric("Cash", f"${alp.get('cash', 0):,.2f}" if connected else "—")

    if not connected:
        render_empty_state(
            "Alpaca Paper Not Connected",
            alp.get("error") or "Add ALPACA_API_KEY and ALPACA_SECRET_KEY to .env for paper trading.",
            "🔌",
        )
        return

    health = alp.get("health", {})
    st.caption(
        f"API Health: {'OK' if connected else 'Error'} | "
        f"Market: {'Open' if health.get('market_open') else 'Closed'} | Mode: {MODE}"
    )

    positions = alp.get("position_list", [])
    if positions:
        st.markdown("#### Open Positions")
        st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Open Positions", "Alpaca paper account has no open stock positions.", "📊")

    open_orders = alp.get("open_orders", [])
    if open_orders:
        st.markdown("#### Pending Orders")
        st.dataframe(pd.DataFrame(open_orders), use_container_width=True, hide_index=True)

    recent = alp.get("recent_orders", [])
    if recent:
        st.markdown("#### Recent Executions")
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)

    sym = st.text_input("Run Alpaca scan", "AAPL", key="broker_alp_sym")
    if st.button("Scan via Alpaca Paper", key="broker_alp_scan"):
        with st.spinner(f"Scanning {sym}…"):
            r = engine.scan_symbol(sym.upper(), "alpaca_paper")
        st.json({
            "evaluation_id": r.evaluation_id,
            "setup": r.strategy_signal.setup_detected,
            "approved": r.risk.approved,
            "confidence": r.confidence.confidence,
            "reasons": r.risk.rejection_reasons,
            "order": r.order.message if r.order else None,
        })
        st.rerun()


def _render_futures(engine: TradingEngine, fs: dict) -> None:
    st.subheader("Futures Simulator")
    st.caption("Simulated micro futures — isolated state from Alpaca.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulated Balance", f"${fs.get('balance', 0):,.2f}")
    c2.metric("Equity", f"${fs['equity']:,.2f}")
    c3.metric("Daily P/L", f"${fs['daily_pnl']:,.2f}")
    c4.metric("Open Contracts", fs["positions"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Trades Today", fs.get("trade_count_today", 0))
    c6.metric("Total Commission", f"${fs.get('total_commission', 0):,.2f}")
    c7.metric("Slippage (ticks)", fs.get("slippage_ticks", FUTURES_SLIPPAGE_TICKS))
    c8.metric("Commission/Trade", f"${FUTURES_COMMISSION:.2f}")

    positions = fs.get("open_positions", [])
    if positions:
        st.markdown("#### Open Futures Positions")
        st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Open Futures Positions", "Run a futures scan to open simulated positions.", "📈")

    orders = fs.get("orders", [])
    if orders:
        st.markdown("#### Trade History")
        st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True)

    sym = st.selectbox("Futures symbol", ["MES", "MNQ", "MGC", "MCL", "MYM", "M2K"], key="broker_fut_sym")
    if st.button("Scan via Futures Simulator", key="broker_fut_scan"):
        with st.spinner(f"Scanning {sym}…"):
            r = engine.scan_symbol(sym, "futures_simulator")
        st.json({
            "evaluation_id": r.evaluation_id,
            "setup": r.strategy_signal.setup_detected,
            "approved": r.risk.approved,
            "order": r.order.message if r.order else None,
        })
        st.rerun()
