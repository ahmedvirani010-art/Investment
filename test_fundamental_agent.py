"""
Simple test for PSX Fundamental Agent
Tests the agent with mock data without requiring yfinance
"""

import sys
sys.path.insert(0, '/home/user/Investment')

# Mock yfinance before importing the agent
class MockTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.info = {
            'currentPrice': 100.0,
            'trailingPE': 5.5,
            'priceToBook': 1.2,
            'dividendYield': 0.08,
            'enterpriseToEbitda': 4.5,
            'debtToEquity': 25.0,  # Will be divided by 100
            'currentRatio': 2.1,
            'quickRatio': 1.5,
            'returnOnAssets': 0.12,
            'returnOnEquity': 0.18,
            'revenueGrowth': 0.15,
            'earningsGrowth': 0.22,
            'sector': 'Energy'
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

# Now import the agent
from psx_fundamental_agent import (
    PSXFundamentalAgent,
    Recommendation,
    Confidence,
    RedFlagSeverity
)


def test_quick_analysis():
    """Test quick analysis mode"""
    print("="*80)
    print("TEST 1: Quick Analysis Mode")
    print("="*80)

    agent = PSXFundamentalAgent(cache_ttl_hours=24)

    symbols = ["OGDC", "PPL", "HBL"]

    for symbol in symbols:
        print(f"\nAnalyzing {symbol}...")
        score = agent.quick_analysis(symbol)

        print(f"  Score: {score.fundamental_score:.1f}/100")
        print(f"  Recommendation: {score.recommendation.value}")
        print(f"  Confidence: {score.confidence.value}")
        print(f"  Red Flags: {len(score.red_flags)}")
        print(f"  Processing Time: {score.processing_time_ms}ms")

        # Verify structure
        assert 0 <= score.fundamental_score <= 100, "Score should be 0-100"
        assert score.recommendation in [Recommendation.BUY, Recommendation.HOLD, Recommendation.SELL]
        assert score.confidence in [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW]

    print("\n✅ Quick analysis test passed!")


def test_deep_analysis():
    """Test deep analysis mode"""
    print("\n" + "="*80)
    print("TEST 2: Deep Analysis Mode")
    print("="*80)

    agent = PSXFundamentalAgent(cache_ttl_hours=24)

    symbol = "LUCK"
    print(f"\nDeep analysis of {symbol}...")

    score = agent.deep_analysis(symbol)

    print(f"  Score: {score.fundamental_score:.1f}/100")
    print(f"  Recommendation: {score.recommendation.value}")
    print(f"  Confidence: {score.confidence.value}")
    print(f"  Analysis Mode: {score.analysis_mode}")

    # Deep analysis should have high confidence
    assert score.confidence == Confidence.HIGH, "Deep analysis should have high confidence"
    assert score.analysis_mode == "deep"

    print("\n✅ Deep analysis test passed!")


def test_component_scores():
    """Test individual component scoring"""
    print("\n" + "="*80)
    print("TEST 3: Component Scores")
    print("="*80)

    agent = PSXFundamentalAgent()

    score = agent.quick_analysis("ENGRO")

    print(f"\nComponent Scores for ENGRO:")
    print(f"  Valuation:        {score.valuation_score:.1f}/100")
    print(f"  Financial Health: {score.health_score:.1f}/100")
    print(f"  Growth:           {score.growth_score:.1f}/100")
    print(f"  Momentum:         {score.momentum_score:.1f}/100")

    # Verify all scores are valid
    for component_score in [score.valuation_score, score.health_score,
                            score.growth_score, score.momentum_score]:
        assert 0 <= component_score <= 100, "Component scores should be 0-100"

    print("\n✅ Component scores test passed!")


def test_red_flag_detection():
    """Test red flag detection"""
    print("\n" + "="*80)
    print("TEST 4: Red Flag Detection")
    print("="*80)

    agent = PSXFundamentalAgent()

    # Create mock metrics with red flags
    bad_metrics = {
        'debt_to_equity': 2.0,
        'debt_growth_yoy': 60,
        'current_ratio': 0.8,
        'revenue_growth_yoy': -15,
        'operating_cash_flow': -1000000,
        'quarters_negative_ocf': 3,
        'margin_change_pct': -7,
        'quarters_margin_declining': 2,
        'total_equity': 1000000,
        'current_price': 100
    }

    red_flags = agent._check_red_flags(bad_metrics)

    print(f"\nDetected {len(red_flags)} red flags:")
    for flag in red_flags:
        print(f"  🚩 {flag.severity.value.upper()}: {flag.description}")

    assert len(red_flags) > 0, "Should detect red flags in bad metrics"

    # Test red flag penalties
    base_score = 80.0
    adjusted_score = agent._apply_red_flag_penalties(base_score, red_flags)

    print(f"\nScore adjustment:")
    print(f"  Base score: {base_score:.1f}")
    print(f"  Adjusted score: {adjusted_score:.1f}")
    print(f"  Penalty: {base_score - adjusted_score:.1f} points")

    assert adjusted_score < base_score, "Red flags should reduce score"

    print("\n✅ Red flag detection test passed!")


def test_universe_screening():
    """Test screening multiple stocks"""
    print("\n" + "="*80)
    print("TEST 5: Universe Screening")
    print("="*80)

    agent = PSXFundamentalAgent()

    symbols = ["OGDC", "PPL", "HBL", "LUCK", "ENGRO"]

    print(f"\nScreening {len(symbols)} stocks...")
    results = agent.screen_universe(symbols)

    print(f"\nResults:")
    print(f"{'Symbol':<10} {'Score':<10} {'Recommendation':<15} {'Red Flags'}")
    print("-" * 60)

    for symbol, score in sorted(results.items(),
                                key=lambda x: x[1].fundamental_score,
                                reverse=True):
        print(f"{symbol:<10} {score.fundamental_score:<10.1f} "
              f"{score.recommendation.value:<15} {len(score.red_flags)}")

    assert len(results) == len(symbols), "Should analyze all symbols"

    print("\n✅ Universe screening test passed!")


def test_data_structures():
    """Test data structure completeness"""
    print("\n" + "="*80)
    print("TEST 6: Data Structure Validation")
    print("="*80)

    agent = PSXFundamentalAgent()
    score = agent.quick_analysis("PSO")

    # Verify all required fields exist
    assert score.symbol == "PSO"
    assert score.fundamental_score is not None
    assert score.recommendation is not None
    assert score.confidence is not None
    assert score.valuation is not None
    assert score.financial_health is not None
    assert score.growth_metrics is not None
    assert score.momentum_metrics is not None
    assert isinstance(score.red_flags, list)
    assert isinstance(score.catalysts, list)
    assert score.data_timestamp is not None
    assert 0 <= score.data_quality <= 1.0

    print("\nData structure validation:")
    print(f"  ✓ Symbol: {score.symbol}")
    print(f"  ✓ Score: {score.fundamental_score}")
    print(f"  ✓ Recommendation: {score.recommendation.value}")
    print(f"  ✓ Confidence: {score.confidence.value}")
    print(f"  ✓ Valuation metrics: Present")
    print(f"  ✓ Health metrics: Present")
    print(f"  ✓ Growth metrics: Present")
    print(f"  ✓ Momentum metrics: Present")
    print(f"  ✓ Data quality: {score.data_quality:.2f}")

    print("\n✅ Data structure validation test passed!")


def test_print_analysis():
    """Test the print_analysis method"""
    print("\n" + "="*80)
    print("TEST 7: Print Analysis Output")
    print("="*80)

    agent = PSXFundamentalAgent()
    score = agent.quick_analysis("FFC")

    agent.print_analysis(score)

    print("✅ Print analysis test passed!")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PSX FUNDAMENTAL AGENT - TEST SUITE")
    print("="*80)

    try:
        test_quick_analysis()
        test_deep_analysis()
        test_component_scores()
        test_red_flag_detection()
        test_universe_screening()
        test_data_structures()
        test_print_analysis()

        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nThe PSX Fundamental Agent is working correctly.")
        print("Key features verified:")
        print("  ✓ Quick analysis mode (< 2 min)")
        print("  ✓ Deep analysis mode (comprehensive)")
        print("  ✓ Component scoring (valuation, health, growth, momentum)")
        print("  ✓ Red flag detection and penalties")
        print("  ✓ Universe screening")
        print("  ✓ Data structure completeness")
        print("  ✓ Formatted output")
        print("="*80 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
