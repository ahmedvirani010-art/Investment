"""
PSX Announcement Scraper V2 - Real Implementation

Scrapes official company announcements directly from PSX company pages
Based on actual PSX website structure (Feb 2026)
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime, timedelta
import time
import logging
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RawAnnouncement:
    """Raw announcement data from PSX"""
    symbol: str
    date: str  # YYYY-MM-DD format
    announcement_date: datetime  # datetime object (for compatibility)
    title: str
    text: str
    description: str  # Same as text (for compatibility)
    url: str
    source_url: str = ""  # Same as url (for compatibility)
    pdf_url: Optional[str] = None
    attachment_url: Optional[str] = None  # Same as pdf_url (for compatibility)
    category: str = "unknown"  # financial_results, board_meeting, other
    announcement_id: str = ""  # Generated from symbol + date + title
    source: str = "PSX"  # Data source
    fetched_date: datetime = field(default_factory=datetime.now)  # When it was fetched


class PSXAnnouncementScraperV2:
    """
    Real PSX announcement scraper based on actual website structure

    Scrapes from: https://dps.psx.com.pk/company/{SYMBOL}
    """

    def __init__(self, delay_seconds: float = 2.0):
        """
        Initialize scraper

        Args:
            delay_seconds: Delay between requests (be respectful)
        """
        self.base_url = "https://dps.psx.com.pk"
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        })

    def scrape_announcements(
        self,
        symbols: List[str],
        days_back: int = 30
    ) -> List[RawAnnouncement]:
        """
        Scrape announcements for multiple symbols

        Args:
            symbols: List of stock symbols (e.g., ['HBL', 'OGDC'])
            days_back: Number of days to look back

        Returns:
            List of raw announcements
        """
        all_announcements = []

        for symbol in symbols:
            try:
                announcements = self.scrape_company_announcements(symbol, days_back)
                all_announcements.extend(announcements)

                # Be respectful - delay between requests
                time.sleep(self.delay_seconds)

            except Exception as e:
                logger.error(f"Failed to scrape {symbol}: {e}")
                continue

        logger.info(f"Total announcements scraped: {len(all_announcements)}")
        return all_announcements

    def scrape_company_announcements(
        self,
        symbol: str,
        days_back: int = 30
    ) -> List[RawAnnouncement]:
        """
        Scrape announcements for a specific company

        Args:
            symbol: Company symbol (e.g., 'HBL', 'OGDC')
            days_back: Number of days to look back

        Returns:
            List of raw announcements
        """
        logger.info(f"Scraping {symbol} announcements (last {days_back} days)")

        try:
            # Fetch company page
            url = f"{self.base_url}/company/{symbol}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find announcements section
            announcements_section = soup.find('div', {'id': 'announcements'})
            if not announcements_section:
                logger.warning(f"No announcements section found for {symbol}")
                return []

            # Extract announcements from all tabs
            announcements = []
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Process each tab (Financial Results, Board Meetings, Others)
            tabs = announcements_section.find_all('div', class_='tabs__panel')

            for tab in tabs:
                # Determine category from tab data-name attribute
                tab_name = tab.get('data-name', 'unknown').lower()
                category = self._categorize_tab(tab_name)

                # Find table body
                tbody = tab.find('tbody', class_='tbl__body')
                if not tbody:
                    continue

                # Process each row
                for row in tbody.find_all('tr'):
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue

                        # Extract date
                        date_str = cells[0].get_text(strip=True)
                        announcement_date = self._parse_date(date_str)

                        # Skip if too old
                        if announcement_date < cutoff_date:
                            continue

                        # Extract title
                        title = cells[1].get_text(strip=True)

                        # Extract PDF link
                        pdf_link = None
                        pdf_tag = cells[2].find('a', href=lambda x: x and 'download/document' in x)
                        if pdf_tag:
                            pdf_path = pdf_tag.get('href')
                            pdf_link = f"{self.base_url}{pdf_path}"

                        # Generate announcement ID
                        date_str = announcement_date.strftime('%Y%m%d')
                        title_hash = title[:20].replace(' ', '_')  # Simple hash
                        announcement_id = f"{symbol}_{date_str}_{title_hash}"

                        # Create announcement
                        announcement = RawAnnouncement(
                            symbol=symbol,
                            date=announcement_date.strftime('%Y-%m-%d'),
                            announcement_date=announcement_date,  # datetime object
                            title=title,
                            text=title,  # Full text same as title for now
                            description=title,  # For compatibility
                            url=url,
                            source_url=url,  # For compatibility
                            pdf_url=pdf_link,
                            attachment_url=pdf_link,  # For compatibility
                            category=category,
                            announcement_id=announcement_id
                        )

                        announcements.append(announcement)
                        logger.debug(f"Found: {symbol} - {title} ({announcement_date.strftime('%Y-%m-%d')})")

                    except Exception as e:
                        logger.warning(f"Error parsing row for {symbol}: {e}")
                        continue

            logger.info(f"Found {len(announcements)} announcements for {symbol}")
            return announcements

        except requests.RequestException as e:
            logger.error(f"HTTP error scraping {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping {symbol}: {e}")
            return []

    def _categorize_tab(self, tab_name: str) -> str:
        """Categorize announcement by tab name"""
        tab_name_lower = tab_name.lower()

        if 'financial' in tab_name_lower or 'result' in tab_name_lower:
            return 'financial_results'
        elif 'board' in tab_name_lower or 'meeting' in tab_name_lower:
            return 'board_meeting'
        else:
            return 'other'

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse PSX date format

        PSX uses formats like:
        - "Oct 29, 2025"
        - "Feb 10, 2026"
        """
        try:
            # PSX format: "Oct 29, 2025"
            return datetime.strptime(date_str, '%b %d, %Y')
        except ValueError:
            pass

        # Try other common formats
        formats = [
            '%d %b %Y',        # "29 Oct 2025"
            '%d %b, %Y',       # "29 Oct, 2025"
            '%Y-%m-%d',        # "2025-10-29"
            '%d-%m-%Y',        # "29-10-2025"
            '%d/%m/%Y',        # "29/10/2025"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback
        logger.warning(f"Could not parse date: {date_str}, using current date")
        return datetime.now()


def main():
    """Test the scraper"""
    print("=" * 80)
    print("PSX ANNOUNCEMENT SCRAPER V2 - REAL DATA TEST")
    print("=" * 80)
    print()

    scraper = PSXAnnouncementScraperV2(delay_seconds=2.0)

    # Test with real PSX symbols
    test_symbols = ['HBL', 'OGDC', 'LUCK', 'PPL', 'MCB', 'ENGRO']

    print(f"Scraping announcements for: {', '.join(test_symbols)}")
    print(f"Looking back: 30 days")
    print()

    try:
        announcements = scraper.scrape_announcements(
            symbols=test_symbols,
            days_back=30
        )

        print(f"\n✅ Found {len(announcements)} announcements\n")
        print("=" * 80)

        # Group by symbol
        by_symbol = {}
        for ann in announcements:
            if ann.symbol not in by_symbol:
                by_symbol[ann.symbol] = []
            by_symbol[ann.symbol].append(ann)

        # Display results
        for symbol in sorted(by_symbol.keys()):
            anns = by_symbol[symbol]
            print(f"\n{symbol}: {len(anns)} announcements")
            print("-" * 80)

            for ann in anns[:5]:  # Show first 5
                print(f"  📅 {ann.date} | {ann.category}")
                print(f"     {ann.title[:80]}...")
                if ann.pdf_url:
                    print(f"     📎 {ann.pdf_url}")
                print()

        print("=" * 80)
        print(f"\nTotal announcements: {len(announcements)}")
        print(f"Companies scraped: {len(by_symbol)}")
        print("\n✅ Scraping successful!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
