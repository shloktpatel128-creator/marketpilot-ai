"""Trade journal — persists every decision with full AI context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from storage.database import fetch_decisions_filtered, save_decision, save_market_snapshot
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
            market_conditions=result.agents_context.get("data_quality", result.regime),
            news_context=result.agents_context.get("NewsAnalyst", result.agents_context.get("news_agent", "")),
            timestamp=result.timestamp,
            order_id=result.order.order_id if result.order else None,
            result=result.order.message if result.order else None,
        )
        d = row.to_dict()
        d["indicator_snapshot"] = result.indicator_snapshot
        d["trade_plan"] = result.trade_plan or {}
        d["cio_decision"] = result.cio_decision
        d["agent_outputs"] = result.agents_context
        d["regime"] = result.regime
        d["scan_duration_ms"] = result.scan_duration_ms
        rid = save_decision(d)
        if result.indicator_snapshot:
            save_market_snapshot(result.evaluation_id, result.symbol, result.indicator_snapshot, result.regime)
        return rid

    def get_recent(self, limit: int = 100, broker: Optional[str] = None) -> List[Dict[str, Any]]:
        return fetch_decisions_filtered(limit=limit, broker=broker)
