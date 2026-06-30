"""Routes orders to isolated broker backends."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from config import MODE, PAPER_TRADING_ONLY, REAL_TRADING_ENABLED
from brokers.alpaca_paper import AlpacaPaperBroker, BrokerOrderResult
from brokers.futures_simulator import FuturesSimulator
from storage.schemas import StrategySignal

logger = logging.getLogger(__name__)


class DryRunBroker:
    name = "dry_run"

    def __init__(self) -> None:
        self.state = {"orders": [], "log": []}

    @property
    def connected(self) -> bool:
        return True

    def place_order(self, symbol: str, side: str, notional: float = 1000, **kwargs) -> BrokerOrderResult:
        oid = str(uuid.uuid4())[:8]
        msg = f"[DRY RUN] Would {side} {symbol} ${notional:.0f}"
        self.state["orders"].append({"id": oid, "symbol": symbol, "side": side, "notional": notional})
        self.state["log"].append(msg)
        logger.info(msg)
        return BrokerOrderResult(True, oid, msg)


class BrokerRouter:
    """Isolated broker tracks — failure in one does not crash others."""

    def __init__(self) -> None:
        self.dry_run = DryRunBroker()
        self.futures = FuturesSimulator()
        self.alpaca = AlpacaPaperBroker()
        self._brokers = {
            "dry_run": self.dry_run,
            "futures_simulator": self.futures,
            "alpaca_paper": self.alpaca,
        }

    def get(self, name: str):
        return self._brokers.get(name)

    def route_order(
        self,
        broker_name: str,
        signal: StrategySignal,
        symbol: str,
        notional: float = 1000.0,
        qty: int = 1,
        current_price: Optional[float] = None,
    ) -> BrokerOrderResult:
        if REAL_TRADING_ENABLED or not PAPER_TRADING_ONLY:
            return BrokerOrderResult(False, message="Live trading blocked by architecture.")
        try:
            if broker_name == "dry_run":
                return self.dry_run.place_order(symbol, signal.direction, notional)

            if broker_name == "futures_simulator":
                if not current_price:
                    return BrokerOrderResult(False, message="No price for futures sim.")
                return self.futures.place_order(
                    symbol, signal.direction, qty=qty, price=current_price,
                    stop_loss=signal.stop_loss, take_profit=signal.take_profit,
                )

            if broker_name == "alpaca_paper":
                if MODE == "DRY_RUN":
                    return self.dry_run.place_order(symbol, signal.direction, notional)
                if not self.alpaca.connected:
                    return BrokerOrderResult(
                        False, message=self.alpaca.init_error or "Alpaca paper not connected.",
                    )
                return self.alpaca.place_order(
                    symbol, signal.direction, notional,
                    stop_loss=signal.stop_loss, take_profit=signal.take_profit,
                )

            return BrokerOrderResult(False, message=f"Unknown broker: {broker_name}")
        except Exception as exc:
            logger.exception("Broker %s failed: %s", broker_name, exc)
            return BrokerOrderResult(False, message=f"Broker error: {exc}")

    def status(self) -> Dict[str, Any]:
        return {
            "dry_run": {"connected": True, "orders": len(self.dry_run.state["orders"])},
            "futures_simulator": {
                "connected": True,
                "equity": self.futures.state.equity,
                "positions": len(self.futures.state.positions),
                "daily_pnl": self.futures.state.daily_pnl,
            },
            "alpaca_paper": {
                "connected": self.alpaca.connected,
                "error": self.alpaca.init_error,
                "equity": self.alpaca.state.equity,
                "positions": len(self.alpaca.get_positions()),
                "daily_pnl": self.alpaca.state.daily_pnl,
            },
        }
