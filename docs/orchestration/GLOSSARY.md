# Glossary

## Orchestration Terms

### Agent
An autonomous software component responsible for a specific task (e.g., PSXTechnicalAgent for technical analysis).

### Agent Adapter
A component that dynamically loads and calls agents without hard-coded imports, enabling backward compatibility.

### Compensation
An action that reverses a previously completed task, used in the saga pattern for rollback.

### Coordinator Pattern
An architectural pattern where a central component (WorkflowCoordinator) manages and schedules tasks.

### DAG (Directed Acyclic Graph)
A graph structure representing task dependencies where tasks are nodes and dependencies are edges. "Acyclic" means no circular dependencies.

### Event Bus
A publish-subscribe messaging system that routes events from publishers to subscribers.

### Event-Driven
Architecture where actions are triggered by events rather than direct function calls.

### Execution Engine
Component responsible for executing workflow tasks with parallelism, retries, and caching.

### Orchestration
Coordination of multiple agents/services to accomplish complex workflows.

### Saga Pattern
A design pattern for managing distributed transactions through compensating actions.

### State Manager
Component that persists workflow state to enable resumability.

### Task
A single unit of work in a workflow (e.g., "analyze technical indicators").

### TTL (Time To Live)
Duration for which cached data remains valid before expiration.

### Workflow
A sequence of tasks organized as a DAG to accomplish a specific goal.

### Workflow Definition
A declarative specification of a workflow including tasks and dependencies.

### Workflow Result
The output of a workflow execution, including status, data, and metadata.

---

## PSX-Specific Terms

### Anomaly
An unusual price or volume movement detected through statistical or ML methods.

### Correlation
The relationship between news events and price movements.

### Fundamental Analysis
Analysis of company financial metrics (P/E, ROE, etc.).

### Liquidity Screening
Process of filtering stocks based on trading volume and price.

### P&L (Profit and Loss)
Financial gain or loss from trading positions.

### Position
A holding of a specific stock (open = currently held, closed = sold).

### PSX
Pakistan Stock Exchange.

### Technical Analysis
Analysis of price charts using indicators (RSI, MACD, etc.).

### VaR (Value at Risk)
Statistical measure of potential loss in portfolio value.

---

## Technical Terms

### Backoff
Strategy of waiting progressively longer between retry attempts (e.g., 2s, 4s, 8s).

### Cache Hit
When requested data is found in the cache (no need to recompute).

### Cache Miss
When requested data is not in cache (must compute and cache).

### Concurrent Execution
Multiple tasks running at the same time (in parallel).

### Dependency
A requirement that one task must complete before another can start.

### Deterministic
Producing the same output for the same input every time.

### Idempotent
An operation that produces the same result whether executed once or multiple times.

### Pub/Sub (Publish/Subscribe)
Messaging pattern where publishers send messages to a channel and subscribers receive them.

### Retry Logic
Automatically re-attempting failed operations with configured delays.

### Rollback
Undoing changes to restore previous state after a failure.

### Semaphore
A synchronization primitive that limits concurrent access to a resource.

### Sequential Execution
Tasks running one after another (not in parallel).

### Thread Pool
A collection of worker threads available for parallel task execution.

### Transaction
A sequence of operations that must all succeed or all fail together.

---

## Risk Management Terms

### Concentration Risk
Risk from having too much exposure to a single stock or sector.

### Drawdown
Peak-to-trough decline in portfolio value.

### Leverage
Using borrowed money to increase position size.

### Position Sizing
Determining how much capital to allocate to a single trade.

### Reward-to-Risk Ratio
Expected profit divided by potential loss (e.g., 2:1 means expect $2 profit for $1 risk).

### Risk Level
Categorization of portfolio risk (low, medium, high).

### Risk Rule
A constraint enforced by the risk management system.

### Risk Violation
When a trade or portfolio state breaches a risk rule.

### Sharpe Ratio
Risk-adjusted return metric (higher is better).

### Stop Loss
Pre-defined exit price to limit losses.

---

## Workflow Terms

### Conditional Task
A task that only executes if a condition is met.

### Fan-In
Multiple parallel tasks converging to a single task.

### Fan-Out
A single task spawning multiple parallel tasks.

### Parameterization
Using variables in workflow definitions that are filled at runtime.

### Resumability
Ability to continue a workflow from the point of failure.

### Task Dependency
Requirement that task B must wait for task A to complete.

### Workflow Context
Shared state available to all tasks in a workflow.

### Workflow Trigger
Event or condition that starts a workflow execution.

---

## Database Terms

### Foreign Key
A field that references the primary key of another table.

### Index
Data structure that improves query performance.

### OHLCV
Open, High, Low, Close, Volume - standard price data format.

### Primary Key
Unique identifier for a database row.

### Schema
Structure defining tables, columns, and relationships.

### SQLite
Lightweight, serverless SQL database engine.

### Unique Constraint
Ensures no two rows have the same value in specified column(s).

---

## Performance Terms

### Bottleneck
Component or operation limiting overall system throughput.

### Cache Key
Unique identifier for cached data.

### Latency
Time between request and response.

### Parallelism
Executing multiple operations simultaneously.

### Throughput
Number of operations completed per unit time.

### Worker
Thread or process executing tasks.

---

## Acronyms

- **API**: Application Programming Interface
- **CLI**: Command Line Interface
- **CSV**: Comma-Separated Values
- **DAG**: Directed Acyclic Graph
- **JSON**: JavaScript Object Notation
- **ML**: Machine Learning
- **OHLCV**: Open, High, Low, Close, Volume
- **P&L**: Profit and Loss
- **PSX**: Pakistan Stock Exchange
- **RSS**: Really Simple Syndication
- **SQL**: Structured Query Language
- **TTL**: Time To Live
- **UI**: User Interface
- **VaR**: Value at Risk

---

## Common Abbreviations

- **avg**: average
- **max**: maximum
- **min**: minimum
- **pct**: percentage
- **std dev**: standard deviation
- **vol**: volume

---

**End of Glossary**
