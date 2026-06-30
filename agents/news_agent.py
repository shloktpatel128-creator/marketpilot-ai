from agents.base import BaseAgent
from config import NEWS_AGENTS_SHADOW_MODE


class NewsAgent(BaseAgent):
    name = "news_agent"

    def run(self, symbol: str = "", news=None, **kwargs) -> str:
        news = news or []
        if not news:
            return "No recent news available."
        bullish = sum(1 for n in news if n.get("sentiment") == "bullish")
        bearish = sum(1 for n in news if n.get("sentiment") == "bearish")
        mode = " [SHADOW]" if NEWS_AGENTS_SHADOW_MODE else ""
        return f"News scan{mode}: {len(news)} articles. Bullish {bullish}, Bearish {bearish}."
