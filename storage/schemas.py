"""Data schemas for trades, decisions, and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StrategySignal:
    setup_detected: bool
    direction: str  # BUY | SELL | HOLD
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reward_risk: float
    reason: str
    features_used: List[str] = field(default_factory=list)
    strategy_name: str = ""
    invalidation_level: Optional[float] = None
    setup_confidence: float = 0.0
    debug_notes: List[str] = field(default_factory=list)


@dataclass
class ConfidenceResult:
    confidence: float  # 0-100
    model_version: str
    explanation: str


@dataclass
class RiskDecision:
    approved: bool
    rejection_reasons: List[str] = field(default_factory=list)
    adjusted_size: Optional[float] = None
    risk_score: float = 0.0


@dataclass
class OrderResult:
    success: bool
    broker: str
    order_id: Optional[str] = None
    message: str = ""
    fill_price: Optional[float] = None
    qty: Optional[float] = None


@dataclass
class TradeDecision:
    evaluation_id: str
    broker_provider: str
    symbol: str
    strategy: str
    action: str
    setup_detected: bool
    approved: bool
    rejection_reasons: List[str]
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float
    model_version: str
    risk_score: float
    market_conditions: str
    news_context: str
    timestamp: str
    order_id: Optional[str] = None
    result: Optional[str] = None
    pnl: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    evaluation_id: str
    symbol: str
    broker: str
    strategy_signal: StrategySignal
    confidence: ConfidenceResult
    risk: RiskDecision
    order: Optional[OrderResult]
    agents_context: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    indicator_snapshot: Dict[str, Any] = field(default_factory=dict)
    trade_plan: Optional[Dict[str, Any]] = None
    cio_decision: str = ""
    regime: str = ""
    scan_duration_ms: float = 0.0
