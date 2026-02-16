"""
Yahoo Finance Data Collector

Uses yfinance library to fetch historical price data.
More reliable than web scraping, supports multiple exchanges.

Install: pip install yfinance
"""

from datetime import datetime
from typing import Optional
import pandas as pd

from data_collection.base_collector import BaseDataCollector, CollectionResult


class YahooFinanceCollector(BaseDataCollector):
    """
    Collector using Yahoo Finance API via yfinance library

    Supports multiple exchanges including PSX (Pakistan Stock Exchange).
    PSX symbols need .KA suffix (e.g., "PPL.KA" for PPL on PSX).
    """

    # PSX symbols (add .KA suffix for Yahoo Finance)
    PSX_SUFFIX = ".KA"

    def __init__(self):
        super().__init__("yahoo_finance")

        try:
            import yfinance as yf
            self.yf = yf
            self.available = True
        except ImportError:
            print("⚠️  yfinance not installed. Run: pip install yfinance")
            self.available = False

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol for Yahoo Finance

        Args:
            symbol: Stock symbol (e.g., "PPL")

        Returns:
            Yahoo Finance symbol (e.g., "PPL.KA")
        """
        # If already has suffix, use as-is
        if '.' in symbol:
            return symbol

        # Add PSX suffix
        return f"{symbol}{self.PSX_SUFFIX}"

    def collect_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> CollectionResult:
        """Fetch data from Yahoo Finance"""

        if not self.available:
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error="yfinance library not available",
                source=self.source_name
            )

        yf_symbol = self._format_symbol(symbol)

        try:
            # Create Ticker object
            ticker = self.yf.Ticker(yf_symbol)

            # Download historical data
            df = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=False  # Get raw OHLC without adjustments
            )

            if df is None or df.empty:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error="No data returned (symbol may not exist or no data in range)",
                    source=self.source_name
                )

            # Yahoo Finance returns: Date, Open, High, Low, Close, Volume, Dividends, Stock Splits
            # We only need OHLCV
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[required_cols]

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

        except Exception as e:
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error=str(e),
                source=self.source_name
            )

    def get_prices_dataframe(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Get prices from Yahoo Finance"""

        result = self.collect_symbol(symbol, start_date, end_date)

        if result.success:
            return getattr(self, '_cached_data', {}).get(symbol)
        else:
            return None

    def get_info(self, symbol: str) -> dict:
        """
        Get company info for symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with company information
        """
        if not self.available:
            return {}

        try:
            yf_symbol = self._format_symbol(symbol)
            ticker = self.yf.Ticker(yf_symbol)
            return ticker.info
        except Exception:
            return {}


if __name__ == "__main__":
    """Test Yahoo Finance collector"""
    from datetime import timedelta

    print("="*80)
    print("YAHOO FINANCE COLLECTOR - TEST")
    print("="*80)

    collector = YahooFinanceCollector()

    if not collector.available:
        print("\n❌ yfinance not available")
        print("   Install with: pip install yfinance")
        exit(1)

    # Test with PPL (Pakistan Petroleum Limited)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print(f"\nFetching PPL data...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Yahoo symbol: {collector._format_symbol('PPL')}")

    result = collector.collect_symbol('PPL', start_date, end_date)

    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Rows: {result.rows_collected}")

    if result.success:
        print(f"  Date range: {result.start_date.date()} to {result.end_date.date()}")

        df = collector.get_prices_dataframe('PPL', start_date, end_date)

        print(f"\nData Preview:")
        print(df.head())
        print(f"\nRecent Data:")
        print(df.tail())

        print(f"\nStatistics:")
        print(f"  Total days: {len(df)}")
        print(f"  Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
        print(f"  Latest close: {df['Close'].iloc[-1]:.2f}")

        # Try to get company info
        info = collector.get_info('PPL')
        if info:
            print(f"\nCompany Info:")
            print(f"  Name: {info.get('longName', 'N/A')}")
            print(f"  Sector: {info.get('sector', 'N/A')}")
            print(f"  Industry: {info.get('industry', 'N/A')}")

    else:
        print(f"  Error: {result.error}")
        print(f"\n⚠️  Note: PSX symbols on Yahoo Finance use .KA suffix")
        print(f"   If this fails, the symbol may not be available on Yahoo Finance")
