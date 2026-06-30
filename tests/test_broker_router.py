"""Tests for BrokerRouter isolation."""

from brokers.broker_router import BrokerRouter
from storage.schemas import StrategySignal


def _sig():
    return StrategySignal(
        True, "BUY", 100.0, 95.0, 110.0, 2.0, "test", [], "test",
    )


def test_brokers_have_isolated_state():
    router = BrokerRouter()
    r1 = router.route_order("dry_run", _sig(), "AAPL", 1000)
    r2 = router.route_order("futures_simulator", _sig(), "MES", 1000, qty=1, current_price=5000.0)
    assert r1.success
    assert r2.success
    assert len(router.dry_run.state["orders"]) >= 1
    assert len(router.futures.state.orders) >= 1
    assert router.dry_run.state is not router.futures.state


def test_alpaca_failure_does_not_break_futures():
    router = BrokerRouter()
    router.alpaca._error = "simulated failure"
    router.alpaca._client = None
    fut = router.route_order("futures_simulator", _sig(), "MNQ", 1000, qty=1, current_price=18000.0)
    assert fut.success
