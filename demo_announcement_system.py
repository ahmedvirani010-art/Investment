#!/usr/bin/env python3
"""
PSX Announcement System Demo

Demonstrates the integrated announcement + news + anomaly correlation system
Uses sample data to show the full workflow
"""

from datetime import datetime, timedelta
from psx_announcement_scraper import RawAnnouncement
from psx_announcement_classifier import AnnouncementClassifier
from psx_announcement_storage import AnnouncementStorage, Announcement
from psx_anomaly_agent import Anomaly, AnomalyType, Severity
from psx_news_anomaly_correlator import NewsAnomalyCorrelator


def create_sample_announcements():
    """Create sample PSX announcements for demo"""

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    raw_announcements = [
        # HBL - High dividend
        RawAnnouncement(
            announcement_id="HBL_20260214_001",
            symbol="HBL",
            announcement_date=yesterday,
            title="Final Cash Dividend Announcement for Year Ended December 31, 2025",
            description="The Board of Directors has announced a final cash dividend of Rs 50 per share (500%) for the year ended December 31, 2025. Profit increased by 28.5% to Rs 45 billion. EPS: Rs 78.50",
            source_url="https://dps.psx.com.pk/company/HBL/announcements/20260214",
            source="PSX"
        ),

        # OGDC - Quarterly results
        RawAnnouncement(
            announcement_id="OGDC_20260213_001",
            symbol="OGDC",
            announcement_date=two_days_ago,
            title="First Quarter Financial Results for Period Ended December 31, 2025",
            description="Quarterly results show profit increased by 35% YoY to Rs 38 billion. EPS: Rs 9.20. Oil and gas production remained strong.",
            source_url="https://dps.psx.com.pk/company/OGDC/announcements/20260213",
            source="PSX"
        ),

        # LUCK - Major contract
        RawAnnouncement(
            announcement_id="LUCK_20260213_002",
            symbol="LUCK",
            announcement_date=two_days_ago,
            title="Contract Award - Major Infrastructure Project",
            description="Company has been awarded a major contract worth $150 million for cement supply to infrastructure development project. Project duration: 24 months.",
            source_url="https://dps.psx.com.pk/company/LUCK/announcements/20260213",
            source="PSX"
        ),

        # PPL - Oil discovery
        RawAnnouncement(
            announcement_id="PPL_20260212_001",
            symbol="PPL",
            announcement_date=today - timedelta(days=3),
            title="Oil Discovery in Sindh Province",
            description="Successful oil discovery in exploration well. Initial production estimates: 2,000 barrels per day. Further testing underway.",
            source_url="https://dps.psx.com.pk/company/PPL/announcements/20260212",
            source="PSX"
        ),

        # MCB - Bonus shares
        RawAnnouncement(
            announcement_id="MCB_20260211_001",
            symbol="MCB",
            announcement_date=today - timedelta(days=4),
            title="Bonus Share Announcement 1:1",
            description="Board announces bonus shares at ratio of 1:1 (100% bonus). Annual results show profit of Rs 28 billion, up 18% YoY.",
            source_url="https://dps.psx.com.pk/company/MCB/announcements/20260211",
            source="PSX"
        ),

        # PSO - Board meeting notice (low materiality)
        RawAnnouncement(
            announcement_id="PSO_20260214_001",
            symbol="PSO",
            announcement_date=today,
            title="Notice of Board Meeting",
            description="Notice is given that a meeting of the Board of Directors will be held on February 25, 2026 to consider quarterly financial results.",
            source_url="https://dps.psx.com.pk/company/PSO/announcements/20260214",
            source="PSX"
        ),

        # ENGRO - Book closure (informational)
        RawAnnouncement(
            announcement_id="ENGRO_20260213_003",
            symbol="ENGRO",
            announcement_date=yesterday,
            title="Book Closure Notice",
            description="Books will be closed from March 1 to March 7, 2026 for payment of final dividend.",
            source_url="https://dps.psx.com.pk/company/ENGRO/announcements/20260213",
            source="PSX"
        ),
    ]

    return raw_announcements


def create_sample_anomalies():
    """Create sample anomalies that correlate with announcements"""

    today = datetime.now()

    anomalies = {
        'HBL': [
            Anomaly(
                symbol='HBL',
                date=today.strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                severity=Severity.HIGH,
                value=180.5,  # 180% increase
                baseline=5.4,  # million shares
                z_score=4.82,
                description="Volume +180% from average (15.2M vs 5.4M)",
                details={'volume': 15200000, 'avg_volume': 5400000}
            ),
            Anomaly(
                symbol='HBL',
                date=today.strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.PRICE_MOVEMENT,
                severity=Severity.MEDIUM,
                value=4.8,  # 4.8% gain
                baseline=215.50,
                z_score=3.21,
                description="Price +4.8% (Rs 225.80 vs Rs 215.50 avg)",
                details={'close': 225.80, 'avg_close': 215.50}
            )
        ],
        'OGDC': [
            Anomaly(
                symbol='OGDC',
                date=(today - timedelta(days=1)).strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.PRICE_MOVEMENT,
                severity=Severity.MEDIUM,
                value=5.2,  # 5.2% gain
                baseline=188.30,
                z_score=3.45,
                description="Price +5.2% (Rs 198.10 vs Rs 188.30 avg)",
                details={'close': 198.10, 'avg_close': 188.30}
            )
        ],
        'LUCK': [
            Anomaly(
                symbol='LUCK',
                date=(today - timedelta(days=1)).strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                severity=Severity.HIGH,
                value=145.3,  # 145% increase
                baseline=1.2,
                z_score=4.15,
                description="Volume +145% from average (2.94M vs 1.2M)",
                details={'volume': 2940000, 'avg_volume': 1200000}
            )
        ],
        'PPL': [
            Anomaly(
                symbol='PPL',
                date=(today - timedelta(days=2)).strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.OPENING_GAP,
                severity=Severity.HIGH,
                value=6.8,  # 6.8% gap up
                baseline=145.60,
                z_score=4.52,
                description="Opening gap +6.8% (Rs 155.50 vs Rs 145.60 prev close)",
                details={'open': 155.50, 'prev_close': 145.60}
            )
        ],
        'MCB': [
            Anomaly(
                symbol='MCB',
                date=(today - timedelta(days=3)).strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                severity=Severity.HIGH,
                value=210.4,  # 210% increase
                baseline=3.2,
                z_score=5.18,
                description="Volume +210% from average (9.93M vs 3.2M)",
                details={'volume': 9930000, 'avg_volume': 3200000}
            )
        ],
    }

    return anomalies


def main():
    """Run demo"""

    print("=" * 100)
    print("PSX ANNOUNCEMENT SYSTEM - INTEGRATED DEMO")
    print("=" * 100)
    print("\nThis demo shows the complete workflow:")
    print("  1. Scraping PSX announcements (simulated with sample data)")
    print("  2. Classifying announcements by materiality")
    print("  3. Storing in database")
    print("  4. Correlating with anomalies")
    print("  5. Generating explanations (announcements prioritized over news)")
    print()

    # Step 1: Create sample data
    print("\n" + "=" * 100)
    print("STEP 1: Creating Sample Announcements")
    print("=" * 100)

    raw_announcements = create_sample_announcements()
    print(f"✅ Created {len(raw_announcements)} sample announcements")

    for ann in raw_announcements:
        print(f"   - {ann.symbol:8s} | {ann.title[:60]}")

    # Step 2: Classify announcements
    print("\n" + "=" * 100)
    print("STEP 2: Classifying Announcements")
    print("=" * 100)

    classifier = AnnouncementClassifier()
    classified_announcements = []

    for raw in raw_announcements:
        announcement = classifier.classify(raw)
        classified_announcements.append(announcement)

        tier_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}[announcement.materiality_tier]
        tier_label = {1: "CRITICAL", 2: "MATERIAL", 3: "INFO"}[announcement.materiality_tier]

        print(f"\n{announcement.symbol} - {announcement.title[:50]}")
        print(f"   Category: {announcement.category}")
        print(f"   {tier_emoji} Materiality: Tier {announcement.materiality_tier} ({tier_label})")

        if announcement.dividend_amount:
            print(f"   💰 Dividend: {announcement.dividend_amount}% ({announcement.dividend_type})")
        if announcement.profit_change_pct:
            print(f"   📈 Profit: {announcement.profit_change_pct:+.1f}%")

    # Step 3: Store in database
    print("\n" + "=" * 100)
    print("STEP 3: Storing Announcements in Database")
    print("=" * 100)

    storage = AnnouncementStorage("demo_announcements.db")
    new_count, duplicate_count = storage.save_announcements_bulk(classified_announcements)

    print(f"✅ Saved to database:")
    print(f"   New: {new_count}")
    print(f"   Duplicates: {duplicate_count}")

    # Statistics
    stats = storage.get_statistics(days=7)
    print(f"\nDatabase Statistics:")
    print(f"   Total Announcements: {stats['total_announcements']}")
    print(f"   🔴 Tier 1 (Critical): {stats['tier_1_critical']}")
    print(f"   🟡 Tier 2 (Material): {stats['tier_2_material']}")
    print(f"   🟢 Tier 3 (Info): {stats['tier_3_info']}")

    # Step 4: Create sample anomalies
    print("\n" + "=" * 100)
    print("STEP 4: Creating Sample Anomalies")
    print("=" * 100)

    anomalies_by_symbol = create_sample_anomalies()

    total_anomalies = sum(len(anoms) for anoms in anomalies_by_symbol.values())
    print(f"✅ Created {total_anomalies} sample anomalies")

    for symbol, anomalies in anomalies_by_symbol.items():
        print(f"\n{symbol}: {len(anomalies)} anomalies")
        for anom in anomalies:
            severity_emoji = {
                Severity.HIGH: "🔴",
                Severity.MEDIUM: "🟡",
                Severity.LOW: "🟢"
            }[anom.severity]
            print(f"   {severity_emoji} {anom.anomaly_type.value}: {anom.description}")

    # Step 5: Correlate with announcements + news
    print("\n" + "=" * 100)
    print("STEP 5: Correlating Anomalies with Announcements + News")
    print("=" * 100)

    correlator = NewsAnomalyCorrelator(announcement_storage=storage)

    print("\nRunning correlation analysis...")
    print("(Announcements are prioritized over news articles)")

    correlations = correlator.correlate_all(anomalies_by_symbol, lookback_days=5)

    # Step 6: Generate integrated report
    print("\n" + "=" * 100)
    print("STEP 6: Integrated Analysis Report")
    print("=" * 100)

    correlator.print_correlation_report(correlations)

    # Summary
    print("\n" + "=" * 100)
    print("DEMO SUMMARY")
    print("=" * 100)

    announcement_explained = sum(
        1 for corrs in correlations.values()
        for corr in corrs
        if len(corr.related_announcements) > 0 and corr.correlation_score >= 0.5
    )

    total_with_correlation = sum(
        1 for corrs in correlations.values()
        for corr in corrs
        if corr.correlation_score >= 0.5
    )

    print(f"\n📊 Key Insights:")
    print(f"   • Total Anomalies: {total_anomalies}")
    print(f"   • Explained by Official Announcements: {announcement_explained} ({announcement_explained/total_anomalies*100:.1f}%)")
    print(f"   • Explained by Announcements + News: {total_with_correlation} ({total_with_correlation/total_anomalies*100:.1f}%)")
    print()

    print("✅ Benefits of Announcement Integration:")
    print("   1. Authoritative source - official PSX announcements beat media reports")
    print("   2. No delay - announcements before news articles")
    print("   3. Structured data - easier to extract financial metrics")
    print("   4. Higher confidence - official corporate actions vs. speculation")
    print("   5. Better coverage - announcements + news > news alone")
    print()

    print("🎯 Next Steps:")
    print("   • Implement live PSX scraping (currently uses sample data)")
    print("   • Add PDF parsing for detailed financial statements")
    print("   • Set up daily sync schedule (run at market close)")
    print("   • Create real-time monitoring for critical announcements")
    print("   • Integrate with trading alerts and notifications")
    print()

    print("=" * 100)
    print("✅ DEMO COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
