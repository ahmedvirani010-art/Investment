# PSX Sentiment Momentum Tracker - Implementation Plan

## Problem Statement

The sentiment analyzer (`psx_sentiment_analyzer.py`) currently provides point-in-time sentiment analysis for news articles and text. However, **sentiment data is not tracked over time**, which means:

- No historical sentiment record per symbol
- Cannot detect sentiment momentum (improving/declining sentiment trends)
- Cannot identify sentiment reversals (bearish → bullish or vice versa)
- Cannot correlate sentiment changes with price movements
- No ability to detect sentiment-price divergences (sentiment improving but price falling)
- Missing sentiment-based timing signals for entry/exit

The sentiment momentum tracker should **capture, persist, and analyze sentiment trends over time** to provide momentum signals that complement technical and fundamental analysis.

---

## Architecture: Sentiment Momentum Flow

### Current Flow (Point-in-Time Only)

```
News Article
    |
    v
PSXSentimentAnalyzer.analyze_article()  -->  SentimentResult (in-memory only)
    |
    v
Correlator uses sentiment for current analysis
    |
    v
Sentiment data discarded, no history maintained
```

### Proposed Flow (Momentum Tracking)

```
News Articles (daily)
    |
    v
PSXSentimentAnalyzer.analyze_article()  -->  SentimentResult
    |
    v
SentimentMomentumStore.save_sentiment()  -->  SQLite (sentiment_data/momentum.db)
    |                                           |
    |   (write daily)                           |  (read for analysis)
    |                                           |
    v                                           v
Historical record                      SentimentMomentumTracker
maintained per symbol                  (computes momentum indicators)
    |                                           |
    v                                           v
Sentiment timeline                      MomentumSignal objects
per stock                                      |
                                              v
                                     Correlation / Reporting layer
```

---

## Component 1: Sentiment Momentum Store (`psx_sentiment_momentum_store.py`)

### Purpose

Persistent sentiment storage layer. Stores daily sentiment scores, tracks changes over time, and serves as the single source of truth for sentiment history.

### Database Schema

```sql
-- Daily aggregated sentiment per symbol
CREATE TABLE daily_sentiment (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,              -- ISO format YYYY-MM-DD
    avg_sentiment REAL NOT NULL,     -- Average sentiment score (-1.0 to +1.0)
    sentiment_label TEXT NOT NULL,   -- 'positive', 'negative', 'neutral'
    article_count INTEGER NOT NULL,  -- Number of articles analyzed
    positive_count INTEGER,          -- Articles with positive sentiment
    negative_count INTEGER,          -- Articles with negative sentiment
    neutral_count INTEGER,           -- Articles with neutral sentiment
    max_sentiment REAL,              -- Most positive article
    min_sentiment REAL,              -- Most negative article
    confidence REAL,                 -- Average confidence across articles
    volume_score REAL,               -- article_count * abs(avg_sentiment)
    recorded_at TEXT NOT NULL,       -- Timestamp of calculation
    PRIMARY KEY (symbol, date)
);

-- Individual article sentiment (for drill-down)
CREATE TABLE article_sentiment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT,
    sentiment_score REAL NOT NULL,
    sentiment_label TEXT NOT NULL,
    confidence REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

-- Sentiment momentum indicators (precomputed)
CREATE TABLE sentiment_momentum (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    momentum_7d REAL,                -- 7-day sentiment momentum
    momentum_14d REAL,               -- 14-day sentiment momentum
    momentum_30d REAL,               -- 30-day sentiment momentum
    trend TEXT,                      -- 'improving', 'declining', 'stable'
    strength TEXT,                   -- 'strong', 'moderate', 'weak'
    reversal_signal TEXT,            -- 'bullish_reversal', 'bearish_reversal', null
    divergence_type TEXT,            -- 'bullish_divergence', 'bearish_divergence', null
    signal_type TEXT,                -- 'buy', 'sell', 'hold'
    computed_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_sentiment_symbol ON daily_sentiment(symbol);
CREATE INDEX idx_sentiment_date ON daily_sentiment(date DESC);
CREATE INDEX idx_sentiment_symbol_date ON daily_sentiment(symbol, date DESC);
CREATE INDEX idx_article_symbol ON article_sentiment(symbol);
CREATE INDEX idx_article_date ON article_sentiment(date DESC);
CREATE INDEX idx_momentum_symbol ON sentiment_momentum(symbol);
CREATE INDEX idx_momentum_signal ON sentiment_momentum(signal_type);
```

### Key Design Decisions

1. **Daily aggregation**: Combine multiple articles per day into a single sentiment score per symbol
2. **Momentum indicators**: Precompute 7-day, 14-day, and 30-day momentum for fast querying
3. **Volume-weighted sentiment**: Articles * sentiment magnitude = sentiment volume (similar to price * volume)
4. **Reversal detection**: Flag when sentiment crosses key thresholds (negative → positive, etc.)
5. **Divergence tracking**: Detect when sentiment and price move in opposite directions

### API

```python
class SentimentMomentumStore:
    def __init__(self, db_path="sentiment_data/momentum.db"):
        ...

    def save_sentiment(self, symbol: str, date: str, sentiment_result: SentimentResult,
                      title: str, source: str = None):
        """Save individual article sentiment."""

    def aggregate_daily_sentiment(self, symbol: str, date: str) -> DailySentiment:
        """Aggregate all articles for a symbol on a given date."""

    def get_sentiment_history(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical sentiment data."""

    def compute_momentum(self, symbol: str, date: str) -> SentimentMomentum:
        """Compute momentum indicators for a symbol on a date."""

    def save_momentum(self, momentum: SentimentMomentum):
        """Save computed momentum indicators."""

    def get_symbols_by_signal(self, signal_type: str, date: str = None) -> List[str]:
        """Get symbols with specific signal (buy/sell/hold)."""
```

---

## Component 2: Sentiment Momentum Tracker (`psx_sentiment_momentum_tracker.py`)

### Purpose

Analyzes sentiment history to compute momentum indicators, detect reversals, and identify divergences between sentiment and price.

### Momentum Indicators

#### Sentiment Trend Indicators

| Indicator | Calculation | Signal Logic |
|-----------|-------------|--------------|
| **7-Day Momentum** | Linear regression slope of sentiment over 7 days | Positive slope = improving, Negative = declining |
| **14-Day Momentum** | Linear regression slope of sentiment over 14 days | Smoother trend, filters noise |
| **30-Day Momentum** | Linear regression slope of sentiment over 30 days | Long-term sentiment direction |
| **Sentiment MA Crossover** | SMA(7) vs SMA(21) of sentiment | Crossover signals sentiment shift |

#### Sentiment Reversal Indicators

| Pattern | Detection | Signal |
|---------|-----------|--------|
| **Bullish Reversal** | Sentiment crosses from negative to positive | Buy signal if price oversold |
| **Bearish Reversal** | Sentiment crosses from positive to negative | Sell signal if price overbought |
| **Sentiment Surge** | 2+ SD move in positive direction | Strong momentum confirmation |
| **Sentiment Crash** | 2+ SD move in negative direction | Risk-off signal |

#### Sentiment-Price Divergence

| Divergence Type | Pattern | Interpretation |
|----------------|---------|----------------|
| **Bullish Divergence** | Price falling but sentiment improving | Potential bottom, accumulation |
| **Bearish Divergence** | Price rising but sentiment declining | Potential top, distribution |
| **Confirmation** | Price and sentiment moving together | Trend is healthy |
| **False Move** | Large price move with no sentiment change | Low conviction, likely reversal |

### Data Models

```python
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
    confidence: float
    volume_score: float          # article_count * abs(avg_sentiment)

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
    confidence: float           # 0.0 - 1.0

@dataclass
class MomentumSignal:
    """Trading signal based on sentiment momentum."""
    symbol: str
    date: str
    signal_type: str            # 'buy', 'sell', 'hold'
    strength: str               # 'strong', 'moderate', 'weak'
    reasons: List[str]          # List of reasons for the signal
    sentiment_score: float      # Current sentiment
    momentum_7d: float
    momentum_14d: float
    price_sentiment_correlation: float
    confidence: float
```

### Signal Generation Logic

```python
For each stock:
  1. Get sentiment history (30 days minimum)
  2. Compute momentum indicators (7d, 14d, 30d slopes)
  3. Detect reversals (threshold crossings)
  4. Check for divergences (compare with price data)
  5. Aggregate signals:
     - Buy if: momentum improving + bullish reversal OR bullish divergence
     - Sell if: momentum declining + bearish reversal OR bearish divergence
     - Hold otherwise
  6. Assign strength based on:
     - Strong: 2+ indicators align + high confidence
     - Moderate: 1 indicator + medium confidence
     - Weak: Mixed signals or low confidence
```

### API

```python
class SentimentMomentumTracker:
    def __init__(self, sentiment_store: SentimentMomentumStore,
                 price_store: PSXPriceStore = None):
        self.sentiment_store = sentiment_store
        self.price_store = price_store

    def analyze_symbol(self, symbol: str, date: str = None) -> MomentumSignal:
        """Full momentum analysis for one stock."""

    def analyze_batch(self, symbols: List[str], date: str = None) -> Dict[str, MomentumSignal]:
        """Analyze multiple stocks."""

    def compute_momentum(self, sentiment_history: pd.DataFrame) -> Dict[str, float]:
        """Compute momentum indicators from sentiment history."""

    def detect_reversals(self, sentiment_history: pd.DataFrame) -> Optional[str]:
        """Detect sentiment reversals."""

    def detect_divergences(self, symbol: str, sentiment_history: pd.DataFrame,
                          price_history: pd.DataFrame) -> Optional[str]:
        """Detect sentiment-price divergences."""

    def get_buy_signals(self, date: str = None) -> List[MomentumSignal]:
        """Get all stocks with buy signals."""

    def get_sell_signals(self, date: str = None) -> List[MomentumSignal]:
        """Get all stocks with sell signals."""
```

---

## Component 3: Integration with News Pipeline

### Updated News Collection Flow

```python
# Current: psx_news_agent.py
def collect_news(symbols: List[str]):
    articles = scrape_from_sources()
    for article in articles:
        sentiment = analyzer.analyze_article(article.title, article.text)
        # Currently: sentiment used once, then discarded
        store_news_article(article, sentiment)

# After integration:
def collect_news(symbols: List[str]):
    articles = scrape_from_sources()
    for article in articles:
        sentiment = analyzer.analyze_article(article.title, article.text)

        # Store news article with sentiment
        store_news_article(article, sentiment)

        # NEW: Track sentiment momentum
        sentiment_store.save_sentiment(
            symbol=article.symbol,
            date=article.date,
            sentiment_result=sentiment,
            title=article.title,
            source=article.source
        )

    # NEW: Daily aggregation and momentum computation
    for symbol in symbols:
        daily_sentiment = sentiment_store.aggregate_daily_sentiment(symbol, today)
        momentum = tracker.compute_momentum(symbol, today)
        sentiment_store.save_momentum(momentum)
```

### Integration with Anomaly Correlator

Add sentiment momentum context to anomaly explanations:

```
LUCK - Volume Spike +250%
  News Correlation: 85% - Expansion announcement
  Sentiment Momentum:
    Current Sentiment: +0.65 (Positive)
    7-Day Momentum: +0.12 (Improving rapidly)
    14-Day Momentum: +0.08 (Sustained uptrend)
    Reversal: Bullish reversal detected 3 days ago
    Signal: BUY (Strong) - Sentiment improving with news catalyst
  Technical Context:
    RSI: 68 (Approaching overbought)
    MACD: Bullish crossover

  Interpretation: Volume spike aligns with positive sentiment momentum
  shift following expansion news. Sentiment has been improving for 2 weeks,
  suggesting sustained interest. Watch for overbought conditions.
```

---

## Component 4: Reporting

### Console Report Addition

```
====================================================================
SENTIMENT MOMENTUM ANALYSIS
====================================================================

📈 BULLISH SENTIMENT MOMENTUM:
  ENGRO  Sentiment: +0.72  |  7d Momentum: +0.15  |  Signal: BUY (Strong)
         Reason: Bullish reversal + improving momentum

  PPL    Sentiment: +0.58  |  7d Momentum: +0.09  |  Signal: BUY (Moderate)
         Reason: Sustained positive sentiment, confirming uptrend

📉 BEARISH SENTIMENT MOMENTUM:
  DGKC   Sentiment: -0.61  |  7d Momentum: -0.12  |  Signal: SELL (Strong)
         Reason: Bearish reversal + declining momentum

  MLCF   Sentiment: -0.45  |  7d Momentum: -0.08  |  Signal: SELL (Moderate)
         Reason: Deteriorating sentiment, weak fundamentals

🔄 SENTIMENT REVERSALS (Today):
  HBL    Negative → Positive  |  Potential bottom formation
  LUCK   Positive → Negative  |  Potential distribution phase

⚠️  DIVERGENCES DETECTED:
  OGDC   Bullish Divergence: Price -5% but sentiment +0.18
         → Potential accumulation opportunity

  UBL    Bearish Divergence: Price +8% but sentiment -0.22
         → Potential distribution, consider taking profits

====================================================================
```

### CSV Export

Add sentiment momentum columns to the combined analysis CSV:

```
symbol, date, anomaly_type, severity, z_score, correlation_score,
current_sentiment, sentiment_label, momentum_7d, momentum_14d, momentum_30d,
sentiment_trend, reversal_signal, divergence_type, sentiment_signal,
sentiment_confidence, article_count, volume_score
```

---

## File Structure

```
Investment/
├── psx_sentiment_momentum_store.py       # NEW - Sentiment persistence layer
├── psx_sentiment_momentum_tracker.py     # NEW - Momentum analysis engine
├── psx_sentiment_analyzer.py             # EXISTING - Base sentiment analyzer
├── psx_news_agent.py                     # MODIFIED - Integration point
├── psx_news_anomaly_correlator.py        # MODIFIED - Enriched with sentiment momentum
├── run_integrated_analysis.py            # MODIFIED - Add sentiment momentum step
├── sentiment_data/
│   └── momentum.db                       # NEW - Sentiment momentum database
├── news_data/
│   └── news.db                           # EXISTING - News articles
├── price_data/
│   ├── prices.db                         # EXISTING - OHLCV data
│   └── technicals.db                     # EXISTING - Technical indicators
└── PLAN_SENTIMENT_MOMENTUM_TRACKER.md    # This file
```

---

## Implementation Phases

### Phase 1: Data Store

- [ ] Create `psx_sentiment_momentum_store.py` with SQLite schema
- [ ] Implement `save_sentiment()` for individual articles
- [ ] Implement `aggregate_daily_sentiment()` for daily rollup
- [ ] Implement `get_sentiment_history()` for historical queries
- [ ] Test: Verify data persistence and aggregation logic

### Phase 2: Momentum Computation

- [ ] Create `psx_sentiment_momentum_tracker.py` with data models
- [ ] Implement 7-day, 14-day, 30-day momentum calculations (linear regression)
- [ ] Implement sentiment reversal detection
- [ ] Implement sentiment-price divergence detection
- [ ] Implement signal aggregation logic
- [ ] Test: Validate momentum calculations with known sentiment patterns

### Phase 3: News Pipeline Integration

- [ ] Modify `psx_news_agent.py` to save sentiment data
- [ ] Add daily sentiment aggregation step
- [ ] Add momentum computation step
- [ ] Test: End-to-end news → sentiment → momentum flow

### Phase 4: Correlation & Reporting

- [ ] Enrich anomaly correlation with sentiment momentum context
- [ ] Add sentiment momentum section to console report
- [ ] Add sentiment momentum columns to CSV export
- [ ] Add CLI flags (`--skip-sentiment-momentum`, `--sentiment-lookback`)

### Phase 5: Advanced Features (Future)

- [ ] Sentiment-based entry/exit timing
- [ ] Multi-source sentiment aggregation (Twitter, forums, etc.)
- [ ] Sentiment surprise detection (actual vs expected sentiment)
- [ ] Sentiment contagion analysis (sector-wide sentiment shifts)
- [ ] Machine learning for sentiment momentum prediction

---

## Dependencies

| Library | Status | Used For |
|---------|--------|----------|
| pandas | Already installed | DataFrame operations, time series |
| numpy | Already installed | Mathematical computations, regression |
| scipy | Already installed (via yfinance) | Statistical functions |
| sqlite3 | Python stdlib | Database persistence |
| vaderSentiment | Already installed | Sentiment analysis (existing) |

---

## Data Requirements

- **Minimum history**: 30 days of sentiment data for momentum calculation
- **Daily updates**: Process new articles daily, aggregate sentiment, compute momentum
- **Article retention**: Keep all articles for drill-down analysis
- **Aggregation timing**: Run daily aggregation after market close (4:00 PM PKT)

---

## Performance Considerations

- **Momentum computation**: O(n) with n = days of history, fast with pandas vectorization
- **Batch processing**: Compute momentum for all symbols in parallel
- **Database indexing**: Optimized for symbol + date queries
- **Incremental updates**: Only compute momentum for symbols with new articles

---

## Success Criteria

- [ ] Sentiment data persisted per article and per symbol per day
- [ ] Momentum indicators computed correctly (7d, 14d, 30d)
- [ ] Reversals detected accurately (threshold crossings)
- [ ] Divergences detected when sentiment and price disagree
- [ ] Signals generated with proper strength classification
- [ ] Integration with existing pipeline (news → sentiment → momentum)
- [ ] Console report includes sentiment momentum section
- [ ] CSV export includes sentiment momentum columns

---

## Use Cases

1. **Entry Timing**: Buy when sentiment shows bullish reversal + momentum improving
2. **Exit Timing**: Sell when sentiment shows bearish reversal or divergence
3. **Risk Management**: Avoid stocks with declining sentiment momentum
4. **Confirmation**: Use sentiment momentum to validate technical signals
5. **Contrarian Signals**: Bullish divergence = potential bottom, bearish divergence = potential top

---

**Status**: PLANNED
**Priority**: HIGH (adds powerful timing signals, complements technical analysis)
**New Files**: 2 (sentiment_momentum_store, sentiment_momentum_tracker)
**Modified Files**: 3 (news_agent, correlator, integrated_analysis)
**Estimated Completion**: 2-3 days
