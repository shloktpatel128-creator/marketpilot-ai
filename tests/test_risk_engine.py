"""Tests for RiskEngine."""

import pytest

from risk.risk_engine import RiskContext, RiskEngine
from storage.schemas import ConfidenceResult, StrategySignal


def _signal(**kwargs):
    defaults = dict(
        setup_detected=True, direction="BUY", entry=100.0, stop_loss=95.0,
        take_profit=110.0, reward_risk=2.0, reason="test", strategy_name="test",
    )
    defaults.update(kwargs)
    return StrategySignal(**defaults)


def _ctx(**kwargs):
    defaults = dict(broker="dry_run", symbol="AAPL", broker_connected=True, data_quality_ok=True)
    defaults.update(kwargs)
    return RiskContext(**defaults)


def test_rejects_missing_stop_loss():
    engine = RiskEngine()
    sig = _signal(stop_loss=None)
    conf = ConfidenceResult(75, "v1", "ok")
    result = engine.evaluate(sig, conf, _ctx())
    assert not result.approved
    assert any("stop loss" in r.lower() for r in result.rejection_reasons)


def test_rejects_low_confidence():
    engine = RiskEngine()
    sig = _signal()
    conf = ConfidenceResult(40, "v1", "low")
    result = engine.evaluate(sig, conf, _ctx())
    assert not result.approved
    assert any("confidence" in r.lower() for r in result.rejection_reasons)


def test_approves_valid_trade():
    engine = RiskEngine()
    sig = _signal()
    conf = ConfidenceResult(80, "v1", "ok")
    result = engine.evaluate(sig, conf, _ctx())
    assert result.approved
    assert result.adjusted_size is not None
