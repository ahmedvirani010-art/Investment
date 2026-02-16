"""
Data Collection Manager

Unified interface for collecting and storing historical price data.
Manages multiple data sources with automatic fallback.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
import pandas as pd
import json

from data_collection.base_collector import DataCollectorRegistry, CollectionResult
from data_collection.csv_collector import CSVCollector
from data_collection.yahoo_finance_collector import YahooFinanceCollector
from data_collection.investing_com_collector import InvestingComCollector


class DataCollectionManager:
    """
    High-level manager for collecting and storing price data

    Features:
    - Multiple data source support with automatic fallback
    - Local caching to avoid redundant fetches
    - Batch collection with progress tracking
    - Data validation and quality checks
    """

    def __init__(self, storage_dir: str = "data"):
        """
        Args:
            storage_dir: Root directory for data storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.csv_dir = self.storage_dir / "csv"
        self.cache_dir = self.storage_dir / "cache"
        self.csv_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize registry
        self.registry = DataCollectorRegistry()

        # Register collectors in priority order
        self._setup_collectors()

    def _setup_collectors(self):
        """Initialize and register all data collectors"""

        # Priority 1: CSV files (fastest, local)
        csv_collector = CSVCollector(data_dir=str(self.csv_dir))
        self.registry.register(csv_collector, priority=10)

        # Priority 2: Yahoo Finance (reliable, free API)
        try:
            yahoo_collector = YahooFinanceCollector()
            if yahoo_collector.available:
                self.registry.register(yahoo_collector, priority=5)
        except Exception as e:
            print(f"⚠️  Yahoo Finance collector unavailable: {e}")

        # Priority 3: Investing.com (web scraping, less reliable)
        # Disabled by default due to reliability issues
        # investing_collector = InvestingComCollector()
        # self.registry.register(investing_collector, priority=1)

    def collect(
        self,
        symbol: str,
        days: int = 365,
        end_date: Optional[datetime] = None,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Collect historical data for a symbol

        Args:
            symbol: Stock symbol (e.g., "PPL")
            days: Number of days of history to collect
            end_date: End date (defaults to today)
            force_refresh: Skip cache and fetch fresh data

        Returns:
            DataFrame with OHLCV data or None if collection failed
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=days)

        # Check cache unless force refresh
        if not force_refresh:
            cached = self._load_from_cache(symbol)

            if cached is not None:
                # Ensure timezone-naive for comparison
                if cached.index.tz is not None:
                    cached.index = cached.index.tz_localize(None)

                # Filter to requested date range
                cached = cached[(cached.index >= start_date) & (cached.index <= end_date)]

                if not cached.empty and len(cached) >= days * 0.8:  # Allow 20% missing
                    print(f"✅ Loaded {symbol} from cache ({len(cached)} days)")
                    return cached

        # Collect from sources
        print(f"📥 Collecting {symbol} data...")

        df = self.registry.collect_with_fallback(symbol, start_date, end_date)

        if df is not None and not df.empty:
            # Save to cache
            self._save_to_cache(symbol, df)
            print(f"✅ Collected {len(df)} days for {symbol}")
            return df
        else:
            print(f"❌ Failed to collect data for {symbol}")
            return None

    def collect_batch(
        self,
        symbols: List[str],
        days: int = 365,
        delay_seconds: float = 1.0
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Collect data for multiple symbols

        Args:
            symbols: List of stock symbols
            days: Number of days to collect
            delay_seconds: Delay between requests

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        import time

        results = {}

        print(f"\n{'='*80}")
        print(f"BATCH COLLECTION: {len(symbols)} symbols, {days} days")
        print(f"{'='*80}\n")

        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] {symbol}")

            df = self.collect(symbol, days=days)
            results[symbol] = df

            if i < len(symbols) - 1:
                time.sleep(delay_seconds)

        # Summary
        successful = sum(1 for df in results.values() if df is not None)

        print(f"\n{'='*80}")
        print(f"BATCH COMPLETE: {successful}/{len(symbols)} successful")
        print(f"{'='*80}\n")

        return results

    def import_csv_text(
        self,
        symbol: str,
        csv_text: str
    ) -> CollectionResult:
        """
        Import data from CSV text

        Useful for pasting data directly into the system.

        Args:
            symbol: Stock symbol
            csv_text: CSV content

        Returns:
            CollectionResult
        """
        csv_collector = CSVCollector(data_dir=str(self.csv_dir))
        result = csv_collector.import_from_text(symbol, csv_text, save=True)

        if result.success:
            # Also save to cache
            df = csv_collector.get_prices_dataframe(
                symbol,
                datetime(2000, 1, 1),
                datetime.now()
            )
            if df is not None:
                self._save_to_cache(symbol, df)

        return result

    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for symbol"""
        # Try Parquet first, fall back to CSV
        parquet_path = self.cache_dir / f"{symbol}.parquet"
        csv_path = self.cache_dir / f"{symbol}.csv"

        if parquet_path.exists():
            return parquet_path
        elif csv_path.exists():
            return csv_path
        else:
            # Default to parquet (will try CSV fallback if save fails)
            return parquet_path

    def _load_from_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load data from cache"""
        # Try Parquet first
        parquet_path = self.cache_dir / f"{symbol}.parquet"
        if parquet_path.exists():
            try:
                return pd.read_parquet(parquet_path)
            except Exception:
                pass

        # Fall back to CSV
        csv_path = self.cache_dir / f"{symbol}.csv"
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                # Parse date index
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                return df
            except Exception:
                pass

        return None

    def _save_to_cache(self, symbol: str, df: pd.DataFrame):
        """Save data to cache (Parquet preferred, CSV fallback)"""
        parquet_path = self.cache_dir / f"{symbol}.parquet"
        csv_path = self.cache_dir / f"{symbol}.csv"

        # Try Parquet first
        try:
            df.to_parquet(parquet_path)
            # Remove CSV cache if it exists
            if csv_path.exists():
                csv_path.unlink()
            return
        except Exception:
            pass

        # Fall back to CSV
        try:
            df.to_csv(csv_path)
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")

    def get_cache_info(self, symbol: str) -> Optional[Dict]:
        """
        Get information about cached data

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with cache info or None
        """
        cache_path = self._get_cache_path(symbol)

        if not cache_path.exists():
            return None

        df = self._load_from_cache(symbol)

        if df is None:
            return None

        return {
            'symbol': symbol,
            'rows': len(df),
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'file_size': cache_path.stat().st_size,
            'last_modified': datetime.fromtimestamp(cache_path.stat().st_mtime)
        }

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear cached data

        Args:
            symbol: Specific symbol to clear (or None for all)
        """
        if symbol:
            cache_path = self._get_cache_path(symbol)
            if cache_path.exists():
                cache_path.unlink()
                print(f"🗑️  Cleared cache for {symbol}")
        else:
            for cache_file in self.cache_dir.glob("*.parquet"):
                cache_file.unlink()
            print(f"🗑️  Cleared all cache")


if __name__ == "__main__":
    """Test data collection manager"""

    print("="*80)
    print("DATA COLLECTION MANAGER - TEST")
    print("="*80)

    manager = DataCollectionManager(storage_dir="data")

    # Test 1: Import from CSV text (the PPL data from earlier)
    print("\n" + "="*80)
    print("TEST 1: Import CSV Text")
    print("="*80)

    PPL_CSV = """Date,Price,Open,High,Low,Vol.,Change %
02/16/2026,232,237,237.6,231,1.11M,-1.81%
02/13/2026,236.27,234,238,228.97,12.91M,-0.38%
02-12-26,237.17,248,249,232.2,16.50M,-4.52%
02-11-26,248.39,252.7,254.74,246.97,2.79M,-1.70%
02-10-26,252.68,256,256.99,251.01,4.73M,-0.46%"""

    result = manager.import_csv_text('PPL', PPL_CSV)
    print(f"\nImport Result: {result.success} ({result.rows_collected} rows)")

    # Test 2: Collect (should use cache)
    print("\n" + "="*80)
    print("TEST 2: Collect (from cache)")
    print("="*80)

    df = manager.collect('PPL', days=90)

    if df is not None:
        print(f"\nCollected {len(df)} days")
        print(df.head())

    # Test 3: Cache info
    print("\n" + "="*80)
    print("TEST 3: Cache Info")
    print("="*80)

    info = manager.get_cache_info('PPL')

    if info:
        print(f"\nCache Info for PPL:")
        print(f"  Rows: {info['rows']}")
        print(f"  Date range: {info['start_date'].date()} to {info['end_date'].date()}")
        print(f"  File size: {info['file_size']:,} bytes")
        print(f"  Last modified: {info['last_modified']}")

    print("\n✅ Data Collection Manager ready for use")
