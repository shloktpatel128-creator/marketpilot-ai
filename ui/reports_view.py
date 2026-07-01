"""Reports page — daily/weekly stats and AI briefings."""

from __future__ import annotations

import streamlit as st

from analytics.performance import compute_performance
from journal.reports import ai_summary, format_report_text, generate_daily_report, generate_weekly_report
from services.briefing import generate_daily_briefing
from services.watchlist import scan_watchlist
from storage.database import export_decisions_csv
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
        perf = compute_performance(b)
        st.markdown(f"**Sharpe:** {perf.sharpe_ratio:.2f} | **Sortino:** {perf.sortino_ratio:.2f} | **Max DD:** {perf.max_drawdown:.1f}%")

    st.markdown("---")
    st.markdown("#### AI Daily Briefing")
    if st.button("Generate Market Briefing"):
        st.markdown(generate_daily_briefing())

    st.markdown("#### Watchlist Rankings")
    if st.button("Scan Watchlist"):
        for e in scan_watchlist(limit=10):
            st.write(f"**{e.symbol}** ({e.asset_class}) — score {e.opportunity_score:.0f} | {e.summary}")

    if st.button("Export Journal CSV"):
        path = "storage/journal_export.csv"
        n = export_decisions_csv(path)
        st.success(f"Exported {n} rows to {path}")
