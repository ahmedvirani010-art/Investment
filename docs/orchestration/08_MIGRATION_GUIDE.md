# Migration Guide

## Overview

This guide helps you migrate from the current **sequential pipeline** (`run_integrated_analysis.py`) to the **orchestrated system**.

**Migration Philosophy:** Zero disruption, gradual adoption, backward compatible.

---

## Migration Path

### Phase 1: Parallel Running (Week 1)
Run both systems side-by-side without changes.

### Phase 2: Validation (Week 2)
Validate orchestrated system produces same results.

### Phase 3: Gradual Adoption (Week 3-4)
Migrate workflows one at a time.

### Phase 4: Full Migration (Week 5+)
Deprecate sequential pipeline, use orchestration exclusively.

---

## Phase 1: Parallel Running

### Step 1: Install Orchestration

```bash
# Install dependencies
pip install networkx schedule

# No code changes required for existing agents
```

### Step 2: Run Both Systems

```python
# Option A: Keep running existing sequential pipeline
python run_integrated_analysis.py

# Option B: Also run orchestrated version
python run_orchestration.py
```

**`run_orchestration.py`:**
```python
from psx_orchestration_agent import PSXOrchestrationAgent

agent = PSXOrchestrationAgent()
result = agent.run_daily_analysis(
    min_volume=500000,
    min_price=20.0
)

print(f"Orchestrated analysis complete: {result.status}")
print(f"Execution time: {result.execution_time}s")
```

### Step 3: Compare Results

```python
# Run both and compare
import subprocess
import time

# Run sequential
start = time.time()
subprocess.run(["python", "run_integrated_analysis.py"])
sequential_time = time.time() - start

# Run orchestrated
start = time.time()
result = agent.run_daily_analysis()
orchestrated_time = time.time() - start

print(f"Sequential: {sequential_time:.0f}s")
print(f"Orchestrated: {orchestrated_time:.0f}s")
print(f"Speedup: {sequential_time / orchestrated_time:.1f}x")
```

---

## Phase 2: Validation

### Validate Data Consistency

```python
# Ensure both systems produce same results
def validate_consistency():
    # Run sequential pipeline
    sequential_results = run_sequential_analysis()
    
    # Run orchestrated workflow
    orchestrated_results = agent.run_daily_analysis()
    
    # Compare results
    assert set(sequential_results['symbols']) == set(orchestrated_results.data['symbols'])
    assert len(sequential_results['anomalies']) == len(orchestrated_results.data['anomalies'])
    
    print("✅ Results match!")
```

### Validate Performance

```python
# Measure performance improvement
def benchmark_performance(runs=5):
    sequential_times = []
    orchestrated_times = []
    
    for i in range(runs):
        # Sequential
        start = time.time()
        run_sequential_analysis()
        sequential_times.append(time.time() - start)
        
        # Orchestrated
        start = time.time()
        agent.run_daily_analysis()
        orchestrated_times.append(time.time() - start)
    
    avg_sequential = sum(sequential_times) / len(sequential_times)
    avg_orchestrated = sum(orchestrated_times) / len(orchestrated_times)
    
    print(f"Avg Sequential: {avg_sequential:.0f}s")
    print(f"Avg Orchestrated: {avg_orchestrated:.0f}s")
    print(f"Improvement: {(avg_sequential - avg_orchestrated) / avg_sequential * 100:.1f}%")
```

---

## Phase 3: Gradual Adoption

### Week 3: Migrate Daily Analysis

```python
# Replace sequential script with orchestrated version
# OLD: run_integrated_analysis.py
# NEW: run_orchestration.py

# Update cron job
# OLD: 0 18 * * 1-5 python run_integrated_analysis.py
# NEW: 0 18 * * 1-5 python run_orchestration.py
```

### Week 4: Add Event-Driven Workflows

```python
# Add automatic anomaly investigation
def setup_event_triggers():
    # High-severity anomaly investigation
    agent.event_bus.subscribe(
        EventType.HIGH_SEVERITY_ANOMALY,
        lambda event: agent.run_workflow(
            "high_severity_investigation",
            parameters={"anomaly": event.data}
        )
    )
    
    # Risk violation alerts
    agent.event_bus.subscribe(
        EventType.RISK_VIOLATION,
        lambda event: send_alert(event.data)
    )

setup_event_triggers()
```

---

## Phase 4: Full Migration

### Deprecate Sequential Pipeline

```python
# Mark run_integrated_analysis.py as deprecated
print("⚠️ WARNING: This script is deprecated. Use run_orchestration.py")
print("Migration guide: docs/orchestration/08_MIGRATION_GUIDE.md")

# Optionally redirect to orchestration
from psx_orchestration_agent import PSXOrchestrationAgent
agent = PSXOrchestrationAgent()
result = agent.run_daily_analysis()
```

### Update Documentation

```markdown
# OLD README
## Running Analysis
python run_integrated_analysis.py

# NEW README
## Running Analysis
python run_orchestration.py

# Or use specific workflows
python -c "from psx_orchestration_agent import PSXOrchestrationAgent; agent = PSXOrchestrationAgent(); agent.run_daily_analysis()"
```

---

## Migration Checklist

### Pre-Migration
- [ ] Install dependencies (networkx, schedule)
- [ ] Run orchestration in parallel for 1 week
- [ ] Validate results match sequential pipeline
- [ ] Measure performance improvement
- [ ] Test event-driven workflows

### Migration
- [ ] Update scheduled jobs (cron/schedule)
- [ ] Replace sequential scripts with orchestration calls
- [ ] Add event-driven workflow triggers
- [ ] Enable result caching
- [ ] Set up monitoring

### Post-Migration
- [ ] Deprecate run_integrated_analysis.py
- [ ] Update documentation
- [ ] Train team on new workflows
- [ ] Monitor performance in production
- [ ] Archive sequential pipeline code

---

## Rollback Plan

If issues arise, rollback is simple:

```bash
# Revert to sequential pipeline
python run_integrated_analysis.py

# Update cron
crontab -e
# Change back to run_integrated_analysis.py
```

**Rollback is safe because:**
- ✅ Existing agents unchanged
- ✅ Sequential pipeline still functional
- ✅ Same database, same data
- ✅ No destructive changes

---

## Common Migration Issues

### Issue 1: Performance Regression

**Symptom:** Orchestrated system slower than sequential

**Causes:**
- Cache disabled
- Too few workers
- Network issues

**Solutions:**
```python
# Enable caching
agent = PSXOrchestrationAgent(enable_caching=True)

# Increase workers
agent = PSXOrchestrationAgent(max_workers=8)

# Check network
# yfinance rate limits may require retry config
```

### Issue 2: Different Results

**Symptom:** Orchestrated results differ from sequential

**Causes:**
- Cache returning stale data
- Parallel execution order differences
- Timezone/timestamp differences

**Solutions:**
```python
# Disable cache for comparison
agent = PSXOrchestrationAgent(enable_caching=False)

# Force fresh data
result = agent.run_daily_analysis(cache_enabled=False)

# Clear cache
agent.execution_engine.clear_cache()
```

### Issue 3: Event Handlers Not Triggering

**Symptom:** Event-driven workflows not executing

**Causes:**
- Events not subscribed
- Event emission not enabled in agents

**Solutions:**
```python
# Verify subscription
print(agent.event_bus._subscribers)

# Enable event emission in agents (optional)
# See Agent Integration guide
```

---

## Best Practices

### 1. Gradual Migration
Don't migrate everything at once. Start with one workflow, validate, then proceed.

### 2. Monitor Performance
Track execution times before and after migration.

```python
# Log execution times
result = agent.run_daily_analysis()
with open("performance.log", "a") as f:
    f.write(f"{datetime.now()},{result.execution_time}\n")
```

### 3. Keep Sequential Pipeline
Keep the sequential pipeline functional for at least 1 month after migration as a fallback.

### 4. Document Changes
Update all documentation, READMEs, and team guides.

### 5. Train Team
Ensure team understands new workflows and how to debug issues.

---

## Summary

Migration is:
- ✅ **Zero disruption** - Existing agents unchanged
- ✅ **Gradual** - Migrate one workflow at a time
- ✅ **Reversible** - Easy rollback if needed
- ✅ **Low risk** - Parallel running validates correctness

**Timeline:**
- Week 1: Parallel running
- Week 2: Validation
- Week 3-4: Gradual adoption
- Week 5+: Full migration

**Expected Benefits:**
- 3x faster execution
- Event-driven automation
- Better error handling
- Real-time portfolio/risk management

---

**Next**: See [09_EXAMPLES_AND_USE_CASES.md](09_EXAMPLES_AND_USE_CASES.md) for practical examples.
