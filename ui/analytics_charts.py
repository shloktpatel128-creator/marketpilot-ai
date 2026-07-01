"""Analytics charts for dashboard."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.theme import ACCENT_CHERRY, CHART_LAYOUT, GREEN, RED


def confidence_gauge(score: float, title: str = "AI Confidence") -> go.Figure:
    color = GREEN if score >= 60 else ACCENT_CHERRY if score >= 40 else RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, title={"text": title},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
               "steps": [{"range": [0, 40], "color": "rgba(239,68,68,0.2)"},
                         {"range": [40, 60], "color": "rgba(251,191,36,0.2)"},
                         {"range": [60, 100], "color": "rgba(16,185,129,0.2)"}]},
    ))
    fig.update_layout(**CHART_LAYOUT, height=220)
    return fig


def sentiment_gauge(score: float) -> go.Figure:
    label = "Bullish" if score > 0.1 else "Bearish" if score < -0.1 else "Neutral"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=score * 100, title={"text": f"News Sentiment ({label})"},
        number={"suffix": "%"}, gauge={"axis": {"range": [-100, 100]}, "bar": {"color": ACCENT_CHERRY}},
    ))
    fig.update_layout(**CHART_LAYOUT, height=220)
    return fig


def volatility_gauge(vol_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=vol_pct, title={"text": "Volatility (20d ann.)"},
        number={"suffix": "%"}, gauge={"axis": {"range": [0, 80]}},
    ))
    fig.update_layout(**CHART_LAYOUT, height=220)
    return fig


def equity_curve(rows: List[dict]) -> go.Figure:
    if not rows:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="Equity Curve", height=300)
        return fig
    df = pd.DataFrame(rows).sort_values("timestamp")
    cum = df.get("confidence", pd.Series([0] * len(df))).cumsum()
    fig = go.Figure(go.Scatter(x=list(range(len(cum))), y=cum, fill="tozeroy", line={"color": ACCENT_CHERRY}))
    fig.update_layout(**CHART_LAYOUT, title="Cumulative Signal Strength", height=300)
    return fig


def drawdown_chart(rows: List[dict]) -> go.Figure:
    fig = go.Figure()
    if rows:
        pnls = [float(r.get("pnl") or 0) for r in rows]
        equity = pd.Series(pnls).cumsum()
        peak = equity.cummax()
        dd = (equity - peak)
        fig.add_trace(go.Scatter(y=dd, fill="tozeroy", line={"color": RED}, name="Drawdown"))
    fig.update_layout(**CHART_LAYOUT, title="Drawdown", height=250)
    return fig


def trade_distribution(rows: List[dict]) -> go.Figure:
    symbols = [r.get("symbol", "?") for r in rows if r.get("approved")]
    if not symbols:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="Trade Distribution", height=250)
        return fig
    counts = pd.Series(symbols).value_counts()
    fig = go.Figure(go.Bar(x=counts.index, y=counts.values, marker_color=ACCENT_CHERRY))
    fig.update_layout(**CHART_LAYOUT, title="Trades by Symbol", height=250)
    return fig
