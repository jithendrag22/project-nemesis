# Trade Your Way to Financial Freedom — Van Tharp
## Deep Insights for Project Nemesis
*Profile: ₹1,00,000 capital · ₹1,000 risk/trade · ₹2,000 target · 1:2 R:R · NSE swing trader*

---

## What "R" and R-Multiples Mean

**R = your initial risk on a trade** — the maximum amount you defined you're willing to lose, set before entry.

```
1R = Entry Price − Stop Price  (per share)
Dollar Risk = (Entry − Stop) × Number of Shares
```

Your 1R = ₹1,000 every trade. Fixed. Non-negotiable.

**R-Multiple = how the trade actually played out, divided by your 1R:**

| Outcome | Calculation | R-Multiple |
|---------|------------|-----------|
| Hit ₹2,000 target | ₹2,000 ÷ ₹1,000 | +2R |
| Stopped out | −₹1,000 ÷ ₹1,000 | −1R |
| Moved stop, lost more | −₹1,600 ÷ ₹1,000 | −1.6R ← this is a discipline failure |

**Why this matters:** express every trade result in R-multiples. A ₹5,000 profit means nothing without context — is that 1R or 5R? Only R-multiples tell you if you're trading well or just getting lucky.

---

## Expectancy — The Most Important Number in Trading

**Formula:**
```
Expectancy = (Win Rate × Average Win in R) − (Loss Rate × Average Loss in R)
```

Or more precisely: average of all your R-multiples across all trades (positive and negative).

**Good expectancy benchmarks:**

| Expectancy | System Quality |
|-----------|--------------|
| Negative | Losing system — stop trading it |
| 0.1–0.25R | Marginal |
| 0.25–0.50R | Good |
| 0.50–1.0R | Very good ("superb" per Tharp) |
| Above 1.0R | Excellent |

---

## Your System's Expectancy (Calculated)

**Your parameters:** 60% win rate, +2R winners, −1R losers.

```
Expectancy = (0.60 × 2R) − (0.40 × 1R)
           = 1.20R − 0.40R
           = 0.80R per trade

In rupees: 0.80 × ₹1,000 = ₹800 expected profit per trade
```

**Over 10 trades:**
```
6 wins × ₹2,000 = ₹12,000
4 losses × ₹1,000 = −₹4,000
Net = ₹8,000 (8% on ₹1L)
```

**Your break-even win rate** (with 1:2 R:R) = 33.3%. You have a massive buffer — even if your win rate drops to 50%, expectancy is still +0.5R (positive).

**At 50% win rate:**
```
(0.50 × 2R) − (0.50 × 1R) = 1.0 − 0.5 = 0.50R
```

Still profitable. Protecting your stop matters more than hitting your win rate.

---

## Win Rate vs R:R — Which Matters More?

**Tharp's answer: Expectancy — which combines both — is what matters.**

| System | Win Rate | Avg Win | Avg Loss | Expectancy |
|--------|---------|---------|---------|----------|
| A (high win rate) | 90% | 0.5R | 1R | +0.35R |
| B (low win rate) | 30% | 4R | 1R | +0.50R |
| C (your system) | 60% | 2R | 1R | **+0.80R** |

System A wins 90% of the time and still earns less per trade than your system. This is why protecting your 1R stop is more important than obsessing over win rate.

**The practical implication:** Never move your stop to avoid a loss. Every loss beyond −1R destroys your expectancy. A −2R loss is twice as damaging as it looks — it wipes out the profit from a full winning trade.

---

## The Percent Risk Position Sizing Model (Your Model)

This is the model Tharp recommends for most traders. You are already using it correctly.

**Step-by-step formula:**
```
1. Risk Amount    = Account Equity × 1%
                  = ₹1,00,000 × 1% = ₹1,000

2. Stop Distance  = Entry Price − Stop Price

3. Position Size  = ₹1,000 ÷ Stop Distance per share
                    (always round DOWN, never up)

4. Capital Used   = Position Size × Entry Price
                    (must be ≤ 80% of account)
```

**Live examples:**

| Stock | Entry | Stop | Stop Distance | Shares | Capital Used |
|-------|-------|------|--------------|--------|-------------|
| HDFC Bank | ₹1,700 | ₹1,683 | ₹17 | 58 | ₹98,600 — too large, skip or tighten stop |
| Tata Motors | ₹850 | ₹835 | ₹15 | 66 | ₹56,100 ✓ |
| Reliance | ₹2,950 | ₹2,921 | ₹29 | 34 | ₹1,00,300 — too large, skip |
| ICICI | ₹1,200 | ₹1,180 | ₹20 | 50 | ₹60,000 ✓ |

**The compounding engine:** As your account grows, your dollar risk per trade automatically grows too.
```
After growing to ₹1,10,000:
New risk per trade = ₹1,10,000 × 1% = ₹1,100
```

This is how small consistent gains compound — position size grows with the account, automatically.

---

## System Quality Number (SQN)

SQN combines expectancy, consistency, and sample size into one score.

**Formula:**
```
SQN = (Expectancy ÷ Standard Deviation of R-Multiples) × √N
      (N = number of trades, capped at 100 in Tharp's original version)
```

**Score interpretation:**

| SQN | Quality |
|-----|---------|
| Below 1.5 | Hard to trade |
| 1.5–2.0 | Average |
| 2.0–3.0 | Good |
| 3.0–5.0 | Excellent |
| 5.0–7.0 | Super system |
| Above 7.0 | Suspicious — likely curve-fitted |

**For your system (theoretical, 20 trades at 60% win rate):**
```
Expectancy = 0.80R
Standard deviation ≈ 1.47
SQN = (0.80 ÷ 1.47) × √20 = 0.544 × 4.47 ≈ 2.43 → "Good System"
```

But with only 20 trades, this is not statistically reliable. Tharp requires minimum 30 trades before any meaningful reading, and 100+ for confidence.

---

## How Many Trades Do You Need?

| Sample | Reliability |
|--------|------------|
| < 30 trades | Essentially meaningless |
| 30–50 | Very rough signal |
| 50–100 | Developing picture |
| 100 | Tharp's minimum benchmark |
| 200+ | Statistically robust |

**At your pace:**
- 4 trades/month → 100 trades in ~25 months
- 6 trades/month → 100 trades in ~17 months
- 8 trades/month → 100 trades in ~13 months

**Implication:** Paper trade or trade at 0.5% risk while you accumulate your first 30 live trades. Do not draw conclusions about your system's quality too early.

---

## Handling Drawdowns — The Full Framework

**The asymmetry of drawdowns:**
```
10% drawdown → need +11.1% to recover
20% drawdown → need +25% to recover
50% drawdown → need +100% to recover
```

This is why preventing large drawdowns is more important than maximising returns.

**Built-in protection with percent-risk sizing:** As your account shrinks, dollar risk automatically shrinks.
```
Start: ₹1,00,000 → Risk: ₹1,000/trade
After 10 losses: ₹90,000 → Risk: ₹900/trade
After 20 losses: ₹81,817 → Risk: ₹818/trade
```

A 20-loss streak (extreme statistical outlier at 60% win rate) → only ~18% drawdown, not 20%, because each loss reduces the next position size.

**What to do during a losing streak:**

1. **Never increase position size to "make it back faster"** — fastest path to ruin
2. **Reduce risk to 0.5% per trade** if down more than 10% from your peak equity
3. **Review the system, not the losses:** ask — is the market environment different? Am I executing correctly?
4. **Define your circuit-breaker in advance:** "If I lose 20% from peak, I stop trading and review." Write this down before you start.
5. **Do not change your system after a 5-trade losing streak.** At 60% win rate, the probability of 5 consecutive losses = (0.40)^5 = 1.02% — normal and expected roughly once every 100 trades.

**Probability of consecutive losses at 60% win rate:**
```
5 in a row: 1.02% — happens roughly once per 100 trades
7 in a row: 0.16% — rare but not impossible
```

When this happens, continue executing valid setups at 1% risk. Do not change the strategy.

---

## Your Low-Risk Idea (Tharp's Highest Concept)

Tharp's definition of a "Low-Risk Idea" has three mandatory components:

1. **Positive expectancy** — proven over 30+ trades. Yours: 0.80R ✓
2. **Psychologically survivable R:R pattern** — 60% win rate, 2R reward is comfortable for most. ✓
3. **Correct position sizing** — 1% risk per trade. ✓

**Your system qualifies as a Van Tharp Low-Risk Idea.** The math is sound. The only remaining variable is behavioral execution.

---

## Growth Projection — What the Math Says

**Base case: 6 trades/month, 60% win rate, compounded:**

| Month | Equity | Monthly Gain (~4.8%) |
|-------|--------|---------------------|
| 1 | ₹1,00,000 | ₹4,800 |
| 3 | ₹1,09,830 | ₹5,272 |
| 6 | ₹1,33,000 | ₹6,400 |
| 12 | ₹1,76,000 | ₹8,450 |
| 24 | ₹3,10,000 | ₹14,900 |

**After accounting for transaction costs (~₹100/trade):**
```
Adjusted expectancy = (0.6 × ₹1,900) − (0.4 × ₹1,100)
                    = ₹1,140 − ₹440 = ₹700/trade
```

Still +0.70R — strong.

**Realistic variance:**

| Win Rate | Annual Outcome |
|---------|---------------|
| 65% | ₹1L → ~₹2.1L |
| 60% | ₹1L → ~₹1.76L |
| 55% | ₹1L → ~₹1.48L |
| 50% | ₹1L → ~₹1.25L |

---

## Honest Critiques of This Book

1. **100-trade validation takes too long** at 4–8 trades/month. Workaround: paper trade extra setups simultaneously to accumulate data faster.

2. **US and futures centric** — NSE has circuit breakers, FII flows, and gap risk that Tharp doesn't address. Use stop-loss orders on your broker immediately after entry, never mental stops.

3. **Doesn't account for correlated positions** — if two positions are in the same sector (banking), they may both stop out simultaneously on a sector-wide event. Cap total correlated exposure at 2%.

4. **Position sizing constraints on small accounts** — the formula can produce position sizes requiring more capital than you have. If capital_used > 80% of account, skip the trade or widen the stock criteria.

5. **"Financial Freedom" is a slow timeline on ₹1L** — Year 1 goal should be proving the system works, not replacing income.

---

## The Single Most Important Number to Track

**Your rolling average R-multiple across all live trades.**

- Above +0.50R after 30 trades → working system, continue
- Near 0R after 30 trades → review execution and entry quality
- Below 0R after 30 trades → system has a fundamental problem, pause and analyse

This one metric tells you more than your P&L ever will.

---
*Sources: Van Tharp Institute, TraderLion, Zerodha Varsity, QuantifiedStrategies, Edgewonk, P&L Ledger*
