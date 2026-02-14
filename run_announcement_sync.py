#!/usr/bin/env python3
"""
PSX Announcement Daily Sync

Fetches, classifies, and stores PSX announcements
Run daily after market close (6 PM PKT)
"""

import argparse
from datetime import datetime
import logging
from collections import defaultdict

from psx_announcement_scraper import PSXAnnouncementScraper
from psx_announcement_classifier import AnnouncementClassifier
from psx_announcement_storage import AnnouncementStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main sync function"""
    parser = argparse.ArgumentParser(description='PSX Announcement Daily Sync')
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days to look back (default: 1)'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols to filter (optional)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='announcement_data/announcements.db',
        help='Path to database file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]

    print("=" * 80)
    print("PSX ANNOUNCEMENT SYNC")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Lookback: {args.days} day(s)")
    if symbols:
        print(f"Symbols: {', '.join(symbols)}")
    else:
        print(f"Symbols: ALL")
    print("=" * 80)
    print()

    # Initialize components
    logger.info("Initializing components...")
    scraper = PSXAnnouncementScraper(delay_seconds=2.0)
    classifier = AnnouncementClassifier()
    storage = AnnouncementStorage(db_path=args.db_path)

    # Step 1: Scrape announcements
    print("📥 STEP 1: Scraping announcements from PSX...")
    try:
        raw_announcements = scraper.scrape_announcements(
            days_back=args.days,
            symbols=symbols
        )
        print(f"   ✅ Fetched: {len(raw_announcements)} announcements")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        logger.error(f"Scraping failed: {e}")
        return 1

    if not raw_announcements:
        print("\n⚠️  No announcements found")
        print("\nNote: This could be because:")
        print("  - PSX website is unavailable")
        print("  - No announcements in the time period")
        print("  - Network connectivity issues")
        print("\nFor demo purposes, you can test with mock data.")
        return 0

    # Step 2: Classify announcements
    print("\n🏷️  STEP 2: Classifying announcements...")
    classified_announcements = []
    tier_counts = defaultdict(int)

    for raw in raw_announcements:
        try:
            announcement = classifier.classify(raw)
            classified_announcements.append(announcement)
            tier_counts[announcement.materiality_tier] += 1
        except Exception as e:
            logger.error(f"Classification failed for {raw.announcement_id}: {e}")

    print(f"   ✅ Classified: {len(classified_announcements)} announcements")

    # Step 3: Save to database
    print("\n💾 STEP 3: Saving to database...")
    new_count, duplicate_count = storage.save_announcements_bulk(classified_announcements)

    print(f"   ✅ New: {new_count}")
    print(f"   ℹ️  Duplicates: {duplicate_count}")

    # Step 4: Display summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # By tier
    tier1 = tier_counts[1]
    tier2 = tier_counts[2]
    tier3 = tier_counts[3]

    print(f"\n📊 By Materiality:")
    print(f"   🔴 CRITICAL (Tier 1):      {tier1:3d} announcements")
    print(f"   🟡 MATERIAL (Tier 2):      {tier2:3d} announcements")
    print(f"   🟢 INFORMATIONAL (Tier 3): {tier3:3d} announcements")

    # Show critical announcements
    if tier1 > 0:
        print("\n🔴 CRITICAL ANNOUNCEMENTS:")
        print("   " + "-" * 76)

        critical = [a for a in classified_announcements if a.materiality_tier == 1]
        for ann in critical:
            print(f"   {ann.symbol:8s} - {ann.category:20s} - {ann.title[:40]}")

            if ann.dividend_amount:
                print(f"            Dividend: {ann.dividend_amount}% ({ann.dividend_type})")

            if ann.profit_change_pct:
                print(f"            Profit: {ann.profit_change_pct:+.1f}%")

    # By category
    category_counts = defaultdict(int)
    for ann in classified_announcements:
        if ann.category:
            category_counts[ann.category] += 1

    if category_counts:
        print(f"\n📋 By Category:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category:20s}: {count:3d}")

    # Unique symbols
    unique_symbols = set(ann.symbol for ann in classified_announcements)
    print(f"\n🏢 Unique Symbols: {len(unique_symbols)}")
    if len(unique_symbols) <= 20:
        print(f"   {', '.join(sorted(unique_symbols))}")

    # Record stats
    storage.record_scraping_stats(
        announcements_fetched=len(raw_announcements),
        announcements_new=new_count,
        announcements_duplicate=duplicate_count,
        symbols_covered=len(unique_symbols),
        tier_counts=dict(tier_counts),
        error_count=0,
        notes=f"Sync for {args.days} day(s)"
    )

    print("\n" + "=" * 80)
    print("✅ SYNC COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
