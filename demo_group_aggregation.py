"""
Demonstration: Group-Based Signal Aggregation

Shows how the system handles conflicts between Trend Following and Mean Reversion
strategies using regime-weighted voting.

Creates 3 realistic scenarios:
1. Strong uptrend + overbought (CONFLICT)
2. Oversold + emerging trend (AGREEMENT)
3. Trending market with high volatility (REGIME-WEIGHTED)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig


def create_scenario_1_conflict():
    """
    Scenario 1: Strong uptrend + extreme overbought

    Market has been rallying strongly for weeks, clear uptrend, but RSI is
    extremely overbought. Trend says BUY, mean reversion says SELL.
    """
    print("\n" + "="*80)
    print("SCENARIO 1: CONFLICT - Strong Uptrend + Overbought")
    print("="*80)
    print("Market Context: Price up 20% in 30 days, clear trend but extreme RSI")
    print()

    # Create 200 days of data
    days = 200
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Strong uptrend with recent acceleration
    base = 100
    trend = np.linspace(0, 40, days)  # Moderate trend

    # Add recent acceleration (last 30 days)
    acceleration = np.zeros(days)
    acceleration[-30:] = np.linspace(0, 15, 30)  # Recent spike

    # Small noise
    np.random.seed(42)
    noise = np.random.randn(days) * 2

    close = base + trend + acceleration + noise

    # Ensure positive prices
    close = np.maximum(close, 50)

    df = pd.DataFrame({
        'Open': close * 0.99,
        'High': close * 1.01,
        'Low': close * 0.99,
        'Close': close,
        'Volume': np.random.randint(2000000, 8000000, days)  # High volume
    }, index=dates)

    return df, "Strong uptrend with recent acceleration causing overbought conditions"


def create_scenario_2_agreement():
    """
    Scenario 2: Oversold + emerging uptrend

    Stock was in downtrend, got oversold, now showing early signs of reversal.
    Both trend and reversion strategies agree: BUY.
    """
    print("\n" + "="*80)
    print("SCENARIO 2: AGREEMENT - Oversold + Emerging Uptrend")
    print("="*80)
    print("Market Context: Oversold after decline, now reversing with early trend signals")
    print()

    days = 200
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Downtrend followed by reversal
    np.random.seed(43)

    # First 150 days: downtrend
    downtrend = np.linspace(120, 80, 150)

    # Last 50 days: reversal and new uptrend
    uptrend = np.linspace(80, 95, 50)

    close = np.concatenate([downtrend, uptrend])
    close += np.random.randn(days) * 1.5  # Small noise

    df = pd.DataFrame({
        'Open': close * 0.99,
        'High': close * 1.01,
        'Low': close * 0.99,
        'Close': close,
        'Volume': np.random.randint(1000000, 5000000, days)
    }, index=dates)

    return df, "Recovery from oversold levels with emerging uptrend"


def create_scenario_3_high_vol():
    """
    Scenario 3: Strong trend + high volatility + overbought

    Trending market with high volatility. Regime detection should favor
    trend-following over mean reversion.
    """
    print("\n" + "="*80)
    print("SCENARIO 3: HIGH VOLATILITY - Regime Favors Trend Following")
    print("="*80)
    print("Market Context: Strong uptrend with expanding volatility")
    print()

    days = 200
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(44)

    # Strong trend
    trend = np.linspace(100, 160, days)

    # Increasing volatility (higher noise in recent periods)
    volatility = np.linspace(1, 8, days)
    noise = np.random.randn(days) * volatility

    close = trend + noise
    close = np.maximum(close, 50)

    df = pd.DataFrame({
        'Open': close * 0.98,
        'High': close * 1.03,  # Wider ranges
        'Low': close * 0.97,
        'Close': close,
        'Volume': np.random.randint(3000000, 10000000, days)  # Very high volume
    }, index=dates)

    return df, "Strong trend with expanding volatility"


def analyze_scenario(df, scenario_name, description):
    """Analyze a scenario and display results"""

    # Initialize
    config = TechnicalAgentConfig()

    # Create a mock price store
    class MockPriceStore:
        def get_prices(self, symbol, days=250):
            return df

    price_store = MockPriceStore()
    agent = PSXTechnicalAgent(price_store, config=config)

    # Analyze
    try:
        snapshot = agent.analyze_symbol_enhanced('TEST')
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Display results
    print(f"\n📊 Market Data:")
    print(f"   Price: {df['Close'].iloc[0]:.2f} → {df['Close'].iloc[-1]:.2f}")
    print(f"   Change: {(df['Close'].iloc[-1] / df['Close'].iloc[0] - 1)*100:+.1f}%")
    print(f"   Last 30 days: {(df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1)*100:+.1f}%")
    print(f"   Description: {description}")

    print(f"\n🎯 ENSEMBLE SIGNAL:")
    print(f"   Overall Bias:     {snapshot.overall_bias.value}")
    print(f"   Ensemble Score:   {snapshot.ensemble_score:+.3f}")
    print(f"   Confidence:       {snapshot.confidence:.0%}")
    print(f"   Regime:           {snapshot.regime}")

    print(f"\n📋 Strategy Breakdown:")

    # Group strategies
    trend_strats = []
    reversion_strats = []
    regime_strat = None

    for strat in snapshot.strategy_signals:
        if strat.strategy_name in ['TrendFollowingStrategy', 'MomentumStrategy']:
            trend_strats.append(strat)
        elif strat.strategy_name in ['MeanReversionStrategy', 'StatisticalArbitrageStrategy']:
            reversion_strats.append(strat)
        else:
            regime_strat = strat

    print("\n  TREND Group:")
    for s in trend_strats:
        print(f"    {s.strategy_name:25s}: {s.signal_type.value:12s} (conf: {s.confidence:.0%})")

    print("\n  REVERSION Group:")
    for s in reversion_strats:
        print(f"    {s.strategy_name:25s}: {s.signal_type.value:12s} (conf: {s.confidence:.0%})")

    if regime_strat:
        print(f"\n  REGIME Group:")
        print(f"    {regime_strat.strategy_name:25s}: {regime_strat.signal_type.value:12s} "
              f"(regime: {snapshot.regime})")

    # Interpretation
    print(f"\n💡 INTERPRETATION:")

    # Check for conflict
    trend_bullish = any(s.signal_type.value in ['Bullish'] for s in trend_strats)
    trend_bearish = any(s.signal_type.value in ['Bearish'] for s in trend_strats)
    rev_bullish = any(s.signal_type.value in ['Oversold', 'Bullish'] for s in reversion_strats)
    rev_bearish = any(s.signal_type.value in ['Overbought', 'Bearish'] for s in reversion_strats)

    if (trend_bullish and rev_bearish) or (trend_bearish and rev_bullish):
        print("   ⚠️  CONFLICT DETECTED!")
        print("   Trend and Reversion groups disagree on direction")

        if snapshot.regime == "HIGH_VOL":
            print(f"   → Regime favors TREND group (65% weight)")
            print(f"   → High volatility suggests trend continuation")
        elif snapshot.regime == "LOW_VOL":
            print(f"   → Regime favors REVERSION group (65% weight)")
            print(f"   → Low volatility suggests mean reversion")
        else:
            print(f"   → Equal weighting (50/50) - NORMAL regime")
            print(f"   → Final signal based on slight edge: {snapshot.overall_bias.value}")

        if snapshot.overall_bias.value == "Neutral":
            print(f"   → Result: No clear edge, remain NEUTRAL")

    elif (trend_bullish and rev_bullish) or (trend_bearish and rev_bearish):
        print("   ✅ AGREEMENT!")
        print("   Trend and Reversion groups aligned")
        print(f"   → Signal amplified (confidence boosted by 20%)")
        print(f"   → Strong {snapshot.overall_bias.value} conviction")

    else:
        print(f"   ↔️  Mixed signals or one group neutral")
        print(f"   → Moderate {snapshot.overall_bias.value} bias")

    print("\n" + "-"*80)


if __name__ == "__main__":
    print("="*80)
    print("GROUP-BASED SIGNAL AGGREGATION DEMONSTRATION")
    print("="*80)
    print("\nDemonstrating how the system handles:")
    print("  1. Conflicts between Trend Following and Mean Reversion")
    print("  2. Agreement between strategy groups")
    print("  3. Regime-weighted conflict resolution")

    # Scenario 1: Conflict
    df1, desc1 = create_scenario_1_conflict()
    analyze_scenario(df1, "Scenario 1", desc1)

    # Scenario 2: Agreement
    df2, desc2 = create_scenario_2_agreement()
    analyze_scenario(df2, "Scenario 2", desc2)

    # Scenario 3: High volatility
    df3, desc3 = create_scenario_3_high_vol()
    analyze_scenario(df3, "Scenario 3", desc3)

    print("\n" + "="*80)
    print("✅ Demonstration complete")
    print("="*80)
    print("\nKey Takeaway:")
    print("  The group-based aggregation intelligently resolves conflicts between")
    print("  opposing trading philosophies using market regime context, preventing")
    print("  naive averaging that would lose valuable information from both sides.")
