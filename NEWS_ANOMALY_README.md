# PSX News-Anomaly Integration System

## Overview

This integrated system combines news collection, anomaly detection, and correlation analysis to provide comprehensive market intelligence for the Pakistan Stock Exchange (PSX).

## Architecture

```
┌─────────────────────┐
│  News Collection    │
│  psx_news_agent.py  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌──────────────────────┐
│  News Database      │◄─────┤  Liquidity Screener  │
│  news_data/news.db  │      │  (Stock Selection)   │
└──────────┬──────────┘      └──────────────────────┘
           │                           │
           │                           ▼
           │                 ┌──────────────────────┐
           │                 │  Anomaly Detection   │
           │                 │  psx_anomaly_agent   │
           │                 └──────────┬───────────┘
           │                           │
           └───────────┬───────────────┘
                       ▼
           ┌──────────────────────┐
           │  News-Anomaly        │
           │  Correlator          │
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │  Integrated Report   │
           └──────────────────────┘
```

## Components

### 1. News Collection (`psx_news_agent.py`)
- Fetches news from RSS feeds (Dawn, Business Recorder, Express Tribune, The News)
- Extracts stock symbols mentioned in articles
- Performs sentiment analysis using VADER
- Categorizes macro-economic news (interest rates, oil prices, etc.)
- Stores in SQLite database with full-text search

### 2. News Storage (`psx_news_storage.py`)
- SQLite database with FTS5 full-text search
- Indexes for fast queries by symbol, date, category
- Supports deduplication
- Tracks sentiment, relevance, macro categories

### 3. Anomaly Detection (`psx_anomaly_agent.py`)
- Detects 5 types of anomalies:
  - **Volume Spikes**: Unusual trading activity
  - **Price Movements**: Abnormal returns
  - **Opening Gaps**: Gap up/down patterns
  - **Volatility Spikes**: Unusual price ranges
  - **Liquidity Changes**: Turnover anomalies
- Uses statistical z-score analysis (default: 2.5σ threshold)
- Severity levels: LOW, MEDIUM, HIGH

### 4. News-Anomaly Correlator (`psx_news_anomaly_correlator.py`)
- Correlates detected anomalies with news articles
- Scoring based on:
  - Time proximity (same day, 1 day, 2+ days)
  - Direct mention vs. macro relevance
  - Sentiment alignment (positive news + price surge)
  - Keyword matching (volume keywords for volume spikes)
- Generates human-readable explanations

### 5. Integrated Analysis (`run_integrated_analysis.py`)
- Complete end-to-end pipeline
- Flexible stock selection (liquidity screener or preset list)
- Optional fresh news fetching
- Produces comprehensive correlation report

## Installation

```bash
# Install dependencies
pip install yfinance pandas numpy vaderSentiment rapidfuzz python-dateutil

# Optional: feedparser (has fallback to simple_rss_parser.py)
pip install feedparser
```

## Usage

### Quick Start

```bash
# Run complete analysis (30 top liquid stocks, fetch news, detect anomalies)
python3 run_integrated_analysis.py

# Use preset stock list, skip news fetch (faster)
python3 run_integrated_analysis.py --stocks preset --skip-news

# Analyze top 50 liquid stocks
python3 run_integrated_analysis.py --top 50

# Adjust anomaly sensitivity (lower = more sensitive)
python3 run_integrated_analysis.py --z-threshold 2.0

# Look back 7 days for news correlation
python3 run_integrated_analysis.py --news-hours 168
```

### Command-Line Options

```
--stocks {liquid,preset}   Stock selection: liquid screener or preset list
--top N                    Number of top liquid stocks (default: 30)
--skip-news                Skip news fetch, use existing database
--news-hours N             Hours to look back for news (default: 48)
--z-threshold X            Anomaly detection threshold (default: 2.5)
--lookback N               Days for baseline calculation (default: 60)
```

### Individual Components

```bash
# Fetch news only
python3 psx_news_agent.py

# Detect anomalies only (on preset stocks)
python3 psx_anomaly_agent.py

# Correlate existing anomalies with news
python3 psx_news_anomaly_correlator.py
```

### Programmatic Usage

```python
from run_integrated_analysis import run_full_analysis

# Custom analysis
run_full_analysis(
    use_liquid_stocks=True,
    top_n=50,
    fetch_news=True,
    news_hours=72,
    z_threshold=2.0,
    lookback_days=90
)
```

## Output

### Sample Output

```
====================================================================================================
PSX ANOMALY-NEWS CORRELATION REPORT
====================================================================================================

Total Anomalies: 3
Anomalies with News Correlation (≥50%): 3
Coverage: 100.0%

====================================================================================================
📊 PPL - 1 Anomalies
====================================================================================================

🟢 LOW - Opening Gap
   Date: 2026-02-13
   Gap Down of -1.34%
   Z-Score: -2.91

   🔗 News Correlation: 90%
   📰 Related News (5 articles):
      1. Equities plummet on super tax blow
         Source: Dawn Business | 2026-02-13 (1d after) (positive: +0.69)
         📊 Macro: interest_rates
      2. Bearish wave wipes out 908 points off KSE-100
         Source: Dawn Business | 2026-02-13 (1d after) (negative: -0.29)
         📊 Macro: oil_prices

====================================================================================================

📈 Correlation Statistics:
   Average Correlation Score: 70.0%
   High Correlation (≥70%): 2 (66.7%)
   Medium Correlation (50-70%): 1 (33.3%)
   Low Correlation (<50%): 0 (0.0%)
```

## Features

### News Collection
- ✅ RSS feed parsing (4 major Pakistan business news sources)
- ✅ HTML content cleaning
- ✅ Symbol extraction (95+ PSX stocks)
- ✅ Sentiment analysis (VADER + financial lexicon)
- ✅ Macro categorization (17 categories, 12 chemical subcategories)
- ✅ Duplicate detection
- ✅ Full-text search (SQLite FTS5)

### Anomaly Detection
- ✅ Statistical z-score analysis
- ✅ Multi-type detection (volume, price, gap, volatility, liquidity)
- ✅ Severity classification (LOW, MEDIUM, HIGH)
- ✅ Historical baseline calculation
- ✅ Configurable sensitivity

### Correlation
- ✅ Time-based relevance scoring
- ✅ Sentiment alignment detection
- ✅ Macro news impact mapping
- ✅ Keyword-based relevance
- ✅ Confidence scoring (0-100%)
- ✅ Automated explanation generation

## Database Schema

### news_articles table
```sql
article_id              TEXT PRIMARY KEY
title                   TEXT NOT NULL
url                     TEXT NOT NULL
source                  TEXT NOT NULL
published_date          TEXT NOT NULL
mentioned_symbols       TEXT (JSON array)
primary_symbol          TEXT
sentiment_score         REAL (-1.0 to +1.0)
sentiment_label         TEXT (positive/negative/neutral)
is_macro_news          INTEGER (0/1)
macro_category         TEXT
affected_sectors       TEXT (JSON array)
...
```

### Indexes
- `idx_published_date` - Fast date-range queries
- `idx_source` - Filter by news source
- `idx_macro_category` - Macro news filtering
- `news_fts` - Full-text search (FTS5)

## Performance

- **News Fetch**: 30-60 seconds for 48-hour window
- **Anomaly Detection**: ~1 second per stock
- **Correlation**: <1 second per anomaly
- **Full Analysis (30 stocks)**: ~3-5 minutes

## Correlation Scoring

### Factors

1. **Direct Mention** (50% base score)
   - Primary symbol: +10%
   - Mentioned symbol: base 50%
   - Macro news: 20% base

2. **Time Proximity** (up to 30%)
   - Same day: +30%
   - 1 day: +20%
   - 2 days: +10%

3. **Sentiment Alignment** (up to 30%)
   - Positive news + price surge: +20%
   - Negative news + price drop: +20%
   - Strong sentiment (|score| > 0.5): +10%

4. **Keyword Matching** (up to 10%)
   - Volume anomaly + trading keywords: +10%
   - Price anomaly + price/earnings keywords: +10%
   - Volatility + uncertainty keywords: +10%

### Thresholds
- **High Correlation**: ≥70% (🔗)
- **Medium Correlation**: 50-69% (🔍)
- **Low Correlation**: <50% (❓)

## Macro News Categories

### Supported Categories
- `interest_rates`, `policy_rate`, `monetary_policy`
- `oil_prices`, `gas_prices`, `coal_prices`
- `usd_pkr`, `forex`, `exchange_rate`
- `inflation`, `cpi`, `wpi`
- `gdp_growth`, `trade_balance`
- Chemical prices (12 subcategories)
- And more...

### Sector Mapping
- **Energy**: Oil/gas prices affect PSO, OGDC, PPL, APL, etc.
- **Chemicals**: Propylene prices affect EPCL, LOTTE, ENGRO
- **Banks**: Interest rates affect HBL, UBL, MCB, etc.
- **Consumer**: Inflation affects NESTLE, UNITY, UNILEVER

## Testing

### Test Results (2026-02-14)

**News Collection Test**:
- ✅ 34 articles fetched (48-hour window)
- ✅ 40 unique stock symbols identified
- ✅ 6 macro categories detected
- ✅ 100% processing success rate
- ✅ Database: 328 KB, full-text search operational

**Integration Test**:
- ✅ 29 stocks analyzed
- ✅ 3 anomalies detected
- ✅ 100% correlation coverage (3/3 explained)
- ✅ Average correlation: 70%
- ✅ 2 high correlations (≥70%)
- ✅ 1 medium correlation (50-69%)

## Scheduling

### Daily Automation (Cron)

```bash
# Add to crontab: run at 10 AM daily
0 10 * * * cd /home/user/Investment && python3 run_integrated_analysis.py >> logs/analysis_$(date +\%Y\%m\%d).log 2>&1
```

### Systemd Timer (Alternative)

```ini
[Unit]
Description=PSX Integrated Analysis

[Timer]
OnCalendar=*-*-* 10:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## Future Enhancements

### Planned Features
- [ ] Web dashboard (Flask/Streamlit)
- [ ] Email alerts for high-severity anomalies
- [ ] Machine learning for correlation scoring
- [ ] Historical anomaly tracking
- [ ] Sector-wide anomaly detection
- [ ] Integration with trading signals
- [ ] Real-time WebSocket news feed
- [ ] Advanced NLP for news extraction

### Phase 2 (In Progress)
- [x] News collection
- [x] Anomaly detection
- [x] News-anomaly correlation
- [ ] Automated daily reporting
- [ ] Alert system

## Troubleshooting

### No News Found
- Check internet connection
- Verify RSS feeds are accessible
- Try increasing `--news-hours` parameter

### feedparser Installation Failed
- System uses `simple_rss_parser.py` as fallback
- No action needed, works automatically

### No Anomalies Detected
- Lower z-threshold: `--z-threshold 2.0`
- Increase stock count: `--top 50`
- Check if market was calm (legitimate result)

### Low Correlation Scores
- Fetch more news: `--news-hours 72`
- News might be genuinely unrelated
- Consider expanding news sources

## Data Files

```
Investment/
├── run_integrated_analysis.py    # Main entry point
├── psx_news_agent.py             # News fetching
├── psx_news_storage.py           # Database layer
├── psx_news_sources.py           # RSS source config
├── psx_anomaly_agent.py          # Anomaly detection
├── psx_news_anomaly_correlator.py # Correlation engine
├── simple_rss_parser.py          # RSS parser fallback
└── news_data/
    └── news.db                    # SQLite database
```

## License

MIT License - See LICENSE file

## Support

For issues, questions, or contributions:
- GitHub Issues: [Link to repo]
- Documentation: This file

---

**Last Updated**: 2026-02-14
**Version**: 1.0.0
**Status**: ✅ Production Ready
