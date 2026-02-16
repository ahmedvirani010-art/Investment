# Agent Catalog

## Table of Contents

1. [Overview](#overview)
2. [PSXLiquidityScreener](#psxliquidityscreener)
3. [PSXPriceStore](#psxpricestore)
4. [PSXTechnicalAgent](#psxtechnicalagent)
5. [PSXFundamentalAgent](#psxfundamentalagent)
6. [PSXAnomalyAgent](#psxanomalyagent)
7. [PSXNewsAgent](#psxnewsagent)
8. [PSXNewsPriceCorrelator](#psxnewspricecorrelator)
9. [PSXPortfolioAgent](#psxportfolioagent)
10. [PSXRiskAgent](#psxriskagent)

---

## Overview

The PSX orchestration system coordinates **9 specialized agents**, each responsible for a specific aspect of market analysis, portfolio management, or risk control.

### Agent Ecosystem

```
Data Collection Layer (3 agents):
  • PSXLiquidityScreener - Stock selection
  • PSXPriceStore - Price data management  
  • PSXNewsAgent - News aggregation

Analysis Layer (4 agents):
  • PSXTechnicalAgent - Technical indicators & signals
  • PSXFundamentalAgent - Financial metrics
  • PSXAnomalyAgent - Anomaly detection
  • PSXNewsPriceCorrelator - News-price correlation

Portfolio & Risk Layer (2 agents):
  • PSXPortfolioAgent - Position tracking & P&L
  • PSXRiskAgent - Risk validation & monitoring
```

### Quick Reference

| Agent | Purpose | Primary Methods | Events Emitted |
|-------|---------|----------------|----------------|
| **PSXLiquidityScreener** | Select liquid stocks | `screen_stocks()` | `stocks_screened` |
| **PSXPriceStore** | Fetch & store prices | `update_prices()`, `get_prices()` | `price_data_updated` |
| **PSXTechnicalAgent** | Technical analysis | `analyze_symbol()` | `technical_analysis_complete` |
| **PSXFundamentalAgent** | Fundamental analysis | `analyze_fundamentals()` | `fundamental_analysis_complete` |
| **PSXAnomalyAgent** | Detect anomalies | `detect_anomalies()` | `anomaly_detected`, `high_severity_anomaly` |
| **PSXNewsAgent** | Fetch news | `fetch_news()` | `news_fetched`, `news_published` |
| **PSXNewsPriceCorrelator** | Correlate news & price | `correlate_anomalies()` | `news_correlation_complete` |
| **PSXPortfolioAgent** | Manage portfolio | `add_position()`, `get_pnl()` | `position_opened`, `position_closed` |
| **PSXRiskAgent** | Risk management | `validate_trade()`, `check_portfolio_risk()` | `risk_violation` |

---

## PSXLiquidityScreener

### Purpose
Screens PSX stocks for liquidity and tradability.

### Location
```
psx_liquidity_screener/
├── screener.py
└── __init__.py
```

### Key Method: `screen_stocks()`

```python
def screen_stocks(
    self,
    min_volume: int = 500000,
    min_price: float = 20.0,
    lookback_days: int = 30
) -> List[str]:
    """
    Screen stocks for liquidity.
    
    Returns: List of stock symbols meeting criteria
    """
```

### Example Output
```python
["OGDC", "PPL", "PSO", "ENGRO", "HUBC", ...]  # 30-50 symbols
```

---

## PSXPriceStore

### Purpose
Fetches, stores, and provides historical price data using yfinance.

### Location
```
psx_price_store/
├── store.py
└── __init__.py
```

### Key Methods

#### `update_prices()`
```python
def update_prices(
    self,
    symbols: List[str],
    period: str = "1mo"
) -> Dict[str, int]:
    """Fetch and store price data."""
```

#### `get_prices()`
```python
def get_prices(
    self,
    symbol: str,
    start_date: Optional[str] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Retrieve price data."""
```

### Database Schema
```sql
CREATE TABLE price_data (
    symbol TEXT,
    date DATE,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
);
```

---

## PSXTechnicalAgent

### Purpose
Performs technical analysis using indicators and patterns.

### Location
```
psx_technical_agent/
├── agent.py
└── __init__.py
```

### Key Method: `analyze_symbol()`

```python
def analyze_symbol(
    self,
    symbol: str,
    period: str = "1mo"
) -> Dict[str, Any]:
    """Perform technical analysis."""
```

### Output Structure
```python
{
    "symbol": "OGDC",
    "trend": {
        "direction": "uptrend",
        "strength": 0.75,
        "sma_20": 123.40
    },
    "momentum": {
        "rsi_14": 68.5,
        "macd": {"macd": 2.15, "signal": 1.80}
    },
    "signals": {
        "overall": "buy",
        "strength": 0.72
    }
}
```

### Indicators
- **Trend**: SMA (20, 50, 200), EMA (12, 26)
- **Momentum**: RSI (14), MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, Volume Rate of Change

---

## PSXFundamentalAgent

### Purpose
Analyzes fundamental financial metrics.

### Location
```
psx_fundamental_agent/
├── agent.py
└── __init__.py
```

### Key Method: `analyze_fundamentals()`

```python
def analyze_fundamentals(self, symbol: str) -> Dict[str, Any]:
    """Analyze fundamental metrics."""
```

### Output Structure
```python
{
    "symbol": "OGDC",
    "valuation": {
        "pe_ratio": 12.5,
        "pb_ratio": 1.8,
        "dividend_yield": 4.5
    },
    "profitability": {
        "roe": 15.2,
        "roa": 8.5
    },
    "rating": {
        "overall": "buy",
        "score": 7.5
    }
}
```

---

## PSXAnomalyAgent

### Purpose
Detects price and volume anomalies using statistical and ML methods.

### Location
```
psx_anomaly_agent/
├── agent.py
└── __init__.py
```

### Key Method: `detect_anomalies()`

```python
def detect_anomalies(
    self,
    symbol: str,
    lookback_days: int = 30
) -> Dict[str, Any]:
    """Detect anomalies."""
```

### Output Structure
```python
{
    "symbol": "OGDC",
    "anomalies": [
        {
            "type": "price_surge",
            "severity": 0.85,  # 0-1
            "description": "Price increased 8.5%, 3.2 std devs above avg",
            "metrics": {
                "price_change": 8.5,
                "z_score": 3.2
            }
        }
    ],
    "overall_severity": 0.85,
    "recommendation": "investigate"
}
```

### Detection Methods
- **Statistical**: Z-score, IQR
- **ML**: Isolation Forest
- **Pattern-based**: Spikes, surges

### Anomaly Types
- `price_surge`, `price_drop`
- `volume_surge`
- `volatility_spike`
- `gap_up`, `gap_down`

---

## PSXNewsAgent

### Purpose
Fetches and stores news articles related to PSX.

### Location
```
psx_news_agent/
├── agent.py
└── __init__.py
```

### Key Methods

#### `fetch_news()`
```python
def fetch_news(
    self,
    hours_back: int = 24
) -> List[Dict[str, Any]]:
    """Fetch news articles."""
```

#### `search_news()`
```python
def search_news(
    self,
    query: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Search news articles."""
```

### Output Structure
```python
{
    "id": "news_12345",
    "title": "OGDC announces 20% increase in profits",
    "source": "Business Recorder",
    "published_at": "2026-02-16T10:30:00",
    "symbols_mentioned": ["OGDC", "PPL"],
    "sentiment": {
        "score": 0.75,  # -1 to 1
        "label": "positive"
    }
}
```

### News Sources
- Business Recorder (RSS)
- Dawn Business (RSS)
- The News International (RSS)
- Express Tribune (RSS)

---

## PSXNewsPriceCorrelator

### Purpose
Correlates news events with price anomalies.

### Location
```
psx_news_price_correlator/
├── correlator.py
└── __init__.py
```

### Key Method: `correlate_anomalies()`

```python
def correlate_anomalies(
    self,
    anomalies: List[Dict[str, Any]],
    time_window_hours: int = 24
) -> List[Dict[str, Any]]:
    """Correlate anomalies with news."""
```

### Output Structure
```python
{
    "symbol": "OGDC",
    "anomaly": {
        "type": "price_surge",
        "severity": 0.85
    },
    "correlated_news": [
        {
            "title": "OGDC announces earnings beat",
            "causality_score": 0.92,  # 0-1
            "reasoning": [
                "News 2.5h before price surge",
                "Positive sentiment matches price increase"
            ]
        }
    ],
    "correlation_summary": {
        "likely_cause": True,
        "confidence": 0.92
    }
}
```

### Correlation Algorithm
1. **Temporal Matching**: News within 24h window before anomaly
2. **Symbol Matching**: News mentions symbol
3. **Sentiment Matching**: Sentiment aligns with price direction
4. **Causality Scoring**: Combined score 0-1

---

## PSXPortfolioAgent

### Purpose
Manages portfolio positions and tracks P&L.

### Location
```
psx_portfolio_agent/
├── agent.py
└── __init__.py
```

### Key Methods

#### `add_position()`
```python
def add_position(
    self,
    symbol: str,
    quantity: int,
    entry_price: float
) -> str:
    """Add position. Returns position_id."""
```

#### `close_position()`
```python
def close_position(
    self,
    position_id: str,
    exit_price: float
) -> Dict[str, Any]:
    """Close position. Returns P&L details."""
```

#### `get_pnl()`
```python
def get_pnl(
    self,
    portfolio_id: str = "default"
) -> Dict[str, Any]:
    """Calculate portfolio P&L."""
```

### Output Structure
```python
{
    "portfolio_id": "default",
    "summary": {
        "total_value": 1500000,
        "total_pnl": 125000,
        "total_pnl_pct": 12.5,
        "realized_pnl": 85000,
        "unrealized_pnl": 40000
    },
    "open_positions": [
        {
            "symbol": "OGDC",
            "quantity": 1000,
            "entry_price": 125.50,
            "current_price": 135.75,
            "unrealized_pnl": 10250,
            "unrealized_pnl_pct": 8.17
        }
    ],
    "allocation": {
        "by_sector": {"Energy": 45.0, "Banking": 30.0},
        "by_symbol": {"OGDC": 22.5, "HBL": 30.0}
    }
}
```

### Database Schema
```sql
CREATE TABLE portfolios (
    portfolio_id TEXT PRIMARY KEY,
    name TEXT,
    initial_cash REAL,
    current_cash REAL
);

CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    portfolio_id TEXT,
    symbol TEXT,
    quantity INTEGER,
    entry_price REAL,
    entry_date DATE,
    exit_price REAL,
    exit_date DATE,
    status TEXT
);
```

---

## PSXRiskAgent

### Purpose
Validates trades and monitors portfolio risk.

### Location
```
psx_risk_agent/
├── agent.py
└── __init__.py
```

### Key Methods

#### `validate_trade()`
```python
def validate_trade(
    self,
    symbol: str,
    quantity: int,
    entry_price: float
) -> Dict[str, Any]:
    """Validate trade. Returns approval status."""
```

#### `check_portfolio_risk()`
```python
def check_portfolio_risk(
    self,
    portfolio_id: str = "default"
) -> Dict[str, Any]:
    """Check portfolio risk metrics."""
```

### Validation Output
```python
{
    "approved": False,
    "violations": [
        {
            "rule": "max_position_size",
            "limit": 100000,
            "proposed": 125500,
            "severity": "critical"
        }
    ],
    "reason": "Trade exceeds max position size"
}
```

### Risk Rules
```python
RISK_RULES = {
    "max_risk_per_trade": 0.02,      # 2% of portfolio
    "max_position_size": 0.10,       # 10% in single position
    "max_sector_allocation": 0.50,   # 50% in single sector
    "min_reward_to_risk": 2.0,       # 2:1 ratio
    "min_cash_reserve": 0.20         # 20% cash
}
```

### Portfolio Risk Output
```python
{
    "risk_level": "medium",
    "metrics": {
        "total_exposure": 1000000,
        "concentration": {
            "max_position_pct": 30.0,
            "herfindahl_index": 0.28
        },
        "volatility": {
            "portfolio_std_dev": 0.15,
            "sharpe_ratio": 1.2
        },
        "var": {
            "var_95": -25000,
            "var_99": -38000
        }
    },
    "violations": [],
    "recommendations": [
        "Consider diversifying: Energy sector is 45%"
    ]
}
```

---

## Agent Integration Matrix

### Data Flow

```
Liquidity Screener
    ↓ (symbols)
Price Store ← fetch prices
    ↓ (price data)
    ├→ Technical Agent
    ├→ Fundamental Agent
    └→ Anomaly Agent
         ↓ (anomalies)
    Correlator ← News Agent
         ↓ (correlations)
      Reporting

Portfolio Agent ← Risk Agent (validation)
    ↓ (positions)
Risk Agent (monitoring)
```

### Event Flow

**Data Collection Events:**
- `stocks_screened` → Liquidity
- `price_data_updated` → Price Store
- `news_fetched`, `news_published` → News

**Analysis Events:**
- `technical_analysis_complete` → Technical
- `fundamental_analysis_complete` → Fundamental
- `anomaly_detected`, `high_severity_anomaly` → Anomaly
- `news_correlation_complete` → Correlator

**Portfolio & Risk Events:**
- `position_opened`, `position_closed` → Portfolio
- `portfolio_updated` → Portfolio
- `risk_violation`, `risk_check_complete` → Risk

### Workflow Integration

**Daily Analysis:**
```
1. Liquidity.screen_stocks()
2. PriceStore.update_prices(symbols)
3. [Parallel] Technical.analyze_symbol() × N
4. [Parallel] Anomaly.detect_anomalies() × N
5. News.fetch_news()
6. Correlator.correlate_anomalies()
```

**Validated Trade:**
```
1. Risk.validate_trade()
2. If approved:
   - Portfolio.add_position()
   - Risk.check_portfolio_risk()
3. If rejected:
   - Emit risk_violation event
```

---

## Summary

The 9-agent ecosystem provides:

✅ **Comprehensive Market Analysis**
- Liquidity screening
- Price data management
- Technical & fundamental analysis
- Anomaly detection
- News correlation

✅ **Integrated Risk Management**
- Pre-trade validation
- Portfolio risk monitoring
- Risk limit enforcement

✅ **Event-Driven Architecture**
- Loose coupling via events
- Automatic workflow triggers
- Complete audit trail

✅ **Backward Compatible**
- No agent modifications required
- Works with existing agents
- Gradual enhancement path

---

**Next**: See [04_WORKFLOW_TEMPLATES_GUIDE.md](04_WORKFLOW_TEMPLATES_GUIDE.md) for workflow definitions.
