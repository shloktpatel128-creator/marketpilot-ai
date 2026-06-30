"""Live system logs panel."""

from __future__ import annotations

import streamlit as st

from core.event_log import EVENT_LOG
from ui.app_session import append_scan_log


def render_system_logs(expanded: bool = False) -> None:
    with st.expander("📋 Live System Logs", expanded=expanded):
        text = EVENT_LOG.as_text(80)
        scan_lines = st.session_state.get("scan_log_lines", [])
        if scan_lines:
            text = "\n".join(scan_lines[-80:]) + ("\n" + text if text else "")
        if text.strip():
            st.code(text, language=None)
        else:
            st.caption("No events yet. Run a scan or start the bot.")


def make_step_callback(log_box) -> callable:
    """Return callback that updates a Streamlit placeholder during scan."""

    def _cb(step: str, detail: str) -> None:
        line = f"[{step}] {detail}" if detail else f"[{step}]"
        append_scan_log(line)
        combined = "\n".join(st.session_state.get("scan_log_lines", [])[-40:])
        log_box.code(combined or "Starting…", language=None)

    return _cb
