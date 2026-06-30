"""
Premium Plotly chart builders — TradingView-inspired.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.theme import (
    ACCENT_BLUE,
    ACCENT_CHERRY,
    ACCENT_GREEN,
    ACCENT_PURPLE,
    ACCENT_RED,
    ACCENT_YELLOW,
    BG_CARD,
    CHART_HEIGHT_MAIN,
    CHART_HEIGHT_SUB,
    CHART_LAYOUT,
    GREEN,
    RED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    YELLOW,
)


def _apply_layout(fig: go.Figure, title: str = "", height: int = CHART_HEIGHT_MAIN) -> go.Figure:
    layout = {
        **CHART_LAYOUT,
        "height": height,
        "title": dict(text=title, font=dict(size=14, color=TEXT_PRIMARY), x=0.02, xanchor="left"),
    }
    fig.update_layout(**layout)
    return fig


def sparkline(series: pd.Series, color: str = ACCENT_CHERRY) -> go.Figure:
    """Tiny sparkline for metric cards."""
    fig = go.Figure(go.Scatter(
        x=list(range(len(series))),
        y=series.values,
        mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba(230,57,99,0.12)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=36, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def main_trading_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """TradingView-style chart: candlesticks + volume + MAs + Bollinger."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25], vertical_spacing=0.03,
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color=GREEN, increasing_fillcolor=GREEN,
        decreasing_line_color=RED, decreasing_fillcolor=RED,
        line=dict(width=1),
    ), row=1, col=1)

    ma_styles = [
        ("SMA_20", YELLOW, "SMA 20"),
        ("SMA_50", ACCENT_BLUE, "SMA 50"),
        ("SMA_200", ACCENT_PURPLE, "SMA 200"),
    ]
    for col, color, label in ma_styles:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=label,
                line=dict(color=color, width=1.2),
                hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
            ), row=1, col=1)

    if "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"], name="BB Upper",
            line=dict(color="rgba(148,163,184,0.4)", width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"], name="BB Lower",
            line=dict(color="rgba(148,163,184,0.4)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(59,130,246,0.05)",
            showlegend=False,
        ), row=1, col=1)

    if "Volume" in df.columns:
        colors = [GREEN if c >= o else RED for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], name="Volume",
            marker_color=colors, opacity=0.5,
        ), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1, title_font=dict(size=11))
    fig.update_yaxes(title_text="Vol", row=2, col=1, title_font=dict(size=11))
    return _apply_layout(fig, f"{ticker}", height=CHART_HEIGHT_MAIN)


def price_chart(df: pd.DataFrame, ticker: str, show_bb: bool = False) -> go.Figure:
    """Legacy wrapper — uses main chart when show_bb=False, bollinger overlay when True."""
    if show_bb:
        return main_trading_chart(df, ticker)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=GREEN, decreasing_line_color=RED,
    ))
    for col, color, label in [("SMA_20", YELLOW, "SMA 20"), ("SMA_50", ACCENT_BLUE, "SMA 50"), ("SMA_200", ACCENT_PURPLE, "SMA 200")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=label, line=dict(color=color, width=1.5)))
    fig.update_layout(xaxis_rangeslider_visible=False)
    return _apply_layout(fig, f"{ticker} — Price")


def bollinger_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    return main_trading_chart(df, ticker)


def macd_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close", line=dict(color=ACCENT_BLUE, width=1.5)), row=1, col=1)
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color=ACCENT_CHERRY, width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(color=YELLOW, width=1.5)), row=2, col=1)
        colors = [GREEN if v >= 0 else RED for v in df["MACD_Hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Hist", marker_color=colors, opacity=0.7), row=2, col=1)
    return _apply_layout(fig, f"{ticker} — MACD", height=CHART_HEIGHT_SUB)


def rsi_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI",
            line=dict(color=ACCENT_CHERRY, width=2),
            fill="tozeroy", fillcolor="rgba(230,57,99,0.08)",
        ))
        fig.add_hrect(y0=70, y1=100, fillcolor=RED, opacity=0.06, line_width=0)
        fig.add_hrect(y0=0, y1=30, fillcolor=GREEN, opacity=0.06, line_width=0)
        fig.add_hline(y=70, line_dash="dot", line_color=RED, opacity=0.5)
        fig.add_hline(y=30, line_dash="dot", line_color=GREEN, opacity=0.5)
        fig.update_yaxes(range=[0, 100])
    return _apply_layout(fig, f"{ticker} — RSI", height=CHART_HEIGHT_SUB)


def equity_curve_chart(strategy_curve: pd.Series, buy_hold_curve: pd.Series) -> go.Figure:
    fig = go.Figure()
    if not strategy_curve.empty:
        fig.add_trace(go.Scatter(
            x=strategy_curve.index, y=strategy_curve.values,
            name="Strategy", line=dict(color=GREEN, width=2.5),
            fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
        ))
    if not buy_hold_curve.empty:
        fig.add_trace(go.Scatter(
            x=buy_hold_curve.index, y=buy_hold_curve.values,
            name="Buy & Hold", line=dict(color=TEXT_MUTED, width=2, dash="dash"),
        ))
    fig.update_layout(yaxis_title="Portfolio ($)")
    return _apply_layout(fig, "Equity Curve", height=CHART_HEIGHT_SUB)


def radar_chart(scores: dict) -> go.Figure:
    """Animated-style radar for AI score breakdown."""
    labels = ["Technical", "Momentum", "Volatility", "Risk", "Overall"]
    key_map = {
        "Technical": "Technical Score",
        "Momentum": "Momentum Score",
        "Volatility": "Volatility Score",
        "Risk": "Risk Score",
        "Overall": "Overall Score",
    }
    values = [scores.get(key_map[l], 50) for l in labels]
    values_closed = values + [values[0]]
    labels_closed = labels + [labels[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        fillcolor="rgba(230,57,99,0.15)",
        line=dict(color=ACCENT_CHERRY, width=2),
        name="Scores",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color=TEXT_MUTED, size=9)),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color=TEXT_PRIMARY, size=11)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT_PRIMARY),
        height=340,
        margin=dict(l=60, r=60, t=40, b=40),
        showlegend=False,
    )
    return fig


def sentiment_gauge(bullish_pct: float, title: str = "Market Sentiment") -> go.Figure:
    """Gauge chart for bullish percentage."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=bullish_pct,
        number=dict(suffix="%", font=dict(color=TEXT_PRIMARY, size=28)),
        title=dict(text=title, font=dict(color=TEXT_MUTED, size=13)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=TEXT_MUTED, tickwidth=1),
            bar=dict(color=ACCENT_CHERRY),
            bgcolor=BG_CARD,
            borderwidth=0,
            steps=[
                dict(range=[0, 35], color="rgba(239,68,68,0.2)"),
                dict(range=[35, 65], color="rgba(251,191,36,0.2)"),
                dict(range=[65, 100], color="rgba(16,185,129,0.2)"),
            ],
            threshold=dict(line=dict(color=GREEN, width=3), value=bullish_pct),
        ),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=30, r=30, t=50, b=10),
        font=dict(family="Inter", color=TEXT_PRIMARY),
    )
    return fig


def fear_greed_gauge(score: float) -> go.Figure:
    """Fear & Greed index gauge."""
    label = "Extreme Fear" if score < 25 else "Fear" if score < 45 else "Neutral" if score < 55 else "Greed" if score < 75 else "Extreme Greed"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        title=dict(text=f"Fear & Greed — {label}", font=dict(color=TEXT_MUTED, size=12)),
        number=dict(font=dict(color=TEXT_PRIMARY, size=26)),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=YELLOW),
            bgcolor=BG_CARD,
            borderwidth=0,
            steps=[
                dict(range=[0, 25], color="rgba(239,68,68,0.25)"),
                dict(range=[25, 50], color="rgba(251,191,36,0.2)"),
                dict(range=[50, 75], color="rgba(16,185,129,0.15)"),
                dict(range=[75, 100], color="rgba(16,185,129,0.25)"),
            ],
        ),
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(l=30, r=30, t=60, b=10))
    return fig
