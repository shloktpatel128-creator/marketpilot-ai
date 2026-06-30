"""
Legacy compatibility shim.

DEPRECATED: Use brokers.alpaca_paper.AlpacaPaperBroker via TradingEngine.
Live trading is permanently blocked — paper-only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from brokers.alpaca_paper import AlpacaPaperBroker


class PaperTrader:
    """Deprecated wrapper — delegates to AlpacaPaperBroker (paper-only)."""

    def __init__(self) -> None:
        self._broker = AlpacaPaperBroker()

    @property
    def is_connected(self) -> bool:
        return self._broker.connected

    @property
    def trading_mode(self) -> str:
        return "paper"

    @property
    def init_error(self) -> Optional[str]:
        return self._broker.init_error

    def get_account_status(self) -> Dict[str, Any]:
        self._broker._sync_account()
        return {
            "connected": self._broker.connected,
            "mode": "paper",
            "equity": self._broker.state.equity,
            "cash": self._broker.state.cash,
            "buying_power": self._broker.state.buying_power,
            "daily_pnl": self._broker.state.daily_pnl,
            "message": self._broker.init_error or "Paper account ready.",
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        return self._broker.get_positions()

    def place_trade(self, symbol: str, side: str, notional: float = 1000.0, **kwargs):
        return self._broker.place_order(symbol, side, notional)
