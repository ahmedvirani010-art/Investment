# Phase 1 Implementation Progress: Economic Risk Scoring

## ✅ Completed (Week 1, Days 1-4)

### Core Infrastructure

1. **psx_economic_data.py** (598 lines) - COMPLETE
   - ✅ `EconomicIndicators` dataclass with 19 Pakistan-specific indicators
   - ✅ `EconomicRiskScore` dataclass with 5 component scores
   - ✅ `PSXEconomicData` class with SQLite persistence
   - ✅ Risk calculation with weighted component scores
   - ✅ Trend detection (improving/stable/deteriorating)
   - ✅ Factor identification (positive/negative/risks)
   - ✅ Database schema at `portfolio_data/economic_data.db`

2. **update_economic_data.py** (418 lines) - COMPLETE
   - ✅ Interactive CLI for manual data entry
   - ✅ Smart defaults from previous data
   - ✅ Input validation
   - ✅ Confirmation before saving
   - ✅ Immediate risk report generation
   - ✅ Portfolio implications display

3. **demo_economic_risk.py** (329 lines) - COMPLETE
   - ✅ Current scenario demonstration
   - ✅ Stress scenario analysis (Crisis/Recovery/Stagnation)
   - ✅ Historical data tracking
   - ✅ Position-specific guidance

### Test Results

**Demo output shows correct risk scoring:**
```
Current Scenario: 65.2/100 (NEUTRAL) - Balanced approach recommended
Crisis Scenario:  32.0/100 (UNFAVORABLE) - Risk-off, reduce equity exposure
Recovery Scenario: 82.5/100 (FAVORABLE) - Risk-on, increase cyclical exposure
Stagnation Scenario: 63.5/100 (NEUTRAL) - Maintain current allocation
```

**Component scoring working correctly:**
- Monetary Policy: 60/100 (Weight 25%)
- Currency Stability: 55/100 (Weight 25%)
- Fiscal Health: 70/100 (Weight 20%)
- External Sector: 80/100 (Weight 20%)
- Qualitative Factors: 65/100 (Weight 10%)

## 📊 Economic Indicators Tracked

### Monetary Policy (25% weight)
- SBP Policy Rate
- CPI Inflation
- Food Inflation
- Real Interest Rate (calculated)

### Currency Stability (25% weight)
- PKR/USD Exchange Rate
- 1-Month Change %
- 3-Month Change %
- FX Reserves (USD billions)
- FX Reserves (months of import cover)

### Fiscal Health (20% weight)
- Fiscal Deficit (% of GDP)
- Government Debt (% of GDP)

### External Sector (20% weight)
- Current Account Balance (USD billions)
- Worker Remittances (USD billions)
- Exports (USD billions)
- Imports (USD billions)

### Qualitative Factors (10% weight)
- IMF Program Status (0-10 scale)
- Political Stability (0-10 scale)

## 🎯 Risk Scoring System

### Overall Score Interpretation
- **70-100**: FAVORABLE - Risk-on, increase equity allocation
- **50-69**: NEUTRAL - Balanced approach, maintain allocation
- **30-49**: CAUTIOUS - Defensive positioning, reduce cyclicals
- **0-29**: RISK-OFF - Capital preservation, significantly reduce equity

### Portfolio Implications by Risk Level

#### FAVORABLE Environment (70-100)
- ✅ INCREASE equity allocation to target levels
- ✅ ADD to quality growth stocks on dips
- ✅ Use AGGRESSIVE or BALANCED portfolio model
- ✅ Focus on cyclicals (Banks, Auto, Cement)
- ✅ Reduce cash reserves to minimum

#### NEUTRAL Environment (50-69)
- 🟡 MAINTAIN current equity allocation
- 🟡 HOLD quality positions, trim laggards
- 🟡 Use BALANCED portfolio model
- 🟡 Mix defensive and growth stocks
- 🟡 Keep moderate cash reserves (10-15%)

#### CAUTIOUS Environment (30-49)
- 🟠 REDUCE exposure to cyclicals and small caps
- 🟠 ROTATE into defensive sectors
- 🟠 Use CONSERVATIVE portfolio model
- 🟠 Focus on dividend-paying, low-beta stocks
- 🟠 Increase cash reserves (20-30%)

#### RISK-OFF Environment (0-29)
- 🔴 SIGNIFICANTLY REDUCE equity exposure (50%+)
- 🔴 HOLD only highest-quality defensive names
- 🔴 EXIT speculative and small-cap positions
- 🔴 PAUSE new investments
- 🔴 Raise cash to 40-50%

## 📋 Position-Specific Guidance

The system provides tailored recommendations for your actual portfolio based on economic environment:

### In NEUTRAL/FAVORABLE Environment (Score ≥ 50):
- **NATF (+209%)**: HOLD - Fundamentals strong, macro supportive
- **BAFL (+130%)**: HOLD - Banking sector benefits from stable rates
- **ICL (+105%)**: CONSIDER partial profit-taking if valuation stretched
- **ATLH (+52%)**: HOLD - Auto sector recovery aligned with GDP growth
- **GAL (-10.7%)**: REVIEW - If fundamentals weak, EXIT regardless of macro
- **PAEL (-8.0%)**: REVIEW - Monitor sector headwinds vs. macro recovery

### In CAUTIOUS/RISK-OFF Environment (Score < 50):
- **NATF (+209%)**: REDUCE 30-50% - Lock in gains during uncertainty
- **BAFL (+130%)**: REDUCE 25-30% - Take profits in banking
- **ICL (+105%)**: REDUCE 30% - Trim winners in risk-off environment
- **GAL (-10.7%)**: EXIT - Cut losers in unfavorable macro
- **PAEL (-8.0%)**: EXIT or REDUCE 50% - Limit exposure to weak positions

## 📈 Usage

### 1. Update Economic Data (Monthly)
```bash
python update_economic_data.py
```

**Data Sources:**
- State Bank of Pakistan (SBP): https://www.sbp.org.pk
  - Monetary policy decisions (every 2 months)
  - FX reserves (weekly updates)
  - External sector data (monthly)
- Pakistan Bureau of Statistics: https://www.pbs.gov.pk
  - CPI/inflation data (monthly, ~15th of month)
- Ministry of Finance: https://www.finance.gov.pk
  - Fiscal indicators (quarterly/annual)
- Trading Economics: https://tradingeconomics.com/pakistan
  - Comprehensive dashboard with charts

### 2. View Demo and Test Scenarios
```bash
python demo_economic_risk.py
```

### 3. View Historical Data
```bash
sqlite3 portfolio_data/economic_data.db
SELECT date, overall_score, risk_level, trend FROM economic_risk_scores ORDER BY date DESC;
```

## 🔄 Next Steps (Week 2 - Portfolio Integration)

### Still To Implement:

1. **analyze_with_macro_context.py** - Analyze current portfolio with economic lens
   - Load user's 16-stock portfolio
   - Fetch latest economic risk score
   - Show how each position aligns with macro environment
   - Identify positions at risk if environment deteriorates

2. **portfolio_decisions_with_macro.py** - Position-by-position recommendations
   - For each position, combine:
     - Technical signals (existing PSXTechnicalAgent)
     - Fundamental scores (existing PSXFundamentalAgent)
     - Economic risk score (new PSXEconomicData)
   - Generate BUY/HOLD/REDUCE/EXIT decisions
   - Explain reasoning including macro context

3. **Integration with existing run_integrated_analysis.py**
   - Add economic risk context to final report
   - Show portfolio recommendations adjusted for macro environment
   - Display warning if portfolio is misaligned with economic conditions

4. **Monthly Update Process**
   - Document recommended update schedule
   - Create checklist for data collection
   - Set up reminder system

## 💡 Key Innovation

**This system answers the critical question:**
> "Should I hold NATF despite +209% gain or exit GAL at -10%?"

**Traditional approach:** Sell winners, hold or average down on losers
**Our approach:** Evaluate based on fundamentals + economic environment

**Example decision flow:**
```
NATF: +209% gain
├─ Fundamental Score: 85/100 (Strong)
├─ Economic Risk: 65/100 (Neutral-Favorable)
├─ Sector Outlook: Food sector defensive, benefits from stable environment
└─ Decision: HOLD (Don't sell just because price is up)

GAL: -10.7% loss
├─ Fundamental Score: 45/100 (Weak margins, high debt)
├─ Economic Risk: 65/100 (Neutral)
├─ Sector Outlook: Auto sector cyclical, needs strong GDP growth
└─ Decision: EXIT (Sell due to weak fundamentals, not just because it's down)
```

## 📊 Database Schema

**Tables created:**
- `economic_indicators` - Raw economic data
- `economic_risk_scores` - Calculated risk scores with trend analysis

**Location:** `portfolio_data/economic_data.db`

## 🎓 Lessons Learned

1. **Pakistan-specific indicators matter**: Generic global indicators insufficient
2. **0-10 vs 0-100 scales**: Qualitative factors use 0-10 for simplicity
3. **Real interest rate critical**: Calculated field (policy rate - inflation) is key signal
4. **FX reserves in months**: More meaningful than absolute USD value
5. **Trend detection**: Single point-in-time score insufficient, need historical context

## ✨ What Makes This Different

**Compared to traditional portfolio management:**
- ❌ Traditional: "Stock up 200%, take profits"
- ✅ Ours: "Stock up 200% but fundamentals strong + macro supportive → HOLD"

**Compared to other systems:**
- Most systems: Focus only on technical/fundamental
- Our system: Adds macro-economic layer for Pakistan-specific risks
- Unique: Manual data entry (necessary for Pakistan where APIs limited)
- Unique: Rule-based scoring (transparent, explainable, no black box)

## 📝 Notes

- All data entry is manual (Pakistan economic APIs limited/unreliable)
- Update frequency: Monthly after official releases
- SBP monetary policy decisions: Every 2 months
- CPI/inflation data: Monthly around 15th
- External sector data: Monthly from SBP
- System is rule-based (no LLM), fully deterministic and explainable

---

**Status:** Phase 1 foundation complete ✅
**Next:** Week 2 - Portfolio integration and decision-making logic
**Timeline:** On track for 2-week Phase 1 completion
