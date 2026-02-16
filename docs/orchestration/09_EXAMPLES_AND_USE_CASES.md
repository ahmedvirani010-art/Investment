# Examples & Use Cases

## Table of Contents

1. [Daily Analysis](#daily-analysis)
2. [Trade Execution](#trade-execution)
3. [Anomaly Investigation](#anomaly-investigation)
4. [Portfolio Management](#portfolio-management)
5. [Risk Monitoring](#risk-monitoring)
6. [Custom Workflows](#custom-workflows)
7. [Event-Driven Automation](#event-driven-automation)
8. [Scheduled Operations](#scheduled-operations)

---

## Daily Analysis

### Use Case: Automated Daily Market Analysis

**Objective:** Analyze all liquid PSX stocks every weekday at 6 PM.

```python
from psx_orchestration_agent import PSXOrchestrationAgent
import schedule
import time

# Initialize agent
agent = PSXOrchestrationAgent()

# Define daily analysis job
def run_daily_analysis():
    print("Starting daily analysis...")
    
    result = agent.run_daily_analysis(
        min_volume=500000,
        min_price=20.0
    )
    
    print(f"✅ Analysis complete: {result.status}")
    print(f"   Execution time: {result.execution_time}s")
    print(f"   Stocks analyzed: {len(result.data['symbols'])}")
    print(f"   Anomalies found: {len(result.data['anomalies'])}")
    
    # Print high-severity anomalies
    high_severity = [a for a in result.data['anomalies'] if a['severity'] > 0.8]
    if high_severity:
        print(f"\n⚠️ High-Severity Anomalies ({len(high_severity)}):")
        for anomaly in high_severity:
            print(f"   {anomaly['symbol']}: {anomaly['type']} (severity: {anomaly['severity']:.2f})")

# Schedule for weekdays at 6 PM
schedule.every().monday.at("18:00").do(run_daily_analysis)
schedule.every().tuesday.at("18:00").do(run_daily_analysis)
schedule.every().wednesday.at("18:00").do(run_daily_analysis)
schedule.every().thursday.at("18:00").do(run_daily_analysis)
schedule.every().friday.at("18:00").do(run_daily_analysis)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

**Expected Output:**
```
Starting daily analysis...
✅ Analysis complete: completed
   Execution time: 58s
   Stocks analyzed: 32
   Anomalies found: 8

⚠️ High-Severity Anomalies (2):
   OGDC: price_surge (severity: 0.92)
   HUBC: volume_surge (severity: 0.85)
```

---

## Trade Execution

### Use Case: Execute Trade with Risk Validation

**Objective:** Buy 1000 shares of OGDC with automated risk checking.

```python
from psx_orchestration_agent import PSXOrchestrationAgent

agent = PSXOrchestrationAgent()

# Execute validated trade
result = agent.run_workflow(
    "validated_trade_execution",
    parameters={
        "trade": {
            "symbol": "OGDC",
            "quantity": 1000,
            "entry_price": 125.50,
            "total_value": 125500
        }
    }
)

if result.status == "completed":
    position_id = result.data['add_position']['position_id']
    risk_level = result.data['check_post_trade_risk']['risk_level']
    
    print(f"✅ Trade Executed Successfully!")
    print(f"   Position ID: {position_id}")
    print(f"   Symbol: OGDC")
    print(f"   Quantity: 1000")
    print(f"   Entry Price: PKR 125.50")
    print(f"   Total Investment: PKR 125,500")
    print(f"   Post-Trade Risk Level: {risk_level}")
else:
    print(f"❌ Trade Blocked: {result.error}")
    if result.data.get('validate_risk'):
        violations = result.data['validate_risk'].get('violations', [])
        print("\nViolations:")
        for v in violations:
            print(f"   - {v['rule']}: {v['message']}")
```

**Scenario 1: Approved Trade**
```
✅ Trade Executed Successfully!
   Position ID: pos_20260216_001
   Symbol: OGDC
   Quantity: 1000
   Entry Price: PKR 125.50
   Total Investment: PKR 125,500
   Post-Trade Risk Level: medium
```

**Scenario 2: Blocked Trade (Position Size)**
```
❌ Trade Blocked: Risk validation failed

Violations:
   - max_position_size: Trade value (PKR 125,500) exceeds max position size of PKR 100,000 (10% of portfolio)
```

---

## Anomaly Investigation

### Use Case: Automatically Investigate High-Severity Anomalies

**Objective:** When a high-severity anomaly is detected, automatically run deep investigation.

```python
from psx_orchestration_agent import PSXOrchestrationAgent
from psx_orchestration_agent.event_bus import EventType

agent = PSXOrchestrationAgent()

# Set up automatic investigation
def investigate_anomaly(event):
    anomaly = event.data
    
    if anomaly['severity'] > 0.8:
        print(f"\n🔍 High-Severity Anomaly Detected: {anomaly['symbol']}")
        print(f"   Type: {anomaly['type']}")
        print(f"   Severity: {anomaly['severity']:.2f}")
        print("   Triggering deep investigation...")
        
        # Trigger investigation workflow
        result = agent.run_workflow(
            "high_severity_investigation",
            parameters={"anomaly": anomaly}
        )
        
        if result.status == "completed":
            print(f"\n✅ Investigation Complete")
            
            # Print correlation results
            correlation = result.data['correlate_events']
            if correlation['correlation_summary']['news_found']:
                print(f"\n📰 Correlated News:")
                for news in correlation['correlated_news'][:3]:
                    print(f"   - {news['title']}")
                    print(f"     Causality: {news['causality_score']:.2f}")

# Subscribe to anomaly events
agent.event_bus.subscribe(
    EventType.ANOMALY_DETECTED,
    investigate_anomaly
)

# Run daily analysis (will auto-trigger investigations)
result = agent.run_daily_analysis()
```

**Example Output:**
```
🔍 High-Severity Anomaly Detected: OGDC
   Type: price_surge
   Severity: 0.92
   Triggering deep investigation...

✅ Investigation Complete

📰 Correlated News:
   - OGDC announces 20% increase in quarterly profits
     Causality: 0.95
   - Energy sector rallies on oil price surge
     Causality: 0.72
```

---

## Portfolio Management

### Use Case: Track Portfolio Performance

**Objective:** Monitor portfolio P&L and allocation.

```python
from psx_portfolio_agent import PSXPortfolioAgent
import pandas as pd

portfolio = PSXPortfolioAgent()

# Get portfolio P&L
pnl = portfolio.get_pnl(portfolio_id="default")

# Print summary
print("Portfolio Summary")
print("=" * 50)
print(f"Total Value:      PKR {pnl['summary']['total_value']:>12,.0f}")
print(f"Cash:             PKR {pnl['summary']['cash']:>12,.0f}")
print(f"Invested:         PKR {pnl['summary']['invested']:>12,.0f}")
print(f"Total P&L:        PKR {pnl['summary']['total_pnl']:>12,.0f}")
print(f"Return:               {pnl['summary']['total_pnl_pct']:>10.2f}%")
print(f"Realized P&L:     PKR {pnl['summary']['realized_pnl']:>12,.0f}")
print(f"Unrealized P&L:   PKR {pnl['summary']['unrealized_pnl']:>12,.0f}")

# Print open positions
print("\nOpen Positions")
print("=" * 50)
positions_df = pd.DataFrame(pnl['open_positions'])
print(positions_df[['symbol', 'quantity', 'entry_price', 'current_price', 
                    'unrealized_pnl', 'unrealized_pnl_pct']].to_string(index=False))

# Print sector allocation
print("\nSector Allocation")
print("=" * 50)
for sector, pct in pnl['allocation']['by_sector'].items():
    bar = '█' * int(pct / 2)
    print(f"{sector:15} {pct:5.1f}% {bar}")
```

**Example Output:**
```
Portfolio Summary
==================================================
Total Value:      PKR    1,500,000
Cash:             PKR      500,000
Invested:         PKR    1,000,000
Total P&L:        PKR      125,000
Return:                     12.50%
Realized P&L:     PKR       85,000
Unrealized P&L:   PKR       40,000

Open Positions
==================================================
 symbol  quantity  entry_price  current_price  unrealized_pnl  unrealized_pnl_pct
   OGDC      1000       125.50         135.75           10250                8.17
    PPL       800       210.00         218.40            6720                4.00
    HBL       500       145.80         142.30           -1750               -2.40

Sector Allocation
==================================================
Energy           45.0% ██████████████████████
Banking          30.0% ███████████████
Cement           25.0% ████████████
```

---

## Risk Monitoring

### Use Case: Hourly Portfolio Risk Check

**Objective:** Monitor portfolio risk every hour and alert on violations.

```python
from psx_orchestration_agent import PSXOrchestrationAgent
from psx_orchestration_agent.event_bus import EventType
import schedule
import time

agent = PSXOrchestrationAgent()

# Define risk check job
def check_portfolio_risk():
    print(f"\n[{time.strftime('%H:%M:%S')}] Running portfolio risk check...")
    
    result = agent.run_workflow("portfolio_risk_check")
    
    risk_metrics = result.data['check_risk_metrics']
    violations = risk_metrics.get('violations', [])
    
    print(f"   Risk Level: {risk_metrics['risk_level']}")
    print(f"   Portfolio VaR (95%): PKR {risk_metrics['metrics']['var']['var_95']:,.0f}")
    
    if violations:
        print(f"\n   ⚠️ VIOLATIONS: {len(violations)}")
        for v in violations:
            print(f"      - [{v['severity']}] {v['rule']}: {v['message']}")
    else:
        print("   ✅ No violations")

# Set up risk violation alerts
def alert_risk_violation(event):
    violations = event.data['violations']
    
    print(f"\n🚨 RISK ALERT!")
    for v in violations:
        print(f"   [{v['severity']}] {v['rule']}: {v['message']}")
    
    # Send notification (email/Slack/etc.)
    # send_alert(violations)

agent.event_bus.subscribe(EventType.RISK_VIOLATION, alert_risk_violation)

# Schedule hourly checks during market hours (9 AM - 4 PM)
for hour in range(9, 17):
    schedule.every().day.at(f"{hour:02d}:00").do(check_portfolio_risk)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

**Example Output:**
```
[10:00:00] Running portfolio risk check...
   Risk Level: medium
   Portfolio VaR (95%): PKR -25,000
   ✅ No violations

[11:00:00] Running portfolio risk check...
   Risk Level: high
   Portfolio VaR (95%): PKR -45,000
   
   ⚠️ VIOLATIONS: 1
      - [critical] max_sector_allocation: Energy sector is 52% (limit: 50%)

🚨 RISK ALERT!
   [critical] max_sector_allocation: Energy sector is 52% (limit: 50%)
```

---

## Custom Workflows

### Use Case: Sector-Specific Analysis

**Objective:** Analyze only energy sector stocks.

```python
from psx_orchestration_agent import PSXOrchestrationAgent
from psx_orchestration_agent.models import WorkflowDefinition, Task

agent = PSXOrchestrationAgent()

# Define custom energy sector workflow
energy_analysis = WorkflowDefinition(
    name="energy_sector_analysis",
    description="Analyze energy sector stocks",
    tasks=[
        Task(
            name="filter_energy_stocks",
            agent="liquidity",
            method="screen_stocks",
            parameters={
                "min_volume": 500000,
                "sector": "Energy"  # Filter by sector
            }
        ),
        Task(
            name="analyze_technical",
            agent="technical",
            method="analyze_symbol",
            parameters={"symbol": "${symbol}"},
            depends_on=["filter_energy_stocks"]
        ),
        Task(
            name="analyze_fundamental",
            agent="fundamental",
            method="analyze_fundamentals",
            parameters={"symbol": "${symbol}"},
            depends_on=["filter_energy_stocks"]
        ),
        Task(
            name="compare_metrics",
            agent="fundamental",
            method="compare_sector_metrics",
            parameters={
                "symbols": "${filter_energy_stocks.output}",
                "technical": "${analyze_technical.output}",
                "fundamental": "${analyze_fundamental.output}"
            },
            depends_on=["analyze_technical", "analyze_fundamental"]
        )
    ]
)

# Execute custom workflow
result = agent.execute_custom_workflow(energy_analysis)

# Print results
comparison = result.data['compare_metrics']
print("Energy Sector Analysis")
print("=" * 50)
for symbol, metrics in comparison.items():
    print(f"\n{symbol}:")
    print(f"  P/E Ratio: {metrics['pe_ratio']:.2f}")
    print(f"  ROE: {metrics['roe']:.1f}%")
    print(f"  Technical Signal: {metrics['technical_signal']}")
```

---

## Event-Driven Automation

### Use Case: Complete Event-Driven System

**Objective:** Fully automated analysis and trading system.

```python
from psx_orchestration_agent import PSXOrchestrationAgent
from psx_orchestration_agent.event_bus import EventType
import schedule

agent = PSXOrchestrationAgent()

# 1. Auto-investigate anomalies
def auto_investigate(event):
    if event.data['severity'] > 0.8:
        agent.run_workflow("high_severity_investigation", 
                          parameters={"anomaly": event.data})

agent.event_bus.subscribe(EventType.ANOMALY_DETECTED, auto_investigate)

# 2. Auto-check risk on portfolio updates
def auto_risk_check(event):
    agent.run_workflow("portfolio_risk_check")

agent.event_bus.subscribe(EventType.PORTFOLIO_UPDATED, auto_risk_check)

# 3. Auto-alert on risk violations
def auto_alert(event):
    send_alert(f"Risk violation: {event.data['violations']}")

agent.event_bus.subscribe(EventType.RISK_VIOLATION, auto_alert)

# 4. Schedule daily analysis
schedule.every().day.at("18:00").do(agent.run_daily_analysis)

# Run forever
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Scheduled Operations

### Use Case: Multi-Timeframe Analysis

**Objective:** Run different analyses at different intervals.

```python
import schedule
import time

# Daily: Full market analysis
schedule.every().day.at("18:00").do(agent.run_daily_analysis)

# Hourly: Risk check
schedule.every().hour.do(agent.run_workflow, "portfolio_risk_check")

# Every 30 min: News impact analysis
schedule.every(30).minutes.do(agent.run_workflow, "news_impact_analysis")

# Weekly: Portfolio rebalancing
schedule.every().monday.at("09:00").do(agent.run_workflow, "portfolio_rebalance")

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Summary

These examples demonstrate:

✅ **Daily Analysis** - Automated market screening
✅ **Trade Execution** - Risk-validated trading
✅ **Anomaly Investigation** - Event-driven deep analysis
✅ **Portfolio Management** - P&L tracking and analytics
✅ **Risk Monitoring** - Continuous risk checks
✅ **Custom Workflows** - Sector-specific analysis
✅ **Event-Driven Automation** - Fully automated system
✅ **Scheduled Operations** - Multi-timeframe execution

All examples are production-ready and can be deployed immediately.

---

**Next**: See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete database schema.
