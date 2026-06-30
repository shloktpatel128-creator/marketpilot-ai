"""
AI Trading Bot display logic — frontend only, uses existing backend signals.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from config import MIN_CONFIDENCE_TO_TRADE, REAL_TRADING_ENABLED


def _news_sentiment_label(news: List[Dict[str, Any]]) -> str:
    if not news:
        return "No recent news data"
    bullish = sum(1 for n in news if n.get("sentiment") == "bullish")
    bearish = sum(1 for n in news if n.get("sentiment") == "bearish")
    if bullish > bearish:
        return f"News leaning bullish ({bullish} positive headlines)"
    if bearish > bullish:
        return f"News leaning bearish ({bearish} negative headlines)"
    return "News sentiment neutral"


def get_trade_block_reasons(
    signal_action: str,
    confidence: int,
    market_open: bool,
    trader_connected: bool,
    bot_active: bool = True,
    min_confidence: int = MIN_CONFIDENCE_TO_TRADE,
) -> List[str]:
    """Return human-readable reasons why a trade would be blocked."""
    reasons: List[str] = []
    if not bot_active:
        reasons.append("Bot is paused.")
    if REAL_TRADING_ENABLED:
        reasons.append("Real trading flag is enabled — automated orders blocked for safety.")
    if not trader_connected:
        reasons.append("Alpaca paper account not connected.")
    if not market_open:
        reasons.append("Market is closed.")
    if signal_action == "HOLD":
        reasons.append("Signal is HOLD — no directional trade recommended.")
    if confidence < min_confidence:
        reasons.append(f"Confidence {confidence}% is below minimum threshold ({min_confidence}%).")
    return reasons


def get_bot_status_message(
    signal_action: str,
    confidence: int,
    market_open: bool,
    block_reasons: List[str],
) -> str:
    """Primary bot status line for the UI."""
    if not market_open:
        return "Bot is watching only. Trading blocked because market is closed."
    if signal_action == "HOLD":
        return "Bot recommends no trade right now."
    if confidence < MIN_CONFIDENCE_TO_TRADE:
        return "Bot is waiting for a stronger setup."
    if block_reasons:
        return "Bot has a signal but trade is blocked — see checklist below."
    return f"Bot is ready to execute a paper {signal_action} trade."


def build_bot_state(
    *,
    ticker: str,
    signal,
    scores: Dict[str, float],
    ai_analysis: Dict[str, Any],
    news: List[Dict[str, Any]],
    market_open: bool,
    trader_connected: bool,
    bot_active: bool,
    last_scan: Optional[str],
) -> Dict[str, Any]:
    """Assemble all bot display fields for UI components."""
    block_reasons = get_trade_block_reasons(
        signal.action, signal.confidence, market_open, trader_connected, bot_active,
    )
    can_trade = len(block_reasons) == 0 and bot_active

    risk_decision = (
        f"Risk engine: {signal.risk_level} risk"
        f" (Risk score {scores.get('Risk Score', 0):.0f}/100)."
    )
    if signal.risk_level == "High":
        risk_decision += " Elevated caution advised."

    final_decision = f"FINAL: {signal.action} with {signal.confidence}% confidence"
    if can_trade:
        final_decision += " — paper trade eligible."
    else:
        final_decision += " — no trade at this time."

    return {
        "status": "Active" if bot_active else "Paused",
        "mode": "Paper Trading only",
        "ticker": ticker,
        "signal": signal.action,
        "confidence": signal.confidence,
        "risk": signal.risk_level,
        "suggested_action": signal.action if signal.action != "HOLD" else "Wait — no trade",
        "why": signal.explanation,
        "reasons": signal.reasons or [],
        "block_reasons": block_reasons,
        "status_message": get_bot_status_message(
            signal.action, signal.confidence, market_open, block_reasons,
        ),
        "can_trade": can_trade,
        "last_scan": last_scan or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "technical_score": scores.get("Technical Score", 0),
        "momentum_score": scores.get("Momentum Score", 0),
        "volatility_score": scores.get("Volatility Score", 0),
        "overall_score": scores.get("Overall Score", 0),
        "news_sentiment": _news_sentiment_label(news),
        "risk_decision": risk_decision,
        "final_decision": final_decision,
        "entry": ai_analysis.get("entry"),
        "stop_loss": ai_analysis.get("stop_loss"),
        "take_profit": ai_analysis.get("take_profit"),
        "bullish_factors": ai_analysis.get("bullish_factors", []),
        "bearish_factors": ai_analysis.get("bearish_factors", []),
    }
