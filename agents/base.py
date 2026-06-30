"""Base agent — context only, never places trades."""

from __future__ import annotations

from config import AI_CAN_PLACE_TRADES


class BaseAgent:
    name: str = "base"
    can_place_trades: bool = False

    def __init__(self) -> None:
        if AI_CAN_PLACE_TRADES:
            raise RuntimeError("AI agents must never place trades.")

    def run(self, **kwargs) -> str:
        raise NotImplementedError
