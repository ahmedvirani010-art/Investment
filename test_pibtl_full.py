"""
Test PIBTL scraping with longer lookback to find all announcements
"""

from psx_announcement_scraper import PSXAnnouncementScraper

def main():
    print("=" * 70)
    print("PIBTL - FULL ANNOUNCEMENT SCRAPING (120 days)")
    print("=" * 70)
    print()

    scraper = PSXAnnouncementScraper(delay_seconds=2.0)

    # Look back 120 days to catch all announcements
    announcements = scraper.scrape_announcements(
        days_back=120,
        symbols=['PIBTL']
    )

    print(f"\n✓ Found {len(announcements)} total announcements")
    print("=" * 70)
    print()

    if announcements:
        # Group by category (based on title keywords)
        financial = []
        board = []
        others = []

        for ann in announcements:
            title_lower = ann.title.lower()

            if 'financial' in title_lower or 'result' in title_lower or 'report' in title_lower:
                financial.append(ann)
            elif 'board' in title_lower or 'meeting' in title_lower or 'agm' in title_lower:
                board.append(ann)
            else:
                others.append(ann)

        print(f"Financial Results: {len(financial)}")
        print(f"Board Meetings: {len(board)}")
        print(f"Others: {len(others)}")
        print()

        # Show all announcements
        for i, ann in enumerate(announcements, 1):
            print(f"{i}. {ann.announcement_date.strftime('%b %d, %Y')} - {ann.title}")
            if ann.attachment_url:
                print(f"   PDF: {ann.attachment_url}")
            print()

if __name__ == "__main__":
    main()
