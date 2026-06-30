"""
Signal engine: combines technical indicators into BUY / SELL / HOLD signals
with confidence scores, plain-English explanations, and risk levels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import pandas as pd

from config import EMA_FAST, EMA_SLOW, RSI_OVERBOUGHT, RSI_OVERSOLD

SignalAction = Literal["BUY", "SELL", "HOLD"]
RiskLevel = Literal["Low", "Medium", "High"]


@dataclass
class ScoreBreakdown:
    """AI-style score breakdown for dashboard display."""

    technical: float
    momentum: float
    volatility: float
    risk: float
    overall: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "Technical Score": self.technical,
            "Momentum Score": self.momentum,
            "Volatility Score": self.volatility,
            "Risk Score": self.risk,
            "Overall Score": self.overall,
        }


@dataclass
class TradingSignal:
    """A single trading signal with metadata."""

    action: SignalAction
    confidence: int          # 0–100
    explanation: str
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    price: Optional[float] = None
    timestamp: Optional[pd.Timestamp] = None


def _score_ma_crossover(row: pd.Series, prev: pd.Series) -> tuple[int, List[str], SignalAction]:
    """Golden cross / death cross between SMA 20 and SMA 50."""
    score = 0
    reasons: List[str] = []
    bias: SignalAction = "HOLD"

    sma20 = row.get("SMA_20")
    sma50 = row.get("SMA_50")
    prev_sma20 = prev.get("SMA_20")
    prev_sma50 = prev.get("SMA_50")

    if pd.isna(sma20) or pd.isna(sma50) or pd.isna(prev_sma20) or pd.isna(prev_sma50):
        return score, reasons, bias

    if prev_sma20 <= prev_sma50 and sma20 > sma50:
        score += 25
        reasons.append("SMA 20 crossed above SMA 50 (bullish golden cross).")
        bias = "BUY"
    elif prev_sma20 >= prev_sma50 and sma20 < sma50:
        score -= 25
        reasons.append("SMA 20 crossed below SMA 50 (bearish death cross).")
        bias = "SELL"
    elif sma20 > sma50:
        score += 10
        reasons.append("SMA 20 is above SMA 50 (short-term uptrend).")
    else:
        score -= 10
        reasons.append("SMA 20 is below SMA 50 (short-term downtrend).")

    # Long-term trend via SMA 200
    sma200 = row.get("SMA_200")
    close = row.get("Close")
    if pd.notna(sma200) and pd.notna(close):
        if close > sma200:
            score += 10
            reasons.append("Price is above SMA 200 (long-term bullish).")
        else:
            score -= 10
            reasons.append("Price is below SMA 200 (long-term bearish).")

    return score, reasons, bias


def _score_rsi(row: pd.Series) -> tuple[int, List[str], SignalAction]:
    """RSI overbought / oversold conditions."""
    score = 0
    reasons: List[str] = []
    bias: SignalAction = "HOLD"

    rsi = row.get("RSI")
    if pd.isna(rsi):
        return score, reasons, bias

    if rsi <= RSI_OVERSOLD:
        score += 20
        reasons.append(f"RSI is {rsi:.1f} (oversold — potential bounce).")
        bias = "BUY"
    elif rsi >= RSI_OVERBOUGHT:
        score -= 20
        reasons.append(f"RSI is {rsi:.1f} (overbought — potential pullback).")
        bias = "SELL"
    elif rsi < 45:
        score += 5
        reasons.append(f"RSI is {rsi:.1f} (mildly bearish momentum).")
    elif rsi > 55:
        score += 5
        reasons.append(f"RSI is {rsi:.1f} (mildly bullish momentum).")
    else:
        reasons.append(f"RSI is {rsi:.1f} (neutral zone).")

    return score, reasons, bias


def _score_macd(row: pd.Series, prev: pd.Series) -> tuple[int, List[str], SignalAction]:
    """MACD line vs signal line crossover."""
    score = 0
    reasons: List[str] = []
    bias: SignalAction = "HOLD"

    macd = row.get("MACD")
    signal = row.get("MACD_Signal")
    hist = row.get("MACD_Hist")
    prev_macd = prev.get("MACD")
    prev_signal = prev.get("MACD_Signal")

    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]):
        return score, reasons, bias

    if prev_macd <= prev_signal and macd > signal:
        score += 20
        reasons.append("MACD crossed above signal line (bullish momentum).")
        bias = "BUY"
    elif prev_macd >= prev_signal and macd < signal:
        score -= 20
        reasons.append("MACD crossed below signal line (bearish momentum).")
        bias = "SELL"
    elif pd.notna(hist):
        if hist > 0:
            score += 8
            reasons.append("MACD histogram is positive (bullish momentum).")
        else:
            score -= 8
            reasons.append("MACD histogram is negative (bearish momentum).")

    return score, reasons, bias


def _score_volume(row: pd.Series) -> tuple[int, List[str]]:
    """Volume confirmation — above-average volume strengthens the signal."""
    score = 0
    reasons: List[str] = []

    vol_ratio = row.get("Volume_Ratio")
    if pd.isna(vol_ratio):
        return score, reasons

    if vol_ratio >= 1.5:
        score += 10
        reasons.append(f"Volume is {vol_ratio:.1f}x the 20-day average (strong confirmation).")
    elif vol_ratio >= 1.1:
        score += 5
        reasons.append(f"Volume is slightly above average ({vol_ratio:.1f}x).")
    elif vol_ratio < 0.7:
        score -= 5
        reasons.append(f"Volume is below average ({vol_ratio:.1f}x) — weak conviction.")

    return score, reasons


def _score_momentum(row: pd.Series) -> tuple[int, List[str]]:
    """10-bar price momentum."""
    score = 0
    reasons: List[str] = []

    mom = row.get("Momentum_10")
    if pd.isna(mom):
        return score, reasons

    if mom > 5:
        score += 10
        reasons.append(f"Strong 10-period momentum (+{mom:.1f}%).")
    elif mom > 0:
        score += 5
        reasons.append(f"Positive 10-period momentum (+{mom:.1f}%).")
    elif mom < -5:
        score -= 10
        reasons.append(f"Weak 10-period momentum ({mom:.1f}%).")
    elif mom < 0:
        score -= 5
        reasons.append(f"Negative 10-period momentum ({mom:.1f}%).")

    return score, reasons


def _score_trend(row: pd.Series) -> tuple[int, List[str]]:
    """EMA trend and Bollinger Band position."""
    score = 0
    reasons: List[str] = []

    ema_fast = row.get(f"EMA_{EMA_FAST}")
    ema_slow = row.get(f"EMA_{EMA_SLOW}")
    close = row.get("Close")

    if pd.notna(ema_fast) and pd.notna(ema_slow):
        if ema_fast > ema_slow:
            score += 8
            reasons.append(f"EMA {EMA_FAST} is above EMA {EMA_SLOW} (uptrend).")
        else:
            score -= 8
            reasons.append(f"EMA {EMA_FAST} is below EMA {EMA_SLOW} (downtrend).")

    bb_upper = row.get("BB_Upper")
    bb_lower = row.get("BB_Lower")
    if pd.notna(close) and pd.notna(bb_upper) and pd.notna(bb_lower):
        if close >= bb_upper:
            score -= 8
            reasons.append("Price at or above upper Bollinger Band (stretched).")
        elif close <= bb_lower:
            score += 8
            reasons.append("Price at or below lower Bollinger Band (potential support).")

    return score, reasons


def _determine_risk(row: pd.Series, action: SignalAction) -> RiskLevel:
    """Estimate risk based on volatility proxy and signal type."""
    rsi = row.get("RSI", 50)
    mom = abs(row.get("Momentum_10", 0) or 0)
    vol_ratio = row.get("Volume_Ratio", 1) or 1

    risk_points = 0
    if pd.notna(rsi) and (rsi > 75 or rsi < 25):
        risk_points += 2
    if mom > 10:
        risk_points += 2
    if vol_ratio > 2:
        risk_points += 1
    if action == "HOLD":
        risk_points = max(0, risk_points - 1)

    if risk_points >= 4:
        return "High"
    if risk_points >= 2:
        return "Medium"
    return "Low"


def generate_signal(df: pd.DataFrame, bar_index: int = -1) -> TradingSignal:
    """
    Generate a trading signal for a specific bar (default: latest).

    Combines MA crossover, RSI, MACD, volume, momentum, and trend.
    """
    if df is None or len(df) < 2:
        return TradingSignal(
            action="HOLD",
            confidence=0,
            explanation="Not enough data to generate a signal.",
            risk_level="High",
            reasons=["Insufficient historical data."],
        )

    idx = bar_index if bar_index >= 0 else len(df) + bar_index
    if idx < 1 or idx >= len(df):
        idx = len(df) - 1

    row = df.iloc[idx]
    prev = df.iloc[idx - 1]

    total_score = 0
    all_reasons: List[str] = []
    biases: List[SignalAction] = []

    for scorer in (_score_ma_crossover, _score_rsi, _score_macd):
        if scorer == _score_ma_crossover or scorer == _score_macd:
            s, r, b = scorer(row, prev)
        else:
            s, r, b = scorer(row)  # type: ignore[misc]
        total_score += s
        all_reasons.extend(r)
        if b != "HOLD":
            biases.append(b)

    for scorer in (_score_volume, _score_momentum, _score_trend):
        s, r = scorer(row)
        total_score += s
        all_reasons.extend(r)

    # Map composite score to action
    if total_score >= 20:
        action: SignalAction = "BUY"
    elif total_score <= -20:
        action = "SELL"
    else:
        action = "HOLD"

    # Confidence: scale |score| to 0–100, capped
    confidence = min(100, max(0, int(50 + total_score * 1.2)))

    if action == "HOLD":
        confidence = min(confidence, 55)

    risk = _determine_risk(row, action)

    # Build plain-English summary
    price = float(row["Close"]) if pd.notna(row.get("Close")) else None
    ts = df.index[idx] if hasattr(df.index, "__getitem__") else None

    action_phrase = {
        "BUY": "a potential buying opportunity",
        "SELL": "a potential selling opportunity",
        "HOLD": "staying on the sidelines",
    }[action]

    explanation = (
        f"The combined technical analysis suggests {action_phrase} "
        f"with {confidence}% confidence. "
        f"Risk level is assessed as {risk}. "
        f"Key factors: {'; '.join(all_reasons[:4])}."
    )

    return TradingSignal(
        action=action,
        confidence=confidence,
        explanation=explanation,
        risk_level=risk,
        reasons=all_reasons,
        price=price,
        timestamp=ts,
    )


def generate_signals_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate signals for every bar in the DataFrame (for backtesting).

    Returns DataFrame with columns: signal, confidence, score.
    """
    signals = []
    confidences = []

    for i in range(1, len(df)):
        sig = generate_signal(df, bar_index=i)
        signals.append(sig.action)
        confidences.append(sig.confidence)

    # Pad first row
    result = pd.DataFrame(index=df.index)
    result["signal"] = ["HOLD"] + signals
    result["confidence"] = [0] + confidences
    return result


def compute_score_breakdown(df: pd.DataFrame, bar_index: int = -1) -> ScoreBreakdown:
    """
    Compute category scores (0–100) for the dashboard AI breakdown panel.
    """
    if df is None or len(df) < 2:
        return ScoreBreakdown(0, 0, 0, 0, 0)

    idx = bar_index if bar_index >= 0 else len(df) + bar_index
    if idx < 1 or idx >= len(df):
        idx = len(df) - 1

    row = df.iloc[idx]
    prev = df.iloc[idx - 1]

    # Technical: MA, MACD, RSI, trend
    tech_raw = 50.0
    s, _, _ = _score_ma_crossover(row, prev)
    tech_raw += s * 0.8
    s, _, _ = _score_macd(row, prev)
    tech_raw += s * 0.7
    s, _, _ = _score_rsi(row)
    tech_raw += s * 0.6
    s, _ = _score_trend(row)
    tech_raw += s * 0.5
    technical = min(100, max(0, tech_raw))

    # Momentum: price momentum + volume
    mom_raw = 50.0
    s, _ = _score_momentum(row)
    mom_raw += s * 1.5
    s, _ = _score_volume(row)
    mom_raw += s * 1.2
    momentum = min(100, max(0, mom_raw))

    # Volatility: Bollinger width + RSI distance from 50
    vol_raw = 50.0
    close = row.get("Close")
    bb_u, bb_l = row.get("BB_Upper"), row.get("BB_Lower")
    rsi = row.get("RSI")
    if pd.notna(close) and pd.notna(bb_u) and pd.notna(bb_l) and bb_u != bb_l:
        bb_pct = (bb_u - bb_l) / close * 100
        vol_raw = min(100, bb_pct * 8)
    if pd.notna(rsi):
        vol_raw = (vol_raw + abs(rsi - 50) * 1.2) / 2
    volatility = min(100, max(0, vol_raw))

    # Risk: higher = safer (inverse of risk level)
    sig = generate_signal(df, bar_index=idx)
    risk_map = {"Low": 80, "Medium": 50, "High": 25}
    risk = float(risk_map.get(sig.risk_level, 50))

    overall = (technical * 0.35 + momentum * 0.25 + (100 - volatility) * 0.15 + risk * 0.25)
    overall = min(100, max(0, overall))

    return ScoreBreakdown(
        technical=round(float(technical), 1),
        momentum=round(float(momentum), 1),
        volatility=round(float(volatility), 1),
        risk=round(float(risk), 1),
        overall=round(float(overall), 1),
    )
