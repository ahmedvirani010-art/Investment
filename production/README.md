## Production Deployment System

Automated daily technical analysis with scheduling, alerts, and results tracking.

## Quick Start

### 1. Configure Watchlist

```python
from production.config import ProductionConfig

# Load default config
config = ProductionConfig()

# Customize watchlist
config.watchlist.custom = ['PPL', 'OGDC', 'PSO', 'ENGRO']

# Configure alerts
config.alerts.min_confidence = 0.70  # Only alert on 70%+ confidence
config.alerts.alert_on_bullish = True
config.alerts.alert_on_bearish = True

# Save config
config.save_to_file('production/production_config.json')
```

### 2. Run Analysis Manually

```bash
# Run once
python run_daily_analysis.py

# Test mode (no database writes)
python run_daily_analysis.py --test

# Custom symbols
python run_daily_analysis.py --symbols PPL OGDC PSO
```

### 3. Setup Automated Scheduling

**Option A: APScheduler (Recommended)**
```bash
# Install APScheduler
pip install apscheduler

# Start scheduler (runs in foreground)
python -m production.scheduler

# Run once for testing
python -m production.scheduler --once
```

**Option B: Linux Cron**
```bash
# Generate cron entry
python -m production.scheduler --cron

# Add to crontab
crontab -e
# Paste the generated cron entry
```

**Option C: Linux Systemd**
```bash
# Generate systemd service
python -m production.scheduler --systemd

# Follow the instructions to install
sudo systemctl enable psx-analysis
sudo systemctl start psx-analysis
```

**Option D: Windows Task Scheduler**
```bash
# Get instructions
python -m production.scheduler --windows
# Follow the instructions
```

## Components

### Configuration (`config.py`)

Centralized configuration for all production settings.

```python
ProductionConfig:
  - watchlist: Stock symbols to analyze
  - alerts: Alert thresholds and notification settings
  - schedule: Run time and frequency
  - storage: Data storage paths and retention
```

**Configuration File**: `production/production_config.json`

### Daily Analyzer (`daily_analyzer.py`)

Core analysis engine that:
1. Collects price data for watchlist
2. Runs technical analysis
3. Stores results
4. Generates alerts
5. Creates daily reports

### Scheduler (`scheduler.py`)

Automated job scheduler:
- Runs analysis at configured times
- Automatic retry on failure
- Logging and error tracking
- Multiple deployment options

## Workflow

```
Scheduled Time
    ↓
Load Configuration
    ↓
Collect Price Data (200 days)
    ↓
Run Technical Analysis
    ↓
Store Results (JSON + Database)
    ↓
Generate Alerts
    ↓
Create Daily Report
    ↓
Done
```

## Output Files

```
production_data/
├── results/
│   └── report_20260216.txt       # Daily summary report
├── snapshots/
│   └── snapshot_20260216.json    # Full analysis snapshots
├── alerts/
│   └── alerts_20260216.json      # Triggered alerts
├── logs/
│   └── scheduler_202602.log      # Application logs
└── signals.db                     # SQLite database
```

### Daily Report Format

```
================================================================================
DAILY TECHNICAL ANALYSIS REPORT
Date: 2026-02-16
Generated: 2026-02-16 18:00:00
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total Analyzed:  10
Bullish:         4 (40.0%)
Bearish:         3 (30.0%)
Neutral:         3 (30.0%)
Alerts:          5

TOP SIGNALS
--------------------------------------------------------------------------------

Bullish (4):
   1. PPL     :   88% confidence, score: +0.75
   2. OGDC    :   82% confidence, score: +0.68
   ...

Bearish (3):
   1. PSO     :   76% confidence, score: -0.65
   ...

DETAILED RESULTS
================================================================================

PPL
  Signal:     Bullish
  Confidence: 88%
  Score:      +0.750
  Regime:     NORMAL
  Strategies:
    - TrendFollowing          : Bullish      (85%)
    - MeanReversion           : Bullish      (90%)
    - Momentum                : Bullish      (80%)
    ...
```

## Alert System

### Alert Criteria

Alerts are triggered when:
- Confidence >= `min_confidence` (default: 70%)
- Score magnitude >= `min_score` (default: 0.5)
- Signal type matches enabled alerts

### Alert Channels

1. **Console**: Print to terminal (immediate)
2. **File**: Save to JSON file (always on)
3. **Email**: Send via SMTP (optional, requires config)

### Configuring Email Alerts

```python
config = ProductionConfig.load_from_file()

# Enable email
config.alerts.enable_email = True
config.alerts.email_from = 'alerts@example.com'
config.alerts.email_to = ['your@email.com']

# SMTP settings
config.alerts.smtp_server = 'smtp.gmail.com'
config.alerts.smtp_port = 587
config.alerts.smtp_username = 'your@gmail.com'
config.alerts.smtp_password = 'your_app_password'

config.save_to_file()
```

## Database Schema

SQLite database stores historical signals:

```sql
CREATE TABLE daily_signals (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    overall_bias TEXT,
    confidence REAL,
    ensemble_score REAL,
    regime TEXT,
    created_at TEXT,
    UNIQUE(date, symbol)
);
```

### Querying Historical Data

```python
import sqlite3

conn = sqlite3.connect('production_data/signals.db')
cursor = conn.cursor()

# Get latest signals
cursor.execute('''
    SELECT symbol, overall_bias, confidence, ensemble_score
    FROM daily_signals
    WHERE date = ?
    ORDER BY confidence DESC
''', ('2026-02-16',))

for row in cursor.fetchall():
    print(row)
```

## Deployment Options

### Development

Run manually for testing:
```bash
python run_daily_analysis.py --test
```

### Production - Local Server

Use APScheduler:
```bash
pip install apscheduler
python -m production.scheduler
```

Run in background:
```bash
nohup python -m production.scheduler > scheduler.log 2>&1 &
```

### Production - Linux Server (Systemd)

1. Create service file:
```bash
python -m production.scheduler --systemd > /tmp/psx-analysis.service
sudo mv /tmp/psx-analysis.service /etc/systemd/system/
```

2. Update paths in service file:
```bash
sudo nano /etc/systemd/system/psx-analysis.service
# Update User and WorkingDirectory
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable psx-analysis
sudo systemctl start psx-analysis
sudo systemctl status psx-analysis
```

4. View logs:
```bash
sudo journalctl -u psx-analysis -f
```

### Production - Linux Server (Cron)

1. Generate cron entry:
```bash
python -m production.scheduler --cron
```

2. Add to crontab:
```bash
crontab -e
# Paste the cron entry
```

3. Verify:
```bash
crontab -l
```

### Production - Windows

1. Get instructions:
```bash
python -m production.scheduler --windows
```

2. Follow the Task Scheduler setup

3. Test the task manually before enabling

## Monitoring

### Check Latest Run

```bash
# View latest report
cat production_data/results/report_$(date +%Y%m%d).txt

# View latest alerts
cat production_data/alerts/alerts_$(date +%Y%m%d).json

# View logs
tail -f production_data/logs/scheduler_$(date +%Y%m).log
```

### Performance Metrics

Track in database:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('production_data/signals.db')

# Daily signal distribution
df = pd.read_sql('''
    SELECT date, overall_bias, COUNT(*) as count
    FROM daily_signals
    GROUP BY date, overall_bias
    ORDER BY date DESC
''', conn)

print(df)
```

## Troubleshooting

### Issue: No Data Collected

**Problem**: Symbols fail to collect data

**Solutions**:
1. Check internet connection
2. Verify Yahoo Finance is accessible
3. Try manual collection: `python collect_data.py PPL --days 200`
4. Check symbol format (PSX uses .KA suffix)

### Issue: Analysis Fails

**Problem**: Analysis throws errors

**Solutions**:
1. Check data has sufficient history (120+ days)
2. Review logs: `production_data/logs/`
3. Run in test mode: `python run_daily_analysis.py --test`
4. Check technical analysis configuration

### Issue: Scheduler Not Running

**Problem**: Scheduled jobs don't execute

**Solutions**:
1. Verify scheduler is running: `ps aux | grep scheduler`
2. Check system logs
3. Test manual execution first
4. Verify time zone settings

### Issue: Alerts Not Sent

**Problem**: No alerts generated

**Solutions**:
1. Check alert thresholds in config
2. Verify signals meet criteria (confidence >= 70%)
3. Check alert channel settings
4. Review alerts file: `production_data/alerts/`

## Maintenance

### Daily
- Monitor logs for errors
- Check alerts for important signals
- Review daily reports

### Weekly
- Review signal distribution
- Check disk space
- Verify data collection success rate

### Monthly
- Clean old logs (retention: 30 days)
- Clean old results (retention: 90 days)
- Review and update watchlist
- Check system performance

### Cleanup

```bash
# Remove old logs (older than 30 days)
find production_data/logs -name "*.log" -mtime +30 -delete

# Remove old results (older than 90 days)
find production_data/results -name "report_*.txt" -mtime +90 -delete
find production_data/snapshots -name "snapshot_*.json" -mtime +90 -delete
```

## Best Practices

1. **Start Small**: Test with 2-3 symbols before running full watchlist
2. **Monitor First Week**: Watch logs closely during initial deployment
3. **Backup Database**: Regular backups of `signals.db`
4. **Version Control**: Keep config files in git
5. **Document Changes**: Log watchlist changes and config updates
6. **Test Updates**: Always test in `--test` mode first
7. **Set Alerts Wisely**: Start with high confidence threshold (70%+)
8. **Review Regularly**: Check daily reports for quality

## Advanced Features

### Custom Strategies

Modify technical configuration:
```python
from config.technical_config import TechnicalAgentConfig

config = TechnicalAgentConfig()

# Adjust strategy weights
config.strategies.strategy_weights['TrendFollowing'] = 0.30
config.strategies.strategy_weights['MeanReversion'] = 0.25

# Adjust thresholds
config.strategies.rsi_oversold = 25
config.strategies.rsi_overbought = 75
```

### Multiple Watchlists

Create separate configs for different groups:
```bash
# Blue chips
python run_daily_analysis.py --config production/bluechips_config.json

# Speculative
python run_daily_analysis.py --config production/speculative_config.json
```

### Integration with Other Systems

Export to CSV for Excel/Google Sheets:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('production_data/signals.db')
df = pd.read_sql('SELECT * FROM daily_signals', conn)
df.to_csv('signals_export.csv', index=False)
```

## Support

For issues or questions:
1. Check logs: `production_data/logs/`
2. Review configuration: `production/production_config.json`
3. Test manually: `python run_daily_analysis.py --test`
4. Check data collection: `python collect_data.py SYMBOL --days 200`

## Next Steps

After deployment:
1. ✅ **Week 1**: Monitor daily, verify alerts working
2. ✅ **Week 2-4**: Track signal quality, adjust thresholds
3. ✅ **Month 2**: Build historical performance tracking
4. ✅ **Month 3+**: Consider web dashboard for visualization
