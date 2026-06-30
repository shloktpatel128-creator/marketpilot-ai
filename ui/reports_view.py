"""Reports view — daily and weekly."""

from __future__ import annotations

import streamlit as st

from journal.reports import format_report_text, generate_daily_report, generate_weekly_report


def render_reports_view() -> None:
    st.subheader("Reports")
    broker = st.selectbox("Broker track", ["all", "dry_run", "futures_simulator", "alpaca_paper"], key="report_broker")
    b = None if broker == "all" else broker

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Daily Report"):
            report = generate_daily_report(b)
            st.code(format_report_text(report))
    with col2:
        if st.button("Generate Weekly Report"):
            report = generate_weekly_report(b)
            st.code(format_report_text(report))

    st.markdown("#### Alpaca Paper Report")
    st.code(format_report_text(generate_daily_report("alpaca_paper")))
    st.markdown("#### Futures Simulator Report")
    st.code(format_report_text(generate_daily_report("futures_simulator")))
