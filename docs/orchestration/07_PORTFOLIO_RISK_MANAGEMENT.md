# Portfolio & Risk Management

## Table of Contents

1. [Overview](#overview)
2. [PSXPortfolioAgent Integration](#psxportfolioagent-integration)
3. [PSXRiskAgent Integration](#psxriskagent-integration)
4. [Validated Trade Workflow](#validated-trade-workflow)
5. [Risk Monitoring](#risk-monitoring)
6. [Portfolio Analytics](#portfolio-analytics)
7. [Risk Rules Configuration](#risk-rules-configuration)

---

## Overview

The orchestration system integrates **PSXPortfolioAgent** and **PSXRiskAgent** to provide:

✅ **Pre-Trade Validation** - Validate trades before execution
✅ **Portfolio Tracking** - Real-time position and P&L tracking
✅ **Risk Monitoring** - Continuous risk metric monitoring
✅ **Automated Alerts** - Event-driven risk violation alerts
✅ **Saga Rollback** - Automatic rollback on failures

---

## PSXPortfolioAgent Integration

### Purpose
Manages portfolio positions, tracks P&L, and provides portfolio analytics.

### Key Operations

#### Adding Positions

```python
# Manual position add
from psx_portfolio_agent import PSXPortfolioAgent

portfolio = PSXPortfolioAgent()
position_id = portfolio.add_position(
    symbol="OGDC",
    quantity=1000,
    entry_price=125.50
)
```

**Via Orchestration:**
```python
# Automated via workflow
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
```

#### Tracking P&L

```python
# Get portfolio P&L
pnl = portfolio.get_pnl(portfolio_id="default")

print(f"Total Value: PKR {pnl['summary']['total_value']:,.0f}")
print(f"Total P&L: PKR {pnl['summary']['total_pnl']:,.0f}")
print(f"Return: {pnl['summary']['total_pnl_pct']:.2f}%")

# Open positions
for pos in pnl['open_positions']:
    print(f"{pos['symbol']}: {pos['unrealized_pnl_pct']:.2f}%")
```

#### Closing Positions

```python
# Close position
pnl_details = portfolio.close_position(
    position_id="pos_12345",
    exit_price=135.75
)

print(f"Realized P&L: PKR {pnl_details['realized_pnl']:,.0f}")
```

### Event Emission

The portfolio agent emits events for tracking:

```python
# Subscribe to portfolio events
def log_portfolio_changes(event):
    if event.type == EventType.POSITION_OPENED:
        print(f"✅ Opened: {event.data['symbol']} @ {event.data['entry_price']}")
    elif event.type == EventType.POSITION_CLOSED:
        print(f"📊 Closed: {event.data['symbol']} (P&L: {event.data['realized_pnl']})")
    elif event.type == EventType.PORTFOLIO_UPDATED:
        print(f"📈 Portfolio updated: {event.data['total_value']}")

orchestrator.event_bus.subscribe(EventType.POSITION_OPENED, log_portfolio_changes)
orchestrator.event_bus.subscribe(EventType.POSITION_CLOSED, log_portfolio_changes)
orchestrator.event_bus.subscribe(EventType.PORTFOLIO_UPDATED, log_portfolio_changes)
```

---

## PSXRiskAgent Integration

### Purpose
Validates trades, monitors portfolio risk, and enforces risk limits.

### Risk Validation

#### Pre-Trade Validation

```python
from psx_risk_agent import PSXRiskAgent

risk_agent = PSXRiskAgent()

# Validate trade
validation = risk_agent.validate_trade(
    symbol="OGDC",
    quantity=1000,
    entry_price=125.50
)

if validation['approved']:
    print("✅ Trade approved")
    # Execute trade
else:
    print(f"❌ Trade blocked: {validation['reason']}")
    for v in validation['violations']:
        print(f"  - {v['rule']}: {v['severity']}")
```

#### Risk Rules

```python
RISK_RULES = {
    "max_risk_per_trade": 0.02,      # Max 2% of portfolio per trade
    "max_position_size": 0.10,       # Max 10% in single position
    "max_sector_allocation": 0.50,   # Max 50% in single sector
    "min_reward_to_risk": 2.0,       # Min 2:1 reward:risk ratio
    "min_cash_reserve": 0.20,        # Min 20% cash reserve
}
```

#### Validation Examples

**Example 1: Position Size Violation**
```python
# Portfolio value: PKR 1,000,000
# Proposed trade: PKR 150,000 (15% of portfolio)

validation = risk_agent.validate_trade(
    symbol="OGDC",
    quantity=1200,
    entry_price=125.00
)

# Result:
{
    "approved": False,
    "violations": [{
        "rule": "max_position_size",
        "limit": 100000,  # 10% of portfolio
        "proposed": 150000,
        "severity": "critical"
    }],
    "reason": "Trade exceeds max position size (10%)"
}
```

**Example 2: Sector Concentration**
```python
# Current Energy sector allocation: 45%
# Proposed trade: OGDC (Energy) worth PKR 80,000

validation = risk_agent.validate_trade(
    symbol="OGDC",
    quantity=640,
    entry_price=125.00
)

# Result:
{
    "approved": False,
    "violations": [{
        "rule": "max_sector_allocation",
        "message": "Energy sector would be 53% (limit: 50%)",
        "severity": "medium"
    }]
}
```

### Portfolio Risk Monitoring

```python
# Check portfolio risk
risk_metrics = risk_agent.check_portfolio_risk(portfolio_id="default")

print(f"Risk Level: {risk_metrics['risk_level']}")  # low, medium, high
print(f"Portfolio Std Dev: {risk_metrics['metrics']['volatility']['portfolio_std_dev']:.2%}")
print(f"Sharpe Ratio: {risk_metrics['metrics']['volatility']['sharpe_ratio']:.2f}")
print(f"VaR (95%): PKR {risk_metrics['metrics']['var']['var_95']:,.0f}")

# Check violations
if risk_metrics['violations']:
    print("⚠️ Risk Violations:")
    for v in risk_metrics['violations']:
        print(f"  - {v['rule']}: {v['message']}")
```

### Event-Driven Risk Alerts

```python
# Auto-alert on risk violations
def alert_risk_violation(event):
    violations = event.data['violations']
    
    print(f"🚨 RISK ALERT: {len(violations)} violations")
    for v in violations:
        print(f"  [{v['severity']}] {v['rule']}: {v['message']}")
    
    # Optionally trigger risk check workflow
    orchestrator.run_workflow("portfolio_risk_check")

orchestrator.event_bus.subscribe(
    EventType.RISK_VIOLATION,
    alert_risk_violation
)
```

---

## Validated Trade Workflow

### Complete Trade Execution with Validation

```python
# Workflow definition (from WorkflowTemplates)
validated_trade_workflow = WorkflowDefinition(
    name="validated_trade_execution",
    description="Execute trade with pre-validation and saga rollback",
    saga_enabled=True,
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
            parameters={"amount": "${trade.total_value}"},
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
            name="check_post_trade_risk",
            agent="risk",
            method="check_portfolio_risk",
            depends_on=["add_position"]
        )
    ]
)
```

### Usage Example

```python
# Execute validated trade
result = orchestrator.run_workflow(
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
    print(f"✅ Trade executed: Position {position_id}")
    print(f"Post-trade risk level: {result.data['check_post_trade_risk']['risk_level']}")
else:
    print(f"❌ Trade failed: {result.error}")
    # Saga automatically rolled back all changes
```

### Saga Rollback

If any step fails, compensating actions execute in reverse:

```
Success Path:
  1. validate_risk ✅
  2. reserve_cash ✅
  3. add_position ✅
  4. check_post_trade_risk ✅

Failure at Step 3:
  → Compensate Step 2: release_cash()
  → Compensate Step 1: log_failure()
  → Portfolio unchanged (safe rollback)
```

---

## Risk Monitoring

### Continuous Portfolio Monitoring

```python
# Schedule hourly risk checks
import schedule

def run_risk_check():
    result = orchestrator.run_workflow("portfolio_risk_check")
    
    if result.data['violations']:
        print("⚠️ Risk violations detected")
        # Send alert
    else:
        print("✅ Portfolio risk within limits")

schedule.every().hour.do(run_risk_check)
```

### Event-Triggered Monitoring

```python
# Monitor portfolio updates
def monitor_on_portfolio_update(event):
    """Check risk whenever portfolio changes"""
    orchestrator.run_workflow("portfolio_risk_check")

orchestrator.event_bus.subscribe(
    EventType.PORTFOLIO_UPDATED,
    monitor_on_portfolio_update
)
```

---

## Portfolio Analytics

### Position Analytics

```python
# Get detailed position breakdown
pnl = portfolio.get_pnl()

print("Open Positions:")
for pos in pnl['open_positions']:
    print(f"{pos['symbol']:6} | Qty: {pos['quantity']:4} | "
          f"Entry: {pos['entry_price']:7.2f} | "
          f"Current: {pos['current_price']:7.2f} | "
          f"P&L: {pos['unrealized_pnl_pct']:+6.2f}%")
```

**Output:**
```
Open Positions:
OGDC   | Qty: 1000 | Entry:  125.50 | Current:  135.75 | P&L:  +8.17%
PPL    | Qty:  800 | Entry:  210.00 | Current:  218.40 | P&L:  +4.00%
HBL    | Qty:  500 | Entry:  145.80 | Current:  142.30 | P&L:  -2.40%
```

### Sector Allocation

```python
allocation = pnl['allocation']['by_sector']

print("Sector Allocation:")
for sector, pct in allocation.items():
    print(f"{sector:15} {pct:5.1f}%")
```

**Output:**
```
Sector Allocation:
Energy           45.0%
Banking          30.0%
Cement           25.0%
```

### Trade History

```python
history = portfolio.get_trade_history(days=30)

print(f"Trades (Last 30 days): {len(history)}")
print(f"Win Rate: {history['win_rate']:.1f}%")
print(f"Avg Win: PKR {history['avg_win']:,.0f}")
print(f"Avg Loss: PKR {history['avg_loss']:,.0f}")
```

---

## Risk Rules Configuration

### Customizing Risk Rules

```python
# Custom risk configuration
from psx_risk_agent import RiskConfiguration

custom_risk_config = RiskConfiguration(
    max_risk_per_trade=0.015,        # 1.5% (more conservative)
    max_position_size=0.08,          # 8% (more conservative)
    max_sector_allocation=0.40,      # 40% (more diversified)
    min_reward_to_risk=2.5,          # 2.5:1 (higher requirement)
    min_cash_reserve=0.25,           # 25% (higher reserve)
    max_portfolio_leverage=0.0,      # No leverage
    max_drawdown_limit=0.15          # 15% max drawdown
)

# Initialize risk agent with custom config
risk_agent = PSXRiskAgent(config=custom_risk_config)
```

### Risk Levels

```python
# Risk level determination
def determine_risk_level(metrics):
    """Determine portfolio risk level"""
    
    # High risk conditions
    if (metrics['concentration']['max_position_pct'] > 30 or
        metrics['volatility']['portfolio_std_dev'] > 0.25 or
        metrics['var']['var_95'] < -50000):
        return "high"
    
    # Low risk conditions
    elif (metrics['concentration']['max_position_pct'] < 15 and
          metrics['volatility']['portfolio_std_dev'] < 0.10 and
          metrics['cash_reserve_pct'] > 30):
        return "low"
    
    # Medium risk
    else:
        return "medium"
```

---

## Summary

Portfolio & Risk Management features:

✅ **Pre-Trade Validation**
- Automatic risk checking before trades
- Multiple risk rule enforcement
- Immediate rejection of unsafe trades

✅ **Portfolio Tracking**
- Real-time position tracking
- P&L calculation (realized + unrealized)
- Sector and symbol allocation

✅ **Risk Monitoring**
- Continuous risk metric calculation
- VaR, volatility, concentration metrics
- Event-driven risk alerts

✅ **Saga Rollback**
- Automatic compensation on failures
- Data consistency guarantees
- Safe trade execution

✅ **Event-Driven**
- Automatic workflows on portfolio changes
- Risk violation alerts
- Complete audit trail

---

**Next**: See [08_MIGRATION_GUIDE.md](08_MIGRATION_GUIDE.md) for migration from sequential to orchestrated system.
