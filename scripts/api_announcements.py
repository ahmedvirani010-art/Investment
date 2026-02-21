"""
Bridge script: lists or syncs PSX announcements and outputs JSON to stdout for Next.js API.
Usage:
  python scripts/api_announcements.py list [days] [symbols] [tier]
  python scripts/api_announcements.py sync [days]
Defaults: list, days=7, all symbols, all tiers.
"""
import sys
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_announcement_storage import AnnouncementStorage, Announcement


def list_announcements(
    storage: AnnouncementStorage,
    days: int = 7,
    symbols: Optional[List[str]] = None,
    tier: Optional[int] = None,
) -> Dict:
    """Query storage and return JSON-serializable result. No limit - full report."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    announcements = storage.get_announcements_by_date_range(
        start_date, end_date, symbols=symbols, tier=tier
    )
    # Serialize with to_dict() (handles datetimes) - return all rows
    items = [a.to_dict() for a in announcements]
    return {
        "success": True,
        "announcements": items,
        "count": len(items),
    }


def sync_announcements(storage_path: str, days: int = 1) -> Dict:
    """Run scraper + classifier + save; return summary as JSON-serializable dict."""
    try:
        from psx_announcement_scraper_v2 import PSXAnnouncementScraperV2
        from psx_announcement_classifier import AnnouncementClassifier
    except ImportError:
        return {
            "success": False,
            "error": "Scraper or classifier not available (psx_announcement_scraper_v2, psx_announcement_classifier)",
        }

    scraper = PSXAnnouncementScraperV2(delay_seconds=2.0)
    classifier = AnnouncementClassifier()
    storage = AnnouncementStorage(db_path=storage_path)

    default_symbols = [
        "HBL", "OGDC", "LUCK", "PPL", "MCB", "UBL", "ENGRO", "MARI", "PSO", "HUBC"
    ]
    raw_announcements = scraper.scrape_announcements(
        symbols=default_symbols,
        days_back=days,
    )

    tier_counts = defaultdict(int)
    classified = []
    for raw in raw_announcements:
        try:
            ann = classifier.classify(raw)
            classified.append(ann)
            if ann.materiality_tier:
                tier_counts[ann.materiality_tier] += 1
        except Exception:
            pass

    new_count, duplicate_count = storage.save_announcements_bulk(classified)

    storage.record_scraping_stats(
        announcements_fetched=len(raw_announcements),
        announcements_new=new_count,
        announcements_duplicate=duplicate_count,
        symbols_covered=len(set(a.symbol for a in classified)),
        tier_counts=dict(tier_counts),
        error_count=0,
        notes=f"API sync for {days} day(s)",
    )

    return {
        "success": True,
        "fetched": len(raw_announcements),
        "new": new_count,
        "duplicates": duplicate_count,
        "tier_1": tier_counts.get(1, 0),
        "tier_2": tier_counts.get(2, 0),
        "tier_3": tier_counts.get(3, 0),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: list [days] [symbols] [tier] | sync [days]"}))
        sys.exit(1)

    action = (sys.argv[1] or "list").strip().lower()
    if action not in ("list", "sync"):
        print(json.dumps({"success": False, "error": f"Invalid action: {action}. Use list or sync."}))
        sys.exit(1)

    db_path = os.environ.get("ANNOUNCEMENT_DB_PATH", "announcement_data/announcements.db")
    # Resolve relative to project root (script's parent directory)
    if not os.path.isabs(db_path):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(root, db_path)

    if action == "list":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        symbols_arg = (sys.argv[3] or "").strip() if len(sys.argv) > 3 else ""
        tier_arg = (sys.argv[4] or "").strip() if len(sys.argv) > 4 else ""

        symbols = None
        if symbols_arg and symbols_arg.upper() not in ("ALL", "."):
            symbols = [s.strip().upper() for s in symbols_arg.split(",") if s.strip()]

        tier = None
        if tier_arg and tier_arg in ("1", "2", "3"):
            tier = int(tier_arg)

        storage = AnnouncementStorage(db_path=db_path)
        result = list_announcements(storage, days=days, symbols=symbols, tier=tier)
        print(json.dumps(result))
        sys.exit(0)

    # sync
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    result = sync_announcements(storage_path=db_path, days=days)
    print(json.dumps(result))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
