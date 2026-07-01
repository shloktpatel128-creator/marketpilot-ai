"""Weighted AI confidence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from services.macro import MacroAnalysis
from services.multitimeframe import MultiTimeframeResult
from services.news import NewsAnalysis
from services.regime import MarketRegime
from storage.schemas import ConfidenceResult


WEIGHTS = {
    "technical": 0.25,
    "multitimeframe": 0.15,
    "news": 0.15,
    "macro": 0.10,
    "momentum": 0.10,
    "regime": 0.10,
    "strategy_performance": 0.10,
    "agent_consensus": 0.05,
}

VERSION = "ai-weighted-v2"


@dataclass
class ConfidenceInputs:
    df: pd.DataFrame
    mtf: Optional[MultiTimeframeResult] = None
    news: Optional[NewsAnalysis] = None
    macro: Optional[MacroAnalysis] = None
    regime: Optional[MarketRegime] = None
    agent_scores: Optional[Dict[str, float]] = None
    strategy_win_rate: float = 50.0
    direction: str = "HOLD"


class ConfidenceEngine:
    """Combines technical, news, macro, MTF, regime, and agent signals."""

    def score(self, inputs: ConfidenceInputs) -> ConfidenceResult:
        if inputs.direction in ("HOLD", "NO_TRADE"):
            return ConfidenceResult(0, VERSION, "No actionable direction — confidence 0.")

        components = {}
        reasons = []

        # Technical score
        row = inputs.df.iloc[-1] if not inputs.df.empty else None
        tech = 50.0
        if row is not None:
            rsi = float(row.get("RSI", 50) or 50)
            adx = float(row.get("ADX", 20) or 20)
            macd_h = float(row.get("MACD_Hist", 0) or 0)
            if inputs.direction == "BUY":
                if 40 < rsi < 65:
                    tech += 15
                if macd_h > 0:
                    tech += 15
                if float(row.get("SuperTrend_Dir", 0) or 0) > 0:
                    tech += 10
            else:
                if 35 < rsi < 60:
                    tech += 15
                if macd_h < 0:
                    tech += 15
            if adx > 25:
                tech += 10
        components["technical"] = min(100, tech)
        reasons.append(f"Technical {components['technical']:.0f}")

        # MTF
        mtf_score = 50.0
        if inputs.mtf and inputs.mtf.analyses:
            mtf_score = 50 + inputs.mtf.alignment_score / 2
            if inputs.direction == "BUY" and inputs.mtf.dominant_trend == "bullish":
                mtf_score += 15
            elif inputs.direction == "SELL" and inputs.mtf.dominant_trend == "bearish":
                mtf_score += 15
        components["multitimeframe"] = min(100, max(0, mtf_score))
        reasons.append(f"MTF {components['multitimeframe']:.0f}")

        # News
        news_score = 50.0
        if inputs.news and inputs.news.items:
            news_score = 50 + inputs.news.sentiment_score * 40
            if inputs.direction == "BUY" and inputs.news.overall_sentiment == "bullish":
                news_score += 10
            elif inputs.direction == "SELL" and inputs.news.overall_sentiment == "bearish":
                news_score += 10
        components["news"] = min(100, max(0, news_score))
        reasons.append(f"News {components['news']:.0f}")

        # Macro (inverse — events reduce confidence)
        macro_score = 70.0
        if inputs.macro:
            macro_score -= inputs.macro.risk_adjustment
        components["macro"] = max(0, macro_score)
        reasons.append(f"Macro {components['macro']:.0f}")

        # Momentum
        mom_score = 50.0
        if row is not None:
            m10 = float(row.get("Momentum_10", 0) or 0)
            m20 = float(row.get("Momentum_20", 0) or 0)
            if inputs.direction == "BUY":
                mom_score += min(25, max(0, m10 * 5))
                mom_score += min(15, max(0, m20 * 3))
            else:
                mom_score += min(25, max(0, -m10 * 5))
        components["momentum"] = min(100, max(0, mom_score))

        # Regime alignment
        regime_score = 50.0
        if inputs.regime:
            if inputs.regime.regime in ("bull_trend",) and inputs.direction == "BUY":
                regime_score += 25
            elif inputs.regime.regime in ("bear_trend",) and inputs.direction == "SELL":
                regime_score += 25
            elif inputs.regime.regime == "high_volatility":
                regime_score -= 10
        components["regime"] = min(100, max(0, regime_score))

        # Strategy performance
        strat_score = min(100, max(20, inputs.strategy_win_rate))
        components["strategy_performance"] = strat_score

        # Agent consensus
        agent_score = 50.0
        if inputs.agent_scores:
            vals = list(inputs.agent_scores.values())
            agent_score = 50 + sum(vals) / len(vals) if vals else 50
        components["agent_consensus"] = min(100, max(0, agent_score))

        final = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
        final = min(100, max(0, final))

        expl = f"AI confidence {final:.0f}/100 — " + "; ".join(reasons[:5])
        return ConfidenceResult(final, VERSION, expl)
