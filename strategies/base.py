"""Base strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from storage.schemas import StrategySignal


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        """Analyze features and return setup signal."""
