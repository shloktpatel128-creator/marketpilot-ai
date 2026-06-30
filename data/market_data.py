"""OHLCV market data via yfinance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import yfinance as yf

from config import VALID_INTERVALS, VALID_PERIODS


@dataclass
class TickerValidation:
    ticker: str
    is_valid: bool
    name: Optional[str] = None
    warning: Optional[str] = None


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def validate_ticker(ticker: str) -> TickerValidation:
    symbol = normalize_ticker(ticker)
    if not symbol:
        return TickerValidation(symbol, False, warning="Empty ticker.")
    if not re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", symbol):
        return TickerValidation(symbol, False, warning=f"Invalid format: {symbol}")
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        name = info.get("shortName") or info.get("longName")
        hist = stock.history(period="1mo", interval="1d")
        if hist is None or hist.empty or len(hist) < 5:
            return TickerValidation(symbol, False, name=name, warning="Insufficient data.")
        return TickerValidation(symbol, True, name=name)
    except Exception as exc:
        return TickerValidation(symbol, False, warning=str(exc))


def fetch_ohlcv(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> Tuple[pd.DataFrame, Optional[str]]:
    symbol = normalize_ticker(ticker)
    warning: Optional[str] = None
    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period: {period}")
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval: {interval}")
    if interval == "1h" and period in ("1y", "5y"):
        warning = "Hourly limited to ~3mo; using 3mo."
        period = "3mo"
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame(), f"No data for {symbol}"
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[cols].copy().dropna(subset=["Close"])
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df, warning
    except Exception as exc:
        return pd.DataFrame(), str(exc)
