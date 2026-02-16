"""
PSX Company Data Extractor

Extracts financial data from PSX company pages (HTML tables)
More reliable than PDF parsing for PSX since PDFs are often scanned images.

Extracts:
- Annual financial summaries (Sales, PAT, EPS)
- Quarterly financial data
- Financial ratios
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CompanyFinancials:
    """Financial data extracted from company page"""
    symbol: str
    extracted_date: datetime

    # Annual Data (keyed by year)
    annual_sales: Dict[str, float] = None  # {year: sales}
    annual_pat: Dict[str, float] = None  # {year: profit after tax}
    annual_eps: Dict[str, float] = None  # {year: EPS}

    # Quarterly Data (keyed by period)
    quarterly_sales: Dict[str, float] = None  # {period: sales}
    quarterly_pat: Dict[str, float] = None
    quarterly_eps: Dict[str, float] = None

    # Ratios (keyed by year)
    gross_margin: Dict[str, float] = None  # {year: margin%}
    net_margin: Dict[str, float] = None
    eps_growth: Dict[str, float] = None
    peg_ratio: Dict[str, float] = None

    def __post_init__(self):
        if self.annual_sales is None:
            self.annual_sales = {}
        if self.annual_pat is None:
            self.annual_pat = {}
        if self.annual_eps is None:
            self.annual_eps = {}
        if self.quarterly_sales is None:
            self.quarterly_sales = {}
        if self.quarterly_pat is None:
            self.quarterly_pat = {}
        if self.quarterly_eps is None:
            self.quarterly_eps = {}
        if self.gross_margin is None:
            self.gross_margin = {}
        if self.net_margin is None:
            self.net_margin = {}
        if self.eps_growth is None:
            self.eps_growth = {}
        if self.peg_ratio is None:
            self.peg_ratio = {}


class PSXCompanyDataExtractor:
    """Extract financial data from PSX company pages"""

    PSX_BASE_URL = "https://dps.psx.com.pk"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_company_page(self, symbol: str) -> Optional[str]:
        """Fetch company page HTML"""
        url = f"{self.PSX_BASE_URL}/company/{symbol}"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text

        except Exception as e:
            logger.error(f"Failed to fetch company page for {symbol}: {e}")
            return None

    def extract_financials(self, symbol: str) -> Optional[CompanyFinancials]:
        """
        Extract all available financial data from company page

        Args:
            symbol: Stock symbol

        Returns:
            CompanyFinancials object or None
        """
        html = self.fetch_company_page(symbol)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        financials = CompanyFinancials(
            symbol=symbol,
            extracted_date=datetime.now()
        )

        # Find all tables
        tables = soup.find_all('table', class_='tbl')

        for table in tables:
            # Check table headers to identify type
            headers = table.find_all('th')
            header_texts = [h.get_text(strip=True) for h in headers]

            # Annual Financial Summary
            if self._is_annual_summary(header_texts):
                self._parse_annual_summary(table, financials)

            # Quarterly Financial Data
            elif self._is_quarterly_summary(header_texts):
                self._parse_quarterly_summary(table, financials)

            # Financial Ratios
            elif self._is_ratio_table(header_texts):
                self._parse_ratio_table(table, financials)

        return financials

    def _is_annual_summary(self, headers: List[str]) -> bool:
        """Check if table is annual financial summary"""
        # Headers like: ['', '2025', '2024', '2023', '2022']
        year_count = sum(1 for h in headers if re.match(r'^\d{4}$', h))
        return year_count >= 3  # At least 3 years

    def _is_quarterly_summary(self, headers: List[str]) -> bool:
        """Check if table is quarterly data"""
        # Headers like: ['', 'Q1 2026', 'Q3 2025', ...]
        quarter_count = sum(1 for h in headers if 'Q' in h or '2026' in h or '2025' in h)
        return quarter_count >= 2 and not self._is_annual_summary(headers)

    def _is_ratio_table(self, headers: List[str]) -> bool:
        """Check if table contains ratios"""
        first_col = headers[0].lower() if headers else ''
        return 'margin' in first_col or 'growth' in first_col or 'peg' in first_col

    def _parse_annual_summary(self, table, financials: CompanyFinancials):
        """Parse annual financial summary table"""
        try:
            headers = [h.get_text(strip=True) for h in table.find_all('th')]
            years = [h for h in headers[1:] if re.match(r'^\d{4}$', h)]

            rows = table.find_all('tr')

            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) < 2:
                    continue

                label = cols[0].get_text(strip=True).lower()

                # Parse values for each year
                for i, year in enumerate(years, start=1):
                    if i >= len(cols):
                        break

                    value_text = cols[i].get_text(strip=True).replace(',', '')
                    value = self._parse_number(value_text)

                    if value is None:
                        continue

                    # Store based on label
                    if 'sales' in label or 'revenue' in label:
                        financials.annual_sales[year] = value * 1000  # Convert to actual value
                    elif 'profit after tax' in label or 'pat' in label:
                        financials.annual_pat[year] = value * 1000
                    elif 'eps' in label:
                        financials.annual_eps[year] = value

            logger.info(f"Extracted annual data: {len(financials.annual_sales)} years")

        except Exception as e:
            logger.error(f"Failed to parse annual summary: {e}")

    def _parse_quarterly_summary(self, table, financials: CompanyFinancials):
        """Parse quarterly financial data table"""
        try:
            headers = [h.get_text(strip=True) for h in table.find_all('th')]
            periods = [h for h in headers[1:] if 'Q' in h or '202' in h]

            rows = table.find_all('tr')

            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) < 2:
                    continue

                label = cols[0].get_text(strip=True).lower()

                # Parse values for each period
                for i, period in enumerate(periods, start=1):
                    if i >= len(cols):
                        break

                    value_text = cols[i].get_text(strip=True).replace(',', '')
                    value = self._parse_number(value_text)

                    if value is None:
                        continue

                    # Store based on label
                    if 'sales' in label or 'revenue' in label:
                        financials.quarterly_sales[period] = value * 1000
                    elif 'profit after tax' in label or 'pat' in label:
                        financials.quarterly_pat[period] = value * 1000
                    elif 'eps' in label:
                        financials.quarterly_eps[period] = value

            logger.info(f"Extracted quarterly data: {len(financials.quarterly_sales)} periods")

        except Exception as e:
            logger.error(f"Failed to parse quarterly summary: {e}")

    def _parse_ratio_table(self, table, financials: CompanyFinancials):
        """Parse financial ratios table"""
        try:
            headers = [h.get_text(strip=True) for h in table.find_all('th')]
            years = [h for h in headers[1:] if re.match(r'^\d{4}$', h)]

            rows = table.find_all('tr')

            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) < 2:
                    continue

                label = cols[0].get_text(strip=True).lower()

                # Parse values for each year
                for i, year in enumerate(years, start=1):
                    if i >= len(cols):
                        break

                    value_text = cols[i].get_text(strip=True).replace(',', '')
                    value = self._parse_number(value_text)

                    if value is None:
                        continue

                    # Store based on label
                    if 'gross profit margin' in label or 'gross margin' in label:
                        financials.gross_margin[year] = value
                    elif 'net profit margin' in label or 'net margin' in label:
                        financials.net_margin[year] = value
                    elif 'eps growth' in label:
                        financials.eps_growth[year] = value
                    elif 'peg' in label:
                        financials.peg_ratio[year] = value

            logger.info(f"Extracted ratio data for {len(financials.gross_margin)} years")

        except Exception as e:
            logger.error(f"Failed to parse ratio table: {e}")

    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text, handling negatives in parentheses"""
        if not text or text == '-':
            return None

        # Handle negative in parentheses
        if text.startswith('(') and text.endswith(')'):
            text = '-' + text[1:-1]

        try:
            return float(text)
        except ValueError:
            return None

    def to_dict(self, financials: CompanyFinancials) -> Dict:
        """Convert to dictionary"""
        data = asdict(financials)
        data['extracted_date'] = data['extracted_date'].isoformat()
        return data

    def to_json(self, financials: CompanyFinancials, filepath: Optional[str] = None) -> str:
        """Convert to JSON"""
        data = self.to_dict(financials)
        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
            logger.info(f"Saved to: {filepath}")

        return json_str


if __name__ == "__main__":
    print("=" * 70)
    print("PSX COMPANY DATA EXTRACTOR - TEST")
    print("=" * 70)
    print()

    extractor = PSXCompanyDataExtractor()

    # Test with PIBTL
    print("Extracting financial data for PIBTL...")
    print()

    financials = extractor.extract_financials("PIBTL")

    if financials:
        print("✓ Successfully extracted financial data!")
        print("=" * 70)
        print()

        print(f"Company: {financials.symbol}")
        print(f"Extracted: {financials.extracted_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        print("ANNUAL DATA:")
        print(f"  Sales (PKR '000): {financials.annual_sales}")
        print(f"  PAT (PKR '000):   {financials.annual_pat}")
        print(f"  EPS (Rs):         {financials.annual_eps}")
        print()

        print("QUARTERLY DATA:")
        print(f"  Sales (PKR '000): {financials.quarterly_sales}")
        print(f"  PAT (PKR '000):   {financials.quarterly_pat}")
        print(f"  EPS (Rs):         {financials.quarterly_eps}")
        print()

        print("RATIOS:")
        print(f"  Gross Margin (%): {financials.gross_margin}")
        print(f"  Net Margin (%):   {financials.net_margin}")
        print(f"  EPS Growth (%):   {financials.eps_growth}")
        print(f"  PEG Ratio:        {financials.peg_ratio}")
        print()

        # Calculate latest metrics
        if financials.annual_sales:
            latest_year = max(financials.annual_sales.keys())
            print(f"LATEST YEAR ({latest_year}):")
            print(f"  Revenue: PKR {financials.annual_sales[latest_year]:,.0f}")
            if latest_year in financials.annual_pat:
                print(f"  Profit:  PKR {financials.annual_pat[latest_year]:,.0f}")
            if latest_year in financials.annual_eps:
                print(f"  EPS:     Rs. {financials.annual_eps[latest_year]:.2f}")
            if latest_year in financials.net_margin:
                print(f"  Net Margin: {financials.net_margin[latest_year]:.2f}%")
            print()

        # Save to JSON
        json_path = "pibtl_company_financials.json"
        extractor.to_json(financials, json_path)
        print(f"✓ Saved to: {json_path}")

    else:
        print("✗ Failed to extract data")
