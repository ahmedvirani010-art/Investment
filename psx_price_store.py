"""
PSX Price Data Store
Persistent OHLCV storage layer for all price-dependent agents
"""

import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path


class PSXPriceStore:
    """
    Persistent storage for OHLCV (Open, High, Low, Close, Volume) data

    Fetches from yfinance incrementally (only missing dates) and serves
    as the single source of truth for all price-dependent agents.
    """

    def __init__(self, db_path: str = "price_data/prices.db"):
        """
        Initialize price store

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

        # Create directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_prices (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    turnover REAL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, date)
                )
            ''')

            # Create indexes for fast queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_prices_symbol
                ON daily_prices(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_prices_date
                ON daily_prices(date DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_prices_symbol_date
                ON daily_prices(symbol, date DESC)
            ''')

            # Weekly prices table (computed from daily data)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_prices (
                    symbol TEXT NOT NULL,
                    week_start_date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    turnover REAL,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, week_start_date)
                )
            ''')

            # Create indexes for weekly data
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_weekly_symbol
                ON weekly_prices(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_weekly_date
                ON weekly_prices(week_start_date DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_weekly_symbol_date
                ON weekly_prices(symbol, week_start_date DESC)
            ''')

            conn.commit()

    def get_latest_date(self, symbol: str) -> Optional[str]:
        """
        Get the most recent date stored for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Latest date as ISO string (YYYY-MM-DD) or None if no data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(date) FROM daily_prices
                WHERE symbol = ?
            ''', (symbol,))

            result = cursor.fetchone()
            return result[0] if result[0] else None

    def get_prices(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """
        Get stored prices for a symbol

        Args:
            symbol: Stock symbol
            days: Number of days to retrieve

        Returns:
            DataFrame with OHLCV data, indexed by date
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)  # Buffer for weekends

        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT date, open, high, low, close, volume
                FROM daily_prices
                WHERE symbol = ? AND date >= ?
                ORDER BY date ASC
            '''

            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, start_date.strftime('%Y-%m-%d')),
                parse_dates=['date']
            )

            if df.empty:
                return pd.DataFrame()

            # Set date as index to match yfinance format
            df.set_index('date', inplace=True)

            # Capitalize column names to match yfinance format
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            return df

    def fetch_and_store(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """
        Fetch prices from yfinance (only missing dates) and store

        This is the primary method for updating the price store.
        It fetches only the dates not already in the database.

        Args:
            symbol: Stock symbol (without .KA suffix)
            days: Desired number of days of history

        Returns:
            DataFrame with complete OHLCV data for the requested period
        """
        # Get latest date in database
        latest_date_str = self.get_latest_date(symbol)

        # Determine fetch range
        end_date = datetime.now()

        if latest_date_str:
            # We have data, only fetch new dates
            latest_date = datetime.fromisoformat(latest_date_str)
            # Start from day after latest
            start_date = latest_date + timedelta(days=1)

            # If we're up to date, just return stored data
            if start_date >= end_date:
                return self.get_prices(symbol, days)
        else:
            # No data, fetch full range
            start_date = end_date - timedelta(days=days + 50)  # Extra buffer for first fetch

        # Fetch from yfinance (only if we need new data)
        if start_date < end_date:
            try:
                ticker_symbol = f"{symbol}.KA"
                ticker = yf.Ticker(ticker_symbol)

                print(f"  Fetching {symbol} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

                df = ticker.history(start=start_date, end=end_date)

                if not df.empty:
                    # Store fetched data
                    self._store_dataframe(symbol, df)
            except Exception as e:
                print(f"  Warning: Error fetching {symbol}: {str(e)}")

        # Return full requested range from database
        return self.get_prices(symbol, days)

    def _store_dataframe(self, symbol: str, df: pd.DataFrame):
        """
        Store a DataFrame of prices into the database

        Args:
            symbol: Stock symbol
            df: DataFrame from yfinance (indexed by date, with OHLCV columns)
        """
        if df.empty:
            return

        fetched_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for date, row in df.iterrows():
                # Calculate turnover
                turnover = row['Volume'] * row['Close']

                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO daily_prices
                        (symbol, date, open, high, low, close, volume, turnover, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        date.strftime('%Y-%m-%d'),
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        float(turnover),
                        fetched_at
                    ))
                except Exception as e:
                    print(f"  Warning: Error storing {symbol} on {date}: {str(e)}")

            conn.commit()

    def _compute_weekly_data(self, symbol: str) -> pd.DataFrame:
        """
        Compute weekly aggregated prices from daily data

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with weekly OHLCV data, indexed by week start date (Monday)
        """
        # Get all daily data for this symbol
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT date, open, high, low, close, volume
                FROM daily_prices
                WHERE symbol = ?
                ORDER BY date ASC
            '''
            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol,),
                parse_dates=['date']
            )

        if df.empty:
            return pd.DataFrame()

        # Set date as index
        df.set_index('date', inplace=True)

        # Resample to weekly (W-MON = week ending on Monday, labeled with Monday's date)
        weekly_df = df.resample('W-MON').agg({
            'open': 'first',   # First opening price of the week
            'high': 'max',     # Highest price of the week
            'low': 'min',      # Lowest price of the week
            'close': 'last',   # Last closing price of the week
            'volume': 'sum'    # Total volume for the week
        })

        # Remove rows with NaN (weeks with no trading data)
        weekly_df = weekly_df.dropna()

        # Calculate weekly turnover
        weekly_df['turnover'] = weekly_df['volume'] * weekly_df['close']

        return weekly_df

    def _store_weekly_dataframe(self, symbol: str, df: pd.DataFrame):
        """
        Store a DataFrame of weekly prices into the database

        Args:
            symbol: Stock symbol
            df: DataFrame with weekly OHLCV data indexed by week start date
        """
        if df.empty:
            return

        computed_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for date, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO weekly_prices
                        (symbol, week_start_date, open, high, low, close, volume, turnover, computed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        date.strftime('%Y-%m-%d'),
                        float(row['open']),
                        float(row['high']),
                        float(row['low']),
                        float(row['close']),
                        int(row['volume']),
                        float(row['turnover']),
                        computed_at
                    ))
                except Exception as e:
                    print(f"  Warning: Error storing weekly data for {symbol} on {date}: {str(e)}")

            conn.commit()

    def get_weekly_prices(self, symbol: str, weeks: int = 52) -> pd.DataFrame:
        """
        Get stored weekly prices for a symbol

        Args:
            symbol: Stock symbol
            weeks: Number of weeks to retrieve

        Returns:
            DataFrame with weekly OHLCV data, indexed by week start date
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT week_start_date, open, high, low, close, volume
                FROM weekly_prices
                WHERE symbol = ? AND week_start_date >= ?
                ORDER BY week_start_date ASC
            '''

            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, start_date.strftime('%Y-%m-%d')),
                parse_dates=['week_start_date']
            )

            if df.empty:
                return pd.DataFrame()

            # Set week_start_date as index
            df.set_index('week_start_date', inplace=True)

            # Capitalize column names to match daily prices format
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            return df

    def update_weekly_from_daily(self, symbols: List[str]):
        """
        Compute and store weekly aggregations for multiple symbols

        This should be called after bulk_update() to compute weekly data
        from the daily data that was just fetched.

        Args:
            symbols: List of stock symbols
        """
        print(f"\n{'='*80}")
        print(f"COMPUTING WEEKLY AGGREGATIONS")
        print(f"{'='*80}")
        print(f"Symbols: {len(symbols)}")
        print(f"{'='*80}\n")

        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Computing weekly data for {symbol}...")
            try:
                weekly_df = self._compute_weekly_data(symbol)
                if not weekly_df.empty:
                    self._store_weekly_dataframe(symbol, weekly_df)
                    print(f"  ✅ Stored {len(weekly_df)} weeks of data")
                else:
                    print(f"  ⚠️  No daily data available to aggregate")
            except Exception as e:
                print(f"  ❌ Error computing weekly data: {str(e)}")

        print(f"\n{'='*80}")
        print("✅ Weekly aggregation complete")
        print(f"{'='*80}\n")

    def bulk_update(self, symbols: List[str], days: int = 60):
        """
        Update prices for multiple symbols

        This is called at the start of the analysis pipeline to ensure
        all symbols have up-to-date price data.

        Args:
            symbols: List of stock symbols
            days: Number of days of history to maintain
        """
        print(f"\n{'='*80}")
        print(f"PRICE DATA STORE - BULK UPDATE")
        print(f"{'='*80}")
        print(f"Symbols: {len(symbols)}")
        print(f"Target history: {days} days")
        print(f"{'='*80}\n")

        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Updating {symbol}...")
            self.fetch_and_store(symbol, days)

        print(f"\n{'='*80}")
        print("✅ Price data update complete")
        print(f"{'='*80}\n")

    def get_stored_symbols(self) -> List[str]:
        """Get list of all symbols in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol')
            return [row[0] for row in cursor.fetchall()]

    def get_date_range(self, symbol: str) -> Optional[tuple]:
        """
        Get the date range available for a symbol

        Returns:
            Tuple of (earliest_date, latest_date) as ISO strings, or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MIN(date), MAX(date)
                FROM daily_prices
                WHERE symbol = ?
            ''', (symbol,))

            result = cursor.fetchone()
            if result[0] and result[1]:
                return (result[0], result[1])
            return None

    def get_stats(self) -> dict:
        """Get statistics about the price store"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total records
            cursor.execute('SELECT COUNT(*) FROM daily_prices')
            total_records = cursor.fetchone()[0]

            # Number of symbols
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM daily_prices')
            num_symbols = cursor.fetchone()[0]

            # Date range
            cursor.execute('SELECT MIN(date), MAX(date) FROM daily_prices')
            date_range = cursor.fetchone()

            return {
                'total_records': total_records,
                'num_symbols': num_symbols,
                'earliest_date': date_range[0],
                'latest_date': date_range[1]
            }


def main():
    """Example usage of PSXPriceStore"""

    # Initialize store
    print("Initializing PSX Price Store...")
    store = PSXPriceStore()

    # Get stats
    stats = store.get_stats()
    print(f"\nCurrent store statistics:")
    print(f"  Total records: {stats['total_records']:,}")
    print(f"  Symbols: {stats['num_symbols']}")
    if stats['earliest_date']:
        print(f"  Date range: {stats['earliest_date']} to {stats['latest_date']}")

    # Test with a few symbols
    test_symbols = ['HBL', 'LUCK', 'PSO']

    print(f"\nTesting with symbols: {test_symbols}")

    for symbol in test_symbols:
        print(f"\n{symbol}:")

        # Fetch and store
        df = store.fetch_and_store(symbol, days=60)

        if not df.empty:
            print(f"  Records: {len(df)}")
            print(f"  Date range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
            print(f"  Latest close: {df['Close'].iloc[-1]:.2f}")
        else:
            print(f"  No data available")

    # Show updated stats
    stats = store.get_stats()
    print(f"\nUpdated store statistics:")
    print(f"  Total records: {stats['total_records']:,}")
    print(f"  Symbols: {stats['num_symbols']}")
    print(f"  Date range: {stats['earliest_date']} to {stats['latest_date']}")


if __name__ == "__main__":
    main()
