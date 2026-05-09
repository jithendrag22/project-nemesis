# Project Nemesis — System Architecture

---

## What We Are Building

A daily automated scanner that:
1. Downloads EOD market data after 3:30 PM IST
2. Applies the 10-layer strategy filter from `final_strategy_spec.md`
3. Sends a Telegram alert for every valid setup
4. Logs all signals (valid + rejected) to a file for review

You then manually execute the trade on Groww.
No automated order placement. No broker API needed.

---

## Data Flow

```
 3:30 PM IST — Market closes
        │
        ▼
 ┌─────────────────────────────┐
 │   NSE Bhavcopy Download     │  Official NSE daily CSV (all stocks EOD data)
 │   + yfinance historical     │  Yahoo Finance for historical backtest
 └─────────────┬───────────────┘
               │
               ▼
 ┌─────────────────────────────┐
 │   Universe Filter           │  F&O stocks only, ≥ ₹10cr turnover,
 │                             │  price ₹50–₹3,000, no recent listing
 └─────────────┬───────────────┘
               │
               ▼
 ┌─────────────────────────────┐
 │   Indicator Calculator      │  EMA 20/50/150/200, SMA 50/200,
 │                             │  ATR, Volume MA 20-day, RS vs Nifty
 └─────────────┬───────────────┘
               │
               ▼
 ┌─────────────────────────────┐
 │   Market Environment Check  │  Nifty 50 filter (Version A/B/C)
 │                             │  Distribution day count
 └─────────────┬───────────────┘
               │
        ┌──────┴──────┐
       PASS          FAIL
        │              │
        ▼              ▼
 ┌────────────┐  ┌──────────────┐
 │ Stage 2    │  │ Log: MARKET  │
 │ Filter     │  │ FAIL. No     │
 │ (7 rules)  │  │ scan today.  │
 └─────┬──────┘  └──────────────┘
       │
  ┌────┴────┐
 PASS     FAIL → skip stock
  │
  ▼
 ┌─────────────────────────────┐
 │   Setup Scanner             │
 │   ├── Setup A (flat base)   │
 │   └── Setup B (20 EMA pull) │
 └─────────────┬───────────────┘
               │
          ┌────┴────┐
        SETUP     NO SETUP
        FOUND       │
          │    ┌────┴────────────┐
          │    │ Log: WATCH LIST │  Stocks that pass Stage 2
          │    │ (near setup)    │  but pattern not complete yet
          │    └─────────────────┘
          ▼
 ┌─────────────────────────────┐
 │   Signal Validator          │
 │   • Calculate entry/stop    │
 │   • Position size           │
 │   • R:R check (must be ≥2)  │
 │   • Capital check (≤₹50K)   │
 └─────────────┬───────────────┘
               │
        ┌──────┴──────┐
       PASS          FAIL
        │              │
        ▼              ▼
 ┌────────────┐  ┌──────────────┐
 │  ALERT     │  │ Log: REJECT  │
 │  BUILDER   │  │ + reason     │
 └─────┬──────┘  └──────────────┘
       │
       ▼
 ┌─────────────────────────────┐
 │   Telegram Bot              │  Sends formatted alert to your phone
 └─────────────┬───────────────┘
               │
               ▼
 ┌─────────────────────────────┐
 │   Trade Log (CSV)           │  All alerts, rejects, and watch list
 └─────────────────────────────┘
               │
               ▼
         YOU — review alert,
         check chart on TradingView,
         place limit order on Groww next morning
```

---

## Telegram Alert Format

```
🟢 SIGNAL — Setup A (Flat Base Breakout)

Stock    : TITAN (NSE)
Sector   : Consumer Discretionary

Entry    : ₹3,420 (limit order)
Stop     : ₹3,318  (below consolidation low)
Target 1 : ₹3,522  (1:1 — sell 50% here)
Target 2 : ₹3,624  (1:2 — exit remaining)

Risk     : ₹102/share → 9 shares → ₹918 total risk
Capital  : ₹30,780 deployed (30.8% of account)
R:R      : 1 : 2.0 ✓

Base     : 9 days tight (depth: 6.2%)
Volume   : 1.8× average on breakout ✓
RS       : +12.3% vs Nifty (3 months) ✓
Market   : BULL (Nifty above 50d + 200d SMA) ✓

Action   : Buy limit ₹3,420 tomorrow 9:20–9:30 AM on Groww
Skip if  : Opens above ₹3,523 (gap > 3%)

⚠️  Check TradingView chart before placing order.
```

---

## Rejected Signal Format

```
🔴 REJECTED — HDFC Bank

Reason   : R:R = 1:1.4 (below minimum 1:2)
           Target at ₹1,720 only ₹28 above entry
           Stop ₹1,672 requires ₹20/share risk
           At 50 shares: capital = ₹85,000 (exceeds ₹50,000 cap)

Action   : No trade. Logged for review.
```

---

## Watch List Format

```
👀 WATCH — Infosys

Status   : Stage 2 filter PASS | Setup: NOT YET
           Consolidating for 3 days (need 5+)
           Volume drying up ✓
           Watch for breakout in 2–5 days.
```

---

## Technology Stack

| Component | Tool | Why |
|-----------|------|-----|
| Language | Python 3.11+ | Standard for data + finance |
| Data (backtest) | yfinance | Free, reliable, 10+ years NSE history |
| Data (live scan) | NSE Bhavcopy CSV | Official source, most accurate |
| Data processing | pandas, numpy | Industry standard |
| Indicators | pandas-ta | Technical indicators library |
| Scheduler | cron (Mac/Linux) or APScheduler | Run script at 3:45 PM IST daily |
| Alerts | python-telegram-bot | Free, instant, works on all devices |
| Storage | CSV files (simple) → SQLite later | No database overhead to start |
| Charts (you check) | TradingView free tier | Visual confirmation before trading |

---

## File Structure

```
Project Nemesis/
├── docs/
│   ├── final_strategy_spec.md
│   ├── system_architecture.md
│   ├── backtest_plan.md
│   └── book_insights/
│       └── [6 book files]
│
└── src/
    ├── main.py                    ← Daily runner: downloads data, scans, alerts
    │
    ├── data/
    │   ├── downloader.py          ← Download NSE Bhavcopy + yfinance
    │   ├── universe.py            ← Load and filter F&O stock list
    │   └── fo_stocks.csv          ← Master list of NSE F&O eligible stocks
    │
    ├── indicators/
    │   ├── moving_averages.py     ← EMA 20/50/150/200, SMA 50/200
    │   ├── volume.py              ← Volume MA, volume ratio calculation
    │   ├── relative_strength.py  ← RS vs Nifty 50 (3-month %)
    │   └── atr.py                 ← Average True Range
    │
    ├── filters/
    │   ├── market_filter.py       ← Nifty 50 environment check (3 versions)
    │   ├── universe_filter.py     ← Layer 1: turnover, price, exclusions
    │   └── stage2_filter.py       ← Layer 3: 7-condition stock filter
    │
    ├── setups/
    │   ├── setup_a.py             ← Flat base breakout scanner
    │   └── setup_b.py             ← Pullback to 20 EMA scanner
    │
    ├── signals/
    │   ├── validator.py           ← R:R check, position size, capital cap
    │   └── alert_builder.py       ← Format alert / reject / watch messages
    │
    ├── alerts/
    │   └── telegram_bot.py        ← Send messages via Telegram API
    │
    ├── backtest/
    │   ├── engine.py              ← Core backtest runner
    │   ├── metrics.py             ← Win rate, expectancy, SQN, drawdown
    │   └── parameter_sweep.py     ← Test parameter combinations
    │
    └── logs/
        ├── trades.csv             ← All live signals (for tracking)
        ├── rejects.csv            ← All rejected signals (for review)
        └── watchlist.csv          ← Stocks near a setup
```

---

## How Each Component Connects

```
main.py
  │
  ├── data/downloader.py          → pulls today's NSE Bhavcopy + Nifty 50
  │
  ├── data/universe.py            → loads fo_stocks.csv, applies Layer 1 filter
  │
  ├── indicators/*.py             → calculates all indicators for each stock
  │
  ├── filters/market_filter.py    → checks if market is Bull/Neutral/Bear
  │       │
  │       └── if FAIL → log "no scan today" → exit
  │
  ├── filters/stage2_filter.py    → applies 7-condition filter to each stock
  │
  ├── setups/setup_a.py           → checks flat base conditions on each stock
  ├── setups/setup_b.py           → checks 20 EMA pullback on each stock
  │
  ├── signals/validator.py        → calculates entry, stop, target, R:R, size
  │       │
  │       ├── VALID → signals/alert_builder.py → alerts/telegram_bot.py
  │       ├── REJECT → logs/rejects.csv
  │       └── WATCH → logs/watchlist.csv
  │
  └── logs/trades.csv             → all valid signals recorded
```

---

## Running Schedule

| Time (IST) | Action |
|-----------|--------|
| 3:30 PM | NSE market closes |
| 3:45 PM | Cron triggers main.py |
| 3:45–4:00 PM | Data downloads, indicators calculated, scan runs |
| ~4:00 PM | Telegram alerts sent |
| 4:00–9:00 PM | You review alert + TradingView chart |
| 9:20–9:30 AM next day | You place limit order on Groww |

Total daily effort from you: ~10 minutes of review.

---

## Build Sequence (What We Code First)

```
Phase 1 — Backtest foundation (validate strategy before alerting anything)
  1. data/downloader.py + universe.py
  2. indicators/*.py
  3. filters/*.py
  4. setups/setup_a.py + setup_b.py
  5. backtest/engine.py + metrics.py
  6. backtest/parameter_sweep.py
  → Run backtest. Decide parameters. Confirm system has edge.

Phase 2 — Live alerting system (only after backtest confirms positive expectancy)
  7. signals/validator.py + alert_builder.py
  8. alerts/telegram_bot.py
  9. main.py (ties everything together)
  10. Set up cron job

Phase 3 — Paper trading (run the system, don't trade real money yet)
  → 30 paper trades minimum
  → Compare paper results to backtest expectations

Phase 4 — Live trading on Groww
  → Full ₹1L capital
  → Review weekly
```

---
*Version: 1.0 | Created: 2026-05-08*
