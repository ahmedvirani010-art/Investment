"""
PSX Valuation Agent
Production-ready valuation analysis for Pakistan Stock Exchange

Implements four complementary valuation methodologies:
1. DCF (Discounted Cash Flow) - Multi-stage growth model with WACC
2. Owner Earnings - Buffett-style economic profit valuation
3. EV/EBITDA - Market multiples approach with comparable companies
4. Residual Income Model - Edwards-Bell-Ohlson framework

Key Features:
- Structured dataclasses for all outputs
- SQLite storage for valuation history
- Data quality validation with warnings
- Beta estimation from historical returns
- WACC calculation
- Growth rate estimation from historical data
- Weighted aggregation with confidence scoring
- Comprehensive error handling
"""

import sqlite3
import statistics
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ==============================================================================
# ENUMS
# ==============================================================================

class ValuationSignal(Enum):
    """Valuation signal type"""
    BULLISH = "Bullish"      # Undervalued
    BEARISH = "Bearish"      # Overvalued
    NEUTRAL = "Neutral"      # Fairly valued


class ValuationMethod(Enum):
    """Valuation method identifier"""
    DCF = "DCF"
    OWNER_EARNINGS = "Owner Earnings"
    EV_EBITDA = "EV/EBITDA"
    RESIDUAL_INCOME = "Residual Income"


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class ValuationConfig:
    """Configuration for PSX valuation models

    All parameters are calibrated for Pakistan market conditions.
    """

    # Pakistan market parameters
    risk_free_rate: float = 0.13          # 13% Pakistan T-bills
    market_risk_premium: float = 0.08     # 8% emerging market premium
    corporate_tax_rate: float = 0.29      # 29% Pakistan corporate tax
    terminal_growth_rate: float = 0.03    # 3% long-term GDP growth

    # Discount rates
    default_discount_rate: float = 0.15   # 15% base discount rate
    required_return: float = 0.18         # 18% required return for owner earnings

    # Growth assumptions
    default_growth_rate: float = 0.08     # 8% default growth (PSX average)
    max_growth_cap: float = 0.30          # 30% maximum growth rate

    # WACC parameters
    default_beta: float = 1.2             # PSX market beta (higher volatility)
    wacc_floor: float = 0.10              # 10% minimum WACC
    wacc_ceiling: float = 0.25            # 25% maximum WACC

    # Safety margins
    owner_earnings_margin: float = 0.25   # 25% margin of safety
    residual_income_margin: float = 0.20  # 20% margin of safety

    # Model weights (must sum to 1.0)
    dcf_weight: float = 0.35
    owner_earnings_weight: float = 0.35
    ev_ebitda_weight: float = 0.20
    residual_income_weight: float = 0.10

    # Signal thresholds
    bullish_threshold: float = 0.20       # 20% undervalued = bullish
    bearish_threshold: float = -0.20      # 20% overvalued = bearish

    # Projection periods
    forecast_years: int = 5
    dcf_high_growth_years: int = 3
    dcf_transition_years: int = 7

    # Beta bounds
    min_beta: float = 0.6
    max_beta: float = 2.5

    # Sector multiples (PSX benchmark)
    sector_multiples: Dict[str, float] = field(default_factory=lambda: {
        'Banks': 6.5,
        'Cement': 8.0,
        'Oil & Gas': 7.5,
        'Fertilizer': 7.0,
        'Textile': 5.5,
        'Power': 6.0,
        'Food': 9.0,
        'Chemicals': 8.5,
        'Default': 7.5
    })

    def __post_init__(self):
        """Validate configuration"""
        total_weight = (
            self.dcf_weight + self.owner_earnings_weight +
            self.ev_ebitda_weight + self.residual_income_weight
        )
        if not 0.99 <= total_weight <= 1.01:
            raise ValueError(f"Model weights must sum to 1.0, got {total_weight}")


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class FinancialData:
    """Financial data extracted from yfinance"""
    symbol: str
    date: str

    # Market data
    current_price: float
    market_cap: float
    enterprise_value: float
    beta: Optional[float] = None

    # Income statement
    revenue: Optional[float] = None
    operating_income: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None

    # Cash flow
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    free_cash_flow: Optional[float] = None

    # Balance sheet
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    book_value: Optional[float] = None
    working_capital: Optional[float] = None

    # Calculated metrics
    depreciation: Optional[float] = None
    interest_expense: Optional[float] = None

    # Growth rates (from historical comparison)
    revenue_growth: Optional[float] = None
    fcf_growth: Optional[float] = None
    earnings_growth: Optional[float] = None

    # Ratios
    debt_to_equity: Optional[float] = None
    price_to_book: Optional[float] = None
    ev_to_ebitda: Optional[float] = None


@dataclass
class MethodValuation:
    """Valuation result from a single method"""
    method: ValuationMethod
    intrinsic_value: float
    current_market_cap: float
    valuation_gap: float          # (intrinsic - market) / market
    signal: ValuationSignal
    confidence: float             # 0.0 to 1.0
    details: Dict[str, any] = field(default_factory=dict)


@dataclass
class ValuationSnapshot:
    """Complete valuation snapshot for one stock"""
    symbol: str
    date: str
    current_price: float
    market_cap: float

    # Individual method results
    valuations: List[MethodValuation] = field(default_factory=list)

    # Aggregated results
    weighted_intrinsic_value: float = 0.0
    weighted_valuation_gap: float = 0.0
    overall_signal: ValuationSignal = ValuationSignal.NEUTRAL
    overall_confidence: float = 0.0

    # Supporting data
    wacc: Optional[float] = None
    beta: Optional[float] = None
    growth_rate: Optional[float] = None

    # Data quality
    data_quality_score: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ==============================================================================
# MAIN AGENT CLASS
# ==============================================================================

class PSXValuationAgent:
    """
    Valuation agent for Pakistan Stock Exchange

    Performs comprehensive fundamental analysis using multiple valuation
    methodologies with PSX-specific market parameters.
    """

    def __init__(self, config: Optional[ValuationConfig] = None,
                 db_path: str = "price_data/valuations.db"):
        """
        Initialize valuation agent

        Args:
            config: Valuation configuration (uses defaults if None)
            db_path: Path to SQLite database for storing valuations
        """
        self.config = config or ValuationConfig()
        self.db_path = db_path

        # Create directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database tables for valuation history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main valuations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS valuations (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    market_cap REAL NOT NULL,
                    intrinsic_value REAL NOT NULL,
                    valuation_gap REAL NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    wacc REAL,
                    beta REAL,
                    growth_rate REAL,
                    data_quality_score REAL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, date)
                )
            ''')

            # Method-specific valuations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS method_valuations (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    method TEXT NOT NULL,
                    intrinsic_value REAL NOT NULL,
                    valuation_gap REAL NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    details TEXT,
                    PRIMARY KEY (symbol, date, method)
                )
            ''')

            # Financial data snapshots
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS financial_snapshots (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    revenue REAL,
                    ebitda REAL,
                    net_income REAL,
                    free_cash_flow REAL,
                    total_debt REAL,
                    cash REAL,
                    book_value REAL,
                    PRIMARY KEY (symbol, date)
                )
            ''')

            # Indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_valuations_symbol
                ON valuations(symbol, date DESC)
            ''')

            conn.commit()

    def analyze_symbol(self, symbol: str, sector: Optional[str] = None) -> ValuationSnapshot:
        """
        Perform complete valuation analysis for one stock

        Args:
            symbol: Stock symbol (without .KA suffix)
            sector: Optional sector for EV/EBITDA multiples

        Returns:
            ValuationSnapshot with all valuation methods and aggregated results
        """
        print(f"\n{'='*80}")
        print(f"Valuation Analysis: {symbol}")
        print('='*80)

        # Fetch financial data
        print("Fetching financial data from yfinance...")
        financial_data = self._fetch_financial_data(symbol)

        if financial_data is None:
            print(f"Error: Unable to fetch data for {symbol}")
            return self._empty_snapshot(symbol)

        # Validate data quality
        print("Validating data quality...")
        is_valid, warnings = self._validate_financial_data(financial_data)

        if not is_valid:
            print(f"Error: Data quality check failed ({len(warnings)} critical issues)")
            for warning in warnings:
                print(f"  - {warning}")
            snapshot = self._empty_snapshot(symbol)
            snapshot.warnings = warnings
            return snapshot

        # Calculate WACC
        print("Calculating WACC...")
        wacc = self._calculate_wacc(financial_data)
        print(f"  WACC: {wacc:.2%}")

        # Estimate growth rate
        print("Estimating growth rate...")
        growth_rate = self._estimate_growth_rate(financial_data)
        print(f"  Growth rate: {growth_rate:.2%}")

        # Run all valuation methods
        valuations = []

        print("\nRunning valuation methods:")

        # 1. DCF
        print("  1. DCF valuation...")
        dcf_result = self._calculate_dcf(financial_data, wacc, growth_rate)
        if dcf_result:
            valuations.append(dcf_result)
            print(f"     Value: PKR {dcf_result.intrinsic_value:,.0f} (Gap: {dcf_result.valuation_gap:.1%})")

        # 2. Owner Earnings
        print("  2. Owner Earnings valuation...")
        oe_result = self._calculate_owner_earnings(financial_data, growth_rate)
        if oe_result:
            valuations.append(oe_result)
            print(f"     Value: PKR {oe_result.intrinsic_value:,.0f} (Gap: {oe_result.valuation_gap:.1%})")

        # 3. EV/EBITDA
        print("  3. EV/EBITDA valuation...")
        ev_result = self._calculate_ev_ebitda(financial_data, sector)
        if ev_result:
            valuations.append(ev_result)
            print(f"     Value: PKR {ev_result.intrinsic_value:,.0f} (Gap: {ev_result.valuation_gap:.1%})")

        # 4. Residual Income
        print("  4. Residual Income valuation...")
        ri_result = self._calculate_residual_income(financial_data, growth_rate)
        if ri_result:
            valuations.append(ri_result)
            print(f"     Value: PKR {ri_result.intrinsic_value:,.0f} (Gap: {ri_result.valuation_gap:.1%})")

        if not valuations:
            print("Error: All valuation methods failed")
            return self._empty_snapshot(symbol)

        # Aggregate valuations
        print("\nAggregating results...")
        weighted_value, weighted_gap, overall_signal, confidence = self._aggregate_valuations(valuations)

        # Calculate data quality score
        data_quality = self._calculate_data_quality_score(financial_data, warnings)

        # Create snapshot
        snapshot = ValuationSnapshot(
            symbol=symbol,
            date=financial_data.date,
            current_price=financial_data.current_price,
            market_cap=financial_data.market_cap,
            valuations=valuations,
            weighted_intrinsic_value=weighted_value,
            weighted_valuation_gap=weighted_gap,
            overall_signal=overall_signal,
            overall_confidence=confidence,
            wacc=wacc,
            beta=financial_data.beta,
            growth_rate=growth_rate,
            data_quality_score=data_quality,
            warnings=warnings
        )

        # Store in database
        self._store_valuation(snapshot)

        # Print summary
        self._print_summary(snapshot)

        return snapshot

    # ==========================================================================
    # DATA FETCHING AND VALIDATION
    # ==========================================================================

    def _fetch_financial_data(self, symbol: str) -> Optional[FinancialData]:
        """
        Fetch financial data from yfinance

        Args:
            symbol: Stock symbol

        Returns:
            FinancialData object or None if fetch fails
        """
        try:
            ticker_symbol = f"{symbol}.KA"
            ticker = yf.Ticker(ticker_symbol)

            # Get current info
            info = ticker.info

            # Get financial statements
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow

            # Get historical prices for beta calculation
            hist = ticker.history(period='2y')

            # Extract current price and market cap
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price is None and not hist.empty:
                current_price = hist['Close'].iloc[-1]

            market_cap = info.get('marketCap')
            if market_cap is None and current_price:
                shares = info.get('sharesOutstanding')
                if shares:
                    market_cap = current_price * shares

            if not current_price or not market_cap:
                return None

            # Calculate beta from historical returns
            beta = self._estimate_beta(ticker_symbol, hist)

            # Extract financial data (most recent period)
            data = FinancialData(
                symbol=symbol,
                date=datetime.now().strftime('%Y-%m-%d'),
                current_price=float(current_price),
                market_cap=float(market_cap),
                enterprise_value=float(info.get('enterpriseValue', market_cap)),
                beta=beta
            )

            # Income statement items
            if not income_stmt.empty:
                latest_income = income_stmt.iloc[:, 0]  # Most recent column
                data.revenue = self._safe_extract(latest_income, ['Total Revenue', 'Revenue'])
                data.operating_income = self._safe_extract(latest_income, ['Operating Income', 'EBIT'])
                data.ebit = self._safe_extract(latest_income, ['EBIT', 'Operating Income'])
                data.ebitda = self._safe_extract(latest_income, ['EBITDA', 'Normalized EBITDA'])
                data.net_income = self._safe_extract(latest_income, ['Net Income', 'Net Income Common Stockholders'])
                data.interest_expense = self._safe_extract(latest_income, ['Interest Expense', 'Interest Expense Non Operating'])

                # Calculate depreciation if not available
                if data.ebitda and data.ebit:
                    data.depreciation = data.ebitda - data.ebit

            # Cash flow items
            if not cash_flow.empty:
                latest_cf = cash_flow.iloc[:, 0]
                data.operating_cash_flow = self._safe_extract(latest_cf, ['Operating Cash Flow', 'Total Cash From Operating Activities'])
                data.capex = abs(self._safe_extract(latest_cf, ['Capital Expenditure', 'Capital Expenditures']) or 0)
                data.free_cash_flow = self._safe_extract(latest_cf, ['Free Cash Flow'])

                # Calculate FCF if not available
                if data.free_cash_flow is None and data.operating_cash_flow and data.capex:
                    data.free_cash_flow = data.operating_cash_flow - data.capex

            # Balance sheet items
            if not balance_sheet.empty:
                latest_bs = balance_sheet.iloc[:, 0]
                data.total_assets = self._safe_extract(latest_bs, ['Total Assets'])
                data.total_debt = self._safe_extract(latest_bs, ['Total Debt', 'Long Term Debt'])
                data.cash = self._safe_extract(latest_bs, ['Cash', 'Cash And Cash Equivalents'])
                data.book_value = self._safe_extract(latest_bs, ['Stockholders Equity', 'Total Equity Gross Minority Interest'])
                data.working_capital = self._safe_extract(latest_bs, ['Working Capital'])

            # Calculate growth rates from historical data
            if not income_stmt.empty and income_stmt.shape[1] >= 2:
                prev_revenue = self._safe_extract(income_stmt.iloc[:, 1], ['Total Revenue', 'Revenue'])
                if data.revenue and prev_revenue and prev_revenue > 0:
                    data.revenue_growth = (data.revenue - prev_revenue) / prev_revenue

                prev_income = self._safe_extract(income_stmt.iloc[:, 1], ['Net Income'])
                if data.net_income and prev_income and prev_income > 0:
                    data.earnings_growth = (data.net_income - prev_income) / prev_income

            if not cash_flow.empty and cash_flow.shape[1] >= 2:
                prev_fcf = self._safe_extract(cash_flow.iloc[:, 1], ['Free Cash Flow'])
                if data.free_cash_flow and prev_fcf and prev_fcf > 0:
                    data.fcf_growth = (data.free_cash_flow - prev_fcf) / prev_fcf

            # Calculate ratios
            if data.total_debt and data.book_value and data.book_value > 0:
                data.debt_to_equity = data.total_debt / data.book_value

            if data.book_value and data.book_value > 0:
                data.price_to_book = data.market_cap / data.book_value

            if data.ebitda and data.ebitda > 0:
                data.ev_to_ebitda = data.enterprise_value / data.ebitda

            return data

        except Exception as e:
            print(f"  Error fetching data: {str(e)}")
            return None

    def _safe_extract(self, series: pd.Series, keys: List[str]) -> Optional[float]:
        """Safely extract value from pandas Series trying multiple keys"""
        for key in keys:
            if key in series.index:
                val = series[key]
                if pd.notna(val):
                    return float(val)
        return None

    def _validate_financial_data(self, data: FinancialData) -> Tuple[bool, List[str]]:
        """
        Validate financial data quality

        Args:
            data: FinancialData object

        Returns:
            (is_valid, warnings) tuple
        """
        warnings = []

        # Check critical fields
        if data.market_cap <= 0:
            warnings.append("Invalid market cap")

        if data.enterprise_value <= 0:
            warnings.append("Invalid enterprise value")

        # Check for key financial metrics
        if data.revenue is None or data.revenue <= 0:
            warnings.append("Missing or invalid revenue")

        if data.net_income is None:
            warnings.append("Missing net income")

        if data.free_cash_flow is None:
            warnings.append("Missing free cash flow data")

        if data.ebitda is None:
            warnings.append("Missing EBITDA data")

        if data.book_value is None or data.book_value <= 0:
            warnings.append("Missing or invalid book value")

        # Check for outlier growth rates
        if data.revenue_growth and abs(data.revenue_growth) > 1.0:
            warnings.append(f"Extreme revenue growth: {data.revenue_growth:.1%}")

        if data.earnings_growth and abs(data.earnings_growth) > 1.5:
            warnings.append(f"Extreme earnings growth: {data.earnings_growth:.1%}")

        # Check FCF quality
        if data.free_cash_flow and data.free_cash_flow < 0:
            warnings.append("Negative free cash flow")

        # Check balance sheet health
        if data.book_value and data.book_value < 0:
            warnings.append("Negative book value (balance sheet issues)")

        if data.debt_to_equity and data.debt_to_equity > 2.0:
            warnings.append(f"High leverage: D/E = {data.debt_to_equity:.2f}")

        # Critical: more than 3 warnings = failed validation
        is_valid = len(warnings) < 4

        return is_valid, warnings

    def _calculate_data_quality_score(self, data: FinancialData,
                                     warnings: List[str]) -> float:
        """
        Calculate data quality score (0.0 to 1.0)

        Args:
            data: FinancialData object
            warnings: List of validation warnings

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0

        # Penalize for warnings
        score -= len(warnings) * 0.1

        # Bonus for complete data
        completeness = 0
        total_fields = 10

        if data.revenue: completeness += 1
        if data.net_income: completeness += 1
        if data.free_cash_flow: completeness += 1
        if data.ebitda: completeness += 1
        if data.book_value: completeness += 1
        if data.operating_cash_flow: completeness += 1
        if data.total_debt is not None: completeness += 1
        if data.cash: completeness += 1
        if data.revenue_growth is not None: completeness += 1
        if data.beta: completeness += 1

        completeness_bonus = (completeness / total_fields) * 0.3
        score += completeness_bonus

        return max(0.0, min(1.0, score))

    # ==========================================================================
    # BETA AND WACC CALCULATION
    # ==========================================================================

    def _estimate_beta(self, symbol: str, hist: pd.DataFrame,
                      market_symbol: str = '^KSE100') -> Optional[float]:
        """
        Estimate beta from historical returns

        Args:
            symbol: Stock symbol
            hist: Historical price data
            market_symbol: Market index symbol (KSE-100 for PSX)

        Returns:
            Estimated beta or None
        """
        try:
            if hist.empty or len(hist) < 60:  # Need at least 60 days
                return self.config.default_beta

            # Get market index data
            market = yf.Ticker(market_symbol)
            market_hist = market.history(period='2y')

            if market_hist.empty:
                return self.config.default_beta

            # Calculate returns
            stock_returns = hist['Close'].pct_change().dropna()
            market_returns = market_hist['Close'].pct_change().dropna()

            # Align dates
            common_dates = stock_returns.index.intersection(market_returns.index)
            if len(common_dates) < 30:
                return self.config.default_beta

            stock_returns = stock_returns.loc[common_dates]
            market_returns = market_returns.loc[common_dates]

            # Calculate beta (covariance / variance)
            covariance = np.cov(stock_returns, market_returns)[0, 1]
            market_variance = np.var(market_returns)

            if market_variance == 0:
                return self.config.default_beta

            beta = covariance / market_variance

            # Constrain to reasonable range
            beta = max(self.config.min_beta, min(beta, self.config.max_beta))

            return beta

        except Exception as e:
            return self.config.default_beta

    def _calculate_wacc(self, data: FinancialData) -> float:
        """
        Calculate Weighted Average Cost of Capital

        Formula:
            WACC = (E/V × Re) + (D/V × Rd × (1 - Tc))

        Where:
            E = Market value of equity
            D = Market value of debt
            V = E + D
            Re = Cost of equity (CAPM)
            Rd = Cost of debt
            Tc = Corporate tax rate

        Args:
            data: FinancialData object

        Returns:
            WACC as decimal
        """
        # Cost of Equity using CAPM
        beta = data.beta or self.config.default_beta
        cost_of_equity = self.config.risk_free_rate + (beta * self.config.market_risk_premium)

        # Cost of Debt
        if data.interest_expense and data.total_debt and data.total_debt > 0:
            cost_of_debt = abs(data.interest_expense) / data.total_debt
        else:
            # Default to risk-free rate + 5% spread
            cost_of_debt = self.config.risk_free_rate + 0.05

        # Capital structure weights
        net_debt = max((data.total_debt or 0) - (data.cash or 0), 0)
        total_value = data.market_cap + net_debt

        if total_value > 0:
            weight_equity = data.market_cap / total_value
            weight_debt = net_debt / total_value

            # WACC with tax shield
            wacc = (
                (weight_equity * cost_of_equity) +
                (weight_debt * cost_of_debt * (1 - self.config.corporate_tax_rate))
            )
        else:
            wacc = cost_of_equity

        # Constrain to reasonable range
        wacc = max(self.config.wacc_floor, min(wacc, self.config.wacc_ceiling))

        return wacc

    # ==========================================================================
    # GROWTH RATE ESTIMATION
    # ==========================================================================

    def _estimate_growth_rate(self, data: FinancialData) -> float:
        """
        Estimate sustainable growth rate from historical data

        Args:
            data: FinancialData object

        Returns:
            Estimated growth rate as decimal
        """
        growth_rates = []

        # Revenue growth
        if data.revenue_growth is not None and -0.5 < data.revenue_growth < 1.0:
            growth_rates.append(data.revenue_growth)

        # FCF growth
        if data.fcf_growth is not None and -0.5 < data.fcf_growth < 1.0:
            growth_rates.append(data.fcf_growth)

        # Earnings growth
        if data.earnings_growth is not None and -0.5 < data.earnings_growth < 1.0:
            growth_rates.append(data.earnings_growth)

        if growth_rates:
            # Weighted average (revenue gets higher weight)
            if len(growth_rates) == 3:
                avg_growth = (growth_rates[0] * 0.4 + growth_rates[1] * 0.3 + growth_rates[2] * 0.3)
            else:
                avg_growth = statistics.mean(growth_rates)

            # Cap at maximum
            growth = max(-0.2, min(avg_growth, self.config.max_growth_cap))
        else:
            growth = self.config.default_growth_rate

        return growth

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            ticker = yf.Ticker(f"{symbol}.KA")
            info = ticker.info
            return info.get('currentPrice') or info.get('regularMarketPrice')
        except:
            return None

    def _get_market_cap(self, symbol: str) -> Optional[float]:
        """Get current market capitalization"""
        try:
            ticker = yf.Ticker(f"{symbol}.KA")
            return ticker.info.get('marketCap')
        except:
            return None

    # ==========================================================================
    # VALUATION METHODS
    # ==========================================================================

    def _calculate_dcf(self, data: FinancialData, wacc: float,
                       growth_rate: float) -> Optional[MethodValuation]:
        """
        Multi-stage DCF valuation

        Implements three-stage model:
        - Stage 1: High growth (years 1-3)
        - Stage 2: Transition to maturity (years 4-7)
        - Stage 3: Terminal perpetuity

        Args:
            data: FinancialData object
            wacc: Weighted average cost of capital
            growth_rate: Estimated growth rate

        Returns:
            MethodValuation object or None
        """
        if not data.free_cash_flow or data.free_cash_flow <= 0:
            return None

        base_fcf = data.free_cash_flow

        # Stage 1: High growth
        high_growth = min(growth_rate, 0.20)  # Cap at 20%
        pv = 0

        for year in range(1, self.config.dcf_high_growth_years + 1):
            fcf_projected = base_fcf * (1 + high_growth) ** year
            pv += fcf_projected / (1 + wacc) ** year

        # Stage 2: Transition
        transition_growth = (high_growth + self.config.terminal_growth_rate) / 2

        for year in range(self.config.dcf_high_growth_years + 1,
                         self.config.dcf_transition_years + 1):
            years_in_transition = year - self.config.dcf_high_growth_years
            declining_rate = transition_growth * (
                self.config.dcf_transition_years + 1 - year
            ) / 4

            fcf_projected = (
                base_fcf *
                (1 + high_growth) ** self.config.dcf_high_growth_years *
                (1 + declining_rate) ** years_in_transition
            )
            pv += fcf_projected / (1 + wacc) ** year

        # Stage 3: Terminal value
        terminal_growth = self.config.terminal_growth_rate

        if wacc <= terminal_growth:
            terminal_growth = wacc * 0.8

        final_fcf = (
            base_fcf *
            (1 + high_growth) ** self.config.dcf_high_growth_years *
            (1 + transition_growth) ** (
                self.config.dcf_transition_years - self.config.dcf_high_growth_years
            )
        )

        terminal_value = (final_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_terminal = terminal_value / (1 + wacc) ** self.config.dcf_transition_years

        intrinsic_value = pv + pv_terminal

        # Calculate gap and signal
        gap = (intrinsic_value - data.market_cap) / data.market_cap

        if gap > self.config.bullish_threshold:
            signal = ValuationSignal.BULLISH
        elif gap < self.config.bearish_threshold:
            signal = ValuationSignal.BEARISH
        else:
            signal = ValuationSignal.NEUTRAL

        # Confidence based on FCF quality and growth sustainability
        confidence = min(abs(gap) / 0.30, 1.0)
        if data.free_cash_flow < 0:
            confidence *= 0.5

        return MethodValuation(
            method=ValuationMethod.DCF,
            intrinsic_value=intrinsic_value,
            current_market_cap=data.market_cap,
            valuation_gap=gap,
            signal=signal,
            confidence=confidence,
            details={
                'base_fcf': base_fcf,
                'wacc': wacc,
                'high_growth': high_growth,
                'terminal_growth': terminal_growth,
                'pv_explicit': pv,
                'pv_terminal': pv_terminal
            }
        )

    def _calculate_owner_earnings(self, data: FinancialData,
                                  growth_rate: float) -> Optional[MethodValuation]:
        """
        Owner Earnings valuation (Buffett approach)

        Formula:
            Owner Earnings = Net Income + D&A - CapEx - Working Capital Change

        Uses maintenance capex assumption (80% of total capex) to be conservative.

        Args:
            data: FinancialData object
            growth_rate: Estimated growth rate

        Returns:
            MethodValuation object or None
        """
        if not data.net_income:
            return None

        # Calculate owner earnings
        depreciation = data.depreciation or 0

        # Use maintenance capex (estimate as 80% of actual capex)
        maintenance_capex = (data.capex or 0) * 0.8

        # Working capital change - estimate as 5% of revenue growth
        wc_change = 0
        if data.revenue and data.revenue_growth:
            wc_change = data.revenue * data.revenue_growth * 0.05

        owner_earnings = data.net_income + depreciation - maintenance_capex - wc_change

        if owner_earnings <= 0:
            return None

        # Project future owner earnings
        pv = 0.0
        for year in range(1, self.config.forecast_years + 1):
            future_earnings = owner_earnings * (1 + growth_rate) ** year
            pv += future_earnings / (1 + self.config.required_return) ** year

        # Terminal value
        terminal_growth = min(growth_rate, self.config.terminal_growth_rate)
        terminal_earnings = owner_earnings * (1 + growth_rate) ** self.config.forecast_years
        terminal_value = (terminal_earnings * (1 + terminal_growth)) / (
            self.config.required_return - terminal_growth
        )
        pv_terminal = terminal_value / (1 + self.config.required_return) ** self.config.forecast_years

        intrinsic_value = pv + pv_terminal

        # Apply margin of safety
        intrinsic_value *= (1 - self.config.owner_earnings_margin)

        # Calculate gap and signal
        gap = (intrinsic_value - data.market_cap) / data.market_cap

        if gap > self.config.bullish_threshold:
            signal = ValuationSignal.BULLISH
        elif gap < self.config.bearish_threshold:
            signal = ValuationSignal.BEARISH
        else:
            signal = ValuationSignal.NEUTRAL

        # Confidence
        confidence = min(abs(gap) / 0.30, 1.0)

        return MethodValuation(
            method=ValuationMethod.OWNER_EARNINGS,
            intrinsic_value=intrinsic_value,
            current_market_cap=data.market_cap,
            valuation_gap=gap,
            signal=signal,
            confidence=confidence,
            details={
                'owner_earnings': owner_earnings,
                'net_income': data.net_income,
                'depreciation': depreciation,
                'maintenance_capex': maintenance_capex,
                'wc_change': wc_change,
                'margin_of_safety': self.config.owner_earnings_margin
            }
        )

    def _calculate_ev_ebitda(self, data: FinancialData,
                            sector: Optional[str] = None) -> Optional[MethodValuation]:
        """
        EV/EBITDA multiples valuation

        Uses sector-specific multiples for PSX market.

        Args:
            data: FinancialData object
            sector: Optional sector name for sector-specific multiple

        Returns:
            MethodValuation object or None
        """
        if not data.ebitda or data.ebitda <= 0:
            return None

        # Get appropriate multiple
        if sector and sector in self.config.sector_multiples:
            target_multiple = self.config.sector_multiples[sector]
        else:
            target_multiple = self.config.sector_multiples['Default']

        # Calculate implied enterprise value
        implied_ev = data.ebitda * target_multiple

        # Convert to equity value
        net_debt = (data.total_debt or 0) - (data.cash or 0)
        intrinsic_value = max(implied_ev - net_debt, 0)

        # Calculate gap and signal
        gap = (intrinsic_value - data.market_cap) / data.market_cap

        if gap > self.config.bullish_threshold:
            signal = ValuationSignal.BULLISH
        elif gap < self.config.bearish_threshold:
            signal = ValuationSignal.BEARISH
        else:
            signal = ValuationSignal.NEUTRAL

        # Confidence (lower for multiples-based methods)
        confidence = min(abs(gap) / 0.30, 1.0) * 0.8

        return MethodValuation(
            method=ValuationMethod.EV_EBITDA,
            intrinsic_value=intrinsic_value,
            current_market_cap=data.market_cap,
            valuation_gap=gap,
            signal=signal,
            confidence=confidence,
            details={
                'ebitda': data.ebitda,
                'target_multiple': target_multiple,
                'current_multiple': data.ev_to_ebitda,
                'implied_ev': implied_ev,
                'net_debt': net_debt,
                'sector': sector or 'Default'
            }
        )

    def _calculate_residual_income(self, data: FinancialData,
                                   growth_rate: float) -> Optional[MethodValuation]:
        """
        Residual Income Model (Edwards-Bell-Ohlson)

        Formula:
            RI_t = NI_t - (Cost of Equity × Book Value_{t-1})
            Value = Book Value + PV(Future Residual Income)

        Args:
            data: FinancialData object
            growth_rate: Estimated growth rate

        Returns:
            MethodValuation object or None
        """
        if not data.net_income or not data.book_value or data.book_value <= 0:
            return None

        # Cost of equity using CAPM
        beta = data.beta or self.config.default_beta
        cost_of_equity = self.config.risk_free_rate + (beta * self.config.market_risk_premium)

        # Calculate current residual income
        residual_income = data.net_income - (cost_of_equity * data.book_value)

        if residual_income <= 0:
            return None

        # Project future residual income
        pv_ri = 0.0
        for year in range(1, self.config.forecast_years + 1):
            ri_t = residual_income * (1 + growth_rate) ** year
            pv_ri += ri_t / (1 + cost_of_equity) ** year

        # Terminal value
        terminal_growth = min(growth_rate, self.config.terminal_growth_rate)
        terminal_ri = residual_income * (1 + growth_rate) ** (self.config.forecast_years + 1)

        if cost_of_equity <= terminal_growth:
            terminal_growth = cost_of_equity * 0.8

        terminal_value = terminal_ri / (cost_of_equity - terminal_growth)
        pv_terminal = terminal_value / (1 + cost_of_equity) ** self.config.forecast_years

        intrinsic_value = data.book_value + pv_ri + pv_terminal

        # Apply margin of safety
        intrinsic_value *= (1 - self.config.residual_income_margin)

        # Calculate gap and signal
        gap = (intrinsic_value - data.market_cap) / data.market_cap

        if gap > self.config.bullish_threshold:
            signal = ValuationSignal.BULLISH
        elif gap < self.config.bearish_threshold:
            signal = ValuationSignal.BEARISH
        else:
            signal = ValuationSignal.NEUTRAL

        # Confidence
        confidence = min(abs(gap) / 0.30, 1.0) * 0.7  # Lower weight method

        return MethodValuation(
            method=ValuationMethod.RESIDUAL_INCOME,
            intrinsic_value=intrinsic_value,
            current_market_cap=data.market_cap,
            valuation_gap=gap,
            signal=signal,
            confidence=confidence,
            details={
                'book_value': data.book_value,
                'residual_income': residual_income,
                'cost_of_equity': cost_of_equity,
                'pv_ri': pv_ri,
                'pv_terminal': pv_terminal,
                'margin_of_safety': self.config.residual_income_margin
            }
        )

    # ==========================================================================
    # AGGREGATION
    # ==========================================================================

    def _aggregate_valuations(self, valuations: List[MethodValuation]) -> Tuple[float, float, ValuationSignal, float]:
        """
        Aggregate multiple valuation methods with weighted average

        Args:
            valuations: List of MethodValuation objects

        Returns:
            Tuple of (weighted_value, weighted_gap, signal, confidence)
        """
        # Get method weights
        weights = {
            ValuationMethod.DCF: self.config.dcf_weight,
            ValuationMethod.OWNER_EARNINGS: self.config.owner_earnings_weight,
            ValuationMethod.EV_EBITDA: self.config.ev_ebitda_weight,
            ValuationMethod.RESIDUAL_INCOME: self.config.residual_income_weight
        }

        # Calculate total weight from available methods
        total_weight = sum(weights[v.method] for v in valuations)

        if total_weight == 0:
            return 0, 0, ValuationSignal.NEUTRAL, 0

        # Weighted average intrinsic value
        weighted_value = sum(
            v.intrinsic_value * weights[v.method] for v in valuations
        ) / total_weight

        # Weighted average gap
        weighted_gap = sum(
            v.valuation_gap * weights[v.method] for v in valuations
        ) / total_weight

        # Determine overall signal
        if weighted_gap > self.config.bullish_threshold:
            signal = ValuationSignal.BULLISH
        elif weighted_gap < self.config.bearish_threshold:
            signal = ValuationSignal.BEARISH
        else:
            signal = ValuationSignal.NEUTRAL

        # Calculate confidence based on:
        # 1. Magnitude of gap
        # 2. Agreement between methods
        gap_confidence = min(abs(weighted_gap) / 0.30, 1.0)

        # Check agreement (all methods pointing same direction)
        bullish_count = sum(1 for v in valuations if v.signal == ValuationSignal.BULLISH)
        bearish_count = sum(1 for v in valuations if v.signal == ValuationSignal.BEARISH)
        neutral_count = sum(1 for v in valuations if v.signal == ValuationSignal.NEUTRAL)

        total_methods = len(valuations)
        agreement_ratio = max(bullish_count, bearish_count, neutral_count) / total_methods

        # Weighted confidence
        confidence = gap_confidence * 0.6 + agreement_ratio * 0.4

        return weighted_value, weighted_gap, signal, confidence

    # ==========================================================================
    # STORAGE AND OUTPUT
    # ==========================================================================

    def _store_valuation(self, snapshot: ValuationSnapshot):
        """
        Store valuation snapshot in database

        Args:
            snapshot: ValuationSnapshot object
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                created_at = datetime.now().isoformat()

                # Store main valuation
                cursor.execute('''
                    INSERT OR REPLACE INTO valuations
                    (symbol, date, current_price, market_cap, intrinsic_value,
                     valuation_gap, signal, confidence, wacc, beta, growth_rate,
                     data_quality_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot.symbol,
                    snapshot.date,
                    snapshot.current_price,
                    snapshot.market_cap,
                    snapshot.weighted_intrinsic_value,
                    snapshot.weighted_valuation_gap,
                    snapshot.overall_signal.value,
                    snapshot.overall_confidence,
                    snapshot.wacc,
                    snapshot.beta,
                    snapshot.growth_rate,
                    snapshot.data_quality_score,
                    created_at
                ))

                # Store individual method valuations
                for val in snapshot.valuations:
                    cursor.execute('''
                        INSERT OR REPLACE INTO method_valuations
                        (symbol, date, method, intrinsic_value, valuation_gap,
                         signal, confidence, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        snapshot.symbol,
                        snapshot.date,
                        val.method.value,
                        val.intrinsic_value,
                        val.valuation_gap,
                        val.signal.value,
                        val.confidence,
                        str(val.details)
                    ))

                conn.commit()
        except Exception as e:
            print(f"  Warning: Failed to store valuation: {str(e)}")

    def _print_summary(self, snapshot: ValuationSnapshot):
        """
        Print formatted valuation summary

        Args:
            snapshot: ValuationSnapshot object
        """
        print(f"\n{'='*80}")
        print(f"VALUATION SUMMARY: {snapshot.symbol}")
        print('='*80)

        print(f"\nCurrent Market Data:")
        print(f"  Price: PKR {snapshot.current_price:,.2f}")
        print(f"  Market Cap: PKR {snapshot.market_cap:,.0f}")
        print(f"  Beta: {snapshot.beta:.2f}" if snapshot.beta else "  Beta: N/A")
        print(f"  WACC: {snapshot.wacc:.2%}" if snapshot.wacc else "  WACC: N/A")
        print(f"  Growth Rate: {snapshot.growth_rate:.2%}" if snapshot.growth_rate else "  Growth Rate: N/A")

        print(f"\nValuation Methods:")
        for val in snapshot.valuations:
            signal_emoji = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖"}
            emoji = signal_emoji.get(val.signal.value, "")
            print(f"\n  {val.method.value}:")
            print(f"    Intrinsic Value: PKR {val.intrinsic_value:,.0f}")
            print(f"    Valuation Gap: {val.valuation_gap:+.1%}")
            print(f"    Signal: {emoji} {val.signal.value}")
            print(f"    Confidence: {val.confidence*100:.0f}%")

        print(f"\n{'='*80}")
        print(f"OVERALL VALUATION")
        print('='*80)

        signal_emoji = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖"}
        emoji = signal_emoji.get(snapshot.overall_signal.value, "")

        print(f"\n  Weighted Intrinsic Value: PKR {snapshot.weighted_intrinsic_value:,.0f}")
        print(f"  Current Market Cap: PKR {snapshot.market_cap:,.0f}")
        print(f"  Valuation Gap: {snapshot.weighted_valuation_gap:+.1%}")
        print(f"\n  Signal: {emoji} {snapshot.overall_signal.value}")
        print(f"  Confidence: {snapshot.overall_confidence*100:.0f}%")
        print(f"  Data Quality: {snapshot.data_quality_score*100:.0f}%")

        if snapshot.warnings:
            print(f"\n  Warnings ({len(snapshot.warnings)}):")
            for warning in snapshot.warnings:
                print(f"    - {warning}")

        print(f"\n{'='*80}")

    def _empty_snapshot(self, symbol: str) -> ValuationSnapshot:
        """Create empty snapshot for error cases"""
        return ValuationSnapshot(
            symbol=symbol,
            date=datetime.now().strftime('%Y-%m-%d'),
            current_price=0.0,
            market_cap=0.0,
            valuations=[],
            overall_signal=ValuationSignal.NEUTRAL,
            overall_confidence=0.0
        )

    # ==========================================================================
    # BATCH ANALYSIS
    # ==========================================================================

    def analyze_batch(self, symbols: List[str],
                     sectors: Optional[Dict[str, str]] = None) -> Dict[str, ValuationSnapshot]:
        """
        Analyze multiple stocks

        Args:
            symbols: List of stock symbols
            sectors: Optional dictionary mapping symbol to sector

        Returns:
            Dictionary mapping symbol to ValuationSnapshot
        """
        results = {}
        sectors = sectors or {}

        print(f"\n{'='*80}")
        print(f"PSX VALUATION AGENT - BATCH ANALYSIS")
        print(f"{'='*80}")
        print(f"Analyzing {len(symbols)} symbols")
        print(f"{'='*80}\n")

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Analyzing {symbol}...")

            try:
                sector = sectors.get(symbol)
                snapshot = self.analyze_symbol(symbol, sector)
                results[symbol] = snapshot
            except Exception as e:
                print(f"Error analyzing {symbol}: {str(e)}")
                results[symbol] = self._empty_snapshot(symbol)

        # Print batch summary
        print(f"\n{'='*80}")
        print(f"BATCH ANALYSIS SUMMARY")
        print(f"{'='*80}\n")

        for symbol, snapshot in results.items():
            if snapshot.valuations:
                signal_emoji = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖"}
                emoji = signal_emoji.get(snapshot.overall_signal.value, "")
                print(f"{symbol:10s} {emoji} {snapshot.overall_signal.value:8s} "
                      f"Gap: {snapshot.weighted_valuation_gap:+6.1%} "
                      f"Confidence: {snapshot.overall_confidence*100:3.0f}%")

        print(f"\n{'='*80}")
        print(f"Analysis complete")
        print(f"{'='*80}\n")

        return results

    def get_valuation_history(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        Get valuation history for a symbol

        Args:
            symbol: Stock symbol
            days: Number of days of history

        Returns:
            List of valuation records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT date, current_price, market_cap, intrinsic_value,
                       valuation_gap, signal, confidence
                FROM valuations
                WHERE symbol = ? AND date >= ?
                ORDER BY date DESC
            ''', (symbol, cutoff_date))

            columns = ['date', 'current_price', 'market_cap', 'intrinsic_value',
                      'valuation_gap', 'signal', 'confidence']

            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Example usage of PSXValuationAgent"""

    print("="*80)
    print("PSX VALUATION AGENT - DEMO")
    print("="*80)

    # Initialize agent
    print("\nInitializing valuation agent...")
    agent = PSXValuationAgent()

    # Test symbols with sectors
    test_symbols = {
        'HBL': 'Banks',
        'LUCK': 'Cement',
        'PSO': 'Oil & Gas'
    }

    print(f"\nAnalyzing {len(test_symbols)} stocks...")

    # Batch analysis
    results = agent.analyze_batch(
        symbols=list(test_symbols.keys()),
        sectors=test_symbols
    )

    # Show detailed results for first stock
    if results:
        first_symbol = list(results.keys())[0]
        print(f"\n{'='*80}")
        print(f"DETAILED EXAMPLE: {first_symbol}")
        print('='*80)

        snapshot = results[first_symbol]
        if snapshot.valuations:
            print(f"\nMethod Details:")
            for val in snapshot.valuations:
                print(f"\n{val.method.value}:")
                for key, value in val.details.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:,.2f}")
                    else:
                        print(f"  {key}: {value}")

    print(f"\n{'='*80}")
    print("Demo complete")
    print("="*80)


if __name__ == "__main__":
    main()
