"""
Test PSX Announcement Scraper with PIBTL symbol
"""

from psx_announcement_scraper import PSXAnnouncementScraper
from datetime import datetime

def main():
    print("=" * 70)
    print("PSX ANNOUNCEMENT SCRAPER - PIBTL TEST")
    print("=" * 70)
    print()

    scraper = PSXAnnouncementScraper(delay_seconds=2.0)

    print("Testing with symbol: PIBTL")
    print("Company: Pakistan International Bulk Terminal Limited")
    print("Looking back: 30 days")
    print()

    try:
        # Test 1: Try main scraping (will fall back to company page)
        print("Test 1: Main scrape (with company page fallback)")
        print("-" * 70)

        announcements = scraper.scrape_announcements(
            days_back=30,
            symbols=['PIBTL']
        )

        if announcements:
            print(f"✓ SUCCESS: Found {len(announcements)} announcement(s)")
            print()

            for i, ann in enumerate(announcements, 1):
                print(f"Announcement {i}:")
                print(f"  ID: {ann.announcement_id[:50]}...")
                print(f"  Symbol: {ann.symbol}")
                print(f"  Date: {ann.announcement_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Title: {ann.title}")
                print(f"  Description: {ann.description[:200]}...")
                print(f"  Source: {ann.source}")
                print(f"  Source URL: {ann.source_url}")
                if ann.attachment_url:
                    print(f"  Attachment: {ann.attachment_url}")
                print(f"  Fetched: {ann.fetched_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print()

        else:
            print("⚠ No announcements found for PIBTL in the last 30 days")
            print()

        # Test 2: Direct company page scraping
        print()
        print("Test 2: Direct company page scraping")
        print("-" * 70)

        company_announcements = scraper._scrape_company_pages(
            days_back=60,  # Look back further
            symbols=['PIBTL']
        )

        if company_announcements:
            print(f"✓ Found {len(company_announcements)} announcement(s) on company page")
            print()

            for i, ann in enumerate(company_announcements, 1):
                print(f"Company Page Announcement {i}:")
                print(f"  Symbol: {ann.symbol}")
                print(f"  Date: {ann.announcement_date.strftime('%Y-%m-%d')}")
                print(f"  Title: {ann.title}")
                print(f"  Source: {ann.source}")
                print()

        else:
            print("⚠ No announcements found on PIBTL company page")
            print("Possible reasons:")
            print("  - Company page structure may differ from expected")
            print("  - No announcements in the last 60 days")
            print("  - Page uses JavaScript to load content (would need Selenium)")
            print()

        # Test 3: Fetch company page HTML to analyze structure
        print()
        print("Test 3: Company page analysis")
        print("-" * 70)

        company_url = f"{scraper.PSX_BASE_URL}/company/PIBTL"
        print(f"Fetching: {company_url}")
        print()

        response = scraper._fetch_url(company_url)

        if response and response.status_code == 200:
            print(f"✓ Page loaded successfully (Status: {response.status_code})")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"  Content Length: {len(response.text)} bytes")
            print()

            # Analyze content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for key indicators
            print("Page structure analysis:")

            # Find tables
            tables = soup.find_all('table')
            print(f"  - Tables found: {len(tables)}")

            # Find divs with potential announcement classes
            announcement_divs = soup.find_all('div', class_=lambda x: x and ('announcement' in x.lower() or 'notice' in x.lower()))
            print(f"  - Announcement divs: {len(announcement_divs)}")

            # Find all links (might have announcements)
            links = soup.find_all('a')
            pdf_links = [a for a in links if a.get('href', '').endswith('.pdf')]
            print(f"  - Total links: {len(links)}")
            print(f"  - PDF links: {len(pdf_links)}")

            # Look for date patterns
            import re
            date_pattern = re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}')
            dates_found = date_pattern.findall(response.text)
            print(f"  - Date patterns found: {len(dates_found)}")
            if dates_found:
                print(f"    Sample dates: {dates_found[:5]}")

            print()

            # Show first 1000 chars of body text
            body = soup.find('body')
            if body:
                text_content = body.get_text(separator=' ', strip=True)
                print("First 500 characters of page text:")
                print("-" * 70)
                print(text_content[:500])
                print("...")
                print()

        elif response:
            print(f"⚠ Page returned status: {response.status_code}")
            print()
        else:
            print("✗ Failed to fetch company page")
            print()

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
