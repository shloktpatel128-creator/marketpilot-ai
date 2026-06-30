from agents.base import BaseAgent


class BacktestCriticAgent(BaseAgent):
    name = "backtest_critic"

    def run(self, win_rate: float = 0, trades: int = 0, **kwargs) -> str:
        return f"Backtest critic: {trades} trades, {win_rate:.1f}% win rate — review sample size."
