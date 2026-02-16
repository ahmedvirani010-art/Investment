# PSX Proactive Risk Management System

A proactive risk management system for position/swing trading on the Pakistan Stock Exchange (PSX). This system predicts risks before they materialize and automatically monitors positions with daily EOD analysis.

## Features

### ✅ Proactive, Not Reactive
- **Predictive Signals**: Warns 1-7 days BEFORE risks materialize
- **Automated Monitoring**: Runs daily EOD analysis at 4:00 PM
- **Morning News Brief**: Scans overnight news for watchlist symbols
- **Risk Limit Enforcement**: Automatic breach detection
- **Position Management**: Automated action recommendations with approval workflow

### ✅ Core Components

1. **Risk Predictor** (`psx_risk_predictor.py`)
   - Trend Deterioration Detector (3-7 day lead time)
   - Volatility Regime Change Predictor (2-5 day lead time)
   - Multi-Timeframe Divergence Detection

2. **Risk Monitor** (`psx_risk_monitor.py`)
   - EOD position analysis
   - Risk score calculation (0-100)
   - Limit breach detection

3. **Alert Engine** (`psx_alert_engine.py`)
   - Multi-severity alerts (CRITICAL, HIGH, MEDIUM, LOW)
   - Deduplication with cooldown periods
   - EOD digest compilation

4. **Position Manager** (`psx_position_manager.py`)
   - Position tracking with P&L
   - Automated action evaluation (EXIT, REDUCE, TIGHTEN_STOP)
   - Approval workflow
   - Audit trail

5. **Risk Limits** (`psx_risk_limits.py`)
   - Position limits (stop-loss, daily loss, risk score)
   - Portfolio limits (concentration, daily loss, drawdown)
   - Dynamic adjustment based on market volatility

6. **Storage** (`psx_risk_storage.py`)
   - SQLite database for alerts, positions, events, audit log
   - Persistent risk tracking

## Quick Start

### 1. Install Dependencies

```bash
pip install apscheduler pyyaml
```

### 2. Configure Settings

Edit `risk_config.yaml` to customize:
- Monitoring schedule (EOD time, morning brief time)
- Position limits (stop-loss %, max position size, etc.)
- Portfolio limits (concentration, daily loss, drawdown)
- Watchlist symbols
- Alert settings

### 3. Add Positions

```python
from psx_risk_storage import RiskStorage
from psx_position_manager import PositionManager
from psx_alert_engine import AlertEngine
from psx_risk_limits import RiskLimitEnforcer

# Initialize
storage = RiskStorage()
alert_engine = AlertEngine(storage)
limit_enforcer = RiskLimitEnforcer()
position_manager = PositionManager(storage, alert_engine, limit_enforcer)

# Add a position
position_manager.add_position(
    symbol="HBL",
    entry_price=150.0,
    quantity=1000,
    stop_loss_pct=5.0  # 5% stop loss
)
```

### 4. Run the System

**Option A: Continuous Monitoring (Recommended)**
```bash
python psx_risk_orchestrator.py
```

This will:
- Run EOD analysis daily at 4:00 PM (configurable)
- Send morning news brief at 9:00 AM (configurable)
- Keep running in background

**Option B: Manual Analysis (Testing)**
```bash
python psx_risk_orchestrator.py --manual
```

This runs a single analysis cycle and exits.

## Usage Examples

### Check Active Positions

```python
from psx_risk_storage import RiskStorage

storage = RiskStorage()
positions = storage.get_active_positions()

for position in positions:
    print(f"{position.symbol}: P&L {position.unrealized_pnl_pct:.2f}%, "
          f"Risk Score {position.risk_score:.0f}/100")
```

### View Active Alerts

```python
from psx_risk_storage import RiskStorage

storage = RiskStorage()
alerts = storage.get_active_alerts()

for alert in alerts:
    print(f"[{alert.severity}] {alert.symbol} - {alert.description}")
    print(f"  Action: {alert.recommended_action}")
```

### Close a Position

```python
from psx_position_manager import PositionManager

position_manager = PositionManager(storage, alert_engine, limit_enforcer)
position_manager.close_position("HBL")
```

### View Audit Log

```python
from psx_risk_storage import RiskStorage

storage = RiskStorage()
audit_log = storage.get_audit_log(symbol="HBL", limit=10)

for entry in audit_log:
    print(f"{entry.timestamp}: {entry.action_type} - {entry.reason}")
    print(f"  Approved: {entry.approved}, Executed: {entry.executed}")
```

## Configuration

### Position Limits (`risk_config.yaml`)

```yaml
position_limits:
  max_position_size_pct: 10.0  # Max 10% of portfolio per position
  stop_loss_pct: 5.0            # Exit if down 5% from entry
  daily_loss_pct: 2.0           # Max 2% daily loss per position
  max_risk_score: 80.0          # Reduce if risk score > 80
  max_holding_days: 90          # Review positions older than 90 days
```

### Portfolio Limits

```yaml
portfolio_limits:
  max_single_position_pct: 15.0    # Max 15% in single stock
  max_sector_exposure_pct: 40.0    # Max 40% in single sector
  daily_portfolio_loss_pct: 3.0    # Max 3% portfolio loss per day
  drawdown_limit_pct: 15.0         # Max 15% drawdown from peak
```

### Execution Modes

```yaml
execution:
  auto_execute: false  # Manual approval (recommended for safety)
  dry_run: true        # Test mode (log actions but don't execute)
```

## Daily Workflow

### 4:00 PM - EOD Analysis

The system automatically:
1. Updates prices for all watchlist symbols
2. For each active position:
   - Runs predictive risk signals (trend, volatility, divergence)
   - Calculates risk score (0-100)
   - Checks limit breaches
   - Generates alerts
   - Recommends actions (EXIT, REDUCE, TIGHTEN_STOP)
3. Checks portfolio-level limits
4. Compiles and sends EOD digest email

### 9:00 AM - Morning News Brief

The system:
1. Scans overnight news for all watchlist symbols
2. Highlights news affecting current positions (risk management)
3. Flags news creating new opportunities (watchlist stocks)
4. Sends brief summary if material news found
5. Includes gap risk warnings for open positions

## Risk Scores

Position risk scores (0-100) consider:
- **Unrealized Loss** (0-40 points): Larger loss = higher risk
- **Distance from Stop Loss** (0-30 points): Closer to stop = higher risk
- **Predictive Signals** (0-20 points): More/severe signals = higher risk
- **Technical Bias** (0-10 points): BEARISH = +10, NEUTRAL = +5

**Interpretation:**
- 0-40: Low risk
- 40-70: Medium risk
- 70-85: High risk - consider reducing
- 85-100: Critical risk - reduce or exit

## Alert Severity Levels

- **CRITICAL**: Immediate action required (stop-loss breached, major anomaly)
- **HIGH**: Urgent attention (risk score >80, limit approaching)
- **MEDIUM**: Warning (technical reversal, sentiment deteriorating)
- **LOW**: Informational (position held >90 days)

## Files Generated

- `risk_data/risk.db` - SQLite database with alerts, positions, events, audit log
- `alerts/risk_alerts.log` - Alert log file
- `alerts/eod_digest.txt` - Latest EOD digest
- `price_data/prices.db` - Price data cache

## Troubleshooting

### No price data for symbol
- Ensure symbol is listed on PSX
- Check internet connection
- Try running `price_store.bulk_update([symbol], days=100)`

### EOD analysis not running
- Check system time and timezone in config
- Verify scheduler is running
- Check logs for errors

### Positions not updating
- Ensure `psx_price_store.py` is working
- Run manual price update: `position_manager.update_position_prices()`

## Safety Features

1. **Manual Approval by Default**: `auto_execute: false` requires manual approval
2. **Dry Run Mode**: `dry_run: true` logs actions without executing
3. **Audit Trail**: All decisions logged to database
4. **Deduplication**: Prevents alert spam with cooldown periods
5. **Limit Checks**: Multiple safety limits (position, portfolio, daily loss)

## Future Enhancements

- Streamlit dashboard for visualization
- Email integration for EOD digest
- Additional predictive indicators (sentiment momentum, correlation breakdown, event risk)
- Portfolio optimization
- Backtesting framework
- SMS alerts for CRITICAL events

## Support

For issues or questions:
1. Check logs in `logs/risk_management.log`
2. Review configuration in `risk_config.yaml`
3. Check database stats: `storage.get_stats()`

## License

This is a personal risk management tool for the PSX market. Use at your own risk.
