"""Enhanced report statistics."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List

from storage.database import fetch_decisions


def _filter_period(rows: List[Dict], days: int = 1) -> List[Dict]:
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    return [r for r in rows if (r.get("timestamp") or "") >= cutoff]


def _calc_stats(trades: List[Dict], setups: List[Dict], rejected: List[Dict]) -> Dict[str, Any]:
    wins = [r for r in trades if (r.get("pnl") or 0) > 0]
    losses = [r for r in trades if (r.get("pnl") or 0) < 0]
    win_pnls = [r.get("pnl", 0) for r in wins]
    loss_pnls = [abs(r.get("pnl", 0)) for r in losses]
    gross_win = sum(win_pnls)
    gross_loss = sum(loss_pnls)
    avg_win = gross_win / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    profit_factor = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0)
    expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss) if trades else 0
    reasons = Counter()
    for r in rejected:
        for reason in r.get("rejection_reasons", []):
            reasons[reason] += 1
    return {
        "total_setups": len(setups),
        "total_trades": len(trades),
        "rejected_trades": len(rejected),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor if profit_factor != float("inf") else None,
        "expectancy": expectancy,
        "max_drawdown": 0.0,  # placeholder until closed-trade P/L tracked
        "common_rejections": dict(reasons.most_common(5)),
        "by_symbol": dict(Counter(r["symbol"] for r in trades)),
        "by_strategy": dict(Counter(r["strategy"] for r in setups)),
        "by_broker": dict(Counter(r["broker_provider"] for r in trades)),
    }


def generate_daily_report(broker: str = None) -> Dict[str, Any]:
    rows = fetch_decisions(500, broker)
    today = _filter_period(rows, 1)
    setups = [r for r in today if r.get("setup_detected")]
    trades = [r for r in today if r.get("approved")]
    rejected = [r for r in setups if not r.get("approved")]
    stats = _calc_stats(trades, setups, rejected)
    return {"period": "daily", "date": date.today().isoformat(), "broker": broker or "all", **stats}


def generate_weekly_report(broker: str = None) -> Dict[str, Any]:
    rows = _filter_period(fetch_decisions(2000, broker), 7)
    setups = [r for r in rows if r.get("setup_detected")]
    trades = [r for r in rows if r.get("approved")]
    rejected = [r for r in setups if not r.get("approved")]
    stats = _calc_stats(trades, setups, rejected)
    return {"period": "weekly", "date": date.today().isoformat(), "broker": broker or "all", "total_decisions": len(rows), **stats}


def ai_summary(report: Dict[str, Any]) -> str:
    pf = report.get("profit_factor")
    pf_str = f"{pf:.2f}" if pf is not None else "N/A"
    return (
        f"Daily summary: {report.get('total_setups', 0)} setups, "
        f"{report.get('total_trades', 0)} trades, {report.get('rejected_trades', 0)} rejected. "
        f"Win rate {report.get('win_rate', 0):.1f}%, profit factor {pf_str}, "
        f"expectancy ${report.get('expectancy', 0):.2f}."
    )


def format_report_text(report: Dict[str, Any]) -> str:
    lines = [
        f"=== {report.get('period', '').upper()} REPORT — {report.get('date', '')} ===",
        f"Broker: {report.get('broker', 'all')}",
        f"Setups: {report.get('total_setups', 0)}",
        f"Trades: {report.get('total_trades', 0)}",
        f"Rejected: {report.get('rejected_trades', 0)}",
        f"Win rate: {report.get('win_rate', 0):.1f}%",
        f"Avg win: ${report.get('avg_win', 0):.2f}",
        f"Avg loss: ${report.get('avg_loss', 0):.2f}",
        f"Expectancy: ${report.get('expectancy', 0):.2f}",
    ]
    pf = report.get("profit_factor")
    if pf is not None:
        lines.append(f"Profit factor: {pf:.2f}")
    if report.get("common_rejections"):
        lines.append("Top rejections:")
        for k, v in report["common_rejections"].items():
            lines.append(f"  - {k}: {v}")
    return "\n".join(lines)
