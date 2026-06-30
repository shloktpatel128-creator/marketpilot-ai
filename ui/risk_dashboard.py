"""Risk Engine dashboard tab."""

from __future__ import annotations

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
from risk.risk_engine import RiskEngine
from storage.database import fetch_decisions


def render_risk_dashboard() -> None:
    st.subheader("Risk Engine")
    st.caption("Final authority on every trade. AI agents cannot override.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Max Risk / Trade", f"{MAX_RISK_PER_TRADE_PCT*100:.1f}%")
    c2.metric("Max Daily Loss", f"${MAX_DAILY_LOSS_USD:,.0f}")
    c3.metric("Min Confidence", f"{MIN_CONFIDENCE_TO_TRADE}%")

    c4, c5, c6 = st.columns(3)
    c4.metric("Min R:R", f"{MIN_REWARD_RISK}")
    c5.metric("Max Trades/Day", MAX_TRADES_PER_DAY)
    c6.metric("Max Positions", MAX_OPEN_POSITIONS)

    st.markdown(f"**Max Drawdown:** {MAX_DRAWDOWN_PCT*100:.0f}%")

    st.markdown("#### Recent Risk Decisions")
    rows = fetch_decisions(50)
    rejected = [r for r in rows if not r.get("approved") and r.get("setup_detected")]
    if rejected:
        for r in rejected[:10]:
            reasons = ", ".join(r.get("rejection_reasons", []))
            st.warning(f"{r['symbol']} ({r['broker_provider']}) — {reasons}")
    else:
        st.info("No recent rejections.")

    st.markdown("#### Risk Checks")
    checks = [
        "Max risk per trade", "Max daily loss", "Max drawdown",
        "Max trades per day", "Max open positions", "Min confidence",
        "Required stop loss", "Min reward/risk", "Data quality",
        "Broker connection", "Duplicate order prevention",
    ]
    for c in checks:
        st.write(f"✓ {c}")

    st.caption(f"RiskEngine class: {RiskEngine.__name__}")
