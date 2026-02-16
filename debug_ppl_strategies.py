"""
Debug why strategies are returning neutral for PPL
"""

import pandas as pd
from datetime import datetime
from io import StringIO

from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.momentum import MomentumStrategy
from config.technical_config import TechnicalAgentConfig


# Real PPL data
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
    df = pd.read_csv(StringIO(PPL_DATA))
    df['Date'] = pd.to_datetime(df['Date'], format='mixed')
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    df['Volume'] = df['Vol.'].apply(parse_volume)
    df.rename(columns={'Price': 'Close'}, inplace=True)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def debug_mean_reversion():
    """Debug mean reversion strategy"""
    print("="*80)
    print("DEBUGGING MEAN REVERSION STRATEGY")
    print("="*80)

    df = load_ppl_data()
    config = TechnicalAgentConfig()
    strategy = MeanReversionStrategy(config)

    print(f"\nData: {len(df)} days")
    print(f"Required: {strategy.get_required_days()} days")
    print(f"Current price: {df['Close'].iloc[-1]:.2f}")

    # Manually compute Z-score
    lookback = config.indicators.z_score_window
    prices = df['Close']
    mean = prices.rolling(lookback).mean().iloc[-1]
    std = prices.rolling(lookback).std().iloc[-1]
    z_score = (prices.iloc[-1] - mean) / std if std > 0 else 0

    print(f"\nZ-Score Calculation:")
    print(f"  Lookback: {lookback} days")
    print(f"  Mean: {mean:.2f}")
    print(f"  Std: {std:.2f}")
    print(f"  Current: {prices.iloc[-1]:.2f}")
    print(f"  Z-Score: {z_score:.2f}")
    print(f"  Oversold threshold: {config.strategies.z_score_oversold}")
    print(f"  Overbought threshold: {config.strategies.z_score_overbought}")

    # Check RSI
    from indicators.advanced_indicators import AdvancedIndicators
    indicators = AdvancedIndicators(config)
    rsi_fast = indicators.compute_dual_rsi(df)['rsi_fast'].iloc[-1]
    rsi_slow = indicators.compute_dual_rsi(df)['rsi_slow'].iloc[-1]

    print(f"\nRSI:")
    print(f"  Fast RSI (9): {rsi_fast:.1f}")
    print(f"  Slow RSI (21): {rsi_slow:.1f}")
    print(f"  Oversold: {config.strategies.rsi_oversold}")
    print(f"  Overbought: {config.strategies.rsi_overbought}")

    # Check Hurst
    hurst = indicators.compute_hurst_exponent(df)
    print(f"\nHurst Exponent: {hurst:.3f}")
    print(f"  < 0.5: mean reverting")
    print(f"  = 0.5: random walk")
    print(f"  > 0.5: trending")

    # Run strategy
    print(f"\n" + "-"*80)
    print("RUNNING STRATEGY...")
    print("-"*80)

    signal = strategy.analyze('PPL', df, df.index[-1].strftime('%Y-%m-%d'))

    print(f"\nResult:")
    print(f"  Signal: {signal.signal_type.value}")
    print(f"  Strength: {signal.strength.value}")
    print(f"  Confidence: {signal.confidence:.0%}")
    print(f"  Component signals: {len(signal.component_signals)}")

    for comp in signal.component_signals:
        print(f"    - {comp.indicator}: {comp.signal_type.value} ({comp.strength.value})")


if __name__ == "__main__":
    debug_mean_reversion()
