"""News fetching and sentiment analysis."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yfinance as yf

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

BULLISH_WORDS = {
    "surge", "rally", "beat", "upgrade", "growth", "record", "profit", "bullish",
    "outperform", "strong", "gain", "soar", "jump", "positive", "buy", "breakout",
}
BEARISH_WORDS = {
    "fall", "drop", "miss", "downgrade", "loss", "bearish", "weak", "decline",
    "cut", "warning", "lawsuit", "investigation", "sell", "crash", "plunge", "negative",
}


@dataclass
class NewsItem:
    title: str
    publisher: str
    sentiment: str  # bullish | bearish | neutral
    score: float  # -1 to 1
    link: str = ""


@dataclass
class NewsAnalysis:
    items: List[NewsItem] = field(default_factory=list)
    overall_sentiment: str = "neutral"
    sentiment_score: float = 0.0
    bullish_count: int = 0
    bearish_count: int = 0
    summary: str = ""


def _lexicon_sentiment(text: str) -> tuple:
    words = set(re.findall(r"[a-z]+", text.lower()))
    bull = len(words & BULLISH_WORDS)
    bear = len(words & BEARISH_WORDS)
    score = (bull - bear) / max(bull + bear, 1)
    if score > 0.15:
        return "bullish", score
    if score < -0.15:
        return "bearish", score
    return "neutral", score


def _openai_sentiment(text: str) -> Optional[tuple]:
    if not OPENAI_API_KEY:
        return None
    try:
        import urllib.request
        import json
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": f"Classify financial headline sentiment as bullish, bearish, or neutral. Return JSON {{\"sentiment\":\"...\",\"score\":-1to1,\"reason\":\"...\"}}. Headline: {text[:500]}",
            }],
            "max_tokens": 100,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content.strip().strip("`").replace("json\n", ""))
        return parsed.get("sentiment", "neutral"), float(parsed.get("score", 0))
    except Exception as exc:
        logger.debug("OpenAI sentiment failed: %s", exc)
        return None


def fetch_and_analyze_news(symbol: str, limit: int = 15) -> NewsAnalysis:
    result = NewsAnalysis()
    try:
        raw = yf.Ticker(symbol).news or []
    except Exception as exc:
        logger.warning("News fetch failed for %s: %s", symbol, exc)
        result.summary = "News unavailable"
        return result

    scores = []
    for item in raw[:limit]:
        content = item.get("content", item)
        title = content.get("title", item.get("title", ""))
        if not title:
            continue
        pub = content.get("provider", {}).get("displayName", item.get("publisher", "Unknown"))
        link = content.get("canonicalUrl", {}).get("url", item.get("link", ""))

        ai = _openai_sentiment(title)
        if ai:
            sentiment, score = ai
        else:
            sentiment, score = _lexicon_sentiment(title)

        result.items.append(NewsItem(title=title, publisher=pub, sentiment=sentiment, score=score, link=link))
        scores.append(score)
        if sentiment == "bullish":
            result.bullish_count += 1
        elif sentiment == "bearish":
            result.bearish_count += 1

    if scores:
        avg = sum(scores) / len(scores)
        result.sentiment_score = avg
        if avg > 0.1:
            result.overall_sentiment = "bullish"
        elif avg < -0.1:
            result.overall_sentiment = "bearish"
        else:
            result.overall_sentiment = "neutral"
        result.summary = (
            f"{len(result.items)} headlines — {result.overall_sentiment} "
            f"(score {avg:.2f}, {result.bullish_count}↑ {result.bearish_count}↓)"
        )
    else:
        result.summary = "No news headlines found"
    return result
