"""Daily and weekly report generators."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List

from storage.database import fetch_decisions


def _filter_period(rows: List[Dict], days: int = 1) -> List[Dict]:
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    return [r for r in rows if (r.get("timestamp") or "") >= cutoff]


def generate_daily_report(broker: str = None) -> Dict[str, Any]:
    rows = fetch_decisions(500, broker)
    today = _filter_period(rows, 1)
    setups = [r for r in today if r.get("setup_detected")]
    trades = [r for r in today if r.get("approved")]
    rejected = [r for r in setups if not r.get("approved")]
    wins = [r for r in trades if (r.get("pnl") or 0) > 0]
    losses = [r for r in trades if (r.get("pnl") or 0) < 0]
    reasons = Counter()
    for r in rejected:
        for reason in r.get("rejection_reasons", []):
            reasons[reason] += 1
    return {
        "period": "daily",
        "date": date.today().isoformat(),
        "broker": broker or "all",
        "total_setups": len(setups),
        "total_trades": len(trades),
        "rejected_trades": len(rejected),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "common_rejections": dict(reasons.most_common(5)),
        "by_symbol": Counter(r["symbol"] for r in trades),
        "by_strategy": Counter(r["strategy"] for r in setups),
    }


def generate_weekly_report(broker: str = None) -> Dict[str, Any]:
    daily = generate_daily_report(broker)
    rows = _filter_period(fetch_decisions(2000, broker), 7)
    return {**daily, "period": "weekly", "total_decisions": len(rows)}


def format_report_text(report: Dict[str, Any]) -> str:
    lines = [
        f"=== {report.get('period', '').upper()} REPORT — {report.get('date', '')} ===",
        f"Broker: {report.get('broker', 'all')}",
        f"Setups: {report.get('total_setups', 0)}",
        f"Trades: {report.get('total_trades', 0)}",
        f"Rejected: {report.get('rejected_trades', 0)}",
        f"Win rate: {report.get('win_rate', 0):.1f}%",
    ]
    if report.get("common_rejections"):
        lines.append("Top rejections:")
        for k, v in report["common_rejections"].items():
            lines.append(f"  - {k}: {v}")
    return "\n".join(lines)
