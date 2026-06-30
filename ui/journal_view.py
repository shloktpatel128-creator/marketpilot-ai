"""Trade journal — connected to SQLite backend."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from storage.database import fetch_decisions_filtered
from ui.empty_state import render_empty_state


def render_journal_view() -> None:
    st.subheader("Trade Journal")
    st.caption("Every scan creates an entry — approved or rejected.")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        broker = st.selectbox("Broker", ["All", "dry_run", "futures_simulator", "alpaca_paper"], key="j_broker")
    with c2:
        symbol = st.text_input("Symbol", "", key="j_symbol").upper() or None
    with c3:
        strategy = st.selectbox("Strategy", ["All", "vwap_momentum", "breakout", "pullback"], key="j_strat")
    with c4:
        approval = st.selectbox("Approval", ["All", "Approved", "Rejected"], key="j_approval")
    with c5:
        filter_date = st.checkbox("Filter date", key="j_use_date")
        date_filter = st.date_input("Date", value=date.today(), key="j_date") if filter_date else None

    b = None if broker == "All" else broker
    s = None if strategy == "All" else strategy
    approved = None
    if approval == "Approved":
        approved = True
    elif approval == "Rejected":
        approved = False
    date_prefix = date_filter.isoformat() if date_filter else None

    rows = fetch_decisions_filtered(
        limit=300, broker=b, symbol=symbol, strategy=s,
        approved=approved, date_prefix=date_prefix,
    )

    if not rows:
        render_empty_state(
            "No Journal Entries",
            "Run a scan from Command Center to create trade decision records.",
            "📓",
        )
        return

    df = pd.DataFrame(rows)
    display_cols = [
        "timestamp", "evaluation_id", "symbol", "broker_provider", "strategy",
        "action", "setup_detected", "approved", "confidence", "risk_score",
        "entry", "stop_loss", "take_profit", "order_id", "result",
    ]
    show = [c for c in display_cols if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    with st.expander("Detail view (latest 5)"):
        for r in rows[:5]:
            st.markdown(f"### {r['symbol']} — {r['timestamp']}")
            st.write(f"**Evaluation ID:** {r.get('evaluation_id')}")
            st.write(f"**Strategy:** {r.get('strategy')} | **Broker:** {r.get('broker_provider')}")
            st.write(f"**Setup:** {r.get('setup_detected')} | **Approved:** {r.get('approved')}")
            st.write(f"**Confidence:** {r.get('confidence')} | **Risk score:** {r.get('risk_score')}")
            if r.get("rejection_reasons"):
                st.write(f"**Rejection:** {', '.join(r['rejection_reasons'])}")
            if r.get("news_context"):
                st.write(f"**AI context:** {r['news_context'][:200]}")
            if r.get("market_conditions"):
                st.write(f"**Data quality:** {r['market_conditions']}")
            st.divider()
