# Project Nemesis — Strategy Rules

## Your Parameters (locked in)

| Parameter | Value |
|-----------|-------|
| Capital | ₹1,00,000 |
| Risk per trade | ₹1,000 (1% of capital) — hard limit, never exceed |
| Minimum reward target | ₹2,000 (2% of capital) — 1:2 R:R minimum |
| Hold period | 1 day minimum, 5 trading days (1 week) maximum |
| Markets | Indian stocks (NSE) + Crypto |
| Win rate goal | 60% |
| Style | Positional swing — NOT intraday |

---

## The Math First (why this works)

With 60% win rate and 1:2 R:R:

```
Per 10 trades:
  6 winners × ₹2,000 = ₹12,000
  4 losers  × ₹1,000 = -₹4,000
  Net profit          = ₹8,000 (8% on ₹1L)

Expected value per trade = (0.6 × 2) - (0.4 × 1) = +0.8R = +₹800 average
```

You only need to be right 6 out of 10 times.
Even at 5/10 (50%) with strict 1:2, you break even — so the math has a buffer.
The edge compounds fast once you are consistent.

---

## Part 1 — Stock Selection (which stocks to look at)

### Universe (what to scan)
- NSE stocks only (better liquidity, F&O stocks preferred for tighter spreads)
- Price range: ₹50 to ₹3,000 per share (outside this range, position sizing gets awkward)
- Minimum average daily volume: 5 lakh shares OR ₹2 crore daily turnover
- Avoid: penny stocks, Z-category, recently listed (< 1 year), stocks with pending regulatory issues

### Sectors to focus on (established trends, liquid)
- Banking & Finance (HDFC Bank, ICICI, Axis, SBI, Kotak)
- IT & Tech (Infosys, TCS, Wipro, HCL Tech, Tech Mahindra)
- Pharma (Sun Pharma, Dr Reddy's, Cipla, Lupin)
- Auto (Maruti, M&M, Tata Motors, Bajaj Auto)
- FMCG (HUL, ITC, Nestle, Dabur)
- Midcap momentum names (scan daily for breakouts)

### Stock must pass ALL of these before analysis:
1. Price is above its 50-day EMA
2. Price is above its 200-day EMA (long-term uptrend)
3. Stock is within 15% of its 52-week high (strong relative strength)
4. No earnings announcement in the next 7 days (event risk)
5. No promoter pledge news, SEBI action, or major negative fundamental event

---

## Part 2 — Setup Rules (when to enter)

### The only two setups you trade

**Setup A — Breakout from Consolidation (preferred)**
```
Condition:
  Stock has been consolidating for 5–20 days in a tight range (< 8% width)
  Volume has been declining during consolidation (healthy coiling)
  Stock breaks above the consolidation high on volume ≥ 1.5× 20-day average volume

Entry:
  Buy on the breakout candle close (end-of-day order, not intraday)
  OR buy next day open if breakout was strong with high volume close

Stop:
  Below the consolidation low (the lowest candle low during the tight range)
  If (entry − consolidation low) > ₹X where X = 1000 / position_size → skip the trade

Target:
  Measured move = consolidation height × 2, added above breakout level
  Must give ≥ 1:2 R:R. If not → skip.
```

**Setup B — Pullback to Key Level in Uptrend**
```
Condition:
  Stock in clear uptrend (higher highs, higher lows on daily chart)
  Price pulls back to 20 EMA or 50 EMA or a prior breakout level
  Pullback is on declining volume (not a reversal, just cooling off)
  A reversal candle appears at the level: hammer, bullish engulfing, inside bar close above

Entry:
  Buy on close of the reversal candle
  OR buy when next day opens above the reversal candle's high

Stop:
  Below the reversal candle's low OR below the key level (whichever is lower)
  Must be within your ₹1,000 risk budget

Target:
  Prior swing high (minimum), or 2× the risk distance
  Must give ≥ 1:2. If not → skip.
```

### Setups you do NOT take
- Catching falling stocks / "it's too cheap" trades
- Breakdowns or short setups (stick to longs only until you have 6+ months experience)
- Stocks in news-driven spikes without consolidation
- Anything where the stop is more than ₹1,000 away from entry (at your position size)

---

## Part 3 — Position Sizing (exact formula)

```
risk_amount     = ₹1,000  (fixed, never change this)
risk_per_share  = entry_price - stop_price
position_size   = ₹1,000 / risk_per_share  (round down to whole shares)
capital_used    = position_size × entry_price

Check: capital_used must be ≤ ₹80,000 (80% of total capital)
       Never use more than 80% on a single trade.
       Ideally run 2 trades max at once (₹500 risk each, or one full ₹1,000 + no second trade)
```

### Example
```
Entry:  ₹450
Stop:   ₹432
Risk per share: ₹18

Position size = ₹1,000 / ₹18 = 55 shares (round down)
Capital used  = 55 × ₹450 = ₹24,750  ✓ (within 80% limit)

Target (1:2) = ₹450 + (2 × ₹18) = ₹486
Target (1:3) = ₹450 + (3 × ₹18) = ₹504 (runner)

Reward at T2 = 55 × ₹36 = ₹1,980 ≈ ₹2,000 ✓
```

---

## Part 4 — Entry & Exit Rules

### Entry
- Place orders as end-of-day (CNC delivery, not MIS/intraday) on NSE
- Only enter after market close candle confirms the setup (not during the day)
- Entry window: buy at next open or use a limit order at/near breakout level
- If the stock gaps up more than 3% at open — skip, the R:R is broken

### Exit — The Decision Tree
```
After entry, every day follow this:

Day 1:
  → If price hits T1 (1:1 reward): sell 50% of position, move stop to breakeven on remaining
  → If price drops to stop: exit 100%, take ₹1,000 loss, move on

Day 2–4:
  → If at T2 (1:2 reward): exit remaining 50%, trade closed ✓
  → Trail stop: move stop up to below the last swing low (protect profits)
  → If stop hit on remainder: you still made ~₹500-700 on the trade (partial win)

Day 5 (Friday / end of week):
  → Hard exit — close the trade regardless of where price is
  → No exceptions. Holding over the weekend for a 1-week swing is the maximum.
  → If in profit: take it. If at a small loss: take it.
  → Reason: weekend gap risk, no control over what happens

Never move your stop LOWER (wider) to give a trade "more room."
```

### Exit scenarios
| Scenario | Action |
|----------|--------|
| Hits T1 (1:1) | Sell 50%, move stop to breakeven |
| Hits T2 (1:2) | Sell remaining 50%, done |
| Hits T3 (1:3) | Sell 25%, trail rest |
| Stop hit immediately | Full loss ₹1,000, no hesitation |
| Day 5, in profit | Exit all |
| Day 5, small loss | Exit all, cap it |
| Gap down below stop | Exit at open, accept the slippage |

---

## Part 5 — Trade Management Rules

1. **Maximum 2 open trades at any time** — if you have 2 open, wait for one to close before entering a third
2. **No averaging down** — if a stock goes against you, do not buy more. Stop is stop.
3. **No revenge trading** — after a loss, wait until next day's market open before scanning again
4. **Weekly review** — every Sunday, review all closed trades: what worked, what didn't, why
5. **Journal every trade** — entry reason, setup type, result, what you learned
6. **Respect the 1-week hard exit** — time is risk. Stuck trades eat capital and opportunity cost

---

## Part 6 — Crypto Rules (same framework, different adjustments)

Indian exchanges: CoinDCX, WazirX, Binance (with INR on-ramp)
Pairs to focus on: BTC/INR, ETH/INR, BTC/USDT, ETH/USDT only to start

Adjustments for crypto:
- Use the same 1% risk (₹1,000) but expect wider stops (crypto is more volatile)
- Setup types are the same (breakout from consolidation, pullback to EMA)
- No hard 1-week limit — crypto can move faster; can exit in 2-3 days
- Check BTC dominance and overall crypto market trend before entering any altcoin
- Avoid: new tokens, meme coins, low liquidity pairs

---

## Part 7 — Where to Find Stocks (free tools)

| Tool | What to use it for |
|------|--------------------|
| [Chartink.com](https://chartink.com) | Free screener — build custom scans, free alerts |
| [Screener.in](https://screener.in) | Fundamental filters to avoid bad stocks |
| [NSE India](https://nseindia.com) | Official data, circuit filters, bulk deals |
| TradingView | Charting — set up your watchlist, draw levels |
| Zerodha Kite / Dhan | Execution platform (CNC orders) |

### Chartink scan to start with (paste in custom scan)
```
(close > ema(close, 50))
AND (close > ema(close, 200))
AND (close > (0.85 * max(high, 52*5)))   -- within 15% of 52-week high
AND (volume > 1.5 * avg(volume, 20))      -- volume spike today
AND (close > open)                         -- bullish close
```
Run this scan daily after market close (3:30 PM IST). These are your candidates.

---

## Performance Targets (realistic)

| Metric | Target |
|--------|--------|
| Trades per month | 4–8 (quality over quantity) |
| Win rate | ≥ 60% |
| Average winner | ₹2,000+ |
| Average loser | ₹1,000 (hard cap) |
| Monthly net (at 6 trades, 60% WR) | ~₹4,800 avg |
| Monthly return on capital | ~4.8% |
| Annual (if consistent) | ~50-60% (with compounding) |

This is not guaranteed — but it is mathematically sound. The only variable is execution discipline.

---

## The One Rule Above All

> **If the setup doesn't meet every condition, you don't take it.**
> 
> The hardest part of trading is not finding setups. It is sitting on your hands when nothing qualifies.
> A trade not taken is not a missed opportunity — it is capital preserved for a valid setup.
