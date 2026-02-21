---
name: PSX Portfolio & Risk Dashboard
overview: Create a comprehensive portfolio management and risk management dashboard for the Pakistan Stock Exchange that integrates existing Python analysis agents with a modern Next.js/React frontend. The dashboard will provide real-time portfolio tracking, risk monitoring, trade planning, and market analysis capabilities.
todos: []
isProject: false
---

## Phase 1: Foundation & Simple Dashboard (Week 1-2)

### Step 1: Environment Setup & Data Integration

1. **Set up Prisma client and database connection in Next.js**
  - Configure Prisma client in `src/lib/prisma.ts` (already exists)
  - Create API endpoints for portfolio data:
    - `GET /api/portfolio/holdings` - Get current portfolio positions
    - `GET /api/portfolio/snapshots` - Get portfolio history
    - `GET /api/portfolio/transactions` - Get transaction history
2. **Integrate existing Python agents**
  - Create API endpoints that call existing Python agents:
    - `GET /api/analysis/liquidity` - Call PSXLiquidityScreener
    - `GET /api/analysis/anomalies` - Call PSXAnomalyAgent
    - `GET /api/analysis/risk-metrics` - Call PortfolioRiskManager

### Step 2: Basic Dashboard Layout

1. **Create main dashboard layout in `src/app/dashboard/page.tsx`**
  - Navigation sidebar with sections:
    - 📊 Portfolio Overview
    - 💧 Liquidity Analysis
    - 🔔 Anomaly Detection
    - ⚠️ Risk Management
    - 📈 Performance
  - Responsive 3-column layout for metrics
  - Dark/light theme support (already configured)
2. **Add dashboard components using shadcn/ui**
  - `PortfolioMetrics.tsx` - Key portfolio metrics (total value, P&L, etc.)
  - `RiskSummary.tsx` - Risk metrics and violations
  - `LiquidityTable.tsx` - Liquid stocks table
  - `AnomalyAlert.tsx` - Recent anomalies

### Step 3: Portfolio Overview (Existing Data)

1. **Portfolio Metrics Display**
  - Total portfolio value (from AccountSnapshot)
  - Unrealized P&L (from UserStock and current prices)
  - Number of positions (from UserStock count)
  - Cash balance (from AccountSnapshot)
2. **Position Table**
  - Current holdings with: symbol, quantity, avg cost, current price, P&L
  - Use existing UserStock model data
  - Add position sizing and risk metrics from existing PSXRiskAgent

## Phase 2: Enhanced Market Analysis (Week 3-4)

### Step 4: Integrate Existing Python Agents

1. **Liquidity Screener Module**
  - Adapt existing Streamlit liquidity features to Next.js
  - Use existing PSXLiquidityScreener agent via API
  - Top liquid stocks table with configurable parameters
  - Interactive charts adapted from existing Plotly charts
2. **Anomaly Detection Module**
  - Integrate existing PSXAnomalyAgent
  - Display recent anomalies with severity indicators
  - Color-coded alerts (🔴🟡🟢) as in Streamlit dashboard
  - Export functionality (CSV/JSON) from existing implementation

### Step 5: Risk Management Integration

1. **Risk Dashboard**
  - Use existing RiskSettings model for configuration
  - Display current risk metrics from PSXRiskAgent:
    - Total portfolio risk percentage
    - Diversification score
    - Sector exposure breakdown
    - Risk violations monitoring
2. **Position Sizing Calculator**
  - Use existing PSXRiskAgent calculations
  - Pre-trade risk validation using existing risk rules
  - Kelly Criterion calculator (optional setting available)

## Phase 3: Trade Management (Week 5-6)

### Step 6: Trade Planning Module

1. **Trade Plan Interface**
  - Use existing TradePlan model
  - Entry/exit price planning
  - Risk/Reward ratio calculations
  - Position sizing based on risk settings
  - Trade checklist (using existing checklist field)
2. **Trade Journal Integration**
  - Use existing TradeJournal model
  - Post-trade analysis interface
  - Performance tracking with existing metrics
  - Lessons learned section

## Phase 4: Advanced Features & Optimization (Week 7-8)

### Step 7: Performance Analytics

1. **Portfolio Performance Charts**
  - AccountSnapshot history visualization
  - Performance attribution by sector/stock
  - Risk-adjusted returns using existing calculations
2. **Advanced Reporting**
  - Monthly/Quarterly reviews (existing models)
  - PDF report generation using existing @react-pdf/renderer
  - Export functionality for all data

### Step 8: Real-time Features & Notifications

1. **Live Data Integration**
  - Real-time price updates (extend existing yfinance integration)
  - Live portfolio value updates
  - Real-time risk monitoring alerts
2. **Alert System**
  - Risk limit breach notifications
  - Anomaly alerts for portfolio stocks
  - Price target/stop loss notifications

## Key Implementation Principles

### Reuse Existing Components First:

1. **Database Models**: All portfolio and risk models already exist in Prisma
2. **Python Agents**: 37+ agents available for integration
3. **Calculations**: Risk management logic already implemented
4. **Data Sources**: PSX stock data integration via yfinance

### Technology Stack (Existing):

- **Frontend**: Next.js 16.1.6, TypeScript, React 19, Tailwind CSS 4
- **UI Components**: shadcn/ui (Radix UI) - extensive library available
- **Database**: Prisma + SQLite (already configured)
- **Charts**: Recharts 3.7.0 (already installed)
- **Styling**: Tailwind CSS with themes (already set up)

### Data Flow:

1. **Existing backend**: Prisma + SQLite for persistent data
2. **Python agents**: API endpoints to leverage existing analysis
3. **Real-time data**: yfinance for PSX stock prices
4. **Integration layer**: Next.js API routes as bridge

This plan maximizes the use of existing functionality and provides a clear path from simple to advanced features, ensuring rapid development while leveraging your substantial existing codebase.