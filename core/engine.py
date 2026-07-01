"""TradingEngine — institutional AI pipeline."""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from agents.pipeline import AgentPipeline
from analytics.performance import strategy_win_rates
from brokers.broker_router import BrokerRouter
from config import DEFAULT_FUTURES_SYMBOLS, DEFAULT_STOCK_SYMBOLS, MAX_OPEN_POSITIONS, MODE
from core.event_log import EVENT_LOG
from core.scheduler import ScanScheduler
from core.state import STATE
from data.data_quality import check_ohlcv
from data.futures_data import fetch_futures_bars
from data.market_data import fetch_ohlcv
from features.feature_engineering import add_features, get_indicator_snapshot
from journal.trade_journal import TradeJournal
from models.confidence_engine import ConfidenceEngine, ConfidenceInputs
from models.model_registry import ModelRegistry
from notifications import discord_notifier
from risk.risk_engine import RiskContext, RiskEngine
from services.macro import analyze_macro
from services.multitimeframe import analyze_multitimeframe
from services.news import fetch_and_analyze_news
from services.portfolio_risk import assess_portfolio, compute_portfolio_heat
from services.regime import detect_regime
from services.trade_plan import generate_trade_plan
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
    """Full pipeline: data → indicators → MTF → news → macro → regime → agents → CIO → confidence → risk → broker → journal."""

    def __init__(self) -> None:
        init_db()
        self.router = BrokerRouter()
        self.risk = RiskEngine()
        self.confidence_engine = ConfidenceEngine()
        self.agent_pipeline = AgentPipeline()
        self.registry = ModelRegistry()
        self.journal = TradeJournal()
        self.scheduler = ScanScheduler()
        self.evaluation_id = STATE.evaluation_id
        self._step_callback: Optional[Callable[[str, str], None]] = None

    def set_step_callback(self, fn: Optional[Callable[[str, str], None]]) -> None:
        self._step_callback = fn

    def _emit(self, step: str, detail: str = "", level: str = "info") -> None:
        getattr(EVENT_LOG, level if level in ("error", "warn", "trade") else "info")(step, detail)
        logger.info("%s: %s", step, detail)
        if self._step_callback:
            self._step_callback(step, detail)

    def _pick_strategy(self, name: Optional[str] = None, regime=None):
        if regime and regime.recommended_strategies:
            chosen_name = name or regime.recommended_strategies[0]
        else:
            chosen_name = name
        from config import DEFAULT_STRATEGY
        chosen = STRATEGIES.get(chosen_name or DEFAULT_STRATEGY, STRATEGIES["vwap_momentum"])
        STATE.active_strategy = chosen.name
        return chosen

    def _log_failure(self, symbol: str, broker: str, reason: str) -> None:
        self._emit("Pipeline Error", f"{symbol}/{broker}: {reason}", "error")
        sig = StrategySignal(False, "HOLD", None, None, None, 0, reason, [], "")
        conf = ConfidenceResult(0, "error", reason)
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
        t0 = time.time()
        evaluation_id = self.evaluation_id
        self._emit("Scan Start", f"{symbol} via {broker}")

        # 1. Market data
        self._emit("Market Data", f"Downloading live data for {symbol}")
        if broker == "futures_simulator" or symbol in DEFAULT_FUTURES_SYMBOLS:
            df = fetch_futures_bars(symbol)
        else:
            df, warn = fetch_ohlcv(symbol, period="1y", interval="1d")
            if warn:
                self._emit("Market Data", warn, "warn")

        dq = check_ohlcv(df)
        if df.empty:
            self._log_failure(symbol, broker, "No market data")
            return ScanResult(evaluation_id, symbol, broker,
                StrategySignal(False, "HOLD", None, None, None, 0, "No data", [], ""),
                ConfidenceResult(0, "error", ""), RiskDecision(False, ["No data"], None, 0), None)

        # 2. Institutional indicators
        self._emit("Indicators", "Computing institutional indicator suite")
        df = add_features(df)
        indicator_snap = get_indicator_snapshot(df)
        current_price = float(df["Close"].iloc[-1])

        # 3. Multi-timeframe
        self._emit("Multi-Timeframe", "Analyzing 15m, 1h, daily, weekly")
        mtf = analyze_multitimeframe(symbol, ["15m", "1h", "1d", "1wk"])

        # 4. News sentiment
        self._emit("News", "Fetching and analyzing headlines")
        news = fetch_and_analyze_news(symbol)

        # 5. Macro events
        self._emit("Macro", "Checking earnings and macro calendar")
        macro = analyze_macro(symbol)

        # 6. Regime detection
        self._emit("Regime", "Detecting market regime")
        regime = detect_regime(df)
        strategy = self._pick_strategy(strategy_name, regime)

        # 7. Strategy signal
        self._emit("Strategy", f"Running {strategy.name} in {regime.regime} regime")
        sig = strategy.evaluate(df, symbol)

        # 8. Trade plan
        buying_power = 100_000.0
        if broker == "futures_simulator":
            buying_power = self.router.futures.state.equity
        elif broker == "alpaca_paper" and self.router.alpaca.connected:
            buying_power = self.router.alpaca.state.buying_power

        direction = sig.direction if sig.setup_detected else "NO_TRADE"
        plan = generate_trade_plan(df, direction, 50, buying_power)
        if sig.setup_detected and plan.entry:
            sig.entry = plan.entry
            sig.stop_loss = plan.stop_loss
            sig.take_profit = plan.take_profit
            sig.reward_risk = plan.reward_risk

        # 9. AI agent pipeline + CIO
        self._emit("AI Agents", "Running 10-agent analysis pipeline")
        open_pos = len(self.router.futures.state.positions)
        if broker == "alpaca_paper":
            open_pos = len(self.router.alpaca.get_positions())
        heat = compute_portfolio_heat(
            self.router.futures.state.daily_pnl + self.router.alpaca.state.daily_pnl,
            buying_power,
        )
        cio = self.agent_pipeline.run(
            df, sig, mtf, news, macro, regime, plan,
            open_positions=open_pos, max_positions=MAX_OPEN_POSITIONS,
            portfolio_heat=heat,
            broker_connected=broker in ("dry_run", "futures_simulator") or self.router.alpaca.connected,
            market_open=self.router.alpaca.is_market_open() if broker == "alpaca_paper" else True,
        )
        agents_out = self.agent_pipeline.votes_to_context(cio)
        agents_out["data_quality"] = dq.summary()
        agents_out["regime"] = regime.summary
        agents_out["mtf"] = mtf.summary
        agents_out["news"] = news.summary

        # Override direction from CIO if stronger signal
        if cio.final_action in ("BUY", "SELL") and cio.confidence >= 60:
            if not sig.setup_detected:
                sig = StrategySignal(True, cio.final_action, plan.entry, plan.stop_loss, plan.take_profit,
                                     plan.reward_risk, cio.consensus_summary, ["CIO"], strategy.name)
            elif cio.final_action == "NO_TRADE":
                sig = StrategySignal(False, "HOLD", sig.entry, sig.stop_loss, sig.take_profit, 0,
                                     "CIO veto: " + cio.consensus_summary, [], strategy.name)

        from datetime import datetime
        for v in cio.votes:
            STATE.agent_outputs[v.agent] = {"output": v.reasoning, "last_run": datetime.utcnow().isoformat(),
                                            "active": True, "recommendation": v.recommendation}

        # 10. Weighted confidence engine
        self._emit("Confidence Engine", "Computing weighted AI confidence")
        win_rates = strategy_win_rates()
        conf = self.confidence_engine.score(ConfidenceInputs(
            df=df, mtf=mtf, news=news, macro=macro, regime=regime,
            agent_scores={v.agent: v.confidence - 50 for v in cio.votes},
            strategy_win_rate=win_rates.get(strategy.name, 50),
            direction=sig.direction if sig.setup_detected else cio.final_action,
        ))
        self._emit("Confidence Engine", f"{conf.confidence:.0f}/100 — {conf.explanation[:100]}")

        # 11. Risk context
        if broker == "dry_run":
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=True, data_quality_ok=dq.passed,
                              news_restricted=macro.high_impact_soon or macro.earnings_soon)
        elif broker == "futures_simulator":
            st = self.router.futures.state
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=True, data_quality_ok=dq.passed,
                              daily_pnl=st.daily_pnl, trades_today=st.trade_count_today,
                              open_positions=len(st.positions), buying_power=st.equity, market_open=True,
                              news_restricted=macro.earnings_soon)
        elif broker == "alpaca_paper":
            alp = self.router.alpaca
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=alp.connected,
                              data_quality_ok=dq.passed, daily_pnl=alp.state.daily_pnl,
                              trades_today=alp.state.trade_count_today,
                              open_positions=len(alp.get_positions()),
                              buying_power=alp.state.buying_power,
                              market_open=alp.is_market_open() if alp.connected else False,
                              news_restricted=macro.earnings_soon)
        else:
            ctx = RiskContext(broker=broker, symbol=symbol, broker_connected=False, data_quality_ok=dq.passed)

        # 12. RiskEngine (final authority — agents cannot override)
        self._emit("Risk Engine", "Final trade authorization")
        risk = self.risk.evaluate(sig, conf, ctx, plan.position_size_usd or notional)
        if cio.final_action == "NO_TRADE":
            risk = RiskDecision(False, risk.rejection_reasons + ["CIO recommended NO_TRADE"], None, risk.risk_score)

        if risk.approved:
            self._emit("Risk Engine", f"APPROVED — score {risk.risk_score:.0f}", "trade")
        else:
            self._emit("Risk Engine", "; ".join(risk.rejection_reasons[:3]), "warn")

        # 13. Broker execution
        order: Optional[OrderResult] = None
        route_broker = broker
        if risk.approved and sig.setup_detected and sig.direction not in ("HOLD", "NO_TRADE"):
            if MODE == "DRY_RUN" and broker != "futures_simulator":
                route_broker = "dry_run"
            self._emit("Broker Router", f"Executing {sig.direction} on {route_broker}")
            raw = self.router.route_order(
                route_broker, sig, symbol,
                risk.adjusted_size or plan.position_size_usd or notional,
                qty=1, current_price=current_price,
            )
            order = OrderResult(raw.success, route_broker, raw.order_id, raw.message, raw.fill_price, raw.qty)
            if raw.success:
                self._emit("Execution", raw.message, "trade")
                discord_notifier.notify("Trade Entry", f"{sig.direction} {symbol}", "trade")
            else:
                self._emit("Execution", raw.message, "error")

        elapsed = (time.time() - t0) * 1000
        STATE.last_scan_duration_ms = elapsed
        result = ScanResult(
            evaluation_id, symbol, route_broker, sig, conf, risk, order, agents_out,
            indicator_snapshot=indicator_snap, trade_plan=plan.to_dict(),
            cio_decision=cio.consensus_summary, regime=regime.regime, scan_duration_ms=elapsed,
        )
        self.journal.log_scan(result, risk.approved, risk.rejection_reasons)
        STATE.sync_from_brokers(self.router)
        self._emit("Scan Complete", f"{symbol} in {elapsed:.0f}ms — approved={risk.approved}")
        return result

    def run_one_scan(self) -> List[ScanResult]:
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
        stocks = stock_symbols or DEFAULT_STOCK_SYMBOLS[:5]
        futures = futures_symbols or DEFAULT_FUTURES_SYMBOLS[:3]

        for sym in stocks:
            try:
                results.append(self.scan_symbol(sym, "dry_run"))
            except Exception as exc:
                logger.exception("Scan failed %s: %s", sym, exc)
                self._log_failure(sym, "dry_run", str(exc))
            if MODE == "PAPER":
                try:
                    results.append(self.scan_symbol(sym, "alpaca_paper"))
                except Exception as exc:
                    self._log_failure(sym, "alpaca_paper", str(exc))

        for sym in futures:
            try:
                results.append(self.scan_symbol(sym, "futures_simulator"))
            except Exception as exc:
                self._log_failure(sym, "futures_simulator", str(exc))

        STATE.touch_scan()
        STATE.sync_from_brokers(self.router)
        STATE.last_scan_results = results
        return results
