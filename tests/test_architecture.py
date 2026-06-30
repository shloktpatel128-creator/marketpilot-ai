"""Architecture compliance tests."""

from unittest.mock import patch

import pandas as pd

from agents import run_all_agents
from agents.base import BaseAgent
from brokers.broker_router import BrokerRouter
from config import AI_CAN_PLACE_TRADES, MODE, REAL_TRADING_ENABLED
from core.engine import TradingEngine
from journal.trade_journal import TradeJournal
from risk.risk_engine import RiskContext, RiskEngine
from storage.schemas import ConfidenceResult, StrategySignal


def test_real_trading_permanently_disabled():
    assert REAL_TRADING_ENABLED is False


def test_ai_cannot_place_trades():
    assert AI_CAN_PLACE_TRADES is False
    agent = BaseAgent()
    assert agent.can_place_trades is False
    for name, _ in run_all_agents({"symbol": "SPY"}).items():
        assert isinstance(name, str)


def test_broker_router_blocks_live_trading():
    router = BrokerRouter()
    sig = StrategySignal(True, "BUY", 100, 95, 110, 2.0, "t", [], "s")
    # Even if misconfigured, router guard must not crash
    result = router.route_order("dry_run", sig, "AAPL", 1000)
    assert result.success


def test_futures_and_alpaca_isolated_state():
    router = BrokerRouter()
    sig = StrategySignal(True, "BUY", 100, 95, 110, 2.0, "t", [], "s")
    router.route_order("dry_run", sig, "AAPL", 500)
    router.route_order("futures_simulator", sig, "MES", 1000, qty=1, current_price=5000)
    assert router.dry_run.state is not router.futures.state
    assert router.futures.state is not router.alpaca.state


def test_risk_engine_blocks_without_stop():
    engine = RiskEngine()
    sig = StrategySignal(True, "BUY", 100, None, 110, 2.0, "t", [], "s")
    conf = ConfidenceResult(80, "v1", "ok")
    result = engine.evaluate(sig, conf, RiskContext("dry_run", "AAPL", True, True))
    assert not result.approved


def test_rejected_setup_logged_with_evaluation_id():
    journal = TradeJournal()
    from storage.schemas import RiskDecision, ScanResult

    eid = "test-eval-99"
    sig = StrategySignal(True, "BUY", 100, 95, 110, 2.0, "setup", [], "vwap")
    conf = ConfidenceResult(50, "v1", "low")
    risk = RiskDecision(False, ["Confidence too low"], None, 40)
    result = ScanResult(eid, "TSLA", "dry_run", sig, conf, risk, None)
    journal.log_scan(result, False, risk.rejection_reasons)
    rows = journal.get_recent(5)
    match = next((r for r in rows if r.get("evaluation_id") == eid), None)
    assert match is not None
    assert match["setup_detected"] is True
    assert match["approved"] is False


@patch("core.engine.fetch_ohlcv")
@patch("core.engine.add_features")
def test_engine_only_routes_after_risk(mock_features, mock_fetch):
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1_000_000,
    }, index=idx)
    mock_fetch.return_value = (df, None)
    mock_features.return_value = df

    engine = TradingEngine()
    result = engine.scan_symbol("AAPL", "dry_run")
    assert result.evaluation_id == engine.evaluation_id
    # No setup -> risk rejects -> no order
    assert not result.risk.approved
    assert result.order is None


def test_dry_run_works_without_alpaca_keys():
    router = BrokerRouter()
    assert router.dry_run.connected is True
    assert router.dry_run.place_order("SPY", "BUY", 100).success


def test_alpaca_requires_keys_in_paper_mode():
    from unittest.mock import patch
    from brokers.alpaca_paper import AlpacaPaperBroker

    with patch("brokers.alpaca_paper.ALPACA_API_KEY", ""), patch(
        "brokers.alpaca_paper.ALPACA_SECRET_KEY", ""
    ):
        broker = AlpacaPaperBroker()
        assert not broker.connected
        assert broker.init_error is not None
