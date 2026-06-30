"""
Application configuration.

SAFETY: REAL_TRADING_ENABLED defaults to False. Paper trading only unless
you manually set REAL_TRADING_ENABLED=true in your environment AND understand
the risks. This app is for education, not live trading advice.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Trading mode — paper by default
# ---------------------------------------------------------------------------
REAL_TRADING_ENABLED: bool = os.getenv("REAL_TRADING_ENABLED", "false").lower() == "true"

# Alpaca API credentials (paper keys from https://app.alpaca.markets)
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")

# Paper trading base URL (default Alpaca paper endpoint)
ALPACA_PAPER_BASE_URL: str = os.getenv(
    "ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"
)
ALPACA_LIVE_BASE_URL: str = os.getenv(
    "ALPACA_LIVE_BASE_URL", "https://api.alpaca.markets"
)

# ---------------------------------------------------------------------------
# Risk & safety limits
# ---------------------------------------------------------------------------
MAX_POSITION_SIZE_USD: float = float(os.getenv("MAX_POSITION_SIZE_USD", "5000"))
MAX_DAILY_LOSS_USD: float = float(os.getenv("MAX_DAILY_LOSS_USD", "500"))
STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "0.05"))       # 5%
TAKE_PROFIT_PCT: float = float(os.getenv("TAKE_PROFIT_PCT", "0.10"))     # 10%
MIN_CONFIDENCE_TO_TRADE: int = int(os.getenv("MIN_CONFIDENCE_TO_TRADE", "60"))

# ---------------------------------------------------------------------------
# Backtest assumptions
# ---------------------------------------------------------------------------
TRANSACTION_COST_PCT: float = float(os.getenv("TRANSACTION_COST_PCT", "0.001"))  # 0.1%
SLIPPAGE_PCT: float = float(os.getenv("SLIPPAGE_PCT", "0.0005"))                # 0.05%

# ---------------------------------------------------------------------------
# Indicator defaults
# ---------------------------------------------------------------------------
SMA_PERIODS = [20, 50, 200]
EMA_FAST = 12
EMA_SLOW = 26
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
BB_PERIOD = 20
BB_STD = 2
MACD_SIGNAL = 9

# Supported data periods and intervals
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "5y"]
VALID_INTERVALS = ["1d", "1h"]

# Default watchlist for quick picks
DEFAULT_TICKERS = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META"]
