# Project Nemesis — AI Context File

This file is the single source of truth for any AI assistant or new collaborator
picking up this codebase. Read this before touching anything.

---

## What This Project Is

A systematic NSE (Indian stock exchange) swing trading system with:
- **Python backtesting engine** — tests strategies on historical daily + 1-hour data
- **Live intraday scanner** — runs during market hours, sends Telegram alerts
- **TradingView Pine Scripts** — visual validation of the same logic on charts
- **Strategy**: 1:2 R:R (risk ₹1,000 to make ₹2,000 per trade)

The target instrument universe is NSE F&O stocks (~200 liquid large/mid-caps).

---

## Repository Structure

```
Project Nemesis/
├── CLAUDE.md                        ← you are here
├── README.md                        ← setup and run guide
├── src/strategy_c/
│   ├── run.py                       ← CLI entry point (all commands here)
│   ├── config.py                    ← all tunable parameters + Telegram tokens
│   ├── daily_filter.py              ← morning pre-filter (Stage 2, ADX, RS, etc.)
│   ├── intraday_setup.py            ← 15-min candle signal detection
│   ├── scanner.py                   ← live loop that calls daily_filter + intraday_setup
│   ├── alerts.py                    ← Telegram message formatting and sending
│   ├── indicators.py                ← shared TA functions (EMA, ADX, RS, etc.)
│   ├── data_intraday.py             ← yfinance download helpers
│   ├── backtest.py                  ← daily EMA pullback backtest (2015–2024)
│   ├── backtest_intraday.py         ← 1-hour EMA pullback backtest (~3 years data)
│   ├── backtest_cooper.py           ← Cooper 5-Day Method daily backtest
│   └── report.py                    ← unified backtest reporting (prints all stats)
├── data/
│   ├── nifty50.csv                  ← Nifty 50 daily OHLCV (used for market state)
│   ├── sector_seasonality.csv       ← sector × month win-rate matrix
│   ├── universe/                    ← NSE stock universe CSV files
│   ├── intraday_1h/                 ← ** EXCLUDED FROM GIT ** 1-hour candle CSVs
│   └── prices/                      ← ** EXCLUDED FROM GIT ** daily price CSVs
├── results/
│   ├── strategy_c_trades_2015_2024.csv
│   ├── strategy_c_intraday_trades.csv
│   └── strategy_cooper_trades_2015_2024.csv
├── tradingview/
│   ├── NSE_Swing_Strategy.pine      ← Pine Script v6: single-stock strategy tester
│   └── NSE_Multi_Stock_Scanner.pine ← Pine Script v6: 10-stock signal scanner table
├── book_insights/                   ← summaries of key trading books read
└── experiments/                     ← experiment logs and notes
```

---

## How to Run

```bash
# 1. Install dependencies
pip install yfinance pandas numpy requests

# 2. Set Telegram credentials in src/strategy_c/config.py
#    TELEGRAM_BOT_TOKEN = "your_token_from_@BotFather"
#    TELEGRAM_CHAT_ID   = "your_chat_id"

# 3. Run commands
python3 -m src.strategy_c.run --screen               # morning pre-filter, print candidates
python3 -m src.strategy_c.run --scan                 # start live intraday scanner
python3 -m src.strategy_c.run --test RELIANCE.NS     # test signal detection on one stock
python3 -m src.strategy_c.run --alert-test           # print sample Telegram message (dry run)

# Backtests
python3 -m src.strategy_c.run --backtest             # EMA pullback daily (2015–2024)
python3 -m src.strategy_c.run --backtest-intraday    # EMA pullback 1h (~3 years)
python3 -m src.strategy_c.run --backtest-cooper      # Cooper 5-Day daily (2015–2024)

# Save results to CSV
python3 -m src.strategy_c.run --backtest --save
python3 -m src.strategy_c.run --backtest --start 2020-01-01 --end 2023-12-31
```

---

## Strategy A — EMA Pullback (Primary Strategy)

### Core Concept
Trend is up → stock pulls back to EMA(20) → resumes → enter the resumption.

### Entry Rules (all must be true)
1. **Stage 2**: Close > SMA50 > SMA200, and SMA50 > SMA50[20 days ago] (rising)
2. **ADX 25–45**: Trend is real but not overextended (>45 = exhaustion risk)
3. **RS**: Stock up ≥10% more than Nifty over last 63 trading days
4. **Pullback**: 2–5 bars where Low ≤ EMA(20) × 1.005 (within 0.5% of EMA)
5. **Volume**: Signal bar volume ≥ 1.5× 20-bar average (surge confirms resumption)
6. **Break**: Close breaks above the highest High of the entire pullback
7. **SMA50 floor**: Pullback Low must not break below SMA50 × 0.985 (dip, not breakdown)
8. **Skip months**: No trades in July, September, December (historically weak for NSE)

### Stop / Target / Sizing
- Stop: swing low of pullback − 0.25% buffer
- Target: 2:1 R:R from entry (fixed)
- Hard exit: Day 5 at close regardless
- Position size: ₹1,000 risk per trade, max ₹50,000 per position
- Trailing SL: every morning, move SL up to prior day's Low

### Backtest Results (1-hour candles, ~3 years)
- Starting from: −0.074R expectancy (broken baseline)
- After 3 improvements (volume 1.5×, SMA50 floor, ADX cap 45, month skip): −0.007R
- Still not positive — edge is marginal on hourly timeframe
- Daily backtest (2015–2024): better but still needs validation

---

## Strategy B — Cooper 5-Day Method

### Core Concept
Jeff Cooper (US trader): 3–5 consecutive lower closes → buy when price breaks prior bar's high.

### Entry Rules
1. Stage 2 + ADX 25–45 (same as Strategy A)
2. Exactly 3–5 consecutive lower closes (not more — too deep = weakness)
3. Close > yesterday's High (breakout trigger)
4. Pullback Low stays above SMA50 × 0.985
5. Volume dries up during pullback (avg vol of pullback bars < 85% of 20-bar avg)
6. Skip months: Jul, Sep, Dec

### Why Cooper Failed on NSE
- **Only 3 of 175 trades hit 2:1 target** (1.7% target hit rate)
- NSE F&O large-caps (TCS, Reliance, HDFC) move 1–3% per week
- Cooper's method written for US/Nasdaq stocks that move 5–10% per week
- To hit 2:1 in 5 days on NSE requires a 4–10% move — statistically rare
- Hard stop on Day 5 means most trades closed for small losses
- **Conclusion: Cooper is not viable on NSE large-caps at 2:1 R:R**

---

## Key Research Findings (do not repeat this work)

### What makes 1:2 R:R strategies work (from literature)
For a 1:2 system to be profitable, win rate must exceed 33.3%.
Documented win rates for well-filtered pullback-to-MA strategies: **42–52%**.

Five ingredients that separate profitable pullback systems from noise:
1. **Volume surge on breakout** — mandatory confirmation (Minervini, Weinstein)
2. **Trend quality filter** — ADX 25–45 (not too weak, not overextended)
3. **Structural floor** — pullback must stay above key MA (SMA50)
4. **Skip weak seasonal months** — Jul/Sep/Dec historically weak on NSE
5. **Pre-screen for relative strength** — only stocks beating Nifty by ≥10% (63-day)

### Data Limitations
- **Yahoo Finance intraday**: 60-day max for 15-min, ~730 days for 1-hour
- **Yahoo Finance daily**: data quietly stopped at 2024-12-30 for most stocks
- **Nifty data**: `data/nifty50.csv` has been updated to May 2026 manually
- **Stock daily cache** (`data/prices/`): still mostly ends at Dec 2024
- For any 2025+ live testing, yfinance daily data needs re-downloading

### Parameter Bloat Warning
At one point the system had 14+ filters applied to 83 trades over 30 months.
That is statistically meaningless — you cannot distinguish signal from noise.
**Rule: maximum 4–5 core entry conditions. Every filter must be justified by
published research, not backtest curve-fitting.**

### "The 92% Strategy" (RSI-2 Pullback by Larry Connors)
- Historically 90%+ win rate on US large-cap stocks
- But: average win = 0.8R, average loss = 3.5R → negative expectancy overall
- Inverted R:R (risking more than you make) — not suitable for this project

---

## TradingView Scripts

### NSE_Swing_Strategy.pine (Pine Script v6)
Single-stock strategy tester. Load on any NSE daily chart.
- **Green triangle**: EMA Pullback signal
- **Blue triangle**: Cooper 5-Day signal
- **Yellow diamond**: Both strategies agree (highest conviction)
- **Red background**: Skip month (Jul/Sep/Dec)
- Top-right table: Trades, WR%, Profit Factor, Expectancy, Net P&L, Max DD
- Inputs: toggle each strategy on/off, adjust risk, filters

### NSE_Multi_Stock_Scanner.pine (Pine Script v6)
Shows 10 stocks simultaneously in a table. Load on any NSE daily chart.
- Change the 10 symbols in the Inputs panel (format: `NSE:RELIANCE`)
- Table columns: Symbol | Price | Stage2 | ADX | EMA PB | Cooper | Signal
- Gold row = both agree, Green = EMA PB only, Blue = Cooper only, Dark red = skip month

**Note**: TradingView shows one chart at a time. The scanner uses `request.security()`
to pull all 10 stocks' daily data regardless of what stock the chart is on.
Always use Daily timeframe when running these scripts.

---

## Live Alert System (Telegram)

### Setup
1. Create a bot via `@BotFather` on Telegram → get `TELEGRAM_BOT_TOKEN`
2. Get your `TELEGRAM_CHAT_ID` by messaging `@userinfobot`
3. Paste both into `src/strategy_c/config.py`

### Alert Format
Each alert includes: symbol, sector, entry range, stop, target, R:R, position size,
capital required, signal time, and validity window (45 minutes).

### Scanner Flow
```
09:30 IST → daily_filter.py screens all NSE F&O stocks
           → passes candidates to intraday loop
Every 5 min → fetch 15-min candles → run detect() → if signal: send Telegram
15:00 IST → scanner stops
```

---

## Broker Setup (not yet implemented)

The live scanner currently only sends Telegram alerts — it does NOT auto-execute trades.
Target broker: **Zerodha** (Kite Connect API)
Manual workflow: receive Telegram alert → place order in Zerodha app before 45-min window expires

---

## What Has NOT Been Done Yet

- [ ] Zerodha auto-execution (only manual alerts exist)
- [ ] Walk-forward validation on daily backtest
- [ ] Out-of-sample test on 2023–2024 data (currently included in training)
- [ ] Live paper trading log
- [ ] Portfolio-level position sizing (currently each trade sized independently)
- [ ] Re-download daily stock data past Dec 2024

---

## Coding Conventions

- All strategy parameters live in `src/strategy_c/config.py` — change there, not in the logic files
- Backtest functions always return a `pd.DataFrame` with standardized columns (see `report.py`)
- Required trade columns: `entry_date`, `exit_date`, `symbol`, `sector`, `pnl`, `win`,
  `r_multiple`, `trading_days`, `exit_reason`, `season_score`, `adx_at_entry`,
  `pullback_candles`, `nifty_green`, `market_state`
- `report.py:print_report()` accepts any backtest's output — do not change its column expectations
- Do not add filters without a literature citation. Document the source in a comment.
