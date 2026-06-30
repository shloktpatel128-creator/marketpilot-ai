"""Simple scan scheduler stub."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from core.state import STATE


class ScanScheduler:
    """Interval-based scheduler for automated scans (Phase 1 stub)."""

    def __init__(self, interval_minutes: int = 15) -> None:
        self.interval_minutes = interval_minutes
        self._callback: Optional[Callable[[], None]] = None

    def set_callback(self, fn: Callable[[], None]) -> None:
        self._callback = fn

    def schedule_next(self) -> str:
        nxt = datetime.utcnow() + timedelta(minutes=self.interval_minutes)
        label = nxt.strftime("%Y-%m-%d %H:%M:%S UTC")
        STATE.next_scan_time = label
        return label

    def should_run(self, last_run: Optional[datetime]) -> bool:
        if not STATE.running or STATE.paused:
            return False
        if last_run is None:
            return True
        return datetime.utcnow() - last_run >= timedelta(minutes=self.interval_minutes)
