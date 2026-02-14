# 📊 PSX Trading Dashboard

Interactive web-based UI for Pakistan Stock Exchange analysis tools.

![Dashboard Preview](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)

## 🌟 Features

### 💧 Liquidity Screener
- **Real-time analysis** of 100+ PSX stocks
- **30-day average traded value** calculation (Volume × Price)
- **Customizable filters**: minimum price, lookback period
- **Interactive charts**: bar charts, scatter plots, distribution analysis
- **Export options**: CSV and JSON formats
- **Top N ranking** by liquidity

### 🔔 Anomaly Detection
- **5 detection algorithms**:
  - Volume spikes (unusual trading activity)
  - Price movements (abnormal returns)
  - Opening gaps (gap up/down detection)
  - Volatility spikes (unusual price ranges)
  - Liquidity changes (turnover anomalies)
- **Statistical analysis** using Z-scores
- **Severity classification**: High, Medium, Low
- **Visual alerts** with color-coded indicators
- **Detailed anomaly descriptions**

### 📊 Combined Analysis
- **Cross-reference** liquid stocks with anomalies
- **Priority signals**: high liquidity + anomalies = best opportunities
- **Comparative views**: liquid vs illiquid anomalies
- **Integrated reporting**

## 🚀 Quick Start

### Method 1: Using Launch Script (Recommended)

```bash
# Make the script executable
chmod +x launch_dashboard.sh

# Launch the dashboard
./launch_dashboard.sh
```

### Method 2: Manual Launch

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the dashboard
streamlit run psx_trading_dashboard.py
```

### Method 3: Python Command

```bash
python3 -m streamlit run psx_trading_dashboard.py
```

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Internet connection (for fetching PSX data)

### Dependencies

All dependencies are listed in `requirements.txt`:

```
yfinance>=0.2.36    # Stock data fetching
pandas>=2.0.0       # Data manipulation
numpy>=1.24.0       # Numerical computing
streamlit>=1.28.0   # Web UI framework
plotly>=5.18.0      # Interactive charts
```

Install all at once:

```bash
pip3 install -r requirements.txt
```

Or install individually:

```bash
pip3 install streamlit plotly yfinance pandas numpy
```

## 🎯 Usage Guide

### 1. Home Page
- Overview of available tools
- Quick navigation to each module
- Market overview statistics

### 2. Liquidity Screener

**Parameters:**
- **Lookback Period**: 7-90 days (default: 30)
- **Minimum Price**: Filter threshold in PKR (default: Rs 20)
- **Number of Stocks**: 10-100 stocks to display (default: 50)

**Workflow:**
1. Adjust parameters using sliders
2. Click "Run Liquidity Analysis"
3. Wait for analysis (1-3 minutes)
4. View results in charts and tables
5. Export data as CSV or JSON

**Output:**
- Summary statistics
- Top stocks bar chart
- Price distribution pie chart
- Price vs Volume scatter plot
- Detailed data table
- Export options

### 3. Anomaly Detection

**Parameters:**
- **Lookback Period**: 30-90 days (default: 60)
- **Z-Score Threshold**: 2.0-4.0σ (default: 2.5)
- **Stock Selection**:
  - Use liquid stocks (automatic)
  - Custom list (manual entry)

**Workflow:**
1. Configure detection sensitivity
2. Select stocks to analyze
3. Click "Detect Anomalies"
4. Wait for analysis (2-5 minutes)
5. Review detected anomalies
6. Investigate specific stocks

**Output:**
- Anomaly summary statistics
- Severity breakdown (High/Medium/Low)
- Charts by stock and type
- Detailed anomaly descriptions
- Z-score values

### 4. Combined Analysis

**Prerequisites:**
- Run both Liquidity Screener and Anomaly Detection first

**Features:**
- Shows stocks with high liquidity AND anomalies
- Separates liquid stocks (safe) vs anomaly stocks (opportunity/risk)
- Prioritizes trading candidates
- Combined export option

## 📊 Understanding the Metrics

### Liquidity Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| **Avg Traded Value** | Daily average value traded | Volume × Price (30-day avg) |
| **Avg Volume** | Average shares traded daily | Sum(Volume) / Days |
| **Current Price** | Latest closing price | Most recent Close |
| **Trading Days** | Days with data available | Count of valid days |

### Anomaly Metrics

| Type | Detection Method | Threshold |
|------|------------------|-----------|
| **Volume Spike** | Z-score on volume | 2.5σ (configurable) |
| **Price Movement** | Z-score on returns | 2.5σ (configurable) |
| **Opening Gap** | Gap % vs historical | 2.5σ (configurable) |
| **Volatility Spike** | High-Low range % | 2.5σ (configurable) |
| **Liquidity Change** | Turnover variation | 2.5σ (configurable) |

### Severity Levels

- 🔴 **High** (≥4.0σ): Extremely rare events, ~0.003% probability
- 🟡 **Medium** (≥3.0σ): Significant events, ~0.13% probability
- 🟢 **Low** (≥2.5σ): Notable events, ~0.6% probability

## 🎨 Dashboard Features

### Interactive Elements
- ✅ Real-time parameter adjustment
- ✅ Responsive charts (zoom, pan, hover)
- ✅ Expandable detail sections
- ✅ Sortable data tables
- ✅ One-click exports
- ✅ Session state preservation

### Visual Design
- Clean, modern interface
- Color-coded severity indicators
- Professional financial charts
- Mobile-responsive layout
- Dark/light theme support (Streamlit default)

## 📱 Accessing the Dashboard

After launching, the dashboard will be available at:

```
Local URL:    http://localhost:8501
Network URL:  http://YOUR_IP:8501
```

To access from other devices on your network:
1. Find your IP address: `ifconfig` or `ipconfig`
2. Use the Network URL shown in terminal
3. Ensure firewall allows port 8501

## 🔧 Troubleshooting

### Dashboard won't start

```bash
# Check if port 8501 is already in use
lsof -i :8501

# Use a different port
streamlit run psx_trading_dashboard.py --server.port 8502
```

### Data fetching errors

- Check internet connection
- Verify yfinance is properly installed
- Some stocks may be delisted (normal)
- Try reducing the number of stocks analyzed

### Slow performance

- Reduce lookback period
- Analyze fewer stocks at once
- Close other browser tabs
- Restart the dashboard

### Import errors

```bash
# Reinstall all dependencies
pip3 uninstall -y streamlit plotly yfinance pandas numpy
pip3 install -r requirements.txt
```

## 📈 Best Practices

### For Liquidity Screening
1. **Start with Rs 20 filter** to avoid penny stocks
2. **Use 30-day period** for balanced view
3. **Focus on top 50** for best opportunities
4. **Cross-reference with sectors** for diversification

### For Anomaly Detection
1. **Use Z-score 2.5** for initial screening
2. **Combine with liquidity** for tradeable signals
3. **Investigate high-severity** anomalies first
4. **Check multiple anomaly types** for confirmation

### For Trading Decisions
1. **High liquidity + Medium/High anomaly** = Best signals
2. **Low liquidity + High anomaly** = Risky, need investigation
3. **High liquidity + No anomaly** = Safe holdings
4. **Always verify** with other analysis tools

## 🔄 Data Updates

- **Real-time**: Data fetched on each analysis run
- **Cache**: No caching between runs (always fresh)
- **Historical**: Uses Yahoo Finance PSX data
- **Delays**: Market data may have 15-20 minute delay

## 💾 Export Formats

### CSV Export
- Compatible with Excel, Google Sheets
- Includes all metrics
- Timestamp in filename
- UTF-8 encoding

### JSON Export
- API-friendly format
- Includes metadata
- Structured for parsing
- Good for integration

## 🛠️ Advanced Configuration

### Streamlit Config

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
```

### Custom Stock Lists

Edit the stock lists in respective agent files:
- `psx_liquidity_screener.py` - Line 60+
- Add/remove stocks as needed

## 📞 Support

For issues or questions:
1. Check this README
2. Review the troubleshooting section
3. Check terminal output for error messages
4. Verify all dependencies are installed

## 🎓 Learning Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Plotly Charts](https://plotly.com/python/)
- [yfinance Guide](https://pypi.org/project/yfinance/)
- [PSX Official](https://www.psx.com.pk/)

## 📄 License

This dashboard is part of the PSX Trading Analysis toolkit.

---

**Happy Trading! 📈** Remember: Always do your own research and never invest more than you can afford to lose.
