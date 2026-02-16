# Risk-Based Portfolio Management - Implementation Plan

## Executive Summary

Enhance the Portfolio Manager Agent to make decisions based on **economic risk factors, sector dynamics, and company fundamentals** rather than simple profit-taking rules. This creates a more sophisticated system that:

- **Holds winners** with strong fundamentals despite high gains
- **Exits winners** when macro/fundamental risks outweigh upside
- **Buys dips** in quality companies during temporary weakness
- **Exits losers** when structural (not temporary) issues are present

## Problem with Current Approach

**Current Logic (Too Simplistic):**
```
NATF up 209% → "Take profits!"
GAL down 10% → "Cut losses!"
```

**Issues:**
1. ❌ Ignores **why** stock is up (strong fundamentals vs speculation)
2. ❌ Ignores **macro context** (favorable vs deteriorating environment)
3. ❌ Ignores **valuation** (still cheap vs overextended)
4. ❌ Treats all gains/losses equally (quality company vs structurally broken)

**Better Approach:**
```
NATF up 209% + Strong fundamentals + Growing food sector + Still reasonable valuation
→ "HOLD - Let winner run with trailing stop"

GAL down 10% + Auto sector weak + High debt + Losing market share
→ "EXIT - Structural issues, not temporary dip"
```

## Risk Framework Architecture

### 1. Multi-Layer Risk Assessment

```
Portfolio Decision = f(
    Economic Risks,      // Macro environment (30% weight)
    Sector Risks,        // Industry dynamics (25% weight)
    Company Risks,       // Firm-specific (25% weight)
    Valuation Risk,      // Price vs intrinsic value (20% weight)
)
```

### 2. Economic Risk Factors (Pakistan-Specific)

#### A. Monetary Policy Risk
- **SBP Policy Rate** (current: ~22%)
  - Rising rates → Negative for equities, positive for financials
  - Falling rates → Positive for growth stocks, negative for banks
- **Real Interest Rates** (nominal - inflation)
  - Negative real rates → Favor equities over bonds
  - Positive real rates → Favor bonds, pressure on stocks

#### B. Currency Risk
- **PKR/USD Exchange Rate**
  - Devaluation → Positive for exporters (textiles), negative for importers (auto, pharma)
  - Stability → Positive for overall market confidence
- **FX Reserves** (adequacy)
  - Low reserves (<3 months imports) → Currency risk, capital flight
  - Adequate reserves → Market stability

#### C. Inflation Risk
- **CPI Inflation** (current: ~25-30%)
  - High inflation → Erodes purchasing power, pressure on margins
  - Moderating inflation → Positive for consumer discretionary, banks
- **Food Inflation** (subset of CPI)
  - High food inflation → Negative for FMCG companies
  - Moderating → Positive for food sector stocks

#### D. Fiscal Risk
- **Fiscal Deficit** (% of GDP)
  - High deficit → Crowding out, higher rates, PKR pressure
  - Improving deficit → Positive for overall market
- **Government Debt/GDP**
  - Rising debt → Sovereign risk, capital market pressure
  - Stable debt → Better environment

#### E. Political Risk
- **Political Stability Index**
  - Elections, policy uncertainty → Market volatility
  - Stable government → Better for long-term investing
- **IMF Program Status**
  - On-track → FX stability, lower sovereign risk
  - Off-track → Currency risk, capital flight risk

#### F. External Sector
- **Current Account Balance**
  - Deficit → FX pressure, import restrictions
  - Surplus → FX stability, import-dependent sectors benefit
- **Remittances** (monthly flow)
  - Strong remittances → PKR support, consumer spending
  - Weak remittances → FX pressure, consumption risk

### 3. Sector Risk Factors

#### Banking Sector (BAFL, AGP)
**Positive Factors:**
- Rising interest rates (higher NIMs)
- Credit growth recovery
- NPL ratios declining
- Strong capital adequacy

**Negative Factors:**
- Interest rate cuts (margin compression)
- Rising NPLs
- Regulatory changes (higher capital requirements)
- Credit growth slowdown

**Risk Score Calculation:**
```python
banking_risk_score = (
    interest_rate_trajectory * 0.30 +    # Rising = positive
    npl_trend * 0.25 +                   # Declining = positive
    credit_growth * 0.20 +               # Growing = positive
    regulatory_risk * 0.15 +             # Low = positive
    capital_adequacy * 0.10              # Strong = positive
)
```

#### Automobile Sector (SAZEW, GAL, ATLH)
**Positive Factors:**
- PKR stability (imported parts cheaper)
- Lower interest rates (easier auto financing)
- Rising consumer confidence
- New model launches

**Negative Factors:**
- PKR devaluation (parts cost up)
- High interest rates (financing expensive)
- Import restrictions
- Competition from used imports

**Risk Score:**
```python
auto_risk_score = (
    pkr_stability * 0.35 +               # Stable = positive
    interest_rate_level * 0.25 +         # Low = positive
    import_policy * 0.20 +               # Liberal = positive
    consumer_confidence * 0.20           # High = positive
)
```

#### FMCG/Food Sector (NATF, BBFL, BFAGRO)
**Positive Factors:**
- Moderating food inflation
- Rising disposable income
- Distribution expansion
- New product launches

**Negative Factors:**
- High input costs (wheat, sugar, milk)
- Weak consumer spending
- Competition intensifying
- Regulatory (price controls)

**Risk Score:**
```python
fmcg_risk_score = (
    input_cost_trend * 0.30 +            # Falling = positive
    consumer_spending * 0.25 +           # Growing = positive
    inflation_trend * 0.25 +             # Moderating = positive
    competitive_intensity * 0.20         # Low = positive
)
```

#### Pharma Sector (HINOON, BFBIO, HALEON)
**Positive Factors:**
- DRAP pricing flexibility
- Growing healthcare spending
- New drug approvals
- Export opportunities

**Negative Factors:**
- Price controls tightening
- Import duties on APIs
- PKR devaluation (imported APIs)
- Generic competition

**Risk Score:**
```python
pharma_risk_score = (
    regulatory_environment * 0.35 +      # Liberal = positive
    pkr_stability * 0.30 +               # Stable = positive
    healthcare_spending * 0.20 +         # Growing = positive
    competitive_position * 0.15          # Strong = positive
)
```

#### Oil & Gas Sector (HTL)
**Positive Factors:**
- Oil price stability
- Circular debt resolution
- Gas supply improving
- Exploration success

**Negative Factors:**
- Oil price volatility
- Circular debt buildup
- Import restrictions
- Subsidy burden

#### Manufacturing/Chemicals (PAEL, ICL)
**Positive Factors:**
- Industrial activity recovery
- Export demand strong
- Input costs moderating
- Capacity utilization improving

**Negative Factors:**
- Energy costs high
- PKR volatility
- Weak domestic demand
- Import competition

### 4. Company-Specific Risk Factors

#### A. Financial Health Risk
```python
financial_risk_score = (
    debt_to_equity_ratio * 0.30 +        # Low = positive
    interest_coverage * 0.25 +           # High = positive
    current_ratio * 0.20 +               # >1.5 = positive
    cash_flow_stability * 0.15 +         # Stable = positive
    working_capital * 0.10               # Positive = good
)
```

**Red Flags (Auto-Exit):**
- Debt/Equity > 2.0 and rising
- Interest coverage < 2x
- Negative operating cash flow for 2+ quarters
- Working capital turning negative

#### B. Earnings Quality Risk
```python
earnings_quality_score = (
    revenue_recognition * 0.25 +         # Conservative = positive
    accruals_ratio * 0.20 +             # Low = positive
    cash_conversion * 0.25 +            # High = positive
    one_time_items * 0.15 +             # Low = positive
    revenue_concentration * 0.15        # Diversified = positive
)
```

**Red Flags:**
- Receivables growing faster than revenue
- High accruals (earnings without cash)
- Frequent "exceptional items"
- Single customer >30% of revenue

#### C. Competitive Position Risk
```python
competitive_risk_score = (
    market_share_trend * 0.30 +         # Growing = positive
    pricing_power * 0.25 +              # Strong = positive
    brand_strength * 0.20 +             # Strong = positive
    entry_barriers * 0.15 +             # High = positive
    switching_costs * 0.10              # High = positive
)
```

**Red Flags:**
- Losing market share for 2+ years
- Margin compression despite revenue growth
- New entrants gaining share rapidly
- Customers switching to competitors

#### D. Management Quality Risk
```python
management_risk_score = (
    capital_allocation * 0.30 +         # Disciplined = positive
    governance_score * 0.25 +           # Strong = positive
    track_record * 0.20 +               # Consistent = positive
    transparency * 0.15 +               # High = positive
    insider_ownership * 0.10            # Aligned = positive
)
```

**Red Flags:**
- Poor capital allocation (destroying value)
- Related party transactions
- Frequent CEO/CFO changes
- Opaque disclosures

### 5. Valuation Risk Framework

#### A. Absolute Valuation Metrics
```python
valuation_risk = (
    pe_ratio_vs_historical * 0.25 +     # <1.2x = reasonable
    pb_ratio_vs_book_value * 0.20 +     # <1.5x = reasonable
    ev_ebitda_vs_peers * 0.20 +         # Below peers = cheap
    dividend_yield * 0.15 +             # >5% = attractive
    price_to_sales * 0.20               # <1.5x = reasonable
)
```

**Valuation Zones:**
- **Undervalued**: Composite score < 40 → BUY
- **Fair Value**: 40-60 → HOLD
- **Overvalued**: 60-80 → REDUCE
- **Extremely Overvalued**: >80 → SELL

#### B. Relative Valuation
- Compare to sector peers
- Compare to own historical average
- Compare to market (KSE-100)

**Example:**
```
NATF:
- Current P/E: 15x
- 5-year average P/E: 12x → Trading at 1.25x historical (slightly expensive)
- Sector average P/E: 18x → Trading at 0.83x sector (cheap vs peers)
- Verdict: Fairly valued to cheap on relative basis
```

### 6. Integrated Decision Matrix

#### Hold Winner (High Gains, Keep Holding)
**Conditions (ALL must be true):**
1. ✅ Economic risk score: FAVORABLE (>60/100)
2. ✅ Sector risk score: NEUTRAL or better (>50/100)
3. ✅ Company risk score: LOW (<30/100)
4. ✅ Valuation risk: FAIR or better (<70/100)
5. ✅ Earnings momentum: POSITIVE (growing)

**Action:** HOLD with trailing stop at -15% from peak

**Example:**
```
NATF (up 209%):
- Economic: Food inflation moderating → 65/100 ✅
- Sector: FMCG demand stable → 60/100 ✅
- Company: Strong balance sheet, growing market share → 20/100 ✅
- Valuation: P/E 15x vs 5yr avg 12x → 55/100 ✅
- Momentum: Earnings growing 25% YoY → POSITIVE ✅

Decision: HOLD - Let winner run, set trailing stop at PKR 347 (-15%)
```

#### Exit Winner (High Gains, Time to Sell)
**Conditions (ANY can trigger):**
1. ❌ Valuation risk: EXTREME (>85/100)
2. ❌ Sector risk deteriorating rapidly (score falling >20 points/quarter)
3. ❌ Company fundamentals weakening (rising debt, falling margins)
4. ❌ Earnings momentum reversing (negative surprises)
5. ❌ Economic headwinds intensifying (recession, currency crisis)

**Action:** SELL 50-100% depending on severity

**Example:**
```
Hypothetical: BAFL (up 130%)
- Economic: SBP cutting rates → 40/100 (margins compressed) ❌
- Sector: NPLs rising, credit growth slowing → 35/100 ❌
- Company: NIM falling 100bps → 60/100 ⚠️
- Valuation: P/B 2.5x vs 5yr avg 1.2x → 85/100 ❌
- Momentum: Earnings growth slowing → NEGATIVE ❌

Decision: SELL 75% - Multiple red flags, overvalued, deteriorating fundamentals
```

#### Hold Loser (Temporary Dip, Don't Sell)
**Conditions (ALL must be true):**
1. ✅ Company fundamentals: STRONG (low debt, strong moat)
2. ✅ Sector outlook: IMPROVING or stable
3. ✅ Reason for decline: TEMPORARY (market selloff, one-time item)
4. ✅ Valuation: ATTRACTIVE (creating buying opportunity)
5. ✅ Management: EXECUTING well on strategy

**Action:** HOLD or ADD on dips

**Example:**
```
Hypothetical: PAKT down 15% (temporary dip)
- Company: Tobacco monopoly, pricing power intact → Strong ✅
- Sector: Stable demand, regulatory environment unchanged → 70/100 ✅
- Reason: Market selloff, no company-specific issue → Temporary ✅
- Valuation: P/E dropped to 10x vs historical 12x → Attractive ✅
- Management: Track record of shareholder value → Strong ✅

Decision: HOLD - Quality company on temporary weakness, consider adding
```

#### Exit Loser (Structural Issues, Cut Loss)
**Conditions (ANY can trigger):**
1. ❌ Fundamentals deteriorating (rising debt, falling margins)
2. ❌ Competitive position eroding (losing market share)
3. ❌ Sector in structural decline (regulatory changes, obsolescence)
4. ❌ Management issues (governance concerns, poor capital allocation)
5. ❌ Earnings repeatedly missing estimates

**Action:** SELL 100% - Don't average down on broken stocks

**Example:**
```
GAL (down 10.68%):
- Company: High debt (D/E 1.8x), margins falling → 75/100 ❌
- Sector: Auto sales down 30% YoY, import restrictions → 30/100 ❌
- Competitive: Losing share to ATLH, Suzuki → 70/100 ❌
- Valuation: P/E 8x but earnings falling → Not cheap enough ⚠️
- Outlook: Unlikely to recover soon → NEGATIVE ❌

Decision: SELL 100% - Multiple structural issues, not a dip
```

## Implementation Plan

### Phase 1: Data Collection Infrastructure (Week 1-2)

**File:** `psx_economic_data.py`

```python
class PSXEconomicData:
    """Collects and tracks economic indicators for Pakistan"""

    def get_sbp_policy_rate(self) -> float
    def get_inflation_rate(self) -> float
    def get_pkr_usd_rate(self) -> float
    def get_fx_reserves(self) -> float
    def get_current_account_balance(self) -> float

    # Calculate derived metrics
    def get_real_interest_rate(self) -> float
    def get_economic_risk_score(self) -> float  # 0-100
```

**Data Sources:**
- State Bank of Pakistan (SBP) website
- Pakistan Bureau of Statistics (PBS)
- Ministry of Finance
- Trading Economics API (if available)
- Manual input for key metrics

**Database Schema:**
```sql
CREATE TABLE economic_indicators (
    date TEXT PRIMARY KEY,
    policy_rate REAL,
    inflation_cpi REAL,
    inflation_food REAL,
    pkr_usd_rate REAL,
    fx_reserves REAL,
    current_account REAL,
    fiscal_deficit REAL,
    imf_program_status TEXT,
    political_stability_index REAL
);
```

### Phase 2: Sector Risk Scoring (Week 3-4)

**File:** `psx_sector_risk.py`

```python
class PSXSectorRisk:
    """Calculates sector-specific risk scores"""

    def get_banking_sector_risk(self, economic_data) -> SectorRiskScore
    def get_auto_sector_risk(self, economic_data) -> SectorRiskScore
    def get_fmcg_sector_risk(self, economic_data) -> SectorRiskScore
    def get_pharma_sector_risk(self, economic_data) -> SectorRiskScore

    def calculate_sector_risk_score(self, sector: str, symbol: str) -> float
```

**Sector Mappings:**
```python
SECTOR_MAPPING = {
    'BAFL': 'Banking',
    'AGP': 'Banking',
    'HBL': 'Banking',
    'SAZEW': 'Automobile',
    'GAL': 'Automobile',
    'ATLH': 'Automobile',
    'NATF': 'FMCG',
    'BBFL': 'FMCG',
    # ... etc
}
```

### Phase 3: Company Risk Assessment (Week 5-6)

**File:** `psx_company_risk.py`

```python
class PSXCompanyRisk:
    """Assesses company-specific risks"""

    def assess_financial_health(self, symbol: str) -> FinancialRiskScore
    def assess_earnings_quality(self, symbol: str) -> EarningsRiskScore
    def assess_competitive_position(self, symbol: str) -> CompetitiveRiskScore
    def assess_management_quality(self, symbol: str) -> ManagementRiskScore

    def get_company_risk_score(self, symbol: str) -> float  # 0-100
```

**Metrics to Track:**
```python
@dataclass
class FinancialRiskScore:
    debt_to_equity: float
    interest_coverage: float
    current_ratio: float
    cash_flow_from_operations: float
    working_capital: float
    risk_score: float  # 0-100
    red_flags: List[str]
```

### Phase 4: Valuation Risk Analysis (Week 7)

**File:** `psx_valuation_risk.py`

```python
class PSXValuationRisk:
    """Assesses valuation risk (overvalued vs undervalued)"""

    def calculate_pe_risk(self, symbol: str) -> float
    def calculate_pb_risk(self, symbol: str) -> float
    def calculate_dividend_yield_risk(self, symbol: str) -> float

    def get_valuation_zone(self, symbol: str) -> ValuationZone
    # Returns: UNDERVALUED, FAIR, OVERVALUED, EXTREMELY_OVERVALUED
```

### Phase 5: Integrated Risk-Based Portfolio Manager (Week 8-9)

**File:** `psx_risk_based_portfolio_manager.py`

```python
class RiskBasedPortfolioManager(PSXPortfolioManager):
    """
    Enhanced portfolio manager with risk-based decision making
    Inherits from PSXPortfolioManager but overrides decision logic
    """

    def __init__(self, portfolio_store, config, economic_data, sector_risk, company_risk, valuation_risk):
        super().__init__(portfolio_store, config)
        self.economic_data = economic_data
        self.sector_risk = sector_risk
        self.company_risk = company_risk
        self.valuation_risk = valuation_risk

    def _generate_decision(self, signal, current_position, portfolio, model):
        """
        Override parent method to include risk-based logic
        """
        # Get risk scores
        economic_risk = self.economic_data.get_economic_risk_score()
        sector_risk = self.sector_risk.calculate_sector_risk_score(signal.symbol)
        company_risk = self.company_risk.get_company_risk_score(signal.symbol)
        valuation_risk = self.valuation_risk.get_valuation_risk_score(signal.symbol)

        # Make decision based on integrated risk framework
        if current_position:
            return self._decide_on_existing_position(
                signal, current_position,
                economic_risk, sector_risk, company_risk, valuation_risk
            )
        else:
            return self._decide_on_new_position(
                signal, portfolio,
                economic_risk, sector_risk, company_risk, valuation_risk
            )

    def _decide_on_existing_position(self, signal, position, econ_risk, sector_risk, co_risk, val_risk):
        """
        Decide whether to hold, reduce, or exit existing position
        """
        unrealized_pl_pct = position.unrealized_pl_pct

        # HOLD WINNER: High gains but strong fundamentals
        if unrealized_pl_pct > 50:  # Up >50%
            if (econ_risk > 60 and sector_risk > 50 and
                co_risk < 30 and val_risk < 70):
                # Favorable conditions, let winner run
                return TradeDecision(
                    action=ActionType.HOLD,
                    reasoning=self._format_hold_winner_reasoning(
                        unrealized_pl_pct, econ_risk, sector_risk, co_risk, val_risk
                    )
                )

        # EXIT WINNER: High gains + deteriorating fundamentals
        if unrealized_pl_pct > 50:
            if (val_risk > 85 or co_risk > 70 or sector_risk < 30):
                # Red flags, time to exit
                return TradeDecision(
                    action=ActionType.SELL,
                    quantity=position.quantity,
                    reasoning=self._format_exit_winner_reasoning(
                        unrealized_pl_pct, econ_risk, sector_risk, co_risk, val_risk
                    )
                )

        # HOLD LOSER: Down but strong fundamentals
        if unrealized_pl_pct < -5:  # Down >5%
            if (co_risk < 30 and sector_risk > 50 and val_risk < 40):
                # Quality company on temporary dip
                return TradeDecision(
                    action=ActionType.HOLD,
                    reasoning=self._format_hold_loser_reasoning(
                        unrealized_pl_pct, co_risk, sector_risk, val_risk
                    )
                )

        # EXIT LOSER: Down + structural issues
        if unrealized_pl_pct < -5:
            if (co_risk > 60 or sector_risk < 35):
                # Structural problems, exit
                return TradeDecision(
                    action=ActionType.SELL,
                    quantity=position.quantity,
                    reasoning=self._format_exit_loser_reasoning(
                        unrealized_pl_pct, co_risk, sector_risk
                    )
                )

        # Default: Use parent class logic
        return super()._decide_on_existing_position(signal, position, ...)
```

### Phase 6: Enhanced Reporting (Week 10)

**Output Format:**

```
================================================================================
💼 RISK-BASED PORTFOLIO ANALYSIS
================================================================================

📊 ECONOMIC ENVIRONMENT
   Policy Rate:           22.0% (High - Restrictive)
   Inflation (CPI):       28.3% (High - Moderating trend ✓)
   Real Interest Rate:    -6.3% (Negative - Favor equities)
   PKR/USD:              278.5 (Stable - Improving ✓)
   FX Reserves:          $8.2B (3.2 months - Adequate)
   Current Account:      -$1.2B (Deficit - Improving)

   Economic Risk Score:   62/100 (NEUTRAL - Stabilizing)
   Overall Environment:   IMPROVING ✅

================================================================================
📈 POSITION-LEVEL RISK ANALYSIS
================================================================================

1. NATF - HOLD (Up 209.6%)
   Current Value: PKR 224,917 (8.16% of portfolio)

   Risk Assessment:
   • Economic Risk:    65/100 (FAVORABLE - Food inflation moderating)
   • Sector Risk:      60/100 (NEUTRAL - FMCG demand stable)
   • Company Risk:     22/100 (LOW - Strong balance sheet, market leader)
   • Valuation Risk:   55/100 (FAIR - P/E 15x vs 5yr avg 12x)

   Decision: HOLD - Let Winner Run ✅
   Reasoning:
   ✓ Strong fundamentals despite 209% gain
   ✓ Food sector benefiting from moderating inflation
   ✓ Company growing market share, margins expanding
   ✓ Valuation reasonable given 25% earnings growth
   ✓ No red flags detected

   Action: Set trailing stop at PKR 347 (-15% from current)

2. GAL - SELL (Down 10.7%)
   Current Value: PKR 74,399 (2.70% of portfolio)

   Risk Assessment:
   • Economic Risk:    45/100 (UNFAVORABLE - High rates hurt auto demand)
   • Sector Risk:      28/100 (HIGH RISK - Auto sales down 30% YoY)
   • Company Risk:     72/100 (HIGH RISK - High debt, losing market share)
   • Valuation Risk:   65/100 (NOT CHEAP - P/E 8x but earnings falling)

   Decision: SELL 100% - Exit Structurally Weak Position ❌
   Reasoning:
   ✗ Auto sector facing structural headwinds (import restrictions)
   ✗ Company losing market share to ATLH and Suzuki
   ✗ High debt (D/E 1.8x) limits financial flexibility
   ✗ Not a temporary dip - fundamental issues
   ✗ Better opportunities elsewhere

   Action: Sell all 150 shares, redeploy to higher conviction ideas

3. BAFL - TRIM (Up 130.3%)
   Current Value: PKR 189,000 (6.85% of portfolio)

   Risk Assessment:
   • Economic Risk:    42/100 (UNFAVORABLE - Rate cuts will compress NIMs)
   • Sector Risk:      48/100 (NEUTRAL - Banking cycle peaking)
   • Company Risk:     35/100 (MODERATE - Solid but NIMs declining)
   • Valuation Risk:   78/100 (OVERVALUED - P/B 2.5x vs avg 1.2x)

   Decision: TRIM 40% - Take Profits on Cyclical Peak ⚠️
   Reasoning:
   ⚠ Banking cycle likely peaking (SBP to cut rates in 2024)
   ⚠ Valuation stretched (P/B 2.5x vs historical 1.2x)
   ✓ Still fundamentally sound, but upside limited
   ✓ Lock in gains before margin compression begins

   Action: Sell 600 shares (~40%), keep 900 shares for dividend income
```

### Phase 7: Dashboard Integration (Week 11-12)

Add risk visualizations to existing dashboard:

```typescript
// Risk heatmap by position
interface PositionRisk {
  symbol: string;
  economicRisk: number;
  sectorRisk: number;
  companyRisk: number;
  valuationRisk: number;
  overallRisk: number;
  action: 'HOLD' | 'TRIM' | 'EXIT';
}

// Economic indicators chart
<EconomicIndicatorsChart
  policyRate={22.0}
  inflation={28.3}
  pkrUsd={278.5}
  trend="improving"
/>

// Sector risk heatmap
<SectorRiskHeatmap
  sectors={['Banking', 'Auto', 'FMCG', 'Pharma']}
  riskScores={[48, 28, 60, 55]}
/>
```

## Usage Examples

### Example 1: NATF Analysis (Up 209%)

**Old Approach:**
```
NATF up 209% → "Take 50% profits!"
```

**New Risk-Based Approach:**
```python
# Get all risk scores
economic = economic_data.get_economic_risk_score()  # 65/100 (favorable)
sector = sector_risk.get_fmcg_sector_risk()        # 60/100 (neutral)
company = company_risk.assess(NATF)                # 22/100 (low risk)
valuation = valuation_risk.assess(NATF)            # 55/100 (fair value)

# Decision logic
if all([economic > 60, sector > 50, company < 30, valuation < 70]):
    decision = "HOLD - Let winner run with trailing stop"
    reasoning = [
        "✓ Food inflation moderating (favorable macro)",
        "✓ NATF growing market share (strong company)",
        "✓ P/E 15x reasonable for 25% earnings growth",
        "✓ No red flags in financial health",
        "Action: Set trailing stop at -15% from peak"
    ]
```

### Example 2: GAL Analysis (Down 10.7%)

**Old Approach:**
```
GAL down 10.7% → "Hold, it's just a dip"
```

**New Risk-Based Approach:**
```python
economic = 45/100  # High rates hurting auto demand
sector = 28/100    # Auto sector in structural decline
company = 72/100   # High debt, losing market share
valuation = 65/100 # P/E 8x but earnings collapsing

# Decision logic
if sector < 35 or company > 60:
    decision = "SELL 100% - Structural issues, not temporary dip"
    reasoning = [
        "✗ Auto sector down 30% YoY (import restrictions)",
        "✗ GAL losing share to ATLH and Suzuki",
        "✗ High debt (D/E 1.8x) limits flexibility",
        "✗ Margins compressing despite price hikes",
        "Action: Exit and redeploy to quality"
    ]
```

## Configuration

**File:** `portfolio_risk_config.json`

```json
{
  "economic_risk": {
    "policy_rate_weight": 0.25,
    "inflation_weight": 0.20,
    "currency_weight": 0.20,
    "fiscal_weight": 0.15,
    "political_weight": 0.10,
    "external_weight": 0.10
  },

  "sector_thresholds": {
    "banking": {
      "favorable": 60,
      "neutral": 40,
      "unfavorable": 40
    },
    "automobile": {
      "favorable": 55,
      "neutral": 35,
      "unfavorable": 35
    }
  },

  "decision_rules": {
    "hold_winner": {
      "min_economic_risk": 60,
      "min_sector_risk": 50,
      "max_company_risk": 30,
      "max_valuation_risk": 70
    },
    "exit_winner": {
      "valuation_risk_threshold": 85,
      "company_risk_threshold": 70,
      "sector_risk_threshold": 30
    },
    "hold_loser": {
      "max_company_risk": 30,
      "min_sector_risk": 50,
      "max_valuation_risk": 40
    },
    "exit_loser": {
      "company_risk_threshold": 60,
      "sector_risk_threshold": 35
    }
  },

  "trailing_stop": {
    "winner_percentage": 15,
    "loser_percentage": 10
  }
}
```

## Success Metrics

1. **Better Hold Decisions:**
   - Don't sell NATF at +50% if still fundamentally strong
   - Hold through temporary dips in quality companies

2. **Better Exit Decisions:**
   - Exit GAL before larger losses (catch -10% not -30%)
   - Exit overvalued winners before mean reversion

3. **Better Entry Decisions:**
   - Buy quality companies on temporary macro weakness
   - Avoid value traps (cheap for a reason)

4. **Performance vs Benchmark:**
   - Outperform KSE-100 by 5%+ annually
   - Lower volatility (Sharpe ratio >1.0)
   - Max drawdown <20%

## Rollout Plan

**Week 1-2:** Economic data collection
**Week 3-4:** Sector risk scoring
**Week 5-6:** Company risk assessment
**Week 7:** Valuation analysis
**Week 8-9:** Integrated decision engine
**Week 10:** Enhanced reporting
**Week 11-12:** Dashboard integration
**Week 13:** Backtesting on historical data
**Week 14:** Production deployment

## Dependencies

**Data Sources:**
- State Bank of Pakistan API/website scraping
- Pakistan Bureau of Statistics
- yfinance for company fundamentals
- Manual input for qualitative factors

**New Libraries:**
```
pandas-datareader  # For economic data
beautifulsoup4     # For web scraping SBP/PBS
requests           # HTTP requests
```

## Next Steps

1. **Approve this plan** or request modifications
2. **Prioritize components** (which to build first?)
3. **Define data sources** (manual vs automated)
4. **Set timelines** (aggressive 14 weeks or more gradual?)

This risk-based approach will transform the portfolio manager from a simple "take profits on winners" system to a sophisticated decision engine that considers the full economic and fundamental picture.
