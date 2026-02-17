# PSX Technical Analysis Agent - Implementation Plan

## Problem Statement

The anomaly agent (`psx_anomaly_agent.py`) already fetches 60+ days of OHLCV (Open, High, Low, Close, Volume) data from yfinance for every stock it analyzes. **This data is used once in-memory and then discarded.** There is no persistent price history, which means:

- Every run re-fetches the same data from yfinance (slow, rate-limited)
- Historical data beyond the lookback window is lost forever
- Technical analysis (moving averages, RSI, MACD, etc.) cannot be performed without re-fetching
- No ability to backtest signals or track indicator trends over time

The technical analysis agent should **capture and persist this data**, then compute standard technical indicators to complement the anomaly agent's statistical approach.

---

## Architecture: Data Flow Redesign

### Current Flow (Data is Discarded)

```
yfinance API
    |
    v
PSXAnomalyAgent._fetch_stock_data()  -->  pd.DataFrame (in-memory only)
    |
    v
5 detection methods consume DataFrame
    |
    v
Anomaly objects returned, DataFrame garbage-collected
```

### Proposed Flow (Data is Persisted and Reused)

```
yfinance API
    |
    v
PSXPriceStore.fetch_and_store()  -->  SQLite (price_data/prices.db)
    |                                      |
    |   (write once)                       |  (read many)
    |                                      |
    v                                      v
PSXAnomalyAgent                    PSXTechnicalAnalysisAgent
(uses stored data)                 (computes indicators on stored data)
    |                                      |
    v                                      v
Anomaly objects                    TechnicalSignal objects
    |                                      |
    +------------------+-------------------+
                       |
                       v
              Correlation / Reporting layer
```

---

## Component 1: Price Data Store (`psx_price_store.py`)

### Purpose

Persistent OHLCV storage layer. Fetches from yfinance, deduplicates by (symbol, date), and serves as the single source of truth for all price-dependent agents.

### Database Schema

```sql
CREATE TABLE daily_prices (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,          -- ISO format YYYY-MM-DD
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    turnover REAL,              -- volume * close (precomputed)
    fetched_at TEXT NOT NULL,    -- when this row was fetched
    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_prices_symbol ON daily_prices(symbol);
CREATE INDEX idx_prices_date ON daily_prices(date DESC);
CREATE INDEX idx_prices_symbol_date ON daily_prices(symbol, date DESC);
```

### Key Design Decisions

1. **Incremental fetching**: On each run, check the latest stored date per symbol and only fetch missing days from yfinance. This reduces API calls by ~90% on repeat runs.

2. **Shared with anomaly agent**: Modify `PSXAnomalyAgent._fetch_stock_data()` to read from the store instead of hitting yfinance directly. The anomaly agent becomes a consumer, not a fetcher.

3. **Storage location**: `price_data/prices.db` (parallel to `news_data/news.db`).

4. **Data retention**: Keep all historical data (no cleanup). Daily OHLCV is tiny (~100 bytes/row). 100 stocks x 252 trading days x 5 years = ~126K rows = ~15MB. No storage concern.

### API

```python
class PSXPriceStore:
    def __init__(self, db_path="price_data/prices.db"):
        ...

    def fetch_and_store(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """Fetch from yfinance only for missing dates, store, return full range."""

    def get_prices(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """Read stored prices. No API call."""

    def get_latest_date(self, symbol: str) -> Optional[str]:
        """Most recent date in store for this symbol."""

    def bulk_update(self, symbols: List[str], days: int = 60):
        """Update all symbols. Called once at start of pipeline."""
```

### Integration with Anomaly Agent

The anomaly agent's `_fetch_stock_data` method currently calls yfinance directly. After this change:

```python
# Before (current)
def _fetch_stock_data(self, symbol):
    ticker = yf.Ticker(f"{symbol}.KA")
    df = ticker.history(start=start_date, end=end_date)
    return df

# After (uses price store)
def _fetch_stock_data(self, symbol):
    return self.price_store.get_prices(symbol, days=self.lookback_days)
```

The anomaly agent's constructor will accept an optional `PSXPriceStore` instance. When provided, it reads from the store. When not provided, it falls back to direct yfinance (backward compatible).

---

## Component 2: Technical Analysis Agent (`psx_technical_agent.py`)

### Purpose

Computes standard technical indicators on stored price data. Produces `TechnicalSignal` objects that describe the current technical posture of each stock.

### Indicators to Implement

#### Trend Indicators

| Indicator | Calculation | Signal Logic |
|-----------|-------------|--------------|
| **SMA crossover** | SMA(20) vs SMA(50) | Bullish: SMA20 crosses above SMA50. Bearish: below. |
| **EMA crossover** | EMA(12) vs EMA(26) | Same logic as SMA but faster response. |
| **Price vs SMA(200)** | Close vs SMA(200) | Above = long-term uptrend. Below = downtrend. |

#### Momentum Indicators

| Indicator | Calculation | Signal Logic |
|-----------|-------------|--------------|
| **RSI(14)** | Relative Strength Index, 14-day | Overbought: >70. Oversold: <30. |
| **MACD** | EMA(12) - EMA(26), signal = EMA(9) of MACD | Bullish: MACD crosses above signal. |
| **Stochastic %K/%D** | 14-day stochastic oscillator | Overbought: >80. Oversold: <20. |

#### Volatility Indicators

| Indicator | Calculation | Signal Logic |
|-----------|-------------|--------------|
| **Bollinger Bands** | SMA(20) +/- 2*StdDev(20) | Price at upper band = overbought. Lower = oversold. |
| **ATR(14)** | Average True Range, 14-day | High ATR = volatile. Low = consolidation. |

#### Volume Indicators

| Indicator | Calculation | Signal Logic |
|-----------|-------------|--------------|
| **OBV** | On-Balance Volume | Rising OBV + flat price = accumulation. |
| **VWAP** | Volume-Weighted Average Price | Price above VWAP = bullish intraday. |

### Data Model

```python
class SignalType(Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    OVERBOUGHT = "Overbought"
    OVERSOLD = "Oversold"

class SignalStrength(Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"

@dataclass
class TechnicalSignal:
    symbol: str
    date: str
    indicator: str          # "RSI", "MACD", "SMA_crossover", etc.
    signal_type: SignalType
    strength: SignalStrength
    value: float            # Current indicator value
    threshold: float        # Threshold that triggered the signal
    description: str        # Human-readable: "RSI at 28.3 (oversold)"

@dataclass
class TechnicalSnapshot:
    """Full technical picture for one stock on one date."""
    symbol: str
    date: str
    signals: List[TechnicalSignal]
    overall_bias: SignalType      # Aggregated from all signals
    confidence: float             # 0.0-1.0 based on signal agreement
    indicator_values: Dict[str, float]  # {"RSI": 28.3, "MACD": -1.2, ...}
```

### Signal Aggregation Logic

```
For each stock:
  1. Compute all indicators
  2. Count bullish vs bearish signals
  3. Weight by strength (Strong=3, Moderate=2, Weak=1)
  4. overall_bias = weighted majority
  5. confidence = |bullish_weight - bearish_weight| / total_weight
```

Example:
- RSI < 30 (oversold) -> Bullish, Strong -> +3
- MACD below signal -> Bearish, Moderate -> -2
- Price above SMA(200) -> Bullish, Moderate -> +2
- SMA(20) below SMA(50) -> Bearish, Weak -> -1
- Net: +3+2-2-1 = +2, Total = 8, Confidence = 2/8 = 0.25 -> **Bullish, Low Confidence**

### API

```python
class PSXTechnicalAgent:
    def __init__(self, price_store: PSXPriceStore):
        self.price_store = price_store

    def analyze_symbol(self, symbol: str) -> TechnicalSnapshot:
        """Full technical analysis for one stock."""

    def analyze_batch(self, symbols: List[str]) -> Dict[str, TechnicalSnapshot]:
        """Analyze multiple stocks."""

    def get_signals(self, symbol: str) -> List[TechnicalSignal]:
        """Get only actionable signals (non-neutral)."""

    # Individual indicator methods
    def compute_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
    def compute_macd(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    def compute_bollinger(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    def compute_stochastic(self, df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
    def compute_obv(self, df: pd.DataFrame) -> pd.Series:
```

### Data Requirements

| Indicator | Minimum Days Needed |
|-----------|-------------------|
| SMA(200) | 200 |
| SMA(50) | 50 |
| RSI(14) | 15 |
| MACD | 35 (26 + 9) |
| Bollinger(20) | 20 |
| ATR(14) | 15 |
| Stochastic(14) | 14 |

**Implication**: The price store should maintain at least 200 trading days (~10 months) of data for full indicator coverage. On first run, fetch 250 calendar days. After that, incremental daily updates suffice.

---

## Component 3: Technical Signal Storage (`psx_technical_store.py`)

### Purpose

Persist computed technical snapshots so they can be:
- Queried historically (what was RSI last week?)
- Compared across time (how has the bias shifted?)
- Used by the correlator to enrich anomaly explanations

### Database Schema

```sql
-- Individual indicator values per stock per day
CREATE TABLE technical_indicators (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    indicator TEXT NOT NULL,      -- "RSI", "MACD", "SMA_20", etc.
    value REAL NOT NULL,
    signal_type TEXT,             -- "Bullish", "Bearish", "Neutral", etc.
    strength TEXT,                -- "Strong", "Moderate", "Weak"
    computed_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date, indicator)
);

-- Aggregated snapshot per stock per day
CREATE TABLE technical_snapshots (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    overall_bias TEXT NOT NULL,   -- "Bullish", "Bearish", "Neutral"
    confidence REAL NOT NULL,
    bullish_count INTEGER,
    bearish_count INTEGER,
    neutral_count INTEGER,
    indicator_values TEXT,        -- JSON of all indicator values
    computed_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_tech_symbol ON technical_indicators(symbol);
CREATE INDEX idx_tech_date ON technical_indicators(date DESC);
CREATE INDEX idx_snap_symbol ON technical_snapshots(symbol);
CREATE INDEX idx_snap_bias ON technical_snapshots(overall_bias);
```

### API

```python
class TechnicalStore:
    def __init__(self, db_path="price_data/technicals.db"):
        ...

    def save_snapshot(self, snapshot: TechnicalSnapshot):
        """Save full snapshot + individual indicators."""

    def get_snapshot(self, symbol: str, date: str) -> Optional[TechnicalSnapshot]:
        """Retrieve snapshot for a specific date."""

    def get_indicator_history(self, symbol: str, indicator: str, days: int = 30) -> List[Tuple[str, float]]:
        """Get indicator values over time (for charting/trend analysis)."""

    def get_overbought_stocks(self, date: str = None) -> List[str]:
        """Stocks with RSI > 70 on given date."""

    def get_oversold_stocks(self, date: str = None) -> List[str]:
        """Stocks with RSI < 30 on given date."""
```

---

## Component 4: Integration with Existing Pipeline

### Updated `run_integrated_analysis.py`

The pipeline adds two new steps between stock selection and anomaly detection:

```
Step 1: Stock Selection          (existing - liquidity screener)
Step 2: Price Data Sync          (NEW - fetch/update price store)
Step 3: News Collection          (existing - news agent)
Step 4: Technical Analysis       (NEW - compute indicators)
Step 5: Anomaly Detection        (existing - now reads from price store)
Step 6: News-Anomaly Correlation (existing - now enriched with technicals)
```

### Enriched Anomaly Correlation

The correlator can now add technical context to anomaly explanations:

```
HBL - Volume Spike +180%
  News Correlation: 95% - Dividend announcement
  Technical Context:
    RSI: 72.1 (overbought territory)
    MACD: Bullish crossover 2 days ago
    Price: Above SMA(200), uptrend intact
    Bias: Bullish (Strong)

  Interpretation: Volume spike aligns with both news catalyst
  (dividend) and prior bullish technical setup. RSI in overbought
  zone suggests near-term pullback risk after the move.
```

### CLI Arguments (additions to `run_integrated_analysis.py`)

```
--skip-technicals         Skip technical analysis computation
--ta-lookback N           Days of price history for indicators (default: 250)
--save-technicals         Persist computed indicators to database
```

---

## Component 5: Reporting

### Console Report Addition

After the anomaly correlation report, add a technical summary section:

```
====================================================================
TECHNICAL ANALYSIS SUMMARY
====================================================================

OVERBOUGHT (RSI > 70):
  LUCK   RSI: 74.2  |  Bias: Bullish (Strong)  |  Near SMA(20) upper band
  HBL    RSI: 71.8  |  Bias: Bullish (Moderate) |  Above SMA(200)

OVERSOLD (RSI < 30):
  MLCF   RSI: 27.5  |  Bias: Bearish (Strong)  |  Below SMA(200)
  KAPCO  RSI: 29.1  |  Bias: Bearish (Moderate) |  MACD bearish crossover

BULLISH CROSSOVERS (today):
  ENGRO  SMA(20) crossed above SMA(50)
  PPL    MACD crossed above signal line

BEARISH CROSSOVERS (today):
  DGKC   SMA(20) crossed below SMA(50)

====================================================================
```

### CSV Export

Add technical indicator columns to the existing combined analysis CSV:

```
symbol, date, anomaly_type, severity, z_score, correlation_score,
rsi, macd, macd_signal, sma_20, sma_50, sma_200, bollinger_upper,
bollinger_lower, atr, obv, overall_bias, confidence
```

---

## File Structure

```
Investment/
├── psx_price_store.py                # NEW - OHLCV persistence layer
├── psx_technical_agent.py            # NEW - Technical indicator engine
├── psx_technical_store.py            # NEW - Indicator persistence layer
├── psx_anomaly_agent.py              # MODIFIED - reads from price store
├── psx_news_anomaly_correlator.py    # MODIFIED - enriched with technicals
├── run_integrated_analysis.py        # MODIFIED - 2 new pipeline steps
├── price_data/
│   ├── prices.db                     # NEW - OHLCV database
│   └── technicals.db                 # NEW - Computed indicators database
├── news_data/
│   └── news.db                       # EXISTING - news articles
└── PLAN_TECHNICAL_ANALYSIS_AGENT.md  # This file
```

---

## Implementation Phases

### Phase 1: Price Data Store

- [ ] Create `psx_price_store.py` with SQLite schema
- [ ] Implement incremental fetch logic (only missing dates from yfinance)
- [ ] Implement `get_prices()` read method returning DataFrame
- [ ] Modify `PSXAnomalyAgent.__init__` to accept optional `PSXPriceStore`
- [ ] Modify `PSXAnomalyAgent._fetch_stock_data` to use store when available
- [ ] Test: run anomaly agent with and without store, verify identical results

### Phase 2: Technical Indicator Engine

- [ ] Create `psx_technical_agent.py` with `TechnicalSignal`/`TechnicalSnapshot` data models
- [ ] Implement RSI calculation
- [ ] Implement SMA/EMA crossover detection
- [ ] Implement MACD (line, signal, histogram)
- [ ] Implement Bollinger Bands
- [ ] Implement Stochastic Oscillator
- [ ] Implement ATR
- [ ] Implement OBV
- [ ] Implement signal aggregation logic (overall bias + confidence)
- [ ] Test: validate indicators against known values for a sample stock

### Phase 3: Persistence & History

- [ ] Create `psx_technical_store.py` with SQLite schema
- [ ] Implement save/load for snapshots and individual indicators
- [ ] Implement history queries (indicator over time)
- [ ] Implement screener queries (overbought/oversold lists)

### Phase 4: Pipeline Integration

- [ ] Add price sync step to `run_integrated_analysis.py`
- [ ] Add technical analysis step to pipeline
- [ ] Enrich anomaly correlation with technical context
- [ ] Add technical summary section to console report
- [ ] Add technical columns to CSV export
- [ ] Add CLI flags (`--skip-technicals`, `--ta-lookback`, `--save-technicals`)

### Phase 5: Extended Analysis (Future)

- [ ] Support/resistance level detection
- [ ] Fibonacci retracement levels
- [ ] Volume profile analysis
- [ ] Multi-timeframe analysis (weekly + daily)
- [ ] Divergence detection (price vs RSI, price vs OBV)
- [ ] Historical signal accuracy tracking (backtesting)

---

## Dependencies

No new external dependencies required. All indicators are computed using pandas and numpy, which are already in `requirements.txt`.

| Library | Status | Used For |
|---------|--------|----------|
| pandas | Already installed | DataFrame operations, rolling windows |
| numpy | Already installed | Mathematical computations |
| yfinance | Already installed | Data fetching (existing) |
| sqlite3 | Python stdlib | Database persistence |

---

## Key Constraints

1. **No yfinance redundancy**: The price store must be the single fetch point. Neither the anomaly agent nor the technical agent should call yfinance directly once the store is in place.

2. **Backward compatibility**: The anomaly agent must still work without the price store (direct yfinance mode) for users who don't want the database.

3. **Computation speed**: All indicators should compute in <1 second per stock on 250 days of data. pandas rolling operations are already fast enough.

4. **First-run behavior**: On the first run with an empty database, `bulk_update()` will fetch 250 calendar days for all stocks. This is the slow run. Subsequent runs only fetch 1-2 days of delta.

5. **PSX market hours**: PSX trades Sunday-Thursday, 9:30 AM - 3:30 PM PKT. The store should be aware that Friday/Saturday have no data (yfinance already handles this).

---

## Success Criteria

- [ ] Price data persisted across runs (no redundant yfinance calls)
- [ ] All 10 technical indicators compute correctly
- [ ] Signals match expected values for known stock patterns
- [ ] Anomaly agent reads from store with no behavior change
- [ ] Technical summary appears in integrated analysis report
- [ ] CSV export includes indicator columns
- [ ] Full pipeline runs end-to-end with new steps

---

**Status**: PLANNED
**Priority**: HIGH (eliminates wasted API calls, adds significant analytical value)
**New Files**: 3 (price_store, technical_agent, technical_store)
**Modified Files**: 3 (anomaly_agent, correlator, integrated_analysis)
