# Portfolio-Risk Integration System

## Overview

The Portfolio-Risk Integration System is a comprehensive risk management framework for the PSX (Pakistan Stock Exchange) Investment Dashboard. It integrates portfolio management with sophisticated risk analysis to provide:

- **Intelligent Position Sizing**: Calculate optimal position sizes based on risk parameters
- **Real-time Risk Monitoring**: Monitor portfolio risk and generate alerts
- **Trade Validation**: Validate trades against risk rules before execution
- **Portfolio Diversification Analysis**: Assess and improve portfolio diversification
- **Risk-Adjusted Recommendations**: Combine risk and fundamental analysis for trade decisions

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Portfolio Risk Manager                        │
│  (portfolio_risk_integration.py)                                │
│                                                                  │
│  • Load portfolio from Prisma database                          │
│  • Integrate risk + fundamental analysis                        │
│  • Batch evaluate opportunities                                 │
│  • Generate rebalancing recommendations                         │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
    ┌────────▼────────┐           ┌─────────▼──────────┐
    │  PSXRiskAgent   │           │ PSXFundamentalAgent │
    │ (psx_risk_agent.py)         │ (optional)          │
    │                 │           │                     │
    │ • Position sizing          │ • Fundamental score  │
    │ • Risk validation          │ • Red flags          │
    │ • Portfolio risk           │ • Recommendations    │
    │ • Kelly Criterion          │                      │
    └─────────────────┘           └─────────────────────┘
```

## Components

### 1. PSXRiskAgent (`psx_risk_agent.py`)

Core risk management engine providing:

#### Features
- **Position Sizing**: Calculate recommended position sizes based on risk parameters
- **Risk Validation**: Validate trades against portfolio risk rules
- **Portfolio Analysis**: Comprehensive portfolio risk metrics
- **Kelly Criterion**: Optional Kelly Criterion position sizing
- **Diversification Monitoring**: Track sector exposure and concentration

#### Key Classes

**RiskSettings**
```python
RiskSettings(
    account_value=1_000_000,          # Total account value
    max_risk_per_trade_pct=2.0,       # Max 2% risk per trade
    max_position_size_pct=10.0,       # Max 10% per position
    max_total_risk_pct=6.0,           # Max 6% total portfolio risk
    max_sector_exposure_pct=30.0,     # Max 30% per sector
    min_positions=5,                   # Min 5 positions for diversification
    min_reward_risk_ratio=2.0          # Min 2:1 reward/risk
)
```

**TradeRiskAnalysis**
- Comprehensive risk analysis for potential trades
- Position sizing recommendations
- Risk/reward calculations
- Validation against risk rules

**PortfolioRiskMetrics**
- Total portfolio risk percentage
- Diversification score (0-100)
- Concentration score (0-100)
- Sector exposure breakdown
- Risk violations and warnings

#### Example Usage

```python
from psx_risk_agent import PSXRiskAgent, create_default_risk_settings, TradeDirection

# Create risk agent
risk_settings = create_default_risk_settings(account_value=1_000_000)
agent = PSXRiskAgent(risk_settings)

# Calculate position size for a trade
trade = agent.calculate_position_size(
    symbol="ENGRO",
    entry_price=300.0,
    stop_loss=285.0,  # 5% stop loss
    target_price=345.0,  # 15% target
    direction=TradeDirection.LONG
)

print(f"Recommended Shares: {trade.recommended_shares}")
print(f"Risk Amount: PKR {trade.risk_amount:,.0f}")
print(f"Reward/Risk Ratio: {trade.reward_risk_ratio:.2f}:1")
```

### 2. Portfolio Risk Integration (`portfolio_risk_integration.py`)

High-level integration layer connecting portfolio management with risk analysis.

#### Features
- **Prisma Integration**: Load portfolio from Prisma database
- **Unified Trade Evaluation**: Combine risk + fundamental analysis
- **Batch Opportunity Evaluation**: Rank multiple opportunities
- **Real-time Monitoring**: Monitor portfolio risk with live prices
- **Rebalancing Recommendations**: Suggest portfolio adjustments

#### Key Classes

**PortfolioRiskManager**
```python
from portfolio_risk_integration import create_portfolio_manager_with_defaults

# Create manager with risk profile
manager = create_portfolio_manager_with_defaults(
    account_value=2_000_000,
    risk_profile="moderate"  # conservative, moderate, or aggressive
)

# Load portfolio from Prisma data
positions = manager.load_portfolio_from_prisma_data(
    user_stocks=user_stocks_from_db,
    stock_info=stock_info_dict,
    current_prices=current_prices_dict
)

# Evaluate a trade
recommendation = manager.evaluate_trade_with_risk_and_fundamentals(
    symbol="OGDC",
    entry_price=100.0,
    stop_loss=95.0,
    target_price=115.0
)

print(f"Recommendation: {recommendation.recommendation}")
print(f"Combined Score: {recommendation.combined_score:.1f}/100")
```

**EnhancedTradeRecommendation**
- Combined risk + fundamental analysis
- BUY/HOLD/SELL/REJECT recommendation
- Confidence level (high/medium/low)
- Approval/rejection reasons
- Priority ranking

### 3. Database Schema Updates (`prisma/schema.prisma`)

New models for risk management and trade planning:

#### RiskSettings
```prisma
model RiskSettings {
  id                      String   @id @default(cuid())
  accountValue            Float
  maxRiskPerTradePct      Float    @default(2.0)
  maxPositionSizePct      Float    @default(10.0)
  maxTotalRiskPct         Float    @default(6.0)
  // ... more fields
}
```

#### TradePlan
```prisma
model TradePlan {
  id                String   @id @default(cuid())
  stockId           String
  status            String   // PLANNED, ACTIVE, CLOSED, CANCELLED
  direction         String   // LONG or SHORT
  entryPrice        Float
  stopLoss          Float
  targetPrice       Float?
  positionSize      Float?
  riskAmount        Float?
  // ... relations and more fields
}
```

#### Other Models
- **Position**: Track multi-entry/exit positions
- **TradeJournal**: Post-trade analysis and journaling
- **AccountSnapshot**: Daily portfolio value tracking

## Usage Examples

### Basic Position Sizing

```python
from psx_risk_agent import PSXRiskAgent, create_default_risk_settings

# Setup
agent = PSXRiskAgent(create_default_risk_settings(1_000_000))

# Calculate position size
trade = agent.calculate_position_size(
    symbol="HBL",
    entry_price=150.0,
    stop_loss=145.0,
    target_price=165.0
)

if trade.is_valid:
    print(f"Buy {trade.recommended_shares} shares at PKR {trade.entry_price}")
else:
    print(f"Trade rejected: {trade.violations}")
```

### Portfolio Risk Analysis

```python
from psx_risk_agent import PSXRiskAgent, PositionRisk

# Create positions
portfolio = [
    PositionRisk(
        symbol="ENGRO",
        quantity=1000,
        entry_price=300.0,
        current_price=315.0,
        current_value=315000,
        stop_loss=285.0,
        risk_amount=15000,
        sector="Chemicals"
    ),
    # ... more positions
]

# Analyze
agent = PSXRiskAgent(create_default_risk_settings(2_000_000))
metrics = agent.analyze_portfolio_risk(portfolio)

print(f"Total Risk: {metrics.total_portfolio_risk_pct:.2f}%")
print(f"Diversification: {metrics.diversification_score:.1f}/100")
print(f"Risk Level: {metrics.risk_level.value}")
```

### Integrated Trade Evaluation

```python
from portfolio_risk_integration import create_portfolio_manager_with_defaults

# Create manager
manager = create_portfolio_manager_with_defaults(2_000_000, "moderate")

# Load existing portfolio
positions = manager.load_portfolio_from_prisma_data(
    user_stocks, stock_info, current_prices
)

# Evaluate new opportunity
rec = manager.evaluate_trade_with_risk_and_fundamentals(
    symbol="PSO",
    entry_price=200.0,
    stop_loss=195.0,
    target_price=220.0
)

if rec.recommendation == "BUY":
    print(f"✓ Approved: {rec.approval_reasons}")
elif rec.recommendation == "REJECT":
    print(f"✗ Rejected: {rec.rejection_reasons}")
```

### Batch Opportunity Evaluation

```python
opportunities = [
    {'symbol': 'ENGRO', 'entry_price': 300, 'stop_loss': 285, 'target_price': 345},
    {'symbol': 'HBL', 'entry_price': 150, 'stop_loss': 145, 'target_price': 165},
    {'symbol': 'OGDC', 'entry_price': 100, 'stop_loss': 95, 'target_price': 115},
]

recommendations = manager.batch_evaluate_opportunities(opportunities, max_recommendations=3)

for rec in recommendations:
    print(f"{rec.priority_rank}. {rec.symbol}: {rec.recommendation} (Score: {rec.combined_score:.1f})")
```

### Real-time Risk Monitoring

```python
# Monitor with current prices
current_prices = {
    'ENGRO': 315.0,
    'HBL': 155.0,
    'PSO': 205.0
}

metrics, alerts = manager.monitor_portfolio_risk_realtime(current_prices)

for alert in alerts:
    print(alert)
```

## Risk Profiles

### Conservative
- Max risk per trade: 1.0%
- Max position size: 8.0%
- Max total risk: 3.0%
- Minimum 7 positions
- Ideal for capital preservation

### Moderate (Default)
- Max risk per trade: 2.0%
- Max position size: 10.0%
- Max total risk: 6.0%
- Minimum 5 positions
- Balanced risk/reward

### Aggressive
- Max risk per trade: 5.0%
- Max position size: 20.0%
- Max total risk: 15.0%
- Minimum 3 positions
- Higher risk tolerance

## Risk Metrics Explained

### Diversification Score (0-100)
- **90-100**: Excellent diversification
- **70-89**: Good diversification
- **50-69**: Moderate concentration
- **<50**: High concentration risk

### Concentration Score (0-100)
- Inverse of diversification
- Calculated using Herfindahl-Hirschman Index
- Lower is better

### Portfolio Risk Level
- **LOW**: <60% of max total risk
- **MODERATE**: 60-80% of max total risk
- **HIGH**: 80-100% of max total risk
- **CRITICAL**: >100% or multiple violations

## Integration with Next.js Frontend

### API Route Example

```typescript
// /src/app/api/risk/calculate-position/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: NextRequest) {
  const { symbol, entryPrice, stopLoss, targetPrice } = await request.json();

  // Call Python risk agent
  const command = `python -c "
from psx_risk_agent import PSXRiskAgent, create_default_risk_settings
agent = PSXRiskAgent(create_default_risk_settings(1000000))
trade = agent.calculate_position_size('${symbol}', ${entryPrice}, ${stopLoss}, ${targetPrice})
print(trade.recommended_shares, trade.risk_amount, trade.reward_risk_ratio)
"`;

  const { stdout } = await execAsync(command);
  const [shares, risk, ratio] = stdout.trim().split(' ');

  return NextResponse.json({
    recommendedShares: parseInt(shares),
    riskAmount: parseFloat(risk),
    rewardRiskRatio: parseFloat(ratio)
  });
}
```

## Testing

### Run Unit Tests

```bash
# Test risk agent
python psx_risk_agent.py

# Test integration module
python portfolio_risk_integration.py

# Run comprehensive demos
python demo_portfolio_risk_integration.py
```

### Demo Script

The `demo_portfolio_risk_integration.py` script includes 6 comprehensive demos:
1. Basic Position Sizing
2. Portfolio Risk Analysis
3. Trade Validation
4. Integrated Manager
5. Batch Evaluation
6. Risk Report Generation

## Migration Guide

### Database Migration

```bash
# Generate migration
npx prisma migrate dev --name add_risk_management

# Apply migration
npx prisma migrate deploy

# Regenerate client
npx prisma generate
```

### Existing Portfolio Data

The system automatically converts existing UserStock data:

```python
# No changes needed to existing data
# Integration handles conversion automatically
positions = manager.load_portfolio_from_prisma_data(
    user_stocks=existing_user_stocks,
    stock_info=stock_info,
    current_prices=prices
)
```

## Performance Considerations

- **Caching**: Portfolio metrics cached for 5 minutes
- **Batch Processing**: Use batch evaluation for multiple opportunities
- **Database Queries**: Optimized with proper indexes
- **Real-time Updates**: Configurable update intervals

## Best Practices

1. **Always set stop losses**: Risk agent requires stop loss for all trades
2. **Monitor portfolio risk daily**: Use real-time monitoring
3. **Respect risk limits**: Don't override auto-reject violations
4. **Diversify across sectors**: Stay within sector exposure limits
5. **Review risk settings regularly**: Adjust based on market conditions
6. **Use conservative settings initially**: Gradually increase as confidence grows
7. **Document trade decisions**: Utilize TradeJournal for post-trade analysis

## Future Enhancements

- [ ] Machine learning for optimal position sizing
- [ ] Correlation analysis between positions
- [ ] Monte Carlo simulation for portfolio risk
- [ ] Advanced Kelly Criterion with win rate estimation
- [ ] Real-time price alerts and stop-loss triggers
- [ ] Risk-adjusted performance metrics (Sharpe, Sortino)
- [ ] Integration with broker APIs for auto-execution
- [ ] Mobile notifications for risk alerts

## Support

For issues or questions:
- Check demo scripts for examples
- Review code documentation
- Refer to TRADEBENCH_INTEGRATION_PLAN.md for roadmap
- See PSX_ANOMALY_DETECTION.md for related features

## License

Part of the PSX Investment Dashboard project.

---

**Version**: 1.0
**Last Updated**: 2026-02-16
**Status**: Production Ready
