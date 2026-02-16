"""
PSX Sentiment Momentum Store
Persistent storage for sentiment data and momentum indicators
"""

import sqlite3
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os


@dataclass
class DailySentiment:
    """Aggregated sentiment for one symbol on one date."""
    symbol: str
    date: str
    avg_sentiment: float         # -1.0 to +1.0
    sentiment_label: str         # 'positive', 'negative', 'neutral'
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    max_sentiment: float
    min_sentiment: float
    confidence: float
    volume_score: float          # article_count * abs(avg_sentiment)
    recorded_at: str


@dataclass
class SentimentMomentum:
    """Momentum indicators for one symbol on one date."""
    symbol: str
    date: str
    momentum_7d: float           # Slope of 7-day regression
    momentum_14d: float          # Slope of 14-day regression
    momentum_30d: float          # Slope of 30-day regression
    trend: str                   # 'improving', 'declining', 'stable'
    strength: str                # 'strong', 'moderate', 'weak'
    reversal_signal: Optional[str]  # 'bullish_reversal', 'bearish_reversal'
    divergence_type: Optional[str]  # 'bullish_divergence', 'bearish_divergence'
    signal_type: str            # 'buy', 'sell', 'hold'
    computed_at: str


class SentimentMomentumStore:
    """
    Persistent storage for sentiment data and momentum indicators
    """

    def __init__(self, db_path: str = "sentiment_data/momentum.db"):
        """
        Initialize sentiment momentum store

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Create database tables and indexes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Daily aggregated sentiment per symbol
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_sentiment (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                avg_sentiment REAL NOT NULL,
                sentiment_label TEXT NOT NULL,
                article_count INTEGER NOT NULL,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                max_sentiment REAL,
                min_sentiment REAL,
                confidence REAL,
                volume_score REAL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        """)

        # Individual article sentiment (for drill-down)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT,
                sentiment_score REAL NOT NULL,
                sentiment_label TEXT NOT NULL,
                confidence REAL NOT NULL,
                recorded_at TEXT NOT NULL
            )
        """)

        # Sentiment momentum indicators (precomputed)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_momentum (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                momentum_7d REAL,
                momentum_14d REAL,
                momentum_30d REAL,
                trend TEXT,
                strength TEXT,
                reversal_signal TEXT,
                divergence_type TEXT,
                signal_type TEXT,
                computed_at TEXT NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_symbol
            ON daily_sentiment(symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_date
            ON daily_sentiment(date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date
            ON daily_sentiment(symbol, date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_symbol
            ON article_sentiment(symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_date
            ON article_sentiment(date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_momentum_symbol
            ON sentiment_momentum(symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_momentum_signal
            ON sentiment_momentum(signal_type)
        """)

        conn.commit()
        conn.close()

    def save_sentiment(self, symbol: str, date: str, sentiment_score: float,
                      sentiment_label: str, confidence: float,
                      title: str, source: str = None):
        """
        Save individual article sentiment

        Args:
            symbol: Stock symbol
            date: Date (YYYY-MM-DD)
            sentiment_score: Sentiment score (-1.0 to +1.0)
            sentiment_label: 'positive', 'negative', 'neutral'
            confidence: Confidence score (0.0 to 1.0)
            title: Article title
            source: News source
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        recorded_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO article_sentiment
            (symbol, date, title, source, sentiment_score, sentiment_label, confidence, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, date, title, source, sentiment_score, sentiment_label, confidence, recorded_at))

        conn.commit()
        conn.close()

    def aggregate_daily_sentiment(self, symbol: str, date: str) -> Optional[DailySentiment]:
        """
        Aggregate all articles for a symbol on a given date

        Args:
            symbol: Stock symbol
            date: Date (YYYY-MM-DD)

        Returns:
            DailySentiment object or None if no articles
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all articles for this symbol on this date
        cursor.execute("""
            SELECT sentiment_score, sentiment_label, confidence
            FROM article_sentiment
            WHERE symbol = ? AND date = ?
        """, (symbol, date))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # Calculate aggregates
        scores = [row[0] for row in rows]
        labels = [row[1] for row in rows]
        confidences = [row[2] for row in rows]

        avg_sentiment = sum(scores) / len(scores)
        article_count = len(rows)
        positive_count = labels.count('positive')
        negative_count = labels.count('negative')
        neutral_count = labels.count('neutral')
        max_sentiment = max(scores)
        min_sentiment = min(scores)
        avg_confidence = sum(confidences) / len(confidences)
        volume_score = article_count * abs(avg_sentiment)

        # Determine overall label
        if avg_sentiment >= 0.05:
            sentiment_label = 'positive'
        elif avg_sentiment <= -0.05:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'

        recorded_at = datetime.now().isoformat()

        daily_sentiment = DailySentiment(
            symbol=symbol,
            date=date,
            avg_sentiment=avg_sentiment,
            sentiment_label=sentiment_label,
            article_count=article_count,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            max_sentiment=max_sentiment,
            min_sentiment=min_sentiment,
            confidence=avg_confidence,
            volume_score=volume_score,
            recorded_at=recorded_at
        )

        # Save to database
        self._save_daily_sentiment(daily_sentiment)

        return daily_sentiment

    def _save_daily_sentiment(self, daily_sentiment: DailySentiment):
        """Save daily sentiment to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO daily_sentiment
            (symbol, date, avg_sentiment, sentiment_label, article_count,
             positive_count, negative_count, neutral_count,
             max_sentiment, min_sentiment, confidence, volume_score, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            daily_sentiment.symbol,
            daily_sentiment.date,
            daily_sentiment.avg_sentiment,
            daily_sentiment.sentiment_label,
            daily_sentiment.article_count,
            daily_sentiment.positive_count,
            daily_sentiment.negative_count,
            daily_sentiment.neutral_count,
            daily_sentiment.max_sentiment,
            daily_sentiment.min_sentiment,
            daily_sentiment.confidence,
            daily_sentiment.volume_score,
            daily_sentiment.recorded_at
        ))

        conn.commit()
        conn.close()

    def get_sentiment_history(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Get historical sentiment data

        Args:
            symbol: Stock symbol
            days: Number of days to retrieve

        Returns:
            DataFrame with sentiment history
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT date, avg_sentiment, sentiment_label, article_count,
                   positive_count, negative_count, neutral_count,
                   max_sentiment, min_sentiment, confidence, volume_score
            FROM daily_sentiment
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """

        df = pd.read_sql_query(query, conn, params=(symbol, days))
        conn.close()

        if not df.empty:
            # Sort by date ascending for time series analysis
            df = df.sort_values('date')
            df['date'] = pd.to_datetime(df['date'])

        return df

    def save_momentum(self, momentum: SentimentMomentum):
        """
        Save computed momentum indicators

        Args:
            momentum: SentimentMomentum object
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO sentiment_momentum
            (symbol, date, momentum_7d, momentum_14d, momentum_30d,
             trend, strength, reversal_signal, divergence_type, signal_type, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            momentum.symbol,
            momentum.date,
            momentum.momentum_7d,
            momentum.momentum_14d,
            momentum.momentum_30d,
            momentum.trend,
            momentum.strength,
            momentum.reversal_signal,
            momentum.divergence_type,
            momentum.signal_type,
            momentum.computed_at
        ))

        conn.commit()
        conn.close()

    def get_momentum(self, symbol: str, date: str = None) -> Optional[SentimentMomentum]:
        """
        Get momentum indicators for a symbol on a specific date

        Args:
            symbol: Stock symbol
            date: Date (YYYY-MM-DD), defaults to latest

        Returns:
            SentimentMomentum object or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if date:
            cursor.execute("""
                SELECT symbol, date, momentum_7d, momentum_14d, momentum_30d,
                       trend, strength, reversal_signal, divergence_type, signal_type, computed_at
                FROM sentiment_momentum
                WHERE symbol = ? AND date = ?
            """, (symbol, date))
        else:
            cursor.execute("""
                SELECT symbol, date, momentum_7d, momentum_14d, momentum_30d,
                       trend, strength, reversal_signal, divergence_type, signal_type, computed_at
                FROM sentiment_momentum
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """, (symbol,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return SentimentMomentum(
            symbol=row[0],
            date=row[1],
            momentum_7d=row[2],
            momentum_14d=row[3],
            momentum_30d=row[4],
            trend=row[5],
            strength=row[6],
            reversal_signal=row[7],
            divergence_type=row[8],
            signal_type=row[9],
            computed_at=row[10]
        )

    def get_symbols_by_signal(self, signal_type: str, date: str = None) -> List[str]:
        """
        Get symbols with specific signal (buy/sell/hold)

        Args:
            signal_type: 'buy', 'sell', or 'hold'
            date: Date (YYYY-MM-DD), defaults to latest

        Returns:
            List of stock symbols
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if date:
            cursor.execute("""
                SELECT symbol
                FROM sentiment_momentum
                WHERE signal_type = ? AND date = ?
                ORDER BY strength DESC
            """, (signal_type, date))
        else:
            # Get latest date first
            cursor.execute("SELECT MAX(date) FROM sentiment_momentum")
            latest_date = cursor.fetchone()[0]

            if latest_date:
                cursor.execute("""
                    SELECT symbol
                    FROM sentiment_momentum
                    WHERE signal_type = ? AND date = ?
                    ORDER BY strength DESC
                """, (signal_type, latest_date))

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_all_symbols(self) -> List[str]:
        """
        Get all symbols that have sentiment data

        Returns:
            List of stock symbols
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT symbol
            FROM daily_sentiment
            ORDER BY symbol
        """)

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_latest_date(self, symbol: str = None) -> Optional[str]:
        """
        Get the latest date with sentiment data

        Args:
            symbol: Optional symbol to filter by

        Returns:
            Latest date as string (YYYY-MM-DD) or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT MAX(date)
                FROM daily_sentiment
                WHERE symbol = ?
            """, (symbol,))
        else:
            cursor.execute("SELECT MAX(date) FROM daily_sentiment")

        row = cursor.fetchone()
        conn.close()

        return row[0] if row and row[0] else None

    def get_article_count(self, symbol: str = None, date: str = None) -> int:
        """
        Get count of articles

        Args:
            symbol: Optional symbol to filter by
            date: Optional date to filter by

        Returns:
            Number of articles
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if symbol and date:
            cursor.execute("""
                SELECT COUNT(*)
                FROM article_sentiment
                WHERE symbol = ? AND date = ?
            """, (symbol, date))
        elif symbol:
            cursor.execute("""
                SELECT COUNT(*)
                FROM article_sentiment
                WHERE symbol = ?
            """, (symbol,))
        elif date:
            cursor.execute("""
                SELECT COUNT(*)
                FROM article_sentiment
                WHERE date = ?
            """, (date,))
        else:
            cursor.execute("SELECT COUNT(*) FROM article_sentiment")

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else 0
