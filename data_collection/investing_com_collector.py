"""
Investing.com Web Scraper

Collects historical price data from investing.com
Supports PSX (Pakistan Stock Exchange) and other markets.
"""

from datetime import datetime
from typing import Optional, Dict
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup

from data_collection.base_collector import BaseDataCollector, CollectionResult


class InvestingComCollector(BaseDataCollector):
    """
    Web scraper for investing.com historical data

    Note: investing.com may require specific headers and has rate limits.
    This is a basic implementation that may need adjustments based on
    site changes.
    """

    # Symbol mapping for PSX stocks (investing.com uses specific URLs)
    PSX_SYMBOL_MAP = {
        'PPL': 'pakistan-petroleum-limited',
        'OGDC': 'oil-gas-development-co-ltd',
        'PSO': 'pakistan-state-oil',
        'ENGRO': 'engro-corporation',
        'MCB': 'mcb-bank',
        'HBL': 'habib-bank',
        'UBL': 'united-bank',
        'HUBC': 'hub-power-co',
        'LUCK': 'lucky-cement',
        'FFC': 'fauji-fertilizer-co',
        # Add more as needed
    }

    def __init__(self, user_agent: Optional[str] = None):
        """
        Args:
            user_agent: Custom user agent string (optional)
        """
        super().__init__("investing.com")

        self.base_url = "https://www.investing.com"
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def get_symbol_url(self, symbol: str) -> Optional[str]:
        """
        Get investing.com URL for symbol

        Args:
            symbol: Stock symbol (e.g., "PPL")

        Returns:
            URL string or None if symbol not found
        """
        if symbol in self.PSX_SYMBOL_MAP:
            slug = self.PSX_SYMBOL_MAP[symbol]
            return f"{self.base_url}/equities/{slug}-historical-data"
        else:
            # Try to construct URL (may not work for all symbols)
            slug = symbol.lower().replace('_', '-')
            return f"{self.base_url}/equities/{slug}-historical-data"

    def collect_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> CollectionResult:
        """
        Scrape historical data from investing.com

        Note: This is a basic implementation. investing.com may use
        JavaScript/AJAX for loading data, which would require more
        sophisticated scraping (e.g., Selenium).
        """

        url = self.get_symbol_url(symbol)

        if url is None:
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error="Symbol not found in mapping",
                source=self.source_name
            )

        try:
            # Add date range parameters
            params = {
                'start_date': start_date.strftime('%m/%d/%Y'),
                'end_date': end_date.strftime('%m/%d/%Y'),
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            if response.status_code != 200:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error=f"HTTP {response.status_code}",
                    source=self.source_name
                )

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find historical data table
            # (Structure may vary - this is a template)
            table = soup.find('table', {'class': 'historical-data-table'})

            if table is None:
                # Try alternative selectors
                table = soup.find('table', {'id': 'curr_table'})

            if table is None:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error="Data table not found on page (site structure may have changed)",
                    source=self.source_name
                )

            # Parse table to DataFrame
            df = self._parse_table(table)

            if df is None or df.empty:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error="Failed to parse data table",
                    source=self.source_name
                )

            # Standardize
            df = self.standardize_dataframe(df)

            # Cache
            if not hasattr(self, '_cached_data'):
                self._cached_data = {}
            self._cached_data[symbol] = df

            return CollectionResult(
                success=True,
                symbol=symbol,
                rows_collected=len(df),
                start_date=df.index[0] if len(df) > 0 else None,
                end_date=df.index[-1] if len(df) > 0 else None,
                source=self.source_name
            )

        except requests.exceptions.RequestException as e:
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error=f"Network error: {str(e)}",
                source=self.source_name
            )
        except Exception as e:
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error=str(e),
                source=self.source_name
            )

    def _parse_table(self, table) -> Optional[pd.DataFrame]:
        """
        Parse HTML table to DataFrame

        Args:
            table: BeautifulSoup table element

        Returns:
            DataFrame or None
        """
        try:
            # Extract headers
            headers = []
            header_row = table.find('thead').find('tr') if table.find('thead') else None

            if header_row:
                headers = [th.text.strip() for th in header_row.find_all('th')]
            else:
                # Try first row
                first_row = table.find('tr')
                headers = [th.text.strip() for th in first_row.find_all(['th', 'td'])]

            # Extract data rows
            rows = []
            tbody = table.find('tbody') if table.find('tbody') else table

            for tr in tbody.find_all('tr'):
                cells = [td.text.strip() for td in tr.find_all('td')]
                if cells:
                    rows.append(cells)

            if not rows:
                return None

            # Create DataFrame
            df = pd.DataFrame(rows, columns=headers)

            # Find and parse date column
            date_col = None
            for col in df.columns:
                if 'date' in col.lower():
                    date_col = col
                    break

            if date_col is None and len(df.columns) > 0:
                # Assume first column is date
                date_col = df.columns[0]

            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], format='mixed', errors='coerce')
                df.set_index(date_col, inplace=True)

            return df

        except Exception:
            return None

    def get_prices_dataframe(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Get prices from investing.com"""

        result = self.collect_symbol(symbol, start_date, end_date)

        if result.success:
            return getattr(self, '_cached_data', {}).get(symbol)
        else:
            return None

    def add_symbol_mapping(self, symbol: str, slug: str):
        """
        Add custom symbol mapping

        Args:
            symbol: Stock symbol (e.g., "XYZ")
            slug: investing.com URL slug (e.g., "xyz-corporation")
        """
        self.PSX_SYMBOL_MAP[symbol] = slug


# Note: investing.com often uses JavaScript to load data
# For production use, consider:
# 1. Using Selenium for JavaScript-rendered content
# 2. Using their API if available (may require subscription)
# 3. Using alternative data sources like Yahoo Finance, Alpha Vantage


if __name__ == "__main__":
    """Test investing.com collector"""
    from datetime import timedelta

    print("="*80)
    print("INVESTING.COM COLLECTOR - TEST")
    print("="*80)

    collector = InvestingComCollector()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    print(f"\nAttempting to fetch PPL data...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")

    result = collector.collect_symbol('PPL', start_date, end_date)

    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Rows: {result.rows_collected}")
    print(f"  Error: {result.error}")

    if result.success:
        df = collector.get_prices_dataframe('PPL', start_date, end_date)
        print(f"\nData Preview:")
        print(df.head())
    else:
        print(f"\n⚠️  Note: investing.com often requires JavaScript rendering.")
        print(f"   Consider using CSV import or alternative data sources.")
