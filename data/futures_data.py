"""Micro futures contract specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import yfinance as yf


@dataclass
class FuturesContract:
    symbol: str
    name: str
    yahoo_symbol: str
    tick_size: float
    tick_value: float
    margin: float = 1000.0


FUTURES_SPECS: Dict[str, FuturesContract] = {
    "MES": FuturesContract("MES", "Micro E-mini S&P", "ES=F", 0.25, 1.25),
    "MNQ": FuturesContract("MNQ", "Micro E-mini Nasdaq", "NQ=F", 0.25, 0.50),
    "MGC": FuturesContract("MGC", "Micro Gold", "GC=F", 0.10, 1.00),
    "MCL": FuturesContract("MCL", "Micro Crude Oil", "CL=F", 0.01, 1.00),
    "MYM": FuturesContract("MYM", "Micro Dow", "YM=F", 1.0, 0.50),
    "M2K": FuturesContract("M2K", "Micro Russell", "RTY=F", 0.10, 0.50),
}


def get_spec(symbol: str) -> Optional[FuturesContract]:
    return FUTURES_SPECS.get(symbol.upper())


def fetch_futures_bars(symbol: str, period: str = "3mo") -> pd.DataFrame:
    spec = get_spec(symbol)
    if not spec:
        return pd.DataFrame()
    try:
        df = yf.Ticker(spec.yahoo_symbol).history(period=period, interval="1d", auto_adjust=True)
        if df.empty:
            return df
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()
