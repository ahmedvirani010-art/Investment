# Design Decisions

## Overview

This document explains key architectural decisions, rationale, and trade-offs.

---

## 1. Custom Orchestration vs. Prefect/Dagster

### Decision
Build custom orchestration framework instead of using Prefect or Dagster.

### Rationale

**Advantages of Custom:**
- ✅ **Simplicity**: No external dependencies, easier deployment
- ✅ **PSX-Specific**: Tailored event types and workflows
- ✅ **Learning Curve**: Team knows codebase, faster iteration
- ✅ **Lightweight**: Prefect/Dagster too heavy for 9 agents
- ✅ **Migration Path**: Can migrate to Prefect later if needed
- ✅ **Control**: Full control over scheduling and execution

**Disadvantages:**
- ❌ **Less Features**: No web UI, fewer built-in features
- ❌ **Maintenance**: We maintain the orchestration code
- ❌ **Maturity**: Less battle-tested than Prefect/Dagster

### Trade-off
Accept less feature-rich UI and fewer built-in features in exchange for simplicity, control, and faster development.

### Future Path
If system grows to 50+ agents or needs distributed execution, migrate to Prefect.

---

## 2. SQLite vs. Redis for State

### Decision
Use SQLite for state persistence.

### Rationale

**Advantages of SQLite:**
- ✅ **Consistency**: Already using SQLite for price data
- ✅ **Simplicity**: No additional service to run
- ✅ **Persistence**: State survives restarts
- ✅ **ACID**: Workflow state needs transactions
- ✅ **Embedded**: No network latency
- ✅ **Queryable**: Can run SQL queries on state

**Disadvantages:**
- ❌ **Concurrency**: Write locks limit concurrent access
- ❌ **Scalability**: Not suitable for distributed deployment

### Trade-off
Accept lower concurrency limits in exchange for simplicity and consistency with existing data storage.

### Future Path
If system needs distributed execution across multiple machines, migrate to PostgreSQL + Redis.

---

## 3. ThreadPoolExecutor vs. AsyncIO

### Decision
Use ThreadPoolExecutor for parallel execution.

### Rationale

**Advantages of ThreadPoolExecutor:**
- ✅ **Compatibility**: Existing agents use blocking I/O (yfinance, feedparser)
- ✅ **Simplicity**: Easier to reason about than asyncio
- ✅ **Sufficient**: 4-8 workers handle 30 stocks well
- ✅ **No Refactoring**: Works with existing synchronous agents

**Disadvantages:**
- ❌ **Less Efficient**: AsyncIO would be more efficient for I/O-bound tasks
- ❌ **Thread Overhead**: Each worker consumes system resources

### Trade-off
Accept slightly lower efficiency in exchange for compatibility with existing agents and simpler code.

### Future Path
If performance becomes critical, refactor agents to async and migrate to asyncio.

---

## 4. In-Process Event Bus vs. Message Queue

### Decision
Use in-process event bus (not RabbitMQ/Kafka).

### Rationale

**Advantages of In-Process:**
- ✅ **Simplicity**: No external broker to run
- ✅ **Latency**: Sub-millisecond event delivery
- ✅ **Deployment**: Single process, easier to run
- ✅ **Sufficient**: Current scale doesn't need distributed events

**Disadvantages:**
- ❌ **Scalability**: Can't distribute across machines
- ❌ **Reliability**: Events lost if process crashes
- ❌ **No Persistence**: Event history limited to memory/SQLite

### Trade-off
Accept single-process limitation in exchange for simplicity and zero external dependencies.

### Future Path
If system needs distributed execution, migrate to RabbitMQ or Kafka.

---

## 5. Adapter Pattern vs. Agent Refactoring

### Decision
Use adapter pattern for agent integration.

### Rationale

**Advantages of Adapter:**
- ✅ **Backward Compatibility**: Existing agents work unchanged
- ✅ **Risk Mitigation**: No disruption to current operations
- ✅ **Gradual Migration**: Can enhance agents incrementally
- ✅ **Clear Separation**: Orchestration logic separate from agent logic

**Disadvantages:**
- ❌ **Indirection**: Slight overhead from dynamic loading
- ❌ **Type Safety**: Less type checking than direct imports

### Trade-off
Accept slight indirection in exchange for zero-disruption migration.

### Future Path
Optionally enhance agents to emit events directly (backward compatible).

---

## 6. DAG-based vs. Step Functions

### Decision
Use DAG (Directed Acyclic Graph) for workflow definitions.

### Rationale

**Advantages of DAG:**
- ✅ **Flexibility**: Express complex dependencies
- ✅ **Parallelism**: Automatic parallel execution of independent tasks
- ✅ **Visualization**: Easy to visualize workflow structure
- ✅ **Standard**: Industry-standard approach (Airflow, Prefect)

**Disadvantages:**
- ❌ **Complexity**: More complex than linear pipelines
- ❌ **Learning Curve**: Developers need to understand DAG concepts

### Trade-off
Accept higher complexity in exchange for flexibility and automatic parallelism.

---

## 7. Saga Pattern for Rollback

### Decision
Implement saga pattern for transactional workflows.

### Rationale

**Advantages:**
- ✅ **Data Consistency**: Ensures portfolio/risk data stays consistent
- ✅ **Automatic Rollback**: Compensations execute automatically on failure
- ✅ **Clear Semantics**: Easy to understand rollback behavior
- ✅ **Audit Trail**: Log of all compensations

**Disadvantages:**
- ❌ **Complexity**: Must define compensation for each task
- ❌ **Not Perfect**: Some operations can't be fully compensated

### Trade-off
Accept additional complexity in exchange for data consistency guarantees.

---

## 8. TTL-Based Caching

### Decision
Use TTL-based caching (not LRU or other eviction strategies).

### Rationale

**Advantages:**
- ✅ **Predictable**: Results valid for defined time period
- ✅ **Simple**: Easy to understand and configure
- ✅ **Appropriate**: News, prices change on time basis, not access patterns
- ✅ **Configurable**: Different TTLs for different data types

**Disadvantages:**
- ❌ **Memory Usage**: Cache grows until TTL expires
- ❌ **Stale Data**: Might serve stale data within TTL

### Trade-off
Accept potential stale data within TTL in exchange for predictable caching behavior.

---

## 9. Python Expressions for Conditions

### Decision
Use Python expressions for conditional task execution.

### Rationale

**Advantages:**
- ✅ **Flexible**: Full Python expression power
- ✅ **Familiar**: Developers already know Python
- ✅ **No DSL**: No need to learn custom language

**Disadvantages:**
- ❌ **Security**: eval() could be dangerous (mitigated by restricted context)
- ❌ **Error Messages**: Python eval errors can be cryptic

### Trade-off
Accept potential security concerns (mitigated) in exchange for maximum flexibility.

---

## 10. JSON for Serialization

### Decision
Use JSON for serializing workflow state and parameters.

### Rationale

**Advantages:**
- ✅ **Human-Readable**: Easy to debug
- ✅ **Universal**: Works across languages
- ✅ **Simple**: Built-in Python support
- ✅ **SQLite-Compatible**: TEXT field storage

**Disadvantages:**
- ❌ **Type Loss**: No native datetime, Decimal support
- ❌ **Size**: Larger than binary formats (pickle, msgpack)

### Trade-off
Accept larger storage size in exchange for human-readable, debuggable state.

---

## Summary of Key Decisions

| Decision | Choice | Why | Trade-off |
|----------|--------|-----|-----------|
| **Orchestration** | Custom | Simplicity, control | Less features than Prefect |
| **State Storage** | SQLite | Consistency, no extra service | Lower concurrency |
| **Parallelism** | ThreadPool | Existing agents compatible | Less efficient than async |
| **Event Bus** | In-Process | Simplicity, low latency | Can't distribute |
| **Agent Integration** | Adapter | Zero disruption | Slight indirection |
| **Workflow Structure** | DAG | Flexibility, parallelism | Higher complexity |
| **Transactions** | Saga | Data consistency | Must define compensations |
| **Caching** | TTL-based | Predictable behavior | Potential stale data |
| **Conditions** | Python expr | Maximum flexibility | Potential security risk |
| **Serialization** | JSON | Human-readable | Larger size |

---

## Future Evolution

### Phase 1: Current (30 stocks)
- Custom orchestration
- SQLite state
- ThreadPool parallelism
- In-process event bus

### Phase 2: Growth (100-500 stocks)
- Same architecture
- Increase workers
- Add PostgreSQL option
- Connection pooling

### Phase 3: Scale (1000+ stocks)
- Migrate to Prefect/Dagster
- PostgreSQL + Redis
- Distributed execution
- Message queue (RabbitMQ)

**Migration is possible because:**
- Clean separation of concerns
- Well-defined interfaces
- Minimal external dependencies
- Clear upgrade path

---

**Next**: See [GLOSSARY.md](GLOSSARY.md) for terminology reference.
