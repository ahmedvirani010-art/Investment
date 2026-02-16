"""
Base classes for historical price data collection

Provides abstract interface for different data sources (APIs, web scraping, CSV).
All collectors implement a common interface for consistency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd


@dataclass
class CollectionResult:
    """Result from a data collection attempt"""
    success: bool
    symbol: str
    rows_collected: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    error: Optional[str] = None
    source: Optional[str] = None


class BaseDataCollector(ABC):
    """
    Abstract base class for all data collectors

    Subclasses implement specific collection strategies:
    - WebScraperCollector: Scrape from financial websites
    - APICollector: Fetch from REST APIs
    - CSVCollector: Import from CSV files
    """

    def __init__(self, source_name: str):
        """
        Args:
            source_name: Identifier for this data source (e.g., "investing.com", "psx_api")
        """
        self.source_name = source_name

    @abstractmethod
    def collect_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> CollectionResult:
        """
        Collect historical prices for a single symbol

        Args:
            symbol: Stock symbol (e.g., "PPL")
            start_date: Start of date range
            end_date: End of date range

        Returns:
            CollectionResult with success status and data
        """
        pass

    @abstractmethod
    def get_prices_dataframe(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Get historical prices as a DataFrame

        Args:
            symbol: Stock symbol
            start_date: Start of date range
            end_date: End of date range

        Returns:
            DataFrame with columns: [Date, Open, High, Low, Close, Volume]
            Index: DatetimeIndex
            None if collection failed
        """
        pass

    def collect_batch(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        delay_seconds: float = 1.0
    ) -> Dict[str, CollectionResult]:
        """
        Collect data for multiple symbols

        Args:
            symbols: List of stock symbols
            start_date: Start of date range
            end_date: End of date range
            delay_seconds: Delay between requests (for rate limiting)

        Returns:
            Dictionary mapping symbol to CollectionResult
        """
        import time

        results = {}

        for i, symbol in enumerate(symbols):
            print(f"Collecting {symbol} ({i+1}/{len(symbols)})...")

            try:
                result = self.collect_symbol(symbol, start_date, end_date)
                results[symbol] = result

                if result.success:
                    print(f"  ✅ Success: {result.rows_collected} rows")
                else:
                    print(f"  ❌ Failed: {result.error}")

            except Exception as e:
                print(f"  ❌ Exception: {str(e)}")
                results[symbol] = CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error=str(e),
                    source=self.source_name
                )

            # Rate limiting
            if i < len(symbols) - 1:
                time.sleep(delay_seconds)

        return results

    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required columns and format

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        if df is None or df.empty:
            return False

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Check columns exist (case-insensitive)
        df_cols_lower = {col.lower(): col for col in df.columns}

        for col in required_cols:
            if col.lower() not in df_cols_lower:
                return False

        # Check date index
        if not isinstance(df.index, pd.DatetimeIndex):
            return False

        return True

    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame to expected format

        Args:
            df: Raw DataFrame

        Returns:
            Standardized DataFrame with consistent column names and types
        """
        # Create column mapping (case-insensitive)
        col_map = {col.lower(): col for col in df.columns}

        # Rename to standard names
        standard_cols = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'vol': 'Volume',
            'vol.': 'Volume'
        }

        rename_map = {}
        for std_name, target_name in standard_cols.items():
            if std_name in col_map:
                rename_map[col_map[std_name]] = target_name

        df = df.rename(columns=rename_map)

        # Ensure numeric types
        for col in ['Open', 'High', 'Low', 'Close']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Handle Volume (may have M/K suffixes)
        if 'Volume' in df.columns:
            df['Volume'] = df['Volume'].apply(self._parse_volume)

        # Remove timezone if present (for consistent comparison)
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Sort by date
        df = df.sort_index()

        # Select only required columns
        available_cols = [col for col in ['Open', 'High', 'Low', 'Close', 'Volume'] if col in df.columns]
        df = df[available_cols]

        return df

    @staticmethod
    def _parse_volume(vol) -> float:
        """Parse volume strings like '1.11M' to numbers"""
        if pd.isna(vol):
            return 0.0

        if isinstance(vol, (int, float)):
            return float(vol)

        if isinstance(vol, str):
            vol = vol.strip()

            if vol.endswith('M'):
                return float(vol[:-1]) * 1_000_000
            elif vol.endswith('K'):
                return float(vol[:-1]) * 1_000
            elif vol.endswith('B'):
                return float(vol[:-1]) * 1_000_000_000
            else:
                try:
                    return float(vol.replace(',', ''))
                except ValueError:
                    return 0.0

        return 0.0


class DataCollectorRegistry:
    """
    Registry for managing multiple data collectors

    Allows trying multiple sources in fallback order.
    """

    def __init__(self):
        self.collectors: List[BaseDataCollector] = []

    def register(self, collector: BaseDataCollector, priority: int = 0):
        """
        Register a data collector

        Args:
            collector: Collector instance
            priority: Higher priority collectors are tried first
        """
        self.collectors.append((priority, collector))
        self.collectors.sort(key=lambda x: x[0], reverse=True)

    def collect_with_fallback(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Try collectors in priority order until one succeeds

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame if any collector succeeds, None otherwise
        """
        for priority, collector in self.collectors:
            print(f"Trying {collector.source_name} (priority {priority})...")

            try:
                df = collector.get_prices_dataframe(symbol, start_date, end_date)

                if df is not None and not df.empty:
                    print(f"  ✅ Success: {len(df)} rows from {collector.source_name}")
                    return df
                else:
                    print(f"  ⚠️  No data from {collector.source_name}")

            except Exception as e:
                print(f"  ❌ {collector.source_name} failed: {str(e)}")

        print(f"  ❌ All collectors failed for {symbol}")
        return None
