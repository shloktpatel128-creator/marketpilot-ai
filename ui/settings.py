"""Settings page — configure without editing code."""

from __future__ import annotations

import os

import streamlit as st

from config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    DEFAULT_CRYPTO_SYMBOLS,
    DEFAULT_FUTURES_SYMBOLS,
    DEFAULT_STOCK_SYMBOLS,
    DISCORD_WEBHOOK_URL,
    MAX_DAILY_LOSS_USD,
    MAX_OPEN_POSITIONS,
    MAX_TRADES_PER_DAY,
    MIN_CONFIDENCE_TO_TRADE,
    MODE,
    OPENAI_API_KEY,
    SCAN_INTERVAL_MINUTES,
)
from storage.database import get_setting, set_setting


def render_settings() -> None:
    st.subheader("Settings")
    st.caption("Configure bot parameters. Changes to .env require restart.")

    tab_env, tab_risk, tab_watch, tab_ai = st.tabs(["Environment", "Risk Limits", "Watchlists", "AI Models"])

    with tab_env:
        st.markdown("#### Current Configuration")
        st.json({
            "MODE": MODE,
            "SCAN_INTERVAL_MINUTES": SCAN_INTERVAL_MINUTES,
            "ALPACA_CONFIGURED": bool(ALPACA_API_KEY and ALPACA_SECRET_KEY),
            "OPENAI_CONFIGURED": bool(OPENAI_API_KEY),
            "DISCORD_CONFIGURED": bool(DISCORD_WEBHOOK_URL),
        })
        st.info("Edit `.env` for API keys: ALPACA_API_KEY, ALPACA_SECRET_KEY, OPENAI_API_KEY, DISCORD_WEBHOOK_URL")

        custom_interval = st.number_input("Scan interval (minutes)", min_value=1, max_value=1440,
                                          value=int(get_setting("scan_interval", str(SCAN_INTERVAL_MINUTES))))
        if st.button("Save scan interval"):
            set_setting("scan_interval", str(custom_interval))
            st.success(f"Saved — restart bot for interval {custom_interval} min")

    with tab_risk:
        st.metric("Max Daily Loss", f"${MAX_DAILY_LOSS_USD:,.0f}")
        st.metric("Max Trades/Day", MAX_TRADES_PER_DAY)
        st.metric("Max Open Positions", MAX_OPEN_POSITIONS)
        st.metric("Min Confidence", f"{MIN_CONFIDENCE_TO_TRADE}%")
        st.caption("Risk limits are set in config.py / .env")

    with tab_watch:
        st.markdown("#### Default Watchlists")
        st.write("**Stocks:**", ", ".join(DEFAULT_STOCK_SYMBOLS))
        st.write("**Futures:**", ", ".join(DEFAULT_FUTURES_SYMBOLS))
        st.write("**Crypto:**", ", ".join(DEFAULT_CRYPTO_SYMBOLS))
        custom = st.text_area("Custom watchlist (comma-separated)", get_setting("custom_watchlist", ""))
        if st.button("Save watchlist"):
            set_setting("custom_watchlist", custom)
            st.success("Watchlist saved")

    with tab_ai:
        st.markdown("#### AI Configuration")
        st.write(f"OpenAI: {'Configured' if OPENAI_API_KEY else 'Not configured — using lexicon sentiment'}")
        st.write("Model: gpt-4o-mini (via OPENAI_MODEL env)")
        st.write("Agent pipeline: 10 agents + CIO synthesis")
        st.write("Confidence engine: ai-weighted-v2")
