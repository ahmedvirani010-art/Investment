"""
PSX Economic Data Tracker

Collects and tracks Pakistan economic indicators for portfolio risk assessment
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, List, Tuple
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
    positive_factors: List[str]
    negative_factors: List[str]
    key_risks: List[str]

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

    def save_risk_score(self, risk_score: EconomicRiskScore):
        """Save calculated risk score"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO economic_risk_scores
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                risk_score.date,
                risk_score.overall_score,
                risk_score.monetary_policy_score,
                risk_score.currency_stability_score,
                risk_score.fiscal_health_score,
                risk_score.external_sector_score,
                risk_score.qualitative_score,
                risk_score.trend,
                risk_score.trend_score,
                risk_score.risk_level,
                json.dumps(risk_score.positive_factors),
                json.dumps(risk_score.negative_factors),
                json.dumps(risk_score.key_risks)
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

    def get_latest_risk_score(self) -> Optional[EconomicRiskScore]:
        """Get most recent risk score"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM economic_risk_scores
                ORDER BY date DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()
            if not row:
                return None

            return EconomicRiskScore(
                date=row[0],
                overall_score=row[1],
                monetary_policy_score=row[2],
                currency_stability_score=row[3],
                fiscal_health_score=row[4],
                external_sector_score=row[5],
                qualitative_score=row[6],
                trend=row[7],
                trend_score=row[8],
                risk_level=row[9],
                positive_factors=json.loads(row[10]),
                negative_factors=json.loads(row[11]),
                key_risks=json.loads(row[12])
            )

    def get_all_indicators(self, limit: Optional[int] = None) -> List[EconomicIndicators]:
        """Get all economic indicators, optionally limited to most recent N"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if limit:
                query = '''
                    SELECT * FROM economic_indicators
                    ORDER BY date DESC
                    LIMIT ?
                '''
                cursor.execute(query, (limit,))
            else:
                query = '''
                    SELECT * FROM economic_indicators
                    ORDER BY date ASC
                '''
                cursor.execute(query)

            rows = cursor.fetchall()
            if not rows:
                return []

            indicators_list = []
            for row in rows:
                indicators = EconomicIndicators(
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
                indicators_list.append(indicators)

            return indicators_list

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

        risk_score = EconomicRiskScore(
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

        # Save to database
        self.save_risk_score(risk_score)

        return risk_score

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

    def _calculate_trend(self, current: EconomicIndicators) -> Tuple[str, float]:
        """Calculate trend (improving/stable/deteriorating)"""
        improving_factors = 0
        deteriorating_factors = 0

        # Check if inflation is high but with negative real rates (moderating)
        if current.inflation_cpi > 20 and current.real_interest_rate < -5:
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

    def _identify_factors(self, ind: EconomicIndicators) -> Tuple[List[str], List[str], List[str]]:
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
