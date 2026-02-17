#!/usr/bin/env python3
"""
Quick Test: Analyze LUCK, PPL, OGDC with all new features
Run this after installing dependencies: pip install pandas numpy yfinance
"""

from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_divergence_detector import PSXDivergenceDetector
from psx_pattern_recognizer import PSXPatternRecognizer
from psx_technical_store import TechnicalStore

def main():
    symbols = ['LUCK', 'PPL', 'OGDC']

    print("="*100)
    print("PSX TECHNICAL ANALYSIS - LUCK, PPL, OGDC")
    print("="*100)
    print(f"Analyzing: {', '.join(symbols)}")
    print("="*100)

    # Step 1: Price data sync
    print("\n📊 STEP 1: Syncing price data (250 days)...")
    print("-"*100)
    price_store = PSXPriceStore()
    price_store.bulk_update(symbols, days=250)

    # Step 2: Compute weekly aggregations
    print("\n📊 STEP 2: Computing weekly aggregations...")
    print("-"*100)
    price_store.update_weekly_from_daily(symbols)

    # Step 3: Initialize analysis modules
    print("\n📊 STEP 3: Initializing analysis modules...")
    print("-"*100)

    divergence_detector = PSXDivergenceDetector(
        lookback_days=30,
        window=5,
        min_prominence=0.02
    )
    print("✅ Divergence detector initialized (30-day lookback, 2% prominence)")

    pattern_recognizer = PSXPatternRecognizer(
        hs_lookback_days=60,
        hs_min_pattern_days=20,
        dt_lookback_days=50,
        dt_max_pattern_days=40
    )
    print("✅ Pattern recognizer initialized (H&S: 60d, Double: 50d)")

    tech_agent = PSXTechnicalAgent(
        price_store,
        divergence_detector,
        pattern_recognizer
    )
    print("✅ Technical agent ready with all features enabled")

    # Step 4: Run multi-timeframe analysis
    print("\n📊 STEP 4: Running multi-timeframe analysis...")
    print("-"*100)

    results = {}
    for symbol in symbols:
        print(f"\n{'='*100}")
        print(f"📈 {symbol}")
        print('='*100)

        # Get multi-timeframe snapshot
        mtf_snapshot = tech_agent.analyze_multi_timeframe(symbol)
        results[symbol] = mtf_snapshot

        # Display daily analysis
        print(f"\n🔵 DAILY ANALYSIS:")
        print(f"   Overall Bias: {mtf_snapshot.daily.overall_bias.value}")
        print(f"   Confidence: {mtf_snapshot.daily.confidence*100:.1f}%")
        print(f"   Total Signals: {len(mtf_snapshot.daily.signals)}")

        # Show key indicators
        indicators = mtf_snapshot.daily.indicator_values
        print(f"\n   Key Indicators:")
        if 'Close' in indicators:
            print(f"   • Price: Rs {indicators['Close']:.2f}")
        if 'RSI' in indicators:
            rsi = indicators['RSI']
            rsi_status = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            print(f"   • RSI: {rsi:.1f} ({rsi_status})")
        if 'MACD' in indicators:
            print(f"   • MACD: {indicators['MACD']:.2f}")
        if 'SMA_50' in indicators and 'SMA_200' in indicators:
            trend = "Uptrend" if indicators['SMA_50'] > indicators['SMA_200'] else "Downtrend"
            print(f"   • Trend: {trend} (SMA50 vs SMA200)")

        # Display weekly analysis
        print(f"\n🟣 WEEKLY ANALYSIS:")
        print(f"   Overall Bias: {mtf_snapshot.weekly.overall_bias.value}")
        print(f"   Confidence: {mtf_snapshot.weekly.confidence*100:.1f}%")

        # Display multi-timeframe confirmation
        print(f"\n🌍 MULTI-TIMEFRAME CONFIRMATION:")
        conf_score = mtf_snapshot.confirmation_score * 100
        if conf_score >= 80:
            status = "✅ HIGH CONFIRMATION"
        elif conf_score >= 50:
            status = "🟡 MODERATE"
        else:
            status = "⚠️  CONFLICTING"
        print(f"   {status}: {conf_score:.1f}%")

        if mtf_snapshot.aligned_signals:
            print(f"   ✅ Aligned:")
            for signal in mtf_snapshot.aligned_signals[:3]:
                print(f"      • {signal}")

        if mtf_snapshot.conflicting_signals:
            print(f"   ⚠️  Conflicts:")
            for signal in mtf_snapshot.conflicting_signals[:3]:
                print(f"      • {signal}")

        # Show divergences
        if mtf_snapshot.daily.divergences:
            print(f"\n🔄 DIVERGENCES DETECTED: {len(mtf_snapshot.daily.divergences)}")
            for div in mtf_snapshot.daily.divergences:
                emoji = "🟢" if "Bullish" in div.divergence_type.value else "🔴"
                strength_marker = "⚡" if div.strength == "Strong" else "○"
                print(f"   {emoji} {div.divergence_type.value} ({div.strength}) {strength_marker}")
                print(f"      {div.description}")

                # Show price movement
                if div.price_peaks and len(div.price_peaks) >= 2:
                    p1_date, p1_val = div.price_peaks[0]
                    p2_date, p2_val = div.price_peaks[1]
                    print(f"      Price: {p1_val:.2f} ({p1_date}) → {p2_val:.2f} ({p2_date})")

                # Show indicator movement
                if div.indicator_peaks and len(div.indicator_peaks) >= 2:
                    i1_date, i1_val = div.indicator_peaks[0]
                    i2_date, i2_val = div.indicator_peaks[1]
                    indicator_name = "RSI" if "RSI" in div.divergence_type.value else "MACD"
                    print(f"      {indicator_name}: {i1_val:.2f} ({i1_date}) → {i2_val:.2f} ({i2_date})")
        else:
            print(f"\n🔄 DIVERGENCES DETECTED: None")

        # Show patterns
        if mtf_snapshot.daily.patterns:
            print(f"\n📐 CHART PATTERNS: {len(mtf_snapshot.daily.patterns)}")
            for pattern in mtf_snapshot.daily.patterns:
                if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                    emoji = "📉"
                    potential = "Bearish"
                else:
                    emoji = "📈"
                    potential = "Bullish"

                status_emoji = "✅" if pattern.status.value == "Confirmed" else "🔶"
                print(f"   {status_emoji} {emoji} {pattern.pattern_type.value} ({pattern.status.value}, {potential})")

                if pattern.neckline:
                    print(f"      Neckline: Rs {pattern.neckline:.2f}")

                if pattern.target_price and pattern.neckline:
                    change = ((pattern.target_price / pattern.neckline) - 1) * 100
                    print(f"      Target: Rs {pattern.target_price:.2f} ({change:+.1f}%)")

                print(f"      Period: {pattern.start_date} to {pattern.end_date}")
        else:
            print(f"\n📐 CHART PATTERNS: None detected")

    # Step 5: Summary and recommendations
    print("\n" + "="*100)
    print("📊 SUMMARY & RECOMMENDATIONS")
    print("="*100)

    for symbol in symbols:
        mtf = results[symbol]
        conf_score = mtf.confirmation_score * 100

        print(f"\n{symbol}:")
        print(f"  Multi-timeframe: {conf_score:.0f}% confirmation")
        print(f"  Daily: {mtf.daily.overall_bias.value} ({mtf.daily.confidence*100:.0f}%)")
        print(f"  Weekly: {mtf.weekly.overall_bias.value} ({mtf.weekly.confidence*100:.0f}%)")

        # Recommendation logic
        if conf_score >= 80:
            if mtf.daily.overall_bias.value == "Bullish":
                print(f"  💚 Recommendation: STRONG BUY - High confidence bullish signal")
            elif mtf.daily.overall_bias.value == "Bearish":
                print(f"  💔 Recommendation: STRONG SELL - High confidence bearish signal")
            else:
                print(f"  💛 Recommendation: HOLD - Neutral with high confirmation")
        elif conf_score < 50:
            print(f"  ⚠️  Recommendation: CAUTION - Conflicting timeframe signals")
        else:
            print(f"  💙 Recommendation: MODERATE - Watch for confirmation")

        # Pattern-based recommendations
        if mtf.daily.patterns:
            for pattern in mtf.daily.patterns:
                if pattern.status.value == "Confirmed":
                    if "Inverse" in pattern.pattern_type.value or "Bottom" in pattern.pattern_type.value:
                        print(f"  📈 Pattern: {pattern.pattern_type.value} confirmed - Target Rs {pattern.target_price:.2f}")
                    else:
                        print(f"  📉 Pattern: {pattern.pattern_type.value} confirmed - Target Rs {pattern.target_price:.2f}")

    # Step 6: Save to database (optional)
    print("\n" + "="*100)
    print("💾 OPTIONAL: Save results to database? (uncomment code below)")
    print("="*100)

    # Uncomment to save:
    # tech_store = TechnicalStore()
    # for symbol in symbols:
    #     tech_store.save_multi_timeframe_snapshot(results[symbol])
    # print("✅ Results saved to price_data/technicals.db")

    print("\n" + "="*100)
    print("✅ Analysis complete!")
    print("="*100)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nMake sure dependencies are installed:")
        print("  pip install pandas numpy yfinance")
