# Event Catalog

## Overview

Complete reference of all events in the PSX orchestration system.

---

## Event Types

### Data Events

#### `PRICE_DATA_UPDATED`
Emitted when price data is fetched and stored.

**Source:** `PSXPriceStore`

**Data:**
```python
{
    "symbols": ["OGDC", "PPL", "PSO"],
    "count": 3,
    "period": "1mo",
    "rows_inserted": 66
}
```

**Triggered By:** `PSXPriceStore.update_prices()`

**Common Subscribers:** Technical Agent, Anomaly Agent

---

#### `NEWS_FETCHED`
Emitted when news articles are fetched.

**Source:** `PSXNewsAgent`

**Data:**
```python
{
    "articles_count": 15,
    "sources": ["Business Recorder", "Dawn"],
    "time_range": "24h"
}
```

**Triggered By:** `PSXNewsAgent.fetch_news()`

**Common Subscribers:** Correlator

---

#### `NEWS_PUBLISHED`
Emitted when a new article is detected.

**Source:** `PSXNewsAgent`

**Data:**
```python
{
    "article_id": "news_12345",
    "title": "OGDC announces earnings",
    "symbols_mentioned": ["OGDC"],
    "sentiment": {"score": 0.75, "label": "positive"}
}
```

**Triggered By:** `PSXNewsAgent.fetch_news()` (new article detected)

**Common Subscribers:** News Impact Workflow

---

### Analysis Events

#### `TECHNICAL_ANALYSIS_COMPLETE`
Emitted after technical analysis completes.

**Source:** `PSXTechnicalAgent`

**Data:**
```python
{
    "symbol": "OGDC",
    "trend": "uptrend",
    "rsi": 68.5,
    "signal": "buy",
    "strength": 0.72
}
```

**Triggered By:** `PSXTechnicalAgent.analyze_symbol()`

**Common Subscribers:** Anomaly Agent, Correlator

---

#### `FUNDAMENTAL_ANALYSIS_COMPLETE`
Emitted after fundamental analysis completes.

**Source:** `PSXFundamentalAgent`

**Data:**
```python
{
    "symbol": "OGDC",
    "pe_ratio": 12.5,
    "roe": 15.2,
    "rating": "buy",
    "score": 7.5
}
```

**Triggered By:** `PSXFundamentalAgent.analyze_fundamentals()`

**Common Subscribers:** Correlator

---

#### `ANOMALY_DETECTED`
Emitted when any anomaly is detected.

**Source:** `PSXAnomalyAgent`

**Data:**
```python
{
    "symbol": "OGDC",
    "type": "price_surge",
    "severity": 0.85,
    "description": "Price increased 8.5%, 3.2 std devs above avg",
    "metrics": {
        "price_change": 8.5,
        "z_score": 3.2
    }
}
```

**Triggered By:** `PSXAnomalyAgent.detect_anomalies()`

**Common Subscribers:** Investigation Workflow, Correlator

---

#### `HIGH_SEVERITY_ANOMALY`
Emitted when high-severity anomaly detected (severity > 0.8).

**Source:** `PSXAnomalyAgent`

**Data:**
```python
{
    "symbol": "OGDC",
    "type": "price_surge",
    "severity": 0.92,
    "description": "Extreme price movement detected",
    "recommendation": "investigate"
}
```

**Triggered By:** `PSXAnomalyAgent.detect_anomalies()` (severity > 0.8)

**Common Subscribers:** High-Severity Investigation Workflow

---

#### `NEWS_CORRELATION_COMPLETE`
Emitted after news-price correlation analysis.

**Source:** `PSXNewsPriceCorrelator`

**Data:**
```python
{
    "symbol": "OGDC",
    "anomaly_count": 1,
    "correlated_news_count": 2,
    "causality_score": 0.92,
    "likely_cause": True
}
```

**Triggered By:** `PSXNewsPriceCorrelator.correlate_anomalies()`

**Common Subscribers:** Reporting

---

### Portfolio Events

#### `POSITION_OPENED`
Emitted when a new position is added.

**Source:** `PSXPortfolioAgent`

**Data:**
```python
{
    "position_id": "pos_20260216_001",
    "symbol": "OGDC",
    "quantity": 1000,
    "entry_price": 125.50,
    "total_value": 125500,
    "portfolio_id": "default"
}
```

**Triggered By:** `PSXPortfolioAgent.add_position()`

**Common Subscribers:** Risk Agent, Monitoring

---

#### `POSITION_CLOSED`
Emitted when a position is closed.

**Source:** `PSXPortfolioAgent`

**Data:**
```python
{
    "position_id": "pos_20260216_001",
    "symbol": "OGDC",
    "quantity": 1000,
    "entry_price": 125.50,
    "exit_price": 135.75,
    "realized_pnl": 10250,
    "realized_pnl_pct": 8.17,
    "days_held": 15
}
```

**Triggered By:** `PSXPortfolioAgent.close_position()`

**Common Subscribers:** Risk Agent, Performance Tracking

---

#### `PORTFOLIO_UPDATED`
Emitted when portfolio state changes.

**Source:** `PSXPortfolioAgent`

**Data:**
```python
{
    "portfolio_id": "default",
    "total_value": 1500000,
    "total_pnl": 125000,
    "total_pnl_pct": 12.5,
    "open_positions": 8
}
```

**Triggered By:** Position open/close, P&L calculation

**Common Subscribers:** Risk Check Workflow

---

### Risk Events

#### `RISK_CHECK_COMPLETE`
Emitted after portfolio risk check.

**Source:** `PSXRiskAgent`

**Data:**
```python
{
    "portfolio_id": "default",
    "risk_level": "medium",
    "violations_count": 0,
    "var_95": -25000,
    "portfolio_std_dev": 0.15
}
```

**Triggered By:** `PSXRiskAgent.check_portfolio_risk()`

**Common Subscribers:** Monitoring, Alerts

---

#### `RISK_VIOLATION`
Emitted when risk rule violated.

**Source:** `PSXRiskAgent`

**Data:**
```python
{
    "portfolio_id": "default",
    "violations": [
        {
            "rule": "max_sector_allocation",
            "severity": "critical",
            "message": "Energy sector is 52% (limit: 50%)"
        }
    ],
    "timestamp": "2026-02-16T10:30:00"
}
```

**Triggered By:** `PSXRiskAgent.validate_trade()`, `PSXRiskAgent.check_portfolio_risk()`

**Common Subscribers:** Alert System, Risk Check Workflow

---

#### `RISK_THRESHOLD_EXCEEDED`
Emitted when risk metric exceeds threshold.

**Source:** `PSXRiskAgent`

**Data:**
```python
{
    "portfolio_id": "default",
    "metric": "var_95",
    "value": -55000,
    "threshold": -50000,
    "severity": "high"
}
```

**Triggered By:** `PSXRiskAgent.check_portfolio_risk()`

**Common Subscribers:** Alert System

---

### Workflow Events

#### `WORKFLOW_STARTED`
Emitted when workflow execution starts.

**Source:** `WorkflowCoordinator`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "workflow_name": "daily_analysis",
    "total_tasks": 10,
    "parameters": {"min_volume": 500000}
}
```

**Triggered By:** `WorkflowCoordinator.execute()`

**Common Subscribers:** Monitoring

---

#### `WORKFLOW_COMPLETED`
Emitted when workflow completes successfully.

**Source:** `WorkflowCoordinator`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "workflow_name": "daily_analysis",
    "status": "completed",
    "execution_time": 58.3,
    "completed_tasks": 10,
    "failed_tasks": 0
}
```

**Triggered By:** `WorkflowCoordinator.execute()` (success)

**Common Subscribers:** Monitoring, Logging

---

#### `WORKFLOW_FAILED`
Emitted when workflow fails.

**Source:** `WorkflowCoordinator`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "workflow_name": "daily_analysis",
    "status": "failed",
    "failed_task": "sync_prices",
    "error": "ConnectionError: Unable to connect to yfinance",
    "completed_tasks": 3,
    "total_tasks": 10
}
```

**Triggered By:** `WorkflowCoordinator.execute()` (failure)

**Common Subscribers:** Alert System, Error Logging

---

#### `TASK_STARTED`
Emitted when individual task starts.

**Source:** `ExecutionEngine`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "task_name": "technical_analysis",
    "agent": "technical",
    "method": "analyze_symbol",
    "parameters": {"symbol": "OGDC"}
}
```

**Triggered By:** `ExecutionEngine.execute_task()`

**Common Subscribers:** Detailed Monitoring

---

#### `TASK_COMPLETED`
Emitted when task completes.

**Source:** `ExecutionEngine`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "task_name": "technical_analysis",
    "status": "success",
    "execution_time": 2.3,
    "cached": False
}
```

**Triggered By:** `ExecutionEngine.execute_task()` (success)

**Common Subscribers:** Performance Monitoring

---

#### `TASK_FAILED`
Emitted when task fails.

**Source:** `ExecutionEngine`

**Data:**
```python
{
    "workflow_id": "wf_20260216_123456",
    "task_name": "sync_prices",
    "error": "ConnectionError",
    "retry_count": 3,
    "will_retry": False
}
```

**Triggered By:** `ExecutionEngine.execute_task()` (failure)

**Common Subscribers:** Error Logging

---

## Event Subscription Examples

### Subscribe to Specific Event

```python
def handle_anomaly(event):
    print(f"Anomaly: {event.data['symbol']} - {event.data['type']}")

event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    handle_anomaly
)
```

### Subscribe to Multiple Events

```python
def handle_portfolio_changes(event):
    if event.type == EventType.POSITION_OPENED:
        print(f"Opened: {event.data['symbol']}")
    elif event.type == EventType.POSITION_CLOSED:
        print(f"Closed: {event.data['symbol']}")

event_bus.subscribe(EventType.POSITION_OPENED, handle_portfolio_changes)
event_bus.subscribe(EventType.POSITION_CLOSED, handle_portfolio_changes)
```

### Wildcard Subscription

```python
def log_all_events(event):
    print(f"[{event.timestamp}] {event.type} from {event.source}")

event_bus.subscribe_wildcard(log_all_events)
```

---

## Event Chains

### Daily Analysis Event Chain

```
WORKFLOW_STARTED (daily_analysis)
  → TASK_STARTED (select_stocks)
  → TASK_COMPLETED (select_stocks)
  → TASK_STARTED (sync_prices)
  → PRICE_DATA_UPDATED
  → TASK_COMPLETED (sync_prices)
  → TASK_STARTED (technical_analysis)
  → TECHNICAL_ANALYSIS_COMPLETE
  → TASK_COMPLETED (technical_analysis)
  → TASK_STARTED (anomaly_detection)
  → ANOMALY_DETECTED (multiple)
  → HIGH_SEVERITY_ANOMALY (if severity > 0.8)
  → TASK_COMPLETED (anomaly_detection)
  → NEWS_CORRELATION_COMPLETE
  → WORKFLOW_COMPLETED
```

### Trade Execution Event Chain

```
WORKFLOW_STARTED (validated_trade_execution)
  → TASK_STARTED (validate_risk)
  → RISK_CHECK_COMPLETE
  → TASK_COMPLETED (validate_risk)
  → TASK_STARTED (add_position)
  → POSITION_OPENED
  → TASK_COMPLETED (add_position)
  → PORTFOLIO_UPDATED
  → TASK_STARTED (check_post_trade_risk)
  → RISK_CHECK_COMPLETE
  → TASK_COMPLETED (check_post_trade_risk)
  → WORKFLOW_COMPLETED
```

---

**Next**: See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for architectural decisions.
