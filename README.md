# MarketPilot AI — Stock Analyzer & Paper Trading Bot

A beginner-friendly Python app that analyzes stocks, generates buy/sell/hold signals from technical indicators, backtests strategies on historical data, and paper trades via [Alpaca](https://alpaca.markets) — **no real money by default**.

> **Disclaimer:** This project is for **educational purposes only**. It is **not financial advice**. Past performance does not guarantee future results. Always do your own research before investing.

---

## Features

| Feature | Description |
|---------|-------------|
| **Stock analysis** | Enter any US ticker (AAPL, TSLA, NVDA, etc.) with validation |
| **Market data** | Historical OHLCV via yfinance (1mo–5y, daily/hourly) |
| **Indicators** | SMA 20/50/200, EMA 12/26, MACD, RSI, Bollinger Bands, volume trend, momentum (via `ta` library) |
| **Signals** | BUY / SELL / HOLD with confidence score, risk level, and plain-English explanation |
| **Backtesting** | Total return, win rate, max drawdown, trade log vs buy-and-hold |
| **Paper trading** | Alpaca paper API with safety guardrails (position limits, stop-loss, etc.) |
| **Dashboard** | Interactive Streamlit UI with Plotly charts |

---

## Project Structure

```
├── app.py           # Streamlit dashboard (main entry point)
├── config.py        # Settings, API keys, risk limits
├── data.py          # yfinance data fetching & ticker validation
├── indicators.py    # Technical indicator calculations
├── strategy.py      # Signal engine (BUY/SELL/HOLD)
├── backtest.py      # Historical strategy simulation
├── paper_trader.py  # Alpaca paper trading integration
├── requirements.txt
├── .env.example     # Template for API keys
└── README.md
```

---

## Installation

### 1. Clone or download this project

```bash
cd shloksVM
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Alpaca **paper trading** API keys (see below). Paper trading works without keys for analysis and backtesting — only the live paper-trade section needs them.

---

## How to Run

Start the Streamlit dashboard:

```bash
streamlit run app.py
```

Your browser opens to `http://localhost:8501`. The dashboard includes six tabs: **Overview**, **Technicals**, **Backtest**, **Paper Trading**, **Trade Log**, and **Settings**.

### Using the dashboard

1. **Enter a ticker** in the sidebar (or click a quick-pick button).
2. **Choose period and interval** (daily recommended for most analysis).
3. Review the **latest signal**, **price charts**, and **indicator values**.
4. Scroll to **Backtest Results** to see how the strategy performed historically.
5. Connect Alpaca (optional) to view account status and place **paper trades**.

---

## Connecting Alpaca Paper Trading

Alpaca provides a free paper trading account with simulated money.

### Step 1: Create an Alpaca account

1. Go to [https://alpaca.markets](https://alpaca.markets) and sign up.
2. Open the **Paper Trading** dashboard: [https://app.alpaca.markets/paper/dashboard/overview](https://app.alpaca.markets/paper/dashboard/overview)

### Step 2: Generate API keys

1. In the paper dashboard, go to **API Keys**.
2. Create a new key pair (API Key ID + Secret Key).
3. Copy both values into your `.env` file:

```env
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REAL_TRADING_ENABLED=false
```

### Step 3: Restart the app

```bash
streamlit run app.py
```

The **Paper Trading** section at the bottom shows your account equity, open positions, and trade history. Use the **Execute Paper Trade** button in the sidebar to place a simulated order based on the current signal.

### Safety features

| Guardrail | Default | Description |
|-----------|---------|-------------|
| `REAL_TRADING_ENABLED` | `false` | Blocks all live (real money) trading |
| `MAX_POSITION_SIZE_USD` | $5,000 | Caps each order size |
| `MAX_DAILY_LOSS_USD` | $500 | Halts trading after daily loss limit |
| `STOP_LOSS_PCT` | 5% | Auto-sells losing positions |
| `TAKE_PROFIT_PCT` | 10% | Auto-sells winning positions |
| `MIN_CONFIDENCE_TO_TRADE` | 60% | Skips low-confidence signals |
| Market closed check | — | No orders when market is closed |

> **Never set `REAL_TRADING_ENABLED=true` unless you fully understand the risks.** Even when enabled, this app blocks automated live orders for safety.

---

## How Backtesting Works

The backtester simulates the signal strategy on historical data:

1. For each bar, it generates a BUY / SELL / HOLD signal with a confidence score.
2. It enters a long position on **BUY** (when confidence ≥ threshold) and exits on **SELL**.
3. Transaction costs (0.1%) and slippage (0.05%) are applied to each trade.
4. Results are compared against a simple **buy-and-hold** benchmark.

Metrics shown:

- **Strategy Return** — total % gain/loss from the signal strategy
- **Buy & Hold** — passive benchmark return
- **Alpha** — strategy return minus buy-and-hold
- **Win Rate** — % of trades that were profitable
- **Max Drawdown** — largest peak-to-trough decline
- **Equity Curve** — visual comparison chart

Adjust **Min Confidence** in the sidebar to see how stricter thresholds affect results.

---

## Signal Logic (Overview)

Signals combine five factor groups, each contributing to a composite score:

1. **Moving average crossover** — SMA 20 vs SMA 50, price vs SMA 200
2. **RSI** — overbought (>70) / oversold (<30) conditions
3. **MACD** — line vs signal crossover and histogram direction
4. **Volume** — above/below 20-day average volume
5. **Momentum & trend** — 10-bar price change, EMA trend, Bollinger Band position

| Score | Action |
|-------|--------|
| ≥ +20 | BUY |
| ≤ −20 | SELL |
| otherwise | HOLD |

Confidence is scaled from the absolute score (0–100). Risk level considers RSI extremes, momentum magnitude, and volume spikes.

---

## Configuration Reference

All settings live in `config.py` and can be overridden via `.env`:

```env
REAL_TRADING_ENABLED=false
MAX_POSITION_SIZE_USD=5000
MAX_DAILY_LOSS_USD=500
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10
MIN_CONFIDENCE_TO_TRADE=60
TRANSACTION_COST_PCT=0.001
SLIPPAGE_PCT=0.0005
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No data returned for ticker` | Check the symbol is valid and listed on a US exchange |
| `Alpaca not connected` | Copy `.env.example` → `.env`, add paper API keys, restart |
| Hourly data warning | Yahoo limits hourly data to ~60 days; use shorter periods |
| Indicators show NaN | Need more history — try a longer period (e.g. 1y or 5y) |
| `alpaca-py not installed` | Run `pip install alpaca-py` |

---

## Why This Is Educational — Not Financial Advice

- **Simplified signals** — Real trading systems use far more data, risk models, and execution logic.
- **Survivorship bias** — Backtests on historical data don't account for delisted stocks or changing market regimes.
- **No guarantee** — A strategy that worked in the past may fail in the future.
- **Paper ≠ live** — Simulated fills don't reflect real slippage, liquidity, or emotions.

Use this tool to **learn** how technical indicators, signals, backtesting, and broker APIs work. Do not rely on it for actual investment decisions.

---

## License

MIT — use freely for learning and experimentation.
