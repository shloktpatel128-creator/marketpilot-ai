"""
Strategy backtesting engine.

Simulates the signal-based strategy on historical data and compares
performance against a simple buy-and-hold benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from config import SLIPPAGE_PCT, TRANSACTION_COST_PCT
from strategy import generate_signal


@dataclass
class BacktestResult:
    """Summary statistics from a backtest run."""

    total_return_pct: float
    buy_hold_return_pct: float
    win_rate_pct: float
    max_drawdown_pct: float
    num_trades: int
    num_wins: int
    num_losses: int
    final_equity: float
    equity_curve: pd.Series
    trades: pd.DataFrame
    alpha_pct: float  # strategy return minus buy-and-hold


def _apply_costs(price: float, is_buy: bool) -> float:
    """Adjust price for transaction costs and slippage."""
    cost = price * (TRANSACTION_COST_PCT + SLIPPAGE_PCT)
    return price + cost if is_buy else price - cost


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 10_000.0,
    min_confidence: int = 50,
) -> BacktestResult:
    """
    Backtest the signal strategy on historical OHLCV + indicator data.

    Rules:
      - Go long on BUY when confidence >= min_confidence and flat.
      - Exit on SELL when confidence >= min_confidence and long.
      - One position at a time, full capital deployment.

    Args:
        df: DataFrame with OHLCV and indicator columns.
        initial_capital: Starting cash.
        min_confidence: Minimum signal confidence to act.

    Returns:
        BacktestResult with metrics and trade log.
    """
    if df is None or len(df) < 30:
        empty_trades = pd.DataFrame(columns=[
            "entry_date", "exit_date", "entry_price", "exit_price",
            "return_pct", "pnl", "signal_reason",
        ])
        return BacktestResult(
            total_return_pct=0.0,
            buy_hold_return_pct=0.0,
            win_rate_pct=0.0,
            max_drawdown_pct=0.0,
            num_trades=0,
            num_wins=0,
            num_losses=0,
            final_equity=initial_capital,
            equity_curve=pd.Series(dtype=float),
            trades=empty_trades,
            alpha_pct=0.0,
        )

    cash = initial_capital
    shares = 0.0
    entry_price = 0.0
    entry_date = None

    equity_values = []
    equity_dates = []
    trades_log = []

    start_price = float(df["Close"].iloc[0])
    end_price = float(df["Close"].iloc[-1])

    entry_reason = ""

    for i in range(1, len(df)):
        row = df.iloc[i]
        price = float(row["Close"])
        date = df.index[i]

        sig = generate_signal(df, bar_index=i)

        # Mark-to-market equity
        equity = cash + shares * price
        equity_values.append(equity)
        equity_dates.append(date)

        if sig.confidence < min_confidence:
            continue

        # BUY: enter long
        if sig.action == "BUY" and shares == 0:
            fill_price = _apply_costs(price, is_buy=True)
            shares = cash / fill_price
            cash = 0.0
            entry_price = fill_price
            entry_date = date
            entry_reason = "; ".join(sig.reasons[:3]) if sig.reasons else sig.action

        # SELL: exit long
        elif sig.action == "SELL" and shares > 0:
            fill_price = _apply_costs(price, is_buy=False)
            proceeds = shares * fill_price
            pnl = proceeds - (shares * entry_price)
            ret_pct = (fill_price / entry_price - 1) * 100
            exit_reason = "; ".join(sig.reasons[:3]) if sig.reasons else sig.action

            trades_log.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": round(entry_price, 4),
                "exit_price": round(fill_price, 4),
                "return_pct": round(ret_pct, 2),
                "pnl": round(pnl, 2),
                "signal_reason": exit_reason,
            })

            cash = proceeds
            shares = 0.0
            entry_price = 0.0
            entry_date = None

    # Close any open position at last price
    if shares > 0:
        last_price = float(df["Close"].iloc[-1])
        fill_price = _apply_costs(last_price, is_buy=False)
        proceeds = shares * fill_price
        pnl = proceeds - (shares * entry_price)
        ret_pct = (fill_price / entry_price - 1) * 100
        trades_log.append({
            "entry_date": entry_date,
            "exit_date": df.index[-1],
            "entry_price": round(entry_price, 4),
            "exit_price": round(fill_price, 4),
            "return_pct": round(ret_pct, 2),
            "pnl": round(pnl, 2),
            "signal_reason": "End of backtest — position closed",
        })
        cash = proceeds
        shares = 0.0

    final_equity = cash
    total_return = (final_equity / initial_capital - 1) * 100
    buy_hold_return = (end_price / start_price - 1) * 100

    trades_df = pd.DataFrame(trades_log)
    num_trades = len(trades_df)
    num_wins = int((trades_df["pnl"] > 0).sum()) if num_trades > 0 else 0
    num_losses = num_trades - num_wins
    win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0.0

    equity_curve = pd.Series(equity_values, index=equity_dates, name="equity")

    # Max drawdown
    if len(equity_curve) > 0:
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max * 100
        max_dd = float(drawdown.min())
    else:
        max_dd = 0.0

    return BacktestResult(
        total_return_pct=round(total_return, 2),
        buy_hold_return_pct=round(buy_hold_return, 2),
        win_rate_pct=round(win_rate, 2),
        max_drawdown_pct=round(max_dd, 2),
        num_trades=num_trades,
        num_wins=num_wins,
        num_losses=num_losses,
        final_equity=round(final_equity, 2),
        equity_curve=equity_curve,
        trades=trades_df,
        alpha_pct=round(total_return - buy_hold_return, 2),
    )


def buy_hold_equity_curve(
    df: pd.DataFrame,
    initial_capital: float = 10_000.0,
) -> pd.Series:
    """Compute buy-and-hold equity curve for chart overlay."""
    if df.empty:
        return pd.Series(dtype=float)
    shares = initial_capital / float(df["Close"].iloc[0])
    return shares * df["Close"]
