"""
MarketPilot AI — Premium Stock Analysis & Paper Trading Dashboard

Run with:  streamlit run app.py
Frontend-only redesign. All backend logic unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from backtest import buy_hold_equity_curve, run_backtest
from config import (
    MAX_DAILY_LOSS_USD,
    MAX_POSITION_SIZE_USD,
    MIN_CONFIDENCE_TO_TRADE,
    REAL_TRADING_ENABLED,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    VALID_INTERVALS,
    VALID_PERIODS,
)
from data import fetch_ohlcv, validate_ticker
from indicators import add_indicators, get_indicator_summary, get_trend_interpretation
from paper_trader import PaperTrader
from strategy import compute_score_breakdown, generate_signal
from ui.charts import (
    bollinger_chart,
    equity_curve_chart,
    fear_greed_gauge,
    macd_chart,
    main_trading_chart,
    radar_chart,
    rsi_chart,
    sentiment_gauge,
    sparkline,
)
from ui.bot import build_bot_state
from ui.components import (
    render_ai_analysis_panel,
    render_bot_command_center,
    render_bot_logic_panel,
    render_calendar_placeholder,
    render_disclaimer,
    render_earnings_placeholder,
    render_empty_state,
    render_key_levels,
    render_metric_cards,
    render_news_feed,
    render_paper_account_card,
    render_sidebar_branding,
    render_signal_card_premium,
    render_ticker_header,
    render_top_bar,
)
from ui.display import (
    WATCHLIST,
    build_ai_analysis,
    compute_key_levels,
    compute_sentiment,
    fetch_news,
    get_stock_info,
    watchlist_snapshot,
)
from ui.session import (
    KEY_BOT_ACTIVE,
    KEY_LAST_SCAN,
    KEY_PAGE,
    KEY_TRADE_LOG,
    init_session_state,
    interval_index,
    period_index,
    set_page,
    set_period,
    set_ticker,
    sync_interval_from_widget,
    sync_period_from_widget,
    sync_ticker_from_input,
)
from ui.theme import inject_custom_css

# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("marketpilot")

PAGES = [
    "Overview", "AI Trading Bot", "Technicals", "Backtest",
    "Paper Trading", "Trade Log", "Settings",
]
RANGE_MAP = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y", "ALL": "5y"}
NAV_ICONS = {
    "Overview": "◉", "AI Trading Bot": "🤖", "Technicals": "📊", "Backtest": "🔬",
    "Paper Trading": "💼", "Trade Log": "📋", "Settings": "⚙️",
}

# ---------------------------------------------------------------------------
st.set_page_config(page_title="MarketPilot AI", page_icon="◆", layout="wide", initial_sidebar_state="expanded")
st.markdown(inject_custom_css(), unsafe_allow_html=True)

# Initialize canonical session keys BEFORE any widgets
init_session_state()


@st.cache_resource
def get_trader() -> PaperTrader:
    logger.info("Initializing PaperTrader...")
    return PaperTrader()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_watchlist() -> List[Dict[str, Any]]:
    items = []
    for ticker, name in WATCHLIST:
        snap = watchlist_snapshot(ticker)
        if snap:
            items.append(snap)
        else:
            items.append({"ticker": ticker, "name": name, "price": 0, "change_pct": 0})
    return items


@st.cache_data(ttl=120, show_spinner=False)
def _cached_news(ticker: str) -> List[Dict[str, Any]]:
    return fetch_news(ticker)


# ---------------------------------------------------------------------------
# SIDEBAR — Fixed navigation
# ---------------------------------------------------------------------------
render_sidebar_branding()

st.sidebar.markdown('<div class="mp-nav-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("**Navigation**")

for page in PAGES:
    icon = NAV_ICONS.get(page, "•")
    if st.sidebar.button(f"{icon}  {page}", key=f"nav_{page}", use_container_width=True):
        set_page(page)
        st.rerun()

st.sidebar.markdown('<div class="mp-nav-divider"></div>', unsafe_allow_html=True)

# Watchlist quick-select
wl_items = _cached_watchlist()
for item in wl_items:
    label = f"{item['ticker']}  ${item.get('price', 0):,.0f}  ({item.get('change_pct', 0):+.1f}%)"
    if st.sidebar.button(label, key=f"wl_{item['ticker']}", use_container_width=True):
        set_ticker(item["ticker"])
        set_page("Overview")
        st.rerun()

trader = get_trader()
account_status = None
if trader.is_connected:
    try:
        account_status = trader.get_account_status()
    except Exception as exc:
        logger.warning("Account status: %s", exc)

render_paper_account_card(account_status)

if st.sidebar.button("View Paper Trading →", key="nav_paper_trading", use_container_width=True, type="primary"):
    set_page("Paper Trading")
    st.rerun()

st.sidebar.markdown('<div class="mp-nav-divider"></div>', unsafe_allow_html=True)

# Ticker / period / interval — canonical keys only (no widget keys)
ticker_raw = st.sidebar.text_input("Ticker", value=st.session_state.selected_ticker)
ticker_input = sync_ticker_from_input(ticker_raw)

period = sync_period_from_widget(
    st.sidebar.selectbox("Period", VALID_PERIODS, index=period_index())
)
interval = sync_interval_from_widget(
    st.sidebar.selectbox("Interval", VALID_INTERVALS, index=interval_index())
)
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10_000, min_value=100, step=500)
min_confidence_bt = st.sidebar.slider("Min Confidence", 0, 100, 50, key="bt_confidence")
trade_notional = st.sidebar.number_input(
    "Trade Size ($)", value=min(1000, int(MAX_POSITION_SIZE_USD)),
    min_value=100, max_value=int(MAX_POSITION_SIZE_USD), step=100,
)

if trader.is_connected:
    st.sidebar.success("● Alpaca Connected")
else:
    st.sidebar.error("○ Alpaca Disconnected")
    if trader.init_error:
        st.sidebar.caption(trader.init_error[:100])

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
render_disclaimer()

if REAL_TRADING_ENABLED:
    st.error("REAL_TRADING_ENABLED is True. Automated live orders remain blocked.")

# Validate ticker
try:
    validation = validate_ticker(ticker_input)
except Exception as exc:
    logger.exception("Validation failed")
    render_empty_state("Validation Error", str(exc))
    st.stop()

if not validation.is_valid:
    render_empty_state("Invalid Ticker", validation.warning or "Unknown error")
    st.stop()

# Load data
try:
    with st.spinner(""):
        df, data_warning = fetch_ohlcv(ticker_input, period=period, interval=interval)
except Exception as exc:
    logger.exception("Data fetch failed")
    render_empty_state("Data Error", str(exc))
    st.stop()

if data_warning:
    st.warning(data_warning)
if df.empty:
    render_empty_state("No Data", "Try a different ticker or period.")
    st.stop()

try:
    with st.spinner(""):
        df = add_indicators(df)
except Exception as exc:
    logger.exception("Indicators failed")
    render_empty_state("Indicator Error", str(exc))
    st.stop()

# Compute signals & backtest (backend unchanged)
signal = generate_signal(df)
scores = compute_score_breakdown(df)
score_dict = scores.as_dict()

current_price = float(df["Close"].iloc[-1])
prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else current_price
daily_change = current_price - prev_price
daily_change_pct = (daily_change / prev_price * 100) if prev_price else 0.0

market_open = False
if trader.is_connected:
    try:
        market_open = trader.is_market_open()
    except Exception as exc:
        logger.warning("Market clock: %s", exc)

try:
    with st.spinner(""):
        bt = run_backtest(df, initial_capital=initial_capital, min_confidence=min_confidence_bt)
except Exception as exc:
    logger.exception("Backtest failed")
    render_empty_state("Backtest Error", str(exc))
    st.stop()

# Display helpers
stock_info = get_stock_info(ticker_input)
company = validation.name or stock_info.get("name", ticker_input)
ai_analysis = build_ai_analysis(signal, score_dict, current_price)
key_levels = compute_key_levels(df)
sentiment = compute_sentiment(signal.action, signal.confidence, score_dict)
news = _cached_news(ticker_input)

# Record scan time for bot display
st.session_state[KEY_LAST_SCAN] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

bot_state = build_bot_state(
    ticker=ticker_input,
    signal=signal,
    scores=score_dict,
    ai_analysis=ai_analysis,
    news=news,
    market_open=market_open,
    trader_connected=trader.is_connected,
    bot_active=st.session_state.get(KEY_BOT_ACTIVE, True),
    last_scan=st.session_state.get(KEY_LAST_SCAN, ""),
)


def _execute_paper_trade() -> None:
    """Shared paper trade execution used by Paper Trading and AI Bot tabs."""
    with st.spinner("Submitting order..."):
        try:
            result = trader.execute_signal(ticker_input, signal, notional=trade_notional)
        except Exception as exc:
            logger.exception("Trade failed")
            st.error(str(exc))
            return
    if result.success:
        st.success(result.message)
        st.session_state[KEY_TRADE_LOG].append({
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": result.symbol or ticker_input,
            "side": result.side or signal.action,
            "qty": result.qty,
            "notional": trade_notional,
            "confidence": signal.confidence,
            "signal_reason": "; ".join(signal.reasons[:3]),
            "status": "submitted",
        })
    else:
        st.error(result.message)

# Top bar (after market status known)
render_top_bar(market_open=market_open, paper_mode=not REAL_TRADING_ENABLED)

# ---------------------------------------------------------------------------
# Header row
# ---------------------------------------------------------------------------
render_ticker_header(ticker_input, company, stock_info.get("sector", "—"), stock_info.get("industry", "—"))

hdr1, hdr2 = st.columns([4, 1])
with hdr1:
    st.caption(f"{len(df)} bars · {period} · {interval}")
with hdr2:
    if st.button("⚡ Analyze", key="btn_analyze", type="primary", use_container_width=True):
        set_page("Overview")
        st.rerun()

# Range selector — updates canonical selected_period (not a widget key)
range_cols = st.columns(len(RANGE_MAP))
for i, (label, mapped) in enumerate(RANGE_MAP.items()):
    if range_cols[i].button(label, key=f"range_{label}", use_container_width=True):
        set_period(mapped)
        st.rerun()

# Metric cards + optional sparkline row
render_metric_cards(
    current_price, daily_change_pct, daily_change,
    signal.action, signal.confidence, signal.risk_level, market_open,
)
try:
    st.plotly_chart(sparkline(df["Close"].tail(30)), use_container_width=True, config={"displayModeBar": False})
except Exception:
    pass

active = st.session_state[KEY_PAGE]

# ===================================================================
# OVERVIEW
# ===================================================================
if active == "Overview":
    render_bot_command_center(bot_state)

    bot_nav_col1, bot_nav_col2 = st.columns([3, 1])
    with bot_nav_col2:
        if st.button("Open Full Bot Dashboard →", key="goto_bot", use_container_width=True):
            set_page("AI Trading Bot")
            st.rerun()

    main_col, side_col = st.columns([2.4, 1])

    with main_col:
        try:
            st.plotly_chart(main_trading_chart(df, ticker_input), use_container_width=True)
        except Exception as exc:
            logger.exception("Chart error")
            st.error(f"Chart error: {exc}")

    with side_col:
        render_signal_card_premium(signal.action, signal.confidence, signal.risk_level, signal.explanation)
        try:
            st.plotly_chart(radar_chart(score_dict), use_container_width=True, config={"displayModeBar": False})
        except Exception as exc:
            st.error(f"Radar chart: {exc}")
        with st.expander("Signal Details"):
            for r in signal.reasons:
                st.markdown(f"- {r}")

    # Lower grid
    g1, g2, g3 = st.columns(3)
    with g1:
        render_ai_analysis_panel(ai_analysis)
    with g2:
        render_key_levels(key_levels, current_price)
        try:
            st.plotly_chart(sentiment_gauge(sentiment["bullish_pct"]), use_container_width=True, config={"displayModeBar": False})
        except Exception:
            pass
    with g3:
        render_news_feed(news)
        render_earnings_placeholder(ticker_input)

    g4, g5 = st.columns(2)
    with g4:
        try:
            st.plotly_chart(fear_greed_gauge(sentiment["fear_greed"]), use_container_width=True, config={"displayModeBar": False})
        except Exception:
            pass
    with g5:
        render_calendar_placeholder()

# ===================================================================
# AI TRADING BOT
# ===================================================================
elif active == "AI Trading Bot":
    render_bot_command_center(bot_state)

    st.markdown("---")
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    b1.metric("Bot Status", bot_state["status"])
    b2.metric("Mode", "Paper Only")
    b3.metric("Ticker", bot_state["ticker"])
    b4.metric("Signal", bot_state["signal"])
    b5.metric("Confidence", f"{bot_state['confidence']}%")
    b6.metric("Risk", bot_state["risk"])

    st.info(bot_state["status_message"])

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("#### Why the bot chose this action")
        st.markdown(bot_state["why"])
        if bot_state["reasons"]:
            with st.expander("Full signal reasoning", expanded=True):
                for r in bot_state["reasons"]:
                    st.markdown(f"- {r}")

        st.markdown("#### Trade blocked reasons")
        if bot_state["block_reasons"]:
            for reason in bot_state["block_reasons"]:
                st.warning(reason)
        else:
            st.success("No blockers — paper trade is eligible.")

        render_bot_logic_panel(bot_state)

    with right:
        st.markdown("#### Suggested action")
        st.markdown(f"**{bot_state['suggested_action']}**")
        if bot_state.get("entry"):
            st.markdown(f"- Entry: **${bot_state['entry']:,.2f}**")
            st.markdown(f"- Stop loss: **${bot_state['stop_loss']:,.2f}**")
            st.markdown(f"- Take profit: **${bot_state['take_profit']:,.2f}**")

        st.markdown(f"**Last scan:** {bot_state['last_scan']}")

        bot_active = st.session_state.get(KEY_BOT_ACTIVE, True)
        if st.toggle("Bot Active", value=bot_active, key="bot_active_toggle") != bot_active:
            st.session_state[KEY_BOT_ACTIVE] = st.session_state["bot_active_toggle"]
            st.rerun()

        scan_col, _ = st.columns(2)
        with scan_col:
            if st.button("🔄 Run Next Scan", key="bot_rescan", use_container_width=True):
                st.session_state[KEY_LAST_SCAN] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()

        st.markdown("#### Safety checklist")
        confirm = st.checkbox(
            "Paper trade only — simulated money, not real cash",
            key="bot_trade_confirm",
        )
        st.checkbox("I understand this is educational, not financial advice", key="bot_edu_confirm")
        st.checkbox("I accept the current signal and risk level", key="bot_risk_confirm")

        all_checks = confirm and st.session_state.get("bot_edu_confirm") and st.session_state.get("bot_risk_confirm")
        trade_ok = bot_state["can_trade"] and all_checks and trader.is_connected

        if st.button(
            f"Execute Paper {signal.action} — ${trade_notional:,.0f}",
            type="primary",
            disabled=not trade_ok,
            key="bot_execute_trade",
            use_container_width=True,
        ):
            _execute_paper_trade()

        if not trader.is_connected:
            st.caption("Connect Alpaca paper keys in .env to enable trading.")
        elif not market_open:
            st.caption("Bot is watching only. Trading blocked because market is closed.")
        elif signal.action == "HOLD":
            st.caption("Bot recommends no trade right now.")
        elif signal.confidence < MIN_CONFIDENCE_TO_TRADE:
            st.caption("Bot is waiting for a stronger setup.")

# ===================================================================
# TECHNICALS
# ===================================================================
elif active == "Technicals":
    t1, t2 = st.columns(2)
    with t1:
        try:
            st.plotly_chart(rsi_chart(df, ticker_input), use_container_width=True)
        except Exception as exc:
            st.error(str(exc))
    with t2:
        try:
            st.plotly_chart(macd_chart(df, ticker_input), use_container_width=True)
        except Exception as exc:
            st.error(str(exc))

    try:
        st.plotly_chart(bollinger_chart(df, ticker_input), use_container_width=True)
    except Exception as exc:
        st.error(str(exc))

    st.markdown("#### Indicator Values")
    summary = get_indicator_summary(df)
    if summary:
        st.dataframe(
            pd.DataFrame([{"Indicator": k, "Value": f"{v:,.4f}" if abs(v) < 1000 else f"{v:,.2f}"} for k, v in summary.items()]),
            use_container_width=True, hide_index=True,
        )

    st.markdown("#### Trend Interpretation")
    st.info(get_trend_interpretation(df))

# ===================================================================
# BACKTEST
# ===================================================================
elif active == "Backtest":
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    b1.metric("Strategy Return", f"{bt.total_return_pct:+.2f}%")
    b2.metric("Buy & Hold", f"{bt.buy_hold_return_pct:+.2f}%")
    b3.metric("Alpha", f"{bt.alpha_pct:+.2f}%")
    b4.metric("Win Rate", f"{bt.win_rate_pct:.1f}%")
    b5.metric("Max Drawdown", f"{bt.max_drawdown_pct:.2f}%")
    b6.metric("Final Equity", f"${bt.final_equity:,.2f}")

    b7, b8 = st.columns(2)
    b7.metric("Total Trades", bt.num_trades)
    b8.metric("Wins / Losses", f"{bt.num_wins} / {bt.num_losses}")

    if bt.num_trades < 30:
        st.warning(f"Only **{bt.num_trades}** trades — results may not be statistically meaningful. Try period **5y**.")

    st.caption(f"Min confidence: {min_confidence_bt}%. Includes transaction costs and slippage.")

    if not bt.equity_curve.empty:
        try:
            st.plotly_chart(equity_curve_chart(bt.equity_curve, buy_hold_equity_curve(df, initial_capital)), use_container_width=True)
        except Exception as exc:
            st.error(str(exc))

    if not bt.trades.empty:
        st.markdown("#### Trade Log")
        st.dataframe(bt.trades, use_container_width=True, hide_index=True)

# ===================================================================
# PAPER TRADING
# ===================================================================
elif active == "Paper Trading":
    if not trader.is_connected:
        render_empty_state(
            "Alpaca Not Connected",
            trader.init_error or "Add paper API keys to .env and restart.",
        )
    else:
        try:
            status = trader.get_account_status()
        except Exception as exc:
            st.error(str(exc))
            status = None

        if status:
            p1, p2, p3, p4, p5 = st.columns(5)
            p1.metric("Mode", status.mode)
            p2.metric("Equity", f"${status.equity:,.2f}")
            p3.metric("Cash", f"${status.cash:,.2f}")
            p4.metric("Buying Power", f"${status.buying_power:,.2f}")
            p5.metric("Daily P&L", f"${status.daily_pnl:+,.2f}")

            try:
                for r in trader.check_stop_loss_take_profit():
                    if r.success:
                        st.warning(r.message)
            except Exception as exc:
                logger.warning("SL/TP: %s", exc)

        st.markdown("---")
        st.markdown("#### Execute Paper Trade")

        confirm = st.checkbox(
            "I confirm this is a **paper trade** (simulated money) and I understand the risks.",
            key="trade_confirm",
        )

        if signal.action == "HOLD":
            st.caption("Signal is HOLD — trade will be blocked.")
        if signal.confidence < MIN_CONFIDENCE_TO_TRADE:
            st.caption(f"Confidence {signal.confidence}% below threshold ({MIN_CONFIDENCE_TO_TRADE}%).")
        if not market_open:
            st.caption("Market is closed — trade will be blocked.")

        if st.button(
            f"Execute Paper {signal.action} — ${trade_notional:,.0f}",
            type="primary", disabled=not confirm, key="execute_paper_trade",
        ):
            _execute_paper_trade()

        st.markdown("#### Open Positions")
        try:
            positions = trader.get_positions()
            st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True) if positions else st.write("No open positions.")
        except Exception as exc:
            st.error(str(exc))

        st.markdown("#### Recent Orders")
        try:
            history = trader.get_trade_history(limit=20)
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True) if history else st.write("No recent orders.")
        except Exception as exc:
            st.error(str(exc))

# ===================================================================
# TRADE LOG
# ===================================================================
elif active == "Trade Log":
    log_frames = []

    if not bt.trades.empty:
        bt_log = bt.trades.copy()
        bt_log["source"] = "Backtest"
        bt_log["datetime"] = bt_log["exit_date"].astype(str)
        log_frames.append(bt_log)

    if st.session_state[KEY_TRADE_LOG]:
        pdf = pd.DataFrame(st.session_state[KEY_TRADE_LOG])
        pdf["source"] = "Paper (session)"
        log_frames.append(pdf)

    if trader.is_connected:
        try:
            ah = trader.get_trade_history(limit=100)
            if ah:
                adf = pd.DataFrame(ah)
                adf["source"] = "Alpaca"
                adf["datetime"] = adf.get("filled_at", adf.get("submitted_at", ""))
                log_frames.append(adf)
        except Exception as exc:
            logger.warning("History: %s", exc)

    if log_frames:
        combined = pd.concat(log_frames, ignore_index=True, sort=False)
        st.dataframe(combined, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Export CSV",
            combined.to_csv(index=False).encode("utf-8"),
            file_name=f"marketpilot_{ticker_input}_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
            type="primary",
            key="export_csv",
        )
    else:
        render_empty_state("No Trades Yet", "Run a backtest or execute a paper trade.")

# ===================================================================
# SETTINGS
# ===================================================================
elif active == "Settings":
    st.markdown("#### API Status")
    if trader.is_connected:
        st.success(f"Connected — {trader.get_account_status().message}")
    else:
        st.error(trader.init_error or "Not connected.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Risk Settings")
        st.markdown(f"- Max trade size: **${MAX_POSITION_SIZE_USD:,.0f}**")
        st.markdown(f"- Max daily loss: **${MAX_DAILY_LOSS_USD:,.0f}**")
        st.markdown(f"- Min confidence: **{MIN_CONFIDENCE_TO_TRADE}%**")
    with c2:
        st.markdown("#### Trade Limits")
        st.markdown(f"- Stop loss: **{STOP_LOSS_PCT * 100:.0f}%**")
        st.markdown(f"- Take profit: **{TAKE_PROFIT_PCT * 100:.0f}%**")
        st.markdown(f"- Real trading: **{'ENABLED ⚠️' if REAL_TRADING_ENABLED else 'Disabled (paper only)'}**")

    st.warning("Paper trading by default. No real money unless REAL_TRADING_ENABLED=true (automated orders still blocked).")
    st.markdown(f"- Ticker: **{ticker_input}** · Period: **{period}** · Bars: **{len(df)}**")

# Footer
st.markdown("---")
st.caption("MarketPilot AI — Educational tool. Not financial advice.")
