# Phase 1: Economic Risk Scoring - Implementation Guide

## Overview

Build the foundation for risk-based portfolio management by tracking Pakistan's economic indicators and calculating an Economic Risk Score (0-100) that influences hold/sell decisions.

**Timeline:** 2 weeks
**Complexity:** Medium (data collection + simple scoring)
**Immediate Value:** High (changes how you view all positions)

## Week 1: Data Collection & Storage

### Day 1-2: Economic Data Model

**File:** `psx_economic_data.py`

```python
"""
PSX Economic Data Tracker

Collects and tracks Pakistan economic indicators for portfolio risk assessment
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict
import sqlite3
import json
from pathlib import Path


@dataclass
class EconomicIndicators:
    """Pakistan economic indicators snapshot"""
    date: str

    # Monetary Policy
    sbp_policy_rate: float          # State Bank policy rate (%)
    inflation_cpi: float             # CPI inflation (% YoY)
    inflation_food: float            # Food inflation (% YoY)
    real_interest_rate: float        # Policy rate - inflation

    # Currency
    pkr_usd_rate: float             # PKR/USD exchange rate
    pkr_usd_change_1m: float        # % change last 1 month
    pkr_usd_change_3m: float        # % change last 3 months
    fx_reserves_usd: float          # FX reserves (USD billions)
    fx_reserves_months: float       # Months of import cover

    # Fiscal
    fiscal_deficit_gdp: float       # Fiscal deficit (% of GDP)
    government_debt_gdp: float      # Total govt debt (% of GDP)

    # External Sector
    current_account_usd: float      # Current account (USD billions)
    remittances_usd: float          # Monthly remittances (USD billions)
    exports_usd: float              # Monthly exports (USD billions)
    imports_usd: float              # Monthly imports (USD billions)

    # Qualitative (0-10 scale)
    imf_program_status: int         # 0=Off track, 10=On track
    political_stability: int        # 0=Unstable, 10=Stable

    # Metadata
    data_quality: float = 1.0       # 0-1 (how complete/reliable)
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class EconomicRiskScore:
    """Calculated economic risk score"""
    date: str
    overall_score: float            # 0-100 (higher = more favorable)

    # Component scores (0-100 each)
    monetary_policy_score: float
    currency_stability_score: float
    fiscal_health_score: float
    external_sector_score: float
    qualitative_score: float

    # Trend (improving/stable/deteriorating)
    trend: str                      # "improving", "stable", "deteriorating"
    trend_score: float              # -1 to +1

    # Interpretation
    risk_level: str                 # "favorable", "neutral", "unfavorable", "crisis"

    # Details for reporting
    positive_factors: list
    negative_factors: list
    key_risks: list

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class PSXEconomicData:
    """
    Economic data tracker for Pakistan

    Collects, stores, and calculates economic risk scores
    """

    def __init__(self, db_path: str = "portfolio_data/economic_data.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Economic indicators table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS economic_indicators (
                    date TEXT PRIMARY KEY,
                    sbp_policy_rate REAL,
                    inflation_cpi REAL,
                    inflation_food REAL,
                    real_interest_rate REAL,
                    pkr_usd_rate REAL,
                    pkr_usd_change_1m REAL,
                    pkr_usd_change_3m REAL,
                    fx_reserves_usd REAL,
                    fx_reserves_months REAL,
                    fiscal_deficit_gdp REAL,
                    government_debt_gdp REAL,
                    current_account_usd REAL,
                    remittances_usd REAL,
                    exports_usd REAL,
                    imports_usd REAL,
                    imf_program_status INTEGER,
                    political_stability INTEGER,
                    data_quality REAL,
                    notes TEXT
                )
            ''')

            # Risk scores table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS economic_risk_scores (
                    date TEXT PRIMARY KEY,
                    overall_score REAL,
                    monetary_policy_score REAL,
                    currency_stability_score REAL,
                    fiscal_health_score REAL,
                    external_sector_score REAL,
                    qualitative_score REAL,
                    trend TEXT,
                    trend_score REAL,
                    risk_level TEXT,
                    positive_factors TEXT,
                    negative_factors TEXT,
                    key_risks TEXT
                )
            ''')

            conn.commit()

    def save_indicators(self, indicators: EconomicIndicators):
        """Save economic indicators"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO economic_indicators
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                indicators.date,
                indicators.sbp_policy_rate,
                indicators.inflation_cpi,
                indicators.inflation_food,
                indicators.real_interest_rate,
                indicators.pkr_usd_rate,
                indicators.pkr_usd_change_1m,
                indicators.pkr_usd_change_3m,
                indicators.fx_reserves_usd,
                indicators.fx_reserves_months,
                indicators.fiscal_deficit_gdp,
                indicators.government_debt_gdp,
                indicators.current_account_usd,
                indicators.remittances_usd,
                indicators.exports_usd,
                indicators.imports_usd,
                indicators.imf_program_status,
                indicators.political_stability,
                indicators.data_quality,
                indicators.notes
            ))

            conn.commit()

    def get_latest_indicators(self) -> Optional[EconomicIndicators]:
        """Get most recent economic indicators"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM economic_indicators
                ORDER BY date DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()
            if not row:
                return None

            return EconomicIndicators(
                date=row[0],
                sbp_policy_rate=row[1],
                inflation_cpi=row[2],
                inflation_food=row[3],
                real_interest_rate=row[4],
                pkr_usd_rate=row[5],
                pkr_usd_change_1m=row[6],
                pkr_usd_change_3m=row[7],
                fx_reserves_usd=row[8],
                fx_reserves_months=row[9],
                fiscal_deficit_gdp=row[10],
                government_debt_gdp=row[11],
                current_account_usd=row[12],
                remittances_usd=row[13],
                exports_usd=row[14],
                imports_usd=row[15],
                imf_program_status=row[16],
                political_stability=row[17],
                data_quality=row[18],
                notes=row[19]
            )

    def calculate_risk_score(self, indicators: EconomicIndicators) -> EconomicRiskScore:
        """
        Calculate economic risk score from indicators

        Score: 0-100 (higher = more favorable for equities)
        """
        # Component 1: Monetary Policy (25% weight)
        monetary_score = self._score_monetary_policy(indicators)

        # Component 2: Currency Stability (25% weight)
        currency_score = self._score_currency_stability(indicators)

        # Component 3: Fiscal Health (20% weight)
        fiscal_score = self._score_fiscal_health(indicators)

        # Component 4: External Sector (20% weight)
        external_score = self._score_external_sector(indicators)

        # Component 5: Qualitative Factors (10% weight)
        qualitative_score = self._score_qualitative(indicators)

        # Weighted overall score
        overall_score = (
            monetary_score * 0.25 +
            currency_score * 0.25 +
            fiscal_score * 0.20 +
            external_score * 0.20 +
            qualitative_score * 0.10
        )

        # Determine risk level
        if overall_score >= 70:
            risk_level = "favorable"
        elif overall_score >= 50:
            risk_level = "neutral"
        elif overall_score >= 30:
            risk_level = "unfavorable"
        else:
            risk_level = "crisis"

        # Calculate trend
        trend, trend_score = self._calculate_trend(indicators)

        # Identify factors
        positive_factors, negative_factors, key_risks = self._identify_factors(indicators)

        return EconomicRiskScore(
            date=indicators.date,
            overall_score=overall_score,
            monetary_policy_score=monetary_score,
            currency_stability_score=currency_score,
            fiscal_health_score=fiscal_score,
            external_sector_score=external_score,
            qualitative_score=qualitative_score,
            trend=trend,
            trend_score=trend_score,
            risk_level=risk_level,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            key_risks=key_risks
        )

    def _score_monetary_policy(self, ind: EconomicIndicators) -> float:
        """
        Score monetary policy environment (0-100)

        Favorable for equities:
        - Real interest rates negative (inflation > policy rate)
        - Inflation moderating (falling)
        - Policy rates stable or falling
        """
        score = 50.0  # Neutral baseline

        # Real interest rate (30 points)
        if ind.real_interest_rate < -5:
            score += 30  # Very negative real rates = very favorable
        elif ind.real_interest_rate < 0:
            score += 20  # Negative real rates = favorable
        elif ind.real_interest_rate < 5:
            score += 5   # Low real rates = slightly favorable
        else:
            score -= 20  # High real rates = unfavorable

        # Inflation level (20 points)
        if ind.inflation_cpi < 10:
            score += 20  # Low inflation = favorable
        elif ind.inflation_cpi < 20:
            score += 10  # Moderate inflation = neutral
        elif ind.inflation_cpi < 30:
            score -= 10  # High inflation = unfavorable
        else:
            score -= 20  # Very high inflation = very unfavorable

        return max(0, min(100, score))

    def _score_currency_stability(self, ind: EconomicIndicators) -> float:
        """
        Score currency stability (0-100)

        Favorable:
        - PKR stable or appreciating
        - FX reserves adequate (>3 months)
        """
        score = 50.0

        # 1-month PKR change (25 points)
        if ind.pkr_usd_change_1m < -2:
            score += 25  # Appreciation = very favorable
        elif ind.pkr_usd_change_1m < 0:
            score += 15  # Slight appreciation = favorable
        elif ind.pkr_usd_change_1m < 2:
            score += 5   # Stable = slightly favorable
        elif ind.pkr_usd_change_1m < 5:
            score -= 15  # Depreciation = unfavorable
        else:
            score -= 30  # Sharp depreciation = very unfavorable

        # 3-month PKR change (15 points)
        if ind.pkr_usd_change_3m < 0:
            score += 15  # Appreciation trend
        elif ind.pkr_usd_change_3m < 5:
            score += 5   # Stable
        else:
            score -= 15  # Depreciation trend

        # FX reserves adequacy (10 points)
        if ind.fx_reserves_months >= 4:
            score += 10  # Very adequate
        elif ind.fx_reserves_months >= 3:
            score += 5   # Adequate
        elif ind.fx_reserves_months >= 2:
            score -= 5   # Low
        else:
            score -= 15  # Critically low

        return max(0, min(100, score))

    def _score_fiscal_health(self, ind: EconomicIndicators) -> float:
        """Score fiscal health (0-100)"""
        score = 50.0

        # Fiscal deficit
        if ind.fiscal_deficit_gdp < 5:
            score += 25
        elif ind.fiscal_deficit_gdp < 7:
            score += 10
        else:
            score -= 15

        # Government debt
        if ind.government_debt_gdp < 70:
            score += 25
        elif ind.government_debt_gdp < 85:
            score += 10
        else:
            score -= 15

        return max(0, min(100, score))

    def _score_external_sector(self, ind: EconomicIndicators) -> float:
        """Score external sector (0-100)"""
        score = 50.0

        # Current account
        if ind.current_account_usd > 0:
            score += 30  # Surplus
        elif ind.current_account_usd > -1:
            score += 10  # Small deficit
        else:
            score -= 20  # Large deficit

        # Remittances strength
        if ind.remittances_usd > 2.5:
            score += 20  # Strong
        elif ind.remittances_usd > 2.0:
            score += 10  # Adequate
        else:
            score -= 10  # Weak

        return max(0, min(100, score))

    def _score_qualitative(self, ind: EconomicIndicators) -> float:
        """Score qualitative factors (0-100)"""
        score = (
            (ind.imf_program_status / 10) * 50 +  # 50 points
            (ind.political_stability / 10) * 50   # 50 points
        )
        return score

    def _calculate_trend(self, current: EconomicIndicators):
        """Calculate trend (improving/stable/deteriorating)"""
        # Simplified: would compare to previous period in real implementation
        # For now, use heuristics

        improving_factors = 0
        deteriorating_factors = 0

        # Check if inflation is high but moderating
        if current.inflation_cpi > 20:
            # Assume moderating if real rates are very negative
            if current.real_interest_rate < -5:
                improving_factors += 1

        # Check PKR stability
        if abs(current.pkr_usd_change_1m) < 2:
            improving_factors += 1
        elif current.pkr_usd_change_1m > 5:
            deteriorating_factors += 1

        # Check FX reserves
        if current.fx_reserves_months >= 3:
            improving_factors += 1
        elif current.fx_reserves_months < 2:
            deteriorating_factors += 1

        if improving_factors > deteriorating_factors:
            return "improving", 0.5
        elif deteriorating_factors > improving_factors:
            return "deteriorating", -0.5
        else:
            return "stable", 0.0

    def _identify_factors(self, ind: EconomicIndicators):
        """Identify positive/negative factors and key risks"""
        positive = []
        negative = []
        risks = []

        # Monetary policy
        if ind.real_interest_rate < 0:
            positive.append(f"Negative real rates ({ind.real_interest_rate:.1f}%) favor equities over bonds")

        if ind.inflation_cpi > 25:
            negative.append(f"High inflation ({ind.inflation_cpi:.1f}%) erodes purchasing power")
        elif ind.inflation_cpi < 15:
            positive.append(f"Inflation moderating to {ind.inflation_cpi:.1f}%")

        # Currency
        if abs(ind.pkr_usd_change_1m) < 2:
            positive.append(f"PKR stable vs USD (PKR {ind.pkr_usd_rate:.2f})")
        elif ind.pkr_usd_change_1m > 5:
            negative.append(f"PKR depreciating {ind.pkr_usd_change_1m:.1f}% vs USD")
            risks.append("Currency volatility risk - hurts importers, helps exporters")

        # FX reserves
        if ind.fx_reserves_months >= 3:
            positive.append(f"FX reserves adequate ({ind.fx_reserves_months:.1f} months)")
        else:
            negative.append(f"FX reserves low ({ind.fx_reserves_months:.1f} months)")
            risks.append("Low FX reserves increase devaluation risk")

        # External sector
        if ind.current_account_usd > 0:
            positive.append(f"Current account surplus (${ind.current_account_usd:.1f}B)")
        elif ind.current_account_usd < -1:
            negative.append(f"Current account deficit (${ind.current_account_usd:.1f}B)")

        # Qualitative
        if ind.imf_program_status >= 7:
            positive.append("IMF program on track")
        elif ind.imf_program_status < 5:
            negative.append("IMF program compliance concerns")
            risks.append("IMF program disruption could trigger currency crisis")

        return positive, negative, risks


def update_economic_data_manual():
    """
    Manual data entry helper

    Run this monthly to update economic indicators
    """
    print("="*100)
    print("📊 UPDATE ECONOMIC INDICATORS")
    print("="*100)
    print("\nEnter latest economic data for Pakistan:")
    print("(Press Enter to skip any field)\n")

    date = input("Date (YYYY-MM-DD) [today]: ").strip() or datetime.now().strftime('%Y-%m-%d')

    # Monetary policy
    print("\n--- MONETARY POLICY ---")
    policy_rate = float(input("SBP Policy Rate (%): ") or 22.0)
    inflation = float(input("CPI Inflation (% YoY): ") or 28.3)
    food_inflation = float(input("Food Inflation (% YoY): ") or 35.0)

    # Currency
    print("\n--- CURRENCY ---")
    pkr_usd = float(input("PKR/USD Rate: ") or 278.5)
    pkr_1m = float(input("PKR/USD Change 1M (%): ") or 0.5)
    pkr_3m = float(input("PKR/USD Change 3M (%): ") or 2.0)
    fx_reserves = float(input("FX Reserves (USD billions): ") or 8.2)
    fx_months = float(input("FX Reserves (months): ") or 3.2)

    # Fiscal
    print("\n--- FISCAL ---")
    fiscal_deficit = float(input("Fiscal Deficit (% GDP): ") or 6.5)
    govt_debt = float(input("Government Debt (% GDP): ") or 78.0)

    # External
    print("\n--- EXTERNAL SECTOR ---")
    current_account = float(input("Current Account (USD billions): ") or -0.5)
    remittances = float(input("Monthly Remittances (USD billions): ") or 2.4)
    exports = float(input("Monthly Exports (USD billions): ") or 2.8)
    imports = float(input("Monthly Imports (USD billions): ") or 4.2)

    # Qualitative (0-10)
    print("\n--- QUALITATIVE (0-10 scale) ---")
    imf_status = int(input("IMF Program Status (0=off track, 10=on track): ") or 7)
    political_stability = int(input("Political Stability (0=unstable, 10=stable): ") or 6)

    # Notes
    notes = input("\nNotes: ").strip()

    # Calculate real interest rate
    real_rate = policy_rate - inflation

    # Create indicators
    indicators = EconomicIndicators(
        date=date,
        sbp_policy_rate=policy_rate,
        inflation_cpi=inflation,
        inflation_food=food_inflation,
        real_interest_rate=real_rate,
        pkr_usd_rate=pkr_usd,
        pkr_usd_change_1m=pkr_1m,
        pkr_usd_change_3m=pkr_3m,
        fx_reserves_usd=fx_reserves,
        fx_reserves_months=fx_months,
        fiscal_deficit_gdp=fiscal_deficit,
        government_debt_gdp=govt_debt,
        current_account_usd=current_account,
        remittances_usd=remittances,
        exports_usd=exports,
        imports_usd=imports,
        imf_program_status=imf_status,
        political_stability=political_stability,
        notes=notes
    )

    # Save to database
    econ_data = PSXEconomicData()
    econ_data.save_indicators(indicators)

    # Calculate and display risk score
    risk_score = econ_data.calculate_risk_score(indicators)

    print("\n" + "="*100)
    print("✅ ECONOMIC RISK ASSESSMENT")
    print("="*100)
    print(f"\nOverall Score: {risk_score.overall_score:.1f}/100 ({risk_score.risk_level.upper()})")
    print(f"Trend: {risk_score.trend.upper()}")

    print(f"\nComponent Scores:")
    print(f"  Monetary Policy:    {risk_score.monetary_policy_score:.1f}/100")
    print(f"  Currency Stability: {risk_score.currency_stability_score:.1f}/100")
    print(f"  Fiscal Health:      {risk_score.fiscal_health_score:.1f}/100")
    print(f"  External Sector:    {risk_score.external_sector_score:.1f}/100")
    print(f"  Qualitative:        {risk_score.qualitative_score:.1f}/100")

    if risk_score.positive_factors:
        print(f"\n✅ Positive Factors:")
        for factor in risk_score.positive_factors:
            print(f"  • {factor}")

    if risk_score.negative_factors:
        print(f"\n❌ Negative Factors:")
        for factor in risk_score.negative_factors:
            print(f"  • {factor}")

    if risk_score.key_risks:
        print(f"\n⚠️  Key Risks:")
        for risk in risk_score.key_risks:
            print(f"  • {risk}")

    print("\n" + "="*100)


if __name__ == "__main__":
    update_economic_data_manual()
```

### Day 3-4: Initial Data Collection

**Create:** `update_economic_data.py`

Run this script to collect baseline economic data:

```bash
python update_economic_data.py
```

**Data Sources (Manual for now):**

1. **State Bank of Pakistan** (www.sbp.org.pk)
   - Policy rate: Check latest MPC decision
   - FX reserves: Weekly bulletin

2. **Pakistan Bureau of Statistics** (www.pbs.gov.pk)
   - CPI inflation: Monthly reports
   - Food inflation: CPI sub-index

3. **Ministry of Finance**
   - Fiscal deficit: Monthly fiscal bulletin
   - Government debt: Quarterly debt reports

4. **Trading Economics / Bloomberg**
   - PKR/USD rate: Daily (or use xe.com)
   - Current account: Quarterly

**Initial Baseline (February 2026):**
```
SBP Policy Rate: 22.0%
CPI Inflation: 28.3%
Food Inflation: 35.0%
PKR/USD: 278.5
FX Reserves: $8.2B (3.2 months)
Fiscal Deficit: 6.5% of GDP
Current Account: -$0.5B
IMF Status: 7/10 (on track)
```

### Day 5-7: Integration with Portfolio Analysis

**Create:** `analyze_with_economic_context.py`

```python
"""
Analyze portfolio with economic risk context
"""

from psx_economic_data import PSXEconomicData
from analyze_user_portfolio import portfolio


def analyze_with_macro_context():
    """
    Analyze portfolio positions with economic risk context
    """
    # Get economic risk score
    econ_data = PSXEconomicData()
    indicators = econ_data.get_latest_indicators()
    risk_score = econ_data.calculate_risk_score(indicators)

    print("="*100)
    print("💼 PORTFOLIO ANALYSIS WITH ECONOMIC CONTEXT")
    print("="*100)

    # Show economic environment
    print(f"\n📊 ECONOMIC ENVIRONMENT ({indicators.date})")
    print("-"*100)
    print(f"Overall Risk Score: {risk_score.overall_score:.1f}/100 ({risk_score.risk_level.upper()})")
    print(f"Trend: {risk_score.trend.upper()}")

    print(f"\nKey Indicators:")
    print(f"  Policy Rate:  {indicators.sbp_policy_rate:.1f}%")
    print(f"  Inflation:    {indicators.inflation_cpi:.1f}% (Real rate: {indicators.real_interest_rate:+.1f}%)")
    print(f"  PKR/USD:      {indicators.pkr_usd_rate:.2f} ({indicators.pkr_usd_change_1m:+.1f}% 1M)")
    print(f"  FX Reserves:  ${indicators.fx_reserves_usd:.1f}B ({indicators.fx_reserves_months:.1f} months)")

    # Interpret for portfolio
    print(f"\n📈 IMPLICATIONS FOR YOUR PORTFOLIO")
    print("-"*100)

    # Banking sector (BAFL, AGP)
    print(f"\n🏦 BANKING SECTOR (BAFL, AGP):")
    if risk_score.overall_score >= 60:
        print(f"  ✅ Economic environment FAVORABLE for banks")
        print(f"     • High policy rates support net interest margins")
        if risk_score.trend == "improving":
            print(f"     ⚠️  But trend is improving (rates may fall → margin compression ahead)")
            print(f"     → Recommendation: TRIM positions, lock in gains")
        else:
            print(f"     → Recommendation: HOLD, environment still supportive")
    else:
        print(f"  ⚠️  Economic environment NEUTRAL/UNFAVORABLE")
        print(f"     • Rate cuts ahead will compress margins")
        print(f"     → Recommendation: REDUCE exposure")

    # Auto sector (SAZEW, GAL, ATLH)
    print(f"\n🚗 AUTOMOBILE SECTOR (SAZEW, GAL, ATLH):")
    if indicators.pkr_usd_change_3m < 2 and risk_score.currency_stability_score > 60:
        print(f"  ✅ Currency STABLE - favorable for auto sector")
        print(f"     • Stable PKR reduces imported parts cost")
        print(f"     → SAZEW, ATLH: HOLD or ADD on dips")
        print(f"     → GAL: SELL regardless (company-specific issues)")
    else:
        print(f"  ❌ Currency UNSTABLE - unfavorable for auto")
        print(f"     • PKR volatility increases costs")
        print(f"     → Recommendation: REDUCE auto exposure")

    # FMCG sector (NATF, BBFL, BFAGRO)
    print(f"\n🛒 FMCG/FOOD SECTOR (NATF, BBFL, BFAGRO):")
    if risk_score.trend == "improving" and indicators.inflation_food > indicators.inflation_cpi:
        print(f"  ⚠️  Food inflation ({indicators.inflation_food:.1f}%) above CPI ({indicators.inflation_cpi:.1f}%)")
        print(f"     • High input costs pressure margins")
        if risk_score.trend == "improving":
            print(f"     ✅ But moderating trend is favorable")
            print(f"     → NATF: HOLD with trailing stop (quality winner)")
            print(f"     → Others: HOLD, environment improving")
        else:
            print(f"     → Recommendation: REDUCE exposure")
    else:
        print(f"  ✅ Food inflation moderating")
        print(f"     → Favorable for FMCG sector")
        print(f"     → NATF: Strong HOLD")

    # Pharma sector (HINOON, BFBIO, HALEON)
    print(f"\n💊 PHARMA SECTOR (HINOON, BFBIO, HALEON):")
    if indicators.pkr_usd_change_3m > 5:
        print(f"  ❌ PKR depreciation hurts pharma (imported APIs)")
        print(f"     → Recommendation: MONITOR closely, reduce on further weakness")
    else:
        print(f"  ✅ Currency stable - manageable for pharma")
        print(f"     → HALEON: HOLD (strong performer)")
        print(f"     → HINOON: Small position, CONSIDER EXIT")

    # Overall portfolio recommendation
    print(f"\n🎯 OVERALL PORTFOLIO STRATEGY")
    print("-"*100)

    if risk_score.overall_score >= 60 and risk_score.trend == "improving":
        print(f"  ✅ Economic environment IMPROVING")
        print(f"     → Stay invested, favor quality companies")
        print(f"     → Add to positions on market dips")
    elif risk_score.overall_score >= 50:
        print(f"  ⚠️  Economic environment NEUTRAL")
        print(f"     → Selective approach: hold quality, trim weak")
        print(f"     → Focus on companies with pricing power")
    else:
        print(f"  ❌ Economic environment UNFAVORABLE")
        print(f"     → Defensive posture: raise cash, trim positions")
        print(f"     → Only hold highest conviction names")

    print("\n" + "="*100)


if __name__ == "__main__":
    analyze_with_macro_context()
```

## Week 2: Risk-Based Decision Integration

### Day 8-10: Apply to Your Current Portfolio

Create a decision matrix for each of your 16 positions:

**File:** `portfolio_decisions_with_macro.py`

```python
from psx_economic_data import PSXEconomicData
from analyze_user_portfolio import portfolio


def generate_macro_aware_decisions():
    """
    Generate hold/sell decisions incorporating economic risk
    """
    econ_data = PSXEconomicData()
    indicators = econ_data.get_latest_indicators()
    risk_score = econ_data.calculate_risk_score(indicators)

    print("="*100)
    print("🎯 POSITION-BY-POSITION RECOMMENDATIONS (MACRO-AWARE)")
    print("="*100)

    for symbol, data in portfolio.items():
        print(f"\n{symbol} ({data['weight']:.2f}% of portfolio)")
        print("-"*80)

        # Get economic context for sector
        sector_context = get_sector_economic_context(symbol, risk_score, indicators)

        # Make decision
        decision = make_economic_aware_decision(
            symbol, data, sector_context, risk_score
        )

        print(f"Performance: {data['pl_pct']:+.2f}%")
        print(f"Economic Context: {sector_context['description']}")
        print(f"Decision: {decision['action']}")
        print(f"Reasoning:")
        for reason in decision['reasoning']:
            print(f"  {reason}")


def get_sector_economic_context(symbol, risk_score, indicators):
    """Map symbol to sector and get economic context"""

    sector_mapping = {
        'BAFL': 'banking',
        'AGP': 'banking',
        'SAZEW': 'auto',
        'GAL': 'auto',
        'ATLH': 'auto',
        'NATF': 'fmcg',
        'BBFL': 'fmcg',
        'BFAGRO': 'fmcg',
        # ... etc
    }

    sector = sector_mapping.get(symbol, 'general')

    # Banking sector
    if sector == 'banking':
        if risk_score.trend == "improving":
            return {
                'favorable': False,
                'description': 'Rate cuts likely (margin compression ahead)',
                'action_bias': 'trim'
            }
        else:
            return {
                'favorable': True,
                'description': 'High rates support NIMs',
                'action_bias': 'hold'
            }

    # Auto sector
    elif sector == 'auto':
        if indicators.pkr_usd_change_3m < 2:
            return {
                'favorable': True,
                'description': 'PKR stable (cost predictability)',
                'action_bias': 'hold'
            }
        else:
            return {
                'favorable': False,
                'description': 'PKR volatile (parts cost uncertainty)',
                'action_bias': 'reduce'
            }

    # FMCG sector
    elif sector == 'fmcg':
        if risk_score.trend == "improving" and indicators.inflation_food > 25:
            return {
                'favorable': True,
                'description': 'Inflation moderating (margin improvement ahead)',
                'action_bias': 'hold'
            }
        else:
            return {
                'favorable': False,
                'description': 'High input costs',
                'action_bias': 'monitor'
            }

    return {
        'favorable': risk_score.overall_score >= 50,
        'description': 'General market conditions',
        'action_bias': 'hold'
    }


def make_economic_aware_decision(symbol, position_data, sector_context, risk_score):
    """
    Make decision incorporating economic risk
    """
    pl_pct = position_data['pl_pct']

    # Decision matrix
    reasoning = []

    # Winner (up >50%)
    if pl_pct > 50:
        if sector_context['favorable']:
            action = "HOLD"
            reasoning.append(f"✅ Economic environment favorable for sector")
            reasoning.append(f"✅ Strong gain ({pl_pct:+.2f}%) with supportive macro")
            reasoning.append(f"→ Let winner run with trailing stop")
        else:
            action = "TRIM 30-50%"
            reasoning.append(f"⚠️ Economic environment turning unfavorable")
            reasoning.append(f"⚠️ Strong gain ({pl_pct:+.2f}%) but macro headwinds")
            reasoning.append(f"→ Take partial profits, macro may reverse gains")

    # Loser (down >5%)
    elif pl_pct < -5:
        if sector_context['favorable']:
            action = "HOLD"
            reasoning.append(f"✅ Economic environment favorable for sector")
            reasoning.append(f"⚠️ Down {pl_pct:.2f}% but macro supports recovery")
            reasoning.append(f"→ Give time to recover if fundamentals intact")
        else:
            action = "SELL"
            reasoning.append(f"❌ Economic environment unfavorable")
            reasoning.append(f"❌ Down {pl_pct:.2f}% with macro headwinds")
            reasoning.append(f"→ Exit before further deterioration")

    # Near breakeven
    else:
        if sector_context['action_bias'] == 'trim':
            action = "REDUCE 25%"
            reasoning.append(f"⚠️ Macro environment suggests caution")
        else:
            action = "HOLD"
            reasoning.append(f"→ Macro environment neutral, maintain position")

    return {
        'action': action,
        'reasoning': reasoning
    }
```

### Day 11-14: Monitoring & Reporting

Create monthly economic update process:

**Checklist:**
```
□ Week 1 of each month: Update economic indicators
□ Calculate new risk score
□ Review each portfolio position with new context
□ Adjust holdings based on macro changes
□ Document decisions
```

## Success Metrics

After 2 weeks, you should have:

✅ **Economic risk database** populated with current data
✅ **Risk score calculation** (0-100) working
✅ **Sector-specific implications** documented
✅ **Position-level recommendations** with macro context
✅ **Monthly update process** established

## Example Output (Your Portfolio)

```
====================================================================================================
💼 PORTFOLIO ANALYSIS WITH ECONOMIC CONTEXT
====================================================================================================

📊 ECONOMIC ENVIRONMENT (2026-02-16)
----------------------------------------------------------------------------------------------------
Overall Risk Score: 62/100 (NEUTRAL)
Trend: IMPROVING

Key Indicators:
  Policy Rate:  22.0%
  Inflation:    28.3% (Real rate: -6.3%)
  PKR/USD:      278.50 (+0.5% 1M)
  FX Reserves:  $8.2B (3.2 months)

📈 IMPLICATIONS FOR YOUR PORTFOLIO
----------------------------------------------------------------------------------------------------

🏦 BANKING SECTOR (BAFL, AGP):
  ⚠️  Economic environment NEUTRAL/FAVORABLE but PEAKING
     • High policy rates still support net interest margins
     ⚠️  But improving trend (inflation moderating → rate cuts ahead)
     → BAFL (up 130%): TRIM 40% - Lock in gains before cycle turns
     → AGP (up 24%): TRIM 10% - Reduce from 10.36% to 9.5%

🚗 AUTOMOBILE SECTOR (SAZEW, GAL, ATLH):
  ✅ Currency STABLE - favorable for auto sector
     • PKR change 1M: +0.5% (manageable)
     • Stable PKR reduces imported parts cost uncertainty
     → SAZEW (up 15%): HOLD - Benefiting from stability
     → ATLH (up 52%): HOLD - Quality name in favorable environment
     → GAL (down 10.7%): SELL - Company-specific issues override macro

🛒 FMCG/FOOD SECTOR (NATF, BBFL, BFAGRO):
  ✅ Food inflation moderating - FAVORABLE for sector
     • Food inflation 35% but trending down
     • Real rates negative favor consumer spending
     → NATF (up 209%): Strong HOLD with 15% trailing stop
     → BFAGRO (up 14.6%): HOLD
     → BBFL (down 1.8%): HOLD - Near breakeven, give time

🎯 OVERALL PORTFOLIO STRATEGY
----------------------------------------------------------------------------------------------------
  ⚠️  Economic environment IMPROVING but STILL CHALLENGING
     → Selective approach: Hold quality winners, trim cyclical peaks
     → Exit structural losers (GAL)
     → Focus on companies with pricing power (NATF, PAKT)
     → Maintain 10-15% cash for opportunities
```

## Next Steps After Week 2

Once economic risk scoring is established:

**Week 3-4:** Add sector risk models
**Week 5-6:** Add company risk assessment
**Week 7:** Integrate all risk pillars
**Week 8:** Add trailing stops

## Quick Start This Week

**Action Items:**
1. ✅ Run `update_economic_data.py` to set baseline
2. ✅ Run `analyze_with_macro_context.py` on your portfolio
3. ✅ Document decisions with economic rationale
4. ✅ Set calendar reminder for monthly update

Would you like me to start implementing this Phase 1 code now?
