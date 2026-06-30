from agents.base import BaseAgent


class TradeJournalAgent(BaseAgent):
    name = "trade_journal"

    def run(self, decision=None, **kwargs) -> str:
        d = decision or {}
        return f"Logged decision {d.get('evaluation_id', '?')} for {d.get('symbol', '?')} — approved={d.get('approved')}"
