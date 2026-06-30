"""Logging configuration."""

from __future__ import annotations

import logging
import os


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/marketpilot.log"),
        ],
    )
    return logging.getLogger("marketpilot")
