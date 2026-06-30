"""Trade journal view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from journal.trade_journal import TradeJournal


def render_journal_view() -> None:
    st.subheader("Trade Journal")
    journal = TradeJournal()
    broker = st.selectbox("Filter by broker", ["All", "dry_run", "futures_simulator", "alpaca_paper"])
    b = None if broker == "All" else broker
    rows = journal.get_recent(200, b)
    if not rows:
        st.info("No journal entries yet. Run a scan from Command Center.")
        return
    df = pd.DataFrame(rows)
    cols = [
        "timestamp", "symbol", "broker_provider", "strategy", "action",
        "setup_detected", "approved", "confidence", "risk_score", "order_id",
    ]
    show = [c for c in cols if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)
    with st.expander("Rejection reasons (latest 10)"):
        for r in rows[:10]:
            if r.get("rejection_reasons"):
                st.write(f"**{r['symbol']}** — {r['rejection_reasons']}")
