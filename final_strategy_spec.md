# Project Nemesis — Final Strategy Spec v1.0

> Every rule is locked. Parameters marked [BACKTEST] are starting values to be refined
> through testing. Everything else is fixed logic — do not change without a specific reason.

---

## Identity

| Field | Value |
|-------|-------|
| Strategy name | Project Nemesis |
| Style | Positional swing trading |
| Markets | NSE (India) |
| Capital | ₹1,00,000 |
| Risk per trade | ₹1,000 (1% — never negotiable) |
| Minimum reward | ₹2,000 (1:2 R:R minimum) |
| Hold period | 1–5 trading days |
| Max concurrent positions | 2 |
| Execution | Manual on Groww (CNC delivery) |
| Alert delivery | Telegram |
| Scan frequency | Daily, after 3:30 PM IST |

---

## Layer 1 — Stock Universe

Every stock must pass ALL of the following before it enters any further analysis.

| Condition | Rule |
|-----------|------|
| Exchange | NSE only |
| Stock list | F&O eligible stocks (~200 stocks) |
| Min daily turnover | ₹10 crore/day (20-day average) |
| Min price | ₹50 per share |
| Max price | ₹3,000 per share |
| Earnings buffer | No earnings announcement in the next 7 days |
| Exclusions | Z-category, suspended stocks, recently listed (< 1 year) |

---

## Layer 2 — Market Environment

Check Nifty 50 every day before scanning individual stocks.
If market check fails → no new trades, regardless of how good individual setups look.

### Three versions to backtest (pick winner after backtesting):

**Version A — Simple:**
- Nifty 50 closing price > 50-day SMA

**Version B — Moderate (starting default):**
- Nifty 50 closing price > 50-day SMA
- Nifty 50 closing price > 200-day SMA

**Version C — Strict (Minervini):**
- Nifty 50 > 50-day SMA
- Nifty 50 > 150-day SMA
- Nifty 50 > 200-day SMA
- 200-day SMA is trending upward (today's value > 20 days ago)

### Market states and rules:

| Market State | Condition | Action |
|-------------|-----------|--------|
| Bull | Market filter passes | Scan for setups normally |
| Choppy / Neutral | Market filter borderline | Only trade if ALL setup conditions pass with no exceptions |
| Bear | Market filter fails | Zero new trades. 100% cash. |

### Distribution day tracking:
- Count days when Nifty 50 falls > 0.2% on higher volume than previous day
- 4+ distribution days in 3 weeks → treat as Choppy, apply strict rules
- 6+ distribution days in 3 weeks → treat as Bear, no new trades

---

## Layer 3 — Stage 2 Stock Filter

Every stock must pass ALL 7 conditions simultaneously.

| # | Condition | Rule |
|---|-----------|------|
| 1 | Price vs 50-day SMA | Closing price > 50-day SMA |
| 2 | Price vs 200-day SMA | Closing price > 200-day SMA |
| 3 | Near 52-week high | Price within 15% of 52-week high [BACKTEST: also test 10%, 20%] |
| 4 | Short-term trend | 50-day SMA value today > 50-day SMA value 20 days ago (trending up) |
| 5 | Relative strength | Stock 3-month % return > Nifty 50 3-month % return |
| 6 | Liquidity | 20-day average daily turnover > ₹10 crore |
| 7 | Earnings buffer | No announcement in next 7 calendar days |

Stocks passing all 7 enter pattern scanning.

---

## Layer 4 — Setup Identification

### Setup A — Flat Base Breakout

Scan for stocks where ALL of the following are true:

| Parameter | Rule | Status |
|-----------|------|--------|
| Consolidation duration | 5–15 trading days of sideways movement [BACKTEST] | v1.0 |
| Consolidation depth | High-to-low range within base ≤ 8% [BACKTEST: also test 5%, 12%] | v1.0 |
| Volume inside base | Today's volume < 20-day average (declining trend) | Fixed |
| Position in base | Stock is within top 3% of the base range (near the highs) | Fixed |
| Today's action | Today's close > highest close of the prior 5 days | Breakout trigger |
| Breakout volume | Today's volume ≥ 1.5× 20-day average volume [BACKTEST: also test 1.4×, 1.75×] | v1.0 |

### Setup B — Pullback to 20 EMA

Scan for stocks where ALL of the following are true:

| Parameter | Rule | Status |
|-----------|------|--------|
| Uptrend confirmed | Price > 50-day SMA AND > 200-day SMA | Fixed |
| Prior advance | Stock rose ≥ 15% from its last significant low before this pullback [BACKTEST] | v1.0 |
| Pullback target | Today's low touched within 1% of 20-day EMA [BACKTEST: also test 0.5%, 1.5%] | v1.0 |
| Pullback volume | Volume today < 20-day average (healthy pullback, not a reversal) | Fixed |
| Reversal signal | Today's close > 20-day EMA (bounced back above it) | Trigger |
| Confirmation | Today's close > yesterday's close | Fixed |

### Setup C — VCP (Future — v2.0)

> Not in the current scanner. Documented for future implementation.
> Volatility Contraction Pattern: each pullback within a base is measurably smaller
> than the previous in both price range and volume. Requires minimum 2 contractions.
> Add to scanner after 50+ live trades from Setups A and B.
> Reference: book_insights/02_trade_like_a_stock_market_wizard.md

---

## Layer 5 — Signal Validation (R:R Gate)

Before any alert fires, the system calculates R:R. If R:R < 1:2, no alert fires.

```
For Setup A:
  Entry     = today's close (or next-day open estimate)
  Stop      = lowest low of the consolidation period
  Risk      = Entry − Stop (per share)
  Shares    = ₹1,000 ÷ Risk per share  (round down)
  Capital   = Shares × Entry  (must be ≤ ₹50,000)
  Target    = Entry + (2 × Risk per share)
  R:R check = (Target − Entry) ÷ (Entry − Stop) must be ≥ 2.0

For Setup B:
  Entry     = today's close (above 20 EMA)
  Stop      = today's low (reversal candle low) or 20 EMA − 1%
              whichever is lower
  Risk      = Entry − Stop
  [same formula as above]
```

If capital required > ₹50,000 → reduce shares so capital ≤ ₹50,000, recalculate.
If R:R < 2.0 after position sizing → REJECT, do not alert.

---

## Layer 6 — Entry Rules

| Rule | Detail |
|------|--------|
| When scan runs | Daily at 3:30–4:00 PM IST (after market close) |
| Alert delivery | Telegram by 5:00 PM IST |
| Order placement | Next morning, 9:20–9:30 AM on Groww |
| Order type | Limit order at the pivot/entry price |
| Skip condition 1 | Stock gaps up > 3% at open vs prior close → skip trade |
| Skip condition 2 | Stock already > 5% above entry price at open → skip trade |
| Order mode | CNC (delivery) — never MIS |

---

## Layer 7 — Position Sizing

```
Risk per trade  = ₹1,000 (fixed)
Stop distance   = Entry price − Stop price (per share)
Shares          = floor(₹1,000 ÷ Stop distance)
Capital used    = Shares × Entry price

Hard cap: Capital used must be ≤ ₹50,000
If capital > ₹50,000: reduce shares to fit, accept slightly less than ₹1,000 risk

Max 2 positions open simultaneously
Both positions can each carry ₹1,000 risk (2% total account exposure at once)
Two positions must be in different sectors
```

---

## Layer 8 — Stop Loss

| Rule | Detail |
|------|--------|
| Setup A stop | Below the lowest low of the entire consolidation period |
| Setup B stop | Below the reversal candle's low OR below 20 EMA − 1% (whichever lower) |
| When to place | Immediately after buy order executes on Groww (SL order) |
| Type | Hard stop-loss order — no mental stops |
| After 1:1 hit | Move stop to entry price (breakeven) — cannot lose on this trade |
| Trailing | After breakeven: trail stop to most recent swing low on daily chart |
| Gap down | If stock opens below stop → exit at market immediately |
| Never | Widen the stop. The stop only moves up, never down. |

---

## Layer 9 — Exit Rules

| Scenario | Action |
|----------|--------|
| Price hits 1:1 (₹1,000 profit) | Exit 50% of shares. Move stop to breakeven. |
| Price hits 2:1 (₹2,000 profit) | Exit remaining 50%. Trade complete. |
| No +2% move by Day 3 close | Exit 100% — time stop. Dead money. |
| Day 5 (Friday) close | Exit 100% regardless of position. No weekend holds. |
| Earnings announced during hold | Exit the day before the announcement. |
| Stop hit at any time | Exit 100% at market. No hesitation. |
| Breakout fails (reverses below pivot) | Exit 100% at market. |

---

## Layer 10 — When NOT to Trade

| Condition | Rule |
|-----------|------|
| Market filter fails | Zero new trades |
| 5 consecutive losses | Pause. Review last 5 trades. Identify what was wrong before next trade. |
| Down 5% on the month | Stop new trades for rest of calendar month. Review. |
| You are emotional (angry, anxious, euphoric) | Do not trade that day. |
| You haven't reviewed the alert on TradingView | Do not place the order. |
| Setup doesn't feel right but scanner fired | Trust the rules OR skip — never "half trust" by reducing size |

---

## Performance Targets

| Metric | Target | Minimum Acceptable |
|--------|--------|--------------------|
| Trades per month | 4–8 | 2 |
| Win rate | ≥ 60% | ≥ 50% |
| Expectancy per trade | ≥ 0.8R (₹800) | ≥ 0.5R (₹500) |
| Average winner | ₹2,000+ | ₹1,500 |
| Average loser | ≤ ₹1,000 | ≤ ₹1,000 (hard cap) |
| Max consecutive losses | Plan for 5 | — |
| Monthly return (expected) | ~4–8% | ~2% |
| Annual return (compounded) | ~50–80% | ~25% |

---

## Non-Negotiable Rules (Never Break These)

1. Risk per trade is ₹1,000. Not ₹1,500 because "the setup looks amazing."
2. Stop loss order is placed immediately after buy executes. Not later. Now.
3. The stop is never moved lower. It only moves up.
4. Day 5 is the exit. No "one more day."
5. No trades when market filter fails.
6. No two positions in the same sector.
7. No averaging down. If a trade is losing, the stop handles it.

---

*Version: 1.0 | Created: 2026-05-08 | Next review: after first 30 live trades*
