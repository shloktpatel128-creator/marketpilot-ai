"""Model version registry."""

from __future__ import annotations

from config import MODEL_AUTO_PROMOTION, MODEL_DIR
from models.confidence_model import DEFAULT_VERSION


class ModelRegistry:
    def __init__(self) -> None:
        self.active_version = DEFAULT_VERSION
        self.promotion_allowed = MODEL_AUTO_PROMOTION

    def get_active(self) -> str:
        return self.active_version

    def promote(self, version: str) -> bool:
        if not self.promotion_allowed:
            return False
        self.active_version = version
        return True
