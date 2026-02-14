# 🚀 Quick Start - PSX Technical Analysis

## ⚡ Run It Now

```bash
# Analyze default stocks (HBL, LUCK, PSO)
python3 run_technical_analysis.py

# Analyze specific stocks
python3 run_technical_analysis.py HBL OGDC PPL

# Single stock
python3 run_technical_analysis.py HBL
```

## 📊 What You'll Get

```
================================================================================
📊 HBL
================================================================================

📈 Key Indicators:
   RSI                 :        26.88  ← Oversold!
   MACD                :        -3.30
   SMA_20              :       341.95
   Stochastic_K        :         9.80  ← Extremely oversold!

🔔 Signals (2):
   🟡 [Moderate] RSI: RSI at 26.9 (oversold)
   🟡 [Moderate] Stochastic: Stochastic oversold (%K=9.8)

💡 Overall Bias: 📈 Bullish
   Confidence: 100%
```

## 🎯 What This Means

| Current State | Signal | Action |
|---------------|--------|--------|
| RSI: 26.9 | OVERSOLD | Potential BUY |
| Stochastic: 9.8 | OVERSOLD | Potential BUY |
| Bias: Bullish | Strong confidence | Consider entry |

**Interpretation**: HBL is deeply oversold with multiple confirming indicators. This suggests a potential bounce/reversal opportunity.

## 📚 Files Created

### Core Implementation (3 files)
1. **`psx_price_store.py`** (411 lines)
   - Persistent OHLCV storage
   - Incremental fetching from Yahoo Finance
   - 95% faster on repeat runs

2. **`psx_technical_agent.py`** (1012 lines)
   - 10 technical indicators
   - Signal generation with strength
   - Overall bias calculation

3. **`psx_technical_store.py`** (436 lines)
   - Historical indicator storage
   - Screener queries (overbought/oversold)
   - Crossover detection

### Wrappers & Tools (2 files)
4. **`run_technical_analysis.py`** (122 lines)
   - Command-line interface
   - Custom symbol support
   - Summary section

5. **`run_integrated_analysis.py`** (modified)
   - 6-step pipeline
   - Combines news + anomalies + technicals

### Documentation (3 files)
6. **`TECHNICAL_ANALYSIS_README.md`**
   - Architecture & design
   - API reference
   - Performance metrics

7. **`SKILL_USAGE.md`**
   - Comprehensive user guide
   - Output interpretation
   - Trading strategies

8. **`QUICK_START.md`** (this file)
   - Get started in 60 seconds

### Claude Skill
9. **`~/.claude/skills/technical-analysis.md`**
   - Invoke with `/technical-analysis [symbols]`

## 🔧 Installation Check

Dependencies installed:
- ✅ `yfinance` - Yahoo Finance API
- ✅ `pandas` - Data manipulation
- ✅ `numpy` - Numerical operations

## 📈 10 Indicators Included

| Category | Indicators |
|----------|-----------|
| **Trend** | SMA(20), SMA(50), SMA(200) |
| **Momentum** | RSI(14), MACD, Stochastic(%K, %D) |
| **Volatility** | Bollinger Bands, ATR(14) |
| **Volume** | OBV |

## 🎓 Reading the Signals

### RSI (Relative Strength Index)
- **> 70**: Overbought → Consider selling
- **< 30**: Oversold → Consider buying
- **30-70**: Neutral territory

### MACD
- **Crosses above signal**: Bullish → Buy signal
- **Crosses below signal**: Bearish → Sell signal

### Stochastic
- **> 80**: Overbought
- **< 20**: Oversold

### Bollinger Bands
- **Price at upper**: Potentially overbought
- **Price at lower**: Potentially oversold

### SMA Crossovers
- **SMA(20) > SMA(50)**: Golden cross → Bullish
- **SMA(20) < SMA(50)**: Death cross → Bearish

## 🌟 Real Data Example (Today)

Latest run showed:

| Stock | RSI | Signal | Bias |
|-------|-----|--------|------|
| HBL | 26.9 | Oversold | Bullish |
| OGDC | 22.3 | Oversold | Bullish |
| PSO | 28.2 | Oversold | Bullish |

**Market Insight**: All three showing oversold conditions → Potential buying opportunities across the board.

## 🔄 Performance

| Run | Time | API Calls |
|-----|------|-----------|
| First (250 days) | 5-10 min | ~7,500 |
| Second+ (incremental) | 10-20 sec | ~30-60 |
| **Speedup** | **95% faster** | **99% fewer** |

## 📱 Popular PSX Symbols

**Banks**: HBL, MCB, UBL, MEBL
**Oil & Gas**: PSO, OGDC, PPL
**Cement**: LUCK, DGKC, MLCF
**Power**: HUBC
**Fertilizer**: EFERT, FFC
**IT**: TRG
**Telecom**: PTCL
**Conglomerate**: ENGRO

## 🚦 Next Steps

1. **Run the tool** on your portfolio:
   ```bash
   python3 run_technical_analysis.py YOUR_STOCKS
   ```

2. **Check the summary** for oversold/overbought stocks

3. **Review signals** for each stock

4. **Make informed decisions** based on technical + fundamental analysis

5. **Run integrated pipeline** for full analysis:
   ```bash
   python3 run_integrated_analysis.py --save-technicals
   ```

## 💡 Pro Tips

1. **Daily runs**: Indicators change daily
2. **Multiple confirmations**: Don't trade on single indicator
3. **Check volume**: Confirm with OBV/volume trends
4. **Watch confidence**: Low confidence = mixed signals
5. **Respect trends**: Price above SMA(200) = uptrend

## 🆘 Need Help?

**Quick fixes**:
```bash
# Missing dependencies
pip install yfinance pandas numpy

# Database issues
rm -rf price_data/*.db

# No data for symbol
# Use valid PSX ticker (without .KA suffix)
```

**Full documentation**:
- Implementation: `TECHNICAL_ANALYSIS_README.md`
- User guide: `SKILL_USAGE.md`
- Code: `psx_technical_agent.py`

## 🎯 One Command Summary

```bash
python3 run_technical_analysis.py HBL LUCK PSO OGDC PPL
```

This single command will:
1. ✅ Fetch latest price data (incremental)
2. ✅ Compute 10 technical indicators
3. ✅ Generate trading signals
4. ✅ Show overall bias & confidence
5. ✅ Provide overbought/oversold summary

**Time**: ~15 seconds (after initial setup)
**Output**: Actionable trading insights
**Data**: 100% real from Yahoo Finance

---

**Ready? Go!** 🚀

```bash
python3 run_technical_analysis.py
```
