"""Walk-forward validation scaffold."""

from __future__ import annotations

# Chronological validation only:
# 1. Split data by time (e.g. 70% train, 30% test — latest 30%)
# 2. Walk-forward: rolling train window, test on next period
# Do NOT shuffle time-series data.


def validate_model() -> dict:
    return {"status": "not_implemented", "note": "Use walk-forward validation"}
