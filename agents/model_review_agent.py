from agents.base import BaseAgent


class ModelReviewAgent(BaseAgent):
    name = "model_review"

    def run(self, version: str = "", **kwargs) -> str:
        return f"Model review: active version {version}. No drift detected (placeholder)."
