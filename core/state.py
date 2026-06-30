"""Central bot runtime state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import EVALUATION_DAYS, EVALUATION_MODE, MODE


@dataclass
class BotState:
    running: bool = False
    paused: bool = True
    mode: str = MODE
    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    evaluation_mode: bool = EVALUATION_MODE
    evaluation_day: int = 1
    evaluation_days_total: int = EVALUATION_DAYS
    frozen_model_version: str = "rule-based-v1"
    last_scan_time: Optional[str] = None
    next_scan_time: Optional[str] = None
    active_brokers: list = field(default_factory=lambda: ["dry_run", "futures_simulator", "alpaca_paper"])
    active_symbols_stocks: list = field(default_factory=list)
    active_symbols_futures: list = field(default_factory=list)
    daily_pnl: float = 0.0
    risk_used_pct: float = 0.0

    def start(self) -> None:
        self.running = True
        self.paused = False

    def pause(self) -> None:
        self.paused = True
        self.running = False

    def status_label(self) -> str:
        if self.paused or not self.running:
            return "Paused"
        return "Running"

    def touch_scan(self) -> None:
        self.last_scan_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def sync_from_brokers(self, router) -> None:
        """Pull live metrics from broker router into bot state."""
        status = router.status()
        self.daily_pnl = (
            status["futures_simulator"]["daily_pnl"]
            + status["alpaca_paper"]["daily_pnl"]
        )
        self.active_symbols_stocks = [
            o["symbol"] for o in router.dry_run.state.get("orders", [])
        ]
        self.active_symbols_futures = [p.symbol for p in router.futures.state.positions]


# Singleton used by engine and dashboard
STATE = BotState()
