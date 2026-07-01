"""Watchlist manager — scans and ranks symbols by AI opportunity score."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from config import DEFAULT_CRYPTO_SYMBOLS, DEFAULT_FOREX_SYMBOLS, DEFAULT_FUTURES_SYMBOLS, DEFAULT_STOCK_SYMBOLS
from data.futures_data import fetch_futures_bars
from data.market_data import fetch_ohlcv
from features.feature_engineering import add_features
from services.indicators import compute_institutional_indicators
from services.multitimeframe import analyze_multitimeframe
from services.news import fetch_and_analyze_news
from services.regime import detect_regime
from strategies.vwap_momentum import VWAPMomentumStrategy


@dataclass
class WatchlistEntry:
    symbol: str
    asset_class: str
    opportunity_score: float
    direction: str
    regime: str
    news_sentiment: str
    summary: str


def _score_symbol(symbol: str, asset_class: str) -> Optional[WatchlistEntry]:
    try:
        if symbol in DEFAULT_FUTURES_SYMBOLS:
            df = fetch_futures_bars(symbol)
        else:
            df, _ = fetch_ohlcv(symbol, period="6mo", interval="1d")
        if df.empty:
            return None
        df = compute_institutional_indicators(add_features(df))
        regime = detect_regime(df)
        strat = VWAPMomentumStrategy()
        sig = strat.evaluate(df, symbol)
        mtf = analyze_multitimeframe(symbol, ["1h", "1d"])
        news = fetch_and_analyze_news(symbol, limit=5)

        score = 0.0
        if sig.setup_detected:
            score += 30
        score += mtf.alignment_score / 3
        score += news.sentiment_score * 15
        if regime.regime == "bull_trend":
            score += 15
        score += min(20, sig.reward_risk * 5)

        direction = sig.direction if sig.setup_detected else mtf.dominant_trend.upper()[:4] or "HOLD"
        if direction == "BULL":
            direction = "BUY"
        elif direction == "BEAR":
            direction = "SELL"

        return WatchlistEntry(
            symbol=symbol, asset_class=asset_class, opportunity_score=round(score, 1),
            direction=direction, regime=regime.regime, news_sentiment=news.overall_sentiment,
            summary=f"Score {score:.0f} — {regime.regime}, {news.overall_sentiment} news",
        )
    except Exception:
        return None


def scan_watchlist(symbols: Optional[List[str]] = None, limit: int = 20) -> List[WatchlistEntry]:
    if symbols:
        pool = [(s, "stock") for s in symbols]
    else:
        pool = (
            [(s, "stock") for s in DEFAULT_STOCK_SYMBOLS]
            + [(s, "futures") for s in DEFAULT_FUTURES_SYMBOLS]
            + [(s, "forex") for s in DEFAULT_FOREX_SYMBOLS]
            + [(s, "crypto") for s in DEFAULT_CRYPTO_SYMBOLS]
        )
    results = []
    for sym, ac in pool:
        entry = _score_symbol(sym, ac)
        if entry:
            results.append(entry)
    results.sort(key=lambda e: e.opportunity_score, reverse=True)
    return results[:limit]
