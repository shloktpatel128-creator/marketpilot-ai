"""Model training scaffold — use chronological split only."""

from __future__ import annotations

# Future: load features + labels, train with walk-forward validation.
# NEVER use random train/test split on time-series data.
# Use chronological split: train on past, validate on future windows.


def train(path: str = "storage/training_data.csv") -> str:
    """Placeholder — returns model version when implemented."""
    return "rule-based-v1"
