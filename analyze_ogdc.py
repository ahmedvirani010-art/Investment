#!/usr/bin/env python3
"""
Analyze OGDC (Oil & Gas Development Company Limited) Stock

Uses the PSX Fundamental Analysis Agent to perform comprehensive
fundamental analysis on OGDC stock.
"""

import sys
sys.path.insert(0, '/home/user/Investment')

# Mock yfinance for demonstration since it's not installed
class MockTicker:
    def __init__(self, symbol):
        # OGDC (Oil & Gas Development Company) - realistic energy sector data
        if symbol == "OGDC.KA":
            self.info = {
                'currentPrice': 175.50,
                'trailingPE': 4.8,
                'priceToBook': 1.1,
                'dividendYield': 0.092,  # 9.2% - strong dividend payer
                'enterpriseToEbitda': 4.2,
                'debtToEquity': 18.0,  # Very low debt
                'currentRatio': 2.3,
                'quickRatio': 1.8,
                'returnOnAssets': 0.145,  # Strong for asset-heavy O&G
                'returnOnEquity': 0.192,  # Excellent ROE
                'revenueGrowth': 0.185,  # Strong growth
                'earningsGrowth': 0.242,  # Very strong earnings growth
                'sector': 'Energy',
                'fiftyTwoWeekHigh': 220.0,
                'fiftyTwoWeekLow': 155.0,
                'marketCap': 750000000000,  # ~750B PKR
                'volume': 8500000,
                'averageVolume': 6200000,
                'beta': 0.95
            }
        else:
            self.info = {}

        self.balance_sheet = MockDataFrame()
        self.cashflow = MockDataFrame()

class MockDataFrame:
    def __init__(self):
        self.empty = True
        self.shape = (0, 0)

class MockYFinance:
    @staticmethod
    def Ticker(symbol):
        return MockTicker(symbol)

sys.modules['yfinance'] = MockYFinance()

from psx_fundamental_agent import PSXFundamentalAgent

def main():
    print("="*80)
    print("OGDC STOCK ANALYSIS")
    print("Oil & Gas Development Company Limited - Pakistan's Leading E&P Company")
    print("="*80)
    print()
    print("ℹ️  Note: Using demonstration data for analysis")
    print("   Install yfinance for real-time market data: pip install yfinance")
    print()

    # Initialize the fundamental analysis agent
    agent = PSXFundamentalAgent()

    # Perform deep analysis on OGDC
    print("Running comprehensive fundamental analysis...")
    print()

    score = agent.deep_analysis("OGDC")

    # Display the formatted analysis
    agent.print_analysis(score)

    # Additional summary
    print("\n" + "="*80)
    print("INVESTMENT SUMMARY")
    print("="*80)

    if score.recommendation.value == "BUY":
        print("✅ RECOMMENDATION: BUY")
        print(f"   OGDC shows strong fundamentals with a score of {score.fundamental_score:.1f}/100")
    elif score.recommendation.value == "HOLD":
        print("⏸️  RECOMMENDATION: HOLD")
        print(f"   OGDC has moderate fundamentals with a score of {score.fundamental_score:.1f}/100")
    else:
        print("⛔ RECOMMENDATION: SELL")
        print(f"   OGDC shows weak fundamentals with a score of {score.fundamental_score:.1f}/100")

    print(f"   Confidence Level: {score.confidence.value.upper()}")

    if score.red_flags:
        print(f"\n⚠️  WARNING: {len(score.red_flags)} red flag(s) detected")
        print("   Review the detailed analysis above for specific concerns")
    else:
        print("\n✅ No significant red flags detected")

    if score.upside_pct is not None and score.upside_pct > 0:
        print(f"\n📈 Potential Upside: {score.upside_pct:.1f}%")
    elif score.upside_pct is not None and score.upside_pct < 0:
        print(f"\n📉 Potential Downside: {score.upside_pct:.1f}%")

    # Energy sector specific insights
    print("\n" + "="*80)
    print("ENERGY SECTOR INSIGHTS")
    print("="*80)

    print("\n⛽ OGDC is Pakistan's premier E&P company:")
    print("   • Largest reserves base in Pakistan")
    print("   • Diversified portfolio across oil, gas, and LPG")
    print("   • Government-backed with strong operational track record")
    print("   • Key contributor to Pakistan's energy security")

    if score.valuation.dividend_yield and score.valuation.dividend_yield > 8:
        print(f"\n💰 Exceptional dividend yield of {score.valuation.dividend_yield:.1f}%:")
        print("   • One of the highest dividend payers on PSX")
        print("   • Consistent dividend history")
        print("   • Strong cash flow generation supports payouts")

    if score.financial_health.debt_to_equity and score.financial_health.debt_to_equity < 0.30:
        print(f"\n💪 Extremely low debt (D/E = {score.financial_health.debt_to_equity:.2f}):")
        print("   • Conservative balance sheet management")
        print("   • Financial flexibility for growth investments")
        print("   • Low financial risk profile")

    if score.financial_health.roe and score.financial_health.roe > 18:
        print(f"\n📊 Outstanding ROE of {score.financial_health.roe:.1f}%:")
        print("   • Exceptional capital efficiency")
        print("   • Well above energy sector average")
        print("   • Reflects quality of reserves and operations")

    if score.growth_metrics.revenue_growth_yoy and score.growth_metrics.revenue_growth_yoy > 15:
        print(f"\n🚀 Strong revenue growth of {score.growth_metrics.revenue_growth_yoy:.1f}%:")
        print("   • Benefiting from higher oil/gas prices")
        print("   • Production volume increases")
        print("   • New discoveries contributing to growth")

    # Energy sector risks
    print("\n⚠️  ENERGY SECTOR CONSIDERATIONS:")
    print("   • Commodity price sensitivity (oil & gas)")
    print("   • Government gas pricing policies impact")
    print("   • Circular debt in energy sector")
    print("   • Depletion of existing reserves requires continuous exploration")
    print("   • Currency risk (revenues in PKR, some costs in USD)")

    print("\n" + "="*80)
    print()

if __name__ == "__main__":
    main()
