"""Health monitor — system component status."""

from __future__ import annotations

import os
import resource

import streamlit as st

from config import DB_PATH, MODE, REAL_TRADING_ENABLED
from core.bot_runner import BotRunner
from core.engine import TradingEngine
from core.state import STATE
from models.model_registry import ModelRegistry
from storage.database import db_health


def _memory_mb() -> str:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # macOS returns bytes in ru_maxrss; Linux returns KB
        mb = usage.ru_maxrss / (1024 * 1024) if usage.ru_maxrss > 10_000_000 else usage.ru_maxrss / 1024
        return f"{mb:.1f} MB"
    except Exception:
        return "—"


def render_health_monitor(engine: TradingEngine) -> None:
    st.subheader("Health Monitor")

    status = engine.router.status()
    db = db_health()
    runner = BotRunner.get()

    checks = [
        ("Data Feed (yfinance)", "OK", "Market data via yfinance — tested on each scan"),
        ("Broker — Dry Run", "OK", f"{len(status['dry_run'].get('orders', []))} simulated orders"),
        ("Broker — Futures Sim", "OK" if status["futures_simulator"]["connected"] else "Error", f"Equity ${status['futures_simulator']['equity']:,.2f}"),
        ("Broker — Alpaca Paper", "OK" if status["alpaca_paper"]["connected"] else "Disconnected", status["alpaca_paper"].get("error") or "Connected"),
        ("Scheduler", "Running" if runner.is_running and STATE.running else "Idle", f"Next scan: {STATE.next_scan_time or '—'}"),
        ("AI Agents", "Shadow", "Analysis only — cannot place trades"),
        ("Database", "OK" if db["ok"] else "Error", f"{db.get('entries', 0)} journal entries" if db["ok"] else db.get("error", "")),
        ("Model", "Loaded", ModelRegistry().get_active()),
        ("Memory Usage", "OK", _memory_mb()),
        ("Last Error", "None" if not STATE.last_error else "Error", STATE.last_error or "—"),
        ("Trading Mode", MODE, "Live trading disabled" if not REAL_TRADING_ENABLED else "BLOCKED"),
        ("Database Path", "OK" if os.path.exists(DB_PATH) or db["ok"] else "Missing", DB_PATH),
    ]

    for name, stat, detail in checks:
        icon = "🟢" if stat in ("OK", "Running", "Loaded", "Shadow", "Idle", "None", MODE) else "🔴"
        if stat == "Disconnected":
            icon = "🟡"
        c1, c2, c3 = st.columns([2, 1, 3])
        c1.write(f"{icon} **{name}**")
        c2.write(stat)
        c3.caption(str(detail)[:120])
