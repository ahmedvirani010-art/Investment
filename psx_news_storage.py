"""
PSX News Storage Layer
Handles persistence of news articles using SQLite
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class NewsArticle:
    """News article data model"""
    article_id: str
    title: str
    url: str
    source: str
    published_date: datetime
    fetched_date: datetime
    language: str
    full_text: str
    summary: str
    author: Optional[str] = None
    categories: List[str] = field(default_factory=list)

    # Stock-related fields
    mentioned_symbols: List[str] = field(default_factory=list)
    primary_symbol: Optional[str] = None

    # Sentiment fields
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    sentiment_confidence: Optional[float] = None

    # Metadata
    relevance_score: float = 0.5
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None

    # Macro news fields
    is_macro_news: bool = False
    macro_category: Optional[str] = None
    affected_sectors: List[str] = field(default_factory=list)
    indirectly_affected_symbols: List[str] = field(default_factory=list)
    impact_type: Optional[str] = None
    price_change_mentioned: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to ISO format
        data['published_date'] = self.published_date.isoformat()
        data['fetched_date'] = self.fetched_date.isoformat()
        return data

    @staticmethod
    def from_dict(data: Dict) -> 'NewsArticle':
        """Create NewsArticle from dictionary"""
        # Convert ISO format back to datetime
        data['published_date'] = datetime.fromisoformat(data['published_date'])
        data['fetched_date'] = datetime.fromisoformat(data['fetched_date'])
        return NewsArticle(**data)


class NewsStorage:
    """SQLite-based storage for news articles"""

    def __init__(self, db_path: str = "news_data/news.db"):
        """Initialize storage with database path"""
        self.db_path = db_path

        # Create directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_articles (
                    article_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published_date TEXT NOT NULL,
                    fetched_date TEXT NOT NULL,
                    language TEXT,
                    full_text TEXT,
                    summary TEXT,
                    author TEXT,
                    categories TEXT,

                    mentioned_symbols TEXT,
                    primary_symbol TEXT,

                    sentiment_score REAL,
                    sentiment_label TEXT,
                    sentiment_confidence REAL,

                    relevance_score REAL,
                    is_duplicate INTEGER,
                    duplicate_of TEXT,

                    is_macro_news INTEGER,
                    macro_category TEXT,
                    affected_sectors TEXT,
                    indirectly_affected_symbols TEXT,
                    impact_type TEXT,
                    price_change_mentioned REAL,

                    UNIQUE(url, published_date)
                )
            ''')

            # Create indexes for fast queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_published_date
                ON news_articles(published_date DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_source
                ON news_articles(source)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_macro_category
                ON news_articles(macro_category)
            ''')

            # Full-text search table
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                    article_id UNINDEXED,
                    title,
                    full_text,
                    mentioned_symbols
                )
            ''')

            conn.commit()

    @staticmethod
    def generate_article_id(url: str, published_date: datetime) -> str:
        """Generate unique article ID from URL and publish date"""
        content = f"{url}{published_date.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def save_article(self, article: NewsArticle) -> bool:
        """Save article to database. Returns True if saved, False if duplicate"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO news_articles VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                ''', (
                    article.article_id,
                    article.title,
                    article.url,
                    article.source,
                    article.published_date.isoformat(),
                    article.fetched_date.isoformat(),
                    article.language,
                    article.full_text,
                    article.summary,
                    article.author,
                    json.dumps(article.categories),

                    json.dumps(article.mentioned_symbols),
                    article.primary_symbol,

                    article.sentiment_score,
                    article.sentiment_label,
                    article.sentiment_confidence,

                    article.relevance_score,
                    1 if article.is_duplicate else 0,
                    article.duplicate_of,

                    1 if article.is_macro_news else 0,
                    article.macro_category,
                    json.dumps(article.affected_sectors),
                    json.dumps(article.indirectly_affected_symbols),
                    article.impact_type,
                    article.price_change_mentioned
                ))

                # Add to FTS index
                cursor.execute('''
                    INSERT INTO news_fts VALUES (?, ?, ?, ?)
                ''', (
                    article.article_id,
                    article.title,
                    article.full_text,
                    json.dumps(article.mentioned_symbols)
                ))

                conn.commit()
                return True

        except sqlite3.IntegrityError:
            # Duplicate article
            return False

    def get_article(self, article_id: str) -> Optional[NewsArticle]:
        """Get article by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM news_articles WHERE article_id = ?', (article_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_article(row)
            return None

    def get_recent_articles(self, hours: int = 24, limit: int = 1000) -> List[NewsArticle]:
        """Get articles from last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news_articles
                WHERE published_date >= ?
                ORDER BY published_date DESC
                LIMIT ?
            ''', (cutoff.isoformat(), limit))

            return [self._row_to_article(row) for row in cursor.fetchall()]

    def get_articles_by_symbol(self, symbol: str, days: int = 7) -> List[NewsArticle]:
        """Get articles mentioning a specific symbol"""
        cutoff = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news_articles
                WHERE (mentioned_symbols LIKE ? OR primary_symbol = ?)
                AND published_date >= ?
                ORDER BY published_date DESC
            ''', (f'%"{symbol}"%', symbol, cutoff.isoformat()))

            return [self._row_to_article(row) for row in cursor.fetchall()]

    def get_macro_news(self, category: Optional[str] = None, hours: int = 48) -> List[NewsArticle]:
        """Get macro economic news"""
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute('''
                    SELECT * FROM news_articles
                    WHERE is_macro_news = 1
                    AND macro_category = ?
                    AND published_date >= ?
                    ORDER BY published_date DESC
                ''', (category, cutoff.isoformat()))
            else:
                cursor.execute('''
                    SELECT * FROM news_articles
                    WHERE is_macro_news = 1
                    AND published_date >= ?
                    ORDER BY published_date DESC
                ''', (cutoff.isoformat(),))

            return [self._row_to_article(row) for row in cursor.fetchall()]

    def search_articles(self, query: str, limit: int = 100) -> List[NewsArticle]:
        """Full-text search for articles"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.* FROM news_articles a
                JOIN news_fts f ON a.article_id = f.article_id
                WHERE news_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            ''', (query, limit))

            return [self._row_to_article(row) for row in cursor.fetchall()]

    def get_articles_count(self) -> int:
        """Get total number of articles"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM news_articles')
            return cursor.fetchone()[0]

    def _row_to_article(self, row) -> NewsArticle:
        """Convert database row to NewsArticle object"""
        return NewsArticle(
            article_id=row[0],
            title=row[1],
            url=row[2],
            source=row[3],
            published_date=datetime.fromisoformat(row[4]),
            fetched_date=datetime.fromisoformat(row[5]),
            language=row[6],
            full_text=row[7],
            summary=row[8],
            author=row[9],
            categories=json.loads(row[10]) if row[10] else [],

            mentioned_symbols=json.loads(row[11]) if row[11] else [],
            primary_symbol=row[12],

            sentiment_score=row[13],
            sentiment_label=row[14],
            sentiment_confidence=row[15],

            relevance_score=row[16] or 0.5,
            is_duplicate=bool(row[17]),
            duplicate_of=row[18],

            is_macro_news=bool(row[19]),
            macro_category=row[20],
            affected_sectors=json.loads(row[21]) if row[21] else [],
            indirectly_affected_symbols=json.loads(row[22]) if row[22] else [],
            impact_type=row[23],
            price_change_mentioned=row[24]
        )

    def cleanup_old_articles(self, days: int = 90):
        """Archive articles older than N days"""
        cutoff = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM news_articles
                WHERE published_date < ?
            ''', (cutoff.isoformat(),))

            deleted = cursor.rowcount
            conn.commit()

        return deleted
