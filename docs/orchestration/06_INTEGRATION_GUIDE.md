# Integration Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Basic Setup](#basic-setup)
4. [Agent Integration](#agent-integration)
5. [Event-Driven Workflows](#event-driven-workflows)
6. [Scheduled Workflows](#scheduled-workflows)
7. [CLI Integration](#cli-integration)
8. [Testing](#testing)

---

## Quick Start

### 5-Minute Setup

```bash
# 1. Navigate to project
cd Investment

# 2. Install dependencies (if needed)
pip install networkx schedule

# 3. Create orchestration module
mkdir psx_orchestration_agent
touch psx_orchestration_agent/__init__.py

# 4. Initialize agent
python
>>> from psx_orchestration_agent import PSXOrchestrationAgent
>>> agent = PSXOrchestrationAgent()
>>> result = agent.run_daily_analysis()
>>> print(f"Analyzed {len(result.data['symbols'])} stocks in {result.execution_time}s")
```

---

## Installation

### Dependencies

```bash
# Core dependencies
pip install networkx  # DAG workflow management
pip install schedule   # Scheduled workflows (optional)

# Already have (from existing agents)
# - sqlite3 (built-in)
# - pandas
# - yfinance
# - feedparser
```

### Project Structure

```
Investment/
├── psx_orchestration_agent/
│   ├── __init__.py
│   ├── agent.py               # Main PSXOrchestrationAgent
│   ├── workflow_coordinator.py
│   ├── event_bus.py
│   ├── execution_engine.py
│   ├── state_manager.py
│   ├── agent_adapter.py
│   ├── workflow_templates.py
│   └── models.py              # Data models
├── psx_liquidity_screener/    # Existing agents (unchanged)
├── psx_price_store/
├── psx_technical_agent/
├── ... (other agents)
├── data/
│   └── psx_data.db            # Shared SQLite database
├── docs/
│   └── orchestration/         # Documentation
└── run_orchestration.py       # Main entry point
```

---

## Basic Setup

### Step 1: Initialize Agent

```python
# run_orchestration.py
from psx_orchestration_agent import PSXOrchestrationAgent

# Initialize with default settings
agent = PSXOrchestrationAgent(
    db_path="data/psx_data.db",
    max_workers=4,
    enable_caching=True,
    cache_ttl_seconds=1800  # 30 minutes
)
```

### Step 2: Run Your First Workflow

```python
# Run daily analysis
result = agent.run_daily_analysis(
    min_volume=500000,
    min_price=20.0
)

# Print results
print(f"Workflow: {result.workflow_name}")
print(f"Status: {result.status}")
print(f"Execution Time: {result.execution_time:.2f}s")
print(f"Stocks Analyzed: {len(result.data['symbols'])}")
print(f"Anomalies Found: {len(result.data['anomalies'])}")

# Access detailed results
for anomaly in result.data['anomalies']:
    if anomaly['severity'] > 0.8:
        print(f"High severity anomaly: {anomaly['symbol']} - {anomaly['type']}")
```

### Step 3: Check Workflow Status

```python
# Get workflow status
status = agent.get_workflow_status(result.workflow_id)
print(f"Workflow State: {status.state}")
print(f"Progress: {status.completed_tasks}/{status.total_tasks}")
```

---

## Agent Integration

### Existing Agents (No Changes Required)

Your existing agents work unchanged with the orchestration system:

```python
# Existing agent code (unchanged)
class PSXTechnicalAgent:
    def __init__(self, db_path="data/psx_data.db"):
        self.db_path = db_path
    
    def analyze_symbol(self, symbol: str, period: str = "1mo"):
        # Existing implementation
        return analysis_result
```

The orchestration system calls these agents via the **AgentAdapter**:

```python
# Orchestration calls agent automatically
result = agent.run_workflow("daily_analysis")
# Internally calls PSXTechnicalAgent.analyze_symbol() via adapter
```

### Optional: Enable Event Emission

To enhance integration, agents can optionally emit events:

```python
# Enhanced agent (optional upgrade)
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

## Event-Driven Workflows

### Setting Up Event Triggers

```python
from psx_orchestration_agent.event_bus import EventType

# Define event handler
def investigate_high_severity_anomalies(event):
    """Auto-investigate anomalies with severity > 0.8"""
    if event.data["severity"] > 0.8:
        print(f"High severity anomaly detected: {event.data['symbol']}")
        
        # Trigger investigation workflow
        result = agent.run_workflow(
            "high_severity_investigation",
            parameters={
                "anomaly": event.data
            }
        )
        
        print(f"Investigation complete: {result.status}")

# Subscribe to anomaly events
agent.event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    investigate_high_severity_anomalies
)

# Now anomalies automatically trigger investigations
# Run daily analysis
result = agent.run_daily_analysis()
# If high-severity anomalies found → investigation workflow auto-triggers
```

### Risk Violation Alerts

```python
def alert_on_risk_violation(event):
    """Send alert when risk limits violated"""
    violations = event.data["violations"]
    
    print(f"⚠️ RISK VIOLATION: {len(violations)} rules violated")
    for v in violations:
        print(f"  - {v['rule']}: {v['message']}")
    
    # Optionally send email/Slack notification
    # send_notification(violations)

agent.event_bus.subscribe(
    EventType.RISK_VIOLATION,
    alert_on_risk_violation
)
```

### Portfolio Update Monitoring

```python
def monitor_portfolio_updates(event):
    """Monitor portfolio changes"""
    if event.type == EventType.POSITION_OPENED:
        print(f"✅ Position opened: {event.data['symbol']}")
    elif event.type == EventType.POSITION_CLOSED:
        pnl = event.data['realized_pnl']
        print(f"📊 Position closed: {event.data['symbol']} (P&L: {pnl})")

agent.event_bus.subscribe(EventType.POSITION_OPENED, monitor_portfolio_updates)
agent.event_bus.subscribe(EventType.POSITION_CLOSED, monitor_portfolio_updates)
```

---

## Scheduled Workflows

### Using Python schedule

```python
import schedule
import time

# Run daily analysis every weekday at 6 PM
schedule.every().monday.at("18:00").do(agent.run_daily_analysis)
schedule.every().tuesday.at("18:00").do(agent.run_daily_analysis)
schedule.every().wednesday.at("18:00").do(agent.run_daily_analysis)
schedule.every().thursday.at("18:00").do(agent.run_daily_analysis)
schedule.every().friday.at("18:00").do(agent.run_daily_analysis)

# Run portfolio risk check every hour during market hours
schedule.every().hour.at(":00").do(
    agent.run_workflow, "portfolio_risk_check"
)

# Run scheduler loop
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

### Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add scheduled workflows
# Run daily analysis at 6 PM on weekdays
0 18 * * 1-5 cd /path/to/Investment && python run_daily_analysis.py

# Run risk check every hour
0 * * * * cd /path/to/Investment && python run_risk_check.py
```

### Scheduled Script Example

```python
# run_daily_analysis.py
from psx_orchestration_agent import PSXOrchestrationAgent
import logging

logging.basicConfig(level=logging.INFO)

try:
    agent = PSXOrchestrationAgent()
    result = agent.run_daily_analysis()
    
    logging.info(f"Daily analysis complete: {result.status}")
    logging.info(f"Execution time: {result.execution_time}s")
    
except Exception as e:
    logging.error(f"Daily analysis failed: {e}")
    # Optionally send alert
```

---

## CLI Integration

### Command-Line Interface

```python
# run_orchestration_cli.py
import argparse
from psx_orchestration_agent import PSXOrchestrationAgent

def main():
    parser = argparse.ArgumentParser(description="PSX Orchestration CLI")
    parser.add_argument("workflow", help="Workflow to run")
    parser.add_argument("--min-volume", type=int, default=500000)
    parser.add_argument("--min-price", type=float, default=20.0)
    parser.add_argument("--cache", action="store_true", default=True)
    
    args = parser.parse_args()
    
    agent = PSXOrchestrationAgent()
    
    if args.workflow == "daily_analysis":
        result = agent.run_daily_analysis(
            min_volume=args.min_volume,
            min_price=args.min_price,
            cache_enabled=args.cache
        )
    else:
        result = agent.run_workflow(args.workflow)
    
    print(f"Status: {result.status}")
    print(f"Execution time: {result.execution_time}s")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Run daily analysis
python run_orchestration_cli.py daily_analysis --min-volume 500000

# Run risk check
python run_orchestration_cli.py portfolio_risk_check

# List workflows
python run_orchestration_cli.py --list
```

---

## Testing

### Unit Tests

```python
# tests/test_orchestration.py
import unittest
from psx_orchestration_agent import PSXOrchestrationAgent

class TestOrchestration(unittest.TestCase):
    def setUp(self):
        self.agent = PSXOrchestrationAgent(db_path=":memory:")
    
    def test_daily_analysis_workflow(self):
        """Test daily analysis workflow executes"""
        result = self.agent.run_daily_analysis()
        
        self.assertEqual(result.status, "completed")
        self.assertGreater(len(result.data['symbols']), 0)
        self.assertLess(result.execution_time, 120)  # < 2 minutes
    
    def test_workflow_caching(self):
        """Test caching reduces execution time"""
        # First run
        result1 = self.agent.run_daily_analysis()
        time1 = result1.execution_time
        
        # Second run (should use cache)
        result2 = self.agent.run_daily_analysis()
        time2 = result2.execution_time
        
        self.assertLess(time2, time1 * 0.5)  # At least 50% faster
    
    def test_event_emission(self):
        """Test event emission works"""
        events_received = []
        
        def handler(event):
            events_received.append(event)
        
        self.agent.event_bus.subscribe(
            EventType.ANOMALY_DETECTED,
            handler
        )
        
        result = self.agent.run_daily_analysis()
        
        self.assertGreater(len(events_received), 0)

if __name__ == "__main__":
    unittest.main()
```

### Integration Tests

```python
# tests/test_integration.py
import unittest
from psx_orchestration_agent import PSXOrchestrationAgent

class TestIntegration(unittest.TestCase):
    def test_end_to_end_analysis(self):
        """Test complete end-to-end analysis"""
        agent = PSXOrchestrationAgent()
        
        # Run workflow
        result = agent.run_daily_analysis(min_volume=500000)
        
        # Verify results structure
        self.assertIn('symbols', result.data)
        self.assertIn('anomalies', result.data)
        self.assertIn('technical_analysis', result.data)
        
        # Verify data quality
        for symbol in result.data['symbols']:
            self.assertRegex(symbol, r'^[A-Z]+$')  # Valid symbol
    
    def test_workflow_resumability(self):
        """Test workflows can be resumed after failure"""
        agent = PSXOrchestrationAgent()
        
        # Simulate workflow failure
        # ... force failure at task 3 of 5 ...
        
        # Resume from saved state
        result = agent.run_workflow(
            "daily_analysis",
            resume_from="workflow_id_123"
        )
        
        self.assertEqual(result.status, "completed")
```

---

## Configuration

### YAML Configuration (Optional)

```yaml
# config/orchestration.yaml
orchestration:
  db_path: "data/psx_data.db"
  max_workers: 4
  enable_caching: true
  cache_ttl_seconds: 1800

workflows:
  daily_analysis:
    enabled: true
    schedule: "0 18 * * 1-5"  # 6 PM weekdays
    parameters:
      min_volume: 500000
      min_price: 20.0
  
  portfolio_risk_check:
    enabled: true
    schedule: "0 * * * *"  # Every hour
    parameters:
      portfolio_id: "default"

event_triggers:
  high_severity_anomaly:
    workflow: "high_severity_investigation"
    condition: "severity > 0.8"
  
  risk_violation:
    workflow: "portfolio_risk_check"

logging:
  level: "INFO"
  file: "logs/orchestration.log"
```

**Load configuration:**
```python
agent = PSXOrchestrationAgent(config_path="config/orchestration.yaml")
```

---

## Summary

Integration steps:

1. ✅ **Install** dependencies (networkx, schedule)
2. ✅ **Initialize** PSXOrchestrationAgent
3. ✅ **Run** workflows (no agent changes needed)
4. ✅ **Set up** event-driven triggers (optional)
5. ✅ **Schedule** workflows (optional)
6. ✅ **Test** integration
7. ✅ **Deploy** to production

**Key Points:**
- Existing agents work unchanged
- Event emission is optional
- Gradual migration path
- Complete backward compatibility

---

**Next**: See [07_PORTFOLIO_RISK_MANAGEMENT.md](07_PORTFOLIO_RISK_MANAGEMENT.md) for portfolio and risk integration.
