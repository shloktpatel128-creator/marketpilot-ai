"""Thread-safe event log for live dashboard streaming."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, List, Optional


@dataclass
class LogEntry:
    timestamp: str
    level: str
    step: str
    message: str


class EventLog:
    def __init__(self, max_size: int = 500) -> None:
        self._entries: Deque[LogEntry] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add(self, step: str, message: str = "", level: str = "info") -> None:
        entry = LogEntry(
            timestamp=datetime.utcnow().strftime("%H:%M:%S"),
            level=level,
            step=step,
            message=message,
        )
        with self._lock:
            self._entries.append(entry)

    def info(self, step: str, message: str = "") -> None:
        self.add(step, message, "info")

    def warn(self, step: str, message: str = "") -> None:
        self.add(step, message, "warn")

    def error(self, step: str, message: str = "") -> None:
        self.add(step, message, "error")

    def trade(self, step: str, message: str = "") -> None:
        self.add(step, message, "trade")

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def get_entries(self, limit: Optional[int] = None) -> List[LogEntry]:
        with self._lock:
            items = list(self._entries)
        if limit:
            return items[-limit:]
        return items

    def as_text(self, limit: int = 50) -> str:
        lines = []
        for e in self.get_entries(limit):
            msg = f" [{e.message}]" if e.message else ""
            lines.append(f"{e.timestamp} [{e.level.upper()}] {e.step}{msg}")
        return "\n".join(lines)


EVENT_LOG = EventLog()
