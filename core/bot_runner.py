"""Background bot loop — started/paused from dashboard."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from core.event_log import EVENT_LOG
from core.scheduler import ScanScheduler
from core.state import STATE

if TYPE_CHECKING:
    from core.engine import TradingEngine


class BotRunner:
    """Runs TradingEngine on an interval when bot is started."""

    _instance: Optional["BotRunner"] = None

    def __init__(self, interval_minutes: int = 15) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._scheduler = ScanScheduler(interval_minutes=interval_minutes)
        self._last_run: Optional[datetime] = None
        self._engine: Optional["TradingEngine"] = None

    @classmethod
    def get(cls) -> "BotRunner":
        if cls._instance is None:
            cls._instance = BotRunner()
        return cls._instance

    def attach_engine(self, engine: "TradingEngine") -> None:
        self._engine = engine

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            EVENT_LOG.info("Scheduler", "Bot loop already active")
            return
        if not self._engine:
            EVENT_LOG.error("Scheduler", "TradingEngine not attached")
            return
        STATE.start()
        self._stop.clear()
        self._scheduler.schedule_next()
        EVENT_LOG.info("Scheduler", "Bot started — automated scans enabled")
        self._thread = threading.Thread(target=self._loop, daemon=True, name="BotRunner")
        self._thread.start()

    def pause(self) -> None:
        STATE.pause()
        self._stop.set()
        EVENT_LOG.info("Scheduler", "Bot paused — no further scheduled scans")

    def _loop(self) -> None:
        while not self._stop.is_set():
            if STATE.running and not STATE.paused and self._engine:
                if self._scheduler.should_run(self._last_run):
                    EVENT_LOG.info("Scheduler", "Running scheduled full scan")
                    try:
                        self._engine.run_full_scan()
                        self._last_run = datetime.utcnow()
                        STATE.touch_scan()
                        self._scheduler.schedule_next()
                        EVENT_LOG.info("Scheduler", f"Next scan at {STATE.next_scan_time}")
                    except Exception as exc:
                        STATE.last_error = str(exc)
                        EVENT_LOG.error("Scheduler", str(exc))
            time.sleep(30)
