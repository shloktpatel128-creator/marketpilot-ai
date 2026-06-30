from agents.base import BaseAgent


class RiskExplainerAgent(BaseAgent):
    name = "risk_explainer"

    def run(self, reasons=None, approved: bool = False, **kwargs) -> str:
        if approved:
            return "RiskEngine approved the trade — all checks passed."
        return "RiskEngine rejected: " + "; ".join(reasons or ["Unknown"])
