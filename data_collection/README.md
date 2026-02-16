# Data Collection System

Flexible system for collecting historical price data from multiple sources with automatic fallback and local caching.

## Features

- **Multiple Data Sources**:
  - Yahoo Finance (API, most reliable)
  - CSV Import (manual data)
  - Investing.com (web scraping, less reliable)

- **Automatic Fallback**: Tries sources in priority order
- **Local Caching**: Avoids redundant network requests
- **Batch Collection**: Efficiently collect multiple symbols
- **Data Validation**: Ensures data quality and consistency

## Quick Start

### Python API

```python
from data_collection import DataCollectionManager

# Initialize manager
manager = DataCollectionManager()

# Collect 1 year of data
df = manager.collect('PPL', days=365)

# Collect multiple symbols
results = manager.collect_batch(['PPL', 'OGDC', 'PSO'], days=180)

# Import from CSV text
csv_content = """Date,Open,High,Low,Close,Volume
2026-01-01,100,105,98,103,1000000"""

result = manager.import_csv_text('SYMBOL', csv_content)
```

### Command Line

```bash
# Collect single symbol
python collect_data.py PPL --days 365

# Collect multiple symbols
python collect_data.py PPL OGDC PSO --days 180

# Import from CSV
python collect_data.py PPL --import-csv data/ppl.csv

# Force refresh (skip cache)
python collect_data.py PPL --days 365 --force

# Show cache info
python collect_data.py --cache-info PPL

# Clear cache
python collect_data.py --clear-cache PPL
python collect_data.py --clear-cache all
```

## Architecture

### Components

```
data_collection/
├── base_collector.py          # Abstract base class
├── csv_collector.py            # CSV import
├── yahoo_finance_collector.py  # Yahoo Finance API
├── investing_com_collector.py  # Investing.com scraper
├── data_manager.py             # High-level manager
└── README.md
```

### Data Flow

```
User Request
    ↓
DataCollectionManager
    ↓
Check Cache → Return if valid
    ↓
DataCollectorRegistry
    ↓
Try collectors in priority:
  1. CSV (local files)
  2. Yahoo Finance (API)
  3. Investing.com (scraper)
    ↓
Validate & Standardize
    ↓
Save to Cache
    ↓
Return DataFrame
```

## Data Sources

### 1. Yahoo Finance (Recommended)

**Pros**:
- Free API (via yfinance library)
- Reliable and fast
- Good historical data
- Supports multiple exchanges

**Cons**:
- Requires `yfinance` library
- PSX symbols need `.KA` suffix

**Installation**:
```bash
pip install yfinance
```

**Usage**:
```python
from data_collection import YahooFinanceCollector

collector = YahooFinanceCollector()
df = collector.get_prices_dataframe('PPL', start_date, end_date)
```

### 2. CSV Import

**Pros**:
- Simple and reliable
- No network required
- Full control over data

**Cons**:
- Manual data entry
- No automatic updates

**Expected Format**:
```csv
Date,Open,High,Low,Close,Volume
2026-01-01,100,105,98,103,1000000
2026-01-02,103,108,102,107,1200000
```

**Usage**:
```python
from data_collection import CSVCollector

collector = CSVCollector(data_dir="data/csv")
result = collector.import_from_text('PPL', csv_content)
```

### 3. Investing.com

**Pros**:
- Wide coverage
- Free access

**Cons**:
- Web scraping (fragile)
- May require JavaScript rendering
- Rate limits

**Note**: Disabled by default. Consider using Selenium for JavaScript-rendered content.

## Data Storage

### Directory Structure

```
data/
├── csv/              # CSV source files
│   ├── PPL.csv
│   └── OGDC.csv
└── cache/            # Cached data (Parquet format)
    ├── PPL.parquet
    └── OGDC.parquet
```

### Cache Format

- **Format**: Parquet (efficient, compressed)
- **Index**: DatetimeIndex
- **Columns**: Open, High, Low, Close, Volume

### Cache Management

```python
# Check cache
info = manager.get_cache_info('PPL')
print(info['rows'], info['start_date'], info['end_date'])

# Clear cache for symbol
manager.clear_cache('PPL')

# Clear all cache
manager.clear_cache()
```

## Adding Custom Data Sources

### 1. Create Collector Class

```python
from data_collection.base_collector import BaseDataCollector, CollectionResult

class MyCustomCollector(BaseDataCollector):
    def __init__(self):
        super().__init__("my_source")

    def collect_symbol(self, symbol, start_date, end_date):
        # Fetch data
        df = fetch_data_from_source(symbol, start_date, end_date)

        # Standardize
        df = self.standardize_dataframe(df)

        return CollectionResult(
            success=True,
            symbol=symbol,
            rows_collected=len(df),
            start_date=df.index[0],
            end_date=df.index[-1],
            source=self.source_name
        )

    def get_prices_dataframe(self, symbol, start_date, end_date):
        result = self.collect_symbol(symbol, start_date, end_date)
        return cached_df if result.success else None
```

### 2. Register Collector

```python
from data_collection import DataCollectionManager

manager = DataCollectionManager()

# Register custom collector
custom_collector = MyCustomCollector()
manager.registry.register(custom_collector, priority=8)
```

## Common Issues

### Yahoo Finance: Symbol Not Found

**Problem**: PSX symbols not found

**Solution**: PSX stocks on Yahoo Finance use `.KA` suffix:
- `PPL` → `PPL.KA`
- `OGDC` → `OGDC.KA`

The YahooFinanceCollector handles this automatically.

### Insufficient Historical Data

**Problem**: Not enough data for analysis (need 120+ days)

**Solutions**:
1. Collect longer history: `manager.collect('PPL', days=365)`
2. Import from CSV with longer history
3. Use alternative data source

### Web Scraping Fails

**Problem**: Investing.com scraper fails

**Solutions**:
1. Use Yahoo Finance instead (more reliable)
2. Import from CSV manually
3. Use Selenium for JavaScript-rendered content

## Performance

### Benchmark (approximate)

| Source | Speed | Reliability |
|--------|-------|-------------|
| Cache | < 0.1s | 100% |
| CSV | < 0.5s | 100% |
| Yahoo Finance | 1-2s | 95% |
| Investing.com | 3-5s | 60% |

### Optimization Tips

1. **Use cache**: Don't force refresh unless needed
2. **Batch collection**: Collect multiple symbols in one call
3. **Parquet format**: Fast binary format for caching
4. **Rate limiting**: Add delays for web scraping

## Examples

### Collect PPL Data (Simple)

```python
from data_collection import DataCollectionManager

manager = DataCollectionManager()
df = manager.collect('PPL', days=365)

print(f"Collected {len(df)} days")
print(df.tail())
```

### Batch Collection

```python
symbols = ['PPL', 'OGDC', 'PSO', 'ENGRO', 'MCB']
results = manager.collect_batch(symbols, days=180, delay_seconds=1.0)

for symbol, df in results.items():
    if df is not None:
        print(f"{symbol}: {len(df)} days")
```

### Import Manual Data

```python
csv_data = """Date,Open,High,Low,Close,Volume
2026-01-01,232,238,231,236,1110000
2026-01-02,236,242,235,240,1250000"""

result = manager.import_csv_text('PPL', csv_data)

if result.success:
    print(f"Imported {result.rows_collected} rows")
```

### Integration with Technical Analysis

```python
from data_collection import DataCollectionManager
from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig

# Collect data
manager = DataCollectionManager()
df = manager.collect('PPL', days=200)

# Create mock price store
class DataFramePriceStore:
    def __init__(self, data):
        self.data = data

    def get_prices(self, symbol, days=250):
        return self.data

# Run analysis
price_store = DataFramePriceStore(df)
agent = PSXTechnicalAgent(price_store, config=TechnicalAgentConfig())
snapshot = agent.analyze_symbol_enhanced('PPL')

print(f"Signal: {snapshot.overall_bias.value}")
print(f"Confidence: {snapshot.confidence:.0%}")
```

## Testing

Run tests for each collector:

```bash
# Test CSV collector
python -m data_collection.csv_collector

# Test Yahoo Finance
python -m data_collection.yahoo_finance_collector

# Test data manager
python -m data_collection.data_manager
```

## Dependencies

### Required
- pandas
- pyarrow (for Parquet format)

### Optional
- yfinance (for Yahoo Finance)
- requests (for web scraping)
- beautifulsoup4 (for web scraping)

Install all:
```bash
pip install pandas pyarrow yfinance requests beautifulsoup4
```

## License

Part of the PSX Technical Analysis System.
