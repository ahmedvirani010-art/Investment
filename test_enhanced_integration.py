"""
Test PSXTechnicalAgent Enhanced Integration

Tests both basic mode (backward compatible) and enhanced mode.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock price store for testing
class MockPriceStore:
    """Mock price store for testing"""

    def get_prices(self, symbol: str, days: int = 250) -> pd.DataFrame:
        """Generate synthetic price data"""
        # Create date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')[:days]

        # Generate synthetic price data with trend
        np.random.seed(42)
        base_price = 100
        trend = np.linspace(0, 50, days)  # Uptrend
        noise = np.random.randn(days) * 5
        close = base_price + trend + noise

        # OHLCV data
        df = pd.DataFrame({
            'Open': close * 0.98,
            'High': close * 1.02,
            'Low': close * 0.98,
            'Close': close,
            'Volume': np.random.randint(1000000, 5000000, days)
        }, index=dates)

        return df


def test_basic_mode():
    """Test backward-compatible basic mode"""
    print("="*80)
    print("TEST 1: BASIC MODE (Backward Compatible)")
    print("="*80)

    from psx_technical_agent import PSXTechnicalAgent

    # Initialize WITHOUT config (basic mode)
    price_store = MockPriceStore()
    agent = PSXTechnicalAgent(price_store)

    print("\n✓ Agent initialized in basic mode (no config)")
    print(f"   Has config: {agent.config is not None}")
    print(f"   Has strategies: {agent._strategies is not None}")

    # Analyze symbol
    snapshot = agent.analyze_symbol('TEST')

    print(f"\n📊 Basic Analysis Results:")
    print(f"   Symbol: {snapshot.symbol}")
    print(f"   Date: {snapshot.date}")
    print(f"   Overall bias: {snapshot.overall_bias.value}")
    print(f"   Confidence: {snapshot.confidence:.0%}")
    print(f"   Signals: {len(snapshot.signals)}")
    print(f"   Indicator values: {len(snapshot.indicator_values)}")

    if snapshot.signals:
        print(f"\n   Top 3 signals:")
        for sig in snapshot.signals[:3]:
            print(f"      • {sig.indicator}: {sig.signal_type.value} ({sig.strength.value})")

    print("\n✅ Basic mode test PASSED")


def test_enhanced_mode():
    """Test enhanced mode with strategy ensemble"""
    print("\n" + "="*80)
    print("TEST 2: ENHANCED MODE (Strategy Ensemble)")
    print("="*80)

    from psx_technical_agent import PSXTechnicalAgent
    from config.technical_config import TechnicalAgentConfig

    # Initialize WITH config (enhanced mode)
    price_store = MockPriceStore()
    config = TechnicalAgentConfig()
    agent = PSXTechnicalAgent(price_store, config=config)

    print("\n✓ Agent initialized in enhanced mode (with config)")
    print(f"   Has config: {agent.config is not None}")
    print(f"   Min data days: {config.min_data_days}")
    print(f"   Strategy ensemble enabled: {config.use_strategy_ensemble}")

    # Analyze symbol
    snapshot = agent.analyze_symbol_enhanced('TEST')

    print(f"\n📊 Enhanced Analysis Results:")
    print(f"   Symbol: {snapshot.symbol}")
    print(f"   Date: {snapshot.date}")
    print(f"   Overall bias: {snapshot.overall_bias.value}")
    print(f"   Confidence: {snapshot.confidence:.0%}")
    print(f"   Ensemble score: {snapshot.ensemble_score:+.2f}")
    print(f"   Regime: {snapshot.regime}")
    print(f"   Strategy signals: {len(snapshot.strategy_signals)}")
    print(f"   Component signals: {len(snapshot.signals)}")

    print(f"\n📋 Strategy Breakdown:")
    for strategy_name, weight in snapshot.strategy_weights.items():
        # Find matching strategy signal
        strat_signal = next(
            (s for s in snapshot.strategy_signals if s.strategy_name == strategy_name),
            None
        )
        if strat_signal:
            print(f"   • {strategy_name:25s}: {strat_signal.signal_type.value:12s} "
                  f"(conf: {strat_signal.confidence:.0%}, weight: {weight:.0%})")

    print(f"\n📈 Indicator Values:")
    for key, value in list(snapshot.indicator_values.items())[:5]:
        if isinstance(value, (int, float)):
            print(f"   • {key}: {value:.2f}")
        else:
            print(f"   • {key}: {value}")

    print("\n✅ Enhanced mode test PASSED")


def test_batch_analysis():
    """Test batch analysis in both modes"""
    print("\n" + "="*80)
    print("TEST 3: BATCH ANALYSIS")
    print("="*80)

    from psx_technical_agent import PSXTechnicalAgent
    from config.technical_config import TechnicalAgentConfig

    price_store = MockPriceStore()
    symbols = ['TEST1', 'TEST2', 'TEST3']

    # Basic batch
    print("\n📦 Basic Batch Analysis:")
    agent_basic = PSXTechnicalAgent(price_store)
    results_basic = agent_basic.analyze_batch(symbols)
    print(f"   Analyzed: {len(results_basic)} symbols")
    for sym, snap in results_basic.items():
        print(f"   • {sym}: {snap.overall_bias.value} ({len(snap.signals)} signals)")

    # Enhanced batch
    print("\n📦 Enhanced Batch Analysis:")
    config = TechnicalAgentConfig()
    agent_enhanced = PSXTechnicalAgent(price_store, config=config)
    results_enhanced = agent_enhanced.analyze_batch_enhanced(symbols)
    print(f"   Analyzed: {len(results_enhanced)} symbols")
    for sym, snap in results_enhanced.items():
        print(f"   • {sym}: {snap.overall_bias.value} "
              f"(score: {snap.ensemble_score:+.2f}, {len(snap.strategy_signals)} strategies)")

    print("\n✅ Batch analysis test PASSED")


def test_backward_compatibility():
    """Test that existing code still works"""
    print("\n" + "="*80)
    print("TEST 4: BACKWARD COMPATIBILITY")
    print("="*80)

    from psx_technical_agent import PSXTechnicalAgent, SignalType

    price_store = MockPriceStore()
    agent = PSXTechnicalAgent(price_store)  # No config - old style

    # Test all old methods still work
    print("\n✓ Testing old API methods:")

    # analyze_symbol
    snapshot = agent.analyze_symbol('TEST')
    print(f"   • analyze_symbol(): {type(snapshot).__name__}")

    # analyze_batch
    batch = agent.analyze_batch(['TEST1', 'TEST2'])
    print(f"   • analyze_batch(): {len(batch)} results")

    # get_signals
    signals = agent.get_signals('TEST')
    print(f"   • get_signals(): {len(signals)} signals")

    # compute_rsi (direct indicator call)
    df = price_store.get_prices('TEST', days=50)
    rsi = agent.compute_rsi(df)
    print(f"   • compute_rsi(): {rsi:.1f}")

    # compute_macd
    macd, signal, hist = agent.compute_macd(df)
    print(f"   • compute_macd(): MACD={macd:.2f}")

    print("\n✅ Backward compatibility PASSED - all old methods work!")


if __name__ == "__main__":
    print("="*80)
    print("PSX TECHNICAL AGENT - ENHANCED INTEGRATION TEST")
    print("="*80)
    print("\nTesting integration of strategy ensemble with PSXTechnicalAgent")
    print("Verifying backward compatibility and enhanced capabilities\n")

    try:
        test_basic_mode()
        test_enhanced_mode()
        test_batch_analysis()
        test_backward_compatibility()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Basic mode works (backward compatible)")
        print("  ✓ Enhanced mode works (strategy ensemble)")
        print("  ✓ Batch analysis works for both modes")
        print("  ✓ Backward compatibility maintained")
        print("\nIntegration successful! 🎉")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
