"""
Streamlit session-state helpers.

Best practice:
- Canonical keys (selected_ticker, selected_period, …) hold app logic state.
- Widget keys are NEVER written after the widget is instantiated.
- Programmatic updates (watchlist, range buttons, nav) write canonical keys only.
"""

from __future__ import annotations

import streamlit as st

from config import VALID_INTERVALS, VALID_PERIODS

# Canonical session keys — safe to read/write anywhere except never overwrite widget keys
KEY_TICKER = "selected_ticker"
KEY_PERIOD = "selected_period"
KEY_INTERVAL = "selected_interval"
KEY_PAGE = "active_page"
KEY_TRADE_LOG = "paper_trade_log"
KEY_BOT_ACTIVE = "bot_active"
KEY_LAST_SCAN = "last_scan_time"

DEFAULTS = {
    KEY_TICKER: "AAPL",
    KEY_PERIOD: "1y",
    KEY_INTERVAL: "1d",
    KEY_PAGE: "Overview",
    KEY_TRADE_LOG: [],
    KEY_BOT_ACTIVE: True,
    KEY_LAST_SCAN: "",
}


def init_session_state() -> None:
    """Initialize canonical keys once. Call at app startup before any widgets."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_ticker() -> str:
    return str(st.session_state.get(KEY_TICKER, "AAPL")).strip().upper()


def set_ticker(symbol: str) -> None:
    st.session_state[KEY_TICKER] = symbol.strip().upper()


def set_page(page: str) -> None:
    st.session_state[KEY_PAGE] = page


def set_period(period: str) -> None:
    if period in VALID_PERIODS:
        st.session_state[KEY_PERIOD] = period


def set_interval(interval: str) -> None:
    if interval in VALID_INTERVALS:
        st.session_state[KEY_INTERVAL] = interval


def period_index() -> int:
    p = st.session_state.get(KEY_PERIOD, "1y")
    return VALID_PERIODS.index(p) if p in VALID_PERIODS else 3


def interval_index() -> int:
    i = st.session_state.get(KEY_INTERVAL, "1d")
    return VALID_INTERVALS.index(i) if i in VALID_INTERVALS else 0


def sync_ticker_from_input(raw: str) -> str:
    """Update canonical ticker from text input return value (not a widget key)."""
    ticker = (raw or "AAPL").strip().upper()
    st.session_state[KEY_TICKER] = ticker
    return ticker


def sync_period_from_widget(value: str) -> str:
    """Update canonical period from selectbox return value (no widget key used)."""
    if value in VALID_PERIODS:
        st.session_state[KEY_PERIOD] = value
    return st.session_state[KEY_PERIOD]


def sync_interval_from_widget(value: str) -> str:
    """Update canonical interval from selectbox return value (no widget key used)."""
    if value in VALID_INTERVALS:
        st.session_state[KEY_INTERVAL] = value
    return st.session_state[KEY_INTERVAL]
