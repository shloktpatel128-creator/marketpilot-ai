from agents.base import BaseAgent


class DataQualityAgent(BaseAgent):
    name = "data_quality"

    def run(self, report=None, **kwargs) -> str:
        if report is None:
            return "No data quality report."
        return report.summary() if hasattr(report, "summary") else str(report)
