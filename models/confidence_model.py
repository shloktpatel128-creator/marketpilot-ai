"""Rule-based / trained confidence scoring."""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from config import MODEL_DIR
from storage.schemas import ConfidenceResult, StrategySignal

DEFAULT_VERSION = "rule-based-v1"


class ConfidenceModel:
    """Loads trained model if present; otherwise rule-based scoring."""

    def __init__(self) -> None:
        self.model_version = DEFAULT_VERSION
        self._model = None
        self._try_load()

    def _try_load(self) -> None:
        path = os.path.join(MODEL_DIR, "confidence_model.pkl")
        if os.path.exists(path):
            try:
                import joblib  # optional
                self._model = joblib.load(path)
                self.model_version = "trained-v1"
            except Exception:
                pass

    def score(self, df: pd.DataFrame, signal: StrategySignal) -> ConfidenceResult:
        if not signal.setup_detected:
            return ConfidenceResult(0, self.model_version, "No setup — confidence 0.")

        if self._model is not None:
            # Placeholder for trained inference
            pass

        row = df.iloc[-1]
        score = 50.0
        reasons = []

        if signal.direction == "BUY":
            if float(row.get("RSI", 50) or 50) < 60:
                score += 10
                reasons.append("RSI not overbought")
            if float(row.get("Momentum_10", 0) or 0) > 0:
                score += 10
                reasons.append("Positive momentum")
        elif signal.direction == "SELL":
            if float(row.get("RSI", 50) or 50) > 40:
                score += 10
            if float(row.get("Momentum_10", 0) or 0) < 0:
                score += 10

        if signal.reward_risk >= 2:
            score += 15
            reasons.append(f"Strong R:R ({signal.reward_risk})")
        elif signal.reward_risk >= 1.5:
            score += 8

        vol = float(row.get("Volume_Ratio", 1) or 1)
        if vol >= 1.2:
            score += 5
            reasons.append("Volume confirmation")

        score = min(100, max(0, score))
        expl = f"Rule-based confidence {score:.0f}/100. " + "; ".join(reasons[:4])
        return ConfidenceResult(score, self.model_version, expl)
