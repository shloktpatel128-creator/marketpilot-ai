"""
Premium UI components — HTML/CSS rendering for MarketPilot AI.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import streamlit as st

from ui.theme import (
    ACCENT_BLUE,
    ACCENT_CHERRY,
    GREEN,
    RED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    YELLOW,
)


def _html(content: str) -> None:
    """Render HTML block — content must not have leading indent (avoids markdown code blocks)."""
    # Strip leading/trailing blank lines; dedent inner content
    lines = [ln for ln in content.strip().splitlines()]
    st.markdown("\n".join(lines), unsafe_allow_html=True)


def render_top_bar(market_open: bool, paper_mode: bool = True) -> None:
    """Premium top navigation bar."""
    market_span = (
        '<span class="mp-badge mp-badge-open">🟢 Market Open</span>'
        if market_open
        else '<span class="mp-badge mp-badge-closed">🔴 Market Closed</span>'
    )
    paper_badge = "Paper Trading" if paper_mode else "Live ⚠️"
    _html(f"""
<div class="mp-topbar">
<div class="mp-search">
<span>🔍</span>
<span>Search stocks, ETFs, crypto…</span>
<kbd>⌘K</kbd>
</div>
<div style="display:flex;align-items:center;gap:12px;">
<span class="mp-badge mp-badge-paper">📋 {paper_badge}</span>
{market_span}
<span style="font-size:1.2rem;cursor:pointer;" title="Notifications">🔔</span>
<div class="mp-avatar">MP</div>
</div>
</div>
""")


def render_ticker_header(
    ticker: str,
    company: str,
    sector: str,
    industry: str,
) -> None:
    """Large ticker header with metadata."""
    safe_company = html.escape(company)
    safe_ticker = html.escape(ticker)
    _html(f"""
<div class="mp-ticker-header">
<div>
<p class="mp-ticker-name"><span class="mp-star">★</span> {safe_company} ({safe_ticker})</p>
<p class="mp-ticker-meta">{html.escape(sector)} · {html.escape(industry)}</p>
</div>
</div>
""")


def render_metric_cards(
    price: float,
    daily_change_pct: float,
    daily_change: float,
    signal_action: str,
    confidence: int,
    risk: str,
    market_open: bool,
) -> None:
    """Six premium metric cards using native Streamlit metrics (no raw HTML leak)."""
    sig_delta = signal_action
    chg_delta = f"${daily_change:+,.2f}"
    market_label = "Open" if market_open else "Closed"

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Price", f"${price:,.2f}")
    c2.metric("Daily Change", f"{daily_change_pct:+.2f}%", delta=chg_delta)
    c3.metric("Signal", signal_action)
    c4.metric("Confidence", f"{confidence}%")
    c5.metric("Risk", risk)
    c6.metric("Market", market_label)


def render_signal_card_premium(action: str, confidence: int, risk: str, explanation: str) -> None:
    """Cherry gradient signal card."""
    sig_cls = {"BUY": "mp-signal-buy", "SELL": "mp-signal-sell", "HOLD": "mp-signal-hold"}.get(action, "mp-signal-hold")
    safe_exp = html.escape(explanation)
    _html(f"""
<div class="mp-signal-card">
<div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{TEXT_SECONDARY};">Latest Signal</div>
<div class="mp-signal-action {sig_cls}">{html.escape(action)}</div>
<div style="color:{TEXT_SECONDARY};font-size:0.88rem;margin-bottom:12px;">
Confidence <strong style="color:{TEXT_PRIMARY}">{confidence}%</strong>
&nbsp;·&nbsp; Risk <strong style="color:{TEXT_PRIMARY}">{html.escape(risk)}</strong>
</div>
<p style="color:{TEXT_SECONDARY};font-size:0.92rem;line-height:1.65;margin:0;">{safe_exp}</p>
</div>
""")


def render_ai_analysis_panel(analysis: Dict[str, Any]) -> None:
    """Full AI analysis section."""
    rec = html.escape(analysis["recommendation"])
    bull_html = "".join(
        f'<div class="mp-factor mp-factor-bull">{html.escape(f)}</div>' for f in analysis["bullish_factors"]
    )
    bear_html = "".join(
        f'<div class="mp-factor mp-factor-bear">{html.escape(f)}</div>' for f in analysis["bearish_factors"]
    )
    _html(f"""
<div class="mp-glass">
<div class="mp-section-title">AI Analysis</div>
<div class="mp-ai-rec" style="color:{ACCENT_CHERRY};">{rec}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:12px 0;">
<div>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Confidence:</strong> {analysis['confidence']}%</p>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Probability:</strong> {analysis['probability']}%</p>
</div>
<div>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Entry:</strong> ${analysis['entry']:,.2f}</p>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Stop Loss:</strong> ${analysis['stop_loss']:,.2f}</p>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Take Profit:</strong> ${analysis['take_profit']:,.2f}</p>
<p style="color:{TEXT_PRIMARY};margin:4px 0;"><strong>Reward/Risk:</strong> {analysis['reward_risk']}:1</p>
</div>
</div>
<p style="color:{TEXT_SECONDARY};font-size:0.9rem;">{html.escape(analysis['reasoning'])}</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;">
<div><strong style="color:{TEXT_PRIMARY};">Top Bullish Factors</strong>{bull_html}</div>
<div><strong style="color:{TEXT_PRIMARY};">Top Bearish Factors</strong>{bear_html}</div>
</div>
<p style="color:{TEXT_SECONDARY};font-size:0.85rem;margin-top:12px;">{html.escape(analysis['risk_summary'])}</p>
</div>
""")


def render_key_levels(levels: Dict[str, float], current_price: float) -> None:
    """Support and resistance levels card."""
    supports = {k: v for k, v in levels.items() if "support" in k.lower() or "lower" in k.lower() or "sma 50" in k.lower() or "sma 200" in k.lower()}
    resistances = {k: v for k, v in levels.items() if k not in supports}

    def _rows(items: dict, color: str) -> str:
        rows = []
        for name, val in items.items():
            pct = (val / current_price - 1) * 100
            rows.append(
                f'<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">{html.escape(name)}</span>'
                f'<span style="color:{color}">${val:,.2f} ({pct:+.1f}%)</span></div>'
            )
        return "".join(rows)

    _html(f"""
<div class="mp-glass">
<div class="mp-card-title">Key Levels</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
<div><strong style="color:{TEXT_PRIMARY};">Support</strong>{_rows(supports, GREEN)}</div>
<div><strong style="color:{TEXT_PRIMARY};">Resistance</strong>{_rows(resistances, RED)}</div>
</div>
</div>
""")


def render_news_feed(news: List[Dict[str, Any]]) -> None:
    """Beautiful news cards."""
    items_html = ""
    if not news:
        items_html = f'<p style="color:{TEXT_SECONDARY};">No news available for this ticker.</p>'
    else:
        for item in news:
            sent_color = GREEN if item["sentiment"] == "bullish" else RED if item["sentiment"] == "bearish" else YELLOW
            headline = html.escape(item["headline"])
            url = html.escape(item.get("url", "#"))
            items_html += f"""
<a href="{url}" target="_blank" style="text-decoration:none;">
<div class="mp-news-item">
<div class="mp-news-headline">{headline}</div>
<div class="mp-news-meta">
<span style="color:{sent_color};font-weight:600;">{item['sentiment'].upper()}</span>
&nbsp;·&nbsp; {html.escape(item['source'])} &nbsp;·&nbsp; {html.escape(item['time'])}
</div>
</div>
</a>"""
    _html(f'<div class="mp-glass"><div class="mp-card-title">Recent News</div>{items_html}</div>')


def render_sidebar_branding() -> None:
    """Logo and title in sidebar."""
    st.sidebar.markdown(
        '<div class="mp-logo">◆ MARKETPILOT</div><div class="mp-logo-title">MARKETPILOT AI</div>',
        unsafe_allow_html=True,
    )


def render_watchlist_html(items: List[Dict[str, Any]]) -> None:
    """Watchlist display in sidebar."""
    st.sidebar.markdown('<div class="mp-section-title">Watchlist</div>', unsafe_allow_html=True)
    for item in items:
        chg = item.get("change_pct", 0)
        chg_color = GREEN if chg >= 0 else RED
        st.sidebar.markdown(
            f"""
            <div class="mp-watchlist-item">
                <div>
                    <div class="mp-wl-ticker">{html.escape(item['ticker'])}</div>
                    <div class="mp-wl-name">{html.escape(item.get('name', ''))}</div>
                </div>
                <div class="mp-wl-price">
                    <div>${item.get('price', 0):,.2f}</div>
                    <div style="color:{chg_color};font-size:0.78rem;">{chg:+.2f}%</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_paper_account_card(status: Optional[Any]) -> None:
    """Bottom paper account summary in sidebar."""
    if not status or not getattr(status, "connected", False):
        st.sidebar.markdown(
            f'<div class="mp-paper-card">'
            f'<div class="mp-card-title" style="font-size:0.85rem;margin-bottom:12px;">Paper Account</div>'
            f'<p style="color:{TEXT_SECONDARY};font-size:0.82rem;">Not connected</p></div>',
            unsafe_allow_html=True,
        )
        return

    pnl_color = GREEN if status.daily_pnl >= 0 else RED
    st.sidebar.markdown(
        f'<div class="mp-paper-card">'
        f'<div class="mp-card-title" style="font-size:0.85rem;margin-bottom:12px;">Paper Account</div>'
        f'<div class="mp-paper-row"><span class="mp-paper-label">Equity</span><span class="mp-paper-value">${status.equity:,.2f}</span></div>'
        f'<div class="mp-paper-row"><span class="mp-paper-label">Cash</span><span class="mp-paper-value">${status.cash:,.2f}</span></div>'
        f'<div class="mp-paper-row"><span class="mp-paper-label">Buying Power</span><span class="mp-paper-value">${status.buying_power:,.2f}</span></div>'
        f'<div class="mp-paper-row"><span class="mp-paper-label">Daily P/L</span><span class="mp-paper-value" style="color:{pnl_color}">${status.daily_pnl:+,.2f}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_disclaimer() -> None:
    _html(f"""
<div class="mp-glass" style="padding:14px 20px;margin-bottom:20px;border-color:rgba(251,191,36,0.15);">
<span style="color:{YELLOW};font-weight:600;">⚠ Educational use only</span>
<span style="color:{TEXT_SECONDARY};font-size:0.88rem;"> — Not financial advice. Past performance ≠ future results. Paper trading by default.</span>
</div>
""")


def render_empty_state(title: str, message: str) -> None:
    _html(f"""
<div class="mp-glass" style="text-align:center;padding:48px;">
<div style="font-size:2.5rem;margin-bottom:12px;">📊</div>
<div class="mp-card-title">{html.escape(title)}</div>
<p style="color:{TEXT_SECONDARY};">{html.escape(message)}</p>
</div>
""")


def render_calendar_placeholder() -> None:
    _html(f"""
<div class="mp-glass">
<div class="mp-card-title">Economic Calendar</div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">FOMC Meeting</span><span>—</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">CPI Release</span><span>—</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">Jobs Report</span><span>—</span></div>
<p style="color:{TEXT_SECONDARY};font-size:0.8rem;margin-top:12px;">Connect a calendar API for live data.</p>
</div>
""")


def render_earnings_placeholder(ticker: str) -> None:
    _html(f"""
<div class="mp-glass">
<div class="mp-card-title">Upcoming Earnings — {html.escape(ticker)}</div>
<p style="color:{TEXT_SECONDARY};font-size:0.88rem;">Check your broker or financial data provider for earnings dates.</p>
</div>
""")


def render_bot_command_center(bot: Dict[str, Any], compact: bool = True) -> None:
    """Overview page bot summary card."""
    status_color = GREEN if bot["status"] == "Active" else YELLOW
    sig_color = GREEN if bot["signal"] == "BUY" else RED if bot["signal"] == "SELL" else YELLOW
    block_list = "".join(f"<li style='color:{TEXT_SECONDARY};margin:4px 0;'>{html.escape(r)}</li>" for r in bot["block_reasons"]) or f"<li style='color:{GREEN};'>No blockers — paper trade eligible</li>"

    _html(f"""
<div class="mp-signal-card" style="margin-bottom:20px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
<div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ACCENT_CHERRY};">🤖 AI Trading Bot Command Center</div>
<span style="color:{status_color};font-weight:700;font-size:0.85rem;">● {html.escape(bot['status'])}</span>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
<div><div style="color:{TEXT_SECONDARY};font-size:0.72rem;">MODE</div><div style="color:{TEXT_PRIMARY};font-weight:600;">{html.escape(bot['mode'])}</div></div>
<div><div style="color:{TEXT_SECONDARY};font-size:0.72rem;">TICKER</div><div style="color:{TEXT_PRIMARY};font-weight:600;">{html.escape(bot['ticker'])}</div></div>
<div><div style="color:{TEXT_SECONDARY};font-size:0.72rem;">SIGNAL</div><div style="color:{sig_color};font-weight:700;">{html.escape(bot['signal'])}</div></div>
<div><div style="color:{TEXT_SECONDARY};font-size:0.72rem;">CONFIDENCE</div><div style="color:{TEXT_PRIMARY};font-weight:600;">{bot['confidence']}%</div></div>
</div>
<p style="color:{TEXT_PRIMARY};font-size:0.95rem;line-height:1.5;margin-bottom:8px;"><strong>Status:</strong> {html.escape(bot['status_message'])}</p>
<p style="color:{TEXT_SECONDARY};font-size:0.88rem;margin-bottom:12px;">{html.escape(bot['why'][:200])}{'…' if len(bot['why']) > 200 else ''}</p>
<ul style="margin:0;padding-left:18px;font-size:0.85rem;">{block_list}</ul>
</div>
""")


def render_bot_logic_panel(bot: Dict[str, Any]) -> None:
    """Bot decision breakdown panel."""
    _html(f"""
<div class="mp-glass">
<div class="mp-card-title">Bot Logic Breakdown</div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">Technical Analysis</span><span style="color:{TEXT_PRIMARY}">{bot['technical_score']:.0f}/100</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">Momentum Score</span><span style="color:{TEXT_PRIMARY}">{bot['momentum_score']:.0f}/100</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">Volatility Score</span><span style="color:{TEXT_PRIMARY}">{bot['volatility_score']:.0f}/100</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">News Sentiment</span><span style="color:{TEXT_PRIMARY}">{html.escape(bot['news_sentiment'])}</span></div>
<div class="mp-stat-row"><span style="color:{TEXT_SECONDARY}">Risk Engine</span><span style="color:{TEXT_PRIMARY}">{html.escape(bot['risk_decision'])}</span></div>
<div class="mp-stat-row" style="border:none;"><span style="color:{ACCENT_CHERRY};font-weight:700;">Final Decision</span><span style="color:{TEXT_PRIMARY};font-weight:600;">{html.escape(bot['final_decision'])}</span></div>
</div>
""")
