"""Alpaca paper broker — stocks/ETFs only. Live trading blocked."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set

from config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    MAX_POSITION_SIZE_USD,
    REAL_TRADING_ENABLED,
)

logger = logging.getLogger(__name__)


@dataclass
class AlpacaState:
    equity: float = 100_000.0
    cash: float = 100_000.0
    buying_power: float = 100_000.0
    daily_pnl: float = 0.0
    positions: List[Dict[str, Any]] = field(default_factory=list)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    pending_symbols: Set[str] = field(default_factory=set)
    trade_count_today: int = 0
    _daily_start: Optional[date] = None
    _daily_start_equity: float = 100_000.0


@dataclass
class BrokerOrderResult:
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    fill_price: Optional[float] = None
    qty: Optional[float] = None


class AlpacaPaperBroker:
    name = "alpaca_paper"
    asset_class = "stock"

    def __init__(self) -> None:
        self.state = AlpacaState()
        self._client = None
        self._error: Optional[str] = None
        if REAL_TRADING_ENABLED:
            self._error = "Live trading blocked by config."
            return
        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            self._error = "Alpaca API keys not configured."
            return
        try:
            from alpaca.trading.client import TradingClient
            self._client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
            self._sync_account()
        except Exception as exc:
            self._error = str(exc)
            logger.error("Alpaca init failed: %s", exc)

    @property
    def connected(self) -> bool:
        return self._client is not None and not REAL_TRADING_ENABLED

    @property
    def init_error(self) -> Optional[str]:
        return self._error

    def _sync_account(self) -> None:
        if not self._client:
            return
        try:
            acct = self._client.get_account()
            self.state.equity = float(acct.equity)
            self.state.cash = float(acct.cash)
            self.state.buying_power = float(acct.buying_power)
            today = date.today()
            if self.state._daily_start != today:
                self.state._daily_start = today
                self.state._daily_start_equity = self.state.equity
                self.state.trade_count_today = 0
            self.state.daily_pnl = self.state.equity - self.state._daily_start_equity
        except Exception as exc:
            logger.error("Account sync failed: %s", exc)

    def is_market_open(self) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.get_clock().is_open)
        except Exception:
            return False

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            positions = self._client.get_all_positions()
            self.state.positions = [
                {"symbol": p.symbol, "qty": float(p.qty), "avg_entry_price": float(p.avg_entry_price),
                 "current_price": float(p.current_price), "unrealized_pl": float(p.unrealized_pl)}
                for p in positions
            ]
            return self.state.positions
        except Exception as exc:
            logger.error("Positions fetch failed: %s", exc)
            return []

    def get_recent_orders(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self._client:
            return list(self.state.orders[-limit:])
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
            orders = self._client.get_orders(req)
            return [
                {
                    "id": str(o.id), "symbol": o.symbol, "side": str(o.side),
                    "qty": float(o.qty or 0), "status": str(o.status),
                    "filled_avg_price": float(o.filled_avg_price or 0),
                }
                for o in orders
            ]
        except Exception as exc:
            logger.error("Orders fetch failed: %s", exc)
            return list(self.state.orders[-limit:])

    def get_open_orders(self) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            orders = self._client.get_orders(req)
            return [
                {"id": str(o.id), "symbol": o.symbol, "side": str(o.side), "qty": float(o.qty or 0)}
                for o in orders
            ]
        except Exception as exc:
            logger.error("Open orders fetch failed: %s", exc)
            return []

    def health(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "error": self.init_error,
            "market_open": self.is_market_open() if self.connected else False,
        }

    def place_order(
        self,
        symbol: str,
        side: str,
        notional: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> BrokerOrderResult:
        if REAL_TRADING_ENABLED:
            return BrokerOrderResult(False, message="Live trading blocked.")
        if not self.connected:
            return BrokerOrderResult(False, message=self._error or "Not connected.")
        sym = symbol.upper()
        if sym in self.state.pending_symbols:
            return BrokerOrderResult(False, message=f"Duplicate order blocked for {sym}.")
        notional = min(notional, MAX_POSITION_SIZE_USD)
        if not self.is_market_open():
            return BrokerOrderResult(False, message="Market closed.")
        try:
            from alpaca.trading.enums import OrderSide, TimeInForce
            from alpaca.trading.requests import MarketOrderRequest

            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
            if side.upper() == "SELL":
                pos = next((p for p in self.get_positions() if p["symbol"] == sym), None)
                if not pos:
                    return BrokerOrderResult(False, message=f"No position in {sym}.")
                req = MarketOrderRequest(symbol=sym, qty=pos["qty"], side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
            else:
                req = MarketOrderRequest(symbol=sym, notional=notional, side=order_side, time_in_force=TimeInForce.DAY)

            self.state.pending_symbols.add(sym)
            order = self._client.submit_order(req)
            self.state.trade_count_today += 1
            self.state.orders.append({"id": str(order.id), "symbol": sym, "side": side, "notional": notional})
            self.state.pending_symbols.discard(sym)
            self._sync_account()
            return BrokerOrderResult(True, str(order.id), f"Paper {side} {sym} submitted.", qty=float(order.qty or 0))
        except Exception as exc:
            self.state.pending_symbols.discard(sym)
            logger.error("Order failed: %s", exc)
            return BrokerOrderResult(False, message=str(exc))
