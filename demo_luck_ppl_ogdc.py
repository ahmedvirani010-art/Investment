#!/usr/bin/env python3
"""
Demo: LUCK, PPL, OGDC Analysis with Sample Data
Demonstrates all features without requiring yfinance
"""

import sys
sys.path.insert(0, '/home/user/Investment')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from psx_divergence_detector import PSXDivergenceDetector
from psx_pattern_recognizer import PSXPatternRecognizer

def create_luck_data():
    """LUCK: Bullish setup with Inverse H&S and divergence"""
    dates = pd.date_range(start='2025-08-01', end='2026-02-16', freq='D')
    base_price = 450
    prices = []

    for i in range(len(dates)):
        if i < 40:  # Left shoulder
            price = base_price + i * 0.5 - (i % 10) * 2
        elif i < 60:  # Down to head (lowest point)
            price = 470 - (i - 40) * 1.2
        elif i < 90:  # Recovery from head
            price = 446 + (i - 60) * 0.6
        elif i < 110:  # Right shoulder formation
            price = 464 - (i - 90) * 0.4
        elif i < 130:  # Recovery from right shoulder
            price = 456 + (i - 110) * 0.45
        else:  # Breakout above neckline
            price = 465 + (i - 130) * 0.3

        price += np.random.normal(0, 3)
        prices.append(max(price, 440))

    df = pd.DataFrame({
        'date': dates,
        'Open': [p * 0.995 for p in prices],
        'High': [p * 1.015 for p in prices],
        'Low': [p * 0.985 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(2000000, 5000000, len(dates))
    })
    df.set_index('date', inplace=True)

    # Compute RSI for divergence
    delta = df['Close'].diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gains = gains.rolling(window=14, min_periods=14).mean()
    avg_losses = losses.rolling(window=14, min_periods=14).mean()
    rs = avg_gains / avg_losses
    df['RSI'] = 100 - (100 / (1 + rs))

    # Compute MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    df.attrs['symbol'] = 'LUCK'
    return df

def create_ppl_data():
    """PPL: Neutral/consolidating with forming Double Bottom"""
    dates = pd.date_range(start='2025-08-01', end='2026-02-16', freq='D')
    base_price = 150
    prices = []

    for i in range(len(dates)):
        if i < 30:
            price = base_price + i * 0.2  # Mild uptrend
        elif i < 50:
            price = 156 - (i - 30) * 0.3  # Down to first bottom
        elif i < 80:
            price = 150 + (i - 50) * 0.16  # Recovery
        elif i < 105:
            price = 154.8 - (i - 80) * 0.22  # Down to second bottom
        else:
            price = 149 + (i - 105) * 0.08  # Consolidating near support

        price += np.random.normal(0, 1.5)
        prices.append(max(price, 145))

    df = pd.DataFrame({
        'date': dates,
        'Open': [p * 0.998 for p in prices],
        'High': [p * 1.012 for p in prices],
        'Low': [p * 0.988 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1000000, 3000000, len(dates))
    })
    df.set_index('date', inplace=True)

    # Compute RSI
    delta = df['Close'].diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gains = gains.rolling(window=14, min_periods=14).mean()
    avg_losses = losses.rolling(window=14, min_periods=14).mean()
    rs = avg_gains / avg_losses
    df['RSI'] = 100 - (100 / (1 + rs))

    # Compute MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    df.attrs['symbol'] = 'PPL'
    return df

def create_ogdc_data():
    """OGDC: Bearish setup with H&S forming and MACD divergence"""
    dates = pd.date_range(start='2025-08-01', end='2026-02-16', freq='D')
    base_price = 175
    prices = []

    for i in range(len(dates)):
        if i < 35:  # Uptrend to left shoulder
            price = base_price + i * 0.35
        elif i < 50:  # Down from left shoulder
            price = 187 - (i - 35) * 0.5
        elif i < 80:  # Up to head (highest point)
            price = 179.5 + (i - 50) * 0.5
        elif i < 100:  # Down from head
            price = 194.5 - (i - 80) * 0.7
        elif i < 125:  # Up to right shoulder
            price = 180.5 + (i - 100) * 0.38
        else:  # Starting to break down
            price = 190 - (i - 125) * 0.2

        price += np.random.normal(0, 2)
        prices.append(max(price, 170))

    df = pd.DataFrame({
        'date': dates,
        'Open': [p * 0.997 for p in prices],
        'High': [p * 1.018 for p in prices],
        'Low': [p * 0.982 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1500000, 4000000, len(dates))
    })
    df.set_index('date', inplace=True)

    # Compute RSI
    delta = df['Close'].diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gains = gains.rolling(window=14, min_periods=14).mean()
    avg_losses = losses.rolling(window=14, min_periods=14).mean()
    rs = avg_gains / avg_losses
    df['RSI'] = 100 - (100 / (1 + rs))

    # Compute MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    df.attrs['symbol'] = 'OGDC'
    return df

def main():
    print("="*100)
    print("PSX TECHNICAL ANALYSIS DEMO: LUCK, PPL, OGDC")
    print("Using Sample Data to Demonstrate Features")
    print("="*100)

    # Initialize detectors
    print("\n📊 Initializing analysis modules...")
    divergence_detector = PSXDivergenceDetector(
        lookback_days=80,
        window=5,
        min_prominence=0.015
    )
    print("✅ Divergence detector ready")

    pattern_recognizer = PSXPatternRecognizer(
        hs_lookback_days=120,
        hs_min_pattern_days=30,
        hs_head_prominence=0.025,
        hs_shoulder_tolerance=0.06,
        dt_lookback_days=100,
        dt_peak_tolerance=0.04,
        dt_min_trough_depth=0.04,
        dt_max_pattern_days=60
    )
    print("✅ Pattern recognizer ready")

    # Create sample data
    print("\n📈 Generating sample price data (200 days)...")
    stocks = {
        'LUCK': create_luck_data(),
        'PPL': create_ppl_data(),
        'OGDC': create_ogdc_data()
    }
    print("✅ Data generated for LUCK, PPL, OGDC")

    # Analyze each stock
    for symbol, df in stocks.items():
        print("\n" + "="*100)
        print(f"📊 {symbol} - TECHNICAL ANALYSIS")
        print("="*100)

        print(f"\n📈 Price Summary:")
        print(f"   Latest: Rs {df['Close'].iloc[-1]:.2f}")
        print(f"   Range: Rs {df['Close'].min():.2f} - Rs {df['Close'].max():.2f}")
        print(f"   Change: {((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100:+.2f}%")

        # Current indicators
        print(f"\n📊 Current Indicators:")
        if 'RSI' in df.columns:
            rsi = df['RSI'].iloc[-1]
            rsi_status = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            print(f"   RSI: {rsi:.1f} ({rsi_status})")
        if 'MACD' in df.columns:
            macd = df['MACD'].iloc[-1]
            print(f"   MACD: {macd:.2f}")

        # Detect divergences
        print(f"\n🔄 DIVERGENCE DETECTION:")
        divergences = divergence_detector.detect_all_divergences(symbol, df)

        if divergences:
            print(f"   ✅ {len(divergences)} divergence(s) detected:")
            for div in divergences:
                emoji = "🟢" if "Bullish" in div.divergence_type.value else "🔴"
                strength_marker = "⚡" if div.strength == "Strong" else "○"
                print(f"\n   {emoji} {div.divergence_type.value} ({div.strength}) {strength_marker}")
                print(f"      {div.description}")

                if div.price_peaks and len(div.price_peaks) >= 2:
                    p1_date, p1_val = div.price_peaks[0]
                    p2_date, p2_val = div.price_peaks[1]
                    print(f"      Price: Rs {p1_val:.2f} ({p1_date}) → Rs {p2_val:.2f} ({p2_date})")

                if div.indicator_peaks and len(div.indicator_peaks) >= 2:
                    i1_date, i1_val = div.indicator_peaks[0]
                    i2_date, i2_val = div.indicator_peaks[1]
                    indicator_name = "RSI" if "RSI" in div.divergence_type.value else "MACD"
                    print(f"      {indicator_name}: {i1_val:.2f} ({i1_date}) → {i2_val:.2f} ({i2_date})")
        else:
            print("   No divergences detected in current window")

        # Detect patterns
        print(f"\n📐 CHART PATTERN DETECTION:")
        patterns = pattern_recognizer.detect_all_patterns(symbol, df)

        if patterns:
            print(f"   ✅ {len(patterns)} pattern(s) detected:")
            for pattern in patterns:
                if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                    emoji = "📉"
                    signal_type = "BEARISH"
                else:
                    emoji = "📈"
                    signal_type = "BULLISH"

                status_emoji = "✅" if pattern.status.value == "Confirmed" else "🔶"
                print(f"\n   {status_emoji} {emoji} {pattern.pattern_type.value}")
                print(f"      Status: {pattern.status.value} ({signal_type})")
                print(f"      Period: {pattern.start_date} to {pattern.end_date}")

                if pattern.neckline:
                    print(f"      Neckline: Rs {pattern.neckline:.2f}")

                if pattern.target_price and pattern.neckline:
                    change = ((pattern.target_price / pattern.neckline) - 1) * 100
                    print(f"      Target: Rs {pattern.target_price:.2f} ({change:+.1f}%)")

                if pattern.key_points:
                    print(f"      Key Points:")
                    for label, (date, price) in list(pattern.key_points.items())[:3]:
                        print(f"         {label}: Rs {price:.2f} ({date})")
        else:
            print("   No patterns detected in current window")

        # Trading recommendation
        print(f"\n💡 SIMULATED RECOMMENDATION:")

        # Simple logic based on patterns and divergences
        bullish_signals = sum(1 for d in divergences if "Bullish" in d.divergence_type.value)
        bearish_signals = sum(1 for d in divergences if "Bearish" in d.divergence_type.value)

        confirmed_bullish_patterns = sum(1 for p in patterns
            if p.status.value == "Confirmed" and p.pattern_type.value in ["Inverse Head and Shoulders", "Double Bottom"])
        confirmed_bearish_patterns = sum(1 for p in patterns
            if p.status.value == "Confirmed" and p.pattern_type.value in ["Head and Shoulders", "Double Top"])

        forming_bullish_patterns = sum(1 for p in patterns
            if p.status.value == "Forming" and p.pattern_type.value in ["Inverse Head and Shoulders", "Double Bottom"])
        forming_bearish_patterns = sum(1 for p in patterns
            if p.status.value == "Forming" and p.pattern_type.value in ["Head and Shoulders", "Double Top"])

        score = 0
        score += bullish_signals * 2 + confirmed_bullish_patterns * 3 + forming_bullish_patterns * 1
        score -= bearish_signals * 2 + confirmed_bearish_patterns * 3 + forming_bearish_patterns * 1

        if score >= 5:
            print("   🟢 STRONG BUY - Multiple bullish signals")
        elif score >= 3:
            print("   💚 BUY - Bullish setup developing")
        elif score >= 1:
            print("   💙 WEAK BUY - Some bullish signals")
        elif score <= -5:
            print("   🔴 STRONG SELL - Multiple bearish signals")
        elif score <= -3:
            print("   💔 SELL - Bearish setup developing")
        elif score <= -1:
            print("   🧡 WEAK SELL - Some bearish signals")
        else:
            print("   💛 NEUTRAL - Mixed or no clear signals")

        if divergences:
            print(f"   • {len(divergences)} divergence signal(s)")
        if patterns:
            print(f"   • {len(patterns)} pattern(s) detected")

    # Final summary
    print("\n" + "="*100)
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
    print("\nFeatures demonstrated:")
    print("✅ Divergence Detection - RSI & MACD vs Price")
    print("✅ Pattern Recognition - H&S, Inverse H&S, Double Top/Bottom")
    print("✅ Status Tracking - Forming vs Confirmed patterns")
    print("✅ Target Calculation - Based on pattern geometry")
    print("\nNote: This demo uses simulated data. For real market analysis:")
    print("  1. Install yfinance: pip install yfinance")
    print("  2. Run: python test_three_stocks.py")
    print("="*100)

if __name__ == "__main__":
    main()
