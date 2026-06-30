"""SQLite persistence for journal entries."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from config import DB_PATH


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)


@contextmanager
def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS trade_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id TEXT,
            broker_provider TEXT,
            symbol TEXT,
            strategy TEXT,
            action TEXT,
            setup_detected INTEGER,
            approved INTEGER,
            rejection_reasons TEXT,
            entry REAL,
            stop_loss REAL,
            take_profit REAL,
            confidence REAL,
            model_version TEXT,
            risk_score REAL,
            market_conditions TEXT,
            news_context TEXT,
            timestamp TEXT,
            order_id TEXT,
            result TEXT,
            pnl REAL
        );
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)


def save_decision(row: Dict[str, Any]) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO trade_decisions (
                evaluation_id, broker_provider, symbol, strategy, action,
                setup_detected, approved, rejection_reasons, entry, stop_loss,
                take_profit, confidence, model_version, risk_score,
                market_conditions, news_context, timestamp, order_id, result, pnl
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row.get("evaluation_id"), row.get("broker_provider"), row.get("symbol"),
                row.get("strategy"), row.get("action"), int(row.get("setup_detected", False)),
                int(row.get("approved", False)), json.dumps(row.get("rejection_reasons", [])),
                row.get("entry"), row.get("stop_loss"), row.get("take_profit"),
                row.get("confidence"), row.get("model_version"), row.get("risk_score"),
                row.get("market_conditions"), row.get("news_context"), row.get("timestamp"),
                row.get("order_id"), row.get("result"), row.get("pnl"),
            ),
        )
        return cur.lastrowid or 0


def fetch_decisions(limit: int = 200, broker: Optional[str] = None) -> List[Dict[str, Any]]:
    return fetch_decisions_filtered(limit=limit, broker=broker)


def fetch_decisions_filtered(
    limit: int = 200,
    broker: Optional[str] = None,
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    approved: Optional[bool] = None,
    date_prefix: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()
    clauses = []
    params: list = []
    if broker:
        clauses.append("broker_provider = ?")
        params.append(broker)
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if strategy:
        clauses.append("strategy = ?")
        params.append(strategy)
    if approved is not None:
        clauses.append("approved = ?")
        params.append(int(approved))
    if date_prefix:
        clauses.append("timestamp LIKE ?")
        params.append(f"{date_prefix}%")
    q = "SELECT * FROM trade_decisions"
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["rejection_reasons"] = json.loads(d.get("rejection_reasons") or "[]")
        d["setup_detected"] = bool(d.get("setup_detected"))
        d["approved"] = bool(d.get("approved"))
        out.append(d)
    return out


def db_health() -> Dict[str, Any]:
    init_db()
    try:
        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM trade_decisions").fetchone()[0]
        return {"ok": True, "entries": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def count_today(field: str = "approved") -> Dict[str, int]:
    init_db()
    from datetime import date
    today = date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM trade_decisions WHERE timestamp LIKE ?",
            (f"{today}%",),
        ).fetchone()[0]
        setups = conn.execute(
            "SELECT COUNT(*) FROM trade_decisions WHERE timestamp LIKE ? AND setup_detected = 1",
            (f"{today}%",),
        ).fetchone()[0]
        approved = conn.execute(
            "SELECT COUNT(*) FROM trade_decisions WHERE timestamp LIKE ? AND approved = 1",
            (f"{today}%",),
        ).fetchone()[0]
        rejected = conn.execute(
            "SELECT COUNT(*) FROM trade_decisions WHERE timestamp LIKE ? AND approved = 0 AND setup_detected = 1",
            (f"{today}%",),
        ).fetchone()[0]
    return {"total": total, "setups": setups, "approved": approved, "rejected": rejected, "trades": approved}
