from agents.base import BaseAgent


class ModelDriftAgent(BaseAgent):
    name = "model_drift"

    def run(self, **kwargs) -> str:
        return "Model drift: within normal bounds (placeholder)."
