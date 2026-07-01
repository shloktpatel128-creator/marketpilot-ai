"""Backward-compatible wrapper — delegates to ConfidenceEngine."""

from __future__ import annotations

import pandas as pd

from models.confidence_engine import ConfidenceEngine, ConfidenceInputs
from storage.schemas import ConfidenceResult, StrategySignal

DEFAULT_VERSION = "ai-weighted-v2"


class ConfidenceModel:
    """Legacy interface — uses weighted AI confidence engine."""

    def __init__(self) -> None:
        self._engine = ConfidenceEngine()
        self.model_version = DEFAULT_VERSION

    def score(self, df: pd.DataFrame, signal: StrategySignal) -> ConfidenceResult:
        result = self._engine.score(ConfidenceInputs(
            df=df, direction=signal.direction if signal.setup_detected else "HOLD",
        ))
        self.model_version = result.model_version
        return result
