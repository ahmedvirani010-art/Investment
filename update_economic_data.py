#!/usr/bin/env python3
"""
Economic Data Update Script
Provides a user-friendly interface for manually entering monthly economic indicators
and generating Pakistan economic risk reports.
"""

import sys
from datetime import datetime
from typing import Optional
from psx_economic_data import EconomicIndicators, PSXEconomicData


class EconomicDataUpdater:
    """Interactive interface for updating economic indicators"""

    def __init__(self, db_path: str = "portfolio_data/economic_data.db"):
        self.economic_data = PSXEconomicData(db_path)
        self.current_date = datetime.now().strftime("%Y-%m-%d")

    def print_header(self):
        """Print welcome header"""
        print("=" * 100)
        print("📊 PAKISTAN ECONOMIC INDICATORS - DATA UPDATE")
        print("=" * 100)
        print(f"\nDate: {self.current_date}")
        print("\nThis script will guide you through entering the latest economic indicators.")
        print("Press Enter to skip any field (will use previous value if available).\n")

    def get_float_input(self, prompt: str, default: Optional[float] = None) -> Optional[float]:
        """Get validated float input from user"""
        while True:
            default_str = f" [{default}]" if default is not None else ""
            user_input = input(f"{prompt}{default_str}: ").strip()

            if not user_input:
                return default

            try:
                return float(user_input)
            except ValueError:
                print("❌ Invalid number. Please try again.")

    def get_string_input(self, prompt: str, default: Optional[str] = None) -> Optional[str]:
        """Get string input from user"""
        default_str = f" [{default}]" if default else ""
        user_input = input(f"{prompt}{default_str}: ").strip()
        return user_input if user_input else default

    def get_previous_data(self) -> Optional[EconomicIndicators]:
        """Get the most recent economic indicators for defaults"""
        latest = self.economic_data.get_latest_indicators()
        return latest

    def collect_indicators(self) -> EconomicIndicators:
        """Interactively collect all economic indicators"""

        # Get previous data for defaults
        prev = self.get_previous_data()

        print("\n" + "=" * 100)
        print("💰 MONETARY POLICY INDICATORS")
        print("=" * 100)

        sbp_policy_rate = self.get_float_input(
            "SBP Policy Rate (%)",
            prev.sbp_policy_rate if prev else 22.0
        )

        print("\n" + "=" * 100)
        print("📈 INFLATION INDICATORS")
        print("=" * 100)

        inflation_cpi = self.get_float_input(
            "CPI Inflation YoY (%)",
            prev.inflation_cpi if prev else 28.0
        )

        inflation_food = self.get_float_input(
            "Food Inflation YoY (%)",
            prev.inflation_food if prev else 30.0
        )

        # Calculate real interest rate
        real_interest_rate = sbp_policy_rate - inflation_cpi

        print("\n" + "=" * 100)
        print("💱 CURRENCY INDICATORS")
        print("=" * 100)

        pkr_usd_rate = self.get_float_input(
            "PKR/USD Exchange Rate",
            prev.pkr_usd_rate if prev else 278.5
        )

        pkr_usd_change_1m = self.get_float_input(
            "PKR/USD 1-Month Change (%)",
            prev.pkr_usd_change_1m if prev else 0.0
        )

        pkr_usd_change_3m = self.get_float_input(
            "PKR/USD 3-Month Change (%)",
            prev.pkr_usd_change_3m if prev else 0.0
        )

        fx_reserves_usd = self.get_float_input(
            "FX Reserves - Total (USD Billion)",
            prev.fx_reserves_usd if prev else 13.0
        )

        fx_reserves_months = self.get_float_input(
            "FX Reserves - Import Cover (Months)",
            prev.fx_reserves_months if prev else 2.5
        )

        print("\n" + "=" * 100)
        print("🏦 EXTERNAL SECTOR INDICATORS")
        print("=" * 100)

        current_account_usd = self.get_float_input(
            "Current Account Balance (USD Billion, monthly)",
            prev.current_account_usd if prev else -0.2
        )

        remittances_usd = self.get_float_input(
            "Worker Remittances (USD Billion, monthly)",
            prev.remittances_usd if prev else 2.5
        )

        exports_usd = self.get_float_input(
            "Exports (USD Billion, monthly)",
            prev.exports_usd if prev else 2.5
        )

        imports_usd = self.get_float_input(
            "Imports (USD Billion, monthly)",
            prev.imports_usd if prev else 4.0
        )

        print("\n" + "=" * 100)
        print("🏛️ FISCAL INDICATORS")
        print("=" * 100)

        fiscal_deficit_gdp = self.get_float_input(
            "Fiscal Deficit (% of GDP, annual)",
            prev.fiscal_deficit_gdp if prev else 6.5
        )

        government_debt_gdp = self.get_float_input(
            "Government Debt (% of GDP)",
            prev.government_debt_gdp if prev else 78.0
        )

        print("\n" + "=" * 100)
        print("🎯 QUALITATIVE SCORES (0-10)")
        print("=" * 100)

        print("\nIMF Program Status:")
        print("  0-3: Off-track or no program")
        print("  4-6: Program active but conditions at risk")
        print("  7-10: On-track, meeting targets")

        imf_program_status = int(self.get_float_input(
            "IMF Program Status Score (0-10)",
            prev.imf_program_status if prev else 7
        ))

        print("\nPolitical Stability:")
        print("  0-3: High instability, policy uncertainty")
        print("  4-6: Moderate stability, some uncertainty")
        print("  7-10: Stable governance, policy continuity")

        political_stability = int(self.get_float_input(
            "Political Stability Score (0-10)",
            prev.political_stability if prev else 6
        ))

        data_quality = self.get_float_input(
            "Data Quality (0.0-1.0, 1.0 = complete/reliable)",
            prev.data_quality if prev else 1.0
        )

        notes = self.get_string_input(
            "Notes (optional)",
            prev.notes if prev else ""
        )

        # Create the indicators object
        indicators = EconomicIndicators(
            date=self.current_date,
            sbp_policy_rate=sbp_policy_rate,
            inflation_cpi=inflation_cpi,
            inflation_food=inflation_food,
            real_interest_rate=real_interest_rate,
            pkr_usd_rate=pkr_usd_rate,
            pkr_usd_change_1m=pkr_usd_change_1m,
            pkr_usd_change_3m=pkr_usd_change_3m,
            fx_reserves_usd=fx_reserves_usd,
            fx_reserves_months=fx_reserves_months,
            current_account_usd=current_account_usd,
            remittances_usd=remittances_usd,
            exports_usd=exports_usd,
            imports_usd=imports_usd,
            fiscal_deficit_gdp=fiscal_deficit_gdp,
            government_debt_gdp=government_debt_gdp,
            imf_program_status=imf_program_status,
            political_stability=political_stability,
            data_quality=data_quality,
            notes=notes
        )

        return indicators

    def confirm_save(self, indicators: EconomicIndicators) -> bool:
        """Display summary and confirm save"""
        print("\n" + "=" * 100)
        print("📋 DATA SUMMARY")
        print("=" * 100)
        print(f"\nDate: {indicators.date}")
        print(f"\nMonetary Policy:")
        print(f"  SBP Policy Rate:     {indicators.sbp_policy_rate}%")
        print(f"  Real Interest Rate:  {indicators.real_interest_rate}%")

        print(f"\nInflation:")
        print(f"  CPI Inflation:       {indicators.inflation_cpi}%")
        print(f"  Food Inflation:      {indicators.inflation_food}%")

        print(f"\nCurrency:")
        print(f"  PKR/USD Rate:        {indicators.pkr_usd_rate}")
        print(f"  1M Change:           {indicators.pkr_usd_change_1m:+.2f}%")
        print(f"  3M Change:           {indicators.pkr_usd_change_3m:+.2f}%")
        print(f"  FX Reserves:         ${indicators.fx_reserves_usd}B ({indicators.fx_reserves_months} months cover)")

        print(f"\nExternal Sector:")
        print(f"  Current Account:     ${indicators.current_account_usd}B")
        print(f"  Remittances:         ${indicators.remittances_usd}B")
        print(f"  Exports:             ${indicators.exports_usd}B")
        print(f"  Imports:             ${indicators.imports_usd}B")
        print(f"  Trade Balance:       ${indicators.exports_usd - indicators.imports_usd:.2f}B")

        print(f"\nFiscal:")
        print(f"  Fiscal Deficit:      {indicators.fiscal_deficit_gdp}% of GDP")
        print(f"  Government Debt:     {indicators.government_debt_gdp}% of GDP")

        print(f"\nQualitative:")
        print(f"  IMF Program:         {indicators.imf_program_status}/10")
        print(f"  Political Stability: {indicators.political_stability}/10")
        print(f"  Data Quality:        {indicators.data_quality:.1f}")
        if indicators.notes:
            print(f"  Notes:               {indicators.notes}")

        print("\n" + "=" * 100)
        response = input("\nSave this data? (yes/no): ").strip().lower()
        return response in ['yes', 'y']

    def print_risk_report(self, indicators: EconomicIndicators):
        """Generate and print economic risk report"""

        # Calculate risk score
        risk_score = self.economic_data.calculate_risk_score(indicators)

        print("\n" + "=" * 100)
        print("🎯 ECONOMIC RISK ASSESSMENT")
        print("=" * 100)

        # Overall score with color coding
        score = risk_score.overall_score
        if score >= 70:
            level = "FAVORABLE"
            emoji = "🟢"
        elif score >= 50:
            level = "NEUTRAL"
            emoji = "🟡"
        elif score >= 30:
            level = "CAUTIOUS"
            emoji = "🟠"
        else:
            level = "RISK-OFF"
            emoji = "🔴"

        print(f"\n{emoji} Overall Risk Score: {score:.1f}/100 - {level}")
        print(f"\nDate: {risk_score.date}")

        print("\n" + "-" * 100)
        print("COMPONENT SCORES")
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
            print(f"{name:.<30} {comp_score:>5.1f}/100 (Weight: {weight}%) |{bar}|")

        print("\n" + "-" * 100)
        print("POSITIVE FACTORS")
        print("-" * 100)
        for factor in risk_score.positive_factors:
            print(f"  ✓ {factor}")

        print("\n" + "-" * 100)
        print("NEGATIVE FACTORS")
        print("-" * 100)
        for factor in risk_score.negative_factors:
            print(f"  ✗ {factor}")

        print("\n" + "-" * 100)
        print("KEY RISKS")
        print("-" * 100)
        for risk in risk_score.key_risks:
            print(f"  ⚠️  {risk}")

        print("\n" + "-" * 100)
        print("PORTFOLIO IMPLICATIONS")
        print("-" * 100)

        if score >= 70:
            print("  • FAVORABLE environment for equity investing")
            print("  • Consider adding to quality positions")
            print("  • Aggressive portfolio model may be appropriate")
            print("  • Focus on growth stocks and cyclicals")
        elif score >= 50:
            print("  • NEUTRAL environment - balanced approach recommended")
            print("  • Maintain current positions in quality names")
            print("  • Use balanced portfolio model")
            print("  • Mix of defensive and growth stocks")
        elif score >= 30:
            print("  • CAUTIOUS environment - defensive positioning")
            print("  • Reduce exposure to cyclicals and small caps")
            print("  • Use conservative portfolio model")
            print("  • Focus on dividend-paying, low-beta stocks")
            print("  • Keep higher cash reserves")
        else:
            print("  • RISK-OFF environment - capital preservation mode")
            print("  • Consider reducing equity exposure significantly")
            print("  • Hold only highest-quality defensive names")
            print("  • Increase cash allocation substantially")
            print("  • Wait for economic clarity before deploying capital")

        print("\n" + "=" * 100)

    def run(self):
        """Main execution flow"""

        self.print_header()

        # Collect indicators
        indicators = self.collect_indicators()

        # Confirm and save
        if self.confirm_save(indicators):
            self.economic_data.save_indicators(indicators)
            print("\n✅ Data saved successfully!")

            # Generate risk report
            self.print_risk_report(indicators)
        else:
            print("\n❌ Data not saved.")
            return

        print("\n" + "=" * 100)
        print("✅ UPDATE COMPLETE")
        print("=" * 100)
        print("\nNext steps:")
        print("  1. Run portfolio analysis with macro context:")
        print("     python analyze_with_macro_context.py")
        print("  2. Get position-specific recommendations:")
        print("     python portfolio_decisions_with_macro.py")
        print()


def main():
    """Main entry point"""

    # Parse command-line arguments
    db_path = "portfolio_data/economic_data.db"

    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python update_economic_data.py [db_path]")
            print("\nInteractive script to update Pakistan economic indicators.")
            print("\nArguments:")
            print("  db_path    Optional path to database (default: portfolio_data/economic_data.db)")
            print("\nData Sources:")
            print("  • State Bank of Pakistan (SBP): https://www.sbp.org.pk")
            print("  • Pakistan Bureau of Statistics (PBS): https://www.pbs.gov.pk")
            print("  • Ministry of Finance: https://www.finance.gov.pk")
            print("  • Trading Economics: https://tradingeconomics.com/pakistan")
            print("\nUpdate Frequency:")
            print("  • Monthly (after official data releases)")
            print("  • SBP monetary policy decisions (every 2 months)")
            print("  • CPI/inflation data (monthly, ~15th of month)")
            print("  • External sector data (monthly, SBP releases)")
            return
        else:
            db_path = sys.argv[1]

    try:
        updater = EconomicDataUpdater(db_path)
        updater.run()
    except KeyboardInterrupt:
        print("\n\n❌ Update cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
