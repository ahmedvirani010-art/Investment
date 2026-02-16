# Anomaly-Technical Correlation Guide

## Overview

The **Anomaly-Technical Correlation System** identifies high-confidence trading signals by correlating anomaly detection with technical analysis. When both systems agree, you get "confluence signals" - powerful indicators that combine statistical anomalies with technical setups.

## 🎯 What It Does

### The Problem
- **Anomaly detection** finds unusual price/volume patterns but doesn't know direction
- **Technical analysis** shows trends but misses sudden changes
- Traders need **both** to confirm high-probability setups

### The Solution
The correlator identifies "confluence" scenarios where:
- A statistical anomaly occurs (volume spike, price gap, etc.)
- Technical indicators confirm the direction (trend, momentum, RSI)
- Both systems agree → **High-confidence actionable signal**

## 📊 Correlation Scoring

### Confluence Strength Levels

| Strength | Score Range | Description |
|----------|-------------|-------------|
| **Very Strong** | 0.80 - 1.00 | Both systems highly confident and aligned |
| **Strong** | 0.65 - 0.79 | Both systems aligned with good confidence |
| **Moderate** | 0.45 - 0.64 | Systems aligned but lower confidence |
| **Weak** | 0.25 - 0.44 | Signals present but conflicting or low confidence |
| **None** | 0.00 - 0.24 | No meaningful correlation |

### Scoring Algorithm

```python
Base Score = 0.0

# Anomaly severity (0.1 - 0.3)
if HIGH severity:    +0.3
if MEDIUM severity:  +0.2
if LOW severity:     +0.1

# Technical confidence (0.0 - 0.3)
+= technical_confidence * 0.3

# Directional alignment (0.1 - 0.3)
if directions match:     +0.3
if not conflicting:      +0.1

# Combination bonuses (0.0 - 0.25)
# Volume spike + breakout above SMA(200): +0.15
# Volume spike + bullish RSI (50-70):     +0.10
# Price movement + trend confirmation:    +0.10
# Opening gap + momentum confirmation:    +0.10

Total Score = min(1.0, sum of above)
```

## 🔥 Powerful Combinations

### 1. Volume Spike + Breakout
**Example**: LUCK - Score 0.86 (Very Strong)

```
Anomaly:    Extreme volume spike (5.0M vs 1.0M baseline, z=4.5σ)
Technical:  Bullish bias (70% confidence)
            - Price above SMA(200): 465 > 430
            - RSI at 65 (bullish zone)
            - SMA(50) crossover

🎯 ACTIONABLE: Strong buy signal
```

**Why powerful**: High volume confirms genuine interest. Breakout above key level shows strength.

### 2. Opening Gap + Trend Confirmation
**Example**: HBL - Score 0.92 (Very Strong)

```
Anomaly:    Large gap down (-3.8%, z=-4.2σ)
Technical:  Bearish bias (75% confidence)
            - Death cross (SMA(50) < SMA(200))
            - Price below SMA(200): 155 < 160
            - RSI at 35 (weak)

🎯 ACTIONABLE: Strong sell signal / avoid
```

**Why powerful**: Gap confirms sentiment shift. Technical breakdown shows weakness.

### 3. Price Movement + Momentum
When a sharp price move aligns with momentum indicators (MACD, Stochastic), it suggests continuation.

### 4. Conflicting Signals (Warning!)
**Example**: PSO - Score 0.58 (Moderate)

```
Anomaly:    Bearish price drop (-5.2%, z=-3.2σ)
Technical:  Bullish bias (60% confidence)
            - RSI oversold at 28
            - Potential bounce setup

⚠️ CONFLICTING: Caution advised
```

**Why important**: Identifies divergences. May signal reversal or dangerous trap.

## 📈 Usage

### 1. Integrated Analysis (Recommended)

```bash
# Run full pipeline with correlation
python run_integrated_analysis.py --stocks liquid --top 30

# Skip news but include technical correlation
python run_integrated_analysis.py --skip-news
```

### 2. Output Structure

```
STEP 7: Anomaly-Technical Confluence Analysis
================================================================================
🔍 Analyzing confluence between 12 anomalies and technical signals...
✅ Confluence analysis complete
   Total correlations: 12
   Strong confluences: 5
   Actionable signals: 3

🎯 ACTIONABLE SIGNALS (High Confidence)
--------------------------------------------------------------------------------

📈 LUCK - BULLISH
   Confluence: Very Strong (score: 0.86)
   🎯 ACTIONABLE SIGNAL - High confidence trade setup

   Strong BULLISH confluence: Volume Spike (HIGH severity) aligns with
   bullish technical setup. Multiple indicators support upward movement.

   Key Factors:
     • Anomaly: Extreme volume spike: 5.0M vs baseline 1.0M (4.5σ)
     • Technical: BULLISH bias (70% confidence)
     • RSI at 65.0
     • Price above SMA(200)
```

### 3. Programmatic Usage

```python
from psx_anomaly_agent import PSXAnomalyAgent
from psx_technical_agent import PSXTechnicalAgent
from psx_anomaly_technical_correlator import AnomalyTechnicalCorrelator
from psx_price_store import PSXPriceStore

# Setup
price_store = PSXPriceStore()
anomaly_agent = PSXAnomalyAgent(price_store=price_store)
tech_agent = PSXTechnicalAgent(price_store)

# Run analysis
symbols = ['LUCK', 'HBL', 'PSO', 'FFC']
anomalies = anomaly_agent.generate_report(symbols)
technicals = tech_agent.analyze_batch(symbols)

# Correlate
correlator = AnomalyTechnicalCorrelator()
confluences = correlator.correlate_all(anomalies, technicals)

# Filter actionable signals
actionable = [c for c in confluences if c.actionable]

for signal in actionable:
    print(f"{signal.symbol}: {signal.signal_direction}")
    print(f"  Score: {signal.correlation_score:.2f}")
    print(f"  {signal.explanation}")
```

## 🎓 Interpretation Guide

### Actionable Signals
- **Score ≥ 0.80**: Very high confidence
- **Score ≥ 0.65**: High confidence
- **Must have**: Clear direction (BULLISH/BEARISH, not NEUTRAL)
- **Must have**: Either HIGH anomaly severity OR technical confidence ≥ 60%

**Trading Implications**:
- Consider position sizing based on score
- 0.90+ score: Maximum position size
- 0.80-0.89: Standard position
- 0.65-0.79: Reduced position

### Warning Signs
- **CONFLICTING direction**: Anomaly and technical disagree
  - May signal reversal or trap
  - Wait for confirmation
  - Consider divergence strategies

- **Low score + HIGH severity anomaly**: Something unusual happening
  - Market inefficiency?
  - News not yet reflected?
  - Investigate before acting

### Context Matters
Always consider:
1. **Market regime**: Bull/bear/sideways market affects interpretation
2. **Sector context**: Industry-specific factors
3. **News correlation**: Check if news explains the anomaly
4. **Volume profile**: Is volume genuine or manipulation?
5. **Time of day**: Opening hour anomalies may reverse

## 🔬 Technical Details

### Anomaly Direction Mapping

| Anomaly Type | Direction Logic |
|--------------|-----------------|
| Volume Spike | NEUTRAL (could be buying or selling) |
| Price Movement | z > 0 → BULLISH, z < 0 → BEARISH |
| Opening Gap | z > 0 → BULLISH, z < 0 → BEARISH |
| Volatility Spike | NEUTRAL (high volatility goes both ways) |
| Liquidity Change | z > 0 → BULLISH, z < 0 → BEARISH |

### Data Structures

```python
@dataclass
class ConfluenceSignal:
    symbol: str
    date: str
    anomaly: Anomaly                        # Original anomaly
    technical_snapshot: TechnicalSnapshot   # Technical state
    confluence_strength: ConfluenceStrength # Very Strong / Strong / etc.
    correlation_score: float                # 0.0 - 1.0
    signal_direction: str                   # BULLISH / BEARISH / CONFLICTING
    explanation: str                        # Human-readable summary
    key_factors: List[str]                  # Supporting evidence
    actionable: bool                        # High-confidence trade signal?
```

## 📊 Real-World Examples

### Example 1: Lucky Cement (LUCK) - Feb 14, 2026

```
Anomaly:    Volume spike (4.5σ above baseline)
Technical:  Bullish setup
            - Golden cross forming
            - RSI 65 (bullish momentum)
            - Price broke above 200-day MA
Confluence: 0.86 (Very Strong)
Signal:     ACTIONABLE BUY

Result: Strong upward continuation expected
```

### Example 2: Habib Bank (HBL) - Feb 14, 2026

```
Anomaly:    Gap down -3.8% (4.2σ)
Technical:  Bearish breakdown
            - Death cross confirmed
            - Support level broken
            - RSI 35 (weak)
Confluence: 0.92 (Very Strong)
Signal:     ACTIONABLE SELL / AVOID

Result: Further downside likely
```

### Example 3: Pakistan State Oil (PSO) - Feb 14, 2026

```
Anomaly:    Price drop -5.2% (3.2σ)
Technical:  Bullish divergence
            - RSI oversold at 28
            - Potential bounce setup
Confluence: 0.58 (Moderate)
Signal:     ⚠️ CONFLICTING - Caution

Result: Wait for confirmation
        Could be reversal or continuation
```

## ⚙️ Configuration

### Adjusting Thresholds

Edit `psx_anomaly_technical_correlator.py`:

```python
# Make actionable signals more selective
def _is_actionable(...):
    # Require Very Strong confluence only
    if strength != ConfluenceStrength.VERY_STRONG:
        return False

    # Require higher technical confidence
    high_technical = tech_snapshot.confidence >= 0.70  # Was 0.60

    return high_anomaly or high_technical

# Adjust confluence strength boundaries
def _determine_confluence_strength(...):
    if score >= 0.85:  # Was 0.80
        return ConfluenceStrength.VERY_STRONG
    # ... etc
```

### Custom Combination Bonuses

Add your own powerful combinations:

```python
def _get_combination_bonus(...):
    bonus = 0.0

    # Example: Volume spike + MACD bullish crossover
    if atype == AnomalyType.VOLUME_SPIKE:
        if 'MACD' in indicators and 'MACD_Signal' in indicators:
            if indicators['MACD'] > indicators['MACD_Signal']:
                bonus += 0.15

    return bonus
```

## 🧪 Testing

Run the test suite:

```bash
python test_anomaly_technical_correlation.py
```

This demonstrates:
- Bullish confluence scoring
- Bearish confluence scoring
- Conflicting signal detection
- Combined scenario analysis

## 📚 Advanced Topics

### 1. Multi-Timeframe Confluence
Future enhancement: Correlate daily anomalies with weekly technical trends.

### 2. Confluence Backtesting
Track historical accuracy of confluence signals to validate scoring.

### 3. News-Anomaly-Technical Triplet
Combine all three: News explaining anomaly + technical confirmation.

### 4. Machine Learning Enhancement
Train model on historical confluences to predict success rate.

## 🔍 Troubleshooting

### No Confluences Found
- Check if both anomaly detection and technical analysis are enabled
- Lower z-threshold for anomalies: `--z-threshold 2.0`
- Ensure technical confidence isn't too low

### Too Many Low-Quality Signals
- Increase anomaly z-threshold: `--z-threshold 3.0`
- Filter for actionable signals only
- Adjust confluence strength thresholds

### Conflicting Signals Common
- Normal in choppy markets
- May indicate market indecision
- Consider using for contrarian strategies

## 📖 References

- Original Plan: `PLAN_TECHNICAL_ANALYSIS_AGENT.md` (Phase 4)
- Anomaly Agent: `psx_anomaly_agent.py`
- Technical Agent: `psx_technical_agent.py`
- Correlator: `psx_anomaly_technical_correlator.py`

---

**Status**: ✅ **COMPLETE** - Phase 4 requirement fulfilled

**Next Steps**: Add CSV export with correlation columns, implement email alerts for actionable signals.
