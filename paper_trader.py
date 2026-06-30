"""
Alpaca paper trading integration.

SAFETY: This module only connects to Alpaca's paper trading API by default.
Real trading requires REAL_TRADING_ENABLED=true in config — do not enable
unless you fully understand the risks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from config import (
    ALPACA_API_KEY,
    ALPACA_LIVE_BASE_URL,
    ALPACA_PAPER_BASE_URL,
    ALPACA_SECRET_KEY,
    MAX_DAILY_LOSS_USD,
    MAX_POSITION_SIZE_USD,
    MIN_CONFIDENCE_TO_TRADE,
    REAL_TRADING_ENABLED,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
)
from strategy import TradingSignal

logger = logging.getLogger(__name__)

# Lazy import so the app runs without Alpaca credentials
_alpaca_available: Optional[bool] = None


def _check_alpaca() -> bool:
    global _alpaca_available
    if _alpaca_available is not None:
        return _alpaca_available
    try:
        from alpaca.trading.client import TradingClient  # noqa: F401
        _alpaca_available = True
    except ImportError:
        _alpaca_available = False
    return _alpaca_available


@dataclass
class TradeResult:
    """Outcome of attempting to place a paper trade."""

    success: bool
    message: str
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    qty: Optional[float] = None


@dataclass
class AccountStatus:
    """Snapshot of the paper trading account."""

    connected: bool
    mode: str  # "paper" or "live"
    equity: float
    cash: float
    buying_power: float
    daily_pnl: float
    message: str


class PaperTrader:
    """
    Wrapper around Alpaca's trading API with safety guardrails.

    All orders go to the paper endpoint unless REAL_TRADING_ENABLED is True.
    """

    def __init__(self) -> None:
        self._client = None
        self._daily_start_equity: Optional[float] = None
        self._daily_start_date: Optional[date] = None
        self._init_error: Optional[str] = None

        if not _check_alpaca():
            self._init_error = "alpaca-py is not installed. Run: pip install alpaca-py"
            return

        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            self._init_error = (
                "Alpaca API keys not configured. "
                "Copy .env.example to .env and add your paper trading keys."
            )
            return

        if REAL_TRADING_ENABLED:
            logger.warning(
                "REAL TRADING IS ENABLED. Orders will use the LIVE Alpaca endpoint!"
            )

        try:
            from alpaca.trading.client import TradingClient

            paper = not REAL_TRADING_ENABLED
            self._client = TradingClient(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY,
                paper=paper,
            )
        except Exception as exc:
            self._init_error = f"Failed to connect to Alpaca: {exc}"

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def trading_mode(self) -> str:
        return "live" if REAL_TRADING_ENABLED else "paper"

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def _reset_daily_tracker(self, equity: float) -> None:
        today = date.today()
        if self._daily_start_date != today:
            self._daily_start_date = today
            self._daily_start_equity = equity

    def is_market_open(self) -> bool:
        """Return True if the US stock market is currently open."""
        if not self.is_connected:
            return False
        try:
            clock = self._client.get_clock()
            return bool(clock.is_open)
        except Exception as exc:
            logger.error("Could not check market clock: %s", exc)
            return False

    def get_account_status(self) -> AccountStatus:
        """Fetch current account balances and daily P&L."""
        if not self.is_connected:
            return AccountStatus(
                connected=False,
                mode=self.trading_mode,
                equity=0.0,
                cash=0.0,
                buying_power=0.0,
                daily_pnl=0.0,
                message=self._init_error or "Not connected.",
            )

        try:
            acct = self._client.get_account()
            equity = float(acct.equity)
            cash = float(acct.cash)
            buying_power = float(acct.buying_power)

            self._reset_daily_tracker(equity)
            daily_pnl = equity - (self._daily_start_equity or equity)

            mode_label = "LIVE ⚠️" if REAL_TRADING_ENABLED else "Paper (simulated)"
            return AccountStatus(
                connected=True,
                mode=mode_label,
                equity=equity,
                cash=cash,
                buying_power=buying_power,
                daily_pnl=daily_pnl,
                message=f"Connected to Alpaca {mode_label} trading.",
            )
        except Exception as exc:
            return AccountStatus(
                connected=False,
                mode=self.trading_mode,
                equity=0.0,
                cash=0.0,
                buying_power=0.0,
                daily_pnl=0.0,
                message=f"Account error: {exc}",
            )

    def get_positions(self) -> List[Dict[str, Any]]:
        """Return list of open positions."""
        if not self.is_connected:
            return []
        try:
            positions = self._client.get_all_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc) * 100,
                }
                for p in positions
            ]
        except Exception as exc:
            logger.error("Failed to fetch positions: %s", exc)
            return []

    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent filled orders."""
        if not self.is_connected:
            return []
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            request = GetOrdersRequest(
                status=QueryOrderStatus.CLOSED,
                limit=limit,
            )
            orders = self._client.get_orders(filter=request)
            return [
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": str(o.side),
                    "qty": float(o.filled_qty or 0),
                    "filled_price": float(o.filled_avg_price or 0),
                    "status": str(o.status),
                    "submitted_at": str(o.submitted_at),
                    "filled_at": str(o.filled_at),
                }
                for o in orders
            ]
        except Exception as exc:
            logger.error("Failed to fetch order history: %s", exc)
            return []

    def _check_safety(
        self,
        signal: TradingSignal,
        symbol: str,
        side: str,
        notional: float,
    ) -> Optional[str]:
        """Run all safety checks. Returns error message or None if OK."""
        if REAL_TRADING_ENABLED:
            return (
                "REAL_TRADING_ENABLED is True. "
                "This app blocks automated live orders for safety. "
                "Disable REAL_TRADING_ENABLED or use Alpaca's dashboard manually."
            )

        if signal.confidence < MIN_CONFIDENCE_TO_TRADE:
            return (
                f"Confidence {signal.confidence}% is below minimum "
                f"threshold ({MIN_CONFIDENCE_TO_TRADE}%). Trade blocked."
            )

        if signal.action == "HOLD":
            return "Signal is HOLD — no trade placed."

        if not self.is_market_open():
            return "Market is closed. Trade blocked."

        if notional > MAX_POSITION_SIZE_USD:
            return (
                f"Position size ${notional:.2f} exceeds max "
                f"${MAX_POSITION_SIZE_USD:.2f}. Trade blocked."
            )

        status = self.get_account_status()
        if status.daily_pnl < -MAX_DAILY_LOSS_USD:
            return (
                f"Daily loss ${abs(status.daily_pnl):.2f} exceeds max "
                f"${MAX_DAILY_LOSS_USD:.2f}. Trading halted for today."
            )

        # Stop-loss / take-profit checks on existing positions
        if side == "sell":
            positions = self.get_positions()
            pos = next((p for p in positions if p["symbol"] == symbol), None)
            if pos:
                plpc = pos["unrealized_plpc"] / 100
                if plpc <= -STOP_LOSS_PCT:
                    return None  # Allow sell — stop loss triggered
                if plpc >= TAKE_PROFIT_PCT:
                    return None  # Allow sell — take profit triggered

        return None

    def execute_signal(
        self,
        symbol: str,
        signal: TradingSignal,
        notional: float = 1000.0,
    ) -> TradeResult:
        """
        Place a paper trade based on a TradingSignal.

        Args:
            symbol: Ticker symbol.
            signal: Generated trading signal.
            notional: Dollar amount for the order (capped by MAX_POSITION_SIZE_USD).

        Returns:
            TradeResult with success status and message.
        """
        if not self.is_connected:
            return TradeResult(
                success=False,
                message=self._init_error or "Not connected to Alpaca.",
            )

        if signal.action not in ("BUY", "SELL"):
            return TradeResult(
                success=False,
                message="Signal is HOLD — no order submitted.",
            )

        side = "buy" if signal.action == "BUY" else "sell"
        notional = min(notional, MAX_POSITION_SIZE_USD)

        safety_error = self._check_safety(signal, symbol, side, notional)
        if safety_error:
            return TradeResult(success=False, message=safety_error)

        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

            order_data = MarketOrderRequest(
                symbol=symbol.upper(),
                notional=notional if side == "buy" else None,
                qty=None if side == "buy" else self._get_position_qty(symbol),
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )

            # For sells, use qty from position
            if side == "sell":
                qty = self._get_position_qty(symbol)
                if qty <= 0:
                    return TradeResult(
                        success=False,
                        message=f"No open position in {symbol} to sell.",
                    )
                order_data = MarketOrderRequest(
                    symbol=symbol.upper(),
                    qty=qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                )

            order = self._client.submit_order(order_data)

            return TradeResult(
                success=True,
                message=(
                    f"Paper {side.upper()} order submitted for {symbol} "
                    f"(confidence: {signal.confidence}%)."
                ),
                order_id=str(order.id),
                symbol=symbol.upper(),
                side=side,
                qty=float(order.qty) if order.qty else None,
            )

        except Exception as exc:
            return TradeResult(success=False, message=f"Order failed: {exc}")

    def _get_position_qty(self, symbol: str) -> float:
        positions = self.get_positions()
        pos = next((p for p in positions if p["symbol"] == symbol.upper()), None)
        return float(pos["qty"]) if pos else 0.0

    def check_stop_loss_take_profit(self) -> List[TradeResult]:
        """
        Scan open positions and auto-sell if stop-loss or take-profit hit.

        Returns list of TradeResults for any exit orders placed.
        """
        results = []
        if not self.is_connected or not self.is_market_open():
            return results

        for pos in self.get_positions():
            plpc = pos["unrealized_plpc"] / 100
            symbol = pos["symbol"]

            if plpc <= -STOP_LOSS_PCT:
                fake_signal = TradingSignal(
                    action="SELL",
                    confidence=100,
                    explanation="Stop-loss triggered.",
                    risk_level="High",
                )
                # Bypass confidence check for risk exits
                result = self._force_sell(symbol, f"Stop-loss hit ({plpc*100:.1f}%)")
                results.append(result)

            elif plpc >= TAKE_PROFIT_PCT:
                result = self._force_sell(symbol, f"Take-profit hit ({plpc*100:.1f}%)")
                results.append(result)

        return results

    def _force_sell(self, symbol: str, reason: str) -> TradeResult:
        """Sell entire position, bypassing signal confidence checks."""
        if not self.is_connected:
            return TradeResult(success=False, message="Not connected.")

        qty = self._get_position_qty(symbol)
        if qty <= 0:
            return TradeResult(success=False, message=f"No position in {symbol}.")

        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            order = self._client.submit_order(order_data)
            return TradeResult(
                success=True,
                message=f"Auto-sell {symbol}: {reason}",
                order_id=str(order.id),
                symbol=symbol,
                side="sell",
                qty=qty,
            )
        except Exception as exc:
            return TradeResult(success=False, message=f"Force sell failed: {exc}")
