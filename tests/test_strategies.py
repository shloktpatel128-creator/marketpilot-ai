"""Unit tests for strategy setup detection."""

import numpy as np
import pandas as pd
import pytest

from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.reversal import ReversalStrategy
from strategies.scanner import scan_all_strategies
from strategies.trend_continuation import TrendContinuationStrategy
from strategies.vwap_momentum import VWAPMomentumStrategy


def _base_df(n: int = 60, close: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=idx,
    )


def _vwap_buy_df() -> pd.DataFrame:
    df = _base_df(60, 105.0)
    df["VWAP"] = 102.0
    df["Momentum_10"] = 1.5
    df["Volume_Ratio"] = 1.2
    df["RSI"] = 55.0
    df["MACD_Hist"] = 0.5
    df["ATR_14"] = 2.0
    return df


def _breakout_buy_df() -> pd.DataFrame:
    df = _base_df(30, 110.0)
    # Flat range then breakout on last bar
    df.loc[df.index[:-1], "High"] = 105.0
    df.loc[df.index[:-1], "Low"] = 95.0
    df.loc[df.index[:-1], "Close"] = 100.0
    df.iloc[-1, df.columns.get_loc("High")] = 111.0
    df.iloc[-1, df.columns.get_loc("Close")] = 110.0
    df["Volume_Ratio"] = 1.5
    return df


def _pullback_buy_df() -> pd.DataFrame:
    df = _base_df(60, 102.0)
    df["SMA_20"] = 101.5
    df["SMA_50"] = 98.0
    df["EMA_20"] = 101.8
    df["RSI"] = 40.0
    df["ADX"] = 28.0
    df["ATR_14"] = 1.5
    return df


def test_vwap_momentum_detects_buy():
    sig = VWAPMomentumStrategy().evaluate(_vwap_buy_df(), "AAPL")
    assert sig.setup_detected
    assert sig.direction == "BUY"
    assert sig.stop_loss is not None
    assert sig.take_profit is not None
    assert sig.reward_risk >= 1.5
    assert sig.setup_confidence >= 55
    assert sig.invalidation_level is not None


def test_breakout_detects_buy():
    sig = BreakoutStrategy().evaluate(_breakout_buy_df(), "AAPL")
    assert sig.setup_detected
    assert sig.direction == "BUY"
    assert sig.reward_risk >= 1.5


def test_pullback_detects_buy():
    sig = PullbackStrategy().evaluate(_pullback_buy_df(), "AAPL")
    assert sig.setup_detected
    assert sig.direction == "BUY"
    assert sig.stop_loss is not None


def test_scanner_picks_best_setup():
    df = _vwap_buy_df()
    best, all_sigs, debug = scan_all_strategies(df, "AAPL")
    assert best.setup_detected
    assert best.direction == "BUY"
    assert "_selected" in debug
    assert len(all_sigs) == 5


def test_hold_when_no_setup():
    df = _base_df(60, 100.0)
    df["VWAP"] = 100.0
    df["Momentum_10"] = 0.0
    df["Volume_Ratio"] = 0.5
    df["RSI"] = 50.0
    df["MACD_Hist"] = 0.0
    sig = VWAPMomentumStrategy().evaluate(df, "AAPL")
    assert not sig.setup_detected
    assert sig.direction == "HOLD"
    assert sig.debug_notes
