# API Reference

## Table of Contents

1. [PSXOrchestrationAgent](#psxorchestrationagent)
2. [WorkflowCoordinator](#workflowcoordinator)
3. [PSXEventBus](#psxeventbus)
4. [ExecutionEngine](#executionengine)
5. [StateManager](#statemanager)
6. [Data Models](#data-models)

---

## PSXOrchestrationAgent

Main entry point for the orchestration system.

### Constructor

```python
PSXOrchestrationAgent(
    db_path: str = "data/psx_data.db",
    config_path: Optional[str] = None,
    max_workers: int = 4,
    enable_caching: bool = True,
    cache_ttl_seconds: int = 1800
)
```

**Parameters:**
- `db_path`: Path to SQLite database
- `config_path`: Optional YAML config file
- `max_workers`: Parallel workers (default: 4)
- `enable_caching`: Enable result caching (default: True)
- `cache_ttl_seconds`: Cache TTL in seconds (default: 1800)

### Methods

#### `run_workflow()`

```python
def run_workflow(
    workflow_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    resume_from: Optional[str] = None
) -> WorkflowResult
```

Run a predefined workflow by name.

**Parameters:**
- `workflow_name`: Name of workflow to run
- `parameters`: Optional workflow parameters
- `resume_from`: Optional workflow ID to resume

**Returns:** `WorkflowResult`

**Raises:** `WorkflowNotFoundError`, `WorkflowExecutionError`

**Example:**
```python
result = agent.run_workflow(
    "daily_analysis",
    parameters={"min_volume": 500000}
)
```

#### `run_daily_analysis()`

```python
def run_daily_analysis(
    min_volume: int = 500000,
    min_price: float = 20.0,
    cache_enabled: bool = True
) -> WorkflowResult
```

Convenience method for daily analysis workflow.

**Parameters:**
- `min_volume`: Minimum average volume
- `min_price`: Minimum stock price
- `cache_enabled`: Enable caching

**Returns:** `WorkflowResult`

#### `trigger_workflow()`

```python
def trigger_workflow(
    event: PSXEvent,
    workflow_mappings: Optional[Dict[str, str]] = None
) -> Optional[WorkflowResult]
```

Trigger workflow based on event.

**Parameters:**
- `event`: PSXEvent that triggered workflow
- `workflow_mappings`: Optional custom event→workflow mappings

**Returns:** `WorkflowResult` if triggered, `None` otherwise

#### `execute_custom_workflow()`

```python
def execute_custom_workflow(
    workflow_def: WorkflowDefinition,
    parameters: Optional[Dict[str, Any]] = None
) -> WorkflowResult
```

Execute a custom workflow definition.

**Parameters:**
- `workflow_def`: WorkflowDefinition instance
- `parameters`: Optional parameters

**Returns:** `WorkflowResult`

#### `get_workflow_status()`

```python
def get_workflow_status(workflow_id: str) -> WorkflowStatus
```

Get status of a workflow execution.

**Parameters:**
- `workflow_id`: Unique workflow ID

**Returns:** `WorkflowStatus`

#### `list_workflows()`

```python
def list_workflows() -> List[str]
```

List all registered workflow names.

**Returns:** List of workflow names

---

## WorkflowCoordinator

Manages workflow execution and task scheduling.

### Constructor

```python
WorkflowCoordinator(
    execution_engine: ExecutionEngine,
    state_manager: StateManager,
    event_bus: PSXEventBus
)
```

### Methods

#### `execute()`

```python
def execute(
    workflow_def: WorkflowDefinition,
    parameters: Optional[Dict[str, Any]] = None,
    workflow_id: Optional[str] = None
) -> WorkflowResult
```

Execute a workflow definition.

**Parameters:**
- `workflow_def`: Workflow definition (DAG)
- `parameters`: Runtime parameters
- `workflow_id`: Optional ID for resuming

**Returns:** `WorkflowResult`

#### `build_dag()`

```python
def build_dag(workflow_def: WorkflowDefinition) -> nx.DiGraph
```

Build DAG from workflow definition.

**Parameters:**
- `workflow_def`: Workflow definition

**Returns:** NetworkX DiGraph

#### `evaluate_condition()`

```python
def evaluate_condition(
    condition: str,
    workflow_context: WorkflowContext
) -> bool
```

Evaluate conditional task execution.

**Parameters:**
- `condition`: Python expression
- `workflow_context`: Context with results

**Returns:** `True` if condition met

---

## PSXEventBus

In-process publish-subscribe event bus.

### Constructor

```python
PSXEventBus(log_events: bool = True)
```

**Parameters:**
- `log_events`: Log all events for debugging

### Methods

#### `publish()`

```python
def publish(event: PSXEvent) -> None
```

Publish event to all subscribers.

**Parameters:**
- `event`: PSXEvent to publish

#### `subscribe()`

```python
def subscribe(
    event_type: EventType,
    handler: Callable[[PSXEvent], None]
) -> str
```

Subscribe to events of a specific type.

**Parameters:**
- `event_type`: Type of event
- `handler`: Callback function

**Returns:** Subscription ID

**Example:**
```python
def handle_anomaly(event: PSXEvent):
    print(f"Anomaly: {event.data['symbol']}")

sub_id = event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    handle_anomaly
)
```

#### `subscribe_wildcard()`

```python
def subscribe_wildcard(
    handler: Callable[[PSXEvent], None]
) -> str
```

Subscribe to all events.

**Parameters:**
- `handler`: Callback function

**Returns:** Subscription ID

#### `unsubscribe()`

```python
def unsubscribe(subscription_id: str) -> bool
```

Unsubscribe from events.

**Parameters:**
- `subscription_id`: ID from subscribe()

**Returns:** `True` if unsubscribed

#### `get_event_log()`

```python
def get_event_log(
    event_type: Optional[EventType] = None,
    since: Optional[datetime] = None,
    limit: int = 100
) -> List[PSXEvent]
```

Get event history.

**Parameters:**
- `event_type`: Filter by type (None = all)
- `since`: Only events after this time
- `limit`: Maximum events

**Returns:** List of PSXEvent

---

## ExecutionEngine

Handles task execution with parallelism and caching.

### Constructor

```python
ExecutionEngine(
    max_workers: int = 4,
    enable_caching: bool = True,
    cache_ttl_seconds: int = 1800,
    api_rate_limit: int = 2
)
```

**Parameters:**
- `max_workers`: Parallel workers
- `enable_caching`: Enable caching
- `cache_ttl_seconds`: Cache TTL
- `api_rate_limit`: Max concurrent API calls

### Methods

#### `execute_tasks()`

```python
def execute_tasks(
    tasks: List[Task],
    workflow_context: WorkflowContext
) -> Dict[str, TaskResult]
```

Execute multiple tasks in parallel.

**Parameters:**
- `tasks`: List of tasks
- `workflow_context`: Shared context

**Returns:** Dict mapping task name to TaskResult

#### `execute_task()`

```python
def execute_task(
    task: Task,
    workflow_context: WorkflowContext
) -> TaskResult
```

Execute a single task.

**Parameters:**
- `task`: Task definition
- `workflow_context`: Shared context

**Returns:** `TaskResult`

#### `check_cache()`

```python
def check_cache(cache_key: str) -> Optional[Any]
```

Check if task result is cached.

**Parameters:**
- `cache_key`: Unique cache key

**Returns:** Cached result or None

#### `set_cache()`

```python
def set_cache(
    cache_key: str,
    result: Any,
    ttl: Optional[int] = None
) -> None
```

Cache a task result.

**Parameters:**
- `cache_key`: Unique cache key
- `result`: Result to cache
- `ttl`: Optional TTL override

---

## StateManager

Manages workflow state persistence.

### Constructor

```python
StateManager(db_path: str)
```

**Parameters:**
- `db_path`: Path to SQLite database

### Methods

#### `save_workflow_state()`

```python
def save_workflow_state(state: WorkflowState) -> None
```

Save workflow state to database.

**Parameters:**
- `state`: WorkflowState to persist

#### `load_workflow_state()`

```python
def load_workflow_state(workflow_id: str) -> Optional[WorkflowState]
```

Load workflow state from database.

**Parameters:**
- `workflow_id`: Workflow ID

**Returns:** WorkflowState or None

#### `get_workflow_history()`

```python
def get_workflow_history(
    workflow_name: Optional[str] = None,
    limit: int = 100
) -> List[WorkflowState]
```

Get workflow execution history.

**Parameters:**
- `workflow_name`: Filter by workflow name
- `limit`: Maximum results

**Returns:** List of WorkflowState

---

## Data Models

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_name: str
    status: str  # "completed", "failed", "partial"
    started_at: datetime
    completed_at: datetime
    execution_time: float  # seconds
    completed_tasks: List[str]
    failed_tasks: List[str]
    data: Dict[str, Any]
    error: Optional[str] = None
```

### WorkflowStatus

```python
@dataclass
class WorkflowStatus:
    workflow_id: str
    state: str  # "running", "completed", "failed"
    progress: float  # 0-1
    completed_tasks: int
    total_tasks: int
    current_task: Optional[str]
    estimated_completion: Optional[datetime]
```

### PSXEvent

```python
@dataclass
class PSXEvent:
    type: EventType
    source: str
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str
    correlation_id: Optional[str] = None
```

### EventType

```python
class EventType(Enum):
    # Data Events
    PRICE_DATA_UPDATED = "price_data_updated"
    NEWS_FETCHED = "news_fetched"
    
    # Analysis Events
    TECHNICAL_ANALYSIS_COMPLETE = "technical_analysis_complete"
    ANOMALY_DETECTED = "anomaly_detected"
    HIGH_SEVERITY_ANOMALY = "high_severity_anomaly"
    
    # Portfolio Events
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    PORTFOLIO_UPDATED = "portfolio_updated"
    
    # Risk Events
    RISK_VIOLATION = "risk_violation"
    RISK_CHECK_COMPLETE = "risk_check_complete"
    
    # Workflow Events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
```

### TaskResult

```python
@dataclass
class TaskResult:
    task_name: str
    status: str  # "success", "failed", "skipped"
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
```

### RetryConfig

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0
    retryable_exceptions: List[Type[Exception]] = [
        ConnectionError, TimeoutError
    ]
```

---

## Error Handling

### Exceptions

```python
class WorkflowNotFoundError(Exception):
    """Raised when workflow name not found."""
    pass

class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    def __init__(self, message, failed_task, original_error):
        self.failed_task = failed_task
        self.original_error = original_error
        super().__init__(message)

class TaskExecutionError(Exception):
    """Raised when task execution fails."""
    pass

class ValidationError(Exception):
    """Raised when validation fails."""
    pass
```

### Error Handling Pattern

```python
try:
    result = orchestrator.run_workflow("daily_analysis")
except WorkflowNotFoundError as e:
    print(f"Workflow not found: {e}")
except WorkflowExecutionError as e:
    print(f"Workflow failed at task: {e.failed_task}")
    print(f"Original error: {e.original_error}")
    # Optionally resume from failure
    result = orchestrator.run_workflow(
        "daily_analysis",
        resume_from=e.workflow_id
    )
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Complete Usage Example

```python
from psx_orchestration_agent import PSXOrchestrationAgent
from psx_orchestration_agent.event_bus import EventType

# Initialize agent
agent = PSXOrchestrationAgent(
    db_path="data/psx_data.db",
    max_workers=4,
    enable_caching=True
)

# Set up event-driven workflow
def investigate_anomalies(event):
    if event.data["severity"] > 0.8:
        agent.run_workflow(
            "high_severity_investigation",
            parameters={"anomaly": event.data}
        )

agent.event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    investigate_anomalies
)

# Run daily analysis
result = agent.run_daily_analysis(
    min_volume=500000,
    min_price=20.0
)

# Check results
print(f"Status: {result.status}")
print(f"Execution time: {result.execution_time}s")
print(f"Analyzed {len(result.data['symbols'])} stocks")
print(f"Found {len(result.data['anomalies'])} anomalies")

# Get workflow status
status = agent.get_workflow_status(result.workflow_id)
print(f"Progress: {status.completed_tasks}/{status.total_tasks}")
```

---

**Next**: See [06_INTEGRATION_GUIDE.md](06_INTEGRATION_GUIDE.md) for integration instructions.
