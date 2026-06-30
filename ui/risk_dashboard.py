"""Risk Engine dashboard — live exposure and rejections."""

from __future__ import annotations

from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st

from config import (
    MAX_DAILY_LOSS_USD,
    MAX_DRAWDOWN_PCT,
    MAX_OPEN_POSITIONS,
    MAX_RISK_PER_TRADE_PCT,
    MAX_TRADES_PER_DAY,
    MIN_CONFIDENCE_TO_TRADE,
    MIN_REWARD_RISK,
)
from core.engine import TradingEngine
from core.state import STATE
from storage.database import fetch_decisions_filtered
from ui.empty_state import render_empty_state


def render_risk_dashboard(engine: TradingEngine) -> None:
    st.subheader("Risk Engine")
    st.caption("Final authority on every trade. AI agents cannot override.")

    STATE.sync_from_brokers(engine.router)
    status = engine.router.status()
    today = date.today().isoformat()
    today_rows = fetch_decisions_filtered(limit=500, date_prefix=today)
    rejected_today = [r for r in today_rows if r.get("setup_detected") and not r.get("approved")]

    # Live exposure
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Daily P/L", f"${STATE.daily_pnl:,.2f}")
    c2.metric("Risk Used", f"{STATE.risk_used_pct:.1f}%")
    c3.metric("Open Positions", STATE.open_positions)
    c4.metric("Buying Power", f"${STATE.buying_power:,.2f}" if STATE.buying_power else "—")

    c5, c6, c7, c8 = st.columns(4)
    loss_remaining = MAX_DAILY_LOSS_USD + min(0, STATE.daily_pnl)
    c5.metric("Max Daily Loss Remaining", f"${max(0, loss_remaining):,.2f}")
    c6.metric("Confidence Threshold", f"{MIN_CONFIDENCE_TO_TRADE}%")
    c7.metric("Rejected Today", len(rejected_today))
    c8.metric("Drawdown Limit", f"{MAX_DRAWDOWN_PCT*100:.0f}%")

    st.markdown("#### Today's Rejected Trades")
    if rejected_today:
        for r in rejected_today[:15]:
            reasons = ", ".join(r.get("rejection_reasons", []))
            st.warning(f"**{r['symbol']}** ({r['broker_provider']}) — {reasons}")
    else:
        render_empty_state("No Rejections Today", "Rejected setups will appear here after scans.", "✅")

    st.markdown("#### Rejection Reason Breakdown")
    reason_counts = Counter()
    for r in rejected_today:
        for reason in r.get("rejection_reasons", []):
            reason_counts[reason] += 1
    if reason_counts:
        st.bar_chart(pd.Series(dict(reason_counts.most_common(10))))
    else:
        st.caption("No rejection data yet.")

    st.markdown("#### Configured Risk Rules")
    rules = [
        ("Max risk per trade", f"{MAX_RISK_PER_TRADE_PCT*100:.1f}%"),
        ("Max daily loss", f"${MAX_DAILY_LOSS_USD:,.0f}"),
        ("Max drawdown", f"{MAX_DRAWDOWN_PCT*100:.0f}%"),
        ("Max trades per day", str(MAX_TRADES_PER_DAY)),
        ("Max open positions", str(MAX_OPEN_POSITIONS)),
        ("Min confidence", f"{MIN_CONFIDENCE_TO_TRADE}%"),
        ("Min reward/risk", str(MIN_REWARD_RISK)),
        ("Required stop loss", "Yes"),
        ("Duplicate order prevention", "Yes"),
        ("Data quality check", "Yes"),
        ("Broker connection check", "Yes"),
        ("Live trading", "Blocked"),
    ]
    st.dataframe(
        pd.DataFrame(rules, columns=["Rule", "Value"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Broker Exposure")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Alpaca Paper**")
        alp = status["alpaca_paper"]
        st.write(f"Equity: ${alp['equity']:,.2f}" if alp["connected"] else "Not connected")
        st.write(f"Positions: {alp['positions']}")
    with col_b:
        st.markdown("**Futures Simulator**")
        fs = status["futures_simulator"]
        st.write(f"Equity: ${fs['equity']:,.2f}")
        st.write(f"Contracts: {fs['positions']}")
