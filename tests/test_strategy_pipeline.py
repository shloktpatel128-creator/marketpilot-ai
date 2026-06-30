"""Tests for strategy pipeline and agent safety."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from agents.base import BaseAgent
from config import AI_CAN_PLACE_TRADES
from core.engine import TradingEngine
from journal.trade_journal import TradeJournal
from storage.schemas import ConfidenceResult, RiskDecision, StrategySignal


def test_agents_cannot_place_trades():
    assert AI_CAN_PLACE_TRADES is False
    agent = BaseAgent()
    assert agent.can_place_trades is False
    assert not hasattr(agent, "place_order")


def test_journal_logs_rejected_trade():
    journal = TradeJournal()
    sig = StrategySignal(False, "HOLD", None, None, None, 0, "no setup", [], "vwap")
    from storage.schemas import ScanResult
    from models.confidence_model import ConfidenceModel

    conf = ConfidenceResult(0, "v1", "none")
    risk = RiskDecision(False, ["No strategy setup detected."], None, 0)
    result = ScanResult("eval1", "AAPL", "dry_run", sig, conf, risk, None)
    row_id = journal.log_scan(result, False, risk.rejection_reasons)
    assert row_id >= 0
    recent = journal.get_recent(5)
    assert any(r["symbol"] == "AAPL" for r in recent)


@patch("core.engine.fetch_ohlcv")
@patch("core.engine.add_features")
def test_pipeline_scan_with_mock_data(mock_features, mock_fetch):
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1_000_000,
    }, index=idx)
    df["VWAP"] = 99.0
    df["Momentum_10"] = 2.0
    df["Volume_Ratio"] = 1.5
    df["RSI"] = 55.0
    mock_fetch.return_value = (df, None)
    mock_features.return_value = df

    engine = TradingEngine()
    result = engine.scan_symbol("AAPL", "dry_run")
    assert result.symbol == "AAPL"
    assert result.evaluation_id
