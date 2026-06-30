"""Central bot runtime state — single source of truth for dashboard."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import DEFAULT_STRATEGY, EVALUATION_DAYS, EVALUATION_MODE, MAX_DAILY_LOSS_USD, MODE


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
    active_strategy: str = DEFAULT_STRATEGY
    current_broker: str = "dry_run"
    active_symbols_stocks: list = field(default_factory=list)
    active_symbols_futures: list = field(default_factory=list)
    daily_pnl: float = 0.0
    risk_used_pct: float = 0.0
    account_equity: float = 0.0
    open_positions: int = 0
    buying_power: float = 0.0
    last_error: Optional[str] = None
    agent_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_scan_results: List[Any] = field(default_factory=list)

    def start(self) -> None:
        self.running = True
        self.paused = False
        self.last_error = None

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
        fs = status["futures_simulator"]
        alp = status["alpaca_paper"]
        dry = status["dry_run"]

        self.daily_pnl = fs["daily_pnl"] + alp["daily_pnl"]
        self.account_equity = fs["equity"] + alp["equity"]
        self.buying_power = alp.get("buying_power", 0) + fs.get("equity", 0)
        self.open_positions = fs["positions"] + alp["positions"]
        self.active_symbols_stocks = [o["symbol"] for o in dry.get("orders", [])]
        self.active_symbols_futures = fs.get("position_symbols", [])

        loss_used = abs(min(0.0, self.daily_pnl))
        self.risk_used_pct = min(100.0, (loss_used / max(MAX_DAILY_LOSS_USD, 1)) * 100)

        if alp["connected"]:
            self.current_broker = "alpaca_paper"
        elif fs["positions"] > 0:
            self.current_broker = "futures_simulator"
        else:
            self.current_broker = "dry_run"

    def snapshot(self, router, counts: dict, model_version: str) -> Dict[str, Any]:
        """Dashboard-ready metrics dict."""
        self.sync_from_brokers(router)
        st = router.status()
        return {
            "bot_status": self.status_label(),
            "mode": self.mode,
            "current_broker": self.current_broker,
            "evaluation_id": self.evaluation_id,
            "model_version": model_version,
            "active_strategy": self.active_strategy,
            "last_scan_time": self.last_scan_time or "—",
            "next_scan_time": self.next_scan_time or "—",
            "trades_today": counts.get("trades", 0),
            "rejected_today": counts.get("rejected", 0),
            "setups_today": counts.get("setups", 0),
            "daily_pnl": self.daily_pnl,
            "risk_used_pct": self.risk_used_pct,
            "account_equity": self.account_equity,
            "open_positions": self.open_positions,
            "buying_power": self.buying_power,
            "alpaca_connected": st["alpaca_paper"]["connected"],
            "futures_equity": st["futures_simulator"]["equity"],
            "alpaca_equity": st["alpaca_paper"]["equity"],
        }


STATE = BotState()
