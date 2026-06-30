"""Professional empty states — no fake numbers."""

from __future__ import annotations

import streamlit as st

from ui.components import _html


def render_empty_state(title: str, message: str, icon: str = "📭") -> None:
    _html(f"""
<div class="mp-glass" style="text-align:center;padding:40px;">
<p style="font-size:2rem;margin:0;">{icon}</p>
<p class="mp-card-title">{title}</p>
<p style="color:#94A3B8;font-size:0.9rem;">{message}</p>
</div>
""")
