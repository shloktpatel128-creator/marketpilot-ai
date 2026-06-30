"""Trade journal — persists every decision."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from storage.database import fetch_decisions, save_decision
from storage.schemas import ScanResult, TradeDecision


class TradeJournal:
    def log_scan(self, result: ScanResult, approved: bool, rejection_reasons: List[str]) -> int:
        sig = result.strategy_signal
        row = TradeDecision(
            evaluation_id=result.evaluation_id,
            broker_provider=result.broker,
            symbol=result.symbol,
            strategy=sig.strategy_name,
            action=sig.direction,
            setup_detected=sig.setup_detected,
            approved=approved,
            rejection_reasons=rejection_reasons,
            entry=sig.entry,
            stop_loss=sig.stop_loss,
            take_profit=sig.take_profit,
            confidence=result.confidence.confidence,
            model_version=result.confidence.model_version,
            risk_score=result.risk.risk_score,
            market_conditions=result.agents_context.get("data_quality", ""),
            news_context=result.agents_context.get("news_agent", ""),
            timestamp=result.timestamp,
            order_id=result.order.order_id if result.order else None,
            result=result.order.message if result.order else None,
        )
        return save_decision(row.to_dict())

    def get_recent(self, limit: int = 100, broker: Optional[str] = None) -> List[Dict[str, Any]]:
        return fetch_decisions(limit, broker)
