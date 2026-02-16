# PSX Portfolio Manager Agent

## Overview

The Portfolio Manager Agent is a rule-based portfolio management system for the Pakistan Stock Exchange (PSX). It generates non-binding trading recommendations by aggregating signals from multiple analysis agents and applying different investment strategies.

## Features

- **Multi-Model Analysis**: Three built-in investment models (Conservative, Balanced, Aggressive)
- **Signal Aggregation**: Combines Technical, Fundamental, Anomaly, and News signals
- **Risk Management**: Applies position limits, cash reserves, and constraint validation
- **Portfolio Tracking**: SQLite-based persistence for positions, transactions, and decisions
- **Audit Trail**: Complete history of all trading decisions and recommendations

## Architecture

### Rule-Based Approach

Unlike the reference LangGraph script, this implementation uses **deterministic rule-based logic** to match the existing codebase architecture:

- **No LLM Integration**: Pure algorithmic decision-making
- **No LangGraph**: Uses simple Python classes and functions
- **Deterministic**: Same inputs always produce same outputs
- **Explainable**: Clear reasoning for every decision

### Files Created

```
psx_portfolio_models.py      (12 KB)  - Data models (@dataclass)
psx_portfolio_store.py       (23 KB)  - SQLite persistence layer
psx_portfolio_utils.py       (13 KB)  - Helper functions
psx_portfolio_manager.py     (19 KB)  - Main agent logic
run_portfolio_analysis.py    (14 KB)  - Standalone orchestration script
demo_portfolio_manager.py    (8 KB)   - Demo with 5 stocks
test_portfolio_manager.py    (8.4 KB) - Unit tests
```

### Database Schema

**Location**: `portfolio_data/portfolio.db`

**Tables**:
- `portfolio_config` - Portfolio configuration and constraints
- `positions` - Current positions (symbol, quantity, cost basis, P&L)
- `transactions` - Transaction history (buy/sell records)
- `portfolio_snapshots` - Portfolio state snapshots
- `trade_decisions` - Trading decisions audit trail

## Investment Models

### Conservative Model
- **Focus**: Fundamentals-driven (50% weight)
- **Buy Threshold**: 70/100
- **Sell Threshold**: 30/100
- **Min Confidence**: 75%
- **Max Position**: 10% per stock
- **Red Flags**: Strong filtering (auto-reject critical flags)
- **Best For**: Risk-averse investors, long-term value investing

### Balanced Model
- **Focus**: Equal fundamentals (40%) and technicals (30%)
- **Buy Threshold**: 65/100
- **Sell Threshold**: 35/100
- **Min Confidence**: 65%
- **Max Position**: 15% per stock
- **Red Flags**: Moderate filtering
- **Best For**: Balanced growth and stability

### Aggressive Model
- **Focus**: Momentum-driven (40% technical weight)
- **Buy Threshold**: 55/100
- **Sell Threshold**: 40/100
- **Min Confidence**: 55%
- **Max Position**: 20% per stock
- **Red Flags**: Light filtering (cap score instead of reject)
- **Best For**: Active traders, momentum strategies

## How It Works

### 1. Signal Aggregation

For each stock, the portfolio manager:

1. **Converts agent outputs to scores (0-100)**:
   - Technical: Maps bias (Bullish/Bearish/Neutral) + confidence → score
   - Fundamental: Uses fundamental_score directly (already 0-100)
   - Anomaly: Inverts severity (high anomaly = low score = concerning)
   - News: Maps sentiment to score (positive = high, negative = low)

2. **Applies model weights**:
   ```
   composite_score = (technical_score × tech_weight) +
                     (fundamental_score × fund_weight) +
                     (anomaly_score × anomaly_weight) +
                     (news_score × news_weight)
   ```

3. **Applies red flag penalties**:
   - CRITICAL red flag → cap score at 30 (or reject)
   - HIGH red flag → reduce score by 40-50%
   - MEDIUM red flag → reduce score by 15-30%

4. **Calculates confidence** based on signal agreement

### 2. Decision Generation

**For stocks without position**:
- If `composite_score >= buy_threshold` AND `confidence >= min_confidence`:
  - Action: **BUY**
  - Quantity: Calculated based on position sizing formula
- Else:
  - Action: **HOLD** (don't enter)

**For stocks with position**:
- If `composite_score <= sell_threshold`:
  - Action: **SELL** (full position)
- Else if `composite_score <= reduce_threshold`:
  - Action: **REDUCE** (sell 50% of position)
- Else:
  - Action: **HOLD** (keep current position)

### 3. Position Sizing

```python
# Calculate available cash (minus reserve)
available_cash = cash - (total_equity × min_cash_reserve_pct / 100)

# Max position value based on % of portfolio
max_position_value = total_equity × (max_position_pct / 100)

# Scale by signal strength (higher score = larger position)
sizing_factor = (composite_score / 100) × confidence

# Target position value
target_value = min(
    max_position_value × sizing_factor,
    available_cash,
    max_single_order_value
)

# Convert to shares (rounded to lot size = 500)
quantity = floor(target_value / current_price / 500) × 500
```

### 4. Constraint Validation

**Checks**:
- ✓ Max positions limit (default: 10)
- ✓ Max position percentage (model-specific)
- ✓ Cash reserve requirement (default: 10%)
- ✓ Minimum lot size (PSX: 500 shares)

**If constraints violated**:
- Decision marked as `violates_constraints = True`
- Added to `excluded_trades` (not `recommended_trades`)
- Violations listed for user review

## Usage

### Option 1: Standalone Portfolio Analysis

Run complete portfolio analysis with all models:

```bash
python run_portfolio_analysis.py --use-liquid-stocks --top-n 20 --initial-cash 1000000
```

**Options**:
```bash
--use-liquid-stocks     # Use liquidity screener (default: True)
--top-n 20             # Number of stocks to analyze
--initial-cash 1000000  # Initial portfolio cash (PKR)
--portfolio-name default
--models all           # conservative, balanced, aggressive, or all
--symbols HBL LUCK OGDC  # Specific symbols (overrides screener)
```

**Output**: Side-by-side comparison of all three models with detailed recommendations.

### Option 2: Integrated Analysis

Add portfolio management to existing integrated analysis:

```bash
python run_integrated_analysis.py \
  --stocks liquid \
  --top 20 \
  --portfolio-manager \
  --portfolio-cash 1000000 \
  --portfolio-models all
```

**New Options**:
```bash
--portfolio-manager        # Enable portfolio management step
--portfolio-cash 1000000   # Initial cash (PKR)
--portfolio-models all     # Models to run
```

This runs the full pipeline: News → Technical → Fundamental → Anomaly → Correlation → **Portfolio Manager**

### Option 3: Demo

Quick demo with 5 stocks (HBL, LUCK, OGDC, ENGRO, PPL):

```bash
python demo_portfolio_manager.py
```

Shows:
- Side-by-side model comparison
- Detailed recommendations with reasoning
- Signal breakdowns for each decision

### Option 4: Python API

```python
from psx_portfolio_manager import PSXPortfolioManager
from psx_portfolio_store import PSXPortfolioStore
from psx_portfolio_models import PortfolioConfig

# Initialize
config = PortfolioConfig(name="my_portfolio", initial_cash=1_000_000.0)
store = PSXPortfolioStore()
manager = PSXPortfolioManager(store, config)

# Run analysis
output = manager.analyze_portfolio(
    model_name="balanced",
    symbols=["HBL", "LUCK", "OGDC"],
    current_prices={"HBL": 175.0, "LUCK": 750.0, "OGDC": 88.0},
    technical_snapshots=technical_snapshots,
    fundamental_scores=fundamental_scores,
    anomalies=[],
    correlations=None
)

# Access results
for decision in output.recommended_trades:
    print(f"{decision.symbol}: {decision.action.value} {decision.quantity} shares")
    print(f"  Score: {decision.composite_score:.0f}/100")
    print(f"  Reasoning: {decision.reasoning}")
```

## Output Format

### Console Report

```
================================================================================
💼 PORTFOLIO ANALYSIS - MULTI-MODEL COMPARISON
================================================================================

📊 Portfolio Status
   Cash:              PKR 1,000,000
   Positions:         0
   Total Equity:      PKR 1,000,000

================================================================================
📈 MODEL COMPARISON
================================================================================

Symbol     Price        Conservative          Balanced              Aggressive
------------------------------------------------------------------------------------------------
HBL        PKR 175.00   BUY 1000 (78)        BUY 1500 (75)         BUY 2000 (72)
LUCK       PKR 750.00   HOLD (62)            HOLD (65)             BUY 500 (68)
OGDC       PKR 88.00    BUY 2000 (72)        BUY 2500 (70)         BUY 3000 (68)

================================================================================
🎯 CONSERVATIVE MODEL RECOMMENDATIONS
================================================================================

1. HBL - BUY 1,000 shares @ PKR 175.00
   Composite Score: 78/100 | Confidence: 85% | Position Size: 12.5%

   Signal Breakdown:
   • Technical:   75/100 (Bullish)
   • Fundamental: 82/100 (BUY)
   • Anomaly:     50/100 (None)
   • News:        80/100

   Reasoning:
   ✓ Strong fundamental score (82/100) with BUY recommendation
   ✓ Technical bullish bias (75/100)
   ✓ Positive news sentiment (80/100)
   ✓ No red flags detected

2. OGDC - BUY 2,000 shares @ PKR 88.00
   [Similar detail...]
```

### Database Queries

View decisions:
```sql
sqlite3 portfolio_data/portfolio.db

-- Recent decisions
SELECT model_name, symbol, action, quantity, composite_score, confidence
FROM trade_decisions
ORDER BY decision_date DESC
LIMIT 10;

-- Recommendations by model
SELECT model_name, COUNT(*) as count
FROM trade_decisions
WHERE action != 'HOLD'
GROUP BY model_name;
```

View portfolio state:
```sql
-- Current positions
SELECT symbol, quantity, average_cost, current_price, unrealized_pl
FROM positions
WHERE portfolio_name = 'default';

-- Transaction history
SELECT symbol, action, quantity, price, timestamp
FROM transactions
WHERE portfolio_name = 'default'
ORDER BY timestamp DESC
LIMIT 20;
```

## Configuration

### Portfolio Config

Customize constraints via `PortfolioConfig`:

```python
config = PortfolioConfig(
    name="aggressive_portfolio",
    initial_cash=2_000_000.0,
    max_position_pct=20.0,      # 20% per stock
    max_positions=15,            # Max 15 stocks
    min_cash_reserve_pct=5.0,    # Keep 5% cash
    max_single_order_value=300_000.0,
    lot_size=500,
    transaction_fee_pct=0.35
)
```

### Custom Models

Create custom investment models:

```python
from psx_portfolio_models import PortfolioModel, ModelType

custom_model = PortfolioModel(
    name="Growth",
    model_type=ModelType.AGGRESSIVE,
    technical_weight=0.35,
    fundamental_weight=0.35,
    anomaly_weight=0.20,
    news_weight=0.10,
    buy_threshold=60.0,
    sell_threshold=35.0,
    reduce_threshold=45.0,
    min_confidence=0.60,
    max_position_pct=18.0,
    description="Growth-focused with equal tech/fund weights"
)
```

## Testing

Run unit tests:

```bash
# Install dependencies first
pip install -r requirements.txt

# Run tests
python test_portfolio_manager.py
```

**Tests**:
- ✓ Portfolio config creation
- ✓ Position market value calculations
- ✓ Portfolio snapshot totals
- ✓ Model weight validation (sum to 1.0)
- ✓ Signal conversion (technical/fundamental/anomaly/news)
- ✓ Confidence calculation
- ✓ Action type enums
- ✓ Trade decision creation

## Comparison with Reference Script

| Feature | Reference Script | This Implementation |
|---------|-----------------|---------------------|
| **Architecture** | LangGraph with AgentState | Simple Python classes |
| **Decision Logic** | LLM-based (call_llm) | Rule-based algorithms |
| **Dependencies** | langchain, OpenAI/Anthropic | None (uses existing agents) |
| **Cost** | LLM API costs per decision | Zero (deterministic) |
| **Consistency** | May vary with LLM | Always deterministic |
| **Execution** | Can execute trades | Recommendations only |
| **State Management** | LangGraph message passing | Direct function calls |
| **Models** | Single portfolio model | Three built-in models |
| **Explainability** | LLM reasoning (may vary) | Explicit reasoning strings |

## Design Decisions

### Why Rule-Based?

1. **Consistency with Codebase**: All existing agents (Technical, Fundamental, Anomaly, News) are rule-based
2. **Determinism**: Portfolio decisions involving real money require predictable, testable logic
3. **No Dependencies**: No need for LangGraph, LLM APIs, or additional infrastructure
4. **Cost**: Zero API costs for production use
5. **Speed**: Instant decisions without API latency

### Why Multiple Models?

Allows users to:
- **Compare strategies** side-by-side
- **Choose risk profile** (conservative vs aggressive)
- **Understand tradeoffs** between different approaches
- **Customize** based on market conditions or preferences

### Why Recommendations Only?

- **Safety**: User reviews and approves all trades
- **Flexibility**: User can adjust quantities, timing, or skip trades
- **Learning**: User sees reasoning and can learn from recommendations
- **Non-binding**: As explicitly requested by user

## Limitations

1. **No Shorting Support**: PSX doesn't allow short selling (excluded from reference script)
2. **No Margin Trading**: Uses simple cash-based portfolio (can be added later)
3. **No Stop Loss Execution**: Recommendations only (no automated stops)
4. **No Backtesting**: Doesn't track hypothetical performance (can be added)
5. **No Optimization**: Uses fixed model weights (not optimized for Sharpe ratio, etc.)

## Future Enhancements

Potential improvements:

- [ ] **Backtesting Module**: Test strategies on historical data
- [ ] **Performance Tracking**: Track actual vs recommended trades
- [ ] **Model Optimization**: Optimize weights for Sharpe ratio, max drawdown, etc.
- [ ] **Broker Integration**: Connect to PSX broker APIs for execution
- [ ] **Risk Analytics**: VaR, CVaR, correlation matrices
- [ ] **Rebalancing**: Automatic portfolio rebalancing logic
- [ ] **Tax Optimization**: CGT-aware trading recommendations
- [ ] **Sector Allocation**: Sector-level constraints and balancing
- [ ] **Custom Alerts**: Notifications for significant signals

## Examples

### Example 1: Conservative Long-Term Portfolio

```bash
python run_portfolio_analysis.py \
  --use-liquid-stocks \
  --top-n 30 \
  --initial-cash 5000000 \
  --models conservative
```

Use case: Long-term investor, low risk tolerance, focus on dividends and fundamentals.

### Example 2: Aggressive Momentum Trading

```bash
python run_portfolio_analysis.py \
  --symbols HBL UBL MCB OGDC PPL PSO LUCK DGKC ENGRO FFC \
  --initial-cash 2000000 \
  --models aggressive
```

Use case: Active trader, high risk tolerance, momentum-focused.

### Example 3: Multi-Model Comparison

```bash
python run_portfolio_analysis.py \
  --use-liquid-stocks \
  --top-n 20 \
  --initial-cash 1000000 \
  --models all
```

Use case: Compare all three strategies to choose best approach for current market.

## Support

For issues, questions, or contributions:

1. **Read the Plan**: `/root/.claude/plans/wise-doodling-puppy.md`
2. **Check Tests**: `python test_portfolio_manager.py`
3. **Run Demo**: `python demo_portfolio_manager.py`
4. **Review Database**: `sqlite3 portfolio_data/portfolio.db`

## License

Same as the parent Investment project.

---

**Note**: This portfolio manager generates non-binding recommendations only. Users are responsible for their own investment decisions. Past performance does not guarantee future results. Trading stocks involves risk of loss.
