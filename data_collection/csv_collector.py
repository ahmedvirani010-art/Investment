"""
CSV Data Collector

Imports historical price data from CSV files.
Useful for manual data import or as a backup data source.
"""

from datetime import datetime
from typing import Optional
import pandas as pd
from pathlib import Path

from data_collection.base_collector import BaseDataCollector, CollectionResult


class CSVCollector(BaseDataCollector):
    """
    Collector for importing data from CSV files

    Expected CSV format:
    - Date column (various formats supported)
    - Open, High, Low, Close, Volume columns
    - Header row required
    """

    def __init__(self, data_dir: str = "data/csv"):
        """
        Args:
            data_dir: Directory containing CSV files (one per symbol)
        """
        super().__init__("csv_files")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_csv_path(self, symbol: str) -> Path:
        """Get path to CSV file for symbol"""
        return self.data_dir / f"{symbol}.csv"

    def collect_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> CollectionResult:
        """Load data from CSV file"""

        csv_path = self.get_csv_path(symbol)

        if not csv_path.exists():
            return CollectionResult(
                success=False,
                symbol=symbol,
                rows_collected=0,
                error=f"CSV file not found: {csv_path}",
                source=self.source_name
            )

        try:
            df = pd.read_csv(csv_path)

            # Find date column (try common names)
            date_cols = ['Date', 'date', 'DATE', 'Timestamp', 'timestamp']
            date_col = None

            for col in date_cols:
                if col in df.columns:
                    date_col = col
                    break

            if date_col is None:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error="No date column found in CSV",
                    source=self.source_name
                )

            # Parse dates
            df[date_col] = pd.to_datetime(df[date_col], format='mixed')
            df.set_index(date_col, inplace=True)

            # Standardize
            df = self.standardize_dataframe(df)

            # Filter date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            if df.empty:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error=f"No data in date range {start_date.date()} to {end_date.date()}",
                    source=self.source_name
                )

            # Store for later retrieval
            self._cached_data = {symbol: df}

            return CollectionResult(
                success=True,
                symbol=symbol,
                rows_collected=len(df),
                start_date=df.index[0],
                end_date=df.index[-1],
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
        """Get prices from CSV"""

        result = self.collect_symbol(symbol, start_date, end_date)

        if result.success:
            return getattr(self, '_cached_data', {}).get(symbol)
        else:
            return None

    def import_from_text(
        self,
        symbol: str,
        csv_text: str,
        save: bool = True
    ) -> CollectionResult:
        """
        Import data from CSV text (useful for pasting data)

        Args:
            symbol: Stock symbol
            csv_text: CSV content as string
            save: Whether to save to file

        Returns:
            CollectionResult
        """
        from io import StringIO

        try:
            df = pd.read_csv(StringIO(csv_text))

            # Find date column
            date_cols = ['Date', 'date', 'DATE', 'Timestamp', 'timestamp']
            date_col = None

            for col in date_cols:
                if col in df.columns:
                    date_col = col
                    break

            if date_col is None:
                return CollectionResult(
                    success=False,
                    symbol=symbol,
                    rows_collected=0,
                    error="No date column found",
                    source=self.source_name
                )

            # Parse dates
            df[date_col] = pd.to_datetime(df[date_col], format='mixed')
            df.set_index(date_col, inplace=True)

            # Standardize
            df = self.standardize_dataframe(df)

            # Save to file
            if save:
                csv_path = self.get_csv_path(symbol)
                df.to_csv(csv_path)

            # Cache
            if not hasattr(self, '_cached_data'):
                self._cached_data = {}
            self._cached_data[symbol] = df

            return CollectionResult(
                success=True,
                symbol=symbol,
                rows_collected=len(df),
                start_date=df.index[0],
                end_date=df.index[-1],
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


if __name__ == "__main__":
    """Test CSV collector"""
    from datetime import timedelta

    print("="*80)
    print("CSV COLLECTOR - TEST")
    print("="*80)

    # Example: Import the PPL data from earlier
    PPL_CSV = """Date,Price,Open,High,Low,Vol.,Change %
02/16/2026,232,237,237.6,231,1.11M,-1.81%
02/13/2026,236.27,234,238,228.97,12.91M,-0.38%
02-12-26,237.17,248,249,232.2,16.50M,-4.52%"""

    collector = CSVCollector(data_dir="data/csv")

    # Import from text
    result = collector.import_from_text('PPL', PPL_CSV, save=True)

    print(f"\nImport Result:")
    print(f"  Success: {result.success}")
    print(f"  Rows: {result.rows_collected}")
    print(f"  Error: {result.error}")

    # Retrieve
    if result.success:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        df = collector.get_prices_dataframe('PPL', start_date, end_date)

        print(f"\nRetrieved Data:")
        print(df.head())
        print(f"\nShape: {df.shape}")
