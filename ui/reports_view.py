"""Reports page — daily/weekly stats from journal."""

from __future__ import annotations

import streamlit as st

from journal.reports import ai_summary, format_report_text, generate_daily_report, generate_weekly_report
from ui.empty_state import render_empty_state


def render_reports_view() -> None:
    st.subheader("Reports")
    broker = st.selectbox("Broker track", ["all", "dry_run", "futures_simulator", "alpaca_paper"], key="report_broker")
    b = None if broker == "all" else broker

    col1, col2 = st.columns(2)
    with col1:
        daily = generate_daily_report(b)
    with col2:
        weekly = generate_weekly_report(b)

    if daily["total_setups"] == 0 and daily["total_trades"] == 0:
        render_empty_state(
            "No Report Data",
            "Reports populate after scans create journal entries.",
            "📊",
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Setups (today)", daily["total_setups"])
        c2.metric("Trades (today)", daily["total_trades"])
        c3.metric("Win Rate", f"{daily['win_rate']:.1f}%")
        c4.metric("Expectancy", f"${daily['expectancy']:.2f}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Rejected", daily["rejected_trades"])
        c6.metric("Avg Win", f"${daily['avg_win']:.2f}")
        c7.metric("Avg Loss", f"${daily['avg_loss']:.2f}")
        pf = daily.get("profit_factor")
        c8.metric("Profit Factor", f"{pf:.2f}" if pf is not None else "—")

        st.markdown("#### AI Summary")
        st.info(ai_summary(daily))

    tab_d, tab_w = st.tabs(["Daily Report", "Weekly Report"])
    with tab_d:
        st.code(format_report_text(daily))
        if daily.get("by_strategy"):
            st.markdown("**By Strategy:**")
            st.json(daily["by_strategy"])
        if daily.get("by_broker"):
            st.markdown("**By Broker:**")
            st.json(daily["by_broker"])
    with tab_w:
        st.code(format_report_text(weekly))
        st.caption(f"Total decisions (7d): {weekly.get('total_decisions', 0)}")

    st.markdown("---")
    st.markdown("#### Broker-Specific Reports")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Alpaca Paper**")
        st.code(format_report_text(generate_daily_report("alpaca_paper")))
    with col_b:
        st.markdown("**Futures Simulator**")
        st.code(format_report_text(generate_daily_report("futures_simulator")))
