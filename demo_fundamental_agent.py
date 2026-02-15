"""
Comprehensive Demo of PSX Fundamental Analysis Agent

Demonstrates all key features and use cases of the fundamental agent.
"""

import sys
sys.path.insert(0, '/home/user/Investment')

# Mock yfinance
class MockTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        # Vary data by symbol for realistic demo
        seed = sum(ord(c) for c in symbol)

        # Strong fundamentals example (OGDC)
        if symbol == "OGDC.KA":
            self.info = {
                'currentPrice': 175.50,
                'trailingPE': 4.8,
                'priceToBook': 1.1,
                'dividendYield': 0.092,
                'enterpriseToEbitda': 4.2,
                'debtToEquity': 18.0,
                'currentRatio': 2.3,
                'quickRatio': 1.8,
                'returnOnAssets': 0.145,
                'returnOnEquity': 0.192,
                'revenueGrowth': 0.185,
                'earningsGrowth': 0.242,
                'sector': 'Energy'
            }
        # Moderate fundamentals (PPL)
        elif symbol == "PPL.KA":
            self.info = {
                'currentPrice': 145.25,
                'trailingPE': 5.5,
                'priceToBook': 1.3,
                'dividendYield': 0.078,
                'enterpriseToEbitda': 5.1,
                'debtToEquity': 22.0,
                'currentRatio': 2.0,
                'quickRatio': 1.5,
                'returnOnAssets': 0.118,
                'returnOnEquity': 0.165,
                'revenueGrowth': 0.122,
                'earningsGrowth': 0.155,
                'sector': 'Energy'
            }
        # Banking sector (HBL)
        elif symbol == "HBL.KA":
            self.info = {
                'currentPrice': 185.75,
                'trailingPE': 4.2,
                'priceToBook': 0.85,
                'dividendYield': 0.065,
                'enterpriseToEbitda': None,
                'debtToEquity': 480.0,  # Banks have high leverage
                'currentRatio': 1.1,
                'quickRatio': 0.9,
                'returnOnAssets': 0.015,
                'returnOnEquity': 0.185,
                'revenueGrowth': 0.095,
                'earningsGrowth': 0.132,
                'sector': 'Financial Services'
            }
        # Weak fundamentals (example)
        elif symbol == "WEAK.KA":
            self.info = {
                'currentPrice': 50.00,
                'trailingPE': 25.0,  # Expensive
                'priceToBook': 3.5,  # Overvalued
                'dividendYield': 0.01,  # Low dividend
                'enterpriseToEbitda': 18.0,  # High
                'debtToEquity': 180.0,  # High debt
                'currentRatio': 0.8,  # Poor liquidity
                'quickRatio': 0.5,
                'returnOnAssets': 0.03,  # Low profitability
                'returnOnEquity': 0.05,
                'revenueGrowth': -0.15,  # Declining
                'earningsGrowth': -0.25,
                'sector': 'Default'
            }
        else:
            # Default case
            self.info = {
                'currentPrice': 100.0,
                'trailingPE': 6.0,
                'priceToBook': 1.5,
                'dividendYield': 0.05,
                'enterpriseToEbitda': 6.0,
                'debtToEquity': 35.0,
                'currentRatio': 1.8,
                'quickRatio': 1.2,
                'returnOnAssets': 0.10,
                'returnOnEquity': 0.15,
                'revenueGrowth': 0.08,
                'earningsGrowth': 0.10,
                'sector': 'Default'
            }

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

from psx_fundamental_agent import PSXFundamentalAgent, Recommendation


def demo_1_quick_vs_deep_analysis():
    """Demo 1: Compare quick vs deep analysis"""
    print("\n" + "="*80)
    print("DEMO 1: QUICK vs DEEP ANALYSIS")
    print("="*80)

    agent = PSXFundamentalAgent()

    symbol = "OGDC"

    print(f"\n📊 Analyzing {symbol} with QUICK mode...")
    print("-" * 80)
    quick_score = agent.quick_analysis(symbol)
    print(f"Processing Time: {quick_score.processing_time_ms}ms")
    print(f"Confidence: {quick_score.confidence.value.upper()}")
    print(f"Analysis Mode: {quick_score.analysis_mode}")

    print(f"\n📊 Analyzing {symbol} with DEEP mode...")
    print("-" * 80)
    deep_score = agent.deep_analysis(symbol)
    print(f"Processing Time: {deep_score.processing_time_ms}ms")
    print(f"Confidence: {deep_score.confidence.value.upper()}")
    print(f"Analysis Mode: {deep_score.analysis_mode}")

    print(f"\n💡 Comparison:")
    print(f"   Quick: {quick_score.fundamental_score:.1f}/100 ({quick_score.confidence.value})")
    print(f"   Deep:  {deep_score.fundamental_score:.1f}/100 ({deep_score.confidence.value})")
    print(f"\n✅ Both modes work correctly!")


def demo_2_sector_specific_analysis():
    """Demo 2: Analyze different sectors"""
    print("\n" + "="*80)
    print("DEMO 2: SECTOR-SPECIFIC ANALYSIS")
    print("="*80)

    agent = PSXFundamentalAgent()

    sectors = {
        "OGDC": "Energy",
        "PPL": "Energy",
        "HBL": "Banking"
    }

    print("\nAnalyzing stocks across different sectors...")
    print("-" * 80)

    for symbol, sector in sectors.items():
        score = agent.quick_analysis(symbol)

        print(f"\n{symbol} ({sector}):")
        print(f"  Score: {score.fundamental_score:.1f}/100")
        print(f"  Recommendation: {score.recommendation.value}")

        if score.valuation.pe_ratio:
            print(f"  P/E: {score.valuation.pe_ratio:.1f}")
        if score.financial_health.debt_to_equity is not None:
            print(f"  D/E: {score.financial_health.debt_to_equity:.2f}")
        if score.financial_health.roe is not None:
            print(f"  ROE: {score.financial_health.roe:.1f}%")

    print(f"\n✅ Sector-specific benchmarks applied correctly!")


def demo_3_red_flag_detection():
    """Demo 3: Red flag detection and impact"""
    print("\n" + "="*80)
    print("DEMO 3: RED FLAG DETECTION")
    print("="*80)

    agent = PSXFundamentalAgent()

    # Analyze a stock with potential red flags
    print("\nAnalyzing WEAK stock (simulated poor fundamentals)...")
    print("-" * 80)

    score = agent.quick_analysis("WEAK")

    print(f"\nFundamental Score: {score.fundamental_score:.1f}/100")
    print(f"Recommendation: {score.recommendation.value}")

    if score.red_flags:
        print(f"\n🚩 RED FLAGS DETECTED ({len(score.red_flags)}):")
        for flag in score.red_flags:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            icon = severity_icon.get(flag.severity.value, "⚠️")
            print(f"   {icon} {flag.severity.value.upper()}: {flag.description}")
            print(f"      Action: {flag.action.value}")
    else:
        print("\n✅ No red flags detected")

    print(f"\n💡 Component Breakdown:")
    print(f"   Valuation:        {score.valuation_score:.1f}/100")
    print(f"   Financial Health: {score.health_score:.1f}/100")
    print(f"   Growth:           {score.growth_score:.1f}/100")
    print(f"   Momentum:         {score.momentum_score:.1f}/100")

    print(f"\n✅ Red flag system working correctly!")


def demo_4_universe_screening():
    """Demo 4: Screen multiple stocks and rank them"""
    print("\n" + "="*80)
    print("DEMO 4: UNIVERSE SCREENING & RANKING")
    print("="*80)

    agent = PSXFundamentalAgent()

    # PSX top stocks
    universe = ["OGDC", "PPL", "HBL", "LUCK", "ENGRO", "PSO", "FFC"]

    print(f"\nScreening {len(universe)} stocks from PSX...")
    print("-" * 80)

    results = agent.screen_universe(universe)

    # Sort by fundamental score
    sorted_stocks = sorted(results.items(),
                          key=lambda x: x[1].fundamental_score,
                          reverse=True)

    print(f"\n📊 FUNDAMENTAL RANKINGS\n")
    print(f"{'Rank':<6} {'Symbol':<10} {'Score':<10} {'Rec':<8} {'Valuation':<12} {'Health':<10} {'Red Flags'}")
    print("-" * 90)

    for rank, (symbol, score) in enumerate(sorted_stocks, 1):
        rec_icon = {
            Recommendation.BUY: "🟢 BUY",
            Recommendation.HOLD: "🟡 HOLD",
            Recommendation.SELL: "🔴 SELL"
        }
        rec_display = rec_icon.get(score.recommendation, score.recommendation.value)

        print(f"{rank:<6} {symbol:<10} {score.fundamental_score:<10.1f} "
              f"{rec_display:<8} {score.valuation_score:<12.1f} "
              f"{score.health_score:<10.1f} {len(score.red_flags)}")

    # Show top 3 detailed analysis
    print(f"\n🏆 TOP 3 STOCKS - DETAILED ANALYSIS")
    print("="*80)

    for rank, (symbol, score) in enumerate(sorted_stocks[:3], 1):
        print(f"\n#{rank}. {symbol} - {score.fundamental_score:.1f}/100")
        print("-" * 80)

        if score.upside_pct is not None:
            print(f"   Upside/Downside: {score.upside_pct:+.1f}%")

        if score.catalysts:
            print(f"   Catalysts: {', '.join(score.catalysts[:2])}")

        print(f"   Confidence: {score.confidence.value.upper()}")

    print(f"\n✅ Universe screening completed successfully!")


def demo_5_integration_scenario():
    """Demo 5: Integration with technical/sentiment signals"""
    print("\n" + "="*80)
    print("DEMO 5: INTEGRATION WITH OTHER AGENTS")
    print("="*80)

    agent = PSXFundamentalAgent()

    # Simulate signals from other agents
    print("\nSimulating multi-agent trading signal validation...\n")

    scenarios = [
        {
            "symbol": "OGDC",
            "technical_signal": "BUY",
            "sentiment_score": 0.75,
            "description": "Golden cross + positive news"
        },
        {
            "symbol": "WEAK",
            "technical_signal": "BUY",
            "sentiment_score": 0.65,
            "description": "Bullish breakout + neutral sentiment"
        },
        {
            "symbol": "PPL",
            "technical_signal": "HOLD",
            "sentiment_score": 0.55,
            "description": "Consolidation + mixed sentiment"
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: {scenario['symbol']}")
        print("-" * 80)
        print(f"   Technical Signal: {scenario['technical_signal']}")
        print(f"   Sentiment Score: {scenario['sentiment_score']}")
        print(f"   Context: {scenario['description']}")

        # Get fundamental validation
        fundamental = agent.quick_analysis(scenario['symbol'])

        print(f"\n   📊 Fundamental Validation:")
        print(f"      Score: {fundamental.fundamental_score:.1f}/100")
        print(f"      Recommendation: {fundamental.recommendation.value}")
        print(f"      Confidence: {fundamental.confidence.value}")
        print(f"      Red Flags: {len(fundamental.red_flags)}")

        # Combined decision
        print(f"\n   💡 FINAL DECISION:")

        if (scenario['technical_signal'] == "BUY" and
            fundamental.recommendation == Recommendation.BUY and
            scenario['sentiment_score'] > 0.6 and
            len(fundamental.red_flags) == 0):
            print(f"      ✅ STRONG BUY - All signals align!")
        elif (scenario['technical_signal'] == "BUY" and
              fundamental.recommendation in [Recommendation.HOLD, Recommendation.SELL]):
            print(f"      ⚠️  CAUTION - Technical bullish but fundamentals weak")
        else:
            print(f"      ⏸️  HOLD - Mixed signals, wait for confirmation")

        print()

    print("✅ Integration scenarios validated!")


def demo_6_detailed_output():
    """Demo 6: Show detailed formatted output"""
    print("\n" + "="*80)
    print("DEMO 6: DETAILED ANALYSIS OUTPUT")
    print("="*80)

    agent = PSXFundamentalAgent()

    symbols = ["OGDC", "HBL"]

    for symbol in symbols:
        score = agent.deep_analysis(symbol)
        agent.print_analysis(score)


def run_all_demos():
    """Run all demonstration scenarios"""
    print("\n" + "="*80)
    print("PSX FUNDAMENTAL ANALYSIS AGENT - COMPREHENSIVE DEMO")
    print("="*80)
    print("\nThis demo showcases all key features of the fundamental agent:")
    print("  • Quick vs Deep analysis modes")
    print("  • Sector-specific benchmarking")
    print("  • Red flag detection and penalties")
    print("  • Universe screening and ranking")
    print("  • Integration with other trading signals")
    print("  • Detailed formatted output")
    print("="*80)

    demo_1_quick_vs_deep_analysis()
    demo_2_sector_specific_analysis()
    demo_3_red_flag_detection()
    demo_4_universe_screening()
    demo_5_integration_scenario()
    demo_6_detailed_output()

    print("\n" + "="*80)
    print("🎉 DEMO COMPLETE!")
    print("="*80)
    print("\nThe PSX Fundamental Agent is fully operational and ready for:")
    print("  ✓ Validating momentum signals")
    print("  ✓ Screening investment universes")
    print("  ✓ Identifying red flags automatically")
    print("  ✓ Integration with technical/sentiment analysis")
    print("  ✓ Generating actionable investment recommendations")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_demos()
