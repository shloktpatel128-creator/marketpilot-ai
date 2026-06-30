"""Tests for FuturesSimulator tick math."""

from brokers.futures_simulator import FuturesSimulator
from data.futures_data import get_spec


def test_tick_value_mes():
    spec = get_spec("MES")
    assert spec is not None
    sim = FuturesSimulator()
    # Buy at 5000, sell at 5001 = 4 ticks (tick_size 0.25) -> 4 * tick_value
    r = sim.place_order("MES", "BUY", qty=1, price=5000.0)
    assert r.success
    pos = sim.state.positions[0]
    ticks = (5001.0 - pos.entry_price) / spec.tick_size
    pnl = ticks * spec.tick_value * 1
    assert spec.tick_value > 0
    assert spec.tick_size == 0.25


def test_unsupported_symbol_rejected():
    sim = FuturesSimulator()
    r = sim.place_order("INVALID", "BUY", qty=1, price=100.0)
    assert not r.success


def test_duplicate_order_blocked():
    sim = FuturesSimulator()
    sim.state.pending_symbols.add("MES")
    r = sim.place_order("MES", "BUY", qty=1, price=5000.0)
    assert not r.success
    assert "Duplicate" in r.message
