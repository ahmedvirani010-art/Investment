"""
PSX Announcement Storage

Database storage layer for PSX announcements
Uses SQLite with optimized schema for querying
"""

import sqlite3
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class Announcement:
    """Processed announcement with classification"""
    announcement_id: str
    symbol: str
    announcement_date: datetime

    # Classification
    category: Optional[str] = None
    subcategory: Optional[str] = None
    materiality_tier: Optional[int] = None  # 1 (critical), 2 (material), 3 (info)

    # Content
    title: str = ""
    description: str = ""
    attachment_url: Optional[str] = None
    source_url: str = ""
    source: str = "PSX"

    # Extracted Financial Data
    dividend_amount: Optional[float] = None
    dividend_type: Optional[str] = None  # cash, bonus, right
    eps: Optional[float] = None
    profit_amount: Optional[float] = None
    profit_change_pct: Optional[float] = None
    revenue: Optional[float] = None

    # Metadata
    fetched_date: Optional[datetime] = None
    is_processed: bool = False
    processing_notes: str = ""

    # Correlation
    related_anomalies: str = ""  # JSON list of anomaly IDs
    market_impact: Optional[str] = None  # positive, negative, neutral

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to string
        if isinstance(data.get('announcement_date'), datetime):
            data['announcement_date'] = data['announcement_date'].isoformat()
        if isinstance(data.get('fetched_date'), datetime):
            data['fetched_date'] = data['fetched_date'].isoformat()
        return data


class AnnouncementStorage:
    """Storage and retrieval of announcements in SQLite database"""

    def __init__(self, db_path: str = "announcement_data/announcements.db"):
        """
        Initialize storage

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Create directory if needed
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only create if there's a directory component
            os.makedirs(db_dir, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                announcement_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                announcement_date TEXT NOT NULL,

                -- Classification
                category TEXT,
                subcategory TEXT,
                materiality_tier INTEGER,

                -- Content
                title TEXT NOT NULL,
                description TEXT,
                attachment_url TEXT,
                source_url TEXT NOT NULL,
                source TEXT DEFAULT 'PSX',

                -- Extracted Financial Data
                dividend_amount REAL,
                dividend_type TEXT,
                eps REAL,
                profit_amount REAL,
                profit_change_pct REAL,
                revenue REAL,

                -- Metadata
                fetched_date TEXT,
                is_processed INTEGER DEFAULT 0,
                processing_notes TEXT,

                -- Correlation
                related_anomalies TEXT,  -- JSON array
                market_impact TEXT,

                -- Constraints
                UNIQUE(symbol, announcement_date, title)
            )
        """)

        # Create indexes for fast querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_announcements_symbol
            ON announcements(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_announcements_date
            ON announcements(announcement_date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_announcements_tier
            ON announcements(materiality_tier)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_announcements_category
            ON announcements(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_announcements_symbol_date
            ON announcements(symbol, announcement_date DESC)
        """)

        # Statistics table for tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_date TEXT NOT NULL,
                announcements_fetched INTEGER,
                announcements_new INTEGER,
                announcements_duplicate INTEGER,
                symbols_covered INTEGER,
                tier1_count INTEGER,
                tier2_count INTEGER,
                tier3_count INTEGER,
                error_count INTEGER,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Database initialized: {self.db_path}")

    def save_announcement(self, announcement: Announcement) -> bool:
        """
        Save announcement to database

        Args:
            announcement: Announcement object

        Returns:
            True if saved (new), False if duplicate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Convert datetime to ISO format
            announcement_date = announcement.announcement_date.isoformat() if isinstance(announcement.announcement_date, datetime) else announcement.announcement_date
            fetched_date = announcement.fetched_date.isoformat() if isinstance(announcement.fetched_date, datetime) else None

            cursor.execute("""
                INSERT INTO announcements (
                    announcement_id, symbol, announcement_date,
                    category, subcategory, materiality_tier,
                    title, description, attachment_url, source_url, source,
                    dividend_amount, dividend_type, eps, profit_amount,
                    profit_change_pct, revenue,
                    fetched_date, is_processed, processing_notes,
                    related_anomalies, market_impact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                announcement.announcement_id,
                announcement.symbol,
                announcement_date,
                announcement.category,
                announcement.subcategory,
                announcement.materiality_tier,
                announcement.title,
                announcement.description,
                announcement.attachment_url,
                announcement.source_url,
                announcement.source,
                announcement.dividend_amount,
                announcement.dividend_type,
                announcement.eps,
                announcement.profit_amount,
                announcement.profit_change_pct,
                announcement.revenue,
                fetched_date,
                1 if announcement.is_processed else 0,
                announcement.processing_notes,
                announcement.related_anomalies,
                announcement.market_impact
            ))

            conn.commit()
            logger.info(f"Saved new announcement: {announcement.announcement_id}")
            return True

        except sqlite3.IntegrityError:
            # Duplicate announcement
            logger.debug(f"Duplicate announcement: {announcement.announcement_id}")
            return False

        except Exception as e:
            logger.error(f"Error saving announcement: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def save_announcements_bulk(self, announcements: List[Announcement]) -> Tuple[int, int]:
        """
        Save multiple announcements in bulk

        Args:
            announcements: List of Announcement objects

        Returns:
            Tuple of (new_count, duplicate_count)
        """
        new_count = 0
        duplicate_count = 0

        for announcement in announcements:
            if self.save_announcement(announcement):
                new_count += 1
            else:
                duplicate_count += 1

        logger.info(f"Bulk save: {new_count} new, {duplicate_count} duplicates")
        return new_count, duplicate_count

    def get_announcements_by_symbol(
        self,
        symbol: str,
        days: int = 7,
        tier: Optional[int] = None
    ) -> List[Announcement]:
        """
        Get announcements for a specific symbol

        Args:
            symbol: Stock symbol
            days: Number of days to look back
            tier: Optional materiality tier filter (1, 2, or 3)

        Returns:
            List of Announcement objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        if tier is not None:
            cursor.execute("""
                SELECT * FROM announcements
                WHERE symbol = ?
                  AND announcement_date >= ?
                  AND materiality_tier = ?
                ORDER BY announcement_date DESC
            """, (symbol, cutoff_date, tier))
        else:
            cursor.execute("""
                SELECT * FROM announcements
                WHERE symbol = ?
                  AND announcement_date >= ?
                ORDER BY announcement_date DESC
            """, (symbol, cutoff_date))

        rows = cursor.fetchall()
        conn.close()

        announcements = [self._row_to_announcement(row) for row in rows]
        return announcements

    def get_announcements_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[List[str]] = None,
        tier: Optional[int] = None
    ) -> List[Announcement]:
        """
        Get announcements within date range

        Args:
            start_date: Start date
            end_date: End date
            symbols: Optional list of symbols to filter
            tier: Optional materiality tier filter

        Returns:
            List of Announcement objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        query = """
            SELECT * FROM announcements
            WHERE announcement_date BETWEEN ? AND ?
        """
        params = [start_iso, end_iso]

        if symbols:
            placeholders = ','.join('?' * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        if tier is not None:
            query += " AND materiality_tier = ?"
            params.append(tier)

        query += " ORDER BY announcement_date DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        announcements = [self._row_to_announcement(row) for row in rows]
        return announcements

    def get_critical_announcements(self, days: int = 1) -> List[Announcement]:
        """
        Get all critical (Tier 1) announcements from last N days

        Args:
            days: Number of days to look back

        Returns:
            List of critical Announcement objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT * FROM announcements
            WHERE announcement_date >= ?
              AND materiality_tier = 1
            ORDER BY announcement_date DESC
        """, (cutoff_date,))

        rows = cursor.fetchall()
        conn.close()

        announcements = [self._row_to_announcement(row) for row in rows]
        return announcements

    def get_announcement_by_id(self, announcement_id: str) -> Optional[Announcement]:
        """Get specific announcement by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM announcements
            WHERE announcement_id = ?
        """, (announcement_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_announcement(row)
        return None

    def update_announcement_classification(
        self,
        announcement_id: str,
        category: str,
        subcategory: Optional[str] = None,
        materiality_tier: int = 3
    ) -> bool:
        """
        Update announcement classification

        Args:
            announcement_id: Announcement ID
            category: Category
            subcategory: Subcategory
            materiality_tier: Tier (1-3)

        Returns:
            True if updated, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE announcements
                SET category = ?,
                    subcategory = ?,
                    materiality_tier = ?,
                    is_processed = 1
                WHERE announcement_id = ?
            """, (category, subcategory, materiality_tier, announcement_id))

            conn.commit()
            updated = cursor.rowcount > 0
            return updated

        except Exception as e:
            logger.error(f"Error updating announcement: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def update_announcement_financials(
        self,
        announcement_id: str,
        dividend_amount: Optional[float] = None,
        dividend_type: Optional[str] = None,
        eps: Optional[float] = None,
        profit_amount: Optional[float] = None,
        profit_change_pct: Optional[float] = None,
        revenue: Optional[float] = None
    ) -> bool:
        """Update extracted financial data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE announcements
                SET dividend_amount = ?,
                    dividend_type = ?,
                    eps = ?,
                    profit_amount = ?,
                    profit_change_pct = ?,
                    revenue = ?
                WHERE announcement_id = ?
            """, (
                dividend_amount, dividend_type, eps,
                profit_amount, profit_change_pct, revenue,
                announcement_id
            ))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating financials: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def get_statistics(self, days: int = 7) -> Dict:
        """
        Get announcement statistics

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Total announcements
        cursor.execute("""
            SELECT COUNT(*) FROM announcements
            WHERE announcement_date >= ?
        """, (cutoff_date,))
        total = cursor.fetchone()[0]

        # By tier
        cursor.execute("""
            SELECT materiality_tier, COUNT(*)
            FROM announcements
            WHERE announcement_date >= ?
            GROUP BY materiality_tier
        """, (cutoff_date,))
        tier_counts = dict(cursor.fetchall())

        # By category
        cursor.execute("""
            SELECT category, COUNT(*)
            FROM announcements
            WHERE announcement_date >= ?
            GROUP BY category
        """, (cutoff_date,))
        category_counts = dict(cursor.fetchall())

        # Unique symbols
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol)
            FROM announcements
            WHERE announcement_date >= ?
        """, (cutoff_date,))
        unique_symbols = cursor.fetchone()[0]

        conn.close()

        return {
            'total_announcements': total,
            'tier_1_critical': tier_counts.get(1, 0),
            'tier_2_material': tier_counts.get(2, 0),
            'tier_3_info': tier_counts.get(3, 0),
            'category_breakdown': category_counts,
            'unique_symbols': unique_symbols,
            'period_days': days
        }

    def _row_to_announcement(self, row: sqlite3.Row) -> Announcement:
        """Convert database row to Announcement object"""
        return Announcement(
            announcement_id=row['announcement_id'],
            symbol=row['symbol'],
            announcement_date=datetime.fromisoformat(row['announcement_date']),
            category=row['category'],
            subcategory=row['subcategory'],
            materiality_tier=row['materiality_tier'],
            title=row['title'],
            description=row['description'],
            attachment_url=row['attachment_url'],
            source_url=row['source_url'],
            source=row['source'],
            dividend_amount=row['dividend_amount'],
            dividend_type=row['dividend_type'],
            eps=row['eps'],
            profit_amount=row['profit_amount'],
            profit_change_pct=row['profit_change_pct'],
            revenue=row['revenue'],
            fetched_date=datetime.fromisoformat(row['fetched_date']) if row['fetched_date'] else None,
            is_processed=bool(row['is_processed']),
            processing_notes=row['processing_notes'] or "",
            related_anomalies=row['related_anomalies'] or "",
            market_impact=row['market_impact']
        )

    def record_scraping_stats(
        self,
        announcements_fetched: int,
        announcements_new: int,
        announcements_duplicate: int,
        symbols_covered: int,
        tier_counts: Dict[int, int],
        error_count: int = 0,
        notes: str = ""
    ):
        """Record scraping statistics for monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scraping_stats (
                scrape_date, announcements_fetched, announcements_new,
                announcements_duplicate, symbols_covered,
                tier1_count, tier2_count, tier3_count,
                error_count, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            announcements_fetched,
            announcements_new,
            announcements_duplicate,
            symbols_covered,
            tier_counts.get(1, 0),
            tier_counts.get(2, 0),
            tier_counts.get(3, 0),
            error_count,
            notes
        ))

        conn.commit()
        conn.close()


if __name__ == "__main__":
    # Test storage
    print("=" * 60)
    print("PSX ANNOUNCEMENT STORAGE - TEST MODE")
    print("=" * 60)

    storage = AnnouncementStorage("test_announcements.db")

    # Create test announcement
    test_announcement = Announcement(
        announcement_id="HBL_20260214_TEST",
        symbol="HBL",
        announcement_date=datetime.now(),
        title="Test Dividend Announcement",
        description="Final dividend of 50% announced",
        source_url="https://test.psx.com.pk",
        category="dividend",
        subcategory="final_cash",
        materiality_tier=1,
        dividend_amount=50.0,
        dividend_type="cash",
        fetched_date=datetime.now(),
        is_processed=True
    )

    # Save
    print("\n1. Saving test announcement...")
    saved = storage.save_announcement(test_announcement)
    print(f"   {'✅ Saved' if saved else '❌ Duplicate'}")

    # Retrieve
    print("\n2. Retrieving announcements for HBL...")
    announcements = storage.get_announcements_by_symbol("HBL", days=30)
    print(f"   Found {len(announcements)} announcements")

    for ann in announcements:
        print(f"   - {ann.title} (Tier {ann.materiality_tier})")

    # Statistics
    print("\n3. Getting statistics...")
    stats = storage.get_statistics(days=30)
    print(f"   Total: {stats['total_announcements']}")
    print(f"   Tier 1 (Critical): {stats['tier_1_critical']}")
    print(f"   Tier 2 (Material): {stats['tier_2_material']}")
    print(f"   Tier 3 (Info): {stats['tier_3_info']}")

    print("\n✅ Storage test complete")
