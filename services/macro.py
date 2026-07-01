"""Macroeconomic and earnings event tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional

import yfinance as yf


@dataclass
class MacroEvent:
    name: str
    date: str
    impact: str  # high | medium | low
    category: str


@dataclass
class MacroAnalysis:
    events: List[MacroEvent] = field(default_factory=list)
    earnings_soon: bool = False
    high_impact_soon: bool = False
    risk_adjustment: float = 0.0  # subtract from confidence
    summary: str = ""


def _upcoming_fomc() -> List[MacroEvent]:
    """Known FOMC meeting pattern — 8 per year, approximate dates."""
    events = []
    year = date.today().year
    # Typical FOMC months
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    for m in fomc_months:
        d = date(year, m, 15)
        if d >= date.today() - timedelta(days=1):
            events.append(MacroEvent(f"FOMC Meeting (est.)", d.isoformat(), "high", "monetary"))
    return events[:3]


def _economic_calendar() -> List[MacroEvent]:
    today = date.today()
    events = _upcoming_fomc()
    # CPI typically mid-month
    cpi_date = date(today.year, today.month, 13)
    if cpi_date >= today:
        events.append(MacroEvent("CPI Release (est.)", cpi_date.isoformat(), "high", "inflation"))
    # Jobs report first Friday
    first = date(today.year, today.month, 1)
    days_until_fri = (4 - first.weekday()) % 7
    jobs = first + timedelta(days=days_until_fri)
    if jobs >= today:
        events.append(MacroEvent("Non-Farm Payrolls (est.)", jobs.isoformat(), "high", "employment"))
    return events


def analyze_macro(symbol: str) -> MacroAnalysis:
    result = MacroAnalysis()
    result.events = _economic_calendar()

    # Earnings check via yfinance calendar
    try:
        cal = yf.Ticker(symbol).calendar
        if cal is not None and not (hasattr(cal, "empty") and cal.empty):
            if isinstance(cal, dict):
                ed = cal.get("Earnings Date") or cal.get("Earnings Date")
                if ed:
                    result.earnings_soon = True
                    result.events.append(MacroEvent(f"{symbol} Earnings", str(ed)[:10], "high", "earnings"))
            elif hasattr(cal, "iloc"):
                result.earnings_soon = True
    except Exception:
        pass

    horizon = date.today() + timedelta(days=5)
    upcoming = [e for e in result.events if e.date <= horizon.isoformat()]
    result.high_impact_soon = any(e.impact == "high" for e in upcoming)
    if result.high_impact_soon:
        result.risk_adjustment = 10.0
    if result.earnings_soon:
        result.risk_adjustment += 15.0

    parts = [f"{len(result.events)} macro events tracked"]
    if result.earnings_soon:
        parts.append("earnings imminent")
    if result.high_impact_soon:
        parts.append("high-impact macro within 5 days")
    result.summary = "; ".join(parts)
    return result
