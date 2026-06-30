"""Simulated micro futures broker."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set

from config import FUTURES_COMMISSION, FUTURES_MAX_DAILY_LOSS, FUTURES_MAX_TRADES_DAY, FUTURES_SLIPPAGE_TICKS
from data.futures_data import FUTURES_SPECS, get_spec

logger = logging.getLogger(__name__)


@dataclass
class SimPosition:
    symbol: str
    side: str
    qty: int
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_id: str = ""


@dataclass
class FuturesSimState:
    balance: float = 50_000.0
    equity: float = 50_000.0
    daily_pnl: float = 0.0
    positions: List[SimPosition] = field(default_factory=list)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    trade_count_today: int = 0
    pending_symbols: Set[str] = field(default_factory=set)
    _day: Optional[date] = None
    _day_start_equity: float = 50_000.0


@dataclass
class BrokerOrderResult:
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    fill_price: Optional[float] = None
    qty: Optional[float] = None


class FuturesSimulator:
    name = "futures_simulator"
    asset_class = "futures"

    def __init__(self, starting_balance: float = 50_000.0) -> None:
        self.state = FuturesSimState(balance=starting_balance, equity=starting_balance)
        self.state._day_start_equity = starting_balance

    @property
    def connected(self) -> bool:
        return True

    def _reset_day(self) -> None:
        today = date.today()
        if self.state._day != today:
            self.state._day = today
            self.state._day_start_equity = self.state.equity
            self.state.trade_count_today = 0
            self.state.daily_pnl = 0.0

    def _apply_slippage(self, price: float, side: str, tick_size: float) -> float:
        slip = FUTURES_SLIPPAGE_TICKS * tick_size
        return price + slip if side.upper() == "BUY" else price - slip

    def _pnl_ticks(self, pos: SimPosition, exit_price: float) -> float:
        spec = get_spec(pos.symbol)
        if not spec:
            return 0.0
        ticks = (exit_price - pos.entry_price) / spec.tick_size
        if pos.side.upper() == "SELL":
            ticks = -ticks
        return ticks * spec.tick_value * pos.qty

    def mark_to_market(self, symbol: str, current_price: float) -> None:
        unrealized = 0.0
        for p in self.state.positions:
            if p.symbol == symbol:
                unrealized += self._pnl_ticks(p, current_price)
        self.state.equity = self.state.balance + unrealized
        self._reset_day()
        self.state.daily_pnl = self.state.equity - self.state._day_start_equity

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int = 1,
        price: Optional[float] = None,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> BrokerOrderResult:
        self._reset_day()
        sym = symbol.upper()
        spec = get_spec(sym)
        if not spec:
            return BrokerOrderResult(False, message=f"Unsupported futures symbol: {sym}")
        if sym in self.state.pending_symbols:
            return BrokerOrderResult(False, message=f"Duplicate order blocked for {sym}.")
        if self.state.trade_count_today >= FUTURES_MAX_TRADES_DAY:
            return BrokerOrderResult(False, message="Max futures trades per day reached.")
        if self.state.daily_pnl <= -FUTURES_MAX_DAILY_LOSS:
            return BrokerOrderResult(False, message="Futures daily loss limit reached.")
        if price is None:
            return BrokerOrderResult(False, message="Price required for simulation fill.")

        fill = self._apply_slippage(price, side, spec.tick_size)
        if order_type == "limit" and limit_price:
            if side.upper() == "BUY" and fill > limit_price:
                return BrokerOrderResult(False, message="Limit not met — no fill.")
            if side.upper() == "SELL" and fill < limit_price:
                return BrokerOrderResult(False, message="Limit not met — no fill.")

        self.state.pending_symbols.add(sym)
        oid = str(uuid.uuid4())[:12]

        # Close opposite if exists
        existing = [p for p in self.state.positions if p.symbol == sym]
        if side.upper() == "SELL" and existing:
            for p in existing:
                pnl = self._pnl_ticks(p, fill) - FUTURES_COMMISSION
                self.state.balance += pnl
                self.state.positions.remove(p)
        elif side.upper() == "BUY" and existing and existing[0].side.upper() == "SELL":
            p = existing[0]
            pnl = self._pnl_ticks(p, fill) - FUTURES_COMMISSION
            self.state.balance += pnl
            self.state.positions.remove(p)
        else:
            self.state.positions.append(
                SimPosition(sym, side.upper(), qty, fill, stop_loss, take_profit, oid)
            )

        self.state.trade_count_today += 1
        self.state.orders.append({
            "id": oid, "symbol": sym, "side": side, "qty": qty,
            "fill_price": fill, "commission": FUTURES_COMMISSION,
        })
        self.state.pending_symbols.discard(sym)
        self.mark_to_market(sym, fill)
        return BrokerOrderResult(True, oid, f"Simulated {side} {qty} {sym} @ {fill:.4f}", fill, qty)

    def check_stops(self, symbol: str, high: float, low: float, close: float) -> List[BrokerOrderResult]:
        """Check stop-loss / take-profit on open positions."""
        results = []
        for p in list(self.state.positions):
            if p.symbol != symbol.upper():
                continue
            if p.stop_loss and ((p.side == "BUY" and low <= p.stop_loss) or (p.side == "SELL" and high >= p.stop_loss)):
                results.append(self.place_order(symbol, "SELL" if p.side == "BUY" else "BUY", p.qty, p.stop_loss))
            elif p.take_profit and ((p.side == "BUY" and high >= p.take_profit) or (p.side == "SELL" and low <= p.take_profit)):
                results.append(self.place_order(symbol, "SELL" if p.side == "BUY" else "BUY", p.qty, p.take_profit))
        return results

    def end_of_day_close_all(self) -> List[BrokerOrderResult]:
        results = []
        for p in list(self.state.positions):
            results.append(self.place_order(p.symbol, "SELL" if p.side == "BUY" else "BUY", p.qty, p.entry_price))
        return results

    def get_positions(self) -> List[Dict[str, Any]]:
        return [
            {"symbol": p.symbol, "side": p.side, "qty": p.qty, "entry_price": p.entry_price,
             "stop_loss": p.stop_loss, "take_profit": p.take_profit}
            for p in self.state.positions
        ]
