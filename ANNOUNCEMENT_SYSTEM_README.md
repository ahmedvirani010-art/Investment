# PSX Announcement Agent - User Guide

## Overview

The **PSX Announcement Agent** monitors official company announcements from the Pakistan Stock Exchange and integrates them with the anomaly detection and news correlation system.

### Why Announcements Matter

| Source | Delay | Authority | Coverage |
|--------|-------|-----------|----------|
| **PSX Announcements** | Minutes | Official | 100% |
| News Articles | Hours to Days | Secondary | Varies |

**Key Benefit**: Official announcements provide **authoritative** explanations for market anomalies before news articles are published.

---

## System Components

### 1. PSX Announcement Scraper (`psx_announcement_scraper.py`)

Fetches announcements from PSX website and other sources.

**Features**:
- Web scraping with BeautifulSoup
- Fallback to API if available
- Respectful rate limiting
- Duplicate detection

**Usage**:
```python
from psx_announcement_scraper import PSXAnnouncementScraper

scraper = PSXAnnouncementScraper(delay_seconds=2.0)

# Scrape last 7 days
announcements = scraper.scrape_announcements(days_back=7)

# Scrape specific symbols
announcements = scraper.scrape_announcements(
    days_back=7,
    symbols=['HBL', 'OGDC', 'LUCK']
)
```

### 2. Announcement Classifier (`psx_announcement_classifier.py`)

Categorizes announcements and assigns materiality scores.

**Categories**:
- `financial_results` - Quarterly/annual results
- `dividend` - Cash/bonus/rights
- `contract` - Major contracts
- `corporate_action` - M&A, splits
- `board_meeting` - Board meetings
- `material_info` - Price-sensitive info
- `production` - Production updates
- `agm_egm` - General meetings
- `regulatory` - Compliance
- `other` - Miscellaneous

**Materiality Tiers**:
- **Tier 1 (🔴 Critical)**: Immediate price impact expected
  - Financial results with >20% change
  - Dividends >30%
  - Major contracts ($100M+)
  - M&A activity
  - Oil/gas discoveries

- **Tier 2 (🟡 Material)**: Significant but less urgent
  - Interim dividends
  - Board meetings
  - Director dealings
  - Production updates

- **Tier 3 (🟢 Informational)**: Low/no impact
  - Book closures
  - Routine compliance
  - Administrative changes

**Usage**:
```python
from psx_announcement_classifier import AnnouncementClassifier

classifier = AnnouncementClassifier()

# Classify announcement
announcement = classifier.classify(raw_announcement)

print(f"Category: {announcement.category}")
print(f"Tier: {announcement.materiality_tier}")
print(f"Dividend: {announcement.dividend_amount}%")
```

### 3. Announcement Storage (`psx_announcement_storage.py`)

SQLite database for announcements.

**Schema**:
```sql
CREATE TABLE announcements (
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

    -- Correlation
    related_anomalies TEXT,
    market_impact TEXT
);
```

**Usage**:
```python
from psx_announcement_storage import AnnouncementStorage

storage = AnnouncementStorage("announcement_data/announcements.db")

# Save announcement
storage.save_announcement(announcement)

# Query announcements
announcements = storage.get_announcements_by_symbol("HBL", days=7)

# Get critical announcements
critical = storage.get_critical_announcements(days=1)

# Statistics
stats = storage.get_statistics(days=7)
print(f"Tier 1 (Critical): {stats['tier_1_critical']}")
```

### 4. Enhanced News-Anomaly Correlator (`psx_news_anomaly_correlator.py`)

Integrates announcements with news correlation.

**Priority Order**:
1. **Official PSX Announcements** (highest priority)
2. Company-specific news articles
3. Macro/sector news

**Correlation Scoring**:
```
Tier 1 Announcement + Same Day = 0.8 + 0.3 = 1.1 → capped at 1.0 (100%)
Tier 2 Announcement + Same Day = 0.6 + 0.3 = 0.9 (90%)
News Article + Same Day = 0.5 + 0.3 = 0.8 × 0.8 (penalty) = 0.64 (64%)
```

**Usage**:
```python
from psx_news_anomaly_correlator import NewsAnomalyCorrelator

correlator = NewsAnomalyCorrelator()

# Correlate single anomaly
correlation = correlator.correlate_anomaly(anomaly, lookback_days=3)

print(f"Score: {correlation.correlation_score*100:.0f}%")
print(f"Announcements: {len(correlation.related_announcements)}")
print(f"News: {len(correlation.related_news)}")
print(f"Explanation:\n{correlation.explanation}")

# Correlate all anomalies
correlations = correlator.correlate_all(anomalies_by_symbol)
correlator.print_correlation_report(correlations)
```

---

## Daily Operations

### Daily Sync (Run After Market Close)

```bash
# Sync last 24 hours
python3 run_announcement_sync.py --days 1

# Sync specific symbols
python3 run_announcement_sync.py --days 3 --symbols HBL,OGDC,LUCK

# Custom database path
python3 run_announcement_sync.py --days 1 --db-path custom/path.db
```

**Output Example**:
```
================================================================================
PSX ANNOUNCEMENT SYNC
================================================================================
Date: 2026-02-14 18:00:00
Lookback: 1 day(s)
Symbols: ALL
================================================================================

📥 STEP 1: Scraping announcements from PSX...
   ✅ Fetched: 45 announcements

🏷️  STEP 2: Classifying announcements...
   ✅ Classified: 45 announcements

💾 STEP 3: Saving to database...
   ✅ New: 38
   ℹ️  Duplicates: 7

================================================================================
SUMMARY
================================================================================

📊 By Materiality:
   🔴 CRITICAL (Tier 1):      5 announcements
   🟡 MATERIAL (Tier 2):      18 announcements
   🟢 INFORMATIONAL (Tier 3): 15 announcements

🔴 CRITICAL ANNOUNCEMENTS:
   ----------------------------------------------------------------------------
   HBL      - dividend            - Final Dividend 50% for year ended Dec 2025
            Dividend: 50.0% (cash)
   OGDC     - financial_results   - Quarterly Results Q1 2026
            Profit: +35.0%
   LUCK     - contract            - Major Contract Award $150M
   PPL      - production          - Oil Discovery in Sindh Province
   MCB      - dividend            - Bonus Shares 1:1 Announced

================================================================================
✅ SYNC COMPLETE
================================================================================
```

---

## Integration Example

### Full Workflow: Anomaly → Announcement → Explanation

```python
from psx_anomaly_agent import PSXAnomalyAgent
from psx_news_anomaly_correlator import NewsAnomalyCorrelator

# 1. Detect anomalies
anomaly_agent = PSXAnomalyAgent(lookback_days=60, z_threshold=2.5)
anomalies = anomaly_agent.generate_report(['HBL', 'OGDC', 'LUCK'])

# 2. Correlate with announcements + news
correlator = NewsAnomalyCorrelator()
correlations = correlator.correlate_all(anomalies, lookback_days=3)

# 3. Print integrated report
correlator.print_correlation_report(correlations)
```

**Output Example**:
```
================================================================================
PSX ANOMALY-ANNOUNCEMENT-NEWS CORRELATION REPORT
================================================================================

Total Anomalies: 5
Explained by Announcements (≥50%): 4
Explained by News/Announcements (≥50%): 5
Coverage: 100.0%
Announcement Coverage: 80.0%

================================================================================
📊 HBL - 1 Anomaly
================================================================================

🔴 HIGH - Volume Spike
   Date: 2026-02-14
   Volume +180% from average (15.2M vs 5.4M)
   Z-Score: 4.82

   🔗 Correlation Score: 95%

   🎯 PSX Announcements (1):
   ============================================================================
   1. 🔴 Final Cash Dividend Announcement for Year Ended December 31, 2025
      Category: dividend (final_cash) | Tier 1: CRITICAL
      Date: 2026-02-13
      💰 Dividend: 50.0% (cash)
      📊 EPS: Rs 78.5
      📈 Profit: +28.5% YoY
      🔗 https://dps.psx.com.pk/company/HBL/announcements/20260213

   📰 Related News (2 articles):
      1. HBL announces record 50% dividend, highest in banking...
         Source: Dawn Business | 2026-02-14 (same day) (positive: +0.82)
      2. Banking stocks rally as HBL sets new dividend benchmark...
         Source: Business Recorder | 2026-02-14 (same day) (positive: +0.74)

================================================================================
```

---

## Demo Mode

Test the system with sample data:

```bash
python3 demo_announcement_system.py
```

This creates:
- 7 sample announcements (various types)
- 5 sample anomalies (correlated with announcements)
- Demonstrates full workflow
- Shows before/after comparison

---

## Configuration

### Database Location

Default: `announcement_data/announcements.db`

Change via:
```python
storage = AnnouncementStorage("custom/path/announcements.db")
```

### Scraping Parameters

```python
scraper = PSXAnnouncementScraper(
    delay_seconds=2.0  # Delay between requests (be respectful)
)
```

### Correlation Parameters

```python
correlator = NewsAnomalyCorrelator()

correlation = correlator.correlate_anomaly(
    anomaly,
    lookback_days=3  # How far back to search
)
```

---

## Maintenance

### Database Cleanup

```python
from psx_announcement_storage import AnnouncementStorage

storage = AnnouncementStorage()

# Delete old announcements (older than 1 year)
import sqlite3
conn = sqlite3.connect(storage.db_path)
cursor = conn.cursor()

cursor.execute("""
    DELETE FROM announcements
    WHERE announcement_date < date('now', '-1 year')
""")

conn.commit()
conn.close()
```

### Performance Optimization

**Indexes** (already created):
- `idx_announcements_symbol`
- `idx_announcements_date`
- `idx_announcements_tier`
- `idx_announcements_category`
- `idx_announcements_symbol_date`

**Query Tips**:
```python
# Fast: Use indexes
announcements = storage.get_announcements_by_symbol("HBL", days=7)

# Slow: Full table scan
# SELECT * FROM announcements WHERE description LIKE '%dividend%'
```

---

## Troubleshooting

### No Announcements Fetched

**Possible Causes**:
1. PSX website unavailable
2. Network issues
3. Website structure changed
4. Rate limiting

**Solutions**:
```bash
# Check with verbose logging
python3 run_announcement_sync.py --days 1 --verbose

# Test scraper directly
python3 psx_announcement_scraper.py
```

### Classification Issues

**Problem**: Announcements misclassified

**Solution**: Update keyword lists in `psx_announcement_classifier.py`:
```python
CATEGORY_KEYWORDS = {
    'dividend': {
        'keywords': [
            'dividend', 'bonus', 'right issue',
            # Add more keywords here
        ],
        # ...
    }
}
```

### Database Locked

**Problem**: `sqlite3.OperationalError: database is locked`

**Cause**: Multiple processes accessing database

**Solution**:
```python
# Use separate database files per process, or
# Use WAL mode:

import sqlite3
conn = sqlite3.connect("announcements.db")
conn.execute("PRAGMA journal_mode=WAL")
```

---

## API Reference

### AnnouncementStorage Methods

```python
# Save
save_announcement(announcement) -> bool
save_announcements_bulk(announcements) -> Tuple[int, int]

# Query
get_announcements_by_symbol(symbol, days, tier=None) -> List[Announcement]
get_announcements_by_date_range(start, end, symbols, tier) -> List[Announcement]
get_critical_announcements(days) -> List[Announcement]
get_announcement_by_id(id) -> Optional[Announcement]

# Update
update_announcement_classification(id, category, subcategory, tier) -> bool
update_announcement_financials(id, **kwargs) -> bool

# Statistics
get_statistics(days) -> Dict
```

### NewsAnomalyCorrelator Methods

```python
# Correlate
correlate_anomaly(anomaly, lookback_days) -> NewsAnomalyCorrelation
correlate_all(anomalies_by_symbol, lookback_days) -> Dict

# Report
print_correlation_report(correlations)
```

---

## Future Enhancements

### Planned Features

1. **PDF Parsing**
   - Extract financial tables from PDF attachments
   - Parse detailed financial statements

2. **Real-Time Monitoring**
   - Continuous PSX monitoring during market hours
   - Instant alerts for critical announcements

3. **SECP Integration**
   - Fetch regulatory filings
   - Corporate governance reports

4. **Machine Learning**
   - Auto-categorization with ML
   - Sentiment analysis of announcement text
   - Impact prediction

5. **API Development**
   - REST API for announcements
   - WebSocket for real-time updates

---

## Support

For issues or questions:
- Check logs: `--verbose` flag
- Review plan: `PLAN_PSX_ANNOUNCEMENT_AGENT.md`
- Test with demo: `python3 demo_announcement_system.py`

---

**Last Updated**: 2026-02-14
**Version**: 1.0
**Status**: Production Ready
