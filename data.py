"""
Market data fetching and ticker validation using yfinance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import yfinance as yf

from config import VALID_INTERVALS, VALID_PERIODS


@dataclass
class TickerValidation:
    """Result of validating a stock ticker."""

    ticker: str
    is_valid: bool
    name: Optional[str] = None
    warning: Optional[str] = None


def normalize_ticker(ticker: str) -> str:
    """Uppercase and strip whitespace from a ticker symbol."""
    return ticker.strip().upper()


def is_ticker_format_valid(ticker: str) -> bool:
    """Basic format check: 1–5 letters, optional dot suffix (e.g. BRK.B)."""
    return bool(re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", ticker))


def validate_ticker(ticker: str) -> TickerValidation:
    """
    Validate that a ticker exists and has usable market data.

    Returns a TickerValidation with warnings if data is missing or sparse.
    """
    symbol = normalize_ticker(ticker)

    if not symbol:
        return TickerValidation(ticker=symbol, is_valid=False, warning="Ticker cannot be empty.")

    if not is_ticker_format_valid(symbol):
        return TickerValidation(
            ticker=symbol,
            is_valid=False,
            warning=f"'{symbol}' does not look like a valid ticker format.",
        )

    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        name = info.get("shortName") or info.get("longName")

        # Quick history check — need at least a few rows
        hist = stock.history(period="1mo", interval="1d")
        if hist is None or hist.empty or len(hist) < 5:
            return TickerValidation(
                ticker=symbol,
                is_valid=False,
                name=name,
                warning=(
                    f"No recent price data found for '{symbol}'. "
                    "The symbol may be delisted, invalid, or have limited data."
                ),
            )

        warning = None
        if hist["Close"].isna().sum() > len(hist) * 0.2:
            warning = f"'{symbol}' has significant missing price data."

        return TickerValidation(ticker=symbol, is_valid=True, name=name, warning=warning)

    except Exception as exc:
        return TickerValidation(
            ticker=symbol,
            is_valid=False,
            warning=f"Could not validate '{symbol}': {exc}",
        )


def fetch_ohlcv(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Download OHLCV historical data for a ticker.

    Args:
        ticker: Stock symbol (e.g. 'AAPL').
        period: Lookback window — one of VALID_PERIODS.
        interval: Bar size — '1d' (daily) or '1h' (hourly, shorter periods only).

    Returns:
        (dataframe, warning_message) — DataFrame has columns Open, High, Low, Close, Volume.
    """
    symbol = normalize_ticker(ticker)
    warning: Optional[str] = None

    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period '{period}'. Choose from: {VALID_PERIODS}")

    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval '{interval}'. Choose from: {VALID_INTERVALS}")

    # Hourly data is only available for shorter lookbacks on Yahoo Finance
    if interval == "1h" and period in ("1y", "5y"):
        warning = (
            "Hourly data is limited to ~60 days on Yahoo Finance. "
            "Using period='3mo' instead."
        )
        period = "3mo"

    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period, interval=interval, auto_adjust=True)

        if df is None or df.empty:
            return pd.DataFrame(), f"No data returned for '{symbol}'."

        # Keep standard columns and drop rows with no close price
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[cols].copy()
        df.dropna(subset=["Close"], inplace=True)

        if df.empty:
            return pd.DataFrame(), f"All rows had missing Close prices for '{symbol}'."

        if len(df) < 20:
            extra = (
                f" Only {len(df)} bars available — indicators may be unreliable."
            )
            warning = (warning or "") + extra

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        return df, warning

    except Exception as exc:
        return pd.DataFrame(), f"Failed to fetch data for '{symbol}': {exc}"


def get_latest_price(ticker: str) -> Optional[float]:
    """Return the most recent closing price, or None on failure."""
    df, _ = fetch_ohlcv(ticker, period="5d", interval="1d")
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])
