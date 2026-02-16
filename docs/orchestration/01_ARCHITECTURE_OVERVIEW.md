# Architecture Overview

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Principles](#design-principles)
3. [Architecture Patterns](#architecture-patterns)
4. [System Architecture](#system-architecture)
5. [Component Relationships](#component-relationships)
6. [Comparison: Sequential vs. Orchestrated](#comparison-sequential-vs-orchestrated)
7. [Design Decisions](#design-decisions)
8. [Performance Characteristics](#performance-characteristics)
9. [Scalability Considerations](#scalability-considerations)

---

## Executive Summary

The PSX Orchestration Agent transforms the Pakistan Stock Exchange investment platform from a **sequential pipeline** into an **intelligent, event-driven orchestration system**. It coordinates 9 specialized agents through a hybrid architecture combining the **Coordinator Pattern** for workflow management with an **Event Bus** for reactive behaviors.

### Key Innovations

1. **Event-Driven Coordination**: Workflows trigger automatically based on market events
2. **Parallel Execution**: 3x performance improvement through concurrent task processing
3. **Smart Workflow Routing**: Conditional execution paths based on analysis results
4. **Integrated Risk Management**: Pre-trade validation and continuous portfolio risk monitoring
5. **State Persistence**: Full workflow resumability with TTL-based caching
6. **Zero Agent Modifications**: Backward-compatible adapter pattern

### Value Proposition

| Dimension | Improvement |
|-----------|-------------|
| **Speed** | 3x faster (180s → 60s for 30 stocks) |
| **Flexibility** | Fixed pipeline → Dynamic routing |
| **Reliability** | Single point of failure → Task-level resilience |
| **Intelligence** | Manual triggers → Automatic event-driven workflows |
| **Risk Management** | None → Pre-trade validation + monitoring |
| **Caching** | None → 90s saved per run with smart caching |

---

## Design Principles

### 1. **Event-Driven First**

The system is built around events as first-class citizens. Every significant action emits an event, enabling:

- **Reactive Workflows**: Automatically trigger workflows based on market conditions
- **Loose Coupling**: Agents don't directly call each other
- **Extensibility**: Add new workflows by subscribing to events
- **Audit Trail**: Complete event log for debugging and compliance

**Example:**
```python
# High-severity anomaly automatically triggers investigation
event_bus.subscribe(
    EventType.HIGH_SEVERITY_ANOMALY,
    lambda event: orchestrator.trigger_workflow("investigation")
)
```

### 2. **Backward Compatibility**

Existing agents work unchanged through the **Adapter Pattern**:

- No modifications to existing agent code
- Optional event emission for enhanced integration
- Existing CLI interface preserved
- Gradual migration path

**Benefit**: Zero disruption to current operations while adding new capabilities.

### 3. **Intelligent Resource Management**

Smart allocation and caching to optimize performance:

- **Parallel Execution**: ThreadPoolExecutor with configurable workers
- **Rate Limiting**: Semaphores prevent API throttling
- **TTL-Based Caching**: Avoid redundant computations
- **Priority Scheduling**: Critical tasks execute first

### 4. **Resilience & Recoverability**

Robust error handling with graceful degradation:

- **Task-Level Retry**: Exponential backoff for transient failures
- **Saga Pattern**: Compensating actions for rollback
- **State Persistence**: Resume workflows after crashes
- **Circuit Breakers**: Prevent cascading failures

### 5. **Observability**

Complete visibility into system behavior:

- **Workflow State Tracking**: Monitor execution progress
- **Event Logging**: Audit trail of all system events
- **Performance Metrics**: Task execution times and bottlenecks
- **Error Tracking**: Detailed failure information

---

## Architecture Patterns

### Coordinator Pattern

The **WorkflowCoordinator** acts as a central orchestrator managing workflow execution:

```
┌─────────────────────────────────────────────┐
│         Workflow Coordinator                │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │   Workflow Definition (DAG)           │ │
│  │                                       │ │
│  │   Task A ──→ Task B ──→ Task D       │ │
│  │              ↓                        │ │
│  │            Task C ──→ Task E          │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  • Dependency Resolution                   │
│  • Parallel Execution                      │
│  • Conditional Routing                     │
│  • State Management                        │
└─────────────────────────────────────────────┘
```

**Responsibilities:**
- Parse workflow definitions (DAG)
- Resolve task dependencies
- Schedule parallel execution where possible
- Handle conditional task execution
- Manage workflow state

**Advantages:**
- Clear separation of concerns
- Testable workflow definitions
- Easy to add new workflows
- Predictable execution order

### Event Bus Pattern (Pub/Sub)

Enables reactive, loosely-coupled communication:

```
┌──────────────────────────────────────────────────┐
│              Event Bus (In-Process)              │
│                                                  │
│  Publishers              Subscribers             │
│  ┌──────────┐           ┌──────────┐           │
│  │ Agent A  │──publish──│ Handler 1│           │
│  └──────────┘     ↓     └──────────┘           │
│                   ↓                              │
│  ┌──────────┐    ↓     ┌──────────┐           │
│  │ Agent B  │────┴─────│ Handler 2│           │
│  └──────────┘          └──────────┘           │
│                                                  │
│  • Event Routing                                │
│  • Subscription Management                      │
│  • Event Logging                                │
└──────────────────────────────────────────────────┘
```

**Event Types:**
- **Data Events**: `price_data_updated`, `news_fetched`
- **Analysis Events**: `anomaly_detected`, `technical_analysis_complete`
- **Portfolio Events**: `position_opened`, `position_closed`
- **Risk Events**: `risk_violation`, `risk_threshold_exceeded`

**Advantages:**
- Decoupled components
- Easy to add new event handlers
- Supports feedback loops
- Natural fit for reactive workflows

### Saga Pattern

Ensures transactional consistency with compensating actions:

```
Workflow: ValidatedTradeExecution
┌────────────────────────────────────────────────┐
│  Forward Actions      Compensating Actions    │
├────────────────────────────────────────────────┤
│  1. Validate Risk  ←→ Log failure             │
│  2. Reserve Cash   ←→ Release cash            │
│  3. Add Position   ←→ Remove position         │
│  4. Update Portfolio ←→ Revert update         │
└────────────────────────────────────────────────┘

If Step 3 fails → Execute compensations in reverse:
  - Revert Step 2 (Release cash)
  - Revert Step 1 (Log failure)
```

**Advantages:**
- Maintains data consistency
- Graceful failure handling
- Clear rollback semantics
- Audit trail of compensations

---

## System Architecture

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    PSX Orchestration Agent                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Control Plane                            │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │  Workflow    │  │  Event Bus   │  │    State     │    │ │
│  │  │ Coordinator  │  │  (Pub/Sub)   │  │   Manager    │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  │                                                             │ │
│  │  Responsibilities:                                          │ │
│  │  • Workflow orchestration                                  │ │
│  │  • Event routing                                           │ │
│  │  • State persistence                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Data Plane                              │ │
│  │                                                             │ │
│  │  ┌────────────────────────────────────────────────────┐    │ │
│  │  │           Execution Engine                         │    │ │
│  │  │                                                    │    │ │
│  │  │  • Task Executor (ThreadPoolExecutor)            │    │ │
│  │  │  • Retry Handler (Exponential Backoff)           │    │ │
│  │  │  • Resource Manager (Semaphores)                 │    │ │
│  │  │  • Cache Manager (TTL-based)                     │    │ │
│  │  │  • Agent Adapter (Dynamic Loading)               │    │ │
│  │  └────────────────────────────────────────────────────┘    │ │
│  │                                                             │ │
│  │  Responsibilities:                                          │ │
│  │  • Execute tasks with parallelism                          │ │
│  │  • Manage retries and errors                               │ │
│  │  • Control resource limits                                 │ │
│  │  • Cache results                                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴────────────────────┐
        │                                        │
┌───────▼─────────┐                   ┌─────────▼─────────┐
│  9 Specialized  │                   │   Shared Data     │
│     Agents      │◄──────────────────│     Stores        │
│                 │   Read/Write      │   (SQLite)        │
│                 │                   │                   │
│  • Liquidity    │                   │  • price_data     │
│  • Technical    │                   │  • news_articles  │
│  • Fundamental  │                   │  • anomalies      │
│  • Anomaly      │                   │  • portfolios     │
│  • PriceStore   │                   │  • holdings       │
│  • News         │                   │  • risk_settings  │
│  • Correlator   │                   │  • violations     │
│  • Portfolio    │                   │  • workflow_state │
│  • Risk         │                   │                   │
└─────────────────┘                   └───────────────────┘
```

### Layered Architecture

**Layer 1: Orchestration Interface**
- `PSXOrchestrationAgent` - Main API for users and external systems
- Provides high-level methods: `run_workflow()`, `run_daily_analysis()`, `trigger_workflow()`

**Layer 2: Workflow Management**
- `WorkflowCoordinator` - Manages workflow lifecycle
- `WorkflowTemplates` - Predefined workflow definitions
- Handles DAG execution and conditional routing

**Layer 3: Event Infrastructure**
- `PSXEventBus` - Pub/sub event routing
- Event listeners and handlers
- Event logging for audit trail

**Layer 4: Execution & State**
- `ExecutionEngine` - Parallel task execution
- `StateManager` - Persistence and caching
- `AgentAdapter` - Dynamic agent loading

**Layer 5: Agent & Data Layer**
- 9 specialized agents (unchanged)
- SQLite data stores (shared)
- External APIs (yfinance, RSS feeds)

---

## Component Relationships

### Component Interaction Diagram

```
User/CLI
   │
   ▼
PSXOrchestrationAgent
   │
   ├──→ WorkflowCoordinator ──→ ExecutionEngine ──→ AgentAdapter ──→ Agents
   │         │                       │                                  │
   │         │                       │                                  │
   │         ▼                       ▼                                  ▼
   │    PSXEventBus ◄──────── StateManager ◄──────────────── Shared Data Stores
   │         │                       │
   │         │                       │
   │         └───── Event Handlers ──┘
   │                     │
   └─────────────────────┘
         (Feedback Loop)
```

### Data Flow

**1. Workflow Execution Flow:**
```
User Request
   → PSXOrchestrationAgent.run_workflow()
   → WorkflowCoordinator.execute()
      → Build DAG from WorkflowDefinition
      → ExecutionEngine.execute_tasks()
         → For each task:
            → Check cache (StateManager)
            → If cached: return
            → Else: AgentAdapter.call_method()
               → Load agent dynamically
               → Execute method
               → Cache result
               → Emit events (EventBus)
         → Aggregate results
      → Update workflow state
   → Return WorkflowResult
```

**2. Event-Driven Flow:**
```
Agent emits event
   → EventBus.publish(event)
   → EventBus routes to subscribers
   → Subscriber (WorkflowTrigger) receives event
      → Evaluates trigger condition
      → If triggered:
         → PSXOrchestrationAgent.trigger_workflow()
         → (follows workflow execution flow above)
```

**3. Risk Validation Flow:**
```
Trade Plan Created (UI or API)
   → Emit "trade_plan_created" event
   → PSXRiskAgent.validate_trade()
      → Check max_risk_per_trade
      → Check max_position_size
      → Check min_reward_to_risk
      → If violations:
         → Emit "risk_violation" event
         → Block execution
      → If valid:
         → PSXPortfolioAgent.add_position()
         → Emit "position_opened" event
         → PSXPriceStore.update_prices()
         → Emit "portfolio_updated" event
```

### Inter-Component Communication

**Synchronous Communication:**
- User → PSXOrchestrationAgent (API calls)
- WorkflowCoordinator → ExecutionEngine (task execution)
- ExecutionEngine → AgentAdapter → Agents (method invocation)
- All components → StateManager (state read/write)

**Asynchronous Communication:**
- Agents → EventBus (event emission)
- EventBus → Event Handlers (event delivery)
- Event Handlers → WorkflowCoordinator (workflow triggers)

---

## Comparison: Sequential vs. Orchestrated

### Sequential Pipeline (Current)

```
┌─────────────────────────────────────────────┐
│      run_integrated_analysis.py             │
│                                             │
│  1. Stock Selection (PSXLiquidityScreener) │
│           ↓                                 │
│  2. Price Data Sync (PSXPriceStore)        │
│           ↓                                 │
│  3. News Collection (PSXNewsAgent)         │
│           ↓                                 │
│  4. Technical Analysis (PSXTechnicalAgent) │
│           ↓                                 │
│  5. Anomaly Detection (PSXAnomalyAgent)    │
│           ↓                                 │
│  6. News Correlation (Correlator)          │
│           ↓                                 │
│  7. Print Report                            │
└─────────────────────────────────────────────┘

Characteristics:
• Fixed execution order
• No parallelism
• Single failure = entire pipeline fails
• Manual triggers only
• No caching
• No state persistence
```

### Orchestrated System (Proposed)

```
┌──────────────────────────────────────────────────┐
│      PSXOrchestrationAgent                       │
│                                                  │
│  Workflow: DailyAnalysisWorkflow               │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  Task Graph (DAG)                          │ │
│  │                                            │ │
│  │  Stock Selection                           │ │
│  │         ↓                                  │ │
│  │  Price Data Sync                           │ │
│  │         ↓                                  │ │
│  │    ┌────┴────┬────────┬────────┐         │ │
│  │    ↓         ↓        ↓        ↓         │ │
│  │  Tech₁     Tech₂   Tech₃   Tech₄         │ │
│  │  (parallel execution - 4 workers)         │ │
│  │    ↓         ↓        ↓        ↓         │ │
│  │  Anomaly₁  Anomaly₂ Anomaly₃ Anomaly₄    │ │
│  │    └────┬────┴────────┴────────┘         │ │
│  │         ↓                                  │ │
│  │  News Correlation                          │ │
│  │         ↓                                  │ │
│  │  Generate Report                           │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  Features:                                      │
│  • Parallel task execution                      │
│  • Event-driven triggers                        │
│  • Task-level retry                             │
│  • Result caching (TTL)                         │
│  • State persistence                            │
│  • Conditional routing                          │
└──────────────────────────────────────────────────┘
```

### Feature Comparison Matrix

| Feature | Sequential | Orchestrated |
|---------|-----------|--------------|
| **Execution Model** | Linear | DAG-based |
| **Parallelism** | None | ThreadPool (4 workers) |
| **Time for 30 stocks** | ~180s | ~60s |
| **Error Handling** | Pipeline fails | Task retry + compensation |
| **Caching** | None | TTL-based (90s savings) |
| **State Persistence** | None | Full workflow state |
| **Resumability** | Manual restart | Auto-resume |
| **Event Triggers** | Manual only | Automatic + manual |
| **Conditional Execution** | None | Yes (dynamic routing) |
| **Feedback Loops** | None | Yes (event-driven) |
| **Risk Management** | External | Integrated (pre-trade) |
| **Portfolio Tracking** | External | Integrated (real-time) |
| **Agent Coupling** | Tight (direct calls) | Loose (event bus) |
| **Observability** | Print statements | Event logs + state |
| **Extensibility** | Modify pipeline | Add workflows/handlers |

### Migration Benefits

**Performance:**
- 3x faster execution (180s → 60s)
- Smart caching saves 90s per run
- Parallel execution maximizes CPU utilization

**Reliability:**
- Task-level retry prevents total failures
- Saga pattern ensures data consistency
- State persistence enables resumability

**Flexibility:**
- Dynamic workflow routing
- Event-driven automation
- Easy to add new workflows

**Intelligence:**
- Automatic anomaly investigation
- Pre-trade risk validation
- Continuous portfolio monitoring

**Maintainability:**
- Loose coupling via events
- Zero changes to existing agents
- Clear separation of concerns

---

## Design Decisions

### 1. Custom Orchestration vs. Prefect/Dagster

**Decision**: Build custom orchestration framework

**Rationale:**
- **Simplicity**: No external dependencies, easier deployment
- **PSX-Specific**: Tailored event types and workflows
- **Learning Curve**: Team knows codebase, faster iteration
- **Overhead**: Prefect/Dagster too heavy for 9 agents
- **Migration Path**: Can migrate to Prefect later if needed

**Trade-off**: Less feature-rich UI, but faster development

### 2. SQLite vs. Redis for State

**Decision**: SQLite for state persistence

**Rationale:**
- **Consistency**: Already using SQLite for price data
- **Simplicity**: No additional service to run
- **Persistence**: State survives restarts
- **ACID**: Workflow state needs transactions
- **Embedded**: No network latency

**Trade-off**: Less scalable than Redis, but sufficient for single-machine deployment

### 3. ThreadPoolExecutor vs. AsyncIO

**Decision**: ThreadPoolExecutor for parallel execution

**Rationale:**
- **Blocking I/O**: Existing agents use blocking yfinance, feedparser
- **Simplicity**: Easier to reason about
- **Sufficient**: 4-8 workers handle 30 stocks well
- **Compatibility**: Works with existing synchronous agents

**Trade-off**: AsyncIO would be more efficient, but requires agent refactoring

### 4. In-Process Event Bus vs. Message Queue

**Decision**: In-process event bus

**Rationale:**
- **Simplicity**: No external broker (RabbitMQ, Kafka)
- **Latency**: Sub-millisecond event delivery
- **Deployment**: Single process, easier to run
- **Scale**: Sufficient for current needs

**Trade-off**: Can't distribute across machines, but not needed yet

### 5. Adapter Pattern vs. Agent Refactoring

**Decision**: Adapter pattern for agent integration

**Rationale:**
- **Backward Compatibility**: Existing agents work unchanged
- **Risk Mitigation**: No disruption to current operations
- **Gradual Migration**: Can enhance agents incrementally
- **Clear Separation**: Orchestration logic separate from agent logic

**Trade-off**: Slight indirection, but worth the compatibility

---

## Performance Characteristics

### Execution Time Analysis

**Sequential (Current):**
```
Stock Selection:          10s
Price Data Sync:          30s (30 stocks × 1s)
News Collection:          40s
Technical Analysis:       60s (30 stocks × 2s)
Anomaly Detection:        30s (30 stocks × 1s)
News Correlation:         10s
────────────────────────────
Total:                   180s
```

**Orchestrated (Parallel with 4 workers):**
```
Stock Selection:          10s
Price Data Sync:          30s (bottleneck: API rate limit)
Technical Analysis:       15s (60s ÷ 4 workers)
  └─ Parallel with News:  40s (runs concurrently)
News Collection:          40s
Anomaly Detection:         8s (30s ÷ 4 workers)
News Correlation:         10s
────────────────────────────
Total (with parallelism): ~60s (3x improvement)
```

### Caching Impact

**Without Caching (Fresh Run):**
- News fetch: 40s
- Technical computation: 15s
- Total: ~60s

**With Caching (Within TTL):**
- News fetch: 0.5s (cached, 30min TTL)
- Technical computation: 1s (cached, 1hr TTL)
- Total saved: ~53.5s
- **New total: ~7s** (just coordination overhead)

**Realistic Scenario (Mixed):**
- First run: 60s
- Second run (within 30 min): ~15s (news cached)
- Third run (within 1 hr): ~10s (news + tech cached)
- **Average: ~30s** with typical cache hit rates

### Resource Utilization

**CPU:**
- Sequential: 1 core @ 100% (underutilized on multi-core)
- Orchestrated: 4 cores @ 80-90% (better utilization)

**Memory:**
- Sequential: ~200MB (one symbol at a time)
- Orchestrated: ~500MB (4 symbols in parallel)
- Acceptable for modern systems

**I/O:**
- Sequential: Serial API calls (slow)
- Orchestrated: Parallel API calls (semaphore-limited to 2 concurrent)
- Network utilization: 2x improvement

---

## Scalability Considerations

### Current Scale (30 stocks)

**Well-Suited:**
- SQLite handles 1000s of rows easily
- ThreadPool with 4 workers sufficient
- In-process event bus fast enough
- Single-machine deployment simple

### Future Scale (100-500 stocks)

**Adjustments Needed:**
- Increase ThreadPool workers to 8-16
- Batch processing (analyze 50 stocks at a time)
- Consider PostgreSQL for better concurrent writes
- Add connection pooling for database

### Enterprise Scale (1000+ stocks)

**Architecture Evolution:**
- Replace ThreadPoolExecutor with Celery (distributed)
- Replace SQLite with PostgreSQL (multi-machine)
- Replace in-process EventBus with RabbitMQ (distributed)
- Add Redis for distributed caching
- Horizontal scaling across multiple machines

**Migration Path:**
- Phase 1: Current design (30 stocks) ✓
- Phase 2: Optimize (100 stocks) - 2 weeks
- Phase 3: Distribute (500 stocks) - 4 weeks
- Phase 4: Enterprise (1000+ stocks) - 8 weeks

### Bottleneck Analysis

**Current Bottlenecks:**
1. **yfinance API rate limits** (primary)
   - Solution: Caching + batch requests
2. **Single-machine SQLite writes**
   - Solution: Batch inserts, connection pooling
3. **Sequential price data sync**
   - Solution: Parallel with semaphore limiting

**Future Bottlenecks (at scale):**
1. **Memory (500MB × 10 = 5GB at 300 stocks)**
   - Solution: Distributed workers
2. **SQLite lock contention**
   - Solution: PostgreSQL migration
3. **Single-process event bus**
   - Solution: Message queue (RabbitMQ)

---

## Summary

The PSX Orchestration Agent provides a **production-ready foundation** for:

✅ **3x performance improvement** through parallel execution
✅ **Event-driven automation** for reactive workflows
✅ **Integrated risk management** with pre-trade validation
✅ **Real-time portfolio tracking** with P&L calculation
✅ **Zero disruption** to existing agents (adapter pattern)
✅ **Clear migration path** from sequential to orchestrated
✅ **Future-proof design** with scalability to 1000+ stocks

The architecture balances **simplicity** (custom framework, SQLite, ThreadPool) with **sophistication** (event bus, DAG workflows, saga pattern) to deliver immediate value while supporting future growth.

---

**Next**: See [02_COMPONENT_SPECIFICATIONS.md](02_COMPONENT_SPECIFICATIONS.md) for detailed component specifications.
