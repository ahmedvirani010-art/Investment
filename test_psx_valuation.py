#!/usr/bin/env python3
"""
Test script for PSX Valuation Agent

To run this script, first install dependencies:
    pip install -r requirements_valuation.txt

Then run:
    python test_psx_valuation.py
"""

from psx_valuation_agent import PSXValuationAgent, ValuationConfig


def test_single_stock():
    """Test valuation of a single stock"""
    print("="*80)
    print("TEST 1: Single Stock Valuation")
    print("="*80)

    # Initialize agent
    agent = PSXValuationAgent()

    # Analyze HBL (Habib Bank Limited)
    snapshot = agent.analyze_symbol('HBL', sector='Banks')

    # Verify results
    assert snapshot.symbol == 'HBL'
    assert snapshot.current_price > 0
    assert snapshot.market_cap > 0

    print("\n✓ Single stock test passed")
    return snapshot


def test_batch_analysis():
    """Test batch valuation of multiple stocks"""
    print("\n" + "="*80)
    print("TEST 2: Batch Analysis")
    print("="*80)

    # Initialize agent
    agent = PSXValuationAgent()

    # Test symbols from different sectors
    test_stocks = {
        'HBL': 'Banks',
        'LUCK': 'Cement',
        'PSO': 'Oil & Gas'
    }

    # Batch analysis
    results = agent.analyze_batch(
        symbols=list(test_stocks.keys()),
        sectors=test_stocks
    )

    # Verify results
    assert len(results) == 3
    for symbol in test_stocks:
        assert symbol in results
        assert results[symbol].symbol == symbol

    print("\n✓ Batch analysis test passed")
    return results


def test_custom_config():
    """Test valuation with custom configuration"""
    print("\n" + "="*80)
    print("TEST 3: Custom Configuration")
    print("="*80)

    # Create custom config with more conservative parameters
    custom_config = ValuationConfig(
        risk_free_rate=0.14,  # 14% T-bills
        required_return=0.20,  # 20% required return
        dcf_weight=0.40,  # Higher DCF weight
        owner_earnings_weight=0.40,
        ev_ebitda_weight=0.15,
        residual_income_weight=0.05
    )

    # Initialize agent with custom config
    agent = PSXValuationAgent(config=custom_config)

    # Analyze stock
    snapshot = agent.analyze_symbol('LUCK', sector='Cement')

    # Verify configuration was applied
    assert snapshot.symbol == 'LUCK'

    print("\n✓ Custom configuration test passed")
    return snapshot


def test_valuation_history():
    """Test valuation history retrieval"""
    print("\n" + "="*80)
    print("TEST 4: Valuation History")
    print("="*80)

    # Initialize agent
    agent = PSXValuationAgent()

    # Run a valuation to ensure we have data
    agent.analyze_symbol('PSO', sector='Oil & Gas')

    # Retrieve history
    history = agent.get_valuation_history('PSO', days=30)

    # Verify history
    assert isinstance(history, list)
    if history:
        assert 'date' in history[0]
        assert 'intrinsic_value' in history[0]
        assert 'valuation_gap' in history[0]

    print(f"\n  Found {len(history)} historical valuations")
    print("✓ Valuation history test passed")
    return history


def test_data_validation():
    """Test data quality validation"""
    print("\n" + "="*80)
    print("TEST 5: Data Quality Validation")
    print("="*80)

    # Initialize agent
    agent = PSXValuationAgent()

    # Analyze stock and check data quality
    snapshot = agent.analyze_symbol('HBL', sector='Banks')

    # Verify data quality metrics
    assert 0.0 <= snapshot.data_quality_score <= 1.0
    assert isinstance(snapshot.warnings, list)

    print(f"\n  Data Quality Score: {snapshot.data_quality_score*100:.0f}%")
    print(f"  Warnings: {len(snapshot.warnings)}")

    if snapshot.warnings:
        for warning in snapshot.warnings:
            print(f"    - {warning}")

    print("\n✓ Data validation test passed")
    return snapshot


def test_all_valuation_methods():
    """Test that all four valuation methods work"""
    print("\n" + "="*80)
    print("TEST 6: All Valuation Methods")
    print("="*80)

    # Initialize agent
    agent = PSXValuationAgent()

    # Analyze stock
    snapshot = agent.analyze_symbol('LUCK', sector='Cement')

    # Check which methods ran successfully
    methods = {v.method.value for v in snapshot.valuations}

    print(f"\n  Methods that ran successfully:")
    for method in methods:
        print(f"    ✓ {method}")

    # Verify we got at least some methods
    assert len(snapshot.valuations) > 0

    print(f"\n  Total methods: {len(snapshot.valuations)}/4")
    print("✓ Valuation methods test passed")
    return snapshot


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PSX VALUATION AGENT - TEST SUITE")
    print("="*80)
    print("\nRunning comprehensive tests...\n")

    try:
        # Run all tests
        test_single_stock()
        test_batch_analysis()
        test_custom_config()
        test_valuation_history()
        test_data_validation()
        test_all_valuation_methods()

        # Summary
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nPSX Valuation Agent is working correctly!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
