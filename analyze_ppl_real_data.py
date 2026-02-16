"""
Run enhanced technical analysis on real PPL data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from io import StringIO

from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig


# Real PPL data from user
PPL_DATA = """Date,Price,Open,High,Low,Vol.,Change %
02/16/2026,232,237,237.6,231,1.11M,-1.81%
02/13/2026,236.27,234,238,228.97,12.91M,-0.38%
02-12-26,237.17,248,249,232.2,16.50M,-4.52%
02-11-26,248.39,252.7,254.74,246.97,2.79M,-1.70%
02-10-26,252.68,256,256.99,251.01,4.73M,-0.46%
02-09-26,253.84,265.56,265.56,247.2,17.06M,-2.92%
02-06-26,261.47,276.5,276.5,259.9,20.34M,-5.01%
02-04-26,275.26,277.01,279.33,273.65,2.50M,-0.72%
02-03-26,277.26,280.4,282.12,276.5,4.69M,-0.74%
02-02-26,279.32,275.15,282,273.8,5.55M,0.71%
01/30/2026,277.34,273.11,284.6,273.03,9.29M,1.91%
01/29/2026,272.15,282,284.2,270.5,13.53M,-3.33%
01/28/2026,281.52,275.77,283.64,275,9.44M,2.91%
01/27/2026,273.56,268.5,276,266.05,8.39M,1.37%
01/26/2026,269.85,270.99,273.85,268,4.55M,-0.78%
01/23/2026,271.97,275.2,276.01,269.25,4.78M,-1.16%
01/22/2026,275.15,274.46,279,270.7,8.39M,0.52%
01/21/2026,273.74,271.5,278.39,271.3,14.59M,0.94%
01/20/2026,271.18,269.79,272.6,262.2,10.70M,2.43%
01/19/2026,264.75,266.5,269.99,263.01,10.54M,0.00%
01/16/2026,264.76,251.51,266,251.1,24.06M,5.95%
01/15/2026,249.88,247.5,253.9,244,14.98M,1.92%
01/14/2026,245.17,240.8,247,239.12,22.57M,2.13%
01/13/2026,240.06,238,241.23,234.25,10.71M,1.28%
01-12-26,237.02,238.29,240.75,236.2,3.86M,-1.36%
01-09-26,240.29,242.7,244,238.5,7.82M,-0.74%
01-08-26,242.07,249,249.4,241,10.77M,-1.82%
01-07-26,246.55,240.8,250.48,240.8,16.96M,2.59%
01-06-26,240.32,243.96,243.97,236.76,18.84M,-1.15%
01-05-26,243.12,244.4,252.5,240.01,12.95M,-0.35%
01-02-26,243.97,236.7,248.5,235.79,13.64M,3.06%
01-01-26,236.73,235.55,239.7,235.1,7.24M,0.50%
12/31/2025,235.55,235.48,238.87,233.15,9.14M,0.34%
12/30/2025,234.76,230.79,235.62,229.61,9.81M,2.19%
12/29/2025,229.73,228.9,230.55,225.75,9.69M,1.04%
12/26/2025,227.36,221.02,228.4,220.5,9.53M,2.87%
12/24/2025,221.02,218.7,222,217.6,4.27M,1.77%
12/23/2025,217.17,219.05,219.49,215.7,3.10M,-0.59%
12/22/2025,218.46,219.51,220.8,217.72,2.31M,-0.40%
12/19/2025,219.33,221.5,224,218.01,5.99M,-0.67%
12/18/2025,220.81,222,222.75,219.25,4.70M,-0.27%
12/17/2025,221.4,224.99,225.75,220.9,6.26M,-1.23%
12/16/2025,224.15,231,232.1,223.41,7.15M,-2.11%
12/15/2025,228.98,224.01,230.79,224.01,18.84M,3.95%
12-12-25,220.27,219.45,222,215.67,10.13M,1.49%
12-11-25,217.04,220,220,215.81,7.20M,0.77%
12-10-25,215.39,218.88,219.49,214.7,4.68M,-1.53%
12-09-25,218.73,221.5,222,217.8,6.84M,-0.32%
12-08-25,219.43,220,223,219,11.86M,0.96%
12-05-25,217.34,213.48,218.9,211,19.15M,3.19%
12-04-25,210.63,208.11,211.99,206.57,4.98M,0.71%
12-03-25,209.14,209,209.99,206,8.11M,0.43%
12-02-25,208.24,213.51,213.51,207.76,11.03M,-2.31%
12-01-25,213.17,212,215.5,208.05,18.63M,1.26%"""


def parse_volume(vol_str):
    """Parse volume strings like '1.11M' to numbers"""
    if isinstance(vol_str, str):
        vol_str = vol_str.strip()
        if vol_str.endswith('M'):
            return float(vol_str[:-1]) * 1_000_000
        elif vol_str.endswith('K'):
            return float(vol_str[:-1]) * 1_000
    return float(vol_str)


def load_ppl_data():
    """Load and parse PPL data"""

    # Read CSV
    df = pd.read_csv(StringIO(PPL_DATA))

    # Parse dates (handle both / and - separators)
    df['Date'] = pd.to_datetime(df['Date'], format='mixed')

    # Set date as index
    df.set_index('Date', inplace=True)

    # Sort by date (oldest first)
    df.sort_index(inplace=True)

    # Parse volume
    df['Volume'] = df['Vol.'].apply(parse_volume)

    # Rename columns to match expected format
    df.rename(columns={
        'Price': 'Close',
    }, inplace=True)

    # Select relevant columns
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    # Convert to numeric
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def analyze_ppl_real():
    """Analyze real PPL data"""

    print("="*80)
    print("ENHANCED TECHNICAL ANALYSIS - PPL (Real Data)")
    print("="*80)

    # Load data
    df = load_ppl_data()

    print(f"\n📊 Data Loaded:")
    print(f"   Period: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"   Days: {len(df)}")
    print(f"   Price: {df['Close'].iloc[0]:.2f} → {df['Close'].iloc[-1]:.2f}")
    print(f"   Change: {(df['Close'].iloc[-1] / df['Close'].iloc[0] - 1)*100:+.1f}%")
    print(f"   Recent (30d): {(df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1)*100:+.1f}%")
    print(f"   High: {df['High'].max():.2f}")
    print(f"   Low: {df['Low'].min():.2f}")

    # Create mock price store
    class MockPriceStore:
        def __init__(self, data):
            self.data = data

        def get_prices(self, symbol, days=250):
            return self.data

    # Initialize agent
    config = TechnicalAgentConfig()
    price_store = MockPriceStore(df)
    agent = PSXTechnicalAgent(price_store, config=config)

    # Run analysis
    print(f"\n🔍 Running enhanced technical analysis...")

    try:
        snapshot = agent.analyze_symbol_enhanced('PPL')
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Display results
    print(f"\n{'='*80}")
    print("🎯 OVERALL SIGNAL")
    print(f"{'='*80}")
    print(f"Overall Bias:     {snapshot.overall_bias.value}")
    print(f"Strength:         {snapshot.ensemble_signal.bias_strength.value if snapshot.ensemble_signal else 'N/A'}")
    print(f"Ensemble Score:   {snapshot.ensemble_score:+.3f}")
    print(f"Confidence:       {snapshot.confidence:.0%}")
    print(f"Regime:           {snapshot.regime}")
    print(f"Agreement:        {snapshot.indicator_values.get('signal_agreement', 0):.0%}")

    # Strategy signals
    print(f"\n📋 STRATEGY SIGNALS ({len(snapshot.strategy_signals)} strategies)")
    print("-" * 80)

    for strat_signal in snapshot.strategy_signals:
        print(f"  {strat_signal.strategy_name:30s}: {strat_signal.signal_type.value:12s} "
              f"(conf: {strat_signal.confidence:.0%}, str: {strat_signal.strength.value})")

        # Show key metadata
        if strat_signal.metadata:
            indicators = []

            if 'adx' in strat_signal.metadata:
                indicators.append(f"ADX={strat_signal.metadata['adx']:.1f}")
            if 'ema8' in strat_signal.metadata:
                indicators.append(f"EMA8={strat_signal.metadata['ema8']:.1f}")
            if 'z_score' in strat_signal.metadata:
                indicators.append(f"Z-score={strat_signal.metadata['z_score']:.2f}")
            if 'rsi_fast' in strat_signal.metadata:
                indicators.append(f"RSI={strat_signal.metadata['rsi_fast']:.1f}")
            if 'momentum_score' in strat_signal.metadata:
                indicators.append(f"Mom={strat_signal.metadata['momentum_score']*100:+.1f}%")
            if 'hurst' in strat_signal.metadata:
                indicators.append(f"Hurst={strat_signal.metadata['hurst']:.3f}")
            if 'regime' in strat_signal.metadata:
                indicators.append(f"Regime={strat_signal.metadata['regime']}")

            if indicators:
                print(f"      └─ {', '.join(indicators)}")

    # Group consensus
    if snapshot.ensemble_signal:
        print(f"\n🔍 GROUP CONSENSUS")
        print("-" * 80)

        for group_name, consensus in snapshot.ensemble_signal.group_consensus.items():
            if group_name != 'regime':
                print(f"  {group_name.upper():10s}: "
                      f"{consensus.get('bias', 'N/A'):18s} "
                      f"(score: {consensus.get('score', 0):+.2f}, "
                      f"conf: {consensus.get('confidence', 0):.0%}, "
                      f"agree: {consensus.get('agreement', 0):.0%})")
            else:
                print(f"  REGIME:     {consensus.get('regime', 'NORMAL'):15s} "
                      f"(ATR ratio: {consensus.get('atr_ratio', 1.0):.2f})")

        # Check for conflict
        if snapshot.ensemble_signal.metadata.get('conflict_detected'):
            print(f"\n⚠️  CONFLICT DETECTED")
            print(f"  Trend vs Reversion groups disagree on direction")
            print(f"  Group Weights: Trend={snapshot.ensemble_signal.metadata['group_weights']['trend']:.0%}, "
                  f"Reversion={snapshot.ensemble_signal.metadata['group_weights']['reversion']:.0%}")
            print(f"  Confidence damped by {config.strategies.conflict_penalty}x")

    # Component signals (top 10)
    if snapshot.signals:
        print(f"\n🔔 TOP COMPONENT SIGNALS (showing {min(10, len(snapshot.signals))} of {len(snapshot.signals)})")
        print("-" * 80)

        for sig in snapshot.signals[:10]:
            print(f"  {sig.indicator:20s}: {sig.signal_type.value:12s} "
                  f"({sig.strength.value}) - {sig.description}")

    # Interpretation
    print(f"\n{'='*80}")
    print("💡 INTERPRETATION")
    print(f"{'='*80}")

    if snapshot.ensemble_signal:
        trend_group = snapshot.ensemble_signal.group_consensus.get('trend', {})
        reversion_group = snapshot.ensemble_signal.group_consensus.get('reversion', {})
        regime = snapshot.ensemble_signal.group_consensus.get('regime', {}).get('regime', 'NORMAL')
    else:
        trend_group = {}
        reversion_group = {}
        regime = 'NORMAL'

    if snapshot.overall_bias.value == 'Bullish':
        print("  📈 BULLISH SIGNAL")
        print(f"     Overall confidence: {snapshot.confidence:.0%}")

        if trend_group and reversion_group and trend_group.get('bias') == reversion_group.get('bias'):
            print("     ✅ Both Trend and Reversion groups agree")
            print("     → High conviction buy signal")
        elif trend_group and reversion_group:
            print(f"     ⚠️  Groups disagree (Trend: {trend_group.get('bias', 'N/A')}, Reversion: {reversion_group.get('bias', 'N/A')})")
            if regime == 'HIGH_VOL':
                print(f"     → High volatility regime favors Trend group")
            print("     → Moderate conviction (conflict reduces confidence)")

    elif snapshot.overall_bias.value == 'Bearish':
        print("  📉 BEARISH SIGNAL")
        print(f"     Overall confidence: {snapshot.confidence:.0%}")

        if trend_group and reversion_group and trend_group.get('bias') == reversion_group.get('bias'):
            print("     ✅ Both Trend and Reversion groups agree")
            print("     → High conviction sell signal")
        elif trend_group and reversion_group:
            print(f"     ⚠️  Groups disagree (Trend: {trend_group.get('bias', 'N/A')}, Reversion: {reversion_group.get('bias', 'N/A')})")
            print("     → Moderate conviction (conflict reduces confidence)")

    else:
        print("  ↔️  NEUTRAL SIGNAL")
        print(f"     Overall confidence: {snapshot.confidence:.0%}")
        print("     Mixed signals or insufficient conviction")

        if snapshot.ensemble_signal and snapshot.ensemble_signal.metadata.get('conflict_detected'):
            print("     ⚠️  Strategy groups in conflict")
            print("     → Wait for clearer signal")

    # Market context
    print(f"\n📊 MARKET CONTEXT:")
    print(f"  Recent trend: Price from 213 → 232 (+8.9% from Dec 1)")
    print(f"  Peak: 282.12 on Feb 3 (recent -17.8% decline)")
    print(f"  Volatility: {regime} regime")

    if snapshot.regime == 'HIGH_VOL':
        print(f"  → High volatility favors trend-following strategies")
    elif snapshot.regime == 'LOW_VOL':
        print(f"  → Low volatility favors mean-reversion strategies")

    print(f"\n{'='*80}")
    print("✅ Analysis Complete")
    print(f"{'='*80}")


if __name__ == "__main__":
    analyze_ppl_real()
