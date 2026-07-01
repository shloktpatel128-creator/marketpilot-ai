"""CLI entry point for MarketPilot AI trading bot."""

from __future__ import annotations

import argparse
import sys

from core.engine import TradingEngine
from core.logger import setup_logging
from core.state import STATE
from notifications import discord_notifier


def _print_scan_debug(result) -> None:
    sig = result.strategy_signal
    direction = sig.direction if sig.setup_detected else "HOLD"
    print(f"\n{'=' * 60}")
    print(f"{result.symbol} | {result.broker} | {direction}")
    print(f"{'=' * 60}")

    if result.agents_context.get("strategy_debug"):
        print(result.agents_context["strategy_debug"])

    if sig.setup_detected:
        print(f"\nSelected: {sig.strategy_name} ({sig.direction})")
        print(f"  Entry:       {sig.entry}")
        print(f"  Stop loss:   {sig.stop_loss}")
        print(f"  Take profit: {sig.take_profit}")
        print(f"  Invalidation:{sig.invalidation_level}")
        print(f"  R:R:         {sig.reward_risk:.2f}")
        print(f"  Setup conf:  {sig.setup_confidence:.0f}")
        print(f"  Reason:      {sig.reason}")
    else:
        print(f"\nHOLD — {sig.reason}")
        if sig.debug_notes:
            for note in sig.debug_notes[:6]:
                print(f"  • {note}")

    print(f"\nAI confidence: {result.confidence.confidence:.0f}/100")
    print(f"Risk approved: {result.risk.approved}")
    if result.risk.rejection_reasons:
        print("Rejection reasons:")
        for r in result.risk.rejection_reasons:
            print(f"  • {r}")
    elif result.risk.approved:
        print("  All risk checks passed (stop, R:R, confidence, data quality, limits).")


def cmd_scan(args: argparse.Namespace) -> int:
    engine = TradingEngine()
    if args.symbol:
        broker = args.broker or "dry_run"
        result = engine.scan_symbol(args.symbol.upper(), broker, strategy_name=args.strategy)
        _print_scan_debug(result)
        return 0
    results = engine.run_full_scan()
    print(f"\nFull scan: {len(results)} evaluations\n")
    for r in results:
        sig = r.strategy_signal
        direction = sig.direction if sig.setup_detected else "HOLD"
        status = "APPROVED" if r.risk.approved else "REJECTED" if sig.setup_detected else "HOLD"
        print(f"  {r.symbol:6} {r.broker:18} {direction:4} {status:8} conf={r.confidence.confidence:.0f} rr={sig.reward_risk:.2f}")
        if not r.risk.approved and r.risk.rejection_reasons:
            print(f"         → {r.risk.rejection_reasons[0]}")
        elif direction == "HOLD" and sig.reason:
            print(f"         → {sig.reason[:70]}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    from brokers.broker_router import BrokerRouter
    router = BrokerRouter()
    print("Bot status:", STATE.status_label())
    print("Mode:", STATE.mode)
    print("Evaluation ID:", STATE.evaluation_id)
    for name, info in router.status().items():
        print(f"  {name}: {info}")
    return 0


def main() -> int:
    setup_logging()
    discord_notifier.notify("Bot Startup", "MarketPilot CLI started", "info")

    parser = argparse.ArgumentParser(description="MarketPilot AI Trading Bot")
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="Run one scan cycle")
    scan_p.add_argument("--symbol", "-s", help="Single symbol to scan")
    scan_p.add_argument("--broker", "-b", choices=["dry_run", "futures_simulator", "alpaca_paper"])
    scan_p.add_argument("--strategy", default=None)
    scan_p.set_defaults(func=cmd_scan)

    status_p = sub.add_parser("status", help="Show bot status")
    status_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
