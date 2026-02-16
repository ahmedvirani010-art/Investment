# Component Specifications

## Table of Contents

1. [PSXOrchestrationAgent](#psxorchestrationagent)
2. [WorkflowCoordinator](#workflowcoordinator)
3. [PSXEventBus](#psxeventbus)
4. [ExecutionEngine](#executionengine)
5. [StateManager](#statemanager)
6. [AgentAdapter](#agentadapter)
7. [Component Integration](#component-integration)

---

## PSXOrchestrationAgent

### Overview

The `PSXOrchestrationAgent` is the **main entry point** for the orchestration system. It provides a high-level API for users and external systems to interact with workflows, agents, and events.

### Location

```
psx_orchestration_agent/
├── agent.py              # Main PSXOrchestrationAgent class
├── workflow_coordinator.py
├── event_bus.py
└── ...
```

### Class Definition

```python
class PSXOrchestrationAgent:
    """
    Main orchestration agent coordinating all PSX agents through workflows.

    Provides high-level methods for:
    - Running predefined workflows
    - Triggering event-based workflows
    - Executing custom workflows
    - Managing agent lifecycle
    """

    def __init__(
        self,
        db_path: str = "data/psx_data.db",
        config_path: Optional[str] = None,
        max_workers: int = 4,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 1800
    ):
        """
        Initialize orchestration agent.

        Args:
            db_path: Path to SQLite database
            config_path: Optional config file for workflows
            max_workers: Number of parallel workers (default: 4)
            enable_caching: Enable result caching (default: True)
            cache_ttl_seconds: Cache TTL in seconds (default: 1800 = 30 min)
        """
```

### Key Methods

#### 1. `run_workflow()`

Execute a predefined workflow by name.

```python
def run_workflow(
    self,
    workflow_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    resume_from: Optional[str] = None
) -> WorkflowResult:
    """
    Run a predefined workflow.

    Args:
        workflow_name: Name of workflow (e.g., "daily_analysis")
        parameters: Optional parameters for workflow
        resume_from: Optional workflow ID to resume

    Returns:
        WorkflowResult with status, results, and metadata

    Example:
        result = agent.run_workflow(
            "daily_analysis",
            parameters={"min_volume": 500000}
        )
    """
```

**Supported Workflows:**
- `daily_analysis` - Complete daily market analysis
- `validated_trade_execution` - Trade with pre-validation
- `high_severity_investigation` - Investigate anomalies
- `portfolio_risk_check` - Monitor portfolio risk
- `news_impact_analysis` - Correlate news with price moves

#### 2. `run_daily_analysis()`

Convenient method for running daily analysis workflow.

```python
def run_daily_analysis(
    self,
    min_volume: int = 500000,
    min_price: float = 20.0,
    cache_enabled: bool = True
) -> WorkflowResult:
    """
    Run the daily analysis workflow.

    This is a convenience wrapper around run_workflow("daily_analysis").

    Args:
        min_volume: Minimum volume for stock selection
        min_price: Minimum price for stock selection
        cache_enabled: Enable caching for this run

    Returns:
        WorkflowResult containing analysis for all selected stocks

    Workflow Steps:
        1. Select liquid stocks (PSXLiquidityScreener)
        2. Sync price data (PSXPriceStore)
        3. Fetch news (PSXNewsAgent)
        4. Run technical analysis (PSXTechnicalAgent) - parallel
        5. Detect anomalies (PSXAnomalyAgent) - parallel
        6. Correlate news (Correlator)
        7. Generate report
    """
```

#### 3. `trigger_workflow()`

Trigger a workflow based on an event.

```python
def trigger_workflow(
    self,
    event: PSXEvent,
    workflow_mappings: Optional[Dict[str, str]] = None
) -> Optional[WorkflowResult]:
    """
    Trigger workflow based on event type.

    Args:
        event: PSXEvent that triggered the workflow
        workflow_mappings: Optional custom event->workflow mappings

    Returns:
        WorkflowResult if workflow executed, None if no mapping

    Example:
        event = PSXEvent(
            type=EventType.HIGH_SEVERITY_ANOMALY,
            data={"symbol": "OGDC", "severity": 0.95}
        )
        result = agent.trigger_workflow(event)
    """
```

**Default Event Mappings:**
```python
{
    EventType.HIGH_SEVERITY_ANOMALY: "high_severity_investigation",
    EventType.RISK_VIOLATION: "portfolio_risk_check",
    EventType.NEWS_PUBLISHED: "news_impact_analysis",
    EventType.PORTFOLIO_UPDATED: "portfolio_risk_check"
}
```

#### 4. `execute_custom_workflow()`

Execute a custom workflow definition.

```python
def execute_custom_workflow(
    self,
    workflow_def: WorkflowDefinition,
    parameters: Optional[Dict[str, Any]] = None
) -> WorkflowResult:
    """
    Execute a custom workflow definition.

    Allows users to define custom workflows programmatically.

    Args:
        workflow_def: WorkflowDefinition instance
        parameters: Optional parameters

    Returns:
        WorkflowResult

    Example:
        workflow = WorkflowDefinition(
            name="custom_analysis",
            tasks=[
                Task(name="fetch_prices", agent="price_store", ...),
                Task(name="analyze", agent="technical", ...)
            ]
        )
        result = agent.execute_custom_workflow(workflow)
    """
```

#### 5. `get_workflow_status()`

Get status of a running or completed workflow.

```python
def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
    """
    Get status of a workflow.

    Args:
        workflow_id: Unique workflow execution ID

    Returns:
        WorkflowStatus with execution details

    Example:
        status = agent.get_workflow_status("wf_20260216_123456")
        print(f"Status: {status.state}")  # RUNNING, COMPLETED, FAILED
        print(f"Progress: {status.completed_tasks}/{status.total_tasks}")
    """
```

#### 6. `list_workflows()`

List all available workflows.

```python
def list_workflows(self) -> List[str]:
    """
    List all registered workflow names.

    Returns:
        List of workflow names

    Example:
        workflows = agent.list_workflows()
        # ['daily_analysis', 'validated_trade_execution', ...]
    """
```

### Configuration

The agent accepts configuration via:

**1. Constructor Parameters:**
```python
agent = PSXOrchestrationAgent(
    db_path="data/psx_data.db",
    max_workers=4,
    enable_caching=True,
    cache_ttl_seconds=1800
)
```

**2. Config File (`config.yaml`):**
```yaml
orchestration:
  max_workers: 4
  enable_caching: true
  cache_ttl_seconds: 1800

workflows:
  daily_analysis:
    enabled: true
    schedule: "0 18 * * 1-5"  # 6 PM on weekdays

  portfolio_risk_check:
    enabled: true
    schedule: "0 * * * *"  # Every hour
```

### Error Handling

```python
try:
    result = agent.run_workflow("daily_analysis")
except WorkflowNotFoundError as e:
    print(f"Workflow not found: {e}")
except WorkflowExecutionError as e:
    print(f"Execution failed: {e}")
    print(f"Failed task: {e.failed_task}")
    print(f"Error: {e.original_error}")
```

### Thread Safety

The `PSXOrchestrationAgent` is **thread-safe**:
- Single instance can be shared across threads
- Internal locks protect shared state
- Event bus uses thread-safe queues

### Lifecycle

```python
# Initialize
agent = PSXOrchestrationAgent()

# Use agent
result = agent.run_daily_analysis()

# Cleanup (optional, handles cleanup automatically)
agent.close()
```

---

## WorkflowCoordinator

### Overview

The `WorkflowCoordinator` manages workflow execution, dependency resolution, and task scheduling. It's the core orchestration engine.

### Class Definition

```python
class WorkflowCoordinator:
    """
    Coordinates workflow execution using DAG-based task scheduling.

    Responsibilities:
    - Parse workflow definitions
    - Build DAG from task dependencies
    - Schedule parallel execution
    - Handle conditional routing
    - Manage workflow state
    - Implement saga pattern for rollback
    """

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        state_manager: StateManager,
        event_bus: PSXEventBus
    ):
        """
        Initialize workflow coordinator.

        Args:
            execution_engine: Engine for executing tasks
            state_manager: Manager for workflow state
            event_bus: Event bus for publishing events
        """
```

### Key Methods

#### 1. `execute()`

Execute a workflow definition.

```python
def execute(
    self,
    workflow_def: WorkflowDefinition,
    parameters: Optional[Dict[str, Any]] = None,
    workflow_id: Optional[str] = None
) -> WorkflowResult:
    """
    Execute a workflow definition.

    Args:
        workflow_def: Workflow definition (DAG)
        parameters: Runtime parameters
        workflow_id: Optional ID for resuming

    Returns:
        WorkflowResult with status and outputs

    Execution Flow:
        1. Load or create workflow state
        2. Build DAG from workflow definition
        3. Topologically sort tasks
        4. Execute tasks in dependency order
        5. Handle conditional routing
        6. Aggregate results
        7. Persist final state
    """
```

#### 2. `build_dag()`

Build directed acyclic graph from workflow definition.

```python
def build_dag(self, workflow_def: WorkflowDefinition) -> nx.DiGraph:
    """
    Build DAG from workflow definition.

    Args:
        workflow_def: Workflow definition

    Returns:
        NetworkX DiGraph representing task dependencies

    Example DAG:
        stock_selection
              ↓
        price_sync
              ↓
        ┌─────┴─────┬─────┐
        ↓           ↓     ↓
    technical   news   fundamental
        └─────┬─────┘     ↓
              ↓           ↓
          anomaly    ─────┘
              ↓
        correlation
    """
```

#### 3. `execute_task()`

Execute a single task with error handling.

```python
def execute_task(
    self,
    task: Task,
    workflow_context: WorkflowContext
) -> TaskResult:
    """
    Execute a single task.

    Args:
        task: Task definition
        workflow_context: Shared workflow context

    Returns:
        TaskResult with output or error

    Features:
        - Retry logic (exponential backoff)
        - Cache checking
        - Error capture
        - Event emission
        - Compensation tracking (saga)
    """
```

#### 4. `evaluate_condition()`

Evaluate conditional task execution.

```python
def evaluate_condition(
    self,
    condition: str,
    workflow_context: WorkflowContext
) -> bool:
    """
    Evaluate a condition for conditional task execution.

    Args:
        condition: Condition expression (Python expression)
        workflow_context: Context with previous results

    Returns:
        True if condition met, False otherwise

    Example:
        condition = "anomalies.severity > 0.8"

        If context has:
            workflow_context.results["anomalies"] = {"severity": 0.95}

        Returns: True (task will execute)
    """
```

#### 5. `handle_saga_rollback()`

Handle saga pattern rollback with compensating actions.

```python
def handle_saga_rollback(
    self,
    workflow_context: WorkflowContext,
    failed_task: str
) -> None:
    """
    Execute compensating actions in reverse order.

    Args:
        workflow_context: Context with executed tasks
        failed_task: Name of task that failed

    Example:
        Workflow: [Reserve Cash, Add Position, Update Portfolio]

        If "Update Portfolio" fails:
        1. Compensate "Add Position" → Remove position
        2. Compensate "Reserve Cash" → Release cash
        3. Log failure event
    """
```

### WorkflowDefinition Structure

```python
@dataclass
class WorkflowDefinition:
    """Defines a workflow as a DAG of tasks."""

    name: str
    description: str
    tasks: List[Task]
    saga_enabled: bool = False  # Enable saga pattern
    timeout_seconds: Optional[int] = None

@dataclass
class Task:
    """Defines a single task in a workflow."""

    name: str
    agent: str  # Agent name (e.g., "technical")
    method: str  # Method to call (e.g., "analyze_symbol")
    parameters: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # Conditional execution
    retry_config: Optional[RetryConfig] = None
    cache_key: Optional[str] = None
    compensation: Optional[Compensation] = None  # For saga

@dataclass
class RetryConfig:
    """Configuration for task retries."""

    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [ConnectionError, TimeoutError]
    )
```

### Example Workflow Definition

```python
daily_analysis_workflow = WorkflowDefinition(
    name="daily_analysis",
    description="Complete daily market analysis for PSX",
    tasks=[
        Task(
            name="select_stocks",
            agent="liquidity",
            method="screen_stocks",
            parameters={"min_volume": 500000, "min_price": 20.0},
            depends_on=[],
            cache_key="stocks:${date}"
        ),
        Task(
            name="sync_prices",
            agent="price_store",
            method="update_prices",
            parameters={"symbols": "${select_stocks.output}"},
            depends_on=["select_stocks"],
            retry_config=RetryConfig(max_attempts=5)
        ),
        Task(
            name="technical_analysis",
            agent="technical",
            method="analyze_symbol",
            parameters={"symbol": "${symbol}"},  # Parameterized
            depends_on=["sync_prices"],
            cache_key="technical:${symbol}:${date}"
        ),
        Task(
            name="anomaly_detection",
            agent="anomaly",
            method="detect_anomalies",
            parameters={"symbol": "${symbol}"},
            depends_on=["technical_analysis"]
        ),
        Task(
            name="news_correlation",
            agent="correlator",
            method="correlate_anomalies",
            parameters={"anomalies": "${anomaly_detection.output}"},
            depends_on=["anomaly_detection"]
        )
    ]
)
```

### State Management

The coordinator persists workflow state:

```python
@dataclass
class WorkflowState:
    """Persistent workflow state."""

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus  # RUNNING, COMPLETED, FAILED, PAUSED
    created_at: datetime
    updated_at: datetime
    completed_tasks: List[str]
    pending_tasks: List[str]
    failed_tasks: List[str]
    task_results: Dict[str, Any]
    error: Optional[str] = None
```

**Resumability:**
```python
# Workflow fails at task 5 of 10
# Later, resume:
result = coordinator.execute(
    workflow_def,
    workflow_id="wf_12345"  # Resume from saved state
)
# Skips completed tasks 1-4, resumes at task 5
```

---

## PSXEventBus

### Overview

The `PSXEventBus` implements a publish-subscribe pattern for event-driven communication between components.

### Class Definition

```python
class PSXEventBus:
    """
    In-process event bus for PSX system.

    Features:
    - Thread-safe pub/sub
    - Event filtering by type
    - Wildcard subscriptions
    - Event logging
    - Synchronous delivery (can extend to async)
    """

    def __init__(self, log_events: bool = True):
        """
        Initialize event bus.

        Args:
            log_events: Log all events for debugging
        """
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._lock = threading.Lock()
        self._event_log: List[PSXEvent] = []
        self._log_events = log_events
```

### Key Methods

#### 1. `publish()`

Publish an event to all subscribers.

```python
def publish(self, event: PSXEvent) -> None:
    """
    Publish event to all subscribers.

    Args:
        event: PSXEvent to publish

    Delivery:
        - Synchronous (blocks until all handlers complete)
        - Thread-safe (can publish from multiple threads)
        - Wildcard subscribers receive all events
        - Type-specific subscribers receive filtered events

    Example:
        event = PSXEvent(
            type=EventType.ANOMALY_DETECTED,
            source="anomaly_agent",
            data={"symbol": "OGDC", "severity": 0.95},
            timestamp=datetime.now()
        )
        event_bus.publish(event)
    """
```

#### 2. `subscribe()`

Subscribe to events of a specific type.

```python
def subscribe(
    self,
    event_type: EventType,
    handler: Callable[[PSXEvent], None]
) -> str:
    """
    Subscribe to events of a specific type.

    Args:
        event_type: Type of event to subscribe to
        handler: Callback function (receives PSXEvent)

    Returns:
        Subscription ID (for unsubscribing)

    Example:
        def handle_anomaly(event: PSXEvent):
            severity = event.data["severity"]
            if severity > 0.8:
                print(f"High severity: {event.data['symbol']}")

        sub_id = event_bus.subscribe(
            EventType.ANOMALY_DETECTED,
            handle_anomaly
        )
    """
```

#### 3. `subscribe_wildcard()`

Subscribe to all events.

```python
def subscribe_wildcard(
    self,
    handler: Callable[[PSXEvent], None]
) -> str:
    """
    Subscribe to all events (wildcard subscription).

    Args:
        handler: Callback function

    Returns:
        Subscription ID

    Example:
        def log_all_events(event: PSXEvent):
            print(f"[{event.timestamp}] {event.type}: {event.source}")

        event_bus.subscribe_wildcard(log_all_events)
    """
```

#### 4. `unsubscribe()`

Unsubscribe from events.

```python
def unsubscribe(self, subscription_id: str) -> bool:
    """
    Unsubscribe from events.

    Args:
        subscription_id: ID returned from subscribe()

    Returns:
        True if unsubscribed, False if ID not found
    """
```

#### 5. `get_event_log()`

Get historical event log.

```python
def get_event_log(
    self,
    event_type: Optional[EventType] = None,
    since: Optional[datetime] = None,
    limit: int = 100
) -> List[PSXEvent]:
    """
    Get event history.

    Args:
        event_type: Filter by event type (None = all)
        since: Only events after this time
        limit: Maximum number of events

    Returns:
        List of PSXEvent

    Example:
        # Get last 50 anomaly events
        anomalies = event_bus.get_event_log(
            event_type=EventType.ANOMALY_DETECTED,
            limit=50
        )
    """
```

### Event Types

```python
class EventType(Enum):
    """All event types in PSX system."""

    # Data Events
    PRICE_DATA_UPDATED = "price_data_updated"
    NEWS_FETCHED = "news_fetched"
    FUNDAMENTAL_DATA_UPDATED = "fundamental_data_updated"

    # Analysis Events
    TECHNICAL_ANALYSIS_COMPLETE = "technical_analysis_complete"
    ANOMALY_DETECTED = "anomaly_detected"
    HIGH_SEVERITY_ANOMALY = "high_severity_anomaly"
    NEWS_CORRELATION_COMPLETE = "news_correlation_complete"

    # Portfolio Events
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    PORTFOLIO_UPDATED = "portfolio_updated"

    # Risk Events
    RISK_CHECK_COMPLETE = "risk_check_complete"
    RISK_VIOLATION = "risk_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"

    # Workflow Events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
```

### PSXEvent Structure

```python
@dataclass
class PSXEvent:
    """Event data structure."""

    type: EventType
    source: str  # Component that emitted event
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None  # For event chains
```

### Example: Event-Driven Workflow Trigger

```python
# Set up event-driven workflow trigger
def trigger_investigation(event: PSXEvent):
    """Trigger investigation workflow for high-severity anomalies."""
    if event.data["severity"] > 0.8:
        orchestrator.run_workflow(
            "high_severity_investigation",
            parameters={
                "symbol": event.data["symbol"],
                "anomaly_type": event.data["type"]
            }
        )

# Subscribe to anomaly events
event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    trigger_investigation
)

# Now, when anomaly agent emits event, workflow auto-triggers
anomaly_agent.detect_anomalies("OGDC")
# → Emits ANOMALY_DETECTED event
# → trigger_investigation() called
# → Workflow executes automatically
```

---

## ExecutionEngine

### Overview

The `ExecutionEngine` handles the actual execution of tasks with parallelism, retries, caching, and resource management.

### Class Definition

```python
class ExecutionEngine:
    """
    Engine for executing workflow tasks.

    Features:
    - Parallel execution (ThreadPoolExecutor)
    - Retry logic with exponential backoff
    - Result caching (TTL-based)
    - Rate limiting (semaphores)
    - Error handling
    """

    def __init__(
        self,
        max_workers: int = 4,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 1800,
        api_rate_limit: int = 2
    ):
        """
        Initialize execution engine.

        Args:
            max_workers: Number of parallel workers
            enable_caching: Enable result caching
            cache_ttl_seconds: Cache TTL in seconds
            api_rate_limit: Max concurrent API calls
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_enabled = enable_caching
        self._cache_ttl = cache_ttl_seconds
        self._api_semaphore = threading.Semaphore(api_rate_limit)
```

### Key Methods

#### 1. `execute_tasks()`

Execute multiple tasks in parallel.

```python
def execute_tasks(
    self,
    tasks: List[Task],
    workflow_context: WorkflowContext
) -> Dict[str, TaskResult]:
    """
    Execute multiple tasks in parallel.

    Args:
        tasks: List of tasks to execute
        workflow_context: Shared context

    Returns:
        Dict mapping task name to TaskResult

    Execution Strategy:
        - Tasks without dependencies execute immediately
        - Tasks with dependencies wait for completion
        - Uses ThreadPoolExecutor for parallelism
        - Respects max_workers limit

    Example:
        # 3 tasks with no dependencies → all run in parallel
        # 2 tasks depending on first 3 → wait, then run in parallel
    """
```

#### 2. `execute_task()`

Execute a single task with retry logic.

```python
def execute_task(
    self,
    task: Task,
    workflow_context: WorkflowContext
) -> TaskResult:
    """
    Execute a single task.

    Args:
        task: Task definition
        workflow_context: Shared context

    Returns:
        TaskResult

    Execution Flow:
        1. Check cache (if enabled)
        2. If cached and valid → return cached result
        3. Else:
           a. Resolve parameters from context
           b. Load agent via AgentAdapter
           c. Call agent method
           d. Retry on failure (exponential backoff)
           e. Cache result (if successful)
           f. Return TaskResult
    """
```

#### 3. `check_cache()`

Check if task result is cached.

```python
def check_cache(self, cache_key: str) -> Optional[Any]:
    """
    Check cache for task result.

    Args:
        cache_key: Unique cache key

    Returns:
        Cached result if valid, None otherwise

    Cache Entry:
        {
            "result": <task_result>,
            "cached_at": <timestamp>,
            "ttl": <seconds>
        }

    Validity:
        - Entry exists AND
        - (now - cached_at) < ttl
    """
```

#### 4. `set_cache()`

Cache a task result.

```python
def set_cache(
    self,
    cache_key: str,
    result: Any,
    ttl: Optional[int] = None
) -> None:
    """
    Cache a task result.

    Args:
        cache_key: Unique cache key
        result: Result to cache
        ttl: Optional TTL override (uses default if None)
    """
```

#### 5. `retry_with_backoff()`

Retry a function with exponential backoff.

```python
def retry_with_backoff(
    self,
    func: Callable,
    retry_config: RetryConfig,
    task_name: str
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry
        retry_config: Retry configuration
        task_name: Task name (for logging)

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted

    Backoff Formula:
        wait_time = min(
            backoff_multiplier ** attempt,
            max_backoff_seconds
        )

    Example:
        attempt=1: wait 2s (2^1)
        attempt=2: wait 4s (2^2)
        attempt=3: wait 8s (2^3)
        attempt=4: wait 16s (2^4)
        attempt=5: wait 32s (2^5)
        attempt=6: wait 60s (capped at max_backoff_seconds)
    """
```

### Caching Strategy

**Cache Keys:**
```python
# Task-specific cache key
cache_key = f"{agent}:{method}:{param_hash}:{date}"

# Examples:
"technical:analyze_symbol:OGDC:20260216"
"news:fetch_news:PKR:20260216"
"anomaly:detect:OGDC:20260216"
```

**TTL by Task Type:**
```python
CACHE_TTL_MAP = {
    "news": 1800,        # 30 minutes
    "technical": 3600,   # 1 hour
    "fundamental": 86400, # 24 hours
    "prices": 300,       # 5 minutes
    "anomaly": 3600      # 1 hour
}
```

**Cache Invalidation:**
- Automatic (TTL expiry)
- Manual (clear_cache() method)
- Event-driven (e.g., news published → clear news cache)

### Resource Management

**Thread Pool:**
- Default: 4 workers
- Configurable via `max_workers`
- Suitable for I/O-bound tasks (API calls)

**API Rate Limiting:**
- Semaphore limits concurrent API calls
- Prevents overwhelming external APIs
- Default: 2 concurrent calls

**Memory Management:**
- Cache size limit (default: 1000 entries)
- LRU eviction when limit exceeded
- Periodic cleanup of expired entries

---

## StateManager

### Overview

The `StateManager` persists workflow state and execution history to SQLite.

### Class Definition

```python
class StateManager:
    """
    Manages workflow state persistence.

    Features:
    - Save/load workflow state
    - Task result persistence
    - Workflow history
    - Resume capability
    """

    def __init__(self, db_path: str):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_tables()
```

### Database Schema

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

### Key Methods

#### 1. `save_workflow_state()`

Save workflow state to database.

```python
def save_workflow_state(self, state: WorkflowState) -> None:
    """
    Save workflow state.

    Args:
        state: WorkflowState to persist

    Persists:
        - Workflow metadata
        - Task statuses
        - Task results
        - Error information
    """
```

#### 2. `load_workflow_state()`

Load workflow state from database.

```python
def load_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
    """
    Load workflow state.

    Args:
        workflow_id: Workflow ID

    Returns:
        WorkflowState if found, None otherwise

    Use Case:
        Resume a failed workflow from last checkpoint
    """
```

#### 3. `save_task_result()`

Save individual task result.

```python
def save_task_result(
    self,
    workflow_id: str,
    task_name: str,
    result: TaskResult
) -> None:
    """
    Save task result.

    Args:
        workflow_id: Parent workflow ID
        task_name: Task name
        result: TaskResult to save
    """
```

#### 4. `get_workflow_history()`

Get workflow execution history.

```python
def get_workflow_history(
    self,
    workflow_name: Optional[str] = None,
    limit: int = 100
) -> List[WorkflowState]:
    """
    Get workflow execution history.

    Args:
        workflow_name: Filter by workflow name
        limit: Maximum number of results

    Returns:
        List of WorkflowState (most recent first)
    """
```

#### 5. `cleanup_old_workflows()`

Clean up old workflow data.

```python
def cleanup_old_workflows(self, days: int = 30) -> int:
    """
    Delete workflow data older than specified days.

    Args:
        days: Delete workflows older than this

    Returns:
        Number of workflows deleted
    """
```

---

## AgentAdapter

### Overview

The `AgentAdapter` provides a **dynamic loading mechanism** for existing agents without modifying their code.

### Class Definition

```python
class AgentAdapter:
    """
    Adapter for dynamically loading and calling agents.

    Features:
    - Dynamic agent loading (no hard-coded imports)
    - Method invocation with parameter mapping
    - Event emission (optional, backward compatible)
    - Caching of agent instances
    """

    def __init__(self, event_bus: Optional[PSXEventBus] = None):
        """
        Initialize agent adapter.

        Args:
            event_bus: Optional event bus for event emission
        """
        self._agent_instances: Dict[str, Any] = {}
        self._event_bus = event_bus
```

### Key Methods

#### 1. `call_method()`

Dynamically call an agent method.

```python
def call_method(
    self,
    agent_name: str,
    method_name: str,
    parameters: Dict[str, Any]
) -> Any:
    """
    Call an agent method dynamically.

    Args:
        agent_name: Agent identifier (e.g., "technical")
        method_name: Method to call (e.g., "analyze_symbol")
        parameters: Method parameters

    Returns:
        Method result

    Example:
        result = adapter.call_method(
            agent_name="technical",
            method_name="analyze_symbol",
            parameters={"symbol": "OGDC", "period": "1mo"}
        )
    """
```

#### 2. `load_agent()`

Load an agent class dynamically.

```python
def load_agent(self, agent_name: str) -> Any:
    """
    Load agent class dynamically.

    Args:
        agent_name: Agent identifier

    Returns:
        Agent instance

    Caching:
        - First call: Load and instantiate
        - Subsequent calls: Return cached instance

    Mapping:
        agent_name -> module.ClassName

        "technical" -> "psx_technical_agent.PSXTechnicalAgent"
        "anomaly" -> "psx_anomaly_agent.PSXAnomalyAgent"
        etc.
    """
```

### Agent Name Mapping

```python
AGENT_MAPPING = {
    "liquidity": {
        "module": "psx_liquidity_screener",
        "class": "PSXLiquidityScreener"
    },
    "technical": {
        "module": "psx_technical_agent",
        "class": "PSXTechnicalAgent"
    },
    "fundamental": {
        "module": "psx_fundamental_agent",
        "class": "PSXFundamentalAgent"
    },
    "anomaly": {
        "module": "psx_anomaly_agent",
        "class": "PSXAnomalyAgent"
    },
    "price_store": {
        "module": "psx_price_store",
        "class": "PSXPriceStore"
    },
    "news": {
        "module": "psx_news_agent",
        "class": "PSXNewsAgent"
    },
    "correlator": {
        "module": "psx_news_price_correlator",
        "class": "PSXNewsPriceCorrelator"
    },
    "portfolio": {
        "module": "psx_portfolio_agent",
        "class": "PSXPortfolioAgent"
    },
    "risk": {
        "module": "psx_risk_agent",
        "class": "PSXRiskAgent"
    }
}
```

### Backward Compatibility

The adapter works with **existing agents unchanged**:

**Existing Agent (no modifications needed):**
```python
class PSXTechnicalAgent:
    def __init__(self, db_path="data/psx_data.db"):
        self.db_path = db_path

    def analyze_symbol(self, symbol: str, period: str = "1mo"):
        # Existing implementation
        return analysis_result
```

**Orchestration calls it via adapter:**
```python
# No changes to agent code required
result = adapter.call_method(
    "technical",
    "analyze_symbol",
    {"symbol": "OGDC", "period": "1mo"}
)
```

### Optional Event Emission

Agents can **optionally** emit events for enhanced integration:

```python
class PSXTechnicalAgent:
    def __init__(self, db_path="data/psx_data.db", event_bus=None):
        self.db_path = db_path
        self.event_bus = event_bus  # Optional

    def analyze_symbol(self, symbol: str, period: str = "1mo"):
        result = self._perform_analysis(symbol, period)

        # Optional: emit event if event_bus provided
        if self.event_bus:
            self.event_bus.publish(PSXEvent(
                type=EventType.TECHNICAL_ANALYSIS_COMPLETE,
                source="technical_agent",
                data={"symbol": symbol, "result": result}
            ))

        return result
```

**Benefits:**
- Works with old agents (no event bus)
- Works with new agents (with event bus)
- Gradual migration path

---

## Component Integration

### Complete Integration Example

```python
# Initialize all components
db_path = "data/psx_data.db"

# 1. Event Bus
event_bus = PSXEventBus(log_events=True)

# 2. Agent Adapter
adapter = AgentAdapter(event_bus=event_bus)

# 3. State Manager
state_manager = StateManager(db_path=db_path)

# 4. Execution Engine
execution_engine = ExecutionEngine(
    max_workers=4,
    enable_caching=True,
    cache_ttl_seconds=1800
)

# 5. Workflow Coordinator
coordinator = WorkflowCoordinator(
    execution_engine=execution_engine,
    state_manager=state_manager,
    event_bus=event_bus
)

# 6. Orchestration Agent (Main API)
orchestrator = PSXOrchestrationAgent(
    coordinator=coordinator,
    event_bus=event_bus,
    state_manager=state_manager,
    db_path=db_path
)

# Set up event-driven workflow triggers
def trigger_investigation(event: PSXEvent):
    if event.data["severity"] > 0.8:
        orchestrator.run_workflow(
            "high_severity_investigation",
            parameters={"symbol": event.data["symbol"]}
        )

event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    trigger_investigation
)

# Run daily analysis workflow
result = orchestrator.run_daily_analysis(
    min_volume=500000,
    min_price=20.0
)

print(f"Workflow Status: {result.status}")
print(f"Execution Time: {result.execution_time}s")
print(f"Tasks Completed: {len(result.completed_tasks)}")
```

### Data Flow Diagram

```
User Request
     │
     ▼
PSXOrchestrationAgent
     │
     ├──→ WorkflowCoordinator
     │         │
     │         ├──→ Build DAG
     │         │
     │         └──→ ExecutionEngine
     │                   │
     │                   ├──→ Check Cache (StateManager)
     │                   │
     │                   ├──→ Execute Tasks (AgentAdapter)
     │                   │         │
     │                   │         └──→ Load Agent → Call Method
     │                   │                   │
     │                   │                   └──→ Existing Agent
     │                   │
     │                   └──→ Cache Results (StateManager)
     │
     └──→ PSXEventBus
              │
              └──→ Event Handlers
                        │
                        └──→ Workflow Triggers
```

---

## Summary

The 6 core components work together to provide a **complete orchestration system**:

| Component | Responsibility | Key Features |
|-----------|---------------|--------------|
| **PSXOrchestrationAgent** | Main API | High-level workflows, user interface |
| **WorkflowCoordinator** | Workflow execution | DAG scheduling, saga pattern, state management |
| **PSXEventBus** | Event routing | Pub/sub, event logging, loose coupling |
| **ExecutionEngine** | Task execution | Parallelism, retries, caching, rate limiting |
| **StateManager** | Persistence | Workflow state, history, resumability |
| **AgentAdapter** | Agent integration | Dynamic loading, backward compatibility |

Together, they enable:
- ✅ **3x faster execution** (parallel tasks)
- ✅ **Event-driven automation** (reactive workflows)
- ✅ **Resilient execution** (retry, saga, resumability)
- ✅ **Smart caching** (TTL-based, 90s savings)
- ✅ **Zero agent modifications** (adapter pattern)
- ✅ **Complete observability** (events, state, logs)

---

**Next**: See [03_AGENT_CATALOG.md](03_AGENT_CATALOG.md) for detailed agent specifications.
