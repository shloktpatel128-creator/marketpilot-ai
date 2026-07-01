"""AI-generated daily market briefings."""

from __future__ import annotations

from datetime import date

from config import OPENAI_API_KEY
from services.watchlist import scan_watchlist
from storage.database import count_today, fetch_decisions_filtered


def generate_daily_briefing() -> str:
    counts = count_today()
    top = scan_watchlist(limit=5)
    today = date.today().isoformat()
    rejected = fetch_decisions_filtered(limit=20, date_prefix=today, approved=False)

    lines = [
        f"# MarketPilot AI Daily Briefing — {today}",
        "",
        "## Overnight / Today Summary",
        f"- Bot evaluations today: {counts['total']}",
        f"- Setups detected: {counts['setups']}",
        f"- Trades approved: {counts['trades']}",
        f"- Rejections: {counts['rejected']}",
        "",
        "## Top Opportunities (AI Ranked)",
    ]
    for i, e in enumerate(top, 1):
        lines.append(f"{i}. **{e.symbol}** ({e.asset_class}) — score {e.opportunity_score:.0f}, {e.direction}, {e.regime}")

    if rejected:
        lines.append("\n## Notable Rejections")
        for r in rejected[:5]:
            reasons = ", ".join(r.get("rejection_reasons", [])[:2])
            lines.append(f"- {r['symbol']}: {reasons}")

    lines.append("\n## Conviction")
    if top:
        best = top[0]
        lines.append(f"Highest conviction: **{best.symbol}** — {best.summary}")
    else:
        lines.append("No high-conviction setups at this time.")

    briefing = "\n".join(lines)

    if OPENAI_API_KEY:
        try:
            import json
            import urllib.request
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": f"Expand this trading desk briefing into 3 professional paragraphs:\n{briefing}"}],
                "max_tokens": 500,
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            briefing = data["choices"][0]["message"]["content"]
        except Exception:
            pass

    return briefing
