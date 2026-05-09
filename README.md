# Project Nemesis

Systematic NSE swing trading system — EMA Pullback + Cooper 5-Day strategies.
1:2 R:R, ₹1,000 risk per trade, Telegram alerts, TradingView validation.

> **For AI assistants and collaborators**: read `CLAUDE.md` first. It contains
> the full strategy rules, research findings, architecture walkthrough, and
> decisions already made. Do not repeat work documented there.

---

## Quick Start

### Requirements
- Python 3.10+
- `pip install yfinance pandas numpy requests`

### Configure
Open `src/strategy_c/config.py` and fill in:
```python
TELEGRAM_BOT_TOKEN = "your_token"   # from @BotFather on Telegram
TELEGRAM_CHAT_ID   = "your_chat_id" # from @userinfobot on Telegram
```

### Run
```bash
# Morning screen — which stocks pass the pre-filter today?
python3 -m src.strategy_c.run --screen

# Live scanner — runs 09:30–15:00 IST, sends Telegram alerts
python3 -m src.strategy_c.run --scan

# Test one stock right now
python3 -m src.strategy_c.run --test RELIANCE.NS

# Print a sample Telegram alert (no actual message sent)
python3 -m src.strategy_c.run --alert-test
```

### Backtests
```bash
# EMA pullback — daily candles, 2015–2024
python3 -m src.strategy_c.run --backtest --save

# EMA pullback — 1-hour candles, ~3 years
python3 -m src.strategy_c.run --backtest-intraday --save

# Cooper 5-Day — daily candles, 2015–2024
python3 -m src.strategy_c.run --backtest-cooper --save

# Custom date range
python3 -m src.strategy_c.run --backtest --start 2020-01-01 --end 2023-12-31
```

Results are saved to `results/`.

---

## TradingView

Paste either script from `tradingview/` into the Pine Editor (Pine Script v6).
Use **Daily** timeframe on any NSE stock chart.

| Script | Purpose |
|---|---|
| `NSE_Swing_Strategy.pine` | Single-stock strategy tester with stats table |
| `NSE_Multi_Stock_Scanner.pine` | 10-stock signal scanner in one table |

---

## Data

Large CSV files (~76MB total) are excluded from this repo via `.gitignore`.
To download the data:

```bash
# Daily prices (downloads to data/prices/)
python3 -c "from src.strategy_c.daily_filter import download_universe; download_universe()"

# 1-hour intraday (downloads to data/intraday_1h/) — takes ~10 min
python3 -c "from src.strategy_c.data_intraday import download_all; download_all()"
```

`data/nifty50.csv` and `data/sector_seasonality.csv` are included in the repo (small files).

---

## Strategy Summary

| | EMA Pullback | Cooper 5-Day |
|---|---|---|
| Timeframe | Daily or 1-hour | Daily |
| Entry trigger | Close breaks above pullback high on ≥1.5× volume | Close > yesterday's High after 3–5 lower closes |
| Stop | Below pullback swing low | Below pullback swing low |
| Target | 2:1 R:R | 2:1 R:R |
| Hard exit | Day 5 close | Day 5 close |
| Status | Active — marginal edge, needs live validation | Research only — poor fit for NSE large-caps |

Full rules, parameter rationale, and research findings: see `CLAUDE.md`.

---

## Project Status

- [x] EMA Pullback daily backtest (2015–2024)
- [x] EMA Pullback 1-hour backtest (~3 years)
- [x] Cooper 5-Day backtest + conclusion (not viable on NSE)
- [x] Live scanner with Telegram alerts (coded, needs Telegram credentials)
- [x] TradingView strategy + scanner scripts
- [ ] Zerodha auto-execution
- [ ] Walk-forward validation
- [ ] Live paper trading
