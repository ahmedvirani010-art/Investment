#!/usr/bin/env python3
"""
Analyze HBL (Habib Bank Limited) Stock

Uses the PSX Fundamental Analysis Agent to perform comprehensive
fundamental analysis on HBL stock.
"""

import sys
sys.path.insert(0, '/home/user/Investment')

# Mock yfinance for demonstration since it's not installed
class MockTicker:
    def __init__(self, symbol):
        # HBL (Habib Bank Limited) - realistic banking sector data
        if symbol == "HBL.KA":
            self.info = {
                'currentPrice': 185.75,
                'trailingPE': 4.2,
                'priceToBook': 0.85,
                'dividendYield': 0.065,
                'enterpriseToEbitda': None,  # Banks don't use EBITDA
                'debtToEquity': 480.0,  # Banks have high leverage naturally
                'currentRatio': 1.1,
                'quickRatio': 0.9,
                'returnOnAssets': 0.015,  # Banks have lower ROA
                'returnOnEquity': 0.185,  # But good ROE
                'revenueGrowth': 0.095,
                'earningsGrowth': 0.132,
                'sector': 'Financial Services',
                'fiftyTwoWeekHigh': 220.0,
                'fiftyTwoWeekLow': 165.0,
                'marketCap': 270000000000,  # ~270B PKR
                'volume': 2500000,
                'averageVolume': 1800000,
                'beta': 1.15
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
    print("HBL STOCK ANALYSIS")
    print("Habib Bank Limited - Pakistan's Leading Bank")
    print("="*80)
    print()
    print("ℹ️  Note: Using demonstration data for analysis")
    print("   Install yfinance for real-time market data: pip install yfinance")
    print()

    # Initialize the fundamental analysis agent
    agent = PSXFundamentalAgent()

    # Perform deep analysis on HBL
    print("Running comprehensive fundamental analysis...")
    print()

    score = agent.deep_analysis("HBL")

    # Display the formatted analysis
    agent.print_analysis(score)

    # Additional summary
    print("\n" + "="*80)
    print("INVESTMENT SUMMARY")
    print("="*80)

    if score.recommendation.value == "BUY":
        print("✅ RECOMMENDATION: BUY")
        print(f"   HBL shows strong fundamentals with a score of {score.fundamental_score:.1f}/100")
    elif score.recommendation.value == "HOLD":
        print("⏸️  RECOMMENDATION: HOLD")
        print(f"   HBL has moderate fundamentals with a score of {score.fundamental_score:.1f}/100")
    else:
        print("⛔ RECOMMENDATION: SELL")
        print(f"   HBL shows weak fundamentals with a score of {score.fundamental_score:.1f}/100")

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

    # Banking sector specific insights
    print("\n" + "="*80)
    print("BANKING SECTOR INSIGHTS")
    print("="*80)

    print("\n🏦 HBL is Pakistan's largest private sector bank:")
    print("   • Extensive branch network across Pakistan")
    print("   • Strong market position in retail & corporate banking")
    print("   • Significant international presence")

    if score.financial_health.debt_to_equity and score.financial_health.debt_to_equity > 3:
        print("\n📊 High D/E ratio is NORMAL for banks:")
        print("   • Banks are highly leveraged by nature")
        print("   • Deposits are considered 'debt' in banking")
        print("   • Focus on ROE, asset quality, and capital adequacy instead")

    if score.financial_health.roe and score.financial_health.roe > 15:
        print(f"\n💪 Strong ROE of {score.financial_health.roe:.1f}%:")
        print("   • Indicates efficient use of shareholder equity")
        print("   • Above average for Pakistani banking sector")

    if score.valuation.pb_ratio and score.valuation.pb_ratio < 1.0:
        print(f"\n💰 Trading below book value (P/B = {score.valuation.pb_ratio:.2f}):")
        print("   • May indicate undervaluation")
        print("   • Consider asset quality and future earnings potential")

    print("\n" + "="*80)
    print()

if __name__ == "__main__":
    main()
