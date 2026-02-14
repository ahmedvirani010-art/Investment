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
import argparse


def run_full_analysis(
    use_liquid_stocks: bool = True,
    top_n: int = 30,
    fetch_news: bool = True,
    news_hours: int = 48,
    z_threshold: float = 2.5,
    lookback_days: int = 60
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

    # Step 2: Fetch news
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
