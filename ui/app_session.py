"""Streamlit session state initialization."""

from __future__ import annotations

import streamlit as st

from core.event_log import EVENT_LOG


def init_app_session() -> None:
    defaults = {
        "scan_log_lines": [],
        "active_tab": "Command Center",
        "bot_runner_attached": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def append_scan_log(line: str) -> None:
    st.session_state.scan_log_lines.append(line)
    if len(st.session_state.scan_log_lines) > 200:
        st.session_state.scan_log_lines = st.session_state.scan_log_lines[-200:]


def clear_scan_log() -> None:
    st.session_state.scan_log_lines = []
    EVENT_LOG.clear()
