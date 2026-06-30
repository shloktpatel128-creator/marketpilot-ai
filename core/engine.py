"""TradingEngine — orchestrates the full pipeline."""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from agents import run_all_agents
from brokers.broker_router import BrokerRouter
from config import DEFAULT_FUTURES_SYMBOLS, DEFAULT_STOCK_SYMBOLS, DEFAULT_STRATEGY, MODE
from core.event_log import EVENT_LOG
from core.scheduler import ScanScheduler
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
    """Pipeline: data → features → strategy → confidence → agents → risk → broker → journal."""

    def __init__(self) -> None:
        init_db()
        self.router = BrokerRouter()
        self.risk = RiskEngine()
        self.confidence_model = ConfidenceModel()
        self.registry = ModelRegistry()
        self.journal = TradeJournal()
        self.scheduler = ScanScheduler()
        self.evaluation_id = STATE.evaluation_id
        self._step_callback: Optional[Callable[[str, str], None]] = None

    def set_step_callback(self, fn: Optional[Callable[[str, str], None]]) -> None:
        self._step_callback = fn

    def _emit(self, step: str, detail: str = "", level: str = "info") -> None:
        if level == "error":
            EVENT_LOG.error(step, detail)
        elif level == "warn":
            EVENT_LOG.warn(step, detail)
        elif level == "trade":
            EVENT_LOG.trade(step, detail)
        else:
            EVENT_LOG.info(step, detail)
        logger.info("%s: %s", step, detail)
        if self._step_callback:
            self._step_callback(step, detail)

    def _pick_strategy(self, name: Optional[str] = None):
        chosen = STRATEGIES.get(name or DEFAULT_STRATEGY, STRATEGIES["vwap_momentum"])
        STATE.active_strategy = chosen.name
        return chosen

    def _log_failure(self, symbol: str, broker: str, reason: str) -> None:
        self._emit("Pipeline Error", f"{symbol}/{broker}: {reason}", "error")
        sig = StrategySignal(False, "HOLD", None, None, None, 0, reason, [], "")
        conf = ConfidenceResult(0, self.confidence_model.model_version, reason)
        risk = RiskDecision(False, [reason], None, 0)
        result = ScanResult(self.evaluation_id, symbol, broker, sig, conf, risk, None)
        self.journal.log_scan(result, False, [reason])
        STATE.last_error = reason

    def scan_symbol(
        self,
        symbol: str,
        broker: str = "dry_run",
        strategy_name: Optional[str] = None,
        notional: float = 1000.0,
    ) -> ScanResult:
        evaluation_id = self.evaluation_id
        strategy = self._pick_strategy(strategy_name)

        self._emit("Scan Start", f"{symbol} via {broker}")

        # 1. Market data
        self._emit("Market Data", f"Downloading {symbol}…")
        if broker == "futures_simulator" or symbol in DEFAULT_FUTURES_SYMBOLS:
            df = fetch_futures_bars(symbol)
        else:
            df, warn = fetch_ohlcv(symbol, period="6mo", interval="1d")
            if warn:
                self._emit("Market Data", warn, "warn")

        dq = check_ohlcv(df)
        if df.empty:
            self._emit("Market Data", "No data returned", "error")
            sig = strategy.evaluate(df, symbol)
            conf = self.confidence_model.score(df, sig)
            risk = self.risk.evaluate(
                sig, conf,
                RiskContext(broker=broker, symbol=symbol, broker_connected=False, data_quality_ok=False),
            )
            result = ScanResult(evaluation_id, symbol, broker, sig, conf, risk, None)
            self.journal.log_scan(result, False, risk.rejection_reasons + ["No market data"])
            self._emit("Journal", "Logged rejection — no market data")
            return result
        self._emit("Market Data", f"{len(df)} bars loaded — quality {dq.score:.0f}/100")

        # 2. Features
        self._emit("Features", "Calculating indicators…")
        df = add_features(df)
        current_price = float(df["Close"].iloc[-1])

        # 3. Strategy
        self._emit("Strategy", f"Running {strategy.name}…")
        sig = strategy.evaluate(df, symbol)
        self._emit("Strategy", f"Setup={sig.setup_detected} Direction={sig.direction} — {sig.reason}")

        # 4. Confidence
        self._emit("Confidence Model", "Scoring setup…")
        conf = self.confidence_model.score(df, sig)
        self._emit("Confidence Model", f"{conf.confidence:.0f}/100 ({conf.model_version})")

        # 5. Agents (shadow)
        self._emit("AI Agents", "Running shadow context agents…")
        agent_ctx = {"symbol": symbol, "signal": sig, "df": df, "report": dq, "version": self.registry.get_active()}
        agents_out = run_all_agents(agent_ctx)
        agents_out["data_quality"] = dq.summary()
        from datetime import datetime
        for name, text in agents_out.items():
            STATE.agent_outputs[name] = {"output": text, "last_run": datetime.utcnow().isoformat(), "active": True}

        # 6. Risk context
        if broker == "dry_run":
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=True, data_quality_ok=dq.passed)
        elif broker == "futures_simulator":
            st = self.router.futures.state
            ctx = RiskContext(
                broker=broker, symbol=symbol, broker_connected=True, data_quality_ok=dq.passed,
                daily_pnl=st.daily_pnl, trades_today=st.trade_count_today,
                open_positions=len(st.positions), buying_power=st.equity, market_open=True,
            )
        elif broker == "alpaca_paper":
            alp = self.router.alpaca
            ctx = RiskContext(
                broker=broker, symbol=symbol, broker_connected=alp.connected,
                data_quality_ok=dq.passed, daily_pnl=alp.state.daily_pnl,
                trades_today=alp.state.trade_count_today,
                open_positions=len(alp.get_positions()),
                buying_power=alp.state.buying_power,
                market_open=alp.is_market_open() if alp.connected else False,
            )
        else:
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=False, data_quality_ok=dq.passed)

        # 7. RiskEngine
        self._emit("Risk Engine", "Evaluating trade…")
        risk = self.risk.evaluate(sig, conf, ctx, notional)
        if risk.approved:
            self._emit("Risk Engine", f"APPROVED — risk score {risk.risk_score:.0f}", "trade")
        else:
            self._emit("Risk Engine", f"REJECTED — {'; '.join(risk.rejection_reasons[:3])}", "warn")

        # 8. Broker router
        order: Optional[OrderResult] = None
        route_broker = broker
        if risk.approved and sig.setup_detected and sig.direction != "HOLD":
            if MODE == "DRY_RUN" and broker != "futures_simulator":
                route_broker = "dry_run"
            self._emit("Broker Router", f"Routing {sig.direction} to {route_broker}…")
            raw = self.router.route_order(
                route_broker, sig, symbol,
                notional or risk.adjusted_size or 1000, qty=1, current_price=current_price,
            )
            order = OrderResult(raw.success, route_broker, raw.order_id, raw.message, raw.fill_price, raw.qty)
            if raw.success:
                self._emit("Broker Router", raw.message, "trade")
                discord_notifier.notify("Trade Entry", f"{sig.direction} {symbol} via {route_broker}", "trade")
            else:
                self._emit("Broker Router", raw.message, "error")
            agents_out["risk_explainer"] = f"Approved — order {raw.order_id}" if raw.success else raw.message
        else:
            agents_out["risk_explainer"] = "Rejected: " + "; ".join(risk.rejection_reasons)

        # 9. Journal
        result = ScanResult(evaluation_id, symbol, route_broker, sig, conf, risk, order, agents_out)
        self.journal.log_scan(result, risk.approved, risk.rejection_reasons)
        self._emit("Journal", f"Decision logged (eval={evaluation_id})")
        STATE.sync_from_brokers(self.router)
        self._emit("Scan Complete", f"{symbol} approved={risk.approved}")
        return result

    def run_one_scan(self) -> List[ScanResult]:
        """Execute exactly one evaluation cycle — does not start scheduler."""
        EVENT_LOG.info("Engine", "Run One Scan initiated")
        results = self.run_full_scan()
        self.scheduler.schedule_next()
        STATE.last_scan_results = results
        return results

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
        STATE.last_scan_results = results
        return results
