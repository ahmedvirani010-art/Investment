# Workflow Templates Guide

## Table of Contents

1. [Overview](#overview)
2. [Workflow Structure](#workflow-structure)
3. [Daily Analysis Workflow](#daily-analysis-workflow)
4. [Validated Trade Execution Workflow](#validated-trade-execution-workflow)
5. [High Severity Investigation Workflow](#high-severity-investigation-workflow)
6. [Portfolio Risk Check Workflow](#portfolio-risk-check-workflow)
7. [News Impact Analysis Workflow](#news-impact-analysis-workflow)
8. [Custom Workflows](#custom-workflows)
9. [Best Practices](#best-practices)

---

## Overview

Workflow templates define reusable analysis and trading patterns. Each workflow is a **DAG (Directed Acyclic Graph)** of tasks with dependencies.

### Available Workflows

| Workflow | Purpose | Trigger | Duration |
|----------|---------|---------|----------|
| **daily_analysis** | Complete market analysis | Manual/Scheduled | ~60s |
| **validated_trade_execution** | Execute trade with risk validation | Manual | ~5s |
| **high_severity_investigation** | Investigate anomalies | Event-driven | ~30s |
| **portfolio_risk_check** | Monitor portfolio risk | Event/Scheduled | ~10s |
| **news_impact_analysis** | Analyze news impact | Event-driven | ~20s |

---

## Workflow Structure

### WorkflowDefinition

```python
@dataclass
class WorkflowDefinition:
    name: str                          # Unique workflow name
    description: str                   # Human-readable description
    tasks: List[Task]                  # List of tasks
    saga_enabled: bool = False         # Enable saga pattern
    timeout_seconds: Optional[int] = None  # Workflow timeout
```

### Task Definition

```python
@dataclass
class Task:
    name: str                          # Unique task name
    agent: str                         # Agent identifier
    method: str                        # Method to call
    parameters: Dict[str, Any]         # Method parameters
    depends_on: List[str] = []         # Task dependencies
    condition: Optional[str] = None    # Conditional execution
    retry_config: Optional[RetryConfig] = None
    cache_key: Optional[str] = None
    compensation: Optional[Compensation] = None  # Saga
```

### Parameter Substitution

Use `${variable}` syntax to reference previous task outputs:

```python
parameters={
    "symbols": "${select_stocks.output}",  # Output from select_stocks
    "symbol": "${symbol}",                 # Loop variable
    "date": "${workflow.date}"             # Workflow context
}
```

---

## Daily Analysis Workflow

### Purpose
Complete daily market analysis for liquid PSX stocks.

### Workflow Definition

```python
daily_analysis = WorkflowDefinition(
    name="daily_analysis",
    description="Complete daily market analysis",
    tasks=[
        Task(
            name="select_stocks",
            agent="liquidity",
            method="screen_stocks",
            parameters={
                "min_volume": 500000,
                "min_price": 20.0
            },
            cache_key="stocks:${date}"
        ),
        Task(
            name="sync_prices",
            agent="price_store",
            method="update_prices",
            parameters={
                "symbols": "${select_stocks.output}",
                "period": "1mo"
            },
            depends_on=["select_stocks"],
            retry_config=RetryConfig(max_attempts=5)
        ),
        Task(
            name="fetch_news",
            agent="news",
            method="fetch_news",
            parameters={"hours_back": 24},
            depends_on=["select_stocks"],
            cache_key="news:${date}"
        ),
        Task(
            name="technical_analysis",
            agent="technical",
            method="analyze_symbol",
            parameters={"symbol": "${symbol}"},
            depends_on=["sync_prices"],
            cache_key="technical:${symbol}:${date}",
            # This task runs in parallel for each symbol
        ),
        Task(
            name="anomaly_detection",
            agent="anomaly",
            method="detect_anomalies",
            parameters={"symbol": "${symbol}"},
            depends_on=["technical_analysis"],
            cache_key="anomaly:${symbol}:${date}"
        ),
        Task(
            name="news_correlation",
            agent="correlator",
            method="correlate_anomalies",
            parameters={
                "anomalies": "${anomaly_detection.output}"
            },
            depends_on=["anomaly_detection", "fetch_news"]
        )
    ]
)
```

### Execution Flow

```
select_stocks (10s)
    ↓
sync_prices (30s)
    ↓
┌───────┴───────┬───────┬───────┐
↓               ↓       ↓       ↓
tech₁ (15s)   tech₂   tech₃   tech₄  [Parallel - 4 workers]
↓               ↓       ↓       ↓
anom₁ (8s)    anom₂   anom₃   anom₄   [Parallel]
└───────┬───────┴───────┴───────┘
        ↓
news_correlation (10s)
        ↓
    Report Generated

Total: ~60s (with parallelism)
Sequential would be: ~180s
```

### Usage

```python
# Run daily analysis
result = orchestrator.run_daily_analysis(
    min_volume=500000,
    min_price=20.0
)

print(f"Analyzed {len(result.data['symbols'])} stocks")
print(f"Found {len(result.data['anomalies'])} anomalies")
```

---

## Validated Trade Execution Workflow

### Purpose
Execute trades with pre-trade risk validation and saga rollback.

### Workflow Definition

```python
validated_trade = WorkflowDefinition(
    name="validated_trade_execution",
    description="Execute trade with risk validation",
    saga_enabled=True,  # Enable compensations
    tasks=[
        Task(
            name="validate_risk",
            agent="risk",
            method="validate_trade",
            parameters={
                "symbol": "${trade.symbol}",
                "quantity": "${trade.quantity}",
                "entry_price": "${trade.entry_price}"
            }
        ),
        Task(
            name="reserve_cash",
            agent="portfolio",
            method="reserve_cash",
            parameters={
                "amount": "${trade.total_value}"
            },
            depends_on=["validate_risk"],
            condition="${validate_risk.approved} == True",
            compensation=Compensation(
                method="release_cash",
                parameters={"amount": "${trade.total_value}"}
            )
        ),
        Task(
            name="add_position",
            agent="portfolio",
            method="add_position",
            parameters={
                "symbol": "${trade.symbol}",
                "quantity": "${trade.quantity}",
                "entry_price": "${trade.entry_price}"
            },
            depends_on=["reserve_cash"],
            compensation=Compensation(
                method="remove_position",
                parameters={"position_id": "${add_position.position_id}"}
            )
        ),
        Task(
            name="update_portfolio",
            agent="portfolio",
            method="calculate_metrics",
            parameters={"portfolio_id": "default"},
            depends_on=["add_position"],
            compensation=Compensation(
                method="revert_metrics",
                parameters={"snapshot_id": "${update_portfolio.snapshot_id}"}
            )
        ),
        Task(
            name="check_post_trade_risk",
            agent="risk",
            method="check_portfolio_risk",
            parameters={"portfolio_id": "default"},
            depends_on=["update_portfolio"]
        )
    ]
)
```

### Saga Pattern

If any task fails, compensating actions execute in reverse:

```
Success Path:
  validate_risk → reserve_cash → add_position → update_portfolio → check_risk
  
Failure at update_portfolio:
  1. Compensate add_position → remove_position
  2. Compensate reserve_cash → release_cash
  3. Log failure
  4. Emit risk_violation event
```

### Usage

```python
# Execute trade with validation
result = orchestrator.run_workflow(
    "validated_trade_execution",
    parameters={
        "trade": {
            "symbol": "OGDC",
            "quantity": 1000,
            "entry_price": 125.50
        }
    }
)

if result.status == "completed":
    print(f"Trade executed: {result.data['position_id']}")
else:
    print(f"Trade blocked: {result.error}")
```

---

## High Severity Investigation Workflow

### Purpose
Automatically investigate high-severity anomalies with deep analysis.

### Workflow Definition

```python
investigation = WorkflowDefinition(
    name="high_severity_investigation",
    description="Investigate high-severity anomalies",
    tasks=[
        Task(
            name="fetch_detailed_prices",
            agent="price_store",
            method="get_prices",
            parameters={
                "symbol": "${anomaly.symbol}",
                "lookback_days": 90
            }
        ),
        Task(
            name="technical_deep_dive",
            agent="technical",
            method="analyze_symbol",
            parameters={
                "symbol": "${anomaly.symbol}",
                "period": "3mo"
            },
            depends_on=["fetch_detailed_prices"]
        ),
        Task(
            name="search_related_news",
            agent="news",
            method="search_news",
            parameters={
                "query": "${anomaly.symbol}",
                "days_back": 7
            }
        ),
        Task(
            name="correlate_events",
            agent="correlator",
            method="correlate_anomalies",
            parameters={
                "anomalies": ["${anomaly}"],
                "time_window_hours": 48
            },
            depends_on=["search_related_news"]
        ),
        Task(
            name="generate_report",
            agent="reporting",
            method="create_investigation_report",
            parameters={
                "anomaly": "${anomaly}",
                "technical": "${technical_deep_dive.output}",
                "correlation": "${correlate_events.output}"
            },
            depends_on=["technical_deep_dive", "correlate_events"]
        )
    ]
)
```

### Event Trigger

```python
# Auto-trigger on high-severity anomalies
event_bus.subscribe(
    EventType.HIGH_SEVERITY_ANOMALY,
    lambda event: orchestrator.run_workflow(
        "high_severity_investigation",
        parameters={"anomaly": event.data}
    )
)
```

### Usage

```python
# Manually trigger investigation
result = orchestrator.run_workflow(
    "high_severity_investigation",
    parameters={
        "anomaly": {
            "symbol": "OGDC",
            "type": "price_surge",
            "severity": 0.95
        }
    }
)
```

---

## Portfolio Risk Check Workflow

### Purpose
Monitor portfolio risk metrics and detect violations.

### Workflow Definition

```python
risk_check = WorkflowDefinition(
    name="portfolio_risk_check",
    description="Check portfolio risk metrics",
    tasks=[
        Task(
            name="calculate_pnl",
            agent="portfolio",
            method="get_pnl",
            parameters={"portfolio_id": "default"}
        ),
        Task(
            name="check_risk_metrics",
            agent="risk",
            method="check_portfolio_risk",
            parameters={"portfolio_id": "default"},
            depends_on=["calculate_pnl"]
        ),
        Task(
            name="check_position_limits",
            agent="risk",
            method="check_position_limits",
            parameters={"portfolio_id": "default"},
            depends_on=["calculate_pnl"]
        ),
        Task(
            name="alert_if_violations",
            agent="notification",
            method="send_alert",
            parameters={
                "violations": "${check_risk_metrics.violations}"
            },
            depends_on=["check_risk_metrics", "check_position_limits"],
            condition="len(${check_risk_metrics.violations}) > 0"
        )
    ]
)
```

### Scheduled Execution

```python
# Run every hour during market hours
scheduler.schedule(
    workflow="portfolio_risk_check",
    cron="0 9-16 * * 1-5"  # 9 AM - 4 PM, Mon-Fri
)
```

---

## News Impact Analysis Workflow

### Purpose
Analyze the impact of news on stock prices.

### Workflow Definition

```python
news_impact = WorkflowDefinition(
    name="news_impact_analysis",
    description="Analyze news impact on prices",
    tasks=[
        Task(
            name="get_recent_news",
            agent="news",
            method="fetch_news",
            parameters={"hours_back": 24}
        ),
        Task(
            name="extract_symbols",
            agent="news",
            method="extract_mentioned_symbols",
            parameters={"articles": "${get_recent_news.output}"},
            depends_on=["get_recent_news"]
        ),
        Task(
            name="check_price_movements",
            agent="anomaly",
            method="detect_anomalies",
            parameters={
                "symbol": "${symbol}",
                "lookback_days": 1
            },
            depends_on=["extract_symbols"]
        ),
        Task(
            name="correlate_news_price",
            agent="correlator",
            method="correlate_anomalies",
            parameters={
                "anomalies": "${check_price_movements.output}",
                "time_window_hours": 24
            },
            depends_on=["check_price_movements"]
        )
    ]
)
```

### Event Trigger

```python
# Trigger when news published
event_bus.subscribe(
    EventType.NEWS_PUBLISHED,
    lambda event: orchestrator.run_workflow("news_impact_analysis")
)
```

---

## Custom Workflows

### Creating Custom Workflows

```python
# Define custom workflow
custom_workflow = WorkflowDefinition(
    name="custom_energy_sector_analysis",
    description="Analyze energy sector stocks",
    tasks=[
        Task(
            name="filter_energy_stocks",
            agent="liquidity",
            method="screen_stocks",
            parameters={
                "min_volume": 500000,
                "sector": "Energy"
            }
        ),
        Task(
            name="analyze_fundamentals",
            agent="fundamental",
            method="analyze_fundamentals",
            parameters={"symbol": "${symbol}"},
            depends_on=["filter_energy_stocks"]
        ),
        Task(
            name="sector_comparison",
            agent="fundamental",
            method="compare_sector_metrics",
            parameters={
                "symbols": "${filter_energy_stocks.output}",
                "metrics": "${analyze_fundamentals.output}"
            },
            depends_on=["analyze_fundamentals"]
        )
    ]
)

# Execute custom workflow
result = orchestrator.execute_custom_workflow(
    custom_workflow,
    parameters={}
)
```

### Conditional Tasks

```python
Task(
    name="send_buy_alert",
    agent="notification",
    method="send_alert",
    parameters={"message": "Buy signal detected"},
    depends_on=["technical_analysis"],
    condition="${technical_analysis.signal} == 'buy'"
)
```

### Parameterized Tasks

```python
Task(
    name="analyze_with_params",
    agent="technical",
    method="analyze_symbol",
    parameters={
        "symbol": "${symbol}",
        "period": "${workflow.params.period}",  # From workflow parameters
        "indicators": "${workflow.params.indicators}"
    }
)
```

---

## Best Practices

### 1. Use Caching Strategically

```python
Task(
    name="fetch_news",
    agent="news",
    method="fetch_news",
    cache_key="news:${date}",  # Cache by date
    # News doesn't change much within a day
)

Task(
    name="analyze_technical",
    agent="technical",
    method="analyze_symbol",
    cache_key="technical:${symbol}:${date}:${period}",
    # Cache per symbol, date, and period
)
```

### 2. Handle Errors with Retry

```python
Task(
    name="sync_prices",
    agent="price_store",
    method="update_prices",
    retry_config=RetryConfig(
        max_attempts=5,
        backoff_multiplier=2.0,
        retryable_exceptions=[ConnectionError, TimeoutError]
    )
)
```

### 3. Use Saga for Transactional Workflows

```python
# Always use saga for workflows that modify state
WorkflowDefinition(
    name="trade_execution",
    saga_enabled=True,  # Enable rollback
    tasks=[...]
)
```

### 4. Leverage Parallelism

```python
# These tasks can run in parallel (no dependencies)
Task(name="task1", depends_on=[]),
Task(name="task2", depends_on=[]),
Task(name="task3", depends_on=[]),
# Coordinator will execute all 3 in parallel
```

### 5. Set Timeouts

```python
WorkflowDefinition(
    name="daily_analysis",
    timeout_seconds=300,  # Fail if takes > 5 minutes
    tasks=[...]
)
```

### 6. Use Descriptive Names

```python
# Good
Task(name="fetch_energy_sector_news", ...)

# Bad
Task(name="task1", ...)
```

### 7. Document Dependencies

```python
Task(
    name="correlate_news",
    depends_on=[
        "fetch_news",        # Needs news data
        "detect_anomalies"   # Needs anomalies to correlate
    ]
)
```

---

## Workflow Execution Patterns

### Sequential Execution

```python
tasks=[
    Task(name="step1", depends_on=[]),
    Task(name="step2", depends_on=["step1"]),
    Task(name="step3", depends_on=["step2"]),
]
# Executes: step1 → step2 → step3
```

### Parallel Execution

```python
tasks=[
    Task(name="parallel1", depends_on=["init"]),
    Task(name="parallel2", depends_on=["init"]),
    Task(name="parallel3", depends_on=["init"]),
    Task(name="aggregate", depends_on=["parallel1", "parallel2", "parallel3"])
]
# Executes: init → [parallel1, parallel2, parallel3] → aggregate
```

### Fan-out/Fan-in

```python
tasks=[
    Task(name="source", depends_on=[]),
    # Fan-out
    Task(name="process1", depends_on=["source"]),
    Task(name="process2", depends_on=["source"]),
    Task(name="process3", depends_on=["source"]),
    # Fan-in
    Task(name="combine", depends_on=["process1", "process2", "process3"])
]
```

---

## Summary

Workflow templates provide:

✅ **Reusable Patterns** - Pre-defined workflows for common tasks
✅ **Flexible Execution** - Sequential, parallel, conditional
✅ **Error Handling** - Retry, saga, compensation
✅ **Caching** - Avoid redundant computation
✅ **Event-Driven** - Auto-trigger on events
✅ **Custom Workflows** - Define your own patterns

**Key Workflows:**
- `daily_analysis` - Complete market analysis (~60s)
- `validated_trade_execution` - Trade with risk validation (~5s)
- `high_severity_investigation` - Deep anomaly analysis (~30s)
- `portfolio_risk_check` - Risk monitoring (~10s)
- `news_impact_analysis` - News-price correlation (~20s)

---

**Next**: See [05_API_REFERENCE.md](05_API_REFERENCE.md) for complete API documentation.
