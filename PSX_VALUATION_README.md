# PSX Valuation Agent

Production-ready fundamental valuation analysis for Pakistan Stock Exchange (PSX) stocks.

## Overview

The PSX Valuation Agent implements four complementary valuation methodologies with weighted aggregation to provide comprehensive fundamental analysis for PSX-listed companies.

### Valuation Methods

1. **DCF (Discounted Cash Flow)** - 35% weight
   - Multi-stage growth model
   - Three stages: high growth → transition → terminal perpetuity
   - WACC-based discounting
   - Projected free cash flows over 7 years + terminal value

2. **Owner Earnings** - 35% weight
   - Buffett-style economic profit valuation
   - Formula: Net Income + D&A - Maintenance CapEx - Working Capital Change
   - 25% margin of safety built-in
   - Uses 80% of capex as maintenance assumption

3. **EV/EBITDA Multiple** - 20% weight
   - Sector-specific multiples for PSX market
   - Converts enterprise value to equity value
   - Adjusts for net debt

4. **Residual Income Model** - 10% weight
   - Edwards-Bell-Ohlson framework
   - Book value foundation
   - CAPM-based cost of equity
   - 20% margin of safety

## Features

### PSX Market Calibration
- **Risk-free rate**: 13% (Pakistan T-bills)
- **Market risk premium**: 8% (emerging market)
- **Corporate tax rate**: 29%
- **Terminal growth**: 3% (GDP proxy)
- **Default beta**: 1.2 (PSX higher volatility)

### Advanced Capabilities
- **Beta Estimation**: Calculated from 2-year historical returns vs KSE-100 index
- **WACC Calculation**: CAPM-based with debt tax shield
- **Growth Rate Estimation**: Weighted average of revenue, FCF, and earnings growth
- **Data Quality Validation**: Comprehensive checks with warnings
- **Confidence Scoring**: Based on gap magnitude and method agreement
- **SQLite Storage**: Persistent storage of valuation history

### Data Structures
- **Enums**: `ValuationSignal` (Bullish/Bearish/Neutral), `ValuationMethod`
- **Configuration**: `ValuationConfig` with all parameters customizable
- **Financial Data**: `FinancialData` from yfinance
- **Valuation Output**: `ValuationSnapshot` with all methods and aggregated results

## Installation

### Requirements
```bash
pip install -r requirements_valuation.txt
```

Dependencies:
- `yfinance >= 0.2.0` - Financial data from Yahoo Finance
- `pandas >= 1.3.0` - Data manipulation
- `numpy >= 1.20.0` - Numerical computations

### Database
The agent automatically creates a SQLite database at `price_data/valuations.db` with three tables:
- `valuations` - Overall valuation results
- `method_valuations` - Individual method results
- `financial_snapshots` - Historical financial data

## Usage

### Basic Usage

```python
from psx_valuation_agent import PSXValuationAgent

# Initialize agent
agent = PSXValuationAgent()

# Analyze single stock
snapshot = agent.analyze_symbol('HBL', sector='Banks')

# View results
print(f"Symbol: {snapshot.symbol}")
print(f"Signal: {snapshot.overall_signal.value}")
print(f"Valuation Gap: {snapshot.weighted_valuation_gap:+.1%}")
print(f"Confidence: {snapshot.overall_confidence:.0%}")
print(f"Intrinsic Value: PKR {snapshot.weighted_intrinsic_value:,.0f}")
```

### Batch Analysis

```python
# Analyze multiple stocks
stocks = {
    'HBL': 'Banks',
    'LUCK': 'Cement',
    'PSO': 'Oil & Gas',
    'ENGRO': 'Fertilizer',
    'FFC': 'Fertilizer'
}

results = agent.analyze_batch(
    symbols=list(stocks.keys()),
    sectors=stocks
)

# Print summary
for symbol, snapshot in results.items():
    print(f"{symbol}: {snapshot.overall_signal.value} "
          f"({snapshot.weighted_valuation_gap:+.1%})")
```

### Custom Configuration

```python
from psx_valuation_agent import PSXValuationAgent, ValuationConfig

# Create custom configuration
config = ValuationConfig(
    risk_free_rate=0.14,          # 14% T-bills
    required_return=0.20,          # 20% required return
    dcf_weight=0.40,               # Higher DCF weight
    owner_earnings_weight=0.40,
    ev_ebitda_weight=0.15,
    residual_income_weight=0.05,
    bullish_threshold=0.25,        # 25% undervalued for bullish signal
    bearish_threshold=-0.15        # 15% overvalued for bearish signal
)

# Initialize with custom config
agent = PSXValuationAgent(config=config)
snapshot = agent.analyze_symbol('LUCK', sector='Cement')
```

### Valuation History

```python
# Get valuation history for a symbol
history = agent.get_valuation_history('HBL', days=30)

for record in history:
    print(f"{record['date']}: {record['signal']} "
          f"(Gap: {record['valuation_gap']:+.1%})")
```

### Accessing Individual Methods

```python
snapshot = agent.analyze_symbol('PSO', sector='Oil & Gas')

# Access individual method results
for valuation in snapshot.valuations:
    print(f"\n{valuation.method.value}:")
    print(f"  Intrinsic Value: PKR {valuation.intrinsic_value:,.0f}")
    print(f"  Gap: {valuation.valuation_gap:+.1%}")
    print(f"  Signal: {valuation.signal.value}")
    print(f"  Confidence: {valuation.confidence:.1%}")

    # Access method-specific details
    for key, value in valuation.details.items():
        print(f"  {key}: {value}")
```

## Output Structure

### ValuationSnapshot
```python
@dataclass
class ValuationSnapshot:
    symbol: str                           # Stock symbol
    date: str                             # Valuation date
    current_price: float                  # Current market price
    market_cap: float                     # Market capitalization

    valuations: List[MethodValuation]     # Individual method results

    weighted_intrinsic_value: float       # Weighted average intrinsic value
    weighted_valuation_gap: float         # Weighted gap percentage
    overall_signal: ValuationSignal       # Bullish/Bearish/Neutral
    overall_confidence: float             # Confidence score (0-1)

    wacc: float                           # Weighted average cost of capital
    beta: float                           # Estimated beta
    growth_rate: float                    # Estimated growth rate

    data_quality_score: float             # Data quality (0-1)
    warnings: List[str]                   # Data quality warnings
```

## Sector Multiples (EV/EBITDA)

PSX-calibrated sector multiples:
- **Banks**: 6.5x
- **Cement**: 8.0x
- **Oil & Gas**: 7.5x
- **Fertilizer**: 7.0x
- **Textile**: 5.5x
- **Power**: 6.0x
- **Food**: 9.0x
- **Chemicals**: 8.5x
- **Default**: 7.5x

## Signal Thresholds

Default thresholds (customizable via `ValuationConfig`):
- **Bullish**: Intrinsic value > Current value by 20%+ (undervalued)
- **Bearish**: Intrinsic value < Current value by 20%+ (overvalued)
- **Neutral**: Within ±20% range (fairly valued)

## Data Quality Validation

The agent validates:
- ✓ Critical financial metrics presence (revenue, net income, FCF, EBITDA, book value)
- ✓ Reasonable growth rates (flags outliers > 100%)
- ✓ Balance sheet health (debt/equity, negative book value)
- ✓ FCF quality (flags negative FCF)
- ✓ Data completeness score

Valuations with 4+ critical warnings are rejected.

## Testing

Run the comprehensive test suite:

```bash
python test_psx_valuation.py
```

Tests include:
1. Single stock valuation
2. Batch analysis
3. Custom configuration
4. Valuation history
5. Data quality validation
6. All valuation methods

## Architecture

### Pattern Compliance
Follows the established PSX agent patterns:
- Class-based agent with `analyze_symbol()` method
- Uses `yfinance` for data (like `PSXPriceStore`)
- SQLite storage with proper schema and indexes
- Dataclasses for structured output
- Enums for typed signals and methods
- Comprehensive error handling

### Integration with PSX Ecosystem
```python
# Use with PSXPriceStore for price data
from psx_price_store import PSXPriceStore
from psx_valuation_agent import PSXValuationAgent

price_store = PSXPriceStore()
valuation_agent = PSXValuationAgent()

# Get price data
prices = price_store.get_prices('HBL', days=250)

# Get valuation
valuation = valuation_agent.analyze_symbol('HBL', sector='Banks')

# Combined analysis
print(f"Current Price: PKR {valuation.current_price}")
print(f"Intrinsic Value: PKR {valuation.weighted_intrinsic_value/1e9:.2f}B")
print(f"Signal: {valuation.overall_signal.value}")
```

## Performance

- **Single stock analysis**: ~5-10 seconds (including yfinance API calls)
- **Batch analysis**: ~5-10 seconds per stock (API rate limits apply)
- **Database queries**: Milliseconds (indexed)
- **Memory usage**: ~50-100 MB per stock analysis

## Limitations & Considerations

1. **Data Dependency**: Relies on yfinance API availability and data quality
2. **PSX Coverage**: Symbol must exist in Yahoo Finance with `.KA` suffix
3. **Financial Statement Lag**: Uses most recent available financial statements
4. **Beta Calculation**: Requires 60+ days of historical data; falls back to default (1.2)
5. **Sector Multiples**: Static multiples; may need periodic updates
6. **Emerging Market**: Higher volatility and risk premiums vs developed markets

## Customization

All parameters are configurable via `ValuationConfig`:

```python
config = ValuationConfig(
    # Market parameters
    risk_free_rate=0.13,
    market_risk_premium=0.08,
    corporate_tax_rate=0.29,

    # Growth assumptions
    default_growth_rate=0.08,
    max_growth_cap=0.30,
    terminal_growth_rate=0.03,

    # Discount rates
    required_return=0.18,
    default_discount_rate=0.15,

    # WACC bounds
    wacc_floor=0.10,
    wacc_ceiling=0.25,

    # Beta bounds
    default_beta=1.2,
    min_beta=0.6,
    max_beta=2.5,

    # Method weights (must sum to 1.0)
    dcf_weight=0.35,
    owner_earnings_weight=0.35,
    ev_ebitda_weight=0.20,
    residual_income_weight=0.10,

    # Signal thresholds
    bullish_threshold=0.20,
    bearish_threshold=-0.20,

    # Safety margins
    owner_earnings_margin=0.25,
    residual_income_margin=0.20,

    # Sector multiples
    sector_multiples={
        'Banks': 6.5,
        'Cement': 8.0,
        # ... custom multiples
    }
)
```

## Example Output

```
================================================================================
VALUATION SUMMARY: HBL
================================================================================

Current Market Data:
  Price: PKR 185.50
  Market Cap: PKR 256,000,000,000
  Beta: 1.15
  WACC: 16.24%
  Growth Rate: 8.50%

Valuation Methods:

  DCF:
    Intrinsic Value: PKR 312,450,000,000
    Valuation Gap: +22.0%
    Signal: 📈 Bullish
    Confidence: 73%

  Owner Earnings:
    Intrinsic Value: PKR 298,200,000,000
    Valuation Gap: +16.5%
    Signal: 📈 Bullish
    Confidence: 55%

  EV/EBITDA:
    Intrinsic Value: PKR 285,600,000,000
    Valuation Gap: +11.6%
    Signal: ➖ Neutral
    Confidence: 39%

  Residual Income:
    Intrinsic Value: PKR 275,800,000,000
    Valuation Gap: +7.7%
    Signal: ➖ Neutral
    Confidence: 26%

================================================================================
OVERALL VALUATION
================================================================================

  Weighted Intrinsic Value: PKR 297,150,000,000
  Current Market Cap: PKR 256,000,000,000
  Valuation Gap: +16.1%

  Signal: 📈 Bullish
  Confidence: 61%
  Data Quality: 85%

================================================================================
```

## License

Part of the PSX Investment Analysis Suite.

## Contributing

When extending or modifying:
1. Maintain compatibility with existing PSX agent patterns
2. Update `ValuationConfig` for new parameters
3. Add comprehensive tests to `test_psx_valuation.py`
4. Update this README with changes
5. Follow existing code style and documentation standards
