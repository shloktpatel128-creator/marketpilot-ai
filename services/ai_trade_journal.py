"""AI trade journal — explains entries, exits, and lessons."""

from __future__ import annotations

from typing import Dict, Optional

from config import OPENAI_API_KEY


def explain_trade(decision: Dict) -> str:
    symbol = decision.get("symbol", "?")
    approved = decision.get("approved")
    action = decision.get("action", "HOLD")
    conf = decision.get("confidence", 0)
    reasons = decision.get("rejection_reasons", [])
    cio = decision.get("cio_decision", "")
    plan = decision.get("trade_plan") or {}

    lines = [
        f"## Trade Analysis: {symbol}",
        f"**Action:** {action} | **Approved:** {approved} | **Confidence:** {conf:.0f}%",
    ]
    if approved:
        lines.append(f"**Entry rationale:** CIO and strategy aligned on {action}.")
        if plan:
            lines.append(f"**Plan:** Entry ${plan.get('entry', 0):.2f}, Stop ${plan.get('stop_loss', 0):.2f}, "
                         f"Target ${plan.get('take_profit', 0):.2f}, R:R {plan.get('reward_risk', 0)}")
            lines.append(f"**Expected value:** ${plan.get('expected_value', 0):.4f}/share")
    else:
        lines.append(f"**Rejection:** {'; '.join(reasons[:3])}")
        lines.append("**Lesson:** Wait for higher confidence setup or improved market conditions.")

    if cio:
        lines.append(f"**CIO summary:** {cio[:300]}")

    text = "\n".join(lines)
    if OPENAI_API_KEY:
        try:
            import json
            import urllib.request
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": f"As a trading coach, expand this journal entry with lessons learned:\n{text}"}],
                "max_tokens": 300,
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception:
            pass
    return text
