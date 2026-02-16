#!/usr/bin/env python3
"""
PSX Integrated Analysis
Runs news fetching, anomaly detection, and correlation analysis
"""

from datetime import datetime
from psx_news_agent import PSXNewsAgent
from psx_anomaly_agent import PSXAnomalyAgent
from psx_news_anomaly_correlator import NewsAnomalyCorrelator
from psx_liquidity_screener import PSXLiquidityScreener
from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_technical_store import TechnicalStore

# Optional divergence detection
try:
    from psx_divergence_detector import PSXDivergenceDetector
    DIVERGENCE_AVAILABLE = True
except ImportError:
    DIVERGENCE_AVAILABLE = False
    PSXDivergenceDetector = None

# Optional pattern recognition
try:
    from psx_pattern_recognizer import PSXPatternRecognizer
    PATTERN_AVAILABLE = True
except ImportError:
    PATTERN_AVAILABLE = False
    PSXPatternRecognizer = None

import argparse


def run_full_analysis(
    use_liquid_stocks: bool = True,
    top_n: int = 30,
    fetch_news: bool = True,
    news_hours: int = 48,
    z_threshold: float = 2.5,
    lookback_days: int = 60,
    skip_technicals: bool = False,
    ta_lookback: int = 250,
    save_technicals: bool = False,
    multi_timeframe: bool = False,
    skip_divergences: bool = False,
    skip_patterns: bool = False
):
    """
    Run complete integrated analysis

    Args:
        use_liquid_stocks: Use liquidity screener for stock selection
        top_n: Number of top liquid stocks to analyze
        fetch_news: Whether to fetch fresh news
        news_hours: Hours to look back for news
        z_threshold: Z-score threshold for anomaly detection
        lookback_days: Days to look back for baseline calculation
        skip_technicals: Skip technical analysis computation
        ta_lookback: Days of price history for indicators (default: 250)
        save_technicals: Persist computed indicators to database
        multi_timeframe: Enable multi-timeframe analysis (daily + weekly)
        skip_divergences: Skip divergence detection (enabled by default)
        skip_patterns: Skip pattern recognition (enabled by default)
    """

    print("="*100)
    print("PSX INTEGRATED ANALYSIS")
    print("="*100)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Analysis Period: {lookback_days} days")
    print(f"News Window: {news_hours} hours")
    print(f"Anomaly Threshold: {z_threshold}σ")
    print("="*100)

    # Step 1: Get stock symbols to analyze
    print("\n📋 STEP 1: Stock Selection")
    print("-"*100)

    if use_liquid_stocks:
        print(f"🔍 Using liquidity screener to select top {top_n} stocks...")
        screener = PSXLiquidityScreener(lookback_days=30, min_price=20.0)

        # Quick screen without full report
        liquid_stocks = screener.screen_stocks(top_n=top_n)
        symbols = [stock.symbol for stock in liquid_stocks]

        print(f"✅ Selected {len(symbols)} liquid stocks")
        print(f"   Top 10: {symbols[:10]}")
    else:
        # Use predefined list
        symbols = [
            'HBL', 'UBL', 'MCB', 'BAFL', 'ABL', 'BAHL', 'MEBL', 'NBP',
            'OGDC', 'PPL', 'PSO', 'APL', 'POL', 'MARI',
            'LUCK', 'DGKC', 'MLCF', 'FCCL',
            'FFC', 'EFERT', 'FATIMA',
            'HUBC', 'KAPCO',
            'ENGRO', 'ICI', 'EPCL',
            'INDU', 'PSMC', 'HCAR'
        ]
        print(f"✅ Using predefined list of {len(symbols)} stocks")

    # Step 2: Price Data Sync
    print(f"\n💾 STEP 2: Price Data Sync")
    print("-"*100)
    print(f"🔍 Updating price store with {ta_lookback} days of history...")

    price_store = PSXPriceStore()
    price_store.bulk_update(symbols, days=ta_lookback)

    stats = price_store.get_stats()
    print(f"✅ Price store updated")
    print(f"   Total records: {stats['total_records']:,}")
    print(f"   Symbols: {stats['num_symbols']}")
    print(f"   Date range: {stats['earliest_date']} to {stats['latest_date']}")

    # Compute weekly aggregations if multi-timeframe is enabled
    if multi_timeframe:
        print(f"\n📊 Computing weekly aggregations for multi-timeframe analysis...")
        price_store.update_weekly_from_daily(symbols)

    # Step 3: News Collection
    if fetch_news:
        print(f"\n📰 STEP 3: News Collection")
        print("-"*100)
        print(f"🔍 Fetching news from last {news_hours} hours...")

        news_agent = PSXNewsAgent()
        articles = news_agent.fetch_recent_news(hours=news_hours)
        summary = news_agent.process_articles(articles)

        print(f"✅ Fetched {summary.total_fetched} articles")
        print(f"   New: {summary.new_articles}, Duplicates: {summary.duplicates}")
        print(f"   Stock-specific: {summary.stock_news}")
        print(f"   Macro news: {summary.macro_news}")
    else:
        print(f"\n📰 STEP 3: News Collection")
        print("-"*100)
        print("⏭️  Skipping news fetch, using existing database")

    # Step 4: Technical Analysis
    technical_snapshots = {}
    multi_tf_snapshots = {}
    if not skip_technicals:
        print(f"\n📊 STEP 4: Technical Analysis")
        print("-"*100)

        # Initialize divergence detector if available and not skipped
        divergence_detector = None
        if not skip_divergences and DIVERGENCE_AVAILABLE:
            divergence_detector = PSXDivergenceDetector(lookback_days=30, window=5, min_prominence=0.02)
            print(f"🔍 Divergence detection enabled")

        # Initialize pattern recognizer if available and not skipped
        pattern_recognizer = None
        if not skip_patterns and PATTERN_AVAILABLE:
            pattern_recognizer = PSXPatternRecognizer(
                hs_lookback_days=60, hs_min_pattern_days=20,
                dt_lookback_days=50, dt_max_pattern_days=40
            )
            print(f"🔍 Pattern recognition enabled")

        if multi_timeframe:
            print(f"🔍 Computing multi-timeframe analysis (daily + weekly) for {len(symbols)} stocks...")
            tech_agent = PSXTechnicalAgent(price_store, divergence_detector, pattern_recognizer)

            # Analyze each symbol with multi-timeframe
            for symbol in symbols:
                try:
                    mtf_snapshot = tech_agent.analyze_multi_timeframe(symbol)
                    multi_tf_snapshots[symbol] = mtf_snapshot
                    technical_snapshots[symbol] = mtf_snapshot.daily
                except Exception as e:
                    print(f"  Warning: Error analyzing {symbol}: {str(e)}")

            # Count signals
            total_signals = sum(len(snap.signals) for snap in technical_snapshots.values())
            bullish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bullish")
            bearish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bearish")
            high_conf = sum(1 for mtf in multi_tf_snapshots.values() if mtf.confirmation_score >= 0.8)

            print(f"✅ Multi-timeframe analysis complete")
            print(f"   Total signals: {total_signals}")
            print(f"   Bullish: {bullish}, Bearish: {bearish}, Neutral: {len(symbols) - bullish - bearish}")
            print(f"   High confirmation (≥80%): {high_conf}/{len(symbols)}")
        else:
            print(f"🔍 Computing technical indicators for {len(symbols)} stocks...")
            tech_agent = PSXTechnicalAgent(price_store, divergence_detector, pattern_recognizer)
            technical_snapshots = tech_agent.analyze_batch(symbols)

            # Count signals
            total_signals = sum(len(snap.signals) for snap in technical_snapshots.values())
            bullish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bullish")
            bearish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bearish")

            print(f"✅ Technical analysis complete")
            print(f"   Total signals: {total_signals}")
            print(f"   Bullish: {bullish}, Bearish: {bearish}, Neutral: {len(symbols) - bullish - bearish}")

        # Save to database if requested
        if save_technicals:
            print(f"\n💾 Saving technical indicators to database...")
            tech_store = TechnicalStore()
            if multi_timeframe:
                for mtf_snapshot in multi_tf_snapshots.values():
                    tech_store.save_multi_timeframe_snapshot(mtf_snapshot)
                print(f"✅ Saved {len(multi_tf_snapshots)} multi-timeframe snapshots")
            else:
                for snapshot in technical_snapshots.values():
                    tech_store.save_snapshot(snapshot)
                print(f"✅ Saved {len(technical_snapshots)} snapshots")
    else:
        print(f"\n📊 STEP 4: Technical Analysis")
        print("-"*100)
        print("⏭️  Skipping technical analysis")

    # Step 5: Anomaly Detection
    print(f"\n🔍 STEP 5: Anomaly Detection")
    print("-"*100)
    print(f"🔍 Analyzing {len(symbols)} stocks for anomalies...")
    print(f"   Baseline period: {lookback_days} days")
    print(f"   Threshold: {z_threshold}σ")

    # Use price store in anomaly agent
    anomaly_agent = PSXAnomalyAgent(lookback_days=lookback_days, z_threshold=z_threshold, price_store=price_store)
    anomalies_report = anomaly_agent.generate_report(symbols)

    total_anomalies = sum(len(anomalies) for anomalies in anomalies_report.values())
    print(f"✅ Detected {total_anomalies} anomalies in {len(anomalies_report)} stocks")

    # Step 6: News-Anomaly Correlation
    print(f"\n🔗 STEP 6: News-Anomaly Correlation")
    print("-"*100)

    if anomalies_report:
        print(f"🔍 Correlating {total_anomalies} anomalies with news...")
        correlator = NewsAnomalyCorrelator()
        correlations = correlator.correlate_all(anomalies_report, lookback_days=3)

        explained = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if corr.correlation_score >= 0.5
        )

        print(f"✅ Correlation complete")
        print(f"   Anomalies with news explanation (≥50%): {explained}/{total_anomalies} ({explained/total_anomalies*100:.1f}%)")

        # Print full correlation report
        correlator.print_correlation_report(correlations)

        # Print technical summary if available
        if technical_snapshots:
            print_technical_summary(technical_snapshots, anomalies_report, multi_tf_snapshots)

    else:
        print("ℹ️  No anomalies detected - nothing to correlate")
        print("\n" + "="*100)
        print("✅ No market anomalies detected in analyzed stocks")
        print("="*100)

        # Still print technical summary if available
        if technical_snapshots:
            print_technical_summary(technical_snapshots, {}, multi_tf_snapshots)

    # Summary
    print("\n" + "="*100)
    print("📊 ANALYSIS SUMMARY")
    print("="*100)
    print(f"Stocks Analyzed: {len(symbols)}")
    print(f"Price Records: {stats['total_records']:,}")
    if fetch_news:
        print(f"News Articles Fetched: {summary.total_fetched}")
    if not skip_technicals:
        print(f"Technical Signals: {sum(len(snap.signals) for snap in technical_snapshots.values())}")
    print(f"Anomalies Detected: {total_anomalies}")
    if anomalies_report:
        print(f"News Explanations Found: {explained} ({explained/total_anomalies*100:.1f}%)")
    print("="*100)
    print(f"\n✅ Analysis complete at {datetime.now().strftime('%H:%M:%S')}")


def print_technical_summary(technical_snapshots, anomalies_report, multi_tf_snapshots=None):
    """Print technical analysis summary"""
    print("\n" + "="*100)
    print("📊 TECHNICAL ANALYSIS SUMMARY")
    print("="*100)

    # Multi-timeframe confirmation (if available)
    if multi_tf_snapshots:
        print(f"\n🌍 MULTI-TIMEFRAME CONFIRMATION")
        print("="*100)

        # High confirmation stocks (≥80%)
        high_conf = [(symbol, mtf) for symbol, mtf in multi_tf_snapshots.items()
                     if mtf.confirmation_score >= 0.8]

        if high_conf:
            print(f"\n✅ HIGH CONFIRMATION (≥80%):")
            for symbol, mtf in sorted(high_conf, key=lambda x: x[1].confirmation_score, reverse=True):
                daily_bias = mtf.daily.overall_bias.value
                weekly_bias = mtf.weekly.overall_bias.value
                daily_conf = mtf.daily.confidence * 100
                weekly_conf = mtf.weekly.confidence * 100
                confirmation = mtf.confirmation_score * 100
                print(f"   {symbol:8s} Daily: {daily_bias:8s} ({daily_conf:3.0f}%) | "
                      f"Weekly: {weekly_bias:8s} ({weekly_conf:3.0f}%) | Conf: {confirmation:3.0f}%")
        else:
            print(f"\n✅ HIGH CONFIRMATION (≥80%): None")

        # Conflicting signals (<50%)
        conflicting = [(symbol, mtf) for symbol, mtf in multi_tf_snapshots.items()
                       if mtf.confirmation_score < 0.5]

        if conflicting:
            print(f"\n⚠️  CONFLICTING SIGNALS (<50%):")
            for symbol, mtf in sorted(conflicting, key=lambda x: x[1].confirmation_score):
                daily_bias = mtf.daily.overall_bias.value
                weekly_bias = mtf.weekly.overall_bias.value
                daily_conf = mtf.daily.confidence * 100
                weekly_conf = mtf.weekly.confidence * 100
                confirmation = mtf.confirmation_score * 100
                print(f"   {symbol:8s} Daily: {daily_bias:8s} ({daily_conf:3.0f}%) | "
                      f"Weekly: {weekly_bias:8s} ({weekly_conf:3.0f}%) | Conf: {confirmation:3.0f}%")
                if mtf.conflicting_signals:
                    for conflict in mtf.conflicting_signals:
                        print(f"              ⚠️  {conflict}")
        else:
            print(f"\n⚠️  CONFLICTING SIGNALS (<50%): None")

        print("\n" + "="*100)

    # Divergences detected
    divergence_stocks = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                         if hasattr(snap, 'divergences') and snap.divergences]

    if divergence_stocks:
        print(f"\n🔄 DIVERGENCES DETECTED")
        print("="*100)

        for symbol, snap in divergence_stocks:
            for div in snap.divergences:
                # Emoji for divergence type
                if "Bullish" in div.divergence_type.value:
                    emoji = "🟢"  # Bullish (reversal up)
                else:
                    emoji = "🔴"  # Bearish (reversal down)

                strength_marker = "⚡" if div.strength == "Strong" else "○"

                print(f"\n   {emoji} {symbol:8s} {div.divergence_type.value} ({div.strength}) {strength_marker}")
                print(f"              {div.description}")

                # Show price peaks
                if div.price_peaks and len(div.price_peaks) >= 2:
                    p1_date, p1_val = div.price_peaks[0]
                    p2_date, p2_val = div.price_peaks[1]
                    print(f"              Price: {p1_val:.2f} ({p1_date}) → {p2_val:.2f} ({p2_date})")

                # Show indicator peaks
                if div.indicator_peaks and len(div.indicator_peaks) >= 2:
                    i1_date, i1_val = div.indicator_peaks[0]
                    i2_date, i2_val = div.indicator_peaks[1]
                    indicator_name = "RSI" if "RSI" in div.divergence_type.value else "MACD"
                    print(f"              {indicator_name}: {i1_val:.2f} ({i1_date}) → {i2_val:.2f} ({i2_date})")

        print("\n" + "="*100)
    else:
        print(f"\n🔄 DIVERGENCES DETECTED: None")
        print("="*100)

    # Chart patterns detected
    pattern_stocks = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                      if hasattr(snap, 'patterns') and snap.patterns]

    if pattern_stocks:
        print(f"\n📐 CHART PATTERNS")
        print("="*100)

        # Group patterns by status
        forming_patterns = []
        confirmed_patterns = []

        for symbol, snap in pattern_stocks:
            for pattern in snap.patterns:
                if pattern.status.value == "Confirmed":
                    confirmed_patterns.append((symbol, pattern))
                elif pattern.status.value == "Forming":
                    forming_patterns.append((symbol, pattern))

        # Display confirmed patterns (breakouts)
        if confirmed_patterns:
            print(f"\n✅ CONFIRMED PATTERNS (Breakouts):")
            for symbol, pattern in confirmed_patterns:
                # Emoji based on pattern type
                if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                    emoji = "📉"  # Bearish
                    change = ((pattern.target_price / pattern.neckline) - 1) * 100
                else:
                    emoji = "📈"  # Bullish
                    change = ((pattern.target_price / pattern.neckline) - 1) * 100

                print(f"\n   {emoji} {symbol:8s} {pattern.pattern_type.value}")
                print(f"              Neckline: Rs {pattern.neckline:.2f}")
                print(f"              Target: Rs {pattern.target_price:.2f} ({change:+.1f}%)")
                print(f"              Period: {pattern.start_date} to {pattern.end_date}")

        # Display forming patterns (watch list)
        if forming_patterns:
            print(f"\n🔶 FORMING PATTERNS (Watch for breakout):")
            for symbol, pattern in forming_patterns:
                if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                    emoji = "📉"
                    potential = "Bearish"
                else:
                    emoji = "📈"
                    potential = "Bullish"

                print(f"\n   {emoji} {symbol:8s} {pattern.pattern_type.value} ({potential})")
                print(f"              Neckline: Rs {pattern.neckline:.2f} (watch for break)")
                print(f"              Target if confirmed: Rs {pattern.target_price:.2f}")

        print("\n" + "="*100)
    else:
        print(f"\n📐 CHART PATTERNS: None detected")
        print("="*100)

    # Overbought stocks (RSI > 70)
    overbought = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                  if 'RSI' in snap.indicator_values and snap.indicator_values['RSI'] >= 70]

    if overbought:
        print(f"\n🔴 OVERBOUGHT (RSI > 70):")
        for symbol, snap in sorted(overbought, key=lambda x: x[1].indicator_values['RSI'], reverse=True):
            rsi = snap.indicator_values['RSI']
            bias = snap.overall_bias.value
            conf = snap.confidence * 100
            sma200_status = ""
            if 'SMA_200' in snap.indicator_values:
                price = snap.indicator_values.get('Close', 0)
                sma200 = snap.indicator_values['SMA_200']
                if price > sma200:
                    sma200_status = "above SMA(200)"
                else:
                    sma200_status = "below SMA(200)"

            print(f"   {symbol:8s} RSI: {rsi:5.1f}  |  Bias: {bias:8s} ({conf:.0f}%)  |  {sma200_status}")
    else:
        print(f"\n🔴 OVERBOUGHT (RSI > 70): None")

    # Oversold stocks (RSI < 30)
    oversold = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                if 'RSI' in snap.indicator_values and snap.indicator_values['RSI'] <= 30]

    if oversold:
        print(f"\n🟢 OVERSOLD (RSI < 30):")
        for symbol, snap in sorted(oversold, key=lambda x: x[1].indicator_values['RSI']):
            rsi = snap.indicator_values['RSI']
            bias = snap.overall_bias.value
            conf = snap.confidence * 100
            sma200_status = ""
            if 'SMA_200' in snap.indicator_values:
                price = snap.indicator_values.get('Close', 0)
                sma200 = snap.indicator_values['SMA_200']
                if price > sma200:
                    sma200_status = "above SMA(200)"
                else:
                    sma200_status = "below SMA(200)"

            print(f"   {symbol:8s} RSI: {rsi:5.1f}  |  Bias: {bias:8s} ({conf:.0f}%)  |  {sma200_status}")
    else:
        print(f"\n🟢 OVERSOLD (RSI < 30): None")

    # Bullish crossovers
    bullish_crossovers = []
    for symbol, snap in technical_snapshots.items():
        for signal in snap.signals:
            if signal.signal_type.value == "Bullish" and "cross" in signal.description.lower():
                bullish_crossovers.append((symbol, signal))

    if bullish_crossovers:
        print(f"\n📈 BULLISH CROSSOVERS (today):")
        for symbol, signal in bullish_crossovers:
            print(f"   {symbol:8s} {signal.indicator}: {signal.description}")
    else:
        print(f"\n📈 BULLISH CROSSOVERS (today): None")

    # Bearish crossovers
    bearish_crossovers = []
    for symbol, snap in technical_snapshots.items():
        for signal in snap.signals:
            if signal.signal_type.value == "Bearish" and "cross" in signal.description.lower():
                bearish_crossovers.append((symbol, signal))

    if bearish_crossovers:
        print(f"\n📉 BEARISH CROSSOVERS (today):")
        for symbol, signal in bearish_crossovers:
            print(f"   {symbol:8s} {signal.indicator}: {signal.description}")
    else:
        print(f"\n📉 BEARISH CROSSOVERS (today): None")

    print("\n" + "="*100)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='PSX Integrated Analysis - News, Anomalies, and Correlations'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        default='liquid',
        choices=['liquid', 'preset'],
        help='Stock selection method: liquid (screener) or preset (hardcoded list)'
    )

    parser.add_argument(
        '--top',
        type=int,
        default=30,
        help='Number of top liquid stocks to analyze (default: 30)'
    )

    parser.add_argument(
        '--skip-news',
        action='store_true',
        help='Skip news fetching, use existing database'
    )

    parser.add_argument(
        '--news-hours',
        type=int,
        default=48,
        help='Hours to look back for news (default: 48)'
    )

    parser.add_argument(
        '--z-threshold',
        type=float,
        default=2.5,
        help='Z-score threshold for anomaly detection (default: 2.5)'
    )

    parser.add_argument(
        '--lookback',
        type=int,
        default=60,
        help='Days to look back for baseline (default: 60)'
    )

    parser.add_argument(
        '--skip-technicals',
        action='store_true',
        help='Skip technical analysis computation'
    )

    parser.add_argument(
        '--ta-lookback',
        type=int,
        default=250,
        help='Days of price history for indicators (default: 250)'
    )

    parser.add_argument(
        '--save-technicals',
        action='store_true',
        help='Persist computed indicators to database'
    )

    parser.add_argument(
        '--multi-timeframe',
        action='store_true',
        help='Enable multi-timeframe analysis (daily + weekly)'
    )

    parser.add_argument(
        '--skip-divergences',
        action='store_true',
        help='Skip divergence detection (enabled by default)'
    )

    parser.add_argument(
        '--skip-patterns',
        action='store_true',
        help='Skip pattern recognition (enabled by default)'
    )

    args = parser.parse_args()

    run_full_analysis(
        use_liquid_stocks=(args.stocks == 'liquid'),
        top_n=args.top,
        fetch_news=(not args.skip_news),
        news_hours=args.news_hours,
        z_threshold=args.z_threshold,
        lookback_days=args.lookback,
        skip_technicals=args.skip_technicals,
        ta_lookback=args.ta_lookback,
        save_technicals=args.save_technicals,
        multi_timeframe=args.multi_timeframe,
        skip_divergences=args.skip_divergences,
        skip_patterns=args.skip_patterns
    )


if __name__ == "__main__":
    main()
    if fetch_news:
        print(f"\n📰 STEP 2: News Collection")
        print("-"*100)
        print(f"🔍 Fetching news from last {news_hours} hours...")

        news_agent = PSXNewsAgent()
        articles = news_agent.fetch_recent_news(hours=news_hours)
        summary = news_agent.process_articles(articles)

        print(f"✅ Fetched {summary.total_fetched} articles")
        print(f"   New: {summary.new_articles}, Duplicates: {summary.duplicates}")
        print(f"   Stock-specific: {summary.stock_news}")
        print(f"   Macro news: {summary.macro_news}")
    else:
        print(f"\n📰 STEP 2: News Collection")
        print("-"*100)
        print("⏭️  Skipping news fetch, using existing database")

    # Step 3: Anomaly detection
    print(f"\n🔍 STEP 3: Anomaly Detection")
    print("-"*100)
    print(f"🔍 Analyzing {len(symbols)} stocks for anomalies...")
    print(f"   Baseline period: {lookback_days} days")
    print(f"   Threshold: {z_threshold}σ")

    anomaly_agent = PSXAnomalyAgent(lookback_days=lookback_days, z_threshold=z_threshold)
    anomalies_report = anomaly_agent.generate_report(symbols)

    total_anomalies = sum(len(anomalies) for anomalies in anomalies_report.values())
    print(f"✅ Detected {total_anomalies} anomalies in {len(anomalies_report)} stocks")

    # Step 4: News-Anomaly Correlation
    print(f"\n🔗 STEP 4: News-Anomaly Correlation")
    print("-"*100)

    if anomalies_report:
        print(f"🔍 Correlating {total_anomalies} anomalies with news...")
        correlator = NewsAnomalyCorrelator()
        correlations = correlator.correlate_all(anomalies_report, lookback_days=3)

        explained = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if corr.correlation_score >= 0.5
        )

        print(f"✅ Correlation complete")
        print(f"   Anomalies with news explanation (≥50%): {explained}/{total_anomalies} ({explained/total_anomalies*100:.1f}%)")

        # Print full correlation report
        correlator.print_correlation_report(correlations)

    else:
        print("ℹ️  No anomalies detected - nothing to correlate")
        print("\n" + "="*100)
        print("✅ No market anomalies detected in analyzed stocks")
        print("="*100)

    # Summary
    print("\n" + "="*100)
    print("📊 ANALYSIS SUMMARY")
    print("="*100)
    print(f"Stocks Analyzed: {len(symbols)}")
    if fetch_news:
        print(f"News Articles Fetched: {summary.total_fetched}")
    print(f"Anomalies Detected: {total_anomalies}")
    if anomalies_report:
        print(f"News Explanations Found: {explained} ({explained/total_anomalies*100:.1f}%)")
    print("="*100)
    print(f"\n✅ Analysis complete at {datetime.now().strftime('%H:%M:%S')}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='PSX Integrated Analysis - News, Anomalies, and Correlations'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        default='liquid',
        choices=['liquid', 'preset'],
        help='Stock selection method: liquid (screener) or preset (hardcoded list)'
    )

    parser.add_argument(
        '--top',
        type=int,
        default=30,
        help='Number of top liquid stocks to analyze (default: 30)'
    )

    parser.add_argument(
        '--skip-news',
        action='store_true',
        help='Skip news fetching, use existing database'
    )

    parser.add_argument(
        '--news-hours',
        type=int,
        default=48,
        help='Hours to look back for news (default: 48)'
    )

    parser.add_argument(
        '--z-threshold',
        type=float,
        default=2.5,
        help='Z-score threshold for anomaly detection (default: 2.5)'
    )

    parser.add_argument(
        '--lookback',
        type=int,
        default=60,
        help='Days to look back for baseline (default: 60)'
    )

    args = parser.parse_args()

    run_full_analysis(
        use_liquid_stocks=(args.stocks == 'liquid'),
        top_n=args.top,
        fetch_news=(not args.skip_news),
        news_hours=args.news_hours,
        z_threshold=args.z_threshold,
        lookback_days=args.lookback
    )


if __name__ == "__main__":
    main()
