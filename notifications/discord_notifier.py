"""Discord webhook notifications."""

from __future__ import annotations

import json
import logging
import urllib.request

from config import DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)


def notify(title: str, message: str, level: str = "info") -> bool:
    if not DISCORD_WEBHOOK_URL:
        logger.debug("Discord webhook not configured — skip: %s", title)
        return False
    emoji = {"info": "ℹ️", "trade": "📈", "risk": "🛑", "error": "❌", "report": "📊"}.get(level, "ℹ️")
    payload = {"content": f"{emoji} **{title}**\n{message}"}
    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as exc:
        logger.warning("Discord notify failed: %s", exc)
        return False
