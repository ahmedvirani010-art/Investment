"""Test strategies with synthetic data"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

sys.path.insert(0, '/home/user/Investment')

from config.technical_config import TechnicalAgentConfig
from strategies.trend_following import TrendFollowingStrategy


def create_uptrend_data(days=200):
    """Create synthetic uptrending data with realistic intraday variation"""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=days, freq='D')

    # Uptrend with noise
    trend = np.linspace(100, 150, days)
    noise = np.random.randn(days) * 3
    close_prices = trend + noise

    # Create realistic OHLC with intraday variation
    high_prices = close_prices + np.abs(np.random.randn(days)) * 2
    low_prices = close_prices - np.abs(np.random.randn(days)) * 2
    open_prices = low_prices + (high_prices - low_prices) * np.random.rand(days)

    df = pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, days)
    })

    df = df.set_index('date')
    return df


if __name__ == "__main__":
    print("="*80)
    print("STRATEGY TEST - SYNTHETIC DATA")
    print("="*80)

    # Create data
    df = create_uptrend_data(200)
    print(f"\n📊 Created synthetic data: {len(df)} days")
    print(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # Initialize strategy
    config = TechnicalAgentConfig()
    strategy = TrendFollowingStrategy(config)

    print(f"\n🎯 Testing {strategy.name}")
    print(f"   Required days: {strategy.get_required_days()}")

    # Analyze
    date = df.index[-1].strftime('%Y-%m-%d')
    signal = strategy.analyze('TEST', df, date)

    # Display results
    print(f"\n🔔 Signal: {signal.signal_type.value}")
    print(f"   Strength: {signal.strength.value}")
    print(f"   Confidence: {signal.confidence:.0%}")

    print(f"\n📊 Indicators:")
    for key, value in signal.metadata.items():
        if isinstance(value, (int, float)):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    if signal.component_signals:
        print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
        for comp in signal.component_signals:
            print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Test complete")
    print("="*80)
