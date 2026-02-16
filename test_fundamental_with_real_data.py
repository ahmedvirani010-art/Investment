"""
Test Fundamental Agent with Real PSX Data
"""

from psx_fundamental_agent import PSXFundamentalAgent

def main():
    print("=" * 70)
    print("FUNDAMENTAL AGENT - TESTING WITH REAL PSX DATA")
    print("=" * 70)
    print()

    # Initialize agent
    agent = PSXFundamentalAgent()
    print()

    # Test with PIBTL (we have real data stored)
    print("Analyzing PIBTL with real PSX data...")
    print("=" * 70)
    print()

    result = agent.quick_analysis("PIBTL")

    print(f"Symbol: {result.symbol}")
    print(f"Recommendation: {result.recommendation.value}")
    print(f"Confidence: {result.confidence.value}")
    print(f"Score: {result.composite_score:.2f}/100")
    print()

    print("COMPONENT SCORES:")
    print(f"  Valuation:       {result.valuation_score:.2f}")
    print(f"  Financial Health: {result.financial_health_score:.2f}")
    print(f"  Growth:          {result.growth_score:.2f}")
    print(f"  Momentum:        {result.momentum_score:.2f}")
    print()

    print("KEY METRICS:")
    print(f"  P/E Ratio:       {result.key_metrics.get('pe_ratio', 'N/A')}")
    print(f"  P/B Ratio:       {result.key_metrics.get('pb_ratio', 'N/A')}")
    print(f"  ROE:             {result.key_metrics.get('roe', 'N/A')}")
    print(f"  Debt/Equity:     {result.key_metrics.get('debt_to_equity', 'N/A')}")
    print(f"  Current Ratio:   {result.key_metrics.get('current_ratio', 'N/A')}")
    print()

    # Check if using real or mock data
    data_source = result.key_metrics.get('_data_source', 'Unknown')
    if data_source == 'PSX_Real_Data':
        print("✓ USING REAL PSX DATA!")
        if 'psx_revenue' in result.key_metrics:
            print(f"  PSX Revenue: PKR {result.key_metrics['psx_revenue']:,.0f}")
        if 'psx_profit_after_tax' in result.key_metrics:
            print(f"  PSX Profit:  PKR {result.key_metrics['psx_profit_after_tax']:,.0f}")
        if 'psx_eps' in result.key_metrics:
            print(f"  PSX EPS:     Rs. {result.key_metrics['psx_eps']:.2f}")
        if 'psx_latest_quarter_eps' in result.key_metrics:
            print(f"  Q1 2026 EPS: Rs. {result.key_metrics['psx_latest_quarter_eps']:.2f}")
    else:
        print(f"⚠ Using {data_source}")

    print()
    print("REASONS:")
    for reason in result.reasons:
        print(f"  • {reason}")

    print()
    print("RED FLAGS:")
    if result.red_flags:
        for flag in result.red_flags:
            print(f"  ⚠ {flag['description']} ({flag['severity']})")
    else:
        print("  ✓ No critical red flags")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
