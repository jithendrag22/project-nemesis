# Project Nemesis — Backtest Plan

> The goal of backtesting is not to find the best possible numbers.
> It is to find out if this strategy has a real edge — and at what parameter
> settings it is most robust. A strategy that barely works on 10 years of
> data is not worth trading live.

---

## What We Are Testing

We are testing the full 10-layer strategy from `final_strategy_spec.md` on historical
NSE data, varying the parameters marked [BACKTEST] to find the combination that
produces the best risk-adjusted returns.

---

## Data

| Parameter | Value |
|-----------|-------|
| Historical data source | yfinance (Yahoo Finance, `.NS` suffix) |
| Backtest period | 10 years: Jan 2015 – Dec 2024 |
| Why 10 years | Includes bull markets (2017, 2019–2021, 2023–2024), bear markets (2020 Covid crash, 2022 correction), and sideways phases |
| Universe | NSE F&O eligible stocks (~200 stocks) |
| Benchmark | Nifty 50 total return (for comparison) |
| Nifty data | `^NSEI` on yfinance |

---

## Parameters to Test

These are the [BACKTEST] values from the strategy spec. Each will be tested at 3 levels.

| Parameter | Low | Default (v1.0) | High |
|-----------|-----|----------------|------|
| Market filter version | A (50 SMA only) | B (50+200 SMA) | C (Minervini strict) |
| Consolidation duration (Setup A) | 5–10 days | 5–15 days | 5–20 days |
| Consolidation max depth (Setup A) | 5% | 8% | 12% |
| Breakout volume threshold | 1.4× avg | 1.5× avg | 1.75× avg |
| Near 52-week high filter | Within 10% | Within 15% | Within 20% |
| Pullback proximity to 20 EMA (Setup B) | 0.5% | 1.0% | 1.5% |
| Prior advance before pullback (Setup B) | 10% | 15% | 20% |

---

## Test Combinations

Rather than testing every possible combination (which would be 3^7 = 2,187 runs),
we test systematically in phases:

### Phase 1 — Market Filter Test
Fix all other parameters at v1.0 default. Vary only the market filter.
Run 3 backtests: Version A, B, C.
Pick the version with the best expectancy and lowest drawdown. Lock it in.

### Phase 2 — Setup A Parameter Sweep
With the winning market filter locked, vary Setup A parameters independently:
- Run consolidation duration sweep (3 runs)
- Run consolidation depth sweep (3 runs)
- Run breakout volume sweep (3 runs)
- Run 52-week high proximity sweep (3 runs)
Total: 12 runs. Lock the best values for each parameter.

### Phase 3 — Setup B Parameter Sweep
Same approach — vary Setup B parameters independently.
- Pullback proximity: 3 runs
- Prior advance: 3 runs
Total: 6 runs. Lock best values.

### Phase 4 — Combined Final Test
Run the complete strategy with all locked parameters. This is the final backtest.

### Phase 5 — Walk-Forward Validation
Split the 10-year period:
- Train: 2015–2020 (6 years)
- Test: 2021–2024 (4 years, out-of-sample)

Re-run with parameters optimised on the train period. Compare test period results
to train period. If they are within 20% of each other — the strategy is robust.
If test period results are much worse — the parameters are overfit to the past.

---

## Metrics to Record (for every backtest run)

| Metric | How to calculate | Target |
|--------|-----------------|--------|
| Total trades | Count of all signals taken | Minimum 30 per year |
| Win rate | Wins ÷ Total trades | ≥ 55% |
| Average win (R) | Mean of positive R-multiples | ≥ 2.0R |
| Average loss (R) | Mean of negative R-multiples | ≤ 1.0R |
| Expectancy | (Win rate × avg win R) − (loss rate × avg loss R) | ≥ 0.5R |
| Max consecutive losses | Longest losing streak | Plan for up to 7 |
| Max drawdown | Worst peak-to-trough % drop | ≤ 20% |
| Profit factor | Gross profit ÷ Gross loss | ≥ 1.5 |
| SQN | (Expectancy ÷ StdDev of R) × √N | ≥ 2.0 |
| Avg hold time | Mean days per trade | 1–5 days |
| Annual return | % gain per year | ≥ 25% |
| Sharpe ratio | Return ÷ volatility of returns | ≥ 1.0 |

### Minimum passing criteria (all must be met):
- Total trades ≥ 30 per backtest period per year
- Win rate ≥ 50%
- Expectancy ≥ 0.4R
- Max drawdown ≤ 25%
- Profit factor ≥ 1.3

If a parameter combination fails any of these → reject it regardless of other metrics.

---

## What a Backtest Cannot Tell You

Document this clearly before looking at any results:

1. **Survivorship bias** — yfinance data includes stocks that are still listed. Stocks that were delisted (went bankrupt, got acquired, were suspended) are not in the data. This slightly inflates backtest returns. Expect 10–15% lower real-world performance.

2. **Look-ahead bias** — the code must NEVER use future data to make decisions. Each trading decision must use only data available at the close of the prior day. Double-check this in the code.

3. **Slippage** — assume ₹100 per round trip per trade (brokerage + STT + SEBI charges). Deduct this from every trade in the backtest.

4. **Liquidity** — a backtest assumes you can always buy and sell at the closing price. In reality, limit orders may not fill. Build in a 0.1% slippage assumption on entry.

5. **Execution gap** — you scan at 3:30 PM, you execute at 9:20 AM next day. The stock may have moved overnight. The backtest uses next-day open as the actual entry price, not the prior day close.

---

## Step-by-Step Implementation

```
Step 1: Environment setup
  - Install Python 3.11+
  - pip install yfinance pandas numpy pandas-ta matplotlib seaborn

Step 2: Data download
  - Download 10 years of daily OHLCV data for all F&O stocks
  - Download Nifty 50 data for the same period
  - Store as CSV files locally (one file per stock)
  - Handle missing data: forward fill gaps ≤ 3 days, drop stocks with > 30% missing

Step 3: Indicator calculation
  - For each stock and each date:
    EMA 20, EMA 50, EMA 150, EMA 200
    SMA 50, SMA 200
    ATR (14-day)
    Volume MA (20-day)
    52-week high (rolling 252-day high)
    RS vs Nifty (rolling 63-day / 3-month % return)

Step 4: Universe filter (Layer 1)
  - Apply daily: price ₹50–₹3,000, turnover > ₹10 crore
  - This changes over time — apply the filter as it would have applied on each date

Step 5: Market filter (Layer 2)
  - For each date, calculate if Nifty 50 passes the chosen version (A/B/C)
  - On days it fails: mark as "no trading day" — no signals generated

Step 6: Stage 2 filter (Layer 3)
  - Apply all 7 conditions to each stock on each trading day
  - Only stocks passing all 7 continue

Step 7: Setup scanner (Layers 4)
  - Setup A: for each stock passing Stage 2, check the flat base conditions
  - Setup B: for each stock passing Stage 2, check the 20 EMA pullback conditions
  - Record each signal: date, stock, setup type, entry, stop, target, R:R

Step 8: Trade simulator (Layers 5–9)
  - For each signal on date D:
    - Entry = next day (D+1) open price (simulate real execution)
    - Apply 0.1% slippage: actual entry = open × 1.001
    - If open is > 3% above prior close: skip the trade
    - Position size = floor(₹1,000 ÷ (entry − stop))
    - If capital > ₹50,000: reduce shares
    - Track each trade day by day:
      Day 1–3: check if +2% move. If not by Day 3 → exit at Day 3 close
      Any day: check if stop is hit → exit at stop
      Any day: check if 1:1 target hit → sell 50%, move stop to entry
      Any day: check if 2:1 target hit → sell remaining 50%
      Day 5: force exit if still open
    - Record outcome: entry, exit, days held, profit/loss in ₹, R-multiple

Step 9: Cost adjustment
  - Deduct ₹100 per trade (round trip transaction costs) from every trade result

Step 10: Metrics calculation
  - Calculate all metrics from the results table
  - Generate equity curve chart
  - Generate drawdown chart
  - Print summary table

Step 11: Parameter sweep
  - Wrap Steps 5–10 in a loop that varies each parameter
  - Save results for each combination
  - Rank combinations by expectancy × trades (volume × quality)

Step 12: Walk-forward test
  - Split data at 2020-12-31
  - Train on 2015–2020, lock parameters
  - Test on 2021–2024
  - Compare metrics

Step 13: Document the winner
  - Update final_strategy_spec.md with the backtested parameter values
  - Replace all [BACKTEST] labels with actual numbers
```

---

## Monthly Performance Analysis

This is the most important section for understanding what you will actually experience
trading this system. Overall stats look clean — monthly stats show the reality.

### Monthly metrics to calculate (for every month in the backtest):

| Metric | How to calculate |
|--------|-----------------|
| Monthly P&L (₹) | Sum of all trade profits/losses closed in that month |
| Monthly P&L (%) | Monthly P&L ÷ account equity at start of that month |
| Trades taken | Count of trades entered in that month |
| Winners | Count of trades that hit the 1:2 target |
| Losers | Count of trades stopped out |
| Win rate | Winners ÷ total trades for that month |
| Best trade | Highest single R-multiple in that month |
| Worst trade | Lowest single R-multiple in that month |
| Market state | Was Nifty in Bull / Neutral / Bear that month |

### Monthly summary statistics (across all 120 months):

| Stat | What it tells you |
|------|------------------|
| Positive months | How many of 120 months ended in profit |
| Negative months | How many of 120 months ended in a loss |
| Break-even months | Months with 0 trades (market filter blocked all signals) |
| % positive months | Positive ÷ (Positive + Negative) — target ≥ 65% |
| Avg positive month (₹) | What a good month looks like |
| Avg negative month (₹) | What a bad month costs |
| Best month ever (₹) | Know the ceiling |
| Worst month ever (₹) | Know the floor — can you stomach this? |
| Max consecutive positive months | Longest winning streak |
| Max consecutive negative months | Longest losing streak — this is what breaks discipline |
| Months with 0 trades | How often does the market filter block everything |

### Why this matters more than overall stats:

A strategy with 60% annual return might have looked like this month by month:
```
Jan: +₹8,000  Feb: +₹3,000  Mar: -₹4,000  Apr: -₹3,500  May: +₹6,000
Jun: -₹2,000  Jul: +₹5,000  Aug: +₹9,000  Sep: -₹1,000  Oct: +₹7,000
Nov: +₹4,000  Dec: -₹2,000
```
That's 8 positive, 4 negative — 67% positive months. Manageable.

But another strategy with the same 60% annual return might look like:
```
Jan: +₹1,000  Feb: +₹500   Mar: -₹6,000  Apr: -₹5,000  May: -₹4,000
Jun: -₹3,000  Jul: -₹2,000 Aug: +₹25,000 Sep: +₹8,000  Oct: +₹2,000
Nov: +₹1,000  Dec: +₹500
```
Same annual return. But 4 consecutive losing months would cause most people
to abandon the strategy in Month 6 — right before the big recovery in August.
The monthly breakdown tells you which system you can actually stick with.

### Minimum monthly acceptance criteria:
- Positive months ≥ 60% of all active months (months with at least 1 trade)
- Max consecutive negative months ≤ 3
- Worst single month ≤ -₹5,000 (5% of account — if worse, position sizing is wrong)
- Months with 0 trades: should be ≤ 20% of all months (market filter not too strict)

---

## Visualisations to Generate

1. **Equity curve** — account value over time for the backtest period
2. **Drawdown chart** — % drop from peak at each point in time
3. **Monthly returns heatmap** — grid of year × month coloured green/red by P&L
4. **Monthly P&L bar chart** — every month as a bar, green positive, red negative
5. **Consecutive months chart** — streaks of positive and negative months visualised
6. **Win/loss distribution** — histogram of R-multiples
7. **Trades per month** — are we getting enough signals?
8. **Market filter comparison** — side-by-side equity curves for Version A, B, C
9. **Setup A vs Setup B** — separate performance breakdown per month
10. **Bull vs Bear vs Neutral months** — win rate and return separated by market state

---

## Honest Success Criteria

The backtest passes if, on the out-of-sample test period (2021–2024):

| Metric | Required |
|--------|---------|
| Expectancy | ≥ 0.4R per trade |
| Win rate | ≥ 50% |
| Max drawdown | ≤ 25% |
| Annual return | ≥ 20% |
| Total trades | ≥ 25 per year (enough to be statistically meaningful) |
| Degrades vs train | ≤ 30% worse than training period |

If these pass → move to paper trading.
If these fail → review which layer is causing the most rejects and adjust.
Do not torture the data until it gives the answer you want.

---

## Paper Trading Phase (Before Real Money)

After backtest confirms positive expectancy:
- Run the live scanner daily
- Record every alert as a paper trade
- Track the outcome as if you had traded it on Groww
- Minimum 30 paper trades before switching to real money
- If paper trading expectancy ≥ 0.4R → go live
- If paper trading shows a very different result vs backtest → investigate why

---
*Version: 1.0 | Created: 2026-05-08*
