#!/usr/bin/env python3
"""
Demo: Economic Risk Scoring System
Shows how to use the economic data module to assess Pakistan's economic environment
"""

from datetime import datetime
from psx_economic_data import EconomicIndicators, PSXEconomicData


def demo_current_scenario():
    """Demo with current Pakistan economic scenario (Feb 2026)"""

    print("=" * 100)
    print("📊 PAKISTAN ECONOMIC RISK SCORING - DEMONSTRATION")
    print("=" * 100)

    # Initialize the economic data manager
    economic_data = PSXEconomicData("portfolio_data/economic_data.db")

    # Create sample indicators based on recent Pakistan economic data
    # These represent a stabilizing economy scenario
    indicators = EconomicIndicators(
        date=datetime.now().strftime("%Y-%m-%d"),

        # Monetary Policy - Easing cycle beginning
        sbp_policy_rate=20.0,           # Down from peak of 22%
        inflation_cpi=24.5,             # Down from 28%+ peak
        inflation_food=26.0,            # Still elevated
        real_interest_rate=-4.5,        # Negative but improving

        # Currency - Stable with IMF program
        pkr_usd_rate=278.5,             # Relatively stable
        pkr_usd_change_1m=0.2,          # Slight depreciation
        pkr_usd_change_3m=1.5,          # Gradual adjustment
        fx_reserves_usd=13.2,           # Building up
        fx_reserves_months=2.5,         # Adequate import cover

        # External Sector - Improving
        current_account_usd=-0.18,      # Narrow deficit (billions)
        remittances_usd=2.65,           # Strong inflows (billions)
        exports_usd=2.5,                # Exports (billions)
        imports_usd=3.85,               # Imports (billions)

        # Fiscal - Challenging but manageable
        fiscal_deficit_gdp=6.3,         # Within IMF targets
        government_debt_gdp=76.5,       # High but stabilizing

        # Qualitative - On-track with reforms
        imf_program_status=7,           # Meeting targets (0-10)
        political_stability=6,          # Moderate stability (0-10)
        data_quality=0.9,
        notes="Stabilizing economy with IMF program on track"
    )

    print("\n📥 INPUT DATA")
    print("-" * 100)
    print(f"Date: {indicators.date}")
    print(f"\nKey Indicators:")
    print(f"  SBP Policy Rate:     {indicators.sbp_policy_rate}%")
    print(f"  CPI Inflation:       {indicators.inflation_cpi}%")
    print(f"  Real Interest Rate:  {indicators.real_interest_rate}%")
    print(f"  PKR/USD Rate:        {indicators.pkr_usd_rate}")
    print(f"  FX Reserves:         ${indicators.fx_reserves_usd}B ({indicators.fx_reserves_months} months)")
    print(f"  IMF Program Status:  {indicators.imf_program_status}/10")

    # Save to database
    economic_data.save_indicators(indicators)
    print("\n✅ Data saved to database")

    # Calculate risk score
    risk_score = economic_data.calculate_risk_score(indicators)

    # Display risk assessment
    print("\n" + "=" * 100)
    print("🎯 ECONOMIC RISK ASSESSMENT")
    print("=" * 100)

    score = risk_score.overall_score
    if score >= 70:
        level_emoji = "🟢"
    elif score >= 50:
        level_emoji = "🟡"
    elif score >= 30:
        level_emoji = "🟠"
    else:
        level_emoji = "🔴"

    print(f"\n{level_emoji} Overall Economic Risk Score: {score:.1f}/100")
    print(f"Risk Level: {risk_score.risk_level.upper()}")
    print(f"Trend: {risk_score.trend.upper()} (Score: {risk_score.trend_score:+.2f})")

    print("\n📊 Component Breakdown:")
    print("-" * 100)

    components = [
        ("Monetary Policy", risk_score.monetary_policy_score, 25),
        ("Currency Stability", risk_score.currency_stability_score, 25),
        ("Fiscal Health", risk_score.fiscal_health_score, 20),
        ("External Sector", risk_score.external_sector_score, 20),
        ("Qualitative Factors", risk_score.qualitative_score, 10)
    ]

    for name, comp_score, weight in components:
        bar_length = int(comp_score / 2)  # 50 chars max
        bar = "█" * bar_length + "░" * (50 - bar_length)
        contribution = comp_score * (weight / 100)
        print(f"{name:.<30} {comp_score:>5.1f}/100 (Weight {weight:>2}%) → {contribution:>5.2f} |{bar}|")

    print("\n✅ Positive Factors:")
    for factor in risk_score.positive_factors:
        print(f"   • {factor}")

    if risk_score.negative_factors:
        print("\n⚠️  Negative Factors:")
        for factor in risk_score.negative_factors:
            print(f"   • {factor}")

    if risk_score.key_risks:
        print("\n🔴 Key Risks:")
        for risk in risk_score.key_risks:
            print(f"   • {risk}")

    # Portfolio implications
    print("\n" + "=" * 100)
    print("💼 PORTFOLIO IMPLICATIONS")
    print("=" * 100)

    if score >= 70:
        print("\n🟢 FAVORABLE Environment - Risk-On")
        print("   Recommended Actions:")
        print("   • INCREASE equity allocation to target levels")
        print("   • ADD to quality growth stocks on dips")
        print("   • Use AGGRESSIVE or BALANCED portfolio model")
        print("   • Focus on cyclicals (Banks, Auto, Cement)")
        print("   • Reduce cash reserves to minimum levels")

    elif score >= 50:
        print("\n🟡 NEUTRAL Environment - Balanced Approach")
        print("   Recommended Actions:")
        print("   • MAINTAIN current equity allocation")
        print("   • HOLD quality positions, trim laggards")
        print("   • Use BALANCED portfolio model")
        print("   • Mix defensive (Pharma, FMCG) with selective growth")
        print("   • Keep moderate cash reserves (10-15%)")

    elif score >= 30:
        print("\n🟠 CAUTIOUS Environment - Risk Management")
        print("   Recommended Actions:")
        print("   • REDUCE exposure to cyclicals and small caps")
        print("   • ROTATE into defensive sectors (Pharma, Utilities)")
        print("   • Use CONSERVATIVE portfolio model")
        print("   • Focus on dividend-paying, low-beta stocks")
        print("   • Increase cash reserves (20-30%)")

    else:
        print("\n🔴 RISK-OFF Environment - Capital Preservation")
        print("   Recommended Actions:")
        print("   • SIGNIFICANTLY REDUCE equity exposure (50%+ of portfolio)")
        print("   • HOLD only highest-quality defensive names")
        print("   • EXIT speculative and small-cap positions")
        print("   • PAUSE new investments until clarity emerges")
        print("   • Raise cash to 40-50% of portfolio")

    # Specific position guidance based on user's actual portfolio
    print("\n📋 Position-Specific Guidance (Based on Current Portfolio):")
    print("-" * 100)

    if score >= 50:
        print("\nFor your current portfolio:")
        print("  • NATF (+209%): HOLD - Fundamentals strong, macro supportive")
        print("  • BAFL (+130%): HOLD - Banking sector benefits from stable rates")
        print("  • ICL (+105%): CONSIDER partial profit-taking if valuation stretched")
        print("  • ATLH (+52%): HOLD - Auto sector recovery aligned with GDP growth")
        print("  • GAL (-10.7%): REVIEW - If fundamentals weak, EXIT regardless of macro")
        print("  • PAEL (-8.0%): REVIEW - Monitor sector headwinds vs. macro recovery")
    else:
        print("\nFor your current portfolio:")
        print("  • NATF (+209%): REDUCE 30-50% - Lock in gains during uncertainty")
        print("  • BAFL (+130%): REDUCE 25-30% - Take profits in banking")
        print("  • ICL (+105%): REDUCE 30% - Trim winners in risk-off environment")
        print("  • GAL (-10.7%): EXIT - Cut losers in unfavorable macro")
        print("  • PAEL (-8.0%): EXIT or REDUCE 50% - Limit exposure to weak positions")

    print("\n" + "=" * 100)

    # Retrieve historical data
    print("\n📈 HISTORICAL DATA")
    print("-" * 100)

    all_indicators = economic_data.get_all_indicators()
    print(f"\nTotal records in database: {len(all_indicators)}")

    if len(all_indicators) > 1:
        print("\nLast 5 entries:")
        for ind in all_indicators[-5:]:
            hist_score = economic_data.calculate_risk_score(ind).overall_score
            print(f"  {ind.date}: Score {hist_score:.1f}/100 "
                  f"(Rates: {ind.sbp_policy_rate}%, Inflation: {ind.inflation_cpi}%, "
                  f"FX: ${ind.fx_reserves_usd}B)")

    print("\n" + "=" * 100)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 100)
    print("\nNext Steps:")
    print("  1. Update with current data:")
    print("     python update_economic_data.py")
    print("  2. Analyze portfolio with macro context:")
    print("     python analyze_with_macro_context.py")
    print("  3. Get position-specific decisions:")
    print("     python portfolio_decisions_with_macro.py")
    print()


def demo_stress_scenarios():
    """Demo different economic scenarios"""

    print("\n" + "=" * 100)
    print("⚡ STRESS SCENARIO ANALYSIS")
    print("=" * 100)

    economic_data = PSXEconomicData("portfolio_data/economic_data.db")

    scenarios = {
        "Crisis": EconomicIndicators(
            date="2026-02-16",
            sbp_policy_rate=25.0,
            inflation_cpi=35.0,
            inflation_food=40.0,
            real_interest_rate=-10.0,
            pkr_usd_rate=320.0,
            pkr_usd_change_1m=8.0,
            pkr_usd_change_3m=15.0,
            fx_reserves_usd=6.5,
            fx_reserves_months=1.5,
            current_account_usd=-0.8,
            remittances_usd=2.0,
            exports_usd=2.0,
            imports_usd=4.5,
            fiscal_deficit_gdp=8.5,
            government_debt_gdp=85.0,
            imf_program_status=3,
            political_stability=3,
            data_quality=0.8,
            notes="Crisis scenario - IMF off track"
        ),
        "Recovery": EconomicIndicators(
            date="2026-02-16",
            sbp_policy_rate=15.0,
            inflation_cpi=12.0,
            inflation_food=14.0,
            real_interest_rate=3.0,
            pkr_usd_rate=275.0,
            pkr_usd_change_1m=-0.5,
            pkr_usd_change_3m=-1.0,
            fx_reserves_usd=18.0,
            fx_reserves_months=3.5,
            current_account_usd=0.15,
            remittances_usd=3.2,
            exports_usd=3.0,
            imports_usd=2.8,
            fiscal_deficit_gdp=4.5,
            government_debt_gdp=70.0,
            imf_program_status=8,
            political_stability=8,
            data_quality=0.95,
            notes="Recovery scenario - strong fundamentals"
        ),
        "Stagnation": EconomicIndicators(
            date="2026-02-16",
            sbp_policy_rate=18.0,
            inflation_cpi=18.0,
            inflation_food=20.0,
            real_interest_rate=0.0,
            pkr_usd_rate=285.0,
            pkr_usd_change_1m=1.0,
            pkr_usd_change_3m=3.0,
            fx_reserves_usd=10.0,
            fx_reserves_months=2.0,
            current_account_usd=-0.1,
            remittances_usd=2.4,
            exports_usd=2.3,
            imports_usd=2.4,
            fiscal_deficit_gdp=6.0,
            government_debt_gdp=78.0,
            imf_program_status=6,
            political_stability=5,
            data_quality=0.85,
            notes="Stagnation scenario - muddling through"
        )
    }

    print("\nComparing three economic scenarios:\n")

    for scenario_name, indicators in scenarios.items():
        risk_score = economic_data.calculate_risk_score(indicators)
        score = risk_score.overall_score

        if score >= 70:
            emoji = "🟢"
        elif score >= 50:
            emoji = "🟡"
        elif score >= 30:
            emoji = "🟠"
        else:
            emoji = "🔴"

        print(f"{emoji} {scenario_name.upper()} Scenario: {score:.1f}/100 - {risk_score.risk_level.upper()}")
        print(f"   Policy Rate: {indicators.sbp_policy_rate}% | "
              f"Inflation: {indicators.inflation_cpi}% | "
              f"PKR/USD: {indicators.pkr_usd_rate} | "
              f"FX: ${indicators.fx_reserves_usd}B | "
              f"IMF: {indicators.imf_program_status}/10")
        print(f"   Components: Monetary {risk_score.monetary_policy_score:.0f} | "
              f"Currency {risk_score.currency_stability_score:.0f} | "
              f"Fiscal {risk_score.fiscal_health_score:.0f} | "
              f"External {risk_score.external_sector_score:.0f} | "
              f"Qualitative {risk_score.qualitative_score:.0f}")
        print()

    print("=" * 100)


if __name__ == "__main__":
    # Run main demo
    demo_current_scenario()

    # Run stress scenarios
    demo_stress_scenarios()
