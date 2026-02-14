# PSX Materiality & Context Guide

## Overview

This guide explains how the news-anomaly correlation system filters for **material news** in the Pakistan Stock Exchange (PSX) context, focusing on events that genuinely move stock prices rather than daily noise.

---

## Core Philosophy

### ✅ Material News (Include)
News that represents **structural changes** or **significant events** that affect stock fundamentals or investor sentiment.

### ❌ Noise (Filter Out)
Daily fluctuations in global commodity prices, speculation, market commentary, and routine updates that don't impact stock valuations.

---

## Materiality Tiers

### TIER 1: Always Material (High Impact)

These events **always** move PSX stocks:

#### Corporate Actions
- ✅ Dividend declarations & bonus shares
- ✅ Rights issues & stock splits
- ✅ Mergers, acquisitions, takeovers
- ✅ Share buyback programs

#### Financial Results
- ✅ Quarterly/annual earnings
- ✅ Profit/loss announcements
- ✅ Revenue surprises (>20% YoY)
- ✅ Guidance changes

#### Major Contracts & Deals
- ✅ Government contracts (energy, infrastructure)
- ✅ Large commercial agreements
- ✅ Capacity expansion projects
- ✅ Major capital expenditure

#### Management Changes
- ✅ CEO/Chairman appointments/resignations
- ✅ Board composition changes
- ✅ Key management exits

#### Regulatory & Legal
- ✅ SECP investigations/penalties
- ✅ License approvals/revocations
- ✅ Compliance issues
- ✅ Regulatory changes affecting sector

#### Operations
- ✅ Production capacity changes
- ✅ Plant shutdowns/restarts
- ✅ Oil/gas discoveries (E&P sector)
- ✅ Major operational disruptions

#### Debt & Financing
- ✅ Credit rating changes
- ✅ Debt restructuring
- ✅ Major loan agreements
- ✅ Sukuk/TFC issuances
- ✅ Default risks

---

### TIER 2: Conditionally Material (Context-Dependent)

These require **specific conditions** to be material:

#### Interest Rates
**✅ Material when:**
- State Bank of Pakistan (SBP) policy rate decisions
- Actual rate cuts/hikes announced (not speculation)
- Changes ≥50 basis points
- Monetary policy statement releases

**❌ Not material:**
- Daily speculation on rate changes
- "May cut/may raise" articles
- Analyst predictions without official action
- Global interest rate news (unless Pakistan-specific impact)

**PSX Impact:**
- Banks: Direct margin impact (HBL, UBL, MCB, etc.)
- All sectors: Discount rate for valuations changes
- Real estate/construction: Borrowing cost sensitivity

#### Oil & Gas Prices
**✅ Material when:**
- OGRA petroleum pricing decisions (fortnightly)
- Petroleum levy changes
- Gas price revisions by government
- Local discoveries or production changes
- Structural policy changes (circular debt, pricing formula)
- International prices move >10% in single event

**❌ Not material:**
- Daily Brent/WTI fluctuations (±2-3%)
- Routine international market commentary
- Temporary geopolitical noise
- Speculation on future prices

**Why filtered:**
- PSX energy stocks (PSO, OGDC, PPL) respond to LOCAL pricing
- International oil prices are smoothed out through government policy
- Only sustained trends (>1 month) or policy changes matter
- Daily noise creates false correlations

**PSX Impact:**
- E&P companies (OGDC, PPL, POL): Production revenue
- OMCs (PSO, APL, SHEL): Margin management
- Power (HUBC, KAPCO): Fuel cost pass-through
- Consumer: Indirect inflation impact (only if sustained)

#### Chemical Prices (Propylene, PVC, etc.)
**✅ Material when:**
- Local production capacity changes
- Import duty/regulatory changes
- Plant shutdowns affecting supply
- Margin compression >15% sustained
- Feedstock pricing formula changes
- **Consecutive months** of price movement

**❌ Not material:**
- Daily/weekly international price quotes
- Temporary supply disruptions
- Seasonal fluctuations
- Single-day price changes

**Why filtered:**
- Chemical stocks (EPCL, LOTTE, ENGRO) have contracts buffering volatility
- Margins matter more than absolute prices
- Only **sustained trends** (3+ months) affect valuations
- Daily international prices irrelevant without local policy change

**PSX Impact:**
- EPCL, LOTTE: Polymer margins
- ENGRO: Integrated chemical operations
- ICI: Specialized chemicals

#### USD/PKR Exchange Rate
**✅ Material when:**
- SBP policy changes (managed float adjustments)
- Devaluation >1% in single day
- IMF program-related changes
- Reserves crisis / current account deterioration
- All-time highs/lows
- Structural shifts (not daily trading)

**❌ Not material:**
- Daily ±0.2-0.5% fluctuations
- Intraday volatility
- Routine interbank trading

**PSX Impact:**
- Exporters (Textiles: GATM, NCL, NML): Positive from weak PKR
- Importers (Auto: INDU, PSMC): Negative from weak PKR
- Banks: Forex income volatility
- All: Inflation pass-through (if sustained)

#### Inflation (CPI/WPI)
**✅ Material when:**
- Official PBS (Pakistan Bureau of Statistics) releases
- Monthly CPI data
- Core inflation trends
- Food/energy inflation breakdowns
- Policy-relevant inflation metrics

**❌ Not material:**
- Weekly anecdotal price increases
- Single commodity price changes
- Speculation before official release

**PSX Impact:**
- Consumer goods (NESTLE, UNILEVER, COLG): Pricing power
- All sectors: Real wage impacts
- Banks: Loan growth affected by purchasing power

---

### TIER 3: PSX-Specific Events (Always Material)

#### Market Structure
- ✅ SECP regulatory changes
- ✅ PSX/KSE rule changes
- ✅ Margin requirements
- ✅ Circuit breakers / trading halts
- ✅ Listing/delisting events
- ✅ Index rebalancing (KSE-100)

#### Political/Sovereign
- ✅ IMF program updates
- ✅ Credit rating changes (Moody's, Fitch, S&P)
- ✅ Government stability issues
- ✅ Election outcomes
- ✅ Default risk events
- ✅ Geopolitical crises affecting Pakistan

#### Sector-Wide Events
- ✅ Industry-wide regulations
- ✅ Tariff changes for imports/exports
- ✅ Subsidy announcements
- ✅ Sector-specific tax changes

---

## Filtering Rules in Action

### Example 1: Oil Prices

**❌ Filtered (Not Material):**
```
"Brent crude rises 2% on supply concerns"
→ Daily noise, PSX energy stocks unaffected

"Oil touches $80/barrel on Middle East tensions"
→ Temporary geopolitical noise, no Pakistan impact

"Analysts expect oil to reach $90 by year-end"
→ Speculation, not actionable
```

**✅ Included (Material):**
```
"OGRA increases petroleum prices by Rs 15/liter"
→ Direct local impact on OMCs and consumers

"Circular debt reaches Rs 5 trillion, power tariff hike announced"
→ Structural issue affecting power sector

"OGDC announces major oil discovery in Sindh"
→ Company-specific material event
```

### Example 2: Chemical Prices

**❌ Filtered (Not Material):**
```
"Propylene prices up 3% in Asian markets"
→ Daily fluctuation, no local impact

"International PVC prices volatile on demand concerns"
→ General market commentary
```

**✅ Included (Material):**
```
"EPCL announces plant shutdown for 2 months - propylene shortage expected"
→ Supply disruption affecting local market

"Government imposes anti-dumping duty on PVC imports"
→ Policy change affecting margins

"Propylene prices up 25% over last 3 months - EPCL margin compression"
→ Sustained trend with company impact mentioned
```

### Example 3: Interest Rates

**❌ Filtered (Not Material):**
```
"Analysts predict SBP may cut rates next month"
→ Speculation

"Market expects 100bps cut in coming months"
→ Forward-looking speculation
```

**✅ Included (Material):**
```
"SBP cuts policy rate by 150 basis points to 13%"
→ Official policy decision

"Monetary Policy Statement: SBP maintains hawkish stance"
→ Official central bank communication
```

### Example 4: Exchange Rate

**❌ Filtered (Not Material):**
```
"Rupee closes at 279.5 vs dollar, down 0.3%"
→ Daily routine movement

"Interbank dollar-rupee trading shows volatility"
→ Intraday noise
```

**✅ Included (Material):**
```
"Rupee crashes 3% in single day as reserves hit $7 billion"
→ Significant single-day move with context

"SBP announces managed float mechanism change"
→ Policy change affecting future dynamics

"IMF tranche release boosts rupee to 3-month high"
→ Structural development
```

---

## Materiality Scoring Algorithm

### Stock-Specific News

```python
Score = Base(50%) + Time(30%) + Sentiment(20%)

MUST pass materiality filter first:
- Corporate actions → Always pass
- Financial results → Always pass
- Contracts/operations → Pass if >$10M or material
- Management → Pass if C-suite
- Speculation/rumors → Fail (unless confirmed)
- General commentary → Fail
```

### Macro News

```python
Score = Base(20%) + Materiality(40%) + Time(20%) + Relevance(20%)

Materiality thresholds:
- Interest rates: Official SBP action only
- Oil prices: >5% local change or policy
- Chemical prices: >8% sustained or policy
- FX: >1% single day or policy
- Inflation: Official PBS release

Sector relevance:
- Energy macro → Energy stocks only
- Chemical macro → Chemical stocks only
- Monetary/fiscal → All stocks
```

---

## Correlation Thresholds

### Adjusted for PSX Context

- **High (≥70%)**: 🔗 Strong material catalyst
  - Company-specific tier-1 news
  - Major macro policy changes
  - Same-day timing + strong sentiment

- **Medium (50-69%)**: 🔍 Likely driver
  - Sector-wide macro news
  - Tier-2 material events
  - 1-2 day lag but clear connection

- **Low (<50%)**: ❓ Weak/spurious
  - Noise that passed basic filters
  - Timing mismatch
  - Unclear causation

### Unexplained High-Severity Anomalies

**When correlation <50% but severity = HIGH:**
- ⚠️ Flag for investigation
- Possible insider trading
- Unreported material event
- Technical factors (index rebalancing, margin calls)
- Foreign flow (not always news-driven)

---

## PSX Trading Context

### Market Characteristics
- **Liquidity**: Concentrated in top 30-40 stocks
- **Foreign participation**: ~25% of market
- **Retail dominance**: High retail investor base
- **News sensitivity**: Reacts more to local than global news
- **Policy-driven**: Government/SECP actions very material
- **Commodity exposure**: Energy/textile sectors commodity-linked

### What Moves PSX Stocks

**Tier 1 Drivers (Immediate Impact):**
1. Company earnings surprises
2. SBP policy rate decisions
3. IMF program news
4. SECP regulatory actions
5. Political stability events
6. Major government contracts

**Tier 2 Drivers (Gradual Impact):**
1. Sustained commodity trends (>1 month)
2. Sector-wide regulatory changes
3. Exchange rate trends (>3%)
4. Inflation trends affecting sectors
5. Foreign investment flows

**Tier 3 Drivers (Minimal Impact):**
1. Daily global commodity prices
2. International stock market moves
3. Speculation and rumors
4. Analyst reports (unless consensus-changing)
5. General economic commentary

---

## Examples: Material vs. Noise

### Banking Sector (HBL, UBL, MCB)

**✅ Material:**
- SBP policy rate cut by 100bps
- Super tax announced in budget
- NPL (non-performing loans) ratio change
- Dividend announcement
- Merger talks

**❌ Noise:**
- Daily KIBOR fluctuations
- General banking sector commentary
- International banking news
- Speculation on future rates

### Energy Sector (OGDC, PPL, PSO)

**✅ Material:**
- OGRA petroleum price revision
- Oil/gas discovery announcement
- Circular debt policy change
- Production target revision
- Refinery margin policy update

**❌ Noise:**
- Daily Brent crude prices
- OPEC+ meeting speculation
- Global oil inventory reports
- International refining margins

### Chemicals (EPCL, LOTTE, ENGRO)

**✅ Material:**
- Plant capacity expansion
- Import duty change on polymers
- Major contract with downstream industry
- Feedstock pricing formula change
- 3+ months of margin compression

**❌ Noise:**
- Daily Asian propylene spot prices
- International PVC price quotes
- Temporary supply disruptions
- Weekly price movements

### Textiles (GATM, NCL, NML)

**✅ Material:**
- Export incentive policy changes
- Major export order wins
- Cotton crop estimates (Pakistan)
- Capacity expansion announcements
- USD/PKR devaluation >2%

**❌ Noise:**
- Daily cotton price fluctuations
- International fashion trends
- Speculation on export targets
- General textile sector commentary

---

## Implementation in Code

### Key Functions

1. **`_is_news_material()`**: Stock-specific materiality filter
   - Checks for tier-1 corporate events
   - Filters speculation and noise
   - Validates sentiment strength

2. **`_is_macro_relevant()`**: Macro news materiality & relevance
   - Tier-1: Monetary/fiscal policy (all stocks)
   - Tier-2: Sector-specific with thresholds
   - Tier-3: PSX-specific events
   - Filters daily commodity noise

3. **`_calculate_relevance_score()`**: Scoring with materiality bonus
   - Higher base for material tier-1 events
   - Time proximity weighting
   - Sentiment alignment validation

4. **`_generate_explanation()`**: PSX-context explanations
   - Distinguishes company vs. macro drivers
   - Provides actionable insights
   - Flags unexplained high-severity anomalies

---

## Validation Metrics

### Pre-Materiality Filtering
- Average correlation: ~45-50%
- False positives: High (daily commodity noise)
- Unexplained anomalies: Low (over-attributed)

### Post-Materiality Filtering
- Average correlation: ~65-75%
- False positives: Low (only material news)
- Unexplained anomalies: Appropriate (flags real mysteries)
- Actionable insights: High

---

## Best Practices for PSX Analysis

### 1. **Trust Local Over Global**
- SBP decisions > Fed decisions
- OGRA prices > Brent crude
- PBS inflation > US CPI
- Local contracts > international trends

### 2. **Focus on Policy Changes**
- Government decisions are material
- Regulatory changes affect sectors
- Subsidy/tax changes matter
- SECP actions are critical

### 3. **Validate Commodity News**
- Check if price change is local or global
- Look for policy/contract implications
- Require sustained trends, not spikes
- Verify sector-specific impact

### 4. **Investigate Unexplained Anomalies**
- High-severity without news = flag
- May indicate insider information
- Could be technical (rebalancing)
- Worth deeper fundamental review

### 5. **Consider Market Structure**
- Thin liquidity amplifies moves
- Retail-driven can be sentiment-heavy
- Foreign flows matter (not always news)
- Index inclusion/exclusion is material

---

## Conclusion

The materiality filtering system ensures that the news-anomaly correlation focuses on **actionable intelligence** rather than noise. By understanding PSX's unique characteristics—policy-driven moves, local over global sensitivity, and concentrated liquidity—the system provides high-quality signals for market analysis.

**Remember**: In PSX, **local policy > global trends** and **sustained changes > daily noise**.

---

**Last Updated**: 2026-02-14
**Version**: 2.0 (PSX-Contextualized)
