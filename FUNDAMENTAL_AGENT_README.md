# PSX Fundamental Analysis Agent

## Overview

The PSX Fundamental Analysis Agent validates momentum signals with comprehensive financial health assessment for Pakistan Stock Exchange (PSX) stocks. It performs multi-dimensional analysis including valuation, financial health, growth trajectory, and earnings momentum to generate actionable investment recommendations.

## Features

### 🚀 Dual Analysis Modes

1. **Quick Analysis** (< 2 minutes)
   - Fast validation using cached/computed metrics
   - Ideal for validating technical/sentiment signals
   - Uses 24-hour data cache for speed

2. **Deep Analysis** (5-10 minutes)
   - Comprehensive research with fresh data fetching
   - Includes peer comparison and DCF valuation
   - Used for weekly scans or conflicting signals

### 📊 Component Scoring System

The agent calculates a composite fundamental score (0-100) based on four weighted components:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Valuation** | 30% | P/E, P/B, Dividend Yield, EV/EBITDA |
| **Financial Health** | 40% | Debt ratios, liquidity, profitability (ROA, ROE) |
| **Growth** | 20% | Revenue/earnings growth, margin trends |
| **Momentum** | 10% | Earnings surprises, analyst revisions |

### 🚩 Red Flag Detection

Automatically detects and penalizes financial warning signs:

- **Critical**: Negative equity → Auto-reject
- **High**: Debt spike (D/E > 1.5 + 50% growth) → Auto-reject
- **High**: Negative cash flow (2+ quarters) → Auto-reject
- **Medium**: Declining margins (>5% for 2+ quarters) → -50% score
- **Medium**: Revenue decline (>10% YoY) → -30% score
- **Medium**: Low liquidity (Current ratio < 1.0) → -30% score

### 🎯 Investment Recommendations

- **BUY**: Score ≥ 70 (no critical red flags)
- **HOLD**: Score 50-69
- **SELL**: Score < 50 or critical red flags present

## Installation

### Dependencies

```bash
pip install pandas numpy yfinance
```

### Files

- `psx_fundamental_agent.py` - Main agent implementation
- `test_fundamental_agent.py` - Comprehensive test suite

## Usage

### Quick Start

```python
from psx_fundamental_agent import PSXFundamentalAgent

# Initialize agent
agent = PSXFundamentalAgent(cache_ttl_hours=24)

# Quick analysis (< 2 min)
score = agent.quick_analysis("OGDC")
agent.print_analysis(score)

# Deep analysis (comprehensive)
deep_score = agent.deep_analysis("PPL")
agent.print_analysis(deep_score)
```

### Universe Screening

```python
# Screen multiple stocks
symbols = ["OGDC", "PPL", "HBL", "LUCK", "ENGRO"]
results = agent.screen_universe(symbols)

# Sort by score
for symbol, score in sorted(results.items(),
                           key=lambda x: x[1].fundamental_score,
                           reverse=True):
    print(f"{symbol}: {score.fundamental_score:.1f} - {score.recommendation.value}")
```

### Integration with Other Agents

```python
# Validate a technical signal
if technical_signal == "BUY":
    fundamental = agent.quick_analysis(symbol)

    if fundamental.recommendation == Recommendation.BUY and \
       fundamental.confidence in [Confidence.HIGH, Confidence.MEDIUM]:
        # Both technical and fundamental align - strong signal
        execute_trade(symbol, "BUY")
```

## Output Structure

### FundamentalScore Object

```python
{
  "symbol": "OGDC",
  "fundamental_score": 68.5,
  "recommendation": "BUY",
  "confidence": "high",

  "valuation": {
    "pe_ratio": 5.2,
    "pb_ratio": 1.1,
    "dividend_yield": 8.5,
    "ev_ebitda": 4.8
  },

  "financial_health": {
    "debt_to_equity": 0.15,
    "current_ratio": 2.1,
    "roa": 12.3,
    "roe": 18.5,
    "interest_coverage": 8.2
  },

  "growth_metrics": {
    "revenue_growth_yoy": 15.2,
    "earnings_growth_yoy": 22.1,
    "margin_trend": "expanding"
  },

  "red_flags": [],
  "catalysts": ["Strong revenue growth", "Expanding profit margins"],
  "fair_value": 195.00,
  "upside_pct": 12.3,
  "data_quality": 0.95
}
```

## PSX Sector Benchmarks

The agent uses sector-specific benchmarks for valuation scoring:

| Sector | Avg P/E | Avg P/B | Avg Div Yield | Avg D/E |
|--------|---------|---------|---------------|---------|
| Energy | 5.0 | 1.2 | 8.0% | 0.3 |
| Banking | 4.0 | 0.8 | 6.0% | 5.0* |
| Cement | 6.0 | 1.5 | 5.0% | 0.6 |
| Fertilizer | 7.0 | 1.8 | 4.5% | 0.4 |

*Banks naturally have higher leverage due to their business model.

## Data Sources

### Current Implementation
- **yfinance**: Real-time price and basic fundamental data
- **Mock data**: Enhanced metrics (for demo purposes)

### Production Roadmap
1. **PSX Website**: Quarterly/annual reports
2. **SECP Filings**: Official regulatory filings
3. **Bloomberg/Reuters**: Professional-grade financial data
4. **Analyst Research**: Reports from Arif Habib, AKD Securities, Topline
5. **News Sources**: Dawn Business, The News, Profit.pk

## Scoring Methodology

### Valuation Score (0-100)

```python
# Lower valuation = higher score (value bias)
PE Score  = 100 - ((PE - 5) * 10)      # PE < 5 → high score
PB Score  = 100 - ((PB - 1) * 33)      # PB < 1 → high score
DY Score  = Dividend_Yield * 10         # DY > 5% → high score
EV Score  = 100 - ((EV/EBITDA - 5) * 12) # EV/EBITDA < 5 → high score
```

### Financial Health Score (0-100)

```python
Debt Score     = 100 - (D/E * 50)        # Lower debt = better
Liquidity Score = Current_Ratio * 50      # Higher liquidity = better
ROA Score      = ROA * 5                  # ROA > 15% = high score
ROE Score      = ROE * 4                  # ROE > 20% = high score
Coverage Score = Interest_Coverage * 20   # >5x = safe
```

### Growth Score (0-100)

```python
Revenue Score = 50 + (Revenue_Growth * 3)    # 15%+ = high score
Earnings Score = 50 + (Earnings_Growth * 2.5) # 20%+ = high score
Margin Score = 50 + (Margin_Change * 10)      # Expanding = good
```

### Momentum Score (0-100)

```python
Surprise Score = 50 + (Earnings_Surprise * 2)   # Beat = good
Revision Score = 50 + (Estimate_Revisions * 25) # Upgrades = good
Catalyst Score = Num_Catalysts * 20             # More = better (max 5)
```

## Testing

Run the comprehensive test suite:

```bash
python test_fundamental_agent.py
```

Tests include:
- ✅ Quick analysis mode
- ✅ Deep analysis mode
- ✅ Component scoring
- ✅ Red flag detection
- ✅ Universe screening
- ✅ Data structure validation
- ✅ Output formatting

## Performance

- **Quick Analysis**: < 2 minutes (with cache)
- **Deep Analysis**: 5-10 minutes (fresh data)
- **Universe Screening**: ~2 minutes per 10 stocks (quick mode)

## Architecture Integration

### Message Flow

```
Anomaly Agent → Orchestration → Fundamental Agent
                                     ↓
                              [Quick Analysis]
                                     ↓
                              Return Score + Rec
```

### Typical Workflow

1. **Technical Agent** detects golden cross on OGDC
2. **Sentiment Agent** confirms positive news sentiment
3. **Orchestration** requests fundamental validation
4. **Fundamental Agent** runs quick analysis:
   - Score: 72/100
   - Recommendation: BUY
   - Confidence: HIGH
   - Red Flags: None
5. **Orchestration** generates final signal: **STRONG BUY**

## API Reference

### PSXFundamentalAgent

#### `__init__(cache_ttl_hours=24, price_store=None)`
Initialize the agent.

- `cache_ttl_hours`: Hours to cache fundamental data
- `price_store`: Optional PSXPriceStore instance

#### `quick_analysis(symbol: str) -> FundamentalScore`
Fast validation using cached metrics.

#### `deep_analysis(symbol: str) -> FundamentalScore`
Comprehensive analysis with fresh data.

#### `analyze_symbol(symbol: str, mode: str) -> FundamentalScore`
Convenience method supporting both modes.

#### `screen_universe(symbols: List[str]) -> Dict[str, FundamentalScore]`
Screen multiple stocks.

#### `print_analysis(score: FundamentalScore)`
Print formatted analysis report.

## Example Output

```
================================================================================
FUNDAMENTAL ANALYSIS: OGDC
================================================================================

📊 SUMMARY
   Score: 72.3/100
   Recommendation: BUY
   Confidence: HIGH
   Analysis Mode: deep
   Processing Time: 1250ms

📈 COMPONENT SCORES
   Valuation:        85.2/100 (30% weight)
   Financial Health: 78.5/100 (40% weight)
   Growth:           62.1/100 (20% weight)
   Momentum:         45.8/100 (10% weight)

💰 VALUATION
   P/E Ratio:       4.8
   P/B Ratio:       1.1
   Dividend Yield:  9.2%
   EV/EBITDA:       4.2

💪 FINANCIAL HEALTH
   Debt/Equity:     0.18
   Current Ratio:   2.3
   ROA:             14.5%
   ROE:             19.2%
   Interest Cover:  9.5x

📈 GROWTH
   Revenue Growth:  +18.5% YoY
   Earnings Growth: +24.2% YoY
   Margin Trend:    Expanding

✨ CATALYSTS
   • Strong revenue growth
   • Expanding profit margins
   • Recent earnings beat

🎯 PRICE TARGET
   Fair Value:      185.50
   Upside/Downside: +15.2%

   Data Quality:    95%
================================================================================
```

## Limitations & Future Enhancements

### Current Limitations
1. Uses yfinance for data (limited PSX coverage)
2. Mock data for some enhanced metrics
3. No real-time SECP filings integration
4. Simplified DCF valuation model

### Planned Enhancements
1. **Data Sources**:
   - Direct PSX API integration
   - SECP filing parser
   - Bloomberg Terminal integration
   - Analyst report aggregation

2. **Features**:
   - Multi-year financial trend analysis
   - Peer comparison with sector percentiles
   - Full DCF model with customizable assumptions
   - Credit rating integration
   - Insider trading monitoring

3. **Performance**:
   - Async data fetching
   - Distributed caching (Redis)
   - Pre-computation of common metrics

## Contributing

To add new features or fix issues:

1. Maintain the existing scoring methodology
2. Add comprehensive tests
3. Update this documentation
4. Follow PSX-specific benchmarks

## License

Internal use only.

## Support

For questions or issues, contact the development team.

---

**Last Updated**: 2026-02-15
**Version**: 1.0.0
**Status**: Production Ready (with mock data sources)
