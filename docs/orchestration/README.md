# PSX Orchestration Agent Documentation

## Overview

This documentation covers the comprehensive orchestration system for the PSX (Pakistan Stock Exchange) Investment Intelligence Platform. The orchestration framework coordinates **9 specialized agents** through an event-driven architecture, providing market intelligence, trade execution, portfolio management, and risk compliance.

### What is the Orchestration Agent?

The PSX Orchestration Agent is an intelligent coordinator that transforms the platform from a sequential pipeline into a dynamic, event-driven system with:

- **Smart Workflow Routing**: Conditional execution based on analysis results
- **Parallel Execution**: 3x faster analysis through concurrent task processing
- **Event-Driven Triggers**: Automatic workflows triggered by market events
- **State Management**: Persistent workflow state with caching and resumability
- **Risk Management**: Pre-trade validation and continuous risk monitoring
- **Portfolio Tracking**: Real-time position management and P&L calculation

## The 9-Agent Ecosystem

### Market Intelligence Agents (4)

1. **PSXLiquidityScreener** - Identifies liquid stocks for trading based on volume and turnover metrics
2. **PSXTechnicalAgent** - Computes technical indicators (RSI, MACD, SMA) and generates signals
3. **PSXFundamentalAgent** - Analyzes financial health, valuation, and growth metrics
4. **PSXAnomalyAgent** - Detects unusual trading patterns using statistical analysis

### Data Management Agents (3)

5. **PSXPriceStore** - Centralized OHLCV price data persistence (SQLite)
6. **PSXNewsAgent** - Collects news from RSS feeds with sentiment analysis
7. **NewsAnomalyCorrelator** - Correlates market anomalies with news events using PSX materiality filtering

### Trading & Risk Agents (2) - NEW

8. **PSXPortfolioAgent** - Manages portfolios, tracks holdings, calculates position sizing and P&L
9. **PSXRiskAgent** - Enforces risk rules, validates trades, monitors portfolio risk metrics

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              PSX Orchestration Agent (Coordinator)             │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Workflow    │  │  Event Bus   │  │    State     │       │
│  │ Coordinator  │  │  (Pub/Sub)   │  │   Manager    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                │
│  ┌────────────────────────────────────────────────────┐       │
│  │           Execution Engine                         │       │
│  │  • Parallel Task Execution (ThreadPool)           │       │
│  │  • Retry Logic & Error Handling                   │       │
│  │  • Resource Management & Rate Limiting            │       │
│  │  • Result Caching (TTL-based)                     │       │
│  └────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│  9 Specialized │◄───────────────────►│   Shared Data   │
│     Agents     │   (Zero changes    │     Stores      │
│                │    required)       │   (SQLite)      │
└────────────────┘                    └─────────────────┘
```

## Core Components

### 1. PSXOrchestrationAgent
Main interface for workflow execution, event management, and agent coordination.

### 2. WorkflowCoordinator
DAG-based workflow execution with dependency resolution and conditional routing.

### 3. EventBus
Pub/sub event system enabling reactive workflows and inter-agent communication.

### 4. StateManager
SQLite-based persistence for workflow state, task execution history, and result caching.

### 5. ExecutionEngine
Parallel task execution with retry logic, resource limits, and performance optimization.

## Documentation Structure

### Getting Started
- **This README** - Overview and navigation
- **[01_ARCHITECTURE_OVERVIEW.md](01_ARCHITECTURE_OVERVIEW.md)** - System architecture, design principles, patterns

### Core Documentation
- **[02_COMPONENT_SPECIFICATIONS.md](02_COMPONENT_SPECIFICATIONS.md)** - Detailed specs for 5 orchestration components
- **[03_AGENT_CATALOG.md](03_AGENT_CATALOG.md)** - Complete reference for all 9 agents
- **[04_WORKFLOW_TEMPLATES_GUIDE.md](04_WORKFLOW_TEMPLATES_GUIDE.md)** - 7 built-in workflows + custom workflow creation
- **[05_API_REFERENCE.md](05_API_REFERENCE.md)** - Complete Python API for all components and agents

### Integration & Implementation
- **[06_INTEGRATION_GUIDE.md](06_INTEGRATION_GUIDE.md)** - How to integrate agents and maintain backward compatibility
- **[07_PORTFOLIO_RISK_MANAGEMENT.md](07_PORTFOLIO_RISK_MANAGEMENT.md)** - Deep dive on Portfolio & Risk agents
- **[08_MIGRATION_GUIDE.md](08_MIGRATION_GUIDE.md)** - 8-week implementation timeline

### Examples & Reference
- **[09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md)** - Real-world usage examples and workflows
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Complete database schema documentation
- **[EVENT_CATALOG.md](EVENT_CATALOG.md)** - All event types with payload specifications
- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** - Architecture decisions and trade-offs
- **[GLOSSARY.md](GLOSSARY.md)** - Terminology and definitions

### Diagrams
- **[diagrams/architecture_overview.md](diagrams/architecture_overview.md)** - System architecture diagram
- **[diagrams/workflow_execution_flow.md](diagrams/workflow_execution_flow.md)** - Workflow execution visualization
- **[diagrams/event_driven_triggers.md](diagrams/event_driven_triggers.md)** - Event flows and triggers
- **[diagrams/state_management.md](diagrams/state_management.md)** - State persistence patterns
- **[diagrams/portfolio_risk_workflows.md](diagrams/portfolio_risk_workflows.md)** - Portfolio & risk event flows

## Quick Start

### For Architects & Decision Makers
1. Read [01_ARCHITECTURE_OVERVIEW.md](01_ARCHITECTURE_OVERVIEW.md) for design principles and patterns
2. Review [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for rationale behind key choices
3. Check [08_MIGRATION_GUIDE.md](08_MIGRATION_GUIDE.md) for implementation timeline

### For Developers
1. Start with [03_AGENT_CATALOG.md](03_AGENT_CATALOG.md) to understand all 9 agents
2. Read [05_API_REFERENCE.md](05_API_REFERENCE.md) for complete API documentation
3. Explore [09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md) for code examples

### For Traders & Portfolio Managers
1. Read [07_PORTFOLIO_RISK_MANAGEMENT.md](07_PORTFOLIO_RISK_MANAGEMENT.md) for portfolio and risk features
2. Review [04_WORKFLOW_TEMPLATES_GUIDE.md](04_WORKFLOW_TEMPLATES_GUIDE.md) for trading workflows
3. Check [09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md) for portfolio management examples

## Key Features

### Event-Driven Workflows

Workflows trigger automatically based on market events:

```python
# Example: High-severity anomaly → automatic investigation
on_event("high_severity_anomaly", trigger_workflow("investigation"))
```

### Validated Trade Execution

Every trade goes through risk validation before execution:

```
Trade Plan Created → Risk Validation → Position Sizing → Execution → Portfolio Tracking
```

### Real-Time Risk Monitoring

Continuous monitoring with automatic alerts:

```python
# Portfolio risk exceeds threshold → automatic position reduction
on_event("risk_threshold_exceeded", trigger_workflow("reduce_positions"))
```

### Parallel Analysis

Analyze 30 stocks in parallel (3x faster than sequential):

```python
# Sequential: 180 seconds (6s × 30)
# Parallel: 60 seconds (6s ÷ 4 workers)
```

### Smart Caching

Avoid redundant computations with TTL-based caching:

- Technical indicators: 1 hour
- News fetches: 30 minutes
- Fundamental analysis: 24 hours
- **Result**: ~90 seconds saved per run

## Built-In Workflows

### 1. DailyAnalysisWorkflow
**Purpose**: Standard market intelligence workflow
**Steps**: Stock selection → Price sync → Technical analysis → Anomaly detection → News correlation
**Duration**: ~60 seconds for 30 stocks (with parallelization)

### 2. HighSeverityAnomalyWorkflow
**Purpose**: Investigate unexplained high-severity anomalies
**Triggers**: Anomaly severity = HIGH + correlation < 0.3
**Steps**: Fetch announcements → Fundamental deep dive → Sector peer check → Investigation report

### 3. FundamentalDeepDiveWorkflow
**Purpose**: Comprehensive fundamental analysis (expensive, conditional)
**Triggers**: Unexplained anomaly OR user request
**Steps**: Fetch financials → Full analysis → Technical validation → Recommendation

### 4. SectorAnalysisWorkflow
**Purpose**: Analyze all stocks in a sector
**Triggers**: Multiple anomalies in same sector
**Steps**: Identify sector → Analyze all peers → Correlation analysis → Sector report

### 5. ValidatedTradeExecutionWorkflow ⭐ NEW
**Purpose**: Execute trades with risk validation
**Steps**: Risk validation → Position sizing → Add position → Price updates → Portfolio tracking
**Key Feature**: Blocks execution if risk rules violated

### 6. PortfolioRiskMonitoringWorkflow ⭐ NEW
**Purpose**: Continuous portfolio risk monitoring
**Triggers**: Price updates (every minute or on change)
**Steps**: Update prices → Calculate risk metrics → Check rules → Generate alerts

### 7. PositionClosureWorkflow ⭐ NEW
**Purpose**: Close positions with post-trade analysis
**Steps**: Validate exit → Close position → Calculate P&L → Record analysis → Create snapshot

## Current vs. Orchestrated System

| Feature | Current (Sequential) | Orchestrated (Event-Driven) |
|---------|---------------------|----------------------------|
| **Execution** | Sequential pipeline | Parallel + event-driven |
| **Speed (30 stocks)** | ~180 seconds | ~60 seconds (3x faster) |
| **Flexibility** | Fixed workflow | Dynamic routing |
| **Error Handling** | Fail entire pipeline | Task-level retry + compensation |
| **Caching** | None | TTL-based (90s savings) |
| **Event Triggers** | Manual only | Automatic + manual |
| **Risk Management** | None | Pre-trade validation + monitoring |
| **Portfolio Tracking** | External | Integrated |
| **State Persistence** | None | Full workflow state |

## Integration with TradeBench

The Portfolio and Risk agents align with the TradeBench integration plan:

- **Trade Planning**: Pre-trade checklists with automatic validation
- **Position Sizing**: Risk-based calculation with rule enforcement
- **Open Positions**: Real-time tracking with unrealized P&L
- **Trade Journal**: Automatic post-trade analysis and performance tracking
- **Risk Settings**: Configurable risk rules with violation alerts
- **Performance Metrics**: Win rate, profit factor, drawdown tracking

## FAQ

### Q: Do I need to modify existing agents?
**A:** No. The orchestration uses an adapter pattern, so existing agents work unchanged.

### Q: Can I use the orchestrated system alongside the current pipeline?
**A:** Yes. The migration guide shows how to run both systems in parallel during transition.

### Q: How do I create custom workflows?
**A:** See [04_WORKFLOW_TEMPLATES_GUIDE.md](04_WORKFLOW_TEMPLATES_GUIDE.md) for complete guide.

### Q: What happens if a workflow fails?
**A:** The execution engine implements the Saga pattern with compensating actions for rollback.

### Q: How is state persisted?
**A:** All state (workflows, tasks, cache, portfolios) is stored in SQLite. See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

### Q: Can workflows trigger other workflows?
**A:** Yes. Event-driven triggers enable workflow chaining and feedback loops.

### Q: How do I monitor workflow execution?
**A:** Use the StateManager to query workflow status, task execution history, and performance metrics.

### Q: Is this production-ready?
**A:** This is a comprehensive design specification. Implementation requires 8 weeks (see [08_MIGRATION_GUIDE.md](08_MIGRATION_GUIDE.md)).

## Design Sources

This documentation is based on:

- **Orchestration Framework Design** (Plan agent a209cdc): Core components, event bus, workflow coordinator
- **Portfolio & Risk Agents Design** (Plan agent a5ea09f): Complete PSXPortfolioAgent and PSXRiskAgent specifications
- **TradeBench Integration Plan**: Portfolio management and risk management requirements
- **Existing PSX Platform**: Current 7-agent architecture and integration patterns

## Next Steps

1. **Understand the Architecture**: Read [01_ARCHITECTURE_OVERVIEW.md](01_ARCHITECTURE_OVERVIEW.md)
2. **Learn the Agents**: Review [03_AGENT_CATALOG.md](03_AGENT_CATALOG.md)
3. **Explore the API**: Check [05_API_REFERENCE.md](05_API_REFERENCE.md)
4. **See Examples**: Browse [09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md)
5. **Plan Implementation**: Follow [08_MIGRATION_GUIDE.md](08_MIGRATION_GUIDE.md)

## Contributing

When adding new agents or workflows:

1. Update [03_AGENT_CATALOG.md](03_AGENT_CATALOG.md) with agent specifications
2. Add workflow templates to [04_WORKFLOW_TEMPLATES_GUIDE.md](04_WORKFLOW_TEMPLATES_GUIDE.md)
3. Document events in [EVENT_CATALOG.md](EVENT_CATALOG.md)
4. Update database schema in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
5. Add usage examples to [09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md)

## Version

- **Version**: 1.0
- **Last Updated**: 2026-02-16
- **Status**: Design Specification (Documentation Complete)

---

For questions or clarifications, refer to the specific documentation files or consult the [GLOSSARY.md](GLOSSARY.md) for terminology.
