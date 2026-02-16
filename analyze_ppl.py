"""
Analyze PPL (Pakistan Petroleum Limited) using enhanced technical analysis
with group-based strategy aggregation
"""

import sys
from datetime import datetime

from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig


def analyze_ppl():
    """Run enhanced technical analysis on PPL"""

    print("="*80)
    print("ENHANCED TECHNICAL ANALYSIS - PPL (Pakistan Petroleum)")
    print("="*80)

    # Initialize
    price_store = PSXPriceStore()
    config = TechnicalAgentConfig()
    agent = PSXTechnicalAgent(price_store, config=config)

    symbol = 'PPL'

    print(f"\n📊 Analyzing {symbol}...")
    print(f"   Mode: Enhanced (Group-Based Aggregation)")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d')}")

    # Check if we have data
    df = price_store.get_prices(symbol, days=260)

    if df.empty:
        print(f"\n❌ No data available for {symbol}")
        print("   Please ensure price data is loaded in the database.")
        return

    print(f"   Data: {len(df)} days of price history")
    print(f"   Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
    print(f"   Latest: {df['Close'].iloc[-1]:.2f} ({df.index[-1].strftime('%Y-%m-%d')})")

    # Run enhanced analysis
    try:
        snapshot = agent.analyze_symbol_enhanced(symbol)
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Display results
    print(f"\n{'='*80}")
    print("📈 OVERALL SIGNAL")
    print(f"{'='*80}")
    print(f"Bias:             {snapshot.overall_bias.value}")
    print(f"Ensemble Score:   {snapshot.ensemble_score:+.3f}")
    print(f"Confidence:       {snapshot.confidence:.0%}")
    print(f"Regime:           {snapshot.regime}")
    print(f"Agreement:        {snapshot.indicator_values.get('signal_agreement', 0):.0%}")

    # Strategy breakdown
    print(f"\n📋 STRATEGY SIGNALS ({len(snapshot.strategy_signals)} strategies)")
    print("-" * 80)

    for strat_signal in snapshot.strategy_signals:
        print(f"  {strat_signal.strategy_name:25s}: {strat_signal.signal_type.value:12s} "
              f"(conf: {strat_signal.confidence:.0%}, "
              f"strength: {strat_signal.strength.value})")

        # Show key metadata
        if strat_signal.metadata:
            key_indicators = []

            # Extract relevant indicators based on strategy
            if 'adx' in strat_signal.metadata:
                key_indicators.append(f"ADX={strat_signal.metadata['adx']:.1f}")
            if 'z_score' in strat_signal.metadata:
                key_indicators.append(f"Z-score={strat_signal.metadata['z_score']:.2f}")
            if 'momentum_score' in strat_signal.metadata:
                key_indicators.append(f"Momentum={strat_signal.metadata['momentum_score']*100:+.1f}%")
            if 'regime' in strat_signal.metadata:
                key_indicators.append(f"Regime={strat_signal.metadata['regime']}")
            if 'hurst' in strat_signal.metadata:
                key_indicators.append(f"Hurst={strat_signal.metadata['hurst']:.3f}")

            if key_indicators:
                print(f"      └─ {', '.join(key_indicators)}")

    # Group consensus (if available in metadata)
    print(f"\n🔍 GROUP CONSENSUS")
    print("-" * 80)

    # We need to access the ensemble signal's group consensus
    # For now, let's show strategy grouping

    trend_strategies = ['TrendFollowingStrategy', 'MomentumStrategy']
    reversion_strategies = ['MeanReversionStrategy', 'StatisticalArbitrageStrategy']
    regime_strategies = ['VolatilityStrategy']

    print("\n  TREND Group (Continuation-based):")
    for strat_signal in snapshot.strategy_signals:
        if strat_signal.strategy_name in trend_strategies:
            print(f"    • {strat_signal.strategy_name:25s}: {strat_signal.signal_type.value:12s} "
                  f"(conf: {strat_signal.confidence:.0%})")

    print("\n  REVERSION Group (Mean-reversion based):")
    for strat_signal in snapshot.strategy_signals:
        if strat_signal.strategy_name in reversion_strategies:
            print(f"    • {strat_signal.strategy_name:25s}: {strat_signal.signal_type.value:12s} "
                  f"(conf: {strat_signal.confidence:.0%})")

    print("\n  REGIME Group (Market context):")
    for strat_signal in snapshot.strategy_signals:
        if strat_signal.strategy_name in regime_strategies:
            print(f"    • {strat_signal.strategy_name:25s}: {strat_signal.signal_type.value:12s} "
                  f"(regime: {snapshot.regime})")

    # Key indicators
    print(f"\n📊 KEY INDICATORS")
    print("-" * 80)

    for key, value in list(snapshot.indicator_values.items())[:10]:
        if isinstance(value, (int, float)):
            print(f"  {key:25s}: {value:.3f}")
        else:
            print(f"  {key:25s}: {value}")

    # Component signals
    if snapshot.signals:
        print(f"\n🔔 COMPONENT SIGNALS ({len(snapshot.signals)} signals)")
        print("-" * 80)

        # Group by indicator
        from collections import defaultdict
        signals_by_indicator = defaultdict(list)

        for sig in snapshot.signals:
            signals_by_indicator[sig.indicator].append(sig)

        for indicator, sigs in list(signals_by_indicator.items())[:5]:
            for sig in sigs[:2]:  # Show max 2 per indicator
                print(f"  {sig.indicator:20s}: {sig.signal_type.value:12s} "
                      f"({sig.strength.value}) - {sig.description}")

    print(f"\n{'='*80}")
    print("✅ Analysis complete")
    print(f"{'='*80}")

    # Interpretation
    print(f"\n💡 INTERPRETATION")
    print("-" * 80)

    if snapshot.overall_bias.value == 'Bullish':
        print("  📈 BULLISH signal detected")
        print(f"     Confidence: {snapshot.confidence:.0%}")
        if snapshot.ensemble_score > 0.5:
            print("     Strong upward momentum across multiple strategies")
        else:
            print("     Moderate bullish bias with some divergence")
    elif snapshot.overall_bias.value == 'Bearish':
        print("  📉 BEARISH signal detected")
        print(f"     Confidence: {snapshot.confidence:.0%}")
        if snapshot.ensemble_score < -0.5:
            print("     Strong downward pressure across multiple strategies")
        else:
            print("     Moderate bearish bias with some divergence")
    else:
        print("  ↔️  NEUTRAL signal")
        print(f"     Confidence: {snapshot.confidence:.0%}")
        print("     Mixed signals or insufficient conviction from strategies")

        # Check for conflicts
        if snapshot.indicator_values.get('signal_agreement', 1.0) < 0.5:
            print("     ⚠️  Strategy groups may be in conflict")
            print("        (Trend group vs Reversion group disagreement)")


if __name__ == "__main__":
    analyze_ppl()
