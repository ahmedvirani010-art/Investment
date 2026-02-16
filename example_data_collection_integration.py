"""
Example: Integration of Data Collection with Technical Analysis

This example demonstrates how to:
1. Collect historical price data using the Data Collection Manager
2. Run enhanced technical analysis on the collected data
3. Display comprehensive analysis results

This addresses the "insufficient data" issue we encountered with PPL.
"""

from datetime import datetime
from data_collection import DataCollectionManager
from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig


class DataFramePriceStore:
    """
    Simple price store that wraps a DataFrame

    Used to integrate collected data with PSXTechnicalAgent.
    """

    def __init__(self, symbol: str, data):
        self.symbol = symbol
        self.data = data

    def get_prices(self, symbol, days=250):
        """Return the stored DataFrame"""
        # In a real implementation, this would filter to the requested days
        return self.data


def analyze_with_fresh_data(symbol: str, days: int = 200):
    """
    Collect fresh data and run enhanced technical analysis

    Args:
        symbol: Stock symbol (e.g., "PPL")
        days: Number of days of history to collect

    Returns:
        EnhancedSnapshot with analysis results
    """
    print("="*80)
    print(f"ENHANCED ANALYSIS WITH DATA COLLECTION: {symbol}")
    print("="*80)

    # Step 1: Collect data
    print(f"\n📥 STEP 1: Collecting {days} days of data...")
    print("-"*80)

    manager = DataCollectionManager()
    df = manager.collect(symbol, days=days)

    if df is None or df.empty:
        print(f"❌ Failed to collect data for {symbol}")
        return None

    print(f"✅ Collected {len(df)} days")
    print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"   Latest price: {df['Close'].iloc[-1]:.2f}")

    # Step 2: Run technical analysis
    print(f"\n🔍 STEP 2: Running enhanced technical analysis...")
    print("-"*80)

    config = TechnicalAgentConfig()
    price_store = DataFramePriceStore(symbol, df)
    agent = PSXTechnicalAgent(price_store, config=config)

    snapshot = agent.analyze_symbol_enhanced(symbol)

    # Step 3: Display results
    print(f"\n📊 STEP 3: Analysis Results")
    print("-"*80)

    print(f"\n🎯 OVERALL SIGNAL:")
    print(f"   Bias:       {snapshot.overall_bias.value}")
    print(f"   Confidence: {snapshot.confidence:.0%}")
    print(f"   Score:      {snapshot.ensemble_score:+.3f}")
    print(f"   Regime:     {snapshot.regime}")

    if snapshot.ensemble_signal:
        print(f"\n📋 GROUP CONSENSUS:")
        for group_name, consensus in snapshot.ensemble_signal.group_consensus.items():
            if group_name != 'regime':
                print(f"   {group_name.upper():10s}: {consensus.get('bias', 'N/A'):15s} "
                      f"(score: {consensus.get('score', 0):+.2f}, "
                      f"conf: {consensus.get('confidence', 0):.0%})")

    print(f"\n🔔 STRATEGY SIGNALS:")
    for strat_signal in snapshot.strategy_signals:
        print(f"   {strat_signal.strategy_name:25s}: {strat_signal.signal_type.value:12s} "
              f"(conf: {strat_signal.confidence:.0%})")

    # Interpretation
    print(f"\n💡 INTERPRETATION:")

    if snapshot.confidence >= 0.70:
        conviction = "HIGH"
    elif snapshot.confidence >= 0.50:
        conviction = "MODERATE"
    else:
        conviction = "LOW"

    print(f"   Conviction level: {conviction}")

    if snapshot.overall_bias.value == 'Bullish':
        print(f"   📈 BULLISH signal with {snapshot.confidence:.0%} confidence")

        if snapshot.ensemble_signal:
            trend = snapshot.ensemble_signal.group_consensus.get('trend', {})
            reversion = snapshot.ensemble_signal.group_consensus.get('reversion', {})

            if trend.get('bias') == reversion.get('bias'):
                print(f"   ✅ Both trend and reversion groups agree → Strong conviction")
            else:
                print(f"   ⚠️  Groups disagree → Moderate conviction")

    elif snapshot.overall_bias.value == 'Bearish':
        print(f"   📉 BEARISH signal with {snapshot.confidence:.0%} confidence")

        if snapshot.ensemble_signal:
            trend = snapshot.ensemble_signal.group_consensus.get('trend', {})
            reversion = snapshot.ensemble_signal.group_consensus.get('reversion', {})

            if trend.get('bias') == reversion.get('bias'):
                print(f"   ✅ Both trend and reversion groups agree → Strong conviction")
            else:
                print(f"   ⚠️  Groups disagree → Moderate conviction")

    else:
        print(f"   ↔️  NEUTRAL signal → Wait for clearer direction")

    print(f"\n{'='*80}")
    print("✅ Analysis Complete")
    print(f"{'='*80}")

    return snapshot


def batch_analysis(symbols: list, days: int = 200):
    """
    Run analysis on multiple symbols

    Args:
        symbols: List of stock symbols
        days: Number of days of history

    Returns:
        Dictionary mapping symbol to snapshot
    """
    print("="*80)
    print(f"BATCH ANALYSIS: {len(symbols)} symbols")
    print("="*80)

    # Collect data for all symbols
    manager = DataCollectionManager()
    data_results = manager.collect_batch(symbols, days=days)

    # Run analysis on each
    snapshots = {}

    for symbol, df in data_results.items():
        if df is None or df.empty:
            print(f"\n⚠️  Skipping {symbol} (no data)")
            continue

        print(f"\n{'='*80}")
        print(f"Analyzing {symbol}")
        print(f"{'='*80}")

        price_store = DataFramePriceStore(symbol, df)
        agent = PSXTechnicalAgent(price_store, config=TechnicalAgentConfig())
        snapshot = agent.analyze_symbol_enhanced(symbol)

        snapshots[symbol] = snapshot

        print(f"\n{symbol}: {snapshot.overall_bias.value} ({snapshot.confidence:.0%} confidence)")

    # Summary
    print(f"\n{'='*80}")
    print("BATCH SUMMARY")
    print(f"{'='*80}\n")

    bullish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bullish')
    bearish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bearish')
    neutral = len(snapshots) - bullish - bearish

    print(f"Analyzed: {len(snapshots)}/{len(symbols)} symbols")
    print(f"Bullish:  {bullish}")
    print(f"Bearish:  {bearish}")
    print(f"Neutral:  {neutral}")

    print(f"\nTop Bullish Signals:")
    bullish_signals = [(sym, snap) for sym, snap in snapshots.items()
                      if snap.overall_bias.value == 'Bullish']
    bullish_signals.sort(key=lambda x: x[1].confidence, reverse=True)

    for i, (symbol, snapshot) in enumerate(bullish_signals[:5], 1):
        print(f"  {i}. {symbol}: {snapshot.confidence:.0%} confidence, "
              f"score: {snapshot.ensemble_score:+.2f}")

    print(f"\nTop Bearish Signals:")
    bearish_signals = [(sym, snap) for sym, snap in snapshots.items()
                      if snap.overall_bias.value == 'Bearish']
    bearish_signals.sort(key=lambda x: x[1].confidence, reverse=True)

    for i, (symbol, snapshot) in enumerate(bearish_signals[:5], 1):
        print(f"  {i}. {symbol}: {snapshot.confidence:.0%} confidence, "
              f"score: {snapshot.ensemble_score:+.2f}")

    return snapshots


if __name__ == "__main__":
    import sys

    # Example 1: Single symbol analysis
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 200

        snapshot = analyze_with_fresh_data(symbol, days=days)

    else:
        # Demo: Analyze PPL with proper data
        print("DEMO: Enhanced Analysis with Data Collection")
        print("="*80)
        print("\nThis demo shows how to:")
        print("1. Collect sufficient historical data (200 days)")
        print("2. Run enhanced technical analysis")
        print("3. Get high-confidence signals\n")

        print("To analyze a specific symbol:")
        print("  python example_data_collection_integration.py PPL 200")
        print("\nOr edit this script to import your own CSV data.\n")

        # You can uncomment this to run a demo if you have data
        # snapshot = analyze_with_fresh_data('PPL', days=200)
