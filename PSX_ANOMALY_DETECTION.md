# PSX Anomaly Detection Agent

A Python-based anomaly detection agent for the Pakistan Stock Exchange (PSX) that monitors unusual trading patterns and price movements using statistical analysis.

## Features

The agent detects five types of anomalies:

### 1. Volume Spikes
- Detects unusual trading activity
- Identifies when volume deviates significantly from historical average
- Useful for detecting sudden interest or institutional activity

### 2. Price Movements
- Monitors abnormal returns
- Identifies unusual price changes that deviate from typical behavior
- Helps spot potential breakouts or breakdowns

### 3. Opening Gaps
- Detects gap up/down patterns
- Identifies when opening price differs significantly from previous close
- Useful for overnight news or market sentiment changes

### 4. Volatility Spikes
- Monitors unusual price ranges
- Calculated as (High - Low) / Close percentage
- Identifies periods of increased uncertainty or excitement

### 5. Liquidity Changes
- Tracks turnover anomalies
- Monitors Volume × Price patterns
- Detects changes in market liquidity

## How It Works

### Statistical Method
- **Z-Score Analysis**: Uses standardized scores to detect outliers
- **Default Threshold**: 2.5σ (standard deviations)
- **Lookback Period**: 60 days for baseline calculation
- **Severity Levels**:
  - HIGH: |z-score| ≥ 4.0
  - MEDIUM: |z-score| ≥ 3.0
  - LOW: |z-score| ≥ 2.5

### Data Source
- Uses `yfinance` library to fetch PSX data
- PSX symbols require `.KA` suffix (e.g., `LUCK.KA`)
- Fetches historical OHLCV data for analysis

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have Python 3.8 or higher installed

## Usage

### Basic Usage

Run the agent with default top PSX stocks:

```bash
python psx_anomaly_agent.py
```

### Custom Usage in Python

```python
from psx_anomaly_agent import PSXAnomalyAgent

# Initialize agent with custom parameters
agent = PSXAnomalyAgent(
    lookback_days=60,    # Days for baseline calculation
    z_threshold=2.5      # Z-score threshold for detection
)

# Analyze specific symbols
symbols = ["LUCK", "PSO", "HBL", "ENGRO", "MCB"]
report = agent.generate_report(symbols)

# Print formatted report
agent.print_report(report)
```

### Advanced Usage

```python
# Analyze a single symbol
anomalies = agent.analyze_symbol("LUCK")

# Access individual anomaly details
for anomaly in anomalies:
    print(f"Type: {anomaly.anomaly_type.value}")
    print(f"Severity: {anomaly.severity.value}")
    print(f"Description: {anomaly.description}")
    print(f"Z-Score: {anomaly.z_score}")
```

### Custom Sensitivity

Adjust detection sensitivity:

```python
# More sensitive (lower threshold)
sensitive_agent = PSXAnomalyAgent(z_threshold=2.0)

# Less sensitive (higher threshold)
conservative_agent = PSXAnomalyAgent(z_threshold=3.0)

# Longer baseline period
long_baseline_agent = PSXAnomalyAgent(lookback_days=90)
```

## Output Format

The agent generates a comprehensive report with:

1. **Summary**: Total anomalies and affected symbols
2. **Per-Symbol Details**: Anomalies grouped by stock
3. **Severity Indicators**:
   - 🔴 HIGH - Requires immediate attention
   - 🟡 MEDIUM - Significant deviation
   - 🟢 LOW - Notable but mild deviation
4. **Detailed Metrics**: Z-scores, percentages, and comparisons

### Example Output

```
================================================================================
PSX ANOMALY DETECTION REPORT
================================================================================

Total Anomalies Detected: 3
Symbols with Anomalies: 2

LUCK (2 anomalies)
--------------------------------------------------------------------------------

  🔴 HIGH - Volume Spike
     Date: 2026-02-13
     Volume +245.3% from average (12,500,000 vs 3,600,000)
     Z-Score: 4.23

  🟡 MEDIUM - Volatility Spike
     Date: 2026-02-13
     Volatility 8.50% (avg: 2.30%)
     Z-Score: 3.15

PSO (1 anomalies)
--------------------------------------------------------------------------------

  🟢 LOW - Price Movement
     Date: 2026-02-13
     Return +4.50% (avg: +0.15%)
     Z-Score: 2.67
```

## Top PSX Stocks Monitored

The default script monitors these major PSX stocks:

- **LUCK** - Lucky Cement
- **PSO** - Pakistan State Oil
- **HBL** - Habib Bank Limited
- **ENGRO** - Engro Corporation
- **MCB** - MCB Bank
- **OGDC** - Oil & Gas Development Company
- **PPL** - Pakistan Petroleum Limited
- **UBL** - United Bank Limited
- **HUBC** - Hub Power Company
- **FFC** - Fauji Fertilizer Company

## Use Cases

1. **Day Trading**: Identify unusual opportunities in real-time
2. **Risk Management**: Detect abnormal movements in portfolio holdings
3. **Market Research**: Study patterns and anomalies over time
4. **Alert System**: Build automated alerts for specific conditions
5. **Backtesting**: Analyze historical anomalies and their outcomes

## Customization

### Add More Detection Methods

Extend the `PSXAnomalyAgent` class:

```python
def detect_custom_pattern(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
    """Add your custom detection logic"""
    anomalies = []
    # Your detection code here
    return anomalies
```

### Filter by Severity

```python
# Get only HIGH severity anomalies
high_severity = [
    a for a in anomalies
    if a.severity == Severity.HIGH
]
```

### Export to DataFrame

```python
import pandas as pd

# Convert anomalies to DataFrame
data = [{
    'symbol': a.symbol,
    'date': a.date,
    'type': a.anomaly_type.value,
    'severity': a.severity.value,
    'z_score': a.z_score,
    'description': a.description
} for a in anomalies]

df = pd.DataFrame(data)
df.to_csv('anomalies_report.csv', index=False)
```

## Limitations

1. **Data Availability**: Depends on yfinance data quality for PSX
2. **Real-time Delays**: Data may be delayed based on yfinance updates
3. **Market Hours**: Only detects anomalies based on daily close data
4. **Statistical Assumptions**: Assumes normal distribution of metrics

## Future Enhancements

- [ ] Real-time monitoring with continuous updates
- [ ] Integration with notification systems (email, SMS, Slack)
- [ ] Machine learning-based anomaly detection
- [ ] Intraday anomaly detection
- [ ] Correlation analysis between stocks
- [ ] Historical anomaly database and tracking
- [ ] Web dashboard for visualization
- [ ] Automated trading signal generation

## Contributing

Feel free to extend the agent with additional detection methods or improvements.

## License

This agent is part of the Investment project.
