from agents.base import BaseAgent


class MacroNewsAgent(BaseAgent):
    name = "macro_news_agent"

    def run(self, **kwargs) -> str:
        return "Macro context: No major macro events flagged (placeholder)."
