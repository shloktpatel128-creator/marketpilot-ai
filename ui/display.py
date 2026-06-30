"""
Frontend-only display helpers (news, stock info, AI presentation).
Does NOT modify backend trading logic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT

logger = logging.getLogger(__name__)

WATCHLIST = [
    ("TSLA", "Tesla"),
    ("AAPL", "Apple"),
    ("NVDA", "Nvidia"),
    ("SPY", "S&P 500 ETF"),
]

COMPANY_NAMES = {
    "TSLA": "Tesla", "AAPL": "Apple", "NVDA": "Nvidia", "MSFT": "Microsoft",
    "GOOGL": "Google", "AMZN": "Amazon", "META": "Meta", "SPY": "S&P 500 ETF",
}


def get_stock_info(ticker: str) -> Dict[str, str]:
    """Fetch sector/industry from yfinance for display."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return {
            "sector": info.get("sector") or "—",
            "industry": info.get("industry") or "—",
            "name": info.get("shortName") or info.get("longName") or ticker,
        }
    except Exception as exc:
        logger.warning("Stock info fetch failed: %s", exc)
        return {"sector": "—", "industry": "—", "name": ticker}


def fetch_news(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch recent news headlines via yfinance."""
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
        items = []
        for article in raw[:limit]:
            content = article.get("content") or article
            title = content.get("title") or article.get("title", "No title")
            link = content.get("canonicalUrl", {}).get("url") or article.get("link", "#")
            pub = content.get("pubDate") or article.get("providerPublishTime")
            provider = (content.get("provider") or {}).get("displayName") or article.get("publisher", "Unknown")
            if isinstance(pub, (int, float)):
                pub_str = datetime.fromtimestamp(pub).strftime("%b %d, %H:%M")
            elif pub:
                pub_str = str(pub)[:16]
            else:
                pub_str = "Recent"
            sentiment = "neutral"
            title_lower = title.lower()
            if any(w in title_lower for w in ("surge", "gain", "beat", "record", "upgrade", "bull")):
                sentiment = "bullish"
            elif any(w in title_lower for w in ("fall", "drop", "miss", "cut", "downgrade", "bear", "loss")):
                sentiment = "bearish"
            items.append({
                "headline": title,
                "url": link,
                "source": provider,
                "time": pub_str,
                "sentiment": sentiment,
            })
        return items
    except Exception as exc:
        logger.warning("News fetch failed: %s", exc)
        return []


def compute_key_levels(df: pd.DataFrame) -> Dict[str, float]:
    """Support/resistance from indicators."""
    if df.empty:
        return {}
    row = df.iloc[-1]
    levels = {}
    if "BB_Lower" in df.columns and pd.notna(row.get("BB_Lower")):
        levels["Support (BB Lower)"] = float(row["BB_Lower"])
    if "SMA_50" in df.columns and pd.notna(row.get("SMA_50")):
        levels["Support (SMA 50)"] = float(row["SMA_50"])
    if "SMA_200" in df.columns and pd.notna(row.get("SMA_200")):
        levels["Major Support (SMA 200)"] = float(row["SMA_200"])
    if "BB_Upper" in df.columns and pd.notna(row.get("BB_Upper")):
        levels["Resistance (BB Upper)"] = float(row["BB_Upper"])
    if "SMA_20" in df.columns and pd.notna(row.get("SMA_20")):
        levels["Resistance (SMA 20)"] = float(row["SMA_20"])
    return levels


def compute_sentiment(signal_action: str, confidence: int, scores: Dict[str, float]) -> Dict[str, float]:
    """Derive bullish % and fear/greed from existing scores."""
    bullish = 50.0
    if signal_action == "BUY":
        bullish = min(95, 50 + confidence * 0.45)
    elif signal_action == "SELL":
        bullish = max(5, 50 - confidence * 0.45)
    else:
        bullish = 50 + (scores.get("Momentum Score", 50) - 50) * 0.3

    fear_greed = scores.get("Overall Score", 50)
    return {"bullish_pct": round(bullish, 1), "fear_greed": round(fear_greed, 1)}


def build_ai_analysis(
    signal,
    scores: Dict[str, float],
    current_price: float,
) -> Dict[str, Any]:
    """Build rich AI analysis panel from existing signal engine output."""
    reasons = signal.reasons or []
    bullish = [r for r in reasons if any(
        w in r.lower() for w in ("bullish", "above", "oversold", "positive", "uptrend", "bounce", "golden", "support")
    )][:5]
    bearish = [r for r in reasons if any(
        w in r.lower() for w in ("bearish", "below", "overbought", "negative", "downtrend", "death", "stretched", "weak")
    )][:5]

    if not bullish:
        bullish = [r for r in reasons if "+" in r or "above" in r.lower()][:3] or ["No strong bullish factors detected."]
    if not bearish:
        bearish = [r for r in reasons if "-" in r or "below" in r.lower()][:3] or ["No strong bearish factors detected."]

    if signal.action == "BUY":
        entry = current_price
        stop = current_price * (1 - STOP_LOSS_PCT)
        target = current_price * (1 + TAKE_PROFIT_PCT)
    elif signal.action == "SELL":
        entry = current_price
        stop = current_price * (1 + STOP_LOSS_PCT)
        target = current_price * (1 - TAKE_PROFIT_PCT)
    else:
        entry = current_price
        stop = current_price * (1 - STOP_LOSS_PCT)
        target = current_price * (1 + TAKE_PROFIT_PCT)

    risk_amount = abs(entry - stop)
    reward_amount = abs(target - entry)
    rr_ratio = round(reward_amount / risk_amount, 2) if risk_amount > 0 else 0.0

    return {
        "recommendation": f"AI recommends {signal.action}",
        "confidence": signal.confidence,
        "probability": min(99, signal.confidence + 5),
        "reasoning": signal.explanation,
        "bullish_factors": bullish,
        "bearish_factors": bearish,
        "risk_summary": f"Risk level: {signal.risk_level}. Volatility score: {scores.get('Volatility Score', 0):.0f}/100.",
        "entry": entry,
        "stop_loss": stop,
        "take_profit": target,
        "reward_risk": rr_ratio,
    }


def watchlist_snapshot(ticker: str, period: str = "5d") -> Optional[Dict[str, Any]]:
    """Quick price snapshot for watchlist sidebar."""
    try:
        from data import fetch_ohlcv
        df, _ = fetch_ohlcv(ticker, period="1mo", interval="1d")
        if df.empty or len(df) < 2:
            return None
        price = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])
        chg = (price / prev - 1) * 100
        return {
            "ticker": ticker,
            "name": COMPANY_NAMES.get(ticker, ticker),
            "price": price,
            "change_pct": chg,
        }
    except Exception:
        return None
