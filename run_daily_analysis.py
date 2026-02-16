#!/usr/bin/env python3
"""
Run Daily Analysis

Simple script to run daily technical analysis.
Can be executed manually or via cron/Task Scheduler.

Usage:
    # Run analysis
    python run_daily_analysis.py

    # Run with custom config
    python run_daily_analysis.py --config production/my_config.json

    # Test mode (dry run)
    python run_daily_analysis.py --test
"""

import sys
import argparse
from datetime import datetime

from production import DailyAnalyzer, ProductionConfig


def main():
    parser = argparse.ArgumentParser(description="Run daily technical analysis")

    parser.add_argument(
        '--config',
        default='production/production_config.json',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode (dry run, no database writes)'
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Override watchlist with specific symbols'
    )

    args = parser.parse_args()

    # Load config
    try:
        config = ProductionConfig.load_from_file(args.config)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        print(f"   Creating default config...")
        config = ProductionConfig()
        config.save_to_file(args.config)

    # Override symbols if specified
    if args.symbols:
        config.watchlist.custom = args.symbols
        print(f"📋 Using custom watchlist: {', '.join(args.symbols)}")

    # Test mode
    if args.test:
        print("🧪 TEST MODE - Database writes disabled")
        config.storage.use_database = False

    # Create analyzer
    analyzer = DailyAnalyzer(config)

    # Run analysis
    try:
        print(f"\n{'='*80}")
        print(f"Starting daily analysis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        snapshots = analyzer.run_daily_analysis()

        print(f"\n{'='*80}")
        print(f"✅ SUCCESS - Analyzed {len(snapshots)} symbols")
        print(f"{'='*80}\n")

        # Summary
        bullish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bullish')
        bearish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bearish')
        neutral = len(snapshots) - bullish - bearish

        print("Quick Summary:")
        print(f"  Bullish: {bullish}")
        print(f"  Bearish: {bearish}")
        print(f"  Neutral: {neutral}")

        if bullish > 0:
            print(f"\nTop Bullish:")
            bullish_list = [(s, snap) for s, snap in snapshots.items()
                           if snap.overall_bias.value == 'Bullish']
            bullish_list.sort(key=lambda x: x[1].confidence, reverse=True)

            for symbol, snap in bullish_list[:5]:
                print(f"  📈 {symbol}: {snap.confidence:.0%}")

        if bearish > 0:
            print(f"\nTop Bearish:")
            bearish_list = [(s, snap) for s, snap in snapshots.items()
                           if snap.overall_bias.value == 'Bearish']
            bearish_list.sort(key=lambda x: x[1].confidence, reverse=True)

            for symbol, snap in bearish_list[:5]:
                print(f"  📉 {symbol}: {snap.confidence:.0%}")

        print(f"\nResults saved to: {analyzer.storage_paths['base']}")

        return 0

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ FAILED: {str(e)}")
        print(f"{'='*80}\n")

        import traceback
        traceback.print_exc()

        return 1


if __name__ == "__main__":
    sys.exit(main())
