# MarketPilot AI

Automated AI-assisted trading bot platform with a Streamlit control panel.

**Safety defaults:** `MODE=DRY_RUN`, live trading blocked, AI agents cannot place trades. The RiskEngine has final authority on every trade.

## Architecture

```
Market data → features → strategy → confidence model → agents (shadow) → RiskEngine → broker router → journal → dashboard
```

- **Alpaca Paper** — stocks/ETFs only (paper account)
- **Futures Simulator** — isolated simulated MES/MNQ/MGC/MCL/MYM/M2K
- **Dry Run** — logs decisions without broker calls

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add Alpaca keys for paper trading
```

### Run the dashboard (control panel)

```bash
streamlit run app.py
```

### Run the bot from CLI

```bash
# Full scan (dry run + futures sim; Alpaca if MODE=PAPER and keys set)
python main.py scan

# Single symbol
python main.py scan -s AAPL -b dry_run
python main.py scan -s MES -b futures_simulator

# Status
python main.py status
```

### Run tests

```bash
python -m pytest
```

## Project Structure

See `marketpilot-ai/` layout in repo root: `core/`, `data/`, `features/`, `strategies/`, `models/`, `risk/`, `brokers/`, `agents/`, `journal/`, `ui/`, `tests/`.

## Dashboard Tabs

- Command Center — start/pause bot, run scans, daily stats
- Futures Simulator / Alpaca Paper — per-broker views
- Risk Engine — limits and recent rejections
- AI Agents — shadow context (no trading)
- Trade Journal / Reports / Model Performance / Settings

## Phase 1 Status

Working: trading pipeline, risk engine, broker router, futures simulator, journal, dashboard, tests.

Placeholder: trained ML model, OpenAI agent summaries, scheduler automation, evaluation mode UI wiring.
