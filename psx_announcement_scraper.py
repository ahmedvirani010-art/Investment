"""
PSX Announcement Scraper

Scrapes official company announcements from Pakistan Stock Exchange (PSX)
Supports multiple data sources: PSX website, SECP filings, company IR pages
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import re
import logging
from dataclasses import dataclass, field
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RawAnnouncement:
    """Raw announcement data from scraper"""
    announcement_id: str
    symbol: str
    announcement_date: datetime
    title: str
    description: str
    attachment_url: Optional[str] = None
    source_url: str = ""
    source: str = "PSX"  # PSX, SECP, CompanyIR
    raw_html: str = ""
    fetched_date: datetime = field(default_factory=datetime.now)


class PSXAnnouncementScraper:
    """Scraper for PSX official announcements"""

    PSX_BASE_URL = "https://dps.psx.com.pk"
    PSX_ANNOUNCEMENTS_URL = "https://dps.psx.com.pk/company-announcements"

    def __init__(self, delay_seconds: float = 2.0):
        """
        Initialize scraper

        Args:
            delay_seconds: Delay between requests to be respectful
        """
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_announcements(
        self,
        days_back: int = 7,
        symbols: Optional[List[str]] = None
    ) -> List[RawAnnouncement]:
        """
        Scrape PSX announcements from last N days

        Args:
            days_back: Number of days to look back
            symbols: Optional list of symbols to filter (None = all)

        Returns:
            List of RawAnnouncement objects
        """
        logger.info(f"Scraping PSX announcements for last {days_back} days")

        announcements = []

        try:
            # Method 1: Try PSX announcements page
            psx_announcements = self._scrape_psx_website(days_back, symbols)
            announcements.extend(psx_announcements)
            logger.info(f"Found {len(psx_announcements)} announcements from PSX website")

        except Exception as e:
            logger.error(f"Failed to scrape PSX website: {e}")

            # Fallback: Try alternative methods
            logger.info("Trying alternative scraping methods...")

            try:
                # Method 2: Try PSX API (if available)
                api_announcements = self._scrape_psx_api(days_back, symbols)
                announcements.extend(api_announcements)
                logger.info(f"Found {len(api_announcements)} announcements from PSX API")

            except Exception as api_error:
                logger.error(f"PSX API failed: {api_error}")

        # Remove duplicates based on announcement_id
        unique_announcements = self._deduplicate_announcements(announcements)
        logger.info(f"Total unique announcements: {len(unique_announcements)}")

        return unique_announcements

    def _scrape_psx_website(
        self,
        days_back: int,
        symbols: Optional[List[str]] = None
    ) -> List[RawAnnouncement]:
        """
        Scrape announcements from PSX website HTML

        PSX website structure (typical):
        - Table with columns: Date, Symbol, Company, Announcement Type, Title, Attachment
        - May be paginated
        - May load dynamically via JavaScript (requires Selenium)
        """
        announcements = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Try main announcements page
        response = self._fetch_url(self.PSX_ANNOUNCEMENTS_URL)

        if not response:
            raise Exception("Failed to fetch PSX announcements page")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Strategy 1: Look for table with announcements
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            # Skip header row
            for row in rows[1:]:
                try:
                    cols = row.find_all('td')

                    if len(cols) >= 4:  # Minimum columns expected
                        announcement = self._parse_announcement_row(cols, row)

                        if announcement:
                            # Filter by date
                            if announcement.announcement_date >= cutoff_date:
                                # Filter by symbols if provided
                                if symbols is None or announcement.symbol in symbols:
                                    announcements.append(announcement)

                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue

        # Strategy 2: Look for div-based announcements (if not table-based)
        if not announcements:
            announcement_divs = soup.find_all('div', class_=re.compile(r'announcement|company-ann|notice'))

            for div in announcement_divs:
                try:
                    announcement = self._parse_announcement_div(div)

                    if announcement and announcement.announcement_date >= cutoff_date:
                        if symbols is None or announcement.symbol in symbols:
                            announcements.append(announcement)

                except Exception as e:
                    logger.debug(f"Failed to parse div: {e}")
                    continue

        return announcements

    def _parse_announcement_row(self, cols, row) -> Optional[RawAnnouncement]:
        """
        Parse announcement from table row

        Expected columns (typical PSX format):
        [Date, Symbol, Company, Type, Title, Attachment]
        """
        try:
            # Extract date (usually first column)
            date_text = cols[0].get_text(strip=True)
            announcement_date = self._parse_date(date_text)

            # Extract symbol (usually second column)
            symbol = cols[1].get_text(strip=True).upper()

            # Extract title (varies, usually 4th or 5th column)
            title = ""
            for col in cols[2:]:
                text = col.get_text(strip=True)
                if len(text) > 10:  # Likely the title
                    title = text
                    break

            if not title:
                title = cols[-2].get_text(strip=True) if len(cols) >= 2 else "Unknown"

            # Extract description (same as title initially)
            description = title

            # Extract attachment URL
            attachment_url = None
            for col in cols:
                link = col.find('a', href=re.compile(r'\.pdf|download|attachment'))
                if link and link.get('href'):
                    href = link['href']
                    attachment_url = href if href.startswith('http') else f"{self.PSX_BASE_URL}{href}"
                    break

            # Extract source URL
            source_url = self.PSX_ANNOUNCEMENTS_URL
            main_link = row.find('a', href=True)
            if main_link:
                href = main_link['href']
                source_url = href if href.startswith('http') else f"{self.PSX_BASE_URL}{href}"

            # Generate announcement ID
            announcement_id = self._generate_announcement_id(
                symbol, announcement_date, title
            )

            return RawAnnouncement(
                announcement_id=announcement_id,
                symbol=symbol,
                announcement_date=announcement_date,
                title=title,
                description=description,
                attachment_url=attachment_url,
                source_url=source_url,
                source="PSX",
                raw_html=str(row)
            )

        except Exception as e:
            logger.debug(f"Failed to parse announcement row: {e}")
            return None

    def _parse_announcement_div(self, div) -> Optional[RawAnnouncement]:
        """Parse announcement from div element"""
        try:
            # Extract text content
            text = div.get_text(strip=True)

            # Look for symbol (usually 3-4 letter ticker)
            symbol_match = re.search(r'\b([A-Z]{3,5})\b', text)
            symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"

            # Look for date
            date_match = re.search(
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})',
                text
            )
            announcement_date = self._parse_date(date_match.group(1)) if date_match else datetime.now()

            # Title is the main text
            title = text[:200]  # First 200 chars

            # Look for links
            attachment_url = None
            link = div.find('a', href=re.compile(r'\.pdf|download'))
            if link:
                href = link['href']
                attachment_url = href if href.startswith('http') else f"{self.PSX_BASE_URL}{href}"

            announcement_id = self._generate_announcement_id(
                symbol, announcement_date, title
            )

            return RawAnnouncement(
                announcement_id=announcement_id,
                symbol=symbol,
                announcement_date=announcement_date,
                title=title,
                description=text,
                attachment_url=attachment_url,
                source_url=self.PSX_ANNOUNCEMENTS_URL,
                source="PSX",
                raw_html=str(div)
            )

        except Exception as e:
            logger.debug(f"Failed to parse announcement div: {e}")
            return None

    def _scrape_psx_api(
        self,
        days_back: int,
        symbols: Optional[List[str]] = None
    ) -> List[RawAnnouncement]:
        """
        Try to fetch announcements from PSX API (if available)

        Note: PSX may or may not have a public API
        This is a placeholder for API-based fetching
        """
        announcements = []

        # Potential API endpoints (to be verified)
        api_endpoints = [
            f"{self.PSX_BASE_URL}/api/announcements",
            f"{self.PSX_BASE_URL}/api/company-announcements",
            f"{self.PSX_BASE_URL}/json/announcements",
        ]

        for endpoint in api_endpoints:
            try:
                response = self._fetch_url(endpoint)

                if response and response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()

                    # Parse JSON response (structure unknown, adapt as needed)
                    if isinstance(data, list):
                        for item in data:
                            announcement = self._parse_api_announcement(item)
                            if announcement:
                                announcements.append(announcement)

                    logger.info(f"Successfully fetched from API: {endpoint}")
                    break

            except Exception as e:
                logger.debug(f"API endpoint failed: {endpoint} - {e}")
                continue

        return announcements

    def _parse_api_announcement(self, data: Dict) -> Optional[RawAnnouncement]:
        """Parse announcement from API JSON response"""
        try:
            # Adapt field names based on actual API response
            symbol = data.get('symbol', data.get('ticker', 'UNKNOWN')).upper()

            # Parse date
            date_str = data.get('date', data.get('announcement_date', data.get('published_date')))
            announcement_date = self._parse_date(date_str) if date_str else datetime.now()

            title = data.get('title', data.get('subject', 'Untitled'))
            description = data.get('description', data.get('content', title))

            attachment_url = data.get('attachment_url', data.get('pdf_url'))
            source_url = data.get('url', data.get('link', self.PSX_ANNOUNCEMENTS_URL))

            announcement_id = self._generate_announcement_id(
                symbol, announcement_date, title
            )

            return RawAnnouncement(
                announcement_id=announcement_id,
                symbol=symbol,
                announcement_date=announcement_date,
                title=title,
                description=description,
                attachment_url=attachment_url,
                source_url=source_url,
                source="PSX_API"
            )

        except Exception as e:
            logger.debug(f"Failed to parse API announcement: {e}")
            return None

    def scrape_symbol_announcements(
        self,
        symbol: str,
        days_back: int = 30
    ) -> List[RawAnnouncement]:
        """
        Scrape announcements for a specific symbol

        Args:
            symbol: Stock symbol (e.g., 'HBL', 'OGDC')
            days_back: Number of days to look back

        Returns:
            List of announcements for the symbol
        """
        logger.info(f"Scraping announcements for {symbol}")

        # Use symbol-specific URL if available
        symbol_url = f"{self.PSX_BASE_URL}/company/{symbol}/announcements"

        try:
            response = self._fetch_url(symbol_url)

            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Parse using same methods as general scraping
                # ... (implementation similar to _scrape_psx_website)

        except Exception as e:
            logger.debug(f"Symbol-specific scraping failed: {e}")

        # Fallback: Filter from general announcements
        all_announcements = self.scrape_announcements(days_back, symbols=[symbol])
        return all_announcements

    def _fetch_url(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Fetch URL with retries and respectful delays

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None if failed
        """
        for attempt in range(max_retries):
            try:
                time.sleep(self.delay_seconds)

                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                return response

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    time.sleep(self.delay_seconds * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None

        return None

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string to datetime object

        Handles multiple formats:
        - DD-MM-YYYY
        - DD/MM/YYYY
        - YYYY-MM-DD
        - ISO format
        """
        # Clean the date string
        date_str = date_str.strip()

        # Try common formats
        formats = [
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%b-%Y',
            '%d %b %Y',
            '%Y-%m-%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback: Try dateutil parser
        try:
            from dateutil import parser as dateutil_parser
            return dateutil_parser.parse(date_str, dayfirst=True)
        except:
            pass

        # Last resort: return current date
        logger.warning(f"Could not parse date: {date_str}, using current date")
        return datetime.now()

    def _generate_announcement_id(
        self,
        symbol: str,
        date: datetime,
        title: str
    ) -> str:
        """
        Generate unique announcement ID

        Format: {SYMBOL}_{YYYYMMDD}_{HASH}
        """
        date_str = date.strftime('%Y%m%d')

        # Create hash from title for uniqueness
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]

        return f"{symbol}_{date_str}_{title_hash}"

    def _deduplicate_announcements(
        self,
        announcements: List[RawAnnouncement]
    ) -> List[RawAnnouncement]:
        """Remove duplicate announcements based on announcement_id"""
        seen = set()
        unique = []

        for announcement in announcements:
            if announcement.announcement_id not in seen:
                seen.add(announcement.announcement_id)
                unique.append(announcement)

        return unique


class SECPFilingScraper:
    """Scraper for SECP regulatory filings (future enhancement)"""

    SECP_BASE_URL = "https://www.secp.gov.pk"

    def __init__(self):
        self.session = requests.Session()

    def scrape_filings(self, days_back: int = 7) -> List[RawAnnouncement]:
        """Scrape SECP filings (placeholder for future implementation)"""
        logger.info("SECP scraper not yet implemented")
        return []


class CompanyIRScraper:
    """Scraper for company investor relations pages (future enhancement)"""

    # Map of symbols to IR page URLs
    COMPANY_IR_URLS = {
        'HBL': 'https://www.hbl.com/investor-relations',
        'UBL': 'https://www.ubldigital.com/investor-relations',
        'MCB': 'https://www.mcb.com.pk/investor-relations',
        'OGDC': 'https://www.ogdcl.com/investor-relations',
        # ... add more as needed
    }

    def __init__(self):
        self.session = requests.Session()

    def scrape_company_ir(self, symbol: str, days_back: int = 7) -> List[RawAnnouncement]:
        """Scrape company IR page (placeholder for future implementation)"""
        logger.info(f"Company IR scraper not yet implemented for {symbol}")
        return []


if __name__ == "__main__":
    # Test the scraper
    print("=" * 60)
    print("PSX ANNOUNCEMENT SCRAPER - TEST MODE")
    print("=" * 60)

    scraper = PSXAnnouncementScraper(delay_seconds=1.0)

    # Test with sample symbols
    test_symbols = ['HBL', 'OGDC', 'LUCK', 'PPL', 'MCB']

    print(f"\nScraping announcements for: {', '.join(test_symbols)}")
    print(f"Looking back: 7 days\n")

    try:
        announcements = scraper.scrape_announcements(
            days_back=7,
            symbols=test_symbols
        )

        print(f"✅ Found {len(announcements)} announcements\n")

        # Display first 5
        for i, ann in enumerate(announcements[:5], 1):
            print(f"{i}. {ann.symbol} - {ann.announcement_date.strftime('%Y-%m-%d')}")
            print(f"   {ann.title}")
            print(f"   Source: {ann.source_url}")
            if ann.attachment_url:
                print(f"   Attachment: {ann.attachment_url}")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nNote: This scraper requires internet access to PSX website.")
        print("If testing offline, it will return empty results.")
