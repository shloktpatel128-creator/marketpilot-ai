from agents.base import BaseAgent


class TradeAnalysisAgent(BaseAgent):
    name = "trade_analysis"

    def run(self, signal=None, **kwargs) -> str:
        if not signal or not signal.setup_detected:
            return "No trade setup to analyze."
        return f"Setup: {signal.direction} — {signal.reason} R:R {signal.reward_risk}"
