# Database Schema

## Overview

The orchestration system uses **SQLite** for state persistence and data storage. The database schema includes tables for workflow state, price data, news, portfolios, and risk management.

**Database File:** `data/psx_data.db`

---

## Orchestration Tables

### workflow_state

Stores workflow execution state for resumability.

```sql
CREATE TABLE workflow_state (
    workflow_id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- RUNNING, COMPLETED, FAILED, PAUSED
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    parameters TEXT,  -- JSON
    error TEXT,
    INDEX idx_workflow_name (workflow_name),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

### task_results

Stores individual task execution results.

```sql
CREATE TABLE task_results (
    task_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- PENDING, RUNNING, COMPLETED, FAILED
    result TEXT,  -- JSON
    error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (workflow_id) REFERENCES workflow_state(workflow_id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_task_name (task_name)
);
```

### workflow_events

Stores workflow-related events for auditing.

```sql
CREATE TABLE workflow_events (
    event_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT,  -- JSON
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflow_state(workflow_id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_timestamp (timestamp)
);
```

---

## Data Tables

### price_data

Stores historical OHLCV price data.

```sql
CREATE TABLE price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date),
    INDEX idx_symbol (symbol),
    INDEX idx_date (date),
    INDEX idx_symbol_date (symbol, date)
);
```

### news_articles

Stores news articles from various sources.

```sql
CREATE TABLE news_articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    source TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMP NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    symbols_mentioned TEXT,  -- JSON array
    sentiment_score REAL,
    sentiment_label TEXT,
    INDEX idx_published_at (published_at),
    INDEX idx_source (source)
);
```

### anomalies

Stores detected price/volume anomalies.

```sql
CREATE TABLE anomalies (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    anomaly_type TEXT NOT NULL,  -- price_surge, volume_surge, etc.
    severity REAL NOT NULL,  -- 0-1
    description TEXT,
    metrics TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_date (date),
    INDEX idx_severity (severity)
);
```

---

## Portfolio Tables

### portfolios

Stores portfolio metadata.

```sql
CREATE TABLE portfolios (
    portfolio_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    initial_cash REAL NOT NULL,
    current_cash REAL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### positions

Stores portfolio positions (open and closed).

```sql
CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_date DATE NOT NULL,
    exit_price REAL,
    exit_date DATE,
    status TEXT NOT NULL,  -- open, closed
    realized_pnl REAL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    INDEX idx_portfolio (portfolio_id),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status)
);
```

---

## Risk Tables

### risk_settings

Stores risk management configuration.

```sql
CREATE TABLE risk_settings (
    setting_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_value REAL NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    UNIQUE(portfolio_id, rule_name)
);
```

### risk_violations

Stores risk rule violations for auditing.

```sql
CREATE TABLE risk_violations (
    violation_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    severity TEXT NOT NULL,  -- low, medium, high, critical
    message TEXT,
    violated_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    INDEX idx_portfolio (portfolio_id),
    INDEX idx_violated_at (violated_at)
);
```

---

## Indexes for Performance

```sql
-- Price data queries
CREATE INDEX idx_price_symbol_date ON price_data(symbol, date DESC);

-- News queries
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_symbols ON news_articles(symbols_mentioned);

-- Anomaly queries
CREATE INDEX idx_anomaly_severity ON anomalies(severity DESC, date DESC);

-- Workflow queries
CREATE INDEX idx_workflow_status_created ON workflow_state(status, created_at DESC);

-- Portfolio queries
CREATE INDEX idx_positions_portfolio_status ON positions(portfolio_id, status);
```

---

## Sample Queries

### Get Recent Workflow Executions

```sql
SELECT 
    workflow_id,
    workflow_name,
    status,
    created_at,
    julianday(updated_at) - julianday(created_at) as duration_days
FROM workflow_state
WHERE created_at >= date('now', '-7 days')
ORDER BY created_at DESC;
```

### Get Price Data for Symbol

```sql
SELECT date, open, high, low, close, volume
FROM price_data
WHERE symbol = 'OGDC'
  AND date >= date('now', '-30 days')
ORDER BY date DESC;
```

### Get High-Severity Anomalies

```sql
SELECT a.*, p.close as price
FROM anomalies a
JOIN price_data p ON a.symbol = p.symbol AND a.date = p.date
WHERE a.severity > 0.8
  AND a.date >= date('now', '-7 days')
ORDER BY a.severity DESC, a.date DESC;
```

### Get Portfolio P&L

```sql
SELECT 
    p.symbol,
    p.quantity,
    p.entry_price,
    pd.close as current_price,
    (pd.close - p.entry_price) * p.quantity as unrealized_pnl,
    ((pd.close - p.entry_price) / p.entry_price) * 100 as return_pct
FROM positions p
JOIN price_data pd ON p.symbol = pd.symbol
WHERE p.portfolio_id = 'default'
  AND p.status = 'open'
  AND pd.date = (SELECT MAX(date) FROM price_data WHERE symbol = p.symbol);
```

---

## Database Maintenance

### Cleanup Old Data

```sql
-- Delete workflow state older than 90 days
DELETE FROM workflow_state
WHERE created_at < date('now', '-90 days');

-- Delete task results for deleted workflows
DELETE FROM task_results
WHERE workflow_id NOT IN (SELECT workflow_id FROM workflow_state);

-- Vacuum database to reclaim space
VACUUM;
```

### Optimize Indexes

```sql
-- Analyze tables for query optimization
ANALYZE;

-- Rebuild indexes if needed
REINDEX;
```

---

**Next**: See [EVENT_CATALOG.md](EVENT_CATALOG.md) for complete event reference.
