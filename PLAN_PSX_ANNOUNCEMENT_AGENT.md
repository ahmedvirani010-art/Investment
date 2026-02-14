# PSX Announcement Agent - Implementation Plan

## 🎯 Mission

Build an automated agent that monitors **official company announcements** from the Pakistan Stock Exchange, categorizes them by materiality, and integrates with the news-anomaly correlation system to provide **authoritative** explanations for market moves.

---

## 🔍 Why This Matters

### Current Gap
- **News Agent**: Fetches RSS feeds from media outlets (Dawn, Business Recorder)
  - ❌ Secondary sources with delay (hours to days)
  - ❌ May miss important announcements
  - ❌ Subject to journalistic interpretation

- **Announcement Agent**: Direct from PSX/SECP
  - ✅ **Primary source** - no delay
  - ✅ **Official** - no interpretation needed
  - ✅ **Complete** - catches everything material
  - ✅ **Structured** - easier to parse and categorize

### Impact
- **Better Correlation**: Corporate actions directly explain anomalies
- **No Lag**: Announcements before news articles
- **Higher Confidence**: Official source > media report
- **Material Events**: Dividend, earnings, rights issues are 100% material

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   PSX ANNOUNCEMENT AGENT                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ PSX Website  │   │    SECP      │   │  Company IR  │
│ Announcements│   │   Filings    │   │   Websites   │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────┬───────┴────────┬─────────┘
                  ▼                ▼
          ┌────────────────────────────┐
          │   Web Scraper/API Client   │
          │   - Beautiful Soup         │
          │   - Selenium (if needed)   │
          │   - PSX API (if available) │
          └─────────────┬──────────────┘
                        ▼
          ┌────────────────────────────┐
          │  Announcement Parser       │
          │  - Extract metadata        │
          │  - Categorize type         │
          │  - Extract key data        │
          └─────────────┬──────────────┘
                        ▼
          ┌────────────────────────────┐
          │  Materiality Scorer        │
          │  - Tier 1: Critical        │
          │  - Tier 2: Material        │
          │  - Tier 3: Informational   │
          └─────────────┬──────────────┘
                        ▼
          ┌────────────────────────────┐
          │  Database Storage          │
          │  (announcements table)     │
          └─────────────┬──────────────┘
                        ▼
          ┌────────────────────────────┐
          │  Integration Layer         │
          │  - News correlator         │
          │  - Anomaly detector        │
          │  - Alert system            │
          └────────────────────────────┘
```

---

## 🗂️ Data Sources

### Primary: PSX Official Website

**URL**: https://dps.psx.com.pk/company-announcements

**Announcement Types**:
1. **Financial Results** (Quarterly, Annual, Half-yearly)
2. **Dividend Announcements** (Cash, Bonus, Right)
3. **Board Meetings** (Notices, Outcomes)
4. **Directors' Dealings**
5. **Material Information** (Contracts, Projects)
6. **Corporate Actions** (Splits, M&A)
7. **Production Updates** (Monthly, Quarterly)
8. **AGM/EGM Notices**
9. **Book Closure**
10. **Price Sensitive Information**

**Scraping Approach**:
```python
# Option 1: Direct scraping (if no API)
import requests
from bs4 import BeautifulSoup

url = "https://dps.psx.com.pk/company-announcements"
# Parse table, extract announcements

# Option 2: Check for PSX API/RSS
# PSX may have JSON API for announcements

# Option 3: Selenium for dynamic content
from selenium import webdriver
# If page loads announcements via JavaScript
```

### Secondary: SECP

**URL**: https://www.secp.gov.pk/

**Filings**:
- Regulatory filings
- Corporate governance reports
- Major shareholding changes
- Related party transactions

### Tertiary: Company IR Pages

**Selected high-cap stocks only**:
- HBL, UBL, MCB (Banking)
- OGDC, PPL, PSO (Energy)
- LUCK, DGKC (Cement)
- ENGRO, FFC (Fertilizer/Chemical)

---

## 📋 Announcement Categories & Materiality

### TIER 1: CRITICAL (Immediate Price Impact)

**Always Material - Auto-Alert**

| Category | Examples | Expected Impact | Priority |
|----------|----------|-----------------|----------|
| **Financial Results** | Q1 earnings, Annual profit | ±5-20% | 🔴 CRITICAL |
| **Dividend Declaration** | Final dividend 40% | +3-10% | 🔴 CRITICAL |
| **Bonus/Rights** | 1:1 bonus, 1:2 rights | ±5-15% | 🔴 CRITICAL |
| **Major Contracts** | $100M+ contract won | +5-20% | 🔴 CRITICAL |
| **Production Targets** | Oil discovery, capacity up 50% | +10-30% | 🔴 CRITICAL |
| **M&A Activity** | Merger, acquisition announced | ±10-40% | 🔴 CRITICAL |
| **CEO/Chairman Change** | Sudden resignation | ±3-10% | 🔴 CRITICAL |
| **Credit Rating** | Upgrade/downgrade | ±5-15% | 🔴 CRITICAL |
| **Default/Penalty** | Regulatory penalty, default | -10-30% | 🔴 CRITICAL |

### TIER 2: MATERIAL (Significant but Less Urgent)

**Important - Monitor**

| Category | Examples | Expected Impact | Priority |
|----------|----------|-----------------|----------|
| **Interim Dividend** | Interim dividend 15% | +1-3% | 🟡 MATERIAL |
| **Board Meetings** | Meeting scheduled for results | Anticipation | 🟡 MATERIAL |
| **Director Dealings** | Director buys/sells shares | ±1-3% | 🟡 MATERIAL |
| **Small Contracts** | $10-50M contract | +1-5% | 🟡 MATERIAL |
| **Production Updates** | Monthly production data | ±1-3% | 🟡 MATERIAL |
| **Capex Plans** | $50M expansion plan | +2-5% | 🟡 MATERIAL |
| **AGM Notice** | Annual meeting scheduled | Minimal | 🟡 MATERIAL |

### TIER 3: INFORMATIONAL (Low/No Impact)

**Track but Don't Alert**

| Category | Examples | Expected Impact | Priority |
|----------|----------|-----------------|----------|
| **Book Closure** | Books close for dividend | Priced in | 🟢 INFO |
| **Routine Updates** | Periodic compliance | None | 🟢 INFO |
| **Minor Changes** | Registered office address | None | 🟢 INFO |

---

## 🔧 Implementation Phases

### Phase 1: Core Scraping & Storage (Week 1)

**Deliverables**:
```python
# psx_announcement_scraper.py
class PSXAnnouncementScraper:
    def scrape_announcements(self, days_back=7):
        """Scrape PSX announcements from last N days"""
        pass

    def parse_announcement(self, raw_html):
        """Parse individual announcement"""
        pass

    def extract_metadata(self, announcement):
        """Extract symbol, date, type, title"""
        pass

# psx_announcement_storage.py
class AnnouncementStorage:
    def save_announcement(self, announcement):
        """Save to announcements table"""
        pass

    def get_announcements_by_symbol(self, symbol, days):
        """Query announcements for stock"""
        pass
```

**Database Schema**:
```sql
CREATE TABLE announcements (
    announcement_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    announcement_date TIMESTAMP NOT NULL,

    -- Classification
    category TEXT,  -- financial_results, dividend, etc.
    subcategory TEXT,  -- quarterly, annual, cash, bonus
    materiality_tier INTEGER,  -- 1 (critical), 2 (material), 3 (info)

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    attachment_url TEXT,
    source_url TEXT NOT NULL,

    -- Extracted Data
    dividend_amount REAL,
    dividend_type TEXT,  -- cash, bonus, right
    eps REAL,  -- Earnings per share
    profit_amount REAL,
    profit_change_pct REAL,

    -- Metadata
    fetched_date TIMESTAMP,
    is_processed BOOLEAN DEFAULT 0,

    UNIQUE(symbol, announcement_date, title)
);

CREATE INDEX idx_announcements_symbol ON announcements(symbol);
CREATE INDEX idx_announcements_date ON announcements(announcement_date DESC);
CREATE INDEX idx_announcements_tier ON announcements(materiality_tier);
```

### Phase 2: Categorization & Parsing (Week 2)

**Deliverables**:
```python
# psx_announcement_classifier.py
class AnnouncementClassifier:
    def classify_announcement(self, title, description):
        """Categorize announcement type"""
        categories = {
            'financial_results': [
                'quarterly', 'annual', 'half yearly',
                'profit', 'loss', 'earnings', 'results'
            ],
            'dividend': [
                'dividend', 'bonus', 'right issue'
            ],
            'contract': [
                'contract', 'award', 'project', 'agreement'
            ],
            # ... more categories
        }
        pass

    def extract_financial_data(self, announcement):
        """Extract EPS, profit, dividend from text/PDF"""
        # Use regex, NLP, or PDF parsing
        pass

    def score_materiality(self, announcement):
        """Assign tier 1/2/3 based on type and impact"""
        pass
```

**Materiality Scoring Logic**:
```python
def score_materiality(announcement):
    # Tier 1: Critical
    if announcement.category in ['financial_results', 'dividend', 'major_contract']:
        if announcement.profit_change_pct and abs(announcement.profit_change_pct) > 20:
            return 1  # Critical
        if announcement.dividend_amount and announcement.dividend_amount > 30:
            return 1  # Critical (>30% dividend)
        return 2  # Material but not critical

    # Tier 2: Material
    if announcement.category in ['board_meeting', 'production', 'director_dealing']:
        return 2

    # Tier 3: Informational
    return 3
```

### Phase 3: Integration with News-Anomaly System (Week 3)

**Enhanced Correlator**:
```python
# psx_news_anomaly_correlator.py (enhanced)
class NewsAnomalyCorrelator:
    def __init__(self, news_storage, announcement_storage):
        self.news_storage = news_storage
        self.announcement_storage = announcement_storage

    def correlate_anomaly(self, anomaly, lookback_days=3):
        """Enhanced with announcements"""

        # 1. Check official announcements FIRST
        announcements = self.announcement_storage.get_announcements_by_symbol(
            anomaly.symbol,
            days=lookback_days
        )

        # 2. Check news articles
        news = self.news_storage.get_articles_by_symbol(
            anomaly.symbol,
            days=lookback_days
        )

        # 3. PRIORITIZE announcements over news
        scored_items = []

        # Announcements get higher base score
        for ann in announcements:
            if ann.materiality_tier == 1:  # Critical
                base_score = 0.8
            elif ann.materiality_tier == 2:  # Material
                base_score = 0.6
            else:
                base_score = 0.3

            # Time proximity
            time_score = self._time_score(anomaly.date, ann.announcement_date)

            total_score = min(base_score + time_score, 1.0)
            scored_items.append((total_score, 'announcement', ann))

        # News gets lower base score (secondary source)
        for article in news:
            if self._is_news_material(article, anomaly):
                score = self._calculate_relevance_score(anomaly, article, is_direct=True)
                scored_items.append((score * 0.8, 'news', article))  # 20% penalty for being secondary

        # Sort by score
        scored_items.sort(reverse=True, key=lambda x: x[0])

        # Generate explanation prioritizing official announcements
        return self._generate_explanation_with_announcements(
            anomaly, scored_items
        )
```

**Explanation Enhancement**:
```python
def _generate_explanation_with_announcements(self, anomaly, scored_items):
    """Generate explanation with announcements prioritized"""

    if not scored_items:
        return "No announcements or news found."

    best_score, source_type, item = scored_items[0]

    if source_type == 'announcement' and best_score >= 0.7:
        # Official explanation
        return f"""
🎯 OFFICIAL ANNOUNCEMENT (PSX):
   📋 {item.title}
   📅 {item.announcement_date.strftime('%Y-%m-%d')}
   🏷️  Category: {item.category}
   ⭐ Materiality: Tier {item.materiality_tier}

   💡 Action: Official catalyst identified - review fundamentals
        """
    elif source_type == 'news':
        # Secondary source
        return f"""
📰 News Report (verify with PSX announcements):
   {item.title}

   ⚠️  Note: Secondary source - check PSX for official announcement
        """
```

### Phase 4: Alert System (Week 4)

**Real-Time Monitoring**:
```python
# psx_announcement_monitor.py
class AnnouncementMonitor:
    def monitor_continuous(self, check_interval=300):  # 5 minutes
        """Continuous monitoring for new announcements"""

        while True:
            new_announcements = self.scraper.scrape_latest()

            for announcement in new_announcements:
                # Save to DB
                self.storage.save_announcement(announcement)

                # Check materiality
                if announcement.materiality_tier == 1:  # Critical
                    self.send_alert(announcement)

                # Check if it explains recent anomaly
                recent_anomalies = self.get_recent_anomalies(
                    announcement.symbol,
                    hours=24
                )

                if recent_anomalies:
                    self.send_anomaly_explanation_alert(
                        announcement,
                        recent_anomalies
                    )

            time.sleep(check_interval)

    def send_alert(self, announcement):
        """Send notification for critical announcement"""
        # Email, Slack, SMS, etc.
        pass
```

**Alert Channels**:
```python
# psx_alert_system.py
class AlertSystem:
    def __init__(self, channels=['email', 'console']):
        self.channels = channels

    def alert_critical_announcement(self, announcement):
        message = f"""
🔴 CRITICAL PSX ANNOUNCEMENT

Symbol: {announcement.symbol}
Category: {announcement.category}
Title: {announcement.title}

Date: {announcement.announcement_date}
Source: {announcement.source_url}

Take action: Review and trade
        """

        if 'email' in self.channels:
            self.send_email(message)

        if 'slack' in self.channels:
            self.send_slack(message)

        if 'console' in self.channels:
            print(message)
```

---

## 📊 Data Models

### Announcement Object
```python
@dataclass
class Announcement:
    """PSX company announcement"""
    announcement_id: str
    symbol: str
    announcement_date: datetime

    # Classification
    category: str  # financial_results, dividend, contract, etc.
    subcategory: Optional[str]  # quarterly, cash, major, etc.
    materiality_tier: int  # 1 (critical), 2 (material), 3 (info)

    # Content
    title: str
    description: str
    attachment_url: Optional[str]
    source_url: str

    # Extracted Financial Data
    dividend_amount: Optional[float]
    dividend_type: Optional[str]  # cash, bonus, right
    eps: Optional[float]
    profit_amount: Optional[float]
    profit_change_pct: Optional[float]
    revenue: Optional[float]

    # Metadata
    fetched_date: datetime
    is_processed: bool = False

    # Correlation
    related_anomalies: List[str] = field(default_factory=list)
    market_impact: Optional[str] = None  # positive, negative, neutral
```

---

## 🔍 Example Workflows

### Workflow 1: Daily Batch Processing
```bash
# Run at 6 PM daily (after market close)
python3 run_announcement_sync.py --days 1

# Output:
# ====================================
# PSX ANNOUNCEMENT SYNC
# ====================================
# Fetched: 45 announcements (last 24 hours)
# New: 38
# Duplicates: 7
#
# CRITICAL (Tier 1): 5 announcements
#   HBL - Final Dividend 50% (Cash)
#   OGDC - Quarterly Results (Profit +35%)
#   LUCK - Contract Award $150M
#   PPL - Oil Discovery in Sindh
#   MCB - Bonus Shares 1:1
#
# MATERIAL (Tier 2): 18 announcements
# INFORMATIONAL (Tier 3): 15 announcements
# ====================================
```

### Workflow 2: Real-Time Monitoring
```bash
# Run continuously during market hours
python3 run_announcement_monitor.py

# Output (real-time):
# [10:05] 🔴 CRITICAL: HBL - Dividend Announcement (50% cash)
# [10:05] 📊 Checking recent anomalies for HBL...
# [10:05] ✅ Found anomaly: HBL Volume Spike (+180%) at 10:03
# [10:05] 🔗 Correlation: 95% - Announcement explains anomaly
# [10:05] 📧 Alert sent to subscribers
```

### Workflow 3: Integrated Analysis
```bash
# Run full integrated analysis with announcements
python3 run_integrated_analysis.py --include-announcements

# Output:
# ====================================
# PSX INTEGRATED ANALYSIS
# ====================================
#
# 📋 STEP 1: Stock Selection
# ✅ Selected 30 liquid stocks
#
# 📰 STEP 2: News Collection
# ✅ Fetched 28 news articles
#
# 📋 STEP 3: Announcement Sync
# ✅ Fetched 12 PSX announcements (last 48h)
#    - Tier 1 (Critical): 3
#    - Tier 2 (Material): 6
#    - Tier 3 (Info): 3
#
# 🔍 STEP 4: Anomaly Detection
# ✅ Detected 5 anomalies
#
# 🔗 STEP 5: Correlation (Announcements + News)
# ====================================
#
# HBL - Volume Spike +180%
# 🎯 OFFICIAL ANNOUNCEMENT (PSX): 95% correlation
#    📋 Final Dividend 50% Announced
#    📅 2026-02-14
#    🏷️  Category: dividend (cash)
#    ⭐ Materiality: Tier 1 (Critical)
#
#    Supporting news:
#    📰 "HBL announces record dividend" (Dawn Business)
#
#    💡 Action: Official catalyst - dividend creates buying pressure
# ====================================
```

---

## 🎯 Key Metrics & KPIs

### Data Quality
- **Announcement Coverage**: Target 100% of PSX announcements
- **Latency**: <5 minutes from PSX posting to database
- **Classification Accuracy**: >95% correct category
- **Materiality Scoring**: >90% agreement with market impact

### Correlation Performance
- **Explained Anomalies**: Target 85%+ with announcements included
- **False Positives**: <5% (non-material announcements flagged as critical)
- **Alert Accuracy**: >90% of critical alerts lead to price moves

### System Reliability
- **Uptime**: 99%+ during market hours
- **Scraping Success**: >98% successful scrapes
- **Processing Speed**: <1 second per announcement

---

## 🛠️ Technical Stack

### Core Libraries
```python
# Web Scraping
import requests
from bs4 import BeautifulSoup
from selenium import webdriver  # If dynamic content
import cloudscraper  # If anti-bot protection

# PDF Parsing (for attachments)
import PyPDF2
import pdfplumber
import tabula  # For financial tables

# NLP & Data Extraction
import re
from dateutil import parser
import spacy  # For entity extraction

# Database
import sqlite3
import json

# Scheduling & Monitoring
from apscheduler.schedulers.background import BackgroundScheduler
import time
```

### APIs (if available)
```python
# Check if PSX provides API
# https://dps.psx.com.pk/api/announcements (hypothetical)

# Alternative: SECP API
# https://www.secp.gov.pk/api/filings (hypothetical)
```

---

## ⚠️ Challenges & Solutions

### Challenge 1: Dynamic Content
**Problem**: PSX website may load announcements via JavaScript

**Solutions**:
- Option A: Use Selenium/Playwright for headless browser
- Option B: Reverse-engineer API calls (check Network tab)
- Option C: Use PSX RSS feed if available

### Challenge 2: PDF Parsing
**Problem**: Financial results often in PDF attachments

**Solutions**:
- Use `pdfplumber` for table extraction
- OCR for scanned PDFs (pytesseract)
- Regex patterns for common formats

### Challenge 3: Rate Limiting
**Problem**: PSX may rate-limit aggressive scraping

**Solutions**:
- Respectful delays (2-5 seconds between requests)
- User-Agent rotation
- Cached responses
- API if available

### Challenge 4: Categorization Ambiguity
**Problem**: Announcement titles can be ambiguous

**Solutions**:
- Keyword-based classification with confidence scores
- Manual review for tier-1 (critical) announcements
- Machine learning classifier (after collecting training data)

### Challenge 5: Duplicate Detection
**Problem**: Same announcement may appear multiple times

**Solutions**:
- Hash (symbol + date + title)
- Fuzzy matching for similar titles
- Check attachment URLs

---

## 📅 Implementation Timeline

### Week 1: Core Scraping
- [ ] Research PSX announcements page structure
- [ ] Build scraper for announcements table
- [ ] Create database schema
- [ ] Implement basic parser
- [ ] Test with 30-day historical data

### Week 2: Classification & Parsing
- [ ] Build announcement classifier
- [ ] Implement materiality scoring
- [ ] Add PDF parser for attachments
- [ ] Extract financial data (EPS, dividend, profit)
- [ ] Test categorization accuracy

### Week 3: Integration
- [ ] Enhance news-anomaly correlator
- [ ] Prioritize announcements over news
- [ ] Update explanation generator
- [ ] Add announcement display in reports
- [ ] Test end-to-end integration

### Week 4: Monitoring & Alerts
- [ ] Build real-time monitor
- [ ] Implement alert system (email/Slack)
- [ ] Add anomaly-announcement auto-correlation
- [ ] Create dashboard (optional)
- [ ] Production deployment

---

## 🚀 Expected Benefits

### Quantitative
- **Correlation Coverage**: 65% → **85%+** (with announcements)
- **Latency**: Hours (via news) → **Minutes** (direct from PSX)
- **Confidence**: 70% average → **90%+** (official source)
- **False Positives**: Reduced by **40%** (authoritative data)

### Qualitative
- ✅ **Authoritative**: Official source, not media interpretation
- ✅ **Complete**: Catch all material events
- ✅ **Structured**: Easier to parse than free-text news
- ✅ **Timely**: Real-time monitoring possible
- ✅ **Actionable**: Clear corporate actions to trade on

---

## 📋 File Structure

```
Investment/
├── psx_announcement_scraper.py       # Web scraper
├── psx_announcement_parser.py        # PDF/text parser
├── psx_announcement_classifier.py    # Categorization
├── psx_announcement_storage.py       # Database layer
├── psx_announcement_monitor.py       # Real-time monitoring
├── psx_alert_system.py               # Alert notifications
├── run_announcement_sync.py          # Daily batch sync
├── run_announcement_monitor.py       # Continuous monitoring
├── run_integrated_analysis.py        # Enhanced with announcements
├── announcement_data/
│   └── announcements.db              # SQLite database
└── PLAN_PSX_ANNOUNCEMENT_AGENT.md   # This file
```

---

## 🎯 Success Criteria

- [ ] **Scraping**: 100% of PSX announcements captured
- [ ] **Latency**: <5 minutes from PSX to database
- [ ] **Classification**: >95% accuracy
- [ ] **Integration**: Announcements prioritized in correlations
- [ ] **Alerts**: Critical announcements trigger notifications
- [ ] **Coverage**: 85%+ anomaly explanation rate
- [ ] **Documentation**: Complete API and usage guide

---

## 🔮 Future Enhancements

### Phase 5: Advanced Features
- [ ] Machine learning classifier (train on labeled data)
- [ ] Sentiment analysis of announcement text
- [ ] Peer comparison (compare company announcement to sector)
- [ ] Historical pattern matching (similar announcements in past)
- [ ] Predictive alerts (board meeting → likely results soon)

### Phase 6: Multi-Source
- [ ] SECP regulatory filings
- [ ] Company IR website monitoring
- [ ] International exchanges (for dual-listed companies)
- [ ] Broker research reports

### Phase 7: Intelligence
- [ ] Announcement clustering (related announcements)
- [ ] Sector-wide event detection
- [ ] Anomaly prediction (announcement before anomaly)
- [ ] Trading strategy backtesting

---

## 📊 Example Output

### Announcement Record
```json
{
  "announcement_id": "HBL_2026-02-14_DIV",
  "symbol": "HBL",
  "announcement_date": "2026-02-14T10:05:00",
  "category": "dividend",
  "subcategory": "final_cash",
  "materiality_tier": 1,
  "title": "Final Dividend for year ended December 31, 2025",
  "description": "Board of Directors announces final cash dividend of Rs 50 per share (500%)",
  "attachment_url": "https://dps.psx.com.pk/download/announcement/HBL_DIV_2026.pdf",
  "source_url": "https://dps.psx.com.pk/announcements/HBL/2026-02-14",
  "dividend_amount": 50.0,
  "dividend_type": "cash",
  "eps": 78.5,
  "profit_amount": 45000000000,
  "profit_change_pct": 28.5,
  "fetched_date": "2026-02-14T10:06:15",
  "is_processed": true,
  "related_anomalies": ["HBL_2026-02-14_VOLUME"],
  "market_impact": "positive"
}
```

### Enhanced Correlation Report
```
====================================================================================================
PSX ANOMALY-NEWS CORRELATION REPORT (WITH ANNOUNCEMENTS)
====================================================================================================

📊 HBL - 1 Anomaly

🔴 HIGH - Volume Spike
   Date: 2026-02-14
   Volume +180% from average (15.2M vs 5.4M)
   Z-Score: 4.82

   🎯 OFFICIAL ANNOUNCEMENT: 95% correlation
   ====================================
   📋 Final Dividend for year ended December 31, 2025
   📅 Announced: 2026-02-14 10:05
   🏷️  Category: dividend (final_cash)
   💰 Amount: Rs 50 per share (500%)
   📈 EPS: Rs 78.5 (Profit: Rs 45B, +28.5% YoY)
   ⭐ Materiality: Tier 1 (CRITICAL)
   🔗 Source: https://dps.psx.com.pk/announcements/HBL/2026-02-14
   ====================================

   📰 Supporting News:
      1. "HBL announces record 50% dividend, highest in banking sector" (Dawn Business, +0.82 sentiment)
      2. "Banking stocks rally as HBL sets new dividend benchmark" (Business Recorder, +0.74 sentiment)

   💡 Action: Strong buy signal - exceptional dividend yield
              Check sector peers for similar moves
              Review HBL fundamentals for sustained profitability

====================================================================================================
```

---

## ✅ Next Steps

1. **Validate Data Source**: Check PSX announcements page accessibility
2. **Prototype Scraper**: Build basic scraper for 1 week of data
3. **Test Classification**: Manually label 100 announcements, test classifier
4. **Integration Proof**: Link 1 announcement to 1 anomaly successfully
5. **Production Deploy**: After validation, deploy daily sync

---

**Status**: 📋 **PLANNED**
**Priority**: 🔴 **HIGH** (fills critical gap in current system)
**Estimated Effort**: 4 weeks (1 developer)
**Expected ROI**: 🚀 **VERY HIGH** (official source beats secondary news)

---

**End of Plan**
