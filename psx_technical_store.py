"""
PSX Technical Indicator Storage
Persists computed technical indicators and snapshots for historical queries
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from psx_technical_agent import TechnicalSnapshot, TechnicalSignal, SignalType, SignalStrength, MultiTimeframeSnapshot


class TechnicalStore:
    """
    SQLite-based storage for technical indicators and snapshots
    """

    def __init__(self, db_path: str = "price_data/technicals.db"):
        """
        Initialize technical store

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

            # Individual indicator values per stock per day
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    value REAL NOT NULL,
                    signal_type TEXT,
                    strength TEXT,
                    description TEXT,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, date, indicator)
                )
            ''')

            # Aggregated snapshot per stock per day
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technical_snapshots (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    overall_bias TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bullish_count INTEGER,
                    bearish_count INTEGER,
                    neutral_count INTEGER,
                    indicator_values TEXT,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, date)
                )
            ''')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tech_symbol
                ON technical_indicators(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tech_date
                ON technical_indicators(date DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snap_symbol
                ON technical_snapshots(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snap_bias
                ON technical_snapshots(overall_bias)
            ''')

            # Multi-timeframe snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS multi_timeframe_snapshots (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    daily_bias TEXT NOT NULL,
                    weekly_bias TEXT NOT NULL,
                    confirmation_score REAL NOT NULL,
                    daily_confidence REAL,
                    weekly_confidence REAL,
                    aligned_signals TEXT,
                    conflicting_signals TEXT,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, date)
                )
            ''')

            # Create indexes for multi-timeframe data
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_mtf_symbol
                ON multi_timeframe_snapshots(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_mtf_confirmation
                ON multi_timeframe_snapshots(confirmation_score DESC)
            ''')

            conn.commit()

    def save_snapshot(self, snapshot: TechnicalSnapshot):
        """
        Save full snapshot with all indicators and signals

        Args:
            snapshot: TechnicalSnapshot object
        """
        computed_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count signal types
            bullish_count = sum(1 for s in snapshot.signals if s.signal_type in [SignalType.BULLISH, SignalType.OVERSOLD])
            bearish_count = sum(1 for s in snapshot.signals if s.signal_type in [SignalType.BEARISH, SignalType.OVERBOUGHT])
            neutral_count = sum(1 for s in snapshot.signals if s.signal_type == SignalType.NEUTRAL)

            # Save snapshot
            cursor.execute('''
                INSERT OR REPLACE INTO technical_snapshots
                (symbol, date, overall_bias, confidence, bullish_count, bearish_count,
                 neutral_count, indicator_values, computed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.symbol,
                snapshot.date,
                snapshot.overall_bias.value,
                snapshot.confidence,
                bullish_count,
                bearish_count,
                neutral_count,
                json.dumps(snapshot.indicator_values),
                computed_at
            ))

            # Save individual signals
            for signal in snapshot.signals:
                cursor.execute('''
                    INSERT OR REPLACE INTO technical_indicators
                    (symbol, date, indicator, value, signal_type, strength, description, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.symbol,
                    signal.date,
                    signal.indicator,
                    signal.value,
                    signal.signal_type.value,
                    signal.strength.value,
                    signal.description,
                    computed_at
                ))

            # Also save all indicator values (even those without signals)
            for indicator, value in snapshot.indicator_values.items():
                # Skip if already saved as a signal
                if not any(s.indicator == indicator for s in snapshot.signals):
                    cursor.execute('''
                        INSERT OR REPLACE INTO technical_indicators
                        (symbol, date, indicator, value, signal_type, strength, description, computed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        snapshot.symbol,
                        snapshot.date,
                        indicator,
                        value,
                        None,
                        None,
                        "",
                        computed_at
                    ))

            conn.commit()

    def get_snapshot(self, symbol: str, date: str = None) -> Optional[TechnicalSnapshot]:
        """
        Retrieve snapshot for a specific date

        Args:
            symbol: Stock symbol
            date: Date (ISO format). If None, gets latest.

        Returns:
            TechnicalSnapshot or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT date, overall_bias, confidence, indicator_values
                    FROM technical_snapshots
                    WHERE symbol = ? AND date = ?
                ''', (symbol, date))
            else:
                cursor.execute('''
                    SELECT date, overall_bias, confidence, indicator_values
                    FROM technical_snapshots
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 1
                ''', (symbol,))

            row = cursor.fetchone()
            if not row:
                return None

            snapshot_date, overall_bias, confidence, indicator_values_json = row

            # Get signals
            cursor.execute('''
                SELECT indicator, value, signal_type, strength, description
                FROM technical_indicators
                WHERE symbol = ? AND date = ? AND signal_type IS NOT NULL
            ''', (symbol, snapshot_date))

            signals = []
            for ind_row in cursor.fetchall():
                indicator, value, signal_type, strength, description = ind_row
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=snapshot_date,
                    indicator=indicator,
                    signal_type=SignalType(signal_type),
                    strength=SignalStrength(strength),
                    value=value,
                    description=description
                ))

            return TechnicalSnapshot(
                symbol=symbol,
                date=snapshot_date,
                signals=signals,
                overall_bias=SignalType(overall_bias),
                confidence=confidence,
                indicator_values=json.loads(indicator_values_json)
            )

    def get_indicator_history(self, symbol: str, indicator: str, days: int = 30) -> List[Tuple[str, float]]:
        """
        Get indicator values over time

        Args:
            symbol: Stock symbol
            indicator: Indicator name (e.g., "RSI", "MACD")
            days: Number of days to retrieve

        Returns:
            List of (date, value) tuples
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT date, value
                FROM technical_indicators
                WHERE symbol = ? AND indicator = ? AND date >= ?
                ORDER BY date ASC
            ''', (symbol, indicator, cutoff))

            return cursor.fetchall()

    def get_overbought_stocks(self, date: str = None) -> List[str]:
        """
        Get stocks with RSI > 70 on given date

        Args:
            date: Date (ISO format). If None, uses latest.

        Returns:
            List of stock symbols
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT DISTINCT symbol
                    FROM technical_indicators
                    WHERE indicator = 'RSI' AND value >= 70 AND date = ?
                    ORDER BY value DESC
                ''', (date,))
            else:
                # Get latest date first
                cursor.execute('SELECT MAX(date) FROM technical_indicators')
                latest_date = cursor.fetchone()[0]

                if not latest_date:
                    return []

                cursor.execute('''
                    SELECT DISTINCT symbol
                    FROM technical_indicators
                    WHERE indicator = 'RSI' AND value >= 70 AND date = ?
                    ORDER BY value DESC
                ''', (latest_date,))

            return [row[0] for row in cursor.fetchall()]

    def get_oversold_stocks(self, date: str = None) -> List[str]:
        """
        Get stocks with RSI < 30 on given date

        Args:
            date: Date (ISO format). If None, uses latest.

        Returns:
            List of stock symbols
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT DISTINCT symbol
                    FROM technical_indicators
                    WHERE indicator = 'RSI' AND value <= 30 AND date = ?
                    ORDER BY value ASC
                ''', (date,))
            else:
                # Get latest date first
                cursor.execute('SELECT MAX(date) FROM technical_indicators')
                latest_date = cursor.fetchone()[0]

                if not latest_date:
                    return []

                cursor.execute('''
                    SELECT DISTINCT symbol
                    FROM technical_indicators
                    WHERE indicator = 'RSI' AND value <= 30 AND date = ?
                    ORDER BY value ASC
                ''', (latest_date,))

            return [row[0] for row in cursor.fetchall()]

    def get_bullish_crossovers(self, days: int = 1) -> List[Tuple[str, str, str]]:
        """
        Get stocks with bullish crossovers in last N days

        Returns:
            List of (symbol, date, indicator) tuples
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, date, indicator
                FROM technical_indicators
                WHERE signal_type = 'Bullish' AND date >= ?
                ORDER BY date DESC
            ''', (cutoff,))

            return cursor.fetchall()

    def get_bearish_crossovers(self, days: int = 1) -> List[Tuple[str, str, str]]:
        """
        Get stocks with bearish crossovers in last N days

        Returns:
            List of (symbol, date, indicator) tuples
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, date, indicator
                FROM technical_indicators
                WHERE signal_type = 'Bearish' AND date >= ?
                ORDER BY date DESC
            ''', (cutoff,))

            return cursor.fetchall()

    def get_stats(self) -> Dict:
        """Get statistics about the technical store"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total snapshots
            cursor.execute('SELECT COUNT(*) FROM technical_snapshots')
            total_snapshots = cursor.fetchone()[0]

            # Number of symbols
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM technical_snapshots')
            num_symbols = cursor.fetchone()[0]

            # Date range
            cursor.execute('SELECT MIN(date), MAX(date) FROM technical_snapshots')
            date_range = cursor.fetchone()

            # Latest bias breakdown
            cursor.execute('''
                SELECT overall_bias, COUNT(*)
                FROM technical_snapshots
                WHERE date = (SELECT MAX(date) FROM technical_snapshots)
                GROUP BY overall_bias
            ''')
            bias_counts = dict(cursor.fetchall())

            return {
                'total_snapshots': total_snapshots,
                'num_symbols': num_symbols,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'bias_counts': bias_counts
            }

    # ===================================================================
    # MULTI-TIMEFRAME ANALYSIS STORAGE
    # ===================================================================

    def save_multi_timeframe_snapshot(self, snapshot: MultiTimeframeSnapshot):
        """
        Save multi-timeframe analysis snapshot

        Args:
            snapshot: MultiTimeframeSnapshot object with daily and weekly analysis
        """
        computed_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO multi_timeframe_snapshots
                (symbol, date, daily_bias, weekly_bias, confirmation_score,
                 daily_confidence, weekly_confidence, aligned_signals, conflicting_signals, computed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.symbol,
                snapshot.date,
                snapshot.daily.overall_bias.value,
                snapshot.weekly.overall_bias.value,
                snapshot.confirmation_score,
                snapshot.daily.confidence,
                snapshot.weekly.confidence,
                json.dumps(snapshot.aligned_signals),
                json.dumps(snapshot.conflicting_signals),
                computed_at
            ))

            conn.commit()

        # Also save the individual daily and weekly snapshots
        self.save_snapshot(snapshot.daily)
        self.save_snapshot(snapshot.weekly)

    def get_multi_timeframe_snapshot(self, symbol: str, date: str = None) -> Optional[MultiTimeframeSnapshot]:
        """
        Retrieve multi-timeframe snapshot for a specific date

        Args:
            symbol: Stock symbol
            date: Date (ISO format). If None, gets latest.

        Returns:
            MultiTimeframeSnapshot or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT date, daily_bias, weekly_bias, confirmation_score,
                           daily_confidence, weekly_confidence, aligned_signals, conflicting_signals
                    FROM multi_timeframe_snapshots
                    WHERE symbol = ? AND date = ?
                ''', (symbol, date))
            else:
                cursor.execute('''
                    SELECT date, daily_bias, weekly_bias, confirmation_score,
                           daily_confidence, weekly_confidence, aligned_signals, conflicting_signals
                    FROM multi_timeframe_snapshots
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 1
                ''', (symbol,))

            row = cursor.fetchone()
            if not row:
                return None

            (snapshot_date, daily_bias, weekly_bias, confirmation_score,
             daily_confidence, weekly_confidence, aligned_signals_json, conflicting_signals_json) = row

        # Get the full daily and weekly snapshots
        daily_snapshot = self.get_snapshot(symbol, snapshot_date)
        weekly_snapshot = self.get_snapshot(symbol, snapshot_date)

        if not daily_snapshot or not weekly_snapshot:
            return None

        return MultiTimeframeSnapshot(
            symbol=symbol,
            date=snapshot_date,
            daily=daily_snapshot,
            weekly=weekly_snapshot,
            confirmation_score=confirmation_score,
            aligned_signals=json.loads(aligned_signals_json),
            conflicting_signals=json.loads(conflicting_signals_json)
        )

    def get_high_confirmation_stocks(self, min_score: float = 0.8, date: str = None) -> List[Tuple[str, float, str, str]]:
        """
        Get stocks with high multi-timeframe confirmation scores

        Args:
            min_score: Minimum confirmation score (0.0-1.0)
            date: Specific date to query. If None, uses latest for each stock.

        Returns:
            List of tuples: (symbol, confirmation_score, daily_bias, weekly_bias)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if date:
                cursor.execute('''
                    SELECT symbol, confirmation_score, daily_bias, weekly_bias
                    FROM multi_timeframe_snapshots
                    WHERE date = ? AND confirmation_score >= ?
                    ORDER BY confirmation_score DESC
                ''', (date, min_score))
            else:
                # Get latest snapshot for each symbol with high confirmation
                cursor.execute('''
                    SELECT m.symbol, m.confirmation_score, m.daily_bias, m.weekly_bias
                    FROM multi_timeframe_snapshots m
                    INNER JOIN (
                        SELECT symbol, MAX(date) as max_date
                        FROM multi_timeframe_snapshots
                        GROUP BY symbol
                    ) latest ON m.symbol = latest.symbol AND m.date = latest.max_date
                    WHERE m.confirmation_score >= ?
                    ORDER BY m.confirmation_score DESC
                ''', (min_score,))

            return cursor.fetchall()


def main():
    """Example usage of TechnicalStore"""
    from psx_price_store import PSXPriceStore
    from psx_technical_agent import PSXTechnicalAgent

    print("="*80)
    print("PSX TECHNICAL STORE - DEMO")
    print("="*80)

    # Initialize components
    print("\nInitializing components...")
    price_store = PSXPriceStore()
    tech_agent = PSXTechnicalAgent(price_store)
    tech_store = TechnicalStore()

    # Test symbols
    test_symbols = ['HBL', 'LUCK', 'PSO']

    print(f"\nFetching price data...")
    price_store.bulk_update(test_symbols, days=250)

    print("\nComputing and storing technical indicators...")
    for symbol in test_symbols:
        snapshot = tech_agent.analyze_symbol(symbol)
        tech_store.save_snapshot(snapshot)
        print(f"  ✅ {symbol}: {len(snapshot.signals)} signals, bias={snapshot.overall_bias.value}")

    # Query stored data
    print("\n" + "="*80)
    print("QUERY EXAMPLES")
    print("="*80)

    # Stats
    stats = tech_store.get_stats()
    print(f"\nStore Statistics:")
    print(f"  Snapshots: {stats['total_snapshots']}")
    print(f"  Symbols: {stats['num_symbols']}")
    print(f"  Date range: {stats['earliest_date']} to {stats['latest_date']}")
    print(f"  Bias breakdown: {stats['bias_counts']}")

    # Overbought/oversold
    overbought = tech_store.get_overbought_stocks()
    oversold = tech_store.get_oversold_stocks()
    print(f"\nOverbought stocks (RSI > 70): {overbought if overbought else 'None'}")
    print(f"Oversold stocks (RSI < 30): {oversold if oversold else 'None'}")

    # Crossovers
    bullish = tech_store.get_bullish_crossovers(days=1)
    bearish = tech_store.get_bearish_crossovers(days=1)
    print(f"\nBullish crossovers (today): {len(bullish)}")
    for symbol, date, indicator in bullish:
        print(f"  {symbol}: {indicator}")
    print(f"\nBearish crossovers (today): {len(bearish)}")
    for symbol, date, indicator in bearish:
        print(f"  {symbol}: {indicator}")

    # RSI history
    if test_symbols:
        symbol = test_symbols[0]
        rsi_history = tech_store.get_indicator_history(symbol, 'RSI', days=30)
        if rsi_history:
            print(f"\nRSI History for {symbol} (last 5 days):")
            for date, value in rsi_history[-5:]:
                print(f"  {date}: {value:.1f}")

    print("\n" + "="*80)
    print("✅ Technical store demo complete")
    print("="*80)


if __name__ == "__main__":
    main()
