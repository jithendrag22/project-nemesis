# Sector Seasonality Analysis — Project Nemesis
> **Data source:** 9 years of NSE price data (2015–2024) × 16 whitelisted sectors  
> **Two lenses used:** (1) Historical beat-Nifty % from all stocks in each sector (2) Actual trade results from locked Setup A backtest (336 trades)

---

## How to Read This Document

- **Beat %** = how often that sector outperformed Nifty in that calendar month, over 9 years. 50% = coin flip. 65%+ = strong tailwind. Below 35% = headwind.
- **Avg Excess** = average return *above* Nifty for that sector-month (%). Positive = sector beats the index.
- **Actual WR / Avg R** = from real Setup A trades in that sector-month. The ground truth for the strategy.
- Colour legend used in tables: **▲ Strong (≥65%)** · **→ Neutral (50–64%)** · **▽ Weak (35–49%)** · **✗ Very Weak (<35%)**

---

## Part 1: Sector vs Month — Beat-Nifty % (Heat Map)

Values = % of months that sector beat Nifty. **Higher = sector was stronger than market that month.**

| Sector               | Jan  | Feb  | Mar  | Apr  | May  | Jun  | Jul  | Aug  | Sep  | Oct  | Nov  | Dec  | Best months |
|----------------------|------|------|------|------|------|------|------|------|------|------|------|------|-------------|
| **Electronics**      | →61  | ▽43  | ▽43  | →57  | →50  | →57  | ▽43  | ▲71  | **▲93**| →60  | →53  | ▲73  | Sep, Dec, Aug |
| **Capital Goods**    | →61  | **▲65**| →60  | →55  | **▲65**| →50  | ✗30  | ▽45  | ▽40  | →50  | →55  | ▽45  | Feb, May |
| **Mining**           | →56  | **▲90**| ▽40  | →60  | →60  | ▽40  | ▽40  | →50  | ▽40  | →60  | ✗30  | →50  | Feb (dominant) |
| **Consumer Electricals**| →56 | **▲80**| ▽40  | **▲70**| ✗30  | ▽40  | →50  | **▲80**| **▲70**| ✗20  | →50  | →50  | Feb, Aug, Sep, Apr |
| **Healthcare**       | →53  | →53  | ▽42  | →58  | ▽44  | →59  | **▲67**| →59  | →55  | →50  | **▲68**| ▽45  | Jul, Nov |
| **IT**               | **▲71**| →60  | →50  | ✗26  | ▽42  | ▽38  | →52  | **▲66**| ▽48  | →52  | →62  | **▲66**| Jan, Aug, Dec |
| **Insurance**        | ✗33  | ▽36  | ▽45  | →58  | →55  | →58  | **▲68**| ▽45  | ✗19  | ▽44  | ▽42  | Jul |
| **Consumer Durables**| ▽44  | →63  | →60  | ▽47  | ▽37  | ▽40  | →57  | →60  | **▲63**| →60  | ▽37  | →53  | Sep, Feb, Aug, Oct |
| **Real Estate**      | →53  | →54  | ▽44  | ▽48  | ▽42  | →58  | ▽48  | ▽48  | ▽46  | →58  | **▲64**| →60  | Nov, Dec |
| **Utilities**        | →60  | ▽49  | ▽47  | →53  | ▽40  | →54  | ▽49  | →53  | ▽46  | →52  | ▽49  | ▽47  | Jan (most consistent) |
| **FMCG**             | ▽37  | ▽48  | →60  | →54  | →56  | **▲64**| →59  | →50  | ▽48  | ▽37  | ▽43  | ▽48  | Jun, Jul, Mar |
| **Pharma**           | ▽46  | →51  | ▽49  | →59  | ✗34  | →62  | →61  | →57  | →55  | ▽48  | ▽50  | →50  | Jun, Jul |
| **Auto Ancillary**   | ▽44  | ▽48  | →55  | **▲68**| →55  | ▽45  | ▽43  | ▽35  | **▲63**| ▽45  | ▽45  | →58  | Apr, Sep |
| **Cement**           | ▽49  | →62  | ▽48  | →50  | →52  | ▽46  | →56  | ▽46  | →50  | →56  | ▽42  | ▽48  | Feb, Jul, Oct |
| **Consumer**         | ▽41  | →57  | →53  | →53  | ▽47  | ✗33  | →50  | **▲73**| →57  | ▽47  | ▽43  | **▲70**| Aug, Dec |
| **Energy**           | →52  | →53  | ▽47  | →57  | ✗33  | ▽40  | ▽47  | →50  | →57  | →57  | ▽47  | ▽43  | Apr, Sep, Oct |

---

## Part 2: Avg Excess Return vs Nifty (%)

Same table but showing **how much** the sector beat Nifty by, in percentage points.

| Sector               | Jan   | Feb   | Mar   | Apr   | May   | Jun   | Jul   | Aug   | Sep   | Oct   | Nov   | Dec   |
|----------------------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| **Electronics**      | +4.2  | +1.4  | +2.3  | +1.0  | +0.3  | +3.0  | -0.6  | **+5.7** | **+5.8** | +1.9  | +2.7  | **+5.9** |
| **Capital Goods**    | +2.2  | **+5.3** | +1.9  | +0.7  | **+4.1** | +1.2  | -2.7  | -0.2  | +0.4  | +0.0  | -0.2  | -0.7  |
| **Mining**           | +0.7  | **+5.8** | -1.2  | -0.2  | +1.7  | -3.3  | -2.7  | -0.7  | **+3.8** | +0.0  | -1.3  | -1.0  |
| **Consumer Electricals** | +1.5 | **+3.3** | +1.9  | **+2.7** | -0.5  | -1.1  | +1.4  | **+4.6** | +0.9  | -4.2  | +2.0  | +0.4  |
| **Healthcare**       | +1.4  | +1.3  | -0.9  | +1.7  | -2.7  | +2.2  | +2.3  | +2.8  | +1.4  | +0.9  | **+3.7** | -0.3  |
| **IT**               | +1.9  | +1.1  | -0.5  | -3.3  | -0.5  | -0.8  | **+2.5** | +2.0  | +1.3  | -0.2  | +0.2  | +2.2  |
| **Insurance**        | -2.1  | -0.1  | -0.9  | +1.5  | +1.2  | **+2.5** | **+4.0** | -0.8  | -2.2  | -0.6  | +0.4  | -1.0  |
| **Consumer Durables**| -0.1  | +2.6  | +2.1  | +2.0  | -1.1  | +0.1  | +1.0  | +2.7  | **+3.5** | +1.1  | -0.9  | +0.2  |
| **Real Estate**      | +1.3  | +0.4  | +0.0  | +1.7  | -0.1  | **+2.7** | +0.6  | +0.8  | **+2.7** | +1.8  | +2.1  | +2.2  |
| **Utilities**        | **+3.3** | +1.0  | +1.1  | +1.9  | -1.5  | +0.4  | -0.4  | +2.0  | +0.2  | +1.1  | +0.4  | +1.0  |
| **FMCG**             | -1.3  | +0.1  | +1.8  | +0.4  | **+2.1** | +1.6  | +0.8  | +0.8  | +0.1  | -1.6  | -0.7  | -0.1  |
| **Pharma**           | -1.2  | +0.3  | +1.5  | **+2.5** | -3.8  | +1.7  | +1.9  | +1.5  | +1.6  | -1.1  | -0.3  | +0.1  |
| **Auto Ancillary**   | -0.5  | +0.4  | -0.4  | **+4.1** | +1.4  | +0.5  | +0.5  | -2.2  | +1.0  | -0.6  | +1.3  | +1.1  |
| **Cement**           | -0.5  | +0.9  | +0.7  | +1.2  | +0.3  | -0.3  | +1.5  | -1.7  | +0.6  | +0.8  | -1.1  | -0.8  |
| **Consumer**         | -2.1  | +1.3  | +2.0  | -1.1  | -0.5  | -0.5  | +2.6  | +2.9  | +1.7  | -0.5  | -0.6  | +1.6  |
| **Energy**           | +1.5  | +1.4  | +0.7  | +1.6  | -1.1  | -0.8  | +0.0  | 0.0   | +1.9  | 0.0   | +0.3  | +0.4  |

---

## Part 3: Actual Trade Performance by Sector (336 trades, 2015–2024)

| Sector               | Trades | Win Rate | Avg R  | Total P&L | Notes                          |
|----------------------|--------|----------|--------|-----------|--------------------------------|
| **Electronics**      | 10     | **90.0%**| **+1.52R** | ₹15,159 | Best sector by far — very few signals but almost always win |
| **Cement**           | 15     | 60.0%    | +0.75R | ₹11,196   | Consistent, underrated         |
| **Consumer Durables**| 13     | 61.5%    | +0.74R | ₹9,668    | Solid mid-cap performer        |
| **Real Estate**      | 29     | 51.7%    | +0.49R | ₹14,336   | High trade count, reliable     |
| **IT**               | 21     | 52.4%    | +0.49R | ₹10,180   | Good when seasonal tailwind    |
| **Mining**           | 6      | 50.0%    | +0.43R | ₹2,553    | Very few signals               |
| **Consumer**         | 22     | 50.0%    | +0.34R | ₹7,404    | Month-dependent (Oct great, Jul terrible) |
| **FMCG**             | 39     | 46.2%    | +0.34R | ₹13,244   | High volume, Jun+May excellent |
| **Utilities**        | 51     | 47.1%    | +0.33R | ₹16,576   | Highest trade count, Jun+Aug strongest |
| **Consumer Electricals**| 8   | 50.0%    | +0.36R | ₹2,877    | Good Feb + Aug, terrible Oct   |
| **Insurance**        | 13     | 46.2%    | +0.29R | ₹3,718    | Jul is best, Sep terrible      |
| **Energy**           | 18     | 44.4%    | +0.29R | ₹5,155    | Jan + Feb + Jul work           |
| **Healthcare**       | 17     | 47.1%    | +0.22R | ₹3,741    | Jul + Nov; Feb is terrible     |
| **Capital Goods**    | 11     | 45.5%    | +0.22R | ₹2,379    | Fewer trades than expected     |
| **Auto Ancillary**   | 21     | 42.9%    | +0.21R | ₹4,338    | Apr + Nov strong; Aug + Sep avoid |
| **Pharma**           | 42     | 47.6%    | +0.30R | ₹12,436   | Jan + Jul great; Sep catastrophic |

---

## Part 4: The Star Sector-Month Combos (Actual Trades ≥2)

Ranked by Avg R — these are the high-conviction windows to be aggressive:

| Rank | Sector                | Month | Trades | Win Rate | Avg R  | Total P&L | Reliability |
|------|----------------------|-------|--------|----------|--------|-----------|-------------|
| 1    | **FMCG**             | **May**   | 5      | 100%     | +2.06R | ₹10,302   | ⭐⭐⭐ |
| 2    | **FMCG**             | **Oct**   | 2      | 100%     | +2.15R | ₹4,293    | ⭐⭐ (small n) |
| 3    | **Electronics**      | **Jul**   | 2      | 100%     | +1.99R | ₹3,970    | ⭐⭐ (small n) |
| 4    | **Energy**           | **Feb**   | 2      | 100%     | +1.95R | ₹3,900    | ⭐⭐ (small n) |
| 5    | **Auto Ancillary**   | **Nov**   | 2      | 100%     | +1.90R | ₹3,797    | ⭐⭐ (small n) |
| 6    | **Cement**           | **May**   | 2      | 100%     | +1.86R | ₹3,719    | ⭐⭐ (small n) |
| 7    | **Electronics**      | **Aug**   | 2      | 100%     | +1.76R | ₹3,525    | ⭐⭐ (small n) |
| 8    | **Electronics**      | **Dec**   | 2      | 100%     | +1.58R | ₹3,151    | ⭐⭐ (small n) |
| 9    | **Pharma**           | **Jul**   | 8      | **87.5%**| **+1.46R** | ₹11,692 | ⭐⭐⭐ (high n) |
| 10   | **Pharma**           | **Jan**   | 6      | 83.3%    | +1.39R | ₹8,320    | ⭐⭐⭐ (high n) |
| 11   | **Utilities**        | **Aug**   | 4      | 75.0%    | +1.29R | ₹5,152    | ⭐⭐⭐ |
| 12   | **Utilities**        | **Jun**   | 4      | 75.0%    | +1.28R | ₹5,111    | ⭐⭐⭐ |
| 13   | **Consumer**         | **Oct**   | 4      | 75.0%    | +1.18R | ₹4,715    | ⭐⭐⭐ |
| 14   | **FMCG**             | **Jun**   | 7      | 71.4%    | +1.05R | ₹7,343    | ⭐⭐⭐ (high n) |
| 15   | **Real Estate**      | **Jul**   | 3      | 66.7%    | +1.02R | ₹3,071    | ⭐⭐ |

> **High-confidence** = ≥4 trades + ≥65% WR + ≥+1.0R. That gives: Pharma Jul, Pharma Jan, Utilities Aug/Jun, Consumer Oct, FMCG May/Jun.

---

## Part 5: The Danger Zones — Worst Sector-Month Combos

Sector-months to either skip entirely or size down significantly:

| Sector      | Month | Trades | Win Rate | Avg R    | Reason to avoid                        |
|-------------|-------|--------|----------|----------|----------------------------------------|
| **Pharma**  | Sep   | 10     | **10%**  | **-0.80R** | Q2 results disappoint + export concerns |
| **Consumer**| Jul   | 6      | 0%       | -1.14R   | Monsoon slowdown + pre-results caution  |
| **Utilities**| Sep  | 5      | 20%      | -0.60R   | Monsoon winding down, demand uncertain  |
| **Utilities**| Apr  | 5      | 20%      | -0.64R   | Post-election uncertainty              |
| **Healthcare**| Feb | 5      | 20%      | -0.62R   | Q3 results weak, FDA warning seasons   |
| **Energy**  | Nov   | 2      | 0%       | -1.24R   | Post-Diwali demand slowdown            |
| **Energy**  | Apr   | 3      | 0%       | -0.89R   | Summer demand priced in already        |
| **Cement**  | Jul   | 3      | 0%       | -1.03R   | Monsoon kills construction activity    |

---

## Part 6: Sector Deep Dives — Consistency + Reasons

---

### Electronics ⭐ (Best sector, 90% actual WR)

**Seasonal pattern:** Strong Sep–Dec window. Weak Feb–Mar.

| Month | Beat % | Excess Ret | Actual Trades | Actual WR |
|-------|--------|-----------|---------------|-----------|
| Sep   | **93%**| +5.8%     | —             | —         |
| Dec   | **73%**| +5.9%     | 2             | 100%      |
| Aug   | **71%**| +5.7%     | 2             | 100%      |
| Jul   | 43%    | -0.6%     | 2             | 100% (small sample) |
| Feb   | 43%    | +1.4%     | —             | —         |

**Why Electronics is strong Sep–Dec:**
- **Festive season demand** (Sep–Nov): Navratri, Dussehra, Diwali drive massive consumer electronics buying — TVs, smartphones, home appliances. Companies pre-build inventory and guide up.
- **Q2 results** (Oct): Electronics companies report Q2 (Jul–Sep) results in Oct — benefiting from festive pre-stocking. Revenue guidance upgrades are common.
- **Year-end export orders** (Dec): Export-focused electronics firms get Q3 (Jan–Mar) order books loaded in Dec — visibility into next quarter is high.
- **Why Sep is the dominant month:** Advance orders + inventory buildup for Diwali = full-quarter visible demand. Fund managers rotate into electronics ahead of festive results.

---

### Pharma — Split personality (Best Jan+Jul, catastrophic Sep)

**Seasonal pattern:** Strong Jan, Jun, Jul. Catastrophic Sep (10% WR, -0.80R over 10 trades).

| Month | Beat % | Excess Ret | Actual Trades | Actual WR | Avg R   |
|-------|--------|-----------|---------------|-----------|---------|
| Jan   | 46%    | -1.2%     | 6             | **83.3%** | **+1.39R** |
| Jul   | 61%    | +1.9%     | 8             | **87.5%** | **+1.46R** |
| Jun   | 62%    | +1.7%     | 6             | 66.7%     | +0.80R  |
| Sep   | 55%    | +1.6%     | 10            | **10%**   | **-0.80R** |

**Why January is exceptional for Pharma:**
- **Union Budget expectations** (Feb 1 each year): Ahead of the Budget, healthcare allocation speculation drives pharma stocks. Domestic pharma stocks with rural distribution benefit most.
- **Q3 results** (Jan): Pharma reports Oct–Dec quarter. Winter seasonal demand (cold/flu, cardiac, respiratory) is already visible in sales numbers.
- **US FDA approvals calendar**: New drug applications filed in Sep typically get responses in Dec–Jan. Positive responses trigger strong stock moves.

**Why July is exceptional:**
- **Q1 results** (Jul): Apr–Jun is monsoon preparation + summer illness season (gastro, fever). Strong domestic formulation revenue.
- **US generics filing season**: Companies file ANDA applications to US FDA in H1. Q1 results guidance on US filings tends to be positive.
- **Monsoon = rural demand**: Rural India buys ORS, antidiarrheals, antiparasitics in Jul. Domestic pharma sales peak.

**Why September is a disaster for Pharma:**
- **US FDA warning letters**: Historically, US FDA plant inspections cluster in the June–August window. Warning letters land in Aug–Sep, triggering 10–30% single-day drops.
- **Q2 results fear** (Oct): Sep is the last month of Q2. Any Q2 earnings risk gets priced in via selling.
- **Dollar headwinds**: USD/INR often stabilizes or reverses post-Diwali, hurting export-heavy pharma in Sep.
- **Data point**: 10 actual trades in Sep Pharma with a 10% WR and -0.80R avg. This is not noise — this is structural.

**Rule: Never trade Pharma in September.**

---

### FMCG — Summer months dominate

**Seasonal pattern:** May + Jun + Oct are elite. Jan + Sep + Oct are weak.

| Month | Beat % | Excess Ret | Actual Trades | Actual WR | Avg R   |
|-------|--------|-----------|---------------|-----------|---------|
| May   | 56%    | +2.1%     | 5             | **100%**  | **+2.06R** |
| Jun   | **64%**| +1.6%     | 7             | 71.4%     | **+1.05R** |
| Oct   | 37%    | -1.6%     | 2             | 100%      | +2.15R (small n) |
| Jan   | 37%    | -1.3%     | 4             | 25%       | -0.53R  |
| Sep   | 48%    | +0.1%     | 4             | 25%       | -0.22R  |

**Why May–Jun is the golden window for FMCG:**
- **Pre-monsoon stocking** (May): Distributors across rural India build inventory before monsoon disrupts supply chains. FMCG companies report high primary sales in Apr-May.
- **Summer consumption peak**: Beverages, cooling products, skin care peak in Apr–Jun. Categories like juices, ORS, sunscreen, hair oil drive revenue upside.
- **Wedding season** (May–Jun): Mass market FMCG (biscuits, personal care, snacks) benefits from wedding-driven bulk demand.
- **Q4 results** (May): Jan–Mar quarter results for FMCG are released in May. Rural FMCG typically has a solid Q4 (Holi, harvest season, rabi crop income).
- **Fund inflows**: FMCG is a defensive favorite. As Q1 begins, institutional money often rotates into defensives in May–Jun before Q1 earnings uncertainty.

**Why January is weak for FMCG:**
- Post-Diwali destocking: Channel inventory from festive season is high. January sees lower primary sales as distributors work through festive overhang.
- Urban demand slows in Jan (winter, lower discretionary spend).

---

### Capital Goods — Budget play (Feb + May)

**Seasonal pattern:** Feb and May are peak. July is the worst month.

| Month | Beat % | Excess Ret |
|-------|--------|-----------|
| Feb   | **65%**| **+5.3%** |
| May   | **65%**| **+4.1%** |
| Jan   | 61%    | +2.2%     |
| Jul   | **30%**| **-2.7%** |

**Why Feb is the best month for Capital Goods:**
- **Union Budget** is presented on Feb 1. Capital expenditure allocations for railways, defence, roads, power, and manufacturing PLI schemes are announced. Capital goods stocks re-rate immediately.
- **Government tender season**: Ministry budgets get finalized post-Budget. Companies start getting order inflow confirmations in Feb.
- **Q3 results** (Jan): Capital goods companies report a strong Jan-end quarter driven by H2 government ordering cycles.

**Why May is also strong:**
- **Q4 results** (May): Jan–Mar is the final quarter of the Indian fiscal year (Apr–Mar). Government departments rush to utilise remaining capex budgets in Q4. Capital goods companies see an order execution surge. May results reflect this.
- **New government budget cycle starts**: Apr 1 is start of new fiscal. Government order books are typically reset and new spending gets approved in May.

**Why July is the worst:**
- **Monsoon stalls execution**: Construction, infrastructure execution slows sharply in Jul–Sep monsoon months.
- **Q1 results fear**: Apr–Jun is the slowest quarter for capital goods (monsoon starts, new fiscal year starts slowly, government procurement slow).

---

### IT — Jan window and festive tailwind. April is lethal.

**Seasonal pattern:** Jan, Aug, Dec are best. April is catastrophically weak (26% beat rate).

| Month | Beat % | Excess Ret | Actual Trades | Actual WR |
|-------|--------|-----------|---------------|-----------|
| Jan   | **71%**| +1.9%     | —             | —         |
| Aug   | **66%**| +2.0%     | —             | —         |
| Dec   | **66%**| +2.2%     | —             | —         |
| Apr   | **26%**| **-3.3%** | 2             | 50%       |

**Why January is the best month for IT:**
- **US enterprise budget cycles reset** on Jan 1. CIOs release new IT spend approvals. Indian IT companies get deal win announcements in Jan–Feb.
- **Q3 results** (Jan): Oct–Dec is a strong quarter for Indian IT because US enterprise spending is front-loaded to Q3 (calendar Q4 for clients). Results and guidance are typically positive.
- **Analyst upgrades**: After Dec guidance events, IT analyst reports are bullish going into Jan.

**Why August is strong:**
- **Q1 results** (Jul–Aug): Apr–Jun quarter results come out in Jul. US client IT budgets are in full execution by Q2. Guidance upgrades common.
- **Dollar strength in Aug**: Historically, USD strengthens in Aug–Sep, boosting INR revenue for IT exporters.

**Why April is the worst month:**
- **Q4 results fear** (Apr): Indian IT companies report Jan–Mar (Q4) results in Apr. This quarter includes US holiday slowdown (Dec–Jan) and Indian year-end billing cycle confusion. Q4 results frequently disappoint vs estimates.
- **Client budget uncertainty**: US enterprises finalising new CY budgets in Jan–Feb means actual deal execution slows until confirmed. April is the first full quarter of uncertainty.
- **Visa season**: H1-B lottery results come in Mar–Apr. Negative outcomes create overhang.
- **Data point**: 26% beat rate, -3.3% excess return. This is one of the most reliably weak sector-month combos in the dataset.

**Rule: Be very cautious trading IT in April.**

---

### Utilities — Monsoon paradox (Jun + Aug best despite being "wet months")

**Seasonal pattern:** Jun and Aug are elite. Apr and Sep are terrible.

| Month | Actual Trades | Actual WR | Avg R   |
|-------|---------------|-----------|---------|
| Jun   | 4             | **75%**   | **+1.28R** |
| Aug   | 4             | **75%**   | **+1.29R** |
| Nov   | 3             | 67%       | +0.92R  |
| Feb   | 3             | 67%       | +0.99R  |
| Sep   | 5             | 20%       | -0.60R  |
| Apr   | 5             | 20%       | -0.64R  |

**Why Jun + Aug work for Utilities (counterintuitive):**
- **Power demand peaks in pre-monsoon summer** (Apr–Jun). Utilities companies report record generation in May–Jun. Q4 results (May) and Q1 guidance (Jun–Aug) are strong.
- **Monsoon rainfall boosts hydro**: Above-average rainfall in Jul–Sep means hydro power generation is high and cheap. Thermal utilities also benefit as coal procurement is easier (no road disruption).
- **Renewable energy commissioning**: Wind power generation peaks in Jun–Sep. Wind energy companies see maximum revenue in this period.
- **Defensive rotation**: When markets get volatile (May sell-offs, post-Budget correction), funds rotate to defensive Utilities, creating momentum.

**Why September is weak despite monsoon:**
- Monsoon ends, demand outlook for winter is uncertain.
- Q2 results (Oct) guidance tends to be cautious — thermal plants can't always sustain peak-summer run rates in Q2.

---

### Consumer (Discretionary) — Festive season is king

**Seasonal pattern:** October is dominant. July is catastrophic.

| Month | Beat % | Actual Trades | Actual WR | Avg R   |
|-------|--------|---------------|-----------|---------|
| Oct   | 47%    | 4             | **75%**   | **+1.18R** |
| Aug   | **73%**| —             | —         | —       |
| Dec   | **70%**| —             | —         | —       |
| Jul   | 50%    | 6             | **0%**    | **-1.14R** |

**Why October is the best month for Consumer:**
- **Navratri + Dussehra + Diwali** all fall in Oct or straddle Sep–Nov. Consumer spending reaches annual peaks.
- **Premiumisation**: Urban consumers upgrade in festive season — premium TVs, appliances, branded clothes, jewellery. Consumer discretionary companies have strongest quarterly revenue in Q2 (Jul–Sep) and Q3 (Oct–Dec).
- **Salary season**: Diwali bonuses, annual increments effective Oct, and government DA increases all land in Oct quarter.

**Why July is a graveyard:**
- **Monsoon dampens sentiment**: Physical retail slows. Consumers defer big purchases.
- **No catalyst**: There are no major holidays, no results, no policy events in July for pure discretionary.
- **Data point**: 6 actual trades, 0% win rate, -1.14R average. Do not trade Consumer in July.

---

### Insurance — July window only

**Seasonal pattern:** July is the only reliable month. Sep is the worst.

| Month | Beat % | Excess Ret | Actual Trades | Actual WR | Avg R   |
|-------|--------|-----------|---------------|-----------|---------|
| Jul   | **68%**| **+4.0%** | 3             | 67%       | +0.96R  |
| Jun   | 58%    | +2.5%     | 3             | 67%       | +0.90R  |
| Sep   | **19%**| **-2.2%** | —             | —         | —       |
| Jan   | 33%    | -2.1%     | —             | —         | —       |

**Why July works for Insurance:**
- **Q1 results** (Jul): Apr–Jun is the first quarter of insurance companies' fiscal. New premium collections are highest in H1 (Jan–Jun) because ULIP investors tend to invest at year-start. Q1 results beat consensus regularly.
- **Monsoon = life insurance catalyst**: Monsoon season paradoxically increases awareness of mortality and accident risk, driving term plan and health insurance purchases.
- **Group health insurance renewal**: Corporate health insurance policies renew in Apr–Jun. Companies report strong group premium growth in Q1 results.

---

### Mining — February is the anomaly (90% beat rate)

**Seasonal pattern:** February is dominant. November is the worst.

| Month | Beat % | Excess Ret |
|-------|--------|-----------|
| Feb   | **90%**| **+5.8%** |
| Apr   | 60%    | -0.2%     |
| Oct   | 60%    | +0.0%     |
| Nov   | **30%**| -1.3%     |

**Why February is exceptional for Mining:**
- **Union Budget coal and steel royalty policy**: Mining (primarily Coal India + PSU mining) stocks react strongly to Budget announcements around royalty rates, coal block allocations, and green energy transition pace.
- **Q3 results** (Jan): Oct–Dec quarter sees maximum coal dispatching (winter power demand). Coal India typically reports strong Q3, guiding up for Q4.
- **Capital allocation announcements**: Mining companies announce dividend and capex plans in Feb after finalising annual numbers.
- **Note**: Mining sector has only 9–10 stocks in the universe, so sample size is small. The 90% beat rate in Feb is based on 10 observations.

---

## Part 7: Monthly Calendar Summary (All 16 Whitelisted Sectors)

Which months are generally strong or weak for the strategy as a whole:

| Month | Avg Beat % | Avg Excess Ret | Character               | Best sectors to focus on    |
|-------|-----------|----------------|-------------------------|-----------------------------|
| **Jan** | 51.1%   | +0.62%         | Neutral, selective      | IT, Capital Goods, Utilities |
| **Feb** | **56.9%**| **+1.65%**     | **Best month overall**  | Mining, Consumer Electricals, Capital Goods |
| **Mar** | 48.9%   | +0.75%         | Slightly weak, selective| FMCG, Auto Ancillary        |
| **Apr** | **54.6%**| +1.16%         | Second best             | Auto Ancillary, Consumer Electricals, Pharma |
| **May** | 46.3%   | -0.04%         | Marginal, stock-specific| FMCG (exceptional), Capital Goods, Mining |
| **Jun** | 49.1%   | +0.57%         | Selective               | FMCG, Real Estate, Utilities, Pharma |
| **Jul** | 51.2%   | +0.79%         | Selective — mixed bag   | Healthcare, Insurance, Pharma, Energy |
| **Aug** | **55.6%**| **+1.26%**     | **Third best month**    | Electronics, Consumer Electricals, Consumer, Utilities |
| **Sep** | 53.1%   | **+1.52%**     | **High avg but volatile** | Electronics (93%), Auto Ancillary — but avoid Pharma, Utilities, Insurance |
| **Oct** | 49.6%   | -0.08%         | Mixed, festive hope     | Consumer, FMCG (selective), Real Estate |
| **Nov** | 48.8%   | +0.48%         | Below average           | Real Estate, Healthcare, IT |
| **Dec** | 53.0%   | +0.70%         | Moderate positive       | Electronics, Consumer, IT, Real Estate |

**Bottom line on months:**
- **Feb, Apr, Aug** are the three most consistently positive months across sectors
- **May, Nov, Mar** are the three weakest overall — not necessarily bad, but need more selectivity
- **September** is interesting — high average but massive variance (Electronics 93%, Insurance 19%)

---

## Part 8: Strategic Playbook

### Trade with confidence (high-conviction windows)

| Window | Primary Sectors | Why |
|--------|----------------|-----|
| **Jan–Feb** | IT, Capital Goods, Mining | Budget season, US IT cycle reset, Q3 results strong |
| **May–Jun** | FMCG, Utilities, Pharma | Pre-monsoon stocking, summer demand, festive prep |
| **Jul–Aug** | Pharma, Electronics, Utilities, Insurance | Q1 results, festive pre-build, IT export tailwind |
| **Sep** | Electronics only | Festive stocking peak — but avoid Pharma, Insurance, Utilities |
| **Oct–Nov** | Consumer, Real Estate, IT, Healthcare | Festive season, Q2 results, defensive inflows |

### Always avoid (hard rules from data)

| Combination | Win Rate | Avg R | Why |
|-------------|----------|-------|-----|
| Pharma in Sep | 10% | -0.80R | US FDA warning letter season |
| Consumer in Jul | 0% | -1.14R | Monsoon + no catalyst |
| IT in Apr | — | — | Q4 results fear, H1-B overhang |
| Utilities in Apr/Sep | 20% | -0.60R | Season transitions, no demand clarity |
| Energy in Nov | 0% | -1.24R | Post-Diwali demand slowdown |
| Healthcare in Feb | 20% | -0.62R | Q3 results + FDA warning season |

### Current month (May 2026) — what to focus on

**Good this month:**
- FMCG ▲ (historically 100% WR in actual trades — pre-monsoon stocking, Q4 results)
- Capital Goods → 65% beat rate — infrastructure budget execution season
- Mining → 60% beat rate

**Avoid this month:**
- Pharma ✗ 34% beat rate — Very Weak
- Consumer Electricals ✗ 30% — Very Weak
- Energy ✗ 33% — Very Weak
- Utilities ▽ 40% — Below average, only take very high-quality setups

---

## Appendix: Data Quality Notes

- **Observation counts**: Pharma has the most data (1,228 obs), Mining and Consumer Electricals the least (~119). Be more cautious reading Mining/Consumer Electricals signals.
- **Actual trades are sparse**: Some sector-month combos have only 2 trades. Treat those as directional hints, not statistical facts. Focus on combos with 4+ actual trades.
- **Beat % ≠ Win Rate**: The beat % is computed from all stocks in the sector (50 Pharma stocks × 9 years = 450 data points). Actual trade Win Rate is from specific Setup A signals — far fewer data points but directly applicable to the strategy.
- **The data agrees where it matters most**: Pharma Jul (beat% 61%, actual WR 87%), FMCG Jun (beat% 64%, actual WR 71%), IT Apr (beat% 26%, actual WR 50%) — the macro seasonality and actual trade results are directionally consistent.
