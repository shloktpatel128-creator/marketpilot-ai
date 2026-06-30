"""TradingEngine — one full scan cycle."""

from __future__ import annotations

import logging
from typing import List, Optional

from agents import run_all_agents
from brokers.broker_router import BrokerRouter
from config import DEFAULT_FUTURES_SYMBOLS, DEFAULT_STOCK_SYMBOLS, DEFAULT_STRATEGY, MODE
from core.state import STATE
from data.data_quality import check_ohlcv
from data.futures_data import fetch_futures_bars
from data.market_data import fetch_ohlcv
from features.feature_engineering import add_features
from journal.trade_journal import TradeJournal
from models.confidence_model import ConfidenceModel
from models.model_registry import ModelRegistry
from notifications import discord_notifier
from risk.risk_engine import RiskContext, RiskEngine
from storage.database import init_db
from storage.schemas import ConfidenceResult, OrderResult, RiskDecision, ScanResult, StrategySignal
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.vwap_momentum import VWAPMomentumStrategy

logger = logging.getLogger(__name__)

STRATEGIES = {
    "vwap_momentum": VWAPMomentumStrategy(),
    "breakout": BreakoutStrategy(),
    "pullback": PullbackStrategy(),
}


class TradingEngine:
    """
    Pipeline: data → features → strategy → confidence → agents (shadow) →
    risk → broker → journal.
    """

    def __init__(self) -> None:
        init_db()
        self.router = BrokerRouter()
        self.risk = RiskEngine()
        self.confidence_model = ConfidenceModel()
        self.registry = ModelRegistry()
        self.journal = TradeJournal()
        self.evaluation_id = STATE.evaluation_id

    def _pick_strategy(self, name: Optional[str] = None):
        return STRATEGIES.get(name or DEFAULT_STRATEGY, STRATEGIES["vwap_momentum"])

    def _log_failure(self, symbol: str, broker: str, reason: str) -> None:
        sig = StrategySignal(False, "HOLD", None, None, None, 0, reason, [], "")
        conf = ConfidenceResult(0, self.confidence_model.model_version, reason)
        risk = RiskDecision(False, [reason], None, 0)
        result = ScanResult(self.evaluation_id, symbol, broker, sig, conf, risk, None)
        self.journal.log_scan(result, False, [reason])

    def scan_symbol(
        self,
        symbol: str,
        broker: str = "dry_run",
        strategy_name: Optional[str] = None,
        notional: float = 1000.0,
    ) -> ScanResult:
        evaluation_id = self.evaluation_id
        strategy = self._pick_strategy(strategy_name)

        # 1. Load data
        if broker == "futures_simulator" or symbol in DEFAULT_FUTURES_SYMBOLS:
            df = fetch_futures_bars(symbol)
        else:
            df, _ = fetch_ohlcv(symbol, period="6mo", interval="1d")

        dq = check_ohlcv(df)
        if df.empty:
            sig = strategy.evaluate(df, symbol)
            conf = self.confidence_model.score(df, sig)
            risk = self.risk.evaluate(sig, conf, RiskContext(broker=broker, symbol=symbol, broker_connected=False, data_quality_ok=False))
            result = ScanResult(evaluation_id, symbol, broker, sig, conf, risk, None)
            self.journal.log_scan(result, False, risk.rejection_reasons + ["No market data"])
            return result

        # 2. Features
        df = add_features(df)
        current_price = float(df["Close"].iloc[-1])

        # 3. Strategy
        sig = strategy.evaluate(df, symbol)

        # 4. Confidence
        conf = self.confidence_model.score(df, sig)

        # 5. Agents (shadow — never trade)
        agent_ctx = {
            "symbol": symbol, "signal": sig, "df": df,
            "report": dq, "version": self.registry.get_active(),
        }
        agents_out = run_all_agents(agent_ctx)
        agents_out["data_quality"] = dq.summary()

        # 6. Risk context
        brk = self.router.get(broker)
        connected = getattr(brk, "connected", False) if brk else False
        if broker == "dry_run":
            connected = True
        if broker == "futures_simulator":
            connected = True
            st = self.router.futures.state
            ctx = RiskContext(
                broker=broker, symbol=symbol, broker_connected=True,
                data_quality_ok=dq.passed, daily_pnl=st.daily_pnl,
                trades_today=st.trade_count_today, open_positions=len(st.positions),
                buying_power=st.equity, market_open=True,
            )
        elif broker == "alpaca_paper":
            alp = self.router.alpaca
            ctx = RiskContext(
                broker=broker, symbol=symbol, broker_connected=alp.connected,
                data_quality_ok=dq.passed, daily_pnl=alp.state.daily_pnl,
                trades_today=alp.state.trade_count_today,
                open_positions=len(alp.get_positions()),
                buying_power=alp.state.buying_power,
                market_open=alp.is_market_open(),
            )
        else:
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=connected, data_quality_ok=dq.passed)

        # 7. RiskEngine
        risk = self.risk.evaluate(sig, conf, ctx, notional)

        # 8. Route order if approved
        order: Optional[OrderResult] = None
        if risk.approved and sig.setup_detected and sig.direction != "HOLD":
            if MODE == "DRY_RUN" and broker != "futures_simulator":
                broker = "dry_run"
            raw = self.router.route_order(broker, sig, symbol, notional or risk.adjusted_size or 1000, qty=1, current_price=current_price)
            order = OrderResult(raw.success, broker, raw.order_id, raw.message, raw.fill_price, raw.qty)
            if raw.success:
                discord_notifier.notify("Trade Entry", f"{sig.direction} {symbol} via {broker}", "trade")
            agents_out["risk_explainer"] = f"Approved — order {raw.order_id}"
        else:
            agents_out["risk_explainer"] = "Rejected: " + "; ".join(risk.rejection_reasons)
            discord_notifier.notify("Risk Rejection", f"{symbol}: {'; '.join(risk.rejection_reasons[:2])}", "risk")

        result = ScanResult(evaluation_id, symbol, broker, sig, conf, risk, order, agents_out)
        self.journal.log_scan(result, risk.approved, risk.rejection_reasons)
        STATE.sync_from_brokers(self.router)
        logger.info("Scan %s %s %s — approved=%s", symbol, broker, sig.direction, risk.approved)
        return result

    def run_full_scan(
        self,
        stock_symbols: Optional[List[str]] = None,
        futures_symbols: Optional[List[str]] = None,
    ) -> List[ScanResult]:
        results = []
        stocks = stock_symbols or DEFAULT_STOCK_SYMBOLS[:3]
        futures = futures_symbols or DEFAULT_FUTURES_SYMBOLS[:2]

        for sym in stocks:
            try:
                results.append(self.scan_symbol(sym, "dry_run"))
            except Exception as exc:
                logger.exception("Stock scan failed %s: %s", sym, exc)
                self._log_failure(sym, "dry_run", str(exc))
            if MODE == "PAPER":
                try:
                    results.append(self.scan_symbol(sym, "alpaca_paper"))
                except Exception as exc:
                    logger.exception("Alpaca scan failed %s: %s", sym, exc)
                    self._log_failure(sym, "alpaca_paper", str(exc))

        for sym in futures:
            try:
                results.append(self.scan_symbol(sym, "futures_simulator"))
            except Exception as exc:
                logger.exception("Futures scan failed %s: %s", sym, exc)
                self._log_failure(sym, "futures_simulator", str(exc))

        STATE.touch_scan()
        STATE.sync_from_brokers(self.router)
        return results
