#!/usr/bin/env python3
"""
PSX Technical Analysis - Command-line wrapper
Usage: python3 run_technical_analysis.py [SYMBOL1 SYMBOL2 ...]
"""

import sys
import os

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent


def main():
    # Parse symbols from command line
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ['HBL', 'LUCK', 'PSO']

    print("=" * 80)
    print("PSX TECHNICAL ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing: {', '.join(symbols)}\n")

    # Initialize components
    price_store = PSXPriceStore()
    tech_agent = PSXTechnicalAgent(price_store)

    # Update price data
    print("Fetching latest price data...\n")
    price_store.bulk_update(symbols, days=250)

    # Run analysis
    print("\nRunning technical analysis...\n")
    snapshots = tech_agent.analyze_batch(symbols)

    # Display results
    for symbol in symbols:
        if symbol not in snapshots:
            print(f"⚠️  No data available for {symbol}\n")
            continue

        snap = snapshots[symbol]

        print("\n" + "=" * 80)
        print(f"📊 {symbol}")
        print("=" * 80 + "\n")

        # Key indicators
        print("📈 Key Indicators:")
        for indicator, value in sorted(snap.indicator_values.items()):
            print(f"   {indicator:20s}: {value:>12.2f}")

        # Signals
        if snap.signals:
            print(f"\n🔔 Signals ({len(snap.signals)}):")
            for signal in snap.signals:
                emoji = "🔴" if signal.strength.value == "Strong" else "🟡" if signal.strength.value == "Moderate" else "⚪"
                print(f"   {emoji} [{signal.strength.value}] {signal.indicator}: {signal.description}")
        else:
            print("\n🔔 Signals: None (neutral territory)")

        # Overall assessment
        bias_emoji = {
            'Bullish': '📈',
            'Bearish': '📉',
            'Neutral': '➡️'
        }.get(snap.overall_bias.value, '❓')

        print(f"\n💡 Overall Bias: {bias_emoji} {snap.overall_bias.value}")
        print(f"   Confidence: {snap.confidence*100:.0f}%")

    print("\n" + "=" * 80)
    print("✅ Analysis complete")
    print("=" * 80 + "\n")

    # Summary
    print("📊 SUMMARY:")
    print("-" * 80)

    overbought = []
    oversold = []
    bullish_bias = []
    bearish_bias = []

    for symbol, snap in snapshots.items():
        rsi = snap.indicator_values.get('RSI', 50)

        if rsi >= 70:
            overbought.append((symbol, rsi))
        elif rsi <= 30:
            oversold.append((symbol, rsi))

        if snap.overall_bias.value == 'Bullish':
            bullish_bias.append(symbol)
        elif snap.overall_bias.value == 'Bearish':
            bearish_bias.append(symbol)

    if oversold:
        print("\n🟢 OVERSOLD (RSI ≤ 30 - Potential Buy):")
        for symbol, rsi in oversold:
            print(f"   {symbol}: RSI = {rsi:.1f}")

    if overbought:
        print("\n🔴 OVERBOUGHT (RSI ≥ 70 - Potential Sell):")
        for symbol, rsi in overbought:
            print(f"   {symbol}: RSI = {rsi:.1f}")

    if not oversold and not overbought:
        print("\n➡️  All stocks in neutral territory (RSI 30-70)")

    print(f"\n📈 Bullish bias: {len(bullish_bias)}/{len(symbols)}")
    print(f"📉 Bearish bias: {len(bearish_bias)}/{len(symbols)}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
