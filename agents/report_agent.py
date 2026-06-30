from agents.base import BaseAgent


class ReportAgent(BaseAgent):
    name = "report_agent"

    def run(self, stats=None, **kwargs) -> str:
        s = stats or {}
        return f"Report: {s.get('setups', 0)} setups, {s.get('trades', 0)} trades today."
