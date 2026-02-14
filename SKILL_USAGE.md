# Technical Analysis Skill - Usage Guide

## Overview

The Technical Analysis skill has been installed at `~/.claude/skills/technical-analysis.md` and provides a command-line interface to analyze PSX stocks with real-time technical indicators.

## Installation Complete ✅

The skill is now available in Claude Code. You can invoke it using:

```bash
/technical-analysis [SYMBOL1 SYMBOL2 ...]
```

## Quick Start

### Default Analysis (HBL, LUCK, PSO)

Simply run:
```bash
python3 run_technical_analysis.py
```

Or use the skill:
```bash
/technical-analysis
```

### Custom Symbols

Analyze specific stocks:
```bash
python3 run_technical_analysis.py HBL OGDC PPL ENGRO
```

Or via skill:
```bash
/technical-analysis HBL OGDC PPL ENGRO
```

### Single Stock Deep Dive

```bash
python3 run_technical_analysis.py HBL
```

## Output Explained

### Key Indicators Section

```
📈 Key Indicators:
   ATR                 :         8.80   ← Average True Range (volatility)
   RSI                 :        26.88   ← Relative Strength Index (momentum)
   MACD                :        -3.30   ← Moving Average Convergence Divergence
   SMA_20              :       341.95   ← 20-day Simple Moving Average
   SMA_50              :       334.67   ← 50-day Simple Moving Average
   Stochastic_K        :         9.80   ← Stochastic oscillator %K
   BB_Upper/Lower      :  363.07/320.83 ← Bollinger Bands (upper/lower)
```

### Signal Strength

- 🔴 **Strong**: High conviction signal (RSI extreme, major crossover)
- 🟡 **Moderate**: Standard signal (oversold/overbought, trend confirmation)
- ⚪ **Weak**: Minor signal (early warning, watch zone)

### Trading Signals Interpretation

#### RSI (Relative Strength Index)
- **RSI > 70**: Overbought → Potential selling opportunity
- **RSI < 30**: Oversold → Potential buying opportunity
- **RSI 30-70**: Neutral territory

#### MACD (Moving Average Convergence Divergence)
- **MACD crosses above signal**: Bullish crossover → Buy signal
- **MACD crosses below signal**: Bearish crossover → Sell signal

#### Stochastic Oscillator
- **%K > 80**: Overbought
- **%K < 20**: Oversold
- **%K crosses %D upward**: Bullish signal

#### Bollinger Bands
- **Price at upper band**: Potentially overbought
- **Price at lower band**: Potentially oversold
- **Band squeeze**: Low volatility, breakout coming

#### SMA Crossovers
- **SMA(20) crosses above SMA(50)**: Golden cross → Bullish
- **SMA(20) crosses below SMA(50)**: Death cross → Bearish
- **Price above SMA(200)**: Long-term uptrend intact

### Overall Bias

The agent aggregates all signals to provide an overall market sentiment:

```
💡 Overall Bias: 📈 Bullish
   Confidence: 75%
```

**Confidence calculation**:
- Strong signals = 3 points
- Moderate signals = 2 points
- Weak signals = 1 point

Bullish points - Bearish points = Net sentiment
Confidence = Agreement level among indicators

### Summary Section

```
📊 SUMMARY:
--------------------------------------------------------------------------------

🟢 OVERSOLD (RSI ≤ 30 - Potential Buy):
   HBL: RSI = 26.9
   OGDC: RSI = 22.3

🔴 OVERBOUGHT (RSI ≥ 70 - Potential Sell):
   None

📈 Bullish bias: 2/2
📉 Bearish bias: 0/2
```

This helps you quickly identify:
- **Oversold stocks**: Good buying candidates
- **Overbought stocks**: Consider taking profits
- **Market sentiment**: Overall bullish/bearish split

## Real-World Example

From the latest run (Feb 14, 2026):

### HBL Analysis
```
RSI: 26.88 (OVERSOLD)
Stochastic %K: 9.8 (OVERSOLD)
Overall Bias: Bullish (100% confidence)
```

**Interpretation**: HBL is deeply oversold with both RSI and Stochastic in oversold territory. This suggests a potential bounce/reversal opportunity. The 100% confidence means all indicators agree on the bullish outlook.

**Action**: Consider buying if price confirms support at lower Bollinger Band (~320.83).

### OGDC Analysis
```
RSI: 22.27 (EXTREMELY OVERSOLD)
Price at lower Bollinger Band
Stochastic %K: 11.22 (OVERSOLD)
Overall Bias: Bullish (100% confidence)
```

**Interpretation**: OGDC is even more oversold than HBL. The price touching the lower Bollinger Band adds confirmation. Three moderate signals all point to bullish reversal potential.

**Action**: Strong buy candidate if volume confirms accumulation.

## Popular PSX Symbols

| Symbol | Company | Sector |
|--------|---------|--------|
| HBL | Habib Bank Limited | Banking |
| LUCK | Lucky Cement | Cement |
| PSO | Pakistan State Oil | Oil & Gas |
| OGDC | Oil & Gas Development Company | Oil & Gas |
| PPL | Pakistan Petroleum Limited | Oil & Gas |
| ENGRO | Engro Corporation | Conglomerate |
| HUBC | Hub Power Company | Power |
| MCB | MCB Bank Limited | Banking |
| UBL | United Bank Limited | Banking |
| MEBL | Meezan Bank Limited | Islamic Banking |
| TRG | TRG Pakistan Limited | IT Services |
| PTCL | Pakistan Telecommunication | Telecom |
| EFERT | Engro Fertilizers | Fertilizer |
| FFC | Fauji Fertilizer Company | Fertilizer |
| DGKC | DG Khan Cement | Cement |

## Advanced Usage

### Compare Sector Performance

Analyze all banks:
```bash
python3 run_technical_analysis.py HBL MCB UBL MEBL
```

Analyze cement sector:
```bash
python3 run_technical_analysis.py LUCK DGKC MLCF
```

### Portfolio Health Check

Check your portfolio:
```bash
python3 run_technical_analysis.py HBL OGDC PPL ENGRO LUCK
```

### Find Trading Opportunities

Run broad market scan:
```bash
python3 run_technical_analysis.py HBL LUCK PSO OGDC PPL ENGRO HUBC MCB UBL TRG
```

Look in the summary for:
- Oversold stocks (RSI < 30) → Buy candidates
- Overbought stocks (RSI > 70) → Sell candidates
- Bullish crossovers → Momentum plays

## Integration with Anomaly Detection

Combine technical analysis with the anomaly detection agent:

```bash
# Run full pipeline with technicals
python3 run_integrated_analysis.py --stocks preset --top 10 --save-technicals

# This will:
# 1. Select liquid stocks
# 2. Sync price data
# 3. Fetch news
# 4. Run technical analysis ← NEW
# 5. Detect anomalies
# 6. Correlate news with anomalies + technical context
```

The integrated pipeline shows technical signals alongside anomalies:

```
================================================================================
ANOMALY: HBL - High Volume (Z-Score: 3.5)
================================================================================
Date: 2026-02-14
Price: 335.00 (Change: -2.5%)
Volume: 1,500,000 (3.5x average)

📊 TECHNICAL CONTEXT:
   RSI: 26.9 (oversold)
   Bias: Bullish (100%)
   Key Signal: Price at lower Bollinger Band

💡 INTERPRETATION: High volume during oversold conditions suggests smart money
   accumulation. Potential reversal opportunity.

📰 RELATED NEWS:
   - HBL announces Q4 earnings beat...
```

## Performance Metrics

### First Run (Empty Database)
- Fetches 250 days of historical data
- Time: ~5-10 minutes for 10 stocks
- Network intensive

### Subsequent Runs (Incremental Updates)
- Only fetches new trading days (1-2 days)
- Time: ~10-20 seconds for 10 stocks
- 95% faster than first run

### Database Growth
- ~15 MB for 30 stocks × 250 days
- ~100 KB/day ongoing

## Troubleshooting

### "No module named 'yfinance'"

Install dependencies:
```bash
pip install yfinance pandas numpy
```

### "No data found for symbol"

Check if symbol is valid:
- Use `.KA` suffix internally (handled automatically)
- Verify symbol exists on PSX
- Try with a different known symbol (e.g., HBL)

### "Price store failed"

Reset the database:
```bash
rm -rf price_data/*.db
python3 run_technical_analysis.py
```

### Slow performance

First run is slow (fetching 250 days). Subsequent runs are much faster due to incremental updates.

## Best Practices

1. **Run daily**: Technical indicators evolve daily
2. **Combine signals**: Don't rely on a single indicator
3. **Check volume**: Confirm signals with volume analysis
4. **Use support/resistance**: Technical levels matter
5. **Correlate with news**: Technical + fundamental = better decisions
6. **Watch confidence**: Low confidence = mixed signals, proceed with caution
7. **Respect trends**: Don't fight the SMA(200) trend

## What's Under the Hood

### Data Flow

```
yfinance API (PSX .KA symbols)
    ↓
PSXPriceStore (prices.db)
    ↓ (incremental fetch)
PSXTechnicalAgent
    ↓ (compute indicators)
TechnicalSnapshot
    ↓ (signal aggregation)
Console Output
```

### Indicators Computed

1. **SMA(20, 50, 200)**: Trend identification
2. **EMA(12, 26)**: MACD components
3. **RSI(14)**: Momentum oscillator
4. **MACD**: Trend and momentum
5. **Stochastic(%K, %D)**: Overbought/oversold
6. **Bollinger Bands(20, 2)**: Volatility bands
7. **ATR(14)**: Volatility measure
8. **OBV**: Volume trend

All computed using pandas/numpy on locally stored data.

## Next Steps

1. **Create a watchlist**: Save frequently analyzed symbols in a script
2. **Set up alerts**: Modify code to email/notify on specific signals
3. **Backtest strategies**: Use historical data to test indicator combinations
4. **Build screeners**: Find stocks matching specific technical criteria
5. **Add more indicators**: Extend with Fibonacci, pivot points, etc.

## Support

For issues or feature requests:
- Review implementation in `psx_technical_agent.py`
- Check documentation in `TECHNICAL_ANALYSIS_README.md`
- Modify signal thresholds in the agent code

---

**Ready to use!** Just run:
```bash
python3 run_technical_analysis.py [SYMBOLS]
```

Happy trading! 📈
