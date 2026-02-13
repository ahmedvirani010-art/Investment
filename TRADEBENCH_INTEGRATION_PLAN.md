# PSX Dashboard + TradeBench Integration Plan

## Executive Summary

This document outlines the plan to enhance the existing PSX (Pakistan Stock Exchange) Dashboard by integrating key features from TradeBench, a comprehensive trading journal platform that serves over 80,000 traders. The integration will transform the current portfolio tracking system into a full-featured trading journal with advanced analytics, risk management, and trade planning capabilities.

## Current Application Analysis

### Existing Features
- **Stock Management**: Track PSX stocks with ticker, name, sector, market cap, and prices
- **Transaction Tracking**: Record buy/sell transactions with fees and notes
- **Portfolio Management**: Monitor holdings with average cost, realized gains, and dividends
- **Research Notes**: Rich text editor (TipTap) for documenting research
- **Review System**: Monthly and quarterly performance reviews
- **Tagging System**: Organize stocks and notes with custom tags

### Technology Stack
- **Frontend**: Next.js 16, React 19, TypeScript
- **UI**: Shadcn/ui components, Tailwind CSS, Radix UI
- **Database**: Prisma ORM with SQLite
- **Charts**: Recharts for data visualization
- **Form Management**: React Hook Form with Zod validation

## TradeBench Features to Integrate

Based on research, TradeBench offers the following key features that will enhance our PSX dashboard:

### 1. Trade Planning & Execution
- Pre-trade planning with automatic reward/risk ratio calculations
- Position sizing calculator based on risk parameters
- Customizable pre-trade checklists with automation
- Automatic verification (e.g., volume checks for stocks)
- Support for multiple entry/exit points for both long and short positions

### 2. Risk & Money Management
- Define maximum risk percentage per trade
- Set maximum account commitment per trade
- Total position diversification limits
- Automated position sizing based on account value and risk parameters
- Prevention system for trades that violate risk rules

### 3. Open Trades Dashboard
- Real-time price updates for active positions
- Automatic calculation of unrealized profits/losses
- Advanced charting integration (TradingView-style)
- Multi-entry/exit position tracking
- Long and short position support

### 4. Trading Journal & Analytics
- Permanent journal for closed trades
- Post-trade review system with emotional distance
- Annotated chart attachments via drag-and-drop
- Entry/exit decision documentation
- Filtered performance reports by strategy, source, exit method

### 5. Performance Metrics & Reports
- Profit factor calculations
- Average P&L analysis
- Commission cost tracking
- Average hold time metrics
- Win rate and risk/reward analysis
- Customizable labels for categorization

### 6. Paper Trading & Account Management
- Separate journals for paper trading and live accounts
- Strategy simulation capabilities
- Private trade sharing options
- Public portfolio sharing functionality

## Integration Roadmap

### Phase 1: Database Schema Enhancement

#### New Models to Add

```prisma
model TradePlan {
  id                String   @id @default(cuid())
  stockId           String
  status            String   // PLANNED, ACTIVE, CLOSED, CANCELLED
  direction         String   // LONG or SHORT
  entryPrice        Float
  targetPrice       Float?
  stopLoss          Float
  positionSize      Float?
  riskAmount        Float?
  rewardRiskRatio   Float?
  notes             String?
  checklist         String?  // JSON string for checklist items
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  stock             Stock    @relation(fields: [stockId], references: [id])
  positions         Position[]

  @@index([stockId])
  @@index([status])
}

model Position {
  id                String   @id @default(cuid())
  tradePlanId       String
  type              String   // ENTRY or EXIT
  date              DateTime
  price             Float
  quantity          Float
  fees              Float    @default(0)
  notes             String?
  createdAt         DateTime @default(now())

  tradePlan         TradePlan @relation(fields: [tradePlanId], references: [id])

  @@index([tradePlanId])
}

model RiskSettings {
  id                      String   @id @default(cuid())
  maxRiskPerTrade         Float    // Percentage (e.g., 2.0 for 2%)
  maxAccountRiskPerTrade  Float    // Percentage
  maxPositionSize         Float    // Percentage of account
  accountValue            Float
  createdAt               DateTime @default(now())
  updatedAt               DateTime @updatedAt
}

model TradeJournal {
  id                String   @id @default(cuid())
  tradePlanId       String   @unique
  entryDate         DateTime
  exitDate          DateTime?
  entryPrice        Float
  exitPrice         Float?
  quantity          Float
  realizedPL        Float?
  realizedPLPercent Float?
  holdingPeriod     Int?     // in days
  strategyLabel     String?
  ideaSource        String?
  exitMethod        String?
  entryNotes        String?
  exitNotes         String?
  chartImage        String?  // URL or base64
  emotionalState    String?
  lessonsLearned    String?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  tradePlan         TradePlan @relation(fields: [tradePlanId], references: [id])

  @@index([entryDate])
  @@index([strategyLabel])
}

model AccountSnapshot {
  id            String   @id @default(cuid())
  date          DateTime @unique
  totalValue    Float
  cashBalance   Float
  investedValue Float
  unrealizedPL  Float
  realizedPL    Float
  createdAt     DateTime @default(now())

  @@index([date])
}
```

#### Modify Existing Transaction Model

```prisma
// Add relation to TradePlan (optional for historical data)
model Transaction {
  // ... existing fields
  tradePlanId   String?
  tradePlan     TradePlan? @relation(fields: [tradePlanId], references: [id])
}
```

### Phase 2: Core Trade Planning Features

#### Components to Build

1. **Trade Planner Component** (`/src/components/trading/TradePlanner.tsx`)
   - Entry/target/stop-loss price inputs
   - Automatic reward/risk ratio calculation
   - Position size calculator
   - Risk amount calculator
   - Pre-trade checklist builder
   - Visual representation of trade setup

2. **Risk Settings Manager** (`/src/components/settings/RiskSettings.tsx`)
   - Configure max risk per trade
   - Set account value
   - Define position size limits
   - Risk validation alerts

3. **Position Size Calculator** (`/src/components/trading/PositionSizeCalculator.tsx`)
   - Input: Account value, risk %, entry, stop-loss
   - Output: Recommended position size, risk amount, potential loss

#### API Routes

- `POST /api/trade-plans` - Create new trade plan
- `GET /api/trade-plans` - Get all trade plans (with filters)
- `PATCH /api/trade-plans/[id]` - Update trade plan
- `DELETE /api/trade-plans/[id]` - Delete trade plan
- `POST /api/trade-plans/[id]/validate` - Validate against risk rules
- `GET /api/risk-settings` - Get current risk settings
- `POST /api/risk-settings` - Update risk settings

### Phase 3: Open Positions Dashboard

#### Components to Build

1. **Open Positions Table** (`/src/components/trading/OpenPositionsTable.tsx`)
   - Display all active positions
   - Real-time price updates (polling or WebSocket)
   - Unrealized P&L calculations
   - Color coding for profit/loss
   - Quick actions (add to position, close position)

2. **Position Detail Card** (`/src/components/trading/PositionDetailCard.tsx`)
   - Multiple entries/exits visualization
   - Average entry price calculation
   - Current P&L with percentage
   - Distance to stop-loss and target
   - Integrated chart view

3. **Real-Time Price Service** (`/src/lib/priceService.ts`)
   - Fetch current prices for active positions
   - Cache management
   - Update interval configuration
   - Integration with PSX data sources

#### API Routes

- `GET /api/positions/open` - Get all open positions
- `POST /api/positions/[id]/add-entry` - Add to existing position
- `POST /api/positions/[id]/partial-exit` - Partial position exit
- `POST /api/positions/[id]/close` - Close entire position
- `GET /api/prices/realtime` - Get real-time prices for open positions

### Phase 4: Trading Journal & Post-Trade Analysis

#### Components to Build

1. **Trade Journal List** (`/src/components/journal/TradeJournalList.tsx`)
   - Filterable table of closed trades
   - Sort by date, P&L, strategy, etc.
   - Quick stats summary
   - Export functionality (CSV, PDF)

2. **Trade Review Form** (`/src/components/journal/TradeReviewForm.tsx`)
   - Entry/exit documentation
   - Chart image upload (drag-and-drop)
   - Emotional state tracking
   - Lessons learned section
   - Strategy/source/exit method labels

3. **Chart Annotation Tool** (`/src/components/journal/ChartAnnotation.tsx`)
   - Upload trade screenshots
   - Basic annotation tools (arrows, text, lines)
   - Save annotated charts to journal entry

#### API Routes

- `GET /api/journal/trades` - Get all journal entries (with filters)
- `GET /api/journal/trades/[id]` - Get specific journal entry
- `PATCH /api/journal/trades/[id]` - Update journal entry
- `POST /api/journal/trades/[id]/upload-chart` - Upload chart image
- `GET /api/journal/stats` - Get journal statistics

### Phase 5: Performance Analytics & Reports

#### Components to Build

1. **Performance Dashboard** (`/src/components/analytics/PerformanceDashboard.tsx`)
   - Key metrics cards (win rate, profit factor, avg P&L)
   - Equity curve chart
   - Monthly/quarterly performance table
   - Trade distribution charts

2. **Strategy Analysis** (`/src/components/analytics/StrategyAnalysis.tsx`)
   - Performance by strategy label
   - Comparison charts
   - Best/worst performers
   - Strategy recommendations

3. **Risk Analysis** (`/src/components/analytics/RiskAnalysis.tsx`)
   - Risk/reward distribution
   - Largest wins/losses
   - Drawdown analysis
   - Risk adherence metrics

4. **Custom Report Builder** (`/src/components/analytics/ReportBuilder.tsx`)
   - Date range selector
   - Filter by strategy, stock, labels
   - Customizable metrics
   - Export to PDF using @react-pdf/renderer

#### Calculations & Metrics

```typescript
// Key metrics to implement
interface PerformanceMetrics {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number; // (winningTrades / totalTrades) * 100
  profitFactor: number; // totalWins / totalLosses
  averageWin: number;
  averageLoss: number;
  averagePL: number;
  largestWin: number;
  largestLoss: number;
  averageRR: number; // Average reward/risk ratio
  totalCommissions: number;
  netPL: number;
  netPLPercent: number;
  averageHoldTime: number; // in days
  expectancy: number; // (winRate * avgWin) - (lossRate * avgLoss)
}
```

#### API Routes

- `GET /api/analytics/performance` - Get performance metrics
- `GET /api/analytics/equity-curve` - Get equity curve data
- `GET /api/analytics/strategy-breakdown` - Performance by strategy
- `GET /api/analytics/risk-metrics` - Risk analysis data
- `POST /api/analytics/generate-report` - Generate custom report
- `GET /api/analytics/export` - Export data (CSV, Excel)

### Phase 6: Advanced Features

#### 6.1 Paper Trading Mode

**Implementation:**
- Add `accountType` field to relevant models (PAPER or LIVE)
- Separate database queries based on account type
- UI toggle to switch between paper and live accounts
- Import paper trades to live journal after verification

**Components:**
- `AccountTypeSwitcher.tsx` - Toggle between paper/live
- `PaperTradingBanner.tsx` - Visual indicator when in paper mode

#### 6.2 Automated Checklist System

**Features:**
- Pre-defined checklist templates (momentum, value, breakout, etc.)
- Custom checklist builder
- Automatic validation rules (e.g., volume > 1M shares)
- Prevent trade execution if checklist incomplete

**Components:**
- `ChecklistBuilder.tsx` - Create/edit checklist templates
- `ChecklistValidator.tsx` - Validate checklist items
- `ChecklistTemplate.tsx` - Pre-built templates

#### 6.3 Price Alerts & Notifications

**Features:**
- Price alerts for target/stop-loss levels
- Browser notifications
- Email alerts (optional)
- Daily/weekly summary emails

**Implementation:**
- Background job to check prices
- Web Push API for notifications
- Email service integration (optional)

#### 6.4 Trade Sharing & Social Features

**Features:**
- Share individual trades (with privacy controls)
- Public portfolio view (optional)
- Shareable performance stats
- Private sharing with specific users

**Components:**
- `TradeShareDialog.tsx` - Share trade with controls
- `PublicPortfolioView.tsx` - Public-facing portfolio page
- `PrivacySettings.tsx` - Configure sharing preferences

#### 6.5 Enhanced Charting

**Integration Options:**
1. **TradingView Widget** (Recommended)
   - Embed TradingView lightweight charts
   - Real-time data for PSX stocks
   - Professional charting tools

2. **Custom Chart Component**
   - Use Recharts for basic charting
   - Add technical indicators
   - Drawing tools for annotations

**Components:**
- `TradingViewChart.tsx` - TradingView integration
- `ChartAnnotations.tsx` - Drawing tools overlay

#### 6.6 Mobile Responsiveness

**Enhancements:**
- Responsive tables with horizontal scroll
- Mobile-optimized forms
- Touch-friendly trade planner
- Quick-action buttons for mobile

**Implementation:**
- Use Tailwind responsive classes
- Test on various device sizes
- Optimize performance for mobile

### Phase 7: Data Import & Export

#### Import Features

1. **CSV Import** (`/src/lib/import/csvImport.ts`)
   - Import historical trades from CSV
   - Validate and map columns
   - Preview before import
   - Error handling and reporting

2. **Broker Integration** (Future)
   - API integration with Pakistani brokers
   - Automatic trade sync
   - Real-time portfolio updates

#### Export Features

1. **CSV Export** - Already using xlsx library
2. **PDF Reports** - Using @react-pdf/renderer
3. **Excel Export** - Advanced formatting with xlsx
4. **Tax Report Generator** - Capital gains calculation for tax filing

**Components:**
- `ImportWizard.tsx` - Step-by-step import process
- `ExportDialog.tsx` - Choose export format and options
- `TaxReportGenerator.tsx` - Generate tax reports

### Phase 8: UI/UX Enhancements

#### Navigation Updates

Current structure:
```
- Dashboard (Home)
- Portfolio
- Transactions
- Research Notes
- Reviews
```

Proposed structure:
```
- Dashboard (Overview)
  ├── Portfolio Summary
  ├── Open Positions
  └── Recent Activity

- Trading
  ├── Plan Trade
  ├── Open Positions
  ├── Closed Trades
  └── Trade Journal

- Analytics
  ├── Performance
  ├── Strategy Analysis
  ├── Risk Metrics
  └── Reports

- Research
  ├── Stock Screener
  ├── Research Notes
  └── Watchlist

- Settings
  ├── Risk Settings
  ├── Account Settings
  ├── Checklists
  └── Preferences
```

#### Theme Enhancements

- Maintain existing dark/light mode with next-themes
- Add color-coded profit/loss indicators
- Consistent spacing and typography
- Accessibility improvements (ARIA labels, keyboard navigation)

### Phase 9: Testing & Quality Assurance

#### Testing Strategy

1. **Unit Tests**
   - Calculation functions (P&L, position sizing, metrics)
   - Form validation logic
   - Risk rule validators

2. **Integration Tests**
   - API route testing
   - Database operations
   - Price update service

3. **E2E Tests** (Optional)
   - Critical user flows
   - Trade planning to execution
   - Journal entry creation

#### Performance Optimization

- Database query optimization with proper indexing
- Implement pagination for large datasets
- Cache frequently accessed data
- Optimize bundle size with code splitting

### Phase 10: Deployment & Monitoring

#### Pre-Deployment Checklist

- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Error tracking setup (Sentry or similar)
- [ ] Performance monitoring
- [ ] Backup strategy implemented
- [ ] SSL certificate configured
- [ ] Database backups automated

#### Monitoring & Maintenance

- Set up error tracking and alerts
- Monitor database performance
- Track user engagement metrics
- Regular security updates
- Database backup verification

## Implementation Priorities

### Must-Have (MVP)
1. Trade planning with risk calculation
2. Position tracking with basic P&L
3. Trade journal entries
4. Basic performance metrics
5. Risk settings management

### Should-Have
1. Real-time price updates
2. Multiple entries/exits per position
3. Performance analytics dashboard
4. Custom reports
5. CSV import/export

### Nice-to-Have
1. Paper trading mode
2. Advanced charting with TradingView
3. Trade sharing features
4. Mobile app
5. Broker integrations

## Technical Considerations

### Performance
- Use React Server Components where appropriate
- Implement proper caching strategies
- Optimize database queries with indexes
- Consider Redis for real-time price caching

### Security
- Input validation with Zod schemas
- SQL injection prevention (Prisma handles this)
- XSS prevention (React handles this)
- CSRF protection for API routes
- Authentication/authorization (add if needed)

### Scalability
- SQLite suitable for single-user application
- Consider PostgreSQL for multi-user deployment
- Implement pagination for large datasets
- Background jobs for price updates and calculations

### Data Integrity
- Foreign key constraints
- Transaction rollback on errors
- Regular database backups
- Data validation at API and database levels

## Migration Strategy

### From Current to Enhanced System

1. **Backward Compatibility**
   - Existing Transaction records remain valid
   - Add optional `tradePlanId` to link with new system
   - Migrate historical data to new schema

2. **Data Migration Script**
   - Convert existing transactions to TradePlan + Position records
   - Generate TradeJournal entries for closed positions
   - Calculate historical performance metrics

3. **User Training**
   - In-app tutorials for new features
   - Help documentation
   - Example trade walkthroughs

## Success Metrics

### User Engagement
- Number of planned trades
- Journal entries completion rate
- Report generation frequency
- Feature adoption rates

### Performance Impact
- Page load times < 2 seconds
- Real-time updates latency < 1 second
- API response times < 500ms
- Zero data loss incidents

### Business Value
- Enhanced decision-making through analytics
- Reduced emotional trading through pre-planning
- Improved risk management adherence
- Better learning through journaling

## Conclusion

This integration plan combines the strengths of the existing PSX Dashboard (portfolio tracking, research notes, reviews) with TradeBench's powerful trading journal features (trade planning, risk management, performance analytics). The phased approach allows for incremental development and testing while maintaining the stability of existing features.

The resulting application will be a comprehensive trading platform specifically tailored for PSX traders, providing professional-grade tools previously unavailable in the Pakistani market.

## References

Based on research from:
- [TradeBench Trading Journal Review 2026](https://trading-journals.com/reviews/tradebench)
- [TradeBench Official Website](https://tradebench.com/)
- [Trading Journal Features - TradeBench](https://tradebench.com/trading-journal-features/)
- [How Our Trading Journal Works - TradeBench](https://tradebench.com/how-our-online-trading-journal-works/)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-13
**Author**: Claude AI Assistant
**Session**: claude/research-tradebench-plan-UVmU0
