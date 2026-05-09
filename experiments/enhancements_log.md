# Project Nemesis — Enhancements Log

> **Scope**: These are post-strategy enhancements — filters and ranking layers applied ON TOP of the locked Setup A config.
> The base strategy (engine.py, setup_a.py) is UNTOUCHED. All improvements here are additive.

---

## Enhancement E1: Seasonality Very-Weak Filter

**Module**: `src/enhancements/seasonality_boost.py`
**Status**: BUILT & TESTED ✅
**Decision**: Optional (confirmed improves metrics, low impact since only 11 trades affected)

### What it does
- Loads `data/sector_seasonality.csv` (built from 9 years of NSE stock + Nifty data)
- For each trade signal, looks up the `beat_nifty_pct` for that (sector, calendar month)
- Labels signals as: **Strong** (≥65%) / **Neutral** (50–64%) / **Weak** (35–49%) / **Very Weak** (<35%)
- Hard filter option: skip any signal in a "Very Weak" sector-month

### Season score tiers (from 336 locked Setup A trades)

| Tier       | Score    | Trades | WR    | Avg R   | Notes                                |
|------------|----------|--------|-------|---------|--------------------------------------|
| Strong     | ≥ 65%    | 27     | 66.7% | +0.821R | Excellent — prioritize these         |
| Neutral    | 50–64%   | 174    | 44.3% | +0.242R | Take as normal                       |
| Weak       | 35–49%   | 109    | 54.1% | +0.521R | KEEP — surprisingly good (Pharma Jan, FMCG Jun etc.) |
| Very Weak  | < 35%    | 11     | 36.4% | -0.016R | Skip — net losing, drag on portfolio |

### Backtest results (filter_very_weak=True)

| Metric               | Original (336) | Enhanced (325) | Delta     |
|----------------------|----------------|----------------|-----------|
| Positive months      | 63.1%          | **63.9%**      | +0.8%     |
| Expectancy           | 0.402R         | **0.416R**     | +0.014R   |
| SQN                  | 4.77           | **4.86**       | +0.09     |
| Total P&L            | ₹1,34,960      | ₹1,35,139      | +₹179     |
| Max drawdown         | ₹-21,021       | **₹-17,547**   | -₹3,474   |
| Max consec. red      | 5 months       | 5 months       | same      |

**Key insight**: 11 trades removed collectively lost money (net -₹179 contribution). Removing them raises expectancy and lowers max drawdown without losing P&L.

### Removed trades (the 11 Very Weak signals)

| Symbol       | Sector              | Month | Score | R      | Win  |
|--------------|---------------------|-------|-------|--------|------|
| TCS.NS       | IT                  | Apr   | 26%   | +1.98  | ✓    |
| TITAN.NS     | Consumer            | Jun   | 33%   | +1.99  | ✓    |
| HCLTECH.NS   | IT                  | Apr   | 26%   | -1.16  | ✗    |
| COALINDIA.NS | Mining              | Nov   | 30%   | -1.26  | ✗    |
| HAVELLS.NS   | Consumer Electricals| Oct   | 20%   | +1.97  | ✓    |
| SIEMENS.NS   | Capital Goods       | Jul   | 30%   | -1.08  | ✗    |
| SIEMENS.NS   | Capital Goods       | Jul   | 30%   | -1.16  | ✗    |
| BIOCON.NS    | Pharma              | May   | 34%   | +2.02  | ✓    |
| AUROPHARMA.NS| Pharma              | May   | 34%   | -1.10  | ✗    |
| ALKEM.NS     | Pharma              | May   | 34%   | -1.11  | ✗    |
| ICICIGI.NS   | Insurance           | Sep   | 19%   | -1.25  | ✗    |

Note: 4 of 11 were winners — this filter is not perfect, but the group's collective edge is negative.
Skipping 4 winners to avoid 7 losers is a good trade when net PnL impact is break-even.

### Season calendar highlights (whitelisted sectors, today = May 2026)

**Best this month (May)**:
- Capital Goods ▲ 65%
- Mining → 60%
- FMCG → 56%
- Insurance → 55%

**Avoid this month (May)**:
- Pharma ✗ 34% — Very Weak (IT results season spills over)
- Consumer Electricals ✗ 30% — Very Weak
- Energy ✗ 33% — Very Weak
- Utilities ▽ 40%

### How to use in the alerter

```python
from enhancements.seasonality_boost import score, label, should_skip, rank_signals

# In the scanner/alerter:
signals = [...]  # list of setup A signals found today
ranked  = rank_signals(signals)   # sorted by season_score desc

for sig in ranked:
    if should_skip(sig["sector"], current_month):
        continue  # drop Very Weak
    send_telegram_alert(sig)      # fire alert with season_label in message
```

---

## Enhancement E2: Strong-Season Upsize (NOT YET BUILT)

**Idea**: When a signal fires in a Strong (≥65%) sector-month, consider sizing up to 1.5R instead of 1R.
**Status**: Not tested — save for Phase 3 after live trading validates the base system.
**Risk**: Changes per-trade risk, needs separate walk-forward validation before live use.

---

## Enhancement E3: News Catalyst Layer (NOT YET BUILT)

**Idea**: Tag signals where a sector-level catalyst exists (budget, policy announcement, earnings season).
**Status**: Deferred — user deprioritized. Requires NLP/RSS feed integration.

---

## Enhancement E4: Multi-Signal Day Ranking (NOT YET BUILT)

**Idea**: On days when 3+ signals fire simultaneously, use season_score to pick top 2.
**Status**: Not tested yet. Currently the engine takes all signals (no daily cap).
**How to test**: Count days with 3+ signals in trades_final.csv, see if season score predicts the better pick.

---

## What NOT to do (from lessons learned)

- Do NOT add time exits to Setup A — they kill 76% of trades (key experiment finding)
- Do NOT use Setup B (EMA pullback) — 43.7% WR, drags performance
- Do NOT hard-filter Weak (35–49%) sector-months — these are actually profitable (54.1% WR)
- Do NOT re-run the full backtest to test enhancements — use trades_final.csv + the filter layer
