"""
MarketPilot AI — global configuration.

SAFETY: Default mode is DRY_RUN. Live trading is blocked.
AI agents cannot place trades. RiskEngine has final authority.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Bot mode & safety (defaults — live trading impossible)
# ---------------------------------------------------------------------------
MODE: str = os.getenv("MODE", "DRY_RUN").upper()  # DRY_RUN | PAPER
# Safety flags are hardcoded — env vars cannot enable live trading or agent orders.
REAL_TRADING_ENABLED: bool = False
PAPER_TRADING_ONLY: bool = True
AI_CAN_PLACE_TRADES: bool = False
MODEL_AUTO_PROMOTION: bool = os.getenv("MODEL_AUTO_PROMOTION", "false").lower() == "true"
NEWS_AGENTS_SHADOW_MODE: bool = os.getenv("NEWS_AGENTS_SHADOW_MODE", "true").lower() == "true"

# Evaluation mode (two-week freeze)
EVALUATION_MODE: bool = os.getenv("EVALUATION_MODE", "false").lower() == "true"
EVALUATION_DAYS: int = int(os.getenv("EVALUATION_DAYS", "14"))

# ---------------------------------------------------------------------------
# Alpaca paper credentials
# ---------------------------------------------------------------------------
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER_BASE_URL: str = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# OpenAI (optional — agents use rule-based fallback)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# Risk limits
# ---------------------------------------------------------------------------
MAX_RISK_PER_TRADE_PCT: float = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.01"))
MAX_DAILY_LOSS_USD: float = float(os.getenv("MAX_DAILY_LOSS_USD", "500"))
MAX_DRAWDOWN_PCT: float = float(os.getenv("MAX_DRAWDOWN_PCT", "0.10"))
MAX_TRADES_PER_DAY: int = int(os.getenv("MAX_TRADES_PER_DAY", "10"))
MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
MIN_CONFIDENCE_TO_TRADE: int = int(os.getenv("MIN_CONFIDENCE_TO_TRADE", "60"))
MIN_REWARD_RISK: float = float(os.getenv("MIN_REWARD_RISK", "1.5"))
MAX_POSITION_SIZE_USD: float = float(os.getenv("MAX_POSITION_SIZE_USD", "5000"))

# ---------------------------------------------------------------------------
# Futures simulator
# ---------------------------------------------------------------------------
FUTURES_COMMISSION: float = float(os.getenv("FUTURES_COMMISSION", "2.50"))
FUTURES_SLIPPAGE_TICKS: int = int(os.getenv("FUTURES_SLIPPAGE_TICKS", "1"))
FUTURES_MAX_DAILY_LOSS: float = float(os.getenv("FUTURES_MAX_DAILY_LOSS", "1000"))
FUTURES_MAX_TRADES_DAY: int = int(os.getenv("FUTURES_MAX_TRADES_DAY", "20"))

# ---------------------------------------------------------------------------
# Data & indicators
# ---------------------------------------------------------------------------
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "5y"]
VALID_INTERVALS = ["1d", "1h"]
DEFAULT_STOCK_SYMBOLS = ["AAPL", "TSLA", "NVDA", "SPY", "QQQ", "MSFT", "AMZN", "META", "GOOGL", "AMD"]
DEFAULT_FUTURES_SYMBOLS = ["MES", "MNQ", "MGC", "MCL", "MYM", "M2K"]
DEFAULT_FOREX_SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
DEFAULT_CRYPTO_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"]
DEFAULT_TICKERS = DEFAULT_STOCK_SYMBOLS  # legacy alias

# Scheduler
SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

# AI model
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
USE_KELLY_SIZING: bool = os.getenv("USE_KELLY_SIZING", "false").lower() == "true"

SMA_PERIODS = [20, 50, 200]
EMA_FAST, EMA_SLOW = 12, 26
RSI_PERIOD = 14
RSI_OVERBOUGHT, RSI_OVERSOLD = 70, 30
BB_PERIOD, BB_STD = 20, 2
MACD_SIGNAL = 9

TRANSACTION_COST_PCT = float(os.getenv("TRANSACTION_COST_PCT", "0.001"))
SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.0005"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.05"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.10"))

# Storage
DB_PATH: str = os.getenv("DB_PATH", "storage/marketpilot.db")
MODEL_DIR: str = os.getenv("MODEL_DIR", "storage/models")

# Strategy default
DEFAULT_STRATEGY: str = os.getenv("DEFAULT_STRATEGY", "vwap_momentum")
