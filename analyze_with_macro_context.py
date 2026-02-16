#!/usr/bin/env python3
"""
Portfolio Analysis with Macro-Economic Context

Analyzes your portfolio positions considering Pakistan's economic environment.
Identifies positions that are well-aligned or misaligned with macro conditions.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from psx_economic_data import PSXEconomicData, EconomicRiskScore


@dataclass
class PortfolioPosition:
    """Individual stock position"""
    symbol: str
    shares: int
    avg_cost: float
    current_price: float
    sector: str

    @property
    def invested(self) -> float:
        return self.shares * self.avg_cost

    @property
    def current_value(self) -> float:
        return self.shares * self.current_price

    @property
    def gain_loss(self) -> float:
        return self.current_value - self.invested

    @property
    def gain_loss_pct(self) -> float:
        return (self.gain_loss / self.invested) * 100 if self.invested > 0 else 0.0


class PortfolioMacroAnalyzer:
    """Analyzes portfolio positions with macro-economic context"""

    # Sector sensitivities to economic factors (0-100, higher = more sensitive)
    SECTOR_SENSITIVITIES = {
        "Banking": {
            "interest_rates": 90,      # Highly sensitive to rate changes
            "economic_growth": 70,      # Loan growth tied to GDP
            "currency_stability": 60,   # FX exposure moderate
            "political_stability": 80,  # Policy changes impact banks
            "cyclicality": 75           # Cyclical business
        },
        "Auto": {
            "interest_rates": 85,       # Auto loans key driver
            "economic_growth": 95,      # Very cyclical
            "currency_stability": 80,   # Import-dependent
            "political_stability": 70,  # Policy impacts (duties, taxes)
            "cyclicality": 90           # Highly cyclical
        },
        "Cement": {
            "interest_rates": 75,       # Construction financing
            "economic_growth": 85,      # Infrastructure spending
            "currency_stability": 60,   # Some import exposure
            "political_stability": 75,  # Govt projects matter
            "cyclicality": 80           # Cyclical
        },
        "Food": {
            "interest_rates": 40,       # Less sensitive
            "economic_growth": 50,      # Defensive, stable demand
            "currency_stability": 70,   # Import costs (palm oil, etc)
            "political_stability": 60,  # Policy on subsidies
            "cyclicality": 30           # Defensive
        },
        "Fertilizer": {
            "interest_rates": 50,       # Moderate sensitivity
            "economic_growth": 65,      # Ag sector tied to economy
            "currency_stability": 85,   # Heavy import dependence (urea)
            "political_stability": 80,  # Govt pricing/subsidies
            "cyclicality": 60           # Moderate cyclical
        },
        "Pharma": {
            "interest_rates": 30,       # Low sensitivity
            "economic_growth": 40,      # Essential goods, defensive
            "currency_stability": 75,   # APIs imported
            "political_stability": 65,  # Drug pricing policy
            "cyclicality": 25           # Defensive
        },
        "Textiles": {
            "interest_rates": 70,       # Working capital intensive
            "economic_growth": 80,      # Export-dependent
            "currency_stability": 90,   # Major FX exposure
            "political_stability": 75,  # Export incentives matter
            "cyclicality": 75           # Cyclical
        },
        "Oil & Gas": {
            "interest_rates": 50,       # Moderate
            "economic_growth": 70,      # Demand tied to activity
            "currency_stability": 85,   # Oil priced in USD
            "political_stability": 80,  # Pricing policy critical
            "cyclicality": 65           # Moderate cyclical
        },
        "Chemicals": {
            "interest_rates": 60,       # Moderate
            "economic_growth": 75,      # Industrial demand
            "currency_stability": 80,   # Import-heavy
            "political_stability": 70,  # Trade policy
            "cyclicality": 70           # Cyclical
        },
        "Technology": {
            "interest_rates": 65,       # Growth financing
            "economic_growth": 80,      # Discretionary spending
            "currency_stability": 75,   # Import costs
            "political_stability": 60,  # Moderate
            "cyclicality": 70           # Growth-oriented
        }
    }

    def __init__(self, db_path: str = "portfolio_data/economic_data.db"):
        self.economic_data = PSXEconomicData(db_path)

    def calculate_macro_alignment(
        self,
        position: PortfolioPosition,
        risk_score: EconomicRiskScore
    ) -> Dict:
        """
        Calculate how well a position aligns with current macro environment
        Returns alignment score (0-100) and detailed reasoning
        """

        sector = position.sector
        if sector not in self.SECTOR_SENSITIVITIES:
            # Unknown sector, assume moderate sensitivity
            return {
                "alignment_score": 50.0,
                "confidence": "low",
                "reasoning": f"Unknown sector '{sector}', assuming moderate macro sensitivity"
            }

        sensitivities = self.SECTOR_SENSITIVITIES[sector]

        # Get economic indicators
        indicators = self.economic_data.get_latest_indicators()
        if not indicators:
            return {
                "alignment_score": 50.0,
                "confidence": "low",
                "reasoning": "No economic data available"
            }

        # Calculate alignment based on risk score components and sector sensitivities
        # Higher risk score = better environment
        # Higher sensitivity = more impact from environment

        # Interest rate environment (lower rates = better for sensitive sectors)
        rate_score = risk_score.monetary_policy_score
        rate_impact = (rate_score * sensitivities["interest_rates"]) / 100

        # Economic growth (higher growth = better for cyclicals)
        growth_score = (risk_score.overall_score - 50) * 2  # Scale to 0-100
        growth_score = max(0, min(100, growth_score))
        cyclicality_impact = (growth_score * sensitivities["cyclicality"]) / 100

        # Currency stability (stable = better for import-heavy sectors)
        currency_score = risk_score.currency_stability_score
        currency_impact = (currency_score * sensitivities["currency_stability"]) / 100

        # Political stability
        political_score = risk_score.qualitative_score
        political_impact = (political_score * sensitivities["political_stability"]) / 100

        # Weighted average (equal weights for simplicity)
        alignment_score = (
            rate_impact * 0.25 +
            cyclicality_impact * 0.35 +
            currency_impact * 0.25 +
            political_impact * 0.15
        )

        # Generate reasoning
        reasoning_parts = []

        if sensitivities["cyclicality"] >= 70:
            if risk_score.overall_score >= 65:
                reasoning_parts.append(
                    f"✓ Cyclical sector benefits from {risk_score.risk_level} macro environment"
                )
            else:
                reasoning_parts.append(
                    f"✗ Cyclical sector vulnerable in {risk_score.risk_level} environment"
                )

        if sensitivities["interest_rates"] >= 70:
            if indicators.real_interest_rate < -3:
                reasoning_parts.append("✓ Negative real rates supportive")
            elif indicators.real_interest_rate > 3:
                reasoning_parts.append("✗ High real rates headwind")

        if sensitivities["currency_stability"] >= 70:
            if risk_score.currency_stability_score >= 60:
                reasoning_parts.append("✓ Currency stability benefits import-dependent sector")
            else:
                reasoning_parts.append("✗ Currency volatility risk for imports")

        # Position-specific context
        if position.gain_loss_pct > 100:
            if alignment_score < 40:
                reasoning_parts.append(
                    f"⚠️  Large gain (+{position.gain_loss_pct:.1f}%) but macro turning unfavorable"
                )
        elif position.gain_loss_pct < -5:
            if alignment_score > 60:
                reasoning_parts.append(
                    f"💡 Down {abs(position.gain_loss_pct):.1f}% but macro supportive - potential buy opportunity"
                )

        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Neutral outlook"

        confidence = "high" if len(reasoning_parts) >= 2 else "moderate"

        return {
            "alignment_score": alignment_score,
            "confidence": confidence,
            "reasoning": reasoning,
            "sector_sensitivities": sensitivities,
            "economic_factors": {
                "rate_impact": rate_impact,
                "growth_impact": cyclicality_impact,
                "currency_impact": currency_impact,
                "political_impact": political_impact
            }
        }

    def analyze_portfolio(self, positions: List[PortfolioPosition]) -> Dict:
        """Analyze entire portfolio with macro context"""

        # Get latest economic risk score
        risk_score = self.economic_data.get_latest_risk_score()
        indicators = self.economic_data.get_latest_indicators()

        if not risk_score or not indicators:
            return {
                "error": "No economic data available. Run 'python update_economic_data.py' first."
            }

        # Calculate totals
        total_invested = sum(p.invested for p in positions)
        total_current = sum(p.current_value for p in positions)
        total_gain = total_current - total_invested
        total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0

        # Analyze each position
        position_analyses = []
        for position in positions:
            macro_alignment = self.calculate_macro_alignment(position, risk_score)

            position_analyses.append({
                "position": position,
                "macro_alignment": macro_alignment
            })

        # Sort by alignment score (lowest first - most at risk)
        position_analyses.sort(key=lambda x: x["macro_alignment"]["alignment_score"])

        # Categorize positions
        well_aligned = [p for p in position_analyses if p["macro_alignment"]["alignment_score"] >= 60]
        neutral = [p for p in position_analyses if 40 <= p["macro_alignment"]["alignment_score"] < 60]
        misaligned = [p for p in position_analyses if p["macro_alignment"]["alignment_score"] < 40]

        return {
            "risk_score": risk_score,
            "indicators": indicators,
            "portfolio_summary": {
                "total_invested": total_invested,
                "total_current": total_current,
                "total_gain": total_gain,
                "total_gain_pct": total_gain_pct,
                "position_count": len(positions)
            },
            "position_analyses": position_analyses,
            "well_aligned": well_aligned,
            "neutral": neutral,
            "misaligned": misaligned
        }


def print_analysis_report(analysis: Dict):
    """Print comprehensive portfolio analysis report"""

    if "error" in analysis:
        print(f"\n❌ Error: {analysis['error']}")
        return

    risk_score = analysis["risk_score"]
    indicators = analysis["indicators"]
    summary = analysis["portfolio_summary"]

    print("=" * 120)
    print("💼 PORTFOLIO ANALYSIS WITH MACRO-ECONOMIC CONTEXT")
    print("=" * 120)

    # Economic environment
    print(f"\n📊 ECONOMIC ENVIRONMENT")
    print("-" * 120)
    print(f"Date: {risk_score.date}")
    print(f"Overall Risk Score: {risk_score.overall_score:.1f}/100 ({risk_score.risk_level.upper()})")
    print(f"Trend: {risk_score.trend.upper()} (Score: {risk_score.trend_score:+.2f})")
    print(f"\nKey Indicators:")
    print(f"  Policy Rate: {indicators.sbp_policy_rate}% | CPI: {indicators.inflation_cpi}% | "
          f"Real Rate: {indicators.real_interest_rate:+.1f}%")
    print(f"  PKR/USD: {indicators.pkr_usd_rate} | FX Reserves: ${indicators.fx_reserves_usd}B "
          f"({indicators.fx_reserves_months} months)")

    # Portfolio summary
    print(f"\n💰 PORTFOLIO SUMMARY")
    print("-" * 120)
    print(f"Total Invested:    PKR {summary['total_invested']:,.0f}")
    print(f"Current Value:     PKR {summary['total_current']:,.0f}")
    print(f"Total Gain/Loss:   PKR {summary['total_gain']:,.0f} ({summary['total_gain_pct']:+.2f}%)")
    print(f"Position Count:    {summary['position_count']}")

    # Macro alignment summary
    well_aligned_count = len(analysis["well_aligned"])
    neutral_count = len(analysis["neutral"])
    misaligned_count = len(analysis["misaligned"])

    print(f"\n🎯 MACRO ALIGNMENT SUMMARY")
    print("-" * 120)
    print(f"Well-Aligned Positions:  {well_aligned_count} (Alignment Score ≥ 60)")
    print(f"Neutral Positions:       {neutral_count} (Alignment Score 40-59)")
    print(f"Misaligned Positions:    {misaligned_count} (Alignment Score < 40)")

    # Detailed position analysis
    print(f"\n📋 DETAILED POSITION ANALYSIS (Sorted by Macro Alignment)")
    print("=" * 120)

    for i, pa in enumerate(analysis["position_analyses"], 1):
        pos = pa["position"]
        ma = pa["macro_alignment"]

        # Alignment emoji
        if ma["alignment_score"] >= 60:
            align_emoji = "🟢"
        elif ma["alignment_score"] >= 40:
            align_emoji = "🟡"
        else:
            align_emoji = "🔴"

        # P&L emoji
        if pos.gain_loss_pct > 0:
            pl_emoji = "📈"
        else:
            pl_emoji = "📉"

        print(f"\n{i}. {align_emoji} {pos.symbol} ({pos.sector})")
        print(f"   {pl_emoji} Position: {pos.shares} shares @ PKR {pos.avg_cost:.2f} → PKR {pos.current_price:.2f}")
        print(f"   Value: PKR {pos.current_value:,.0f} | Gain/Loss: PKR {pos.gain_loss:,.0f} ({pos.gain_loss_pct:+.2f}%)")
        print(f"   Macro Alignment: {ma['alignment_score']:.1f}/100 ({ma['confidence']} confidence)")
        print(f"   {ma['reasoning']}")

    # Recommendations based on macro alignment
    print(f"\n" + "=" * 120)
    print("💡 MACRO-DRIVEN RECOMMENDATIONS")
    print("=" * 120)

    if risk_score.overall_score >= 65:
        print(f"\n🟢 FAVORABLE Environment ({risk_score.overall_score:.1f}/100) - Risk-On Stance")
        print("   Strategy: Add to well-aligned positions, reduce misaligned holdings")
    elif risk_score.overall_score >= 50:
        print(f"\n🟡 NEUTRAL Environment ({risk_score.overall_score:.1f}/100) - Balanced Approach")
        print("   Strategy: Maintain well-aligned positions, trim misaligned holdings")
    else:
        print(f"\n🔴 UNFAVORABLE Environment ({risk_score.overall_score:.1f}/100) - Risk-Off Stance")
        print("   Strategy: Reduce cyclical exposure, focus on defensive sectors")

    if misaligned_count > 0:
        print(f"\n⚠️  HIGH PRIORITY - Misaligned Positions (Vulnerable to Macro Deterioration):")
        for pa in analysis["misaligned"]:
            pos = pa["position"]
            ma = pa["macro_alignment"]
            action = "REDUCE 30-50%" if pos.gain_loss_pct > 20 else "REVIEW for EXIT"
            print(f"   • {pos.symbol}: {action} - {ma['reasoning']}")

    if len(analysis["well_aligned"]) > 0:
        print(f"\n✅ WELL-POSITIONED - Hold or Add to These Positions:")
        for pa in analysis["well_aligned"]:
            pos = pa["position"]
            ma = pa["macro_alignment"]
            action = "HOLD" if pos.gain_loss_pct > 50 else "CONSIDER ADDING"
            print(f"   • {pos.symbol}: {action} - {ma['reasoning']}")

    print(f"\n" + "=" * 120)
    print("Next Step: Run 'python portfolio_decisions_with_macro.py' for specific BUY/HOLD/SELL decisions")
    print("=" * 120)


def main():
    """Main execution"""

    # User's actual portfolio (from previous analysis)
    portfolio_positions = [
        PortfolioPosition("NATF", 400, 137.95, 426.50, "Food"),
        PortfolioPosition("BAFL", 200, 118.50, 272.80, "Banking"),
        PortfolioPosition("ICL", 500, 95.00, 195.50, "Chemicals"),
        PortfolioPosition("ATLH", 300, 130.00, 198.00, "Auto"),
        PortfolioPosition("FFBL", 250, 75.00, 110.00, "Fertilizer"),
        PortfolioPosition("PSO", 150, 180.00, 247.00, "Oil & Gas"),
        PortfolioPosition("ENGRO", 200, 250.00, 325.00, "Fertilizer"),
        PortfolioPosition("LUCK", 100, 650.00, 950.00, "Cement"),
        PortfolioPosition("MEBL", 400, 95.00, 150.00, "Banking"),
        PortfolioPosition("DGKC", 600, 60.00, 85.00, "Cement"),
        PortfolioPosition("SNGP", 300, 40.00, 55.00, "Oil & Gas"),
        PortfolioPosition("PPL", 250, 85.00, 105.00, "Oil & Gas"),
        PortfolioPosition("EFERT", 200, 70.00, 95.00, "Fertilizer"),
        PortfolioPosition("GAL", 150, 185.00, 165.25, "Auto"),
        PortfolioPosition("PAEL", 300, 65.00, 59.80, "Auto"),
        PortfolioPosition("MTL", 400, 45.00, 48.50, "Textiles"),
    ]

    print("\nLoading portfolio data...")
    print(f"Portfolio: {len(portfolio_positions)} positions")

    # Analyze portfolio
    analyzer = PortfolioMacroAnalyzer()
    analysis = analyzer.analyze_portfolio(portfolio_positions)

    # Print report
    print_analysis_report(analysis)


if __name__ == "__main__":
    main()
