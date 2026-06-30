"""CLI entry point for MarketPilot AI trading bot."""

from __future__ import annotations

import argparse
import sys

from core.engine import TradingEngine
from core.logger import setup_logging
from core.state import STATE
from notifications import discord_notifier


def cmd_scan(args: argparse.Namespace) -> int:
    engine = TradingEngine()
    if args.symbol:
        broker = args.broker or "dry_run"
        result = engine.scan_symbol(args.symbol.upper(), broker, strategy_name=args.strategy)
        print(f"{result.symbol} | {result.broker} | setup={result.strategy_signal.setup_detected} "
              f"| approved={result.risk.approved} | conf={result.confidence.confidence:.0f}")
        if result.risk.rejection_reasons:
            print("Rejections:", "; ".join(result.risk.rejection_reasons))
        return 0
    results = engine.run_full_scan()
    print(f"Full scan: {len(results)} evaluations")
    for r in results:
        print(f"  {r.symbol:6} {r.broker:18} approved={r.risk.approved} conf={r.confidence.confidence:.0f}")
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
