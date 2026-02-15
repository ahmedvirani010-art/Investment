from __future__ import annotations
"""Valuation Agent - Enhanced Version

Implements four complementary valuation methodologies with configurable parameters,
comprehensive data validation, enhanced error handling, and sensitivity analysis.

Valuation Methods:
1. Discounted Cash Flow (DCF) - Multi-stage growth model with WACC
2. Owner Earnings - Buffett-style economic profit valuation
3. EV/EBITDA - Implied equity value via market multiples
4. Residual Income Model - Edwards-Bell-Ohlson framework
"""

import json
import statistics
from dataclasses import dataclass, field
from typing import Optional, Callable
from langchain_core.messages import HumanMessage
from src.graph.state import AgentState, show_agent_reasoning
from src.utils.progress import progress
from src.utils.api_key import get_api_key_from_state
from src.tools.api import (
    get_financial_metrics,
    get_market_cap,
    search_line_items,
)


# ==============================================================================
# CONFIGURATION AND CONSTANTS
# ==============================================================================

@dataclass
class ValuationConfig:
    """Configuration for valuation models.

    All parameters can be customized for different markets, risk profiles,
    or investment strategies.
    """

    # Growth assumptions
    default_growth_rate: float = 0.05  # 5% default growth
    terminal_growth_rate: float = 0.03  # 3% perpetuity growth (GDP proxy)
    max_growth_cap: float = 0.25  # 25% maximum growth rate

    # Discount rates
    required_return: float = 0.15  # 15% required return for owner earnings
    discount_rate: float = 0.10  # 10% base discount rate
    risk_free_rate: float = 0.045  # 4.5% risk-free rate (10-year Treasury)
    market_risk_premium: float = 0.06  # 6% equity risk premium

    # Safety margins
    owner_earnings_margin: float = 0.25  # 25% margin of safety
    residual_income_margin: float = 0.20  # 20% margin of safety

    # WACC parameters
    default_beta: float = 1.0  # Market beta proxy
    wacc_floor: float = 0.06  # 6% minimum WACC
    wacc_ceiling: float = 0.20  # 20% maximum WACC
    tax_rate: float = 0.25  # 25% corporate tax rate

    # Model weights (must sum to 1.0)
    dcf_weight: float = 0.35
    owner_earnings_weight: float = 0.35
    ev_ebitda_weight: float = 0.20
    residual_income_weight: float = 0.10

    # Signal thresholds
    bullish_threshold: float = 0.15  # 15% undervalued = bullish
    bearish_threshold: float = -0.15  # 15% overvalued = bearish

    # Projection periods
    forecast_years: int = 5  # Years for explicit forecasting
    dcf_high_growth_years: int = 3  # High growth stage
    dcf_transition_years: int = 7  # Total projection before terminal

    def __post_init__(self):
        """Validate configuration parameters."""
        total_weight = (
            self.dcf_weight + self.owner_earnings_weight +
            self.ev_ebitda_weight + self.residual_income_weight
        )
        if not 0.99 <= total_weight <= 1.01:
            raise ValueError(f"Model weights must sum to 1.0, got {total_weight}")


class ValuationConstants:
    """Constants for valuation calculations."""

    # Economic constants
    GDP_GROWTH_PROXY = 0.03  # Long-term GDP growth

    # Beta bounds
    MIN_BETA = 0.5  # Defensive stocks
    MAX_BETA = 2.0  # Aggressive stocks

    # Market cap thresholds (USD)
    SMALL_CAP_THRESHOLD = 1_000_000_000  # $1B
    LARGE_CAP_THRESHOLD = 50_000_000_000  # $50B

    # Volatility and risk thresholds
    HIGH_VOLATILITY_THRESHOLD = 0.3  # 30% earnings volatility
    HIGH_LEVERAGE_THRESHOLD = 1.0  # Debt/Equity > 1.0

    # Data quality thresholds
    MIN_HISTORICAL_PERIODS = 2  # Minimum data points needed
    MAX_OUTLIER_GROWTH = 1.0  # 100%+ growth flagged as outlier
    FCF_QUALITY_THRESHOLD = 0.6  # 60% of periods must have positive FCF


# ==============================================================================
# DATA VALIDATION
# ==============================================================================

def validate_financial_data(
    most_recent_metrics: object,
    line_items: list,
    ticker: str,
    agent_id: str
) -> tuple[bool, list[str]]:
    """Validate financial data quality and completeness.

    Args:
        most_recent_metrics: Most recent financial metrics object
        line_items: List of historical line items
        ticker: Stock ticker symbol
        agent_id: Agent identifier for logging

    Returns:
        (is_valid, warnings) tuple where is_valid indicates if data passes
        minimum quality checks, and warnings contains list of issues found
    """
    warnings = []

    # Check for required metrics
    if not most_recent_metrics.market_cap or most_recent_metrics.market_cap <= 0:
        warnings.append("Missing or invalid market cap")

    if not most_recent_metrics.enterprise_value:
        warnings.append("Missing enterprise value")

    # Check for minimum historical data
    if len(line_items) < ValuationConstants.MIN_HISTORICAL_PERIODS:
        warnings.append(
            f"Insufficient historical data: {len(line_items)} periods "
            f"(need {ValuationConstants.MIN_HISTORICAL_PERIODS}+)"
        )

    # Detect outlier growth rates
    earnings_growth = most_recent_metrics.earnings_growth or 0
    if abs(earnings_growth) > ValuationConstants.MAX_OUTLIER_GROWTH:
        warnings.append(
            f"Extreme earnings growth detected: {earnings_growth:.1%} "
            "(may indicate data quality issue)"
        )

    revenue_growth = most_recent_metrics.revenue_growth or 0
    if abs(revenue_growth) > ValuationConstants.MAX_OUTLIER_GROWTH:
        warnings.append(f"Extreme revenue growth detected: {revenue_growth:.1%}")

    # Check FCF quality
    fcf_values = [
        li.free_cash_flow for li in line_items
        if hasattr(li, 'free_cash_flow') and li.free_cash_flow is not None
    ]

    if not fcf_values:
        warnings.append("No free cash flow data available")
    else:
        positive_fcf_count = sum(1 for fcf in fcf_values if fcf > 0)
        fcf_quality = positive_fcf_count / len(fcf_values)

        if fcf_quality < ValuationConstants.FCF_QUALITY_THRESHOLD:
            warnings.append(
                f"Low FCF quality: only {fcf_quality:.0%} of periods have positive FCF"
            )

    # Check for negative equity (balance sheet issues)
    if most_recent_metrics.price_to_book_ratio and most_recent_metrics.price_to_book_ratio < 0:
        warnings.append("Negative book value detected (balance sheet issues)")

    # Validate debt metrics
    if most_recent_metrics.debt_to_equity and most_recent_metrics.debt_to_equity < 0:
        warnings.append("Invalid debt-to-equity ratio")

    # Critical failures (more than 2 major issues)
    is_valid = len(warnings) < 3

    # Log warnings
    if warnings:
        progress.update_status(
            agent_id, ticker,
            f"Data validation warnings: {len(warnings)} issues found"
        )
        for warning in warnings:
            progress.update_status(agent_id, ticker, f"  ⚠️  {warning}")

    return is_valid, warnings


# ==============================================================================
# ERROR HANDLING
# ==============================================================================

def safe_calculate_valuation(
    calc_func: Callable,
    method_name: str,
    agent_id: str,
    ticker: str,
    **kwargs
) -> float:
    """Safely execute valuation calculation with comprehensive error handling.

    Args:
        calc_func: Valuation function to execute
        method_name: Name of valuation method (for logging)
        agent_id: Agent identifier for logging
        ticker: Stock ticker symbol
        **kwargs: Arguments to pass to calc_func

    Returns:
        Calculated value, or 0 if calculation fails
    """
    try:
        result = calc_func(**kwargs)

        if result is None or result < 0:
            progress.update_status(
                agent_id, ticker,
                f"Warning: {method_name} returned {result} (expected positive value)"
            )
            return 0

        # Check for unreasonably large values (likely calculation error)
        if result > 1e15:  # $1 quadrillion
            progress.update_status(
                agent_id, ticker,
                f"Warning: {method_name} returned unrealistic value: ${result:,.0f}"
            )
            return 0

        return result

    except ZeroDivisionError:
        progress.update_status(
            agent_id, ticker,
            f"Error in {method_name}: Division by zero (check discount rate > growth rate)"
        )
        return 0

    except ValueError as e:
        progress.update_status(
            agent_id, ticker,
            f"Error in {method_name}: Invalid value - {str(e)}"
        )
        return 0

    except TypeError as e:
        progress.update_status(
            agent_id, ticker,
            f"Error in {method_name}: Type error - {str(e)}"
        )
        return 0

    except Exception as e:
        progress.update_status(
            agent_id, ticker,
            f"Unexpected error in {method_name}: {type(e).__name__} - {str(e)}"
        )
        return 0


# ==============================================================================
# BETA AND WACC ESTIMATION
# ==============================================================================

def estimate_beta(
    ticker: str,
    market_cap: float,
    financial_metrics: list,
    config: ValuationConfig
) -> float:
    """Estimate beta from financial characteristics.

    In absence of actual calculated beta, this function estimates beta based on:
    - Company size (market cap)
    - Financial leverage (debt/equity)
    - Earnings volatility

    Args:
        ticker: Stock ticker symbol
        market_cap: Current market capitalization
        financial_metrics: List of historical financial metrics
        config: Valuation configuration

    Returns:
        Estimated beta, constrained to reasonable range (0.5 to 2.0)
    """
    # Start with market beta
    beta_base = config.default_beta

    # Size adjustment (smaller companies have higher betas)
    if market_cap < ValuationConstants.SMALL_CAP_THRESHOLD:
        beta_base += 0.3  # Small cap premium
    elif market_cap > ValuationConstants.LARGE_CAP_THRESHOLD:
        beta_base -= 0.2  # Large cap discount

    # Leverage adjustment (higher debt increases beta)
    debt_to_equity = financial_metrics[0].debt_to_equity
    if debt_to_equity:
        if debt_to_equity > ValuationConstants.HIGH_LEVERAGE_THRESHOLD:
            beta_base += 0.2  # High leverage penalty
        elif debt_to_equity < 0.3:
            beta_base -= 0.1  # Conservative balance sheet reward

    # Earnings volatility adjustment
    earnings_growth_list = [
        m.earnings_growth for m in financial_metrics
        if m.earnings_growth is not None
    ]

    if len(earnings_growth_list) >= 3:
        try:
            volatility = statistics.stdev(earnings_growth_list)
            if volatility > ValuationConstants.HIGH_VOLATILITY_THRESHOLD:
                beta_base += 0.2  # High volatility penalty
        except statistics.StatisticsError:
            pass  # Not enough data points for stdev

    # Constrain to reasonable range
    beta = max(ValuationConstants.MIN_BETA, min(beta_base, ValuationConstants.MAX_BETA))

    return beta


def calculate_wacc(
    market_cap: float,
    total_debt: float | None,
    cash: float | None,
    interest_coverage: float | None,
    debt_to_equity: float | None,
    ticker: str,
    financial_metrics: list,
    config: ValuationConfig
) -> float:
    """Calculate Weighted Average Cost of Capital (WACC).

    Formula:
        WACC = (E/V × Re) + (D/V × Rd × (1 - Tc))

    Where:
        E = Market value of equity
        D = Market value of debt
        V = E + D (total value)
        Re = Cost of equity (CAPM)
        Rd = Cost of debt
        Tc = Corporate tax rate

    Args:
        market_cap: Market value of equity
        total_debt: Total debt outstanding
        cash: Cash and equivalents
        interest_coverage: EBIT / Interest expense
        debt_to_equity: Debt to equity ratio
        ticker: Stock ticker symbol
        financial_metrics: Historical financial metrics for beta estimation
        config: Valuation configuration

    Returns:
        WACC as decimal (e.g., 0.10 for 10%)
    """
    # Cost of Equity (using CAPM: Rf + β × MRP)
    beta = estimate_beta(ticker, market_cap, financial_metrics, config)
    cost_of_equity = config.risk_free_rate + (beta * config.market_risk_premium)

    # Cost of Debt - estimate from interest coverage
    if interest_coverage and interest_coverage > 0:
        # Higher coverage = lower cost of debt
        # Use inverse relationship with floor at risk-free rate
        cost_of_debt = max(
            config.risk_free_rate + 0.01,  # Minimum spread of 1%
            config.risk_free_rate + (10 / interest_coverage)
        )
    else:
        # Default to risk-free + 5% spread if no coverage data
        cost_of_debt = config.risk_free_rate + 0.05

    # Calculate capital structure weights
    net_debt = max((total_debt or 0) - (cash or 0), 0)
    total_value = market_cap + net_debt

    if total_value > 0:
        weight_equity = market_cap / total_value
        weight_debt = net_debt / total_value

        # WACC formula with tax shield
        wacc = (
            (weight_equity * cost_of_equity) +
            (weight_debt * cost_of_debt * (1 - config.tax_rate))
        )
    else:
        # If no debt or invalid data, use cost of equity
        wacc = cost_of_equity

    # Constrain to reasonable range
    wacc = min(max(wacc, config.wacc_floor), config.wacc_ceiling)

    return wacc


# ==============================================================================
# GROWTH ESTIMATION
# ==============================================================================

def estimate_growth_profile(
    financial_metrics: list,
    market_cap: float,
    fcf_history: list[float],
    config: ValuationConfig
) -> dict:
    """Estimate multi-stage growth rates based on company lifecycle.

    Considers:
    - Historical growth trends (revenue, FCF, earnings)
    - Company size and maturity
    - FCF consistency and quality

    Args:
        financial_metrics: Historical financial metrics
        market_cap: Current market capitalization
        fcf_history: Historical free cash flow values
        config: Valuation configuration

    Returns:
        Dictionary with growth profile:
            - high_growth: Growth rate for initial years
            - terminal_growth: Perpetuity growth rate
            - transition_years: Years before terminal phase
            - confidence: Confidence in projections (0-1)
    """
    # Analyze historical growth
    revenue_growth = financial_metrics[0].revenue_growth or config.default_growth_rate
    fcf_growth = financial_metrics[0].free_cash_flow_growth or config.default_growth_rate
    earnings_growth = financial_metrics[0].earnings_growth or config.default_growth_rate

    # Weighted average of growth metrics
    avg_growth = (
        revenue_growth * 0.4 +
        fcf_growth * 0.3 +
        earnings_growth * 0.3
    )

    # Lifecycle adjustment based on market cap
    if market_cap > ValuationConstants.LARGE_CAP_THRESHOLD:
        # Mature large cap - lower growth expectations
        high_growth = min(avg_growth * 0.7, 0.10)
        terminal_growth = 0.025

    elif market_cap < ValuationConstants.SMALL_CAP_THRESHOLD:
        # Small cap - higher growth potential
        high_growth = min(avg_growth * 1.3, config.max_growth_cap)
        terminal_growth = 0.04

    else:
        # Mid cap
        high_growth = min(avg_growth, 0.15)
        terminal_growth = config.terminal_growth_rate

    # Sustainability check
    if high_growth > 0.20:
        # Unsustainable high growth - shorter high-growth period
        transition_years = 3
    else:
        transition_years = 5

    # Calculate confidence based on FCF stability
    confidence = calculate_growth_confidence(fcf_history)

    return {
        'high_growth': high_growth,
        'terminal_growth': terminal_growth,
        'transition_years': transition_years,
        'confidence': confidence
    }


def calculate_growth_confidence(fcf_history: list[float]) -> float:
    """Calculate confidence in growth projections based on FCF stability.

    Args:
        fcf_history: Historical free cash flow values

    Returns:
        Confidence score from 0.3 (low) to 0.9 (high)
    """
    if len(fcf_history) < 3:
        return 0.3  # Low confidence with limited history

    # Check FCF consistency
    positive_fcf = [fcf for fcf in fcf_history if fcf > 0]
    if len(positive_fcf) < len(fcf_history) * ValuationConstants.FCF_QUALITY_THRESHOLD:
        return 0.4  # Inconsistent FCF

    # Calculate volatility (coefficient of variation)
    volatility = calculate_fcf_volatility(fcf_history)

    # Higher consistency = higher confidence
    confidence = max(0.3, min(1.0 - volatility, 0.9))

    return confidence


def calculate_fcf_volatility(fcf_history: list[float]) -> float:
    """Calculate FCF volatility as coefficient of variation.

    Args:
        fcf_history: Historical free cash flow values

    Returns:
        Coefficient of variation (std dev / mean), capped at 1.0
    """
    if len(fcf_history) < 3:
        return 0.5  # Default moderate volatility

    # Filter out zeros and negatives for volatility calculation
    positive_fcf = [fcf for fcf in fcf_history if fcf > 0]

    if len(positive_fcf) < 2:
        return 0.8  # High volatility if mostly negative FCF

    try:
        mean_fcf = statistics.mean(positive_fcf)
        std_fcf = statistics.stdev(positive_fcf)

        if mean_fcf > 0:
            return min(std_fcf / mean_fcf, 1.0)
        else:
            return 0.8

    except statistics.StatisticsError:
        return 0.5


# ==============================================================================
# VALUATION MODELS
# ==============================================================================

def calculate_owner_earnings_value(
    net_income: float | None,
    depreciation: float | None,
    capex: float | None,
    working_capital_change: float | None,
    growth_rate: float,
    config: ValuationConfig
) -> float:
    """Buffett-style owner earnings valuation.

    Formula:
        Owner Earnings = Net Income + D&A - CapEx - Working Capital Change

    Methodology:
        1. Calculate current owner earnings (economic profit)
        2. Project forward using constant growth rate
        3. Discount future earnings at required return
        4. Add terminal value (perpetuity growth model)
        5. Apply margin of safety discount

    Args:
        net_income: Most recent net income
        depreciation: Depreciation & amortization
        capex: Capital expenditures
        working_capital_change: Change in working capital
        growth_rate: Expected annual growth
        config: Valuation configuration

    Returns:
        Intrinsic value with margin of safety applied, or 0 if invalid

    Assumptions:
        - Terminal growth capped at 3% (GDP proxy)
        - Owner earnings must be positive
        - All inputs must be numeric
    """
    # Validate inputs
    if not all(isinstance(x, (int, float)) for x in [net_income, depreciation, capex, working_capital_change]):
        return 0

    # Calculate owner earnings
    owner_earnings = net_income + depreciation - capex - working_capital_change

    if owner_earnings <= 0:
        return 0

    # Project future owner earnings
    pv = 0.0
    for year in range(1, config.forecast_years + 1):
        future_earnings = owner_earnings * (1 + growth_rate) ** year
        pv += future_earnings / (1 + config.required_return) ** year

    # Terminal value
    terminal_growth = min(growth_rate, ValuationConstants.GDP_GROWTH_PROXY)
    terminal_earnings = owner_earnings * (1 + growth_rate) ** config.forecast_years
    terminal_value = (terminal_earnings * (1 + terminal_growth)) / (
        config.required_return - terminal_growth
    )
    pv_terminal = terminal_value / (1 + config.required_return) ** config.forecast_years

    intrinsic_value = pv + pv_terminal

    # Apply margin of safety
    return intrinsic_value * (1 - config.owner_earnings_margin)


def calculate_intrinsic_value(
    free_cash_flow: float | None,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    num_years: int = 5,
) -> float:
    """Classic DCF on FCF with constant growth and terminal value.

    Args:
        free_cash_flow: Current free cash flow
        growth_rate: Annual growth rate for projection period
        discount_rate: Discount rate (WACC or required return)
        terminal_growth_rate: Perpetuity growth rate
        num_years: Years to project explicitly

    Returns:
        Present value of future cash flows, or 0 if invalid
    """
    if free_cash_flow is None or free_cash_flow <= 0:
        return 0

    if discount_rate <= terminal_growth_rate:
        return 0  # Invalid: discount rate must exceed terminal growth

    # Present value of explicit forecast period
    pv = 0.0
    for year in range(1, num_years + 1):
        fcf_t = free_cash_flow * (1 + growth_rate) ** year
        pv += fcf_t / (1 + discount_rate) ** year

    # Terminal value
    fcf_terminal = free_cash_flow * (1 + growth_rate) ** num_years
    terminal_value = (fcf_terminal * (1 + terminal_growth_rate)) / (
        discount_rate - terminal_growth_rate
    )
    pv_terminal = terminal_value / (1 + discount_rate) ** num_years

    return pv + pv_terminal


def calculate_enhanced_dcf_value(
    fcf_history: list[float],
    growth_metrics: dict,
    wacc: float,
    market_cap: float,
    revenue_growth: float | None,
    config: ValuationConfig
) -> float:
    """Enhanced DCF with multi-stage growth and quality adjustments.

    Implements a three-stage DCF model:
    - Stage 1: High growth (years 1-3)
    - Stage 2: Transition to maturity (years 4-7)
    - Stage 3: Terminal perpetuity growth

    Args:
        fcf_history: Historical free cash flow values
        growth_metrics: Dictionary with growth rates
        wacc: Weighted average cost of capital
        market_cap: Current market capitalization
        revenue_growth: Revenue growth rate
        config: Valuation configuration

    Returns:
        Present value adjusted for FCF quality
    """
    if not fcf_history or fcf_history[0] <= 0:
        return 0

    # Analyze FCF trend and quality
    fcf_current = fcf_history[0]
    fcf_avg_3yr = sum(fcf_history[:min(3, len(fcf_history))]) / min(3, len(fcf_history))
    fcf_volatility = calculate_fcf_volatility(fcf_history)

    # Determine growth stages
    high_growth = min(revenue_growth or config.default_growth_rate, config.max_growth_cap)

    # Adjust for company maturity
    if market_cap > ValuationConstants.LARGE_CAP_THRESHOLD:
        high_growth = min(high_growth, 0.10)  # Cap large cap growth

    transition_growth = (high_growth + ValuationConstants.GDP_GROWTH_PROXY) / 2
    terminal_growth = min(ValuationConstants.GDP_GROWTH_PROXY, high_growth * 0.6)

    # Use conservative base FCF
    base_fcf = max(fcf_current, fcf_avg_3yr * 0.85)

    # Stage 1: High growth (years 1-3)
    pv = 0
    for year in range(1, config.dcf_high_growth_years + 1):
        fcf_projected = base_fcf * (1 + high_growth) ** year
        pv += fcf_projected / (1 + wacc) ** year

    # Stage 2: Transition (years 4-7)
    for year in range(config.dcf_high_growth_years + 1, config.dcf_transition_years + 1):
        years_in_transition = year - config.dcf_high_growth_years
        declining_rate = transition_growth * (config.dcf_transition_years + 1 - year) / 4

        fcf_projected = (
            base_fcf *
            (1 + high_growth) ** config.dcf_high_growth_years *
            (1 + declining_rate) ** years_in_transition
        )
        pv += fcf_projected / (1 + wacc) ** year

    # Stage 3: Terminal value
    final_fcf = (
        base_fcf *
        (1 + high_growth) ** config.dcf_high_growth_years *
        (1 + transition_growth) ** (config.dcf_transition_years - config.dcf_high_growth_years)
    )

    if wacc <= terminal_growth:
        terminal_growth = wacc * 0.8  # Adjust to valid range

    terminal_value = (final_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** config.dcf_transition_years

    # Quality adjustment based on FCF volatility
    quality_factor = max(0.7, 1 - (fcf_volatility * 0.5))

    return (pv + pv_terminal) * quality_factor


def calculate_dcf_scenarios(
    fcf_history: list[float],
    growth_metrics: dict,
    wacc: float,
    market_cap: float,
    revenue_growth: float | None,
    config: ValuationConfig
) -> dict:
    """Calculate DCF under multiple scenarios (bear, base, bull).

    Args:
        fcf_history: Historical free cash flow values
        growth_metrics: Dictionary with growth rates
        wacc: Weighted average cost of capital
        market_cap: Current market capitalization
        revenue_growth: Revenue growth rate
        config: Valuation configuration

    Returns:
        Dictionary with scenario values and expected value
    """
    scenarios = {
        'bear': {'growth_adj': 0.5, 'wacc_adj': 1.2, 'terminal_adj': 0.8},
        'base': {'growth_adj': 1.0, 'wacc_adj': 1.0, 'terminal_adj': 1.0},
        'bull': {'growth_adj': 1.5, 'wacc_adj': 0.9, 'terminal_adj': 1.2}
    }

    results = {}
    base_revenue_growth = revenue_growth or config.default_growth_rate

    for scenario, adjustments in scenarios.items():
        adjusted_revenue_growth = base_revenue_growth * adjustments['growth_adj']
        adjusted_wacc = wacc * adjustments['wacc_adj']

        results[scenario] = calculate_enhanced_dcf_value(
            fcf_history=fcf_history,
            growth_metrics=growth_metrics,
            wacc=adjusted_wacc,
            market_cap=market_cap,
            revenue_growth=adjusted_revenue_growth,
            config=config
        )

    # Probability-weighted expected value
    expected_value = (
        results['bear'] * 0.2 +
        results['base'] * 0.6 +
        results['bull'] * 0.2
    )

    return {
        'scenarios': results,
        'expected_value': expected_value,
        'range': results['bull'] - results['bear'],
        'upside': results['bull'],
        'downside': results['bear']
    }


def calculate_ev_ebitda_value(financial_metrics: list) -> float:
    """Implied equity value via median EV/EBITDA multiple.

    Uses historical median enterprise value multiple to estimate
    current implied equity value.

    Args:
        financial_metrics: Historical financial metrics

    Returns:
        Implied equity value, or 0 if insufficient data
    """
    if not financial_metrics:
        return 0

    current_metrics = financial_metrics[0]

    # Need both EV and EV/EBITDA ratio
    if not (current_metrics.enterprise_value and current_metrics.enterprise_value_to_ebitda_ratio):
        return 0

    if current_metrics.enterprise_value_to_ebitda_ratio == 0:
        return 0

    # Back out current EBITDA
    current_ebitda = current_metrics.enterprise_value / current_metrics.enterprise_value_to_ebitda_ratio

    # Calculate median multiple from history
    multiples = [
        m.enterprise_value_to_ebitda_ratio
        for m in financial_metrics
        if m.enterprise_value_to_ebitda_ratio and m.enterprise_value_to_ebitda_ratio > 0
    ]

    if not multiples:
        return 0

    median_multiple = statistics.median(multiples)

    # Apply median multiple to current EBITDA
    implied_ev = median_multiple * current_ebitda

    # Convert EV to equity value (EV = Market Cap + Net Debt)
    net_debt = (current_metrics.enterprise_value or 0) - (current_metrics.market_cap or 0)
    implied_equity = max(implied_ev - net_debt, 0)

    return implied_equity


def calculate_residual_income_value(
    market_cap: float | None,
    net_income: float | None,
    price_to_book_ratio: float | None,
    book_value_growth: float,
    config: ValuationConfig
) -> float:
    """Residual Income Model (Edwards-Bell-Ohlson).

    Formula:
        RI_t = NI_t - (Cost of Equity × Book Value_{t-1})
        Value = Book Value + PV(Future Residual Income)

    Args:
        market_cap: Current market capitalization
        net_income: Current net income
        price_to_book_ratio: Price to book value ratio
        book_value_growth: Expected book value growth rate
        config: Valuation configuration

    Returns:
        Intrinsic value with margin of safety, or 0 if invalid
    """
    # Validate inputs
    if not (market_cap and net_income and price_to_book_ratio and price_to_book_ratio > 0):
        return 0

    # Calculate book value
    book_value = market_cap / price_to_book_ratio

    # Calculate current residual income
    residual_income = net_income - (config.discount_rate * book_value)

    if residual_income <= 0:
        return 0

    # Project future residual income
    pv_ri = 0.0
    for year in range(1, config.forecast_years + 1):
        ri_t = residual_income * (1 + book_value_growth) ** year
        pv_ri += ri_t / (1 + config.discount_rate) ** year

    # Terminal value of residual income
    terminal_ri = residual_income * (1 + book_value_growth) ** (config.forecast_years + 1)
    terminal_value = terminal_ri / (config.discount_rate - config.terminal_growth_rate)
    pv_terminal = terminal_value / (1 + config.discount_rate) ** config.forecast_years

    intrinsic_value = book_value + pv_ri + pv_terminal

    # Apply margin of safety
    return intrinsic_value * (1 - config.residual_income_margin)


# ==============================================================================
# MAIN AGENT FUNCTION
# ==============================================================================

def valuation_analyst_agent(
    state: AgentState,
    agent_id: str = "valuation_analyst_agent",
    config: ValuationConfig | None = None
):
    """Run valuation across tickers and write signals back to state.

    Implements four valuation methodologies with weighted aggregation:
    1. Enhanced DCF with multi-stage growth
    2. Owner earnings (Buffett approach)
    3. EV/EBITDA multiples
    4. Residual income model

    Args:
        state: Agent state containing tickers and configuration
        agent_id: Identifier for this agent
        config: Optional valuation configuration (uses defaults if None)

    Returns:
        Updated state with valuation analysis results
    """
    # Initialize configuration
    if config is None:
        config = ValuationConfig()

    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")

    valuation_analysis: dict[str, dict] = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching financial data")

        # Fetch historical financial metrics
        financial_metrics = get_financial_metrics(
            ticker=ticker,
            end_date=end_date,
            period="ttm",
            limit=8,
            api_key=api_key,
        )

        if not financial_metrics:
            progress.update_status(agent_id, ticker, "Failed: No financial metrics found")
            continue

        most_recent_metrics = financial_metrics[0]

        # Fetch comprehensive line items
        progress.update_status(agent_id, ticker, "Gathering financial line items")

        line_items = search_line_items(
            ticker=ticker,
            line_items=[
                "free_cash_flow",
                "net_income",
                "depreciation_and_amortization",
                "capital_expenditure",
                "working_capital",
                "total_debt",
                "cash_and_equivalents",
                "interest_expense",
                "revenue",
                "operating_income",
                "ebit",
                "ebitda"
            ],
            end_date=end_date,
            period="ttm",
            limit=8,
            api_key=api_key,
        )

        if len(line_items) < 2:
            progress.update_status(agent_id, ticker, "Failed: Insufficient financial line items")
            continue

        # Validate data quality
        is_valid, warnings = validate_financial_data(
            most_recent_metrics, line_items, ticker, agent_id
        )

        if not is_valid:
            progress.update_status(
                agent_id, ticker,
                f"Failed: Data quality check failed ({len(warnings)} critical issues)"
            )
            continue

        li_curr, li_prev = line_items[0], line_items[1]

        # Calculate working capital change with proper handling
        wc_change = 0.0
        if li_curr.working_capital is not None and li_prev.working_capital is not None:
            wc_change = li_curr.working_capital - li_prev.working_capital
            progress.update_status(
                agent_id, ticker,
                f"Working capital change: ${wc_change:,.0f}"
            )
        else:
            progress.update_status(
                agent_id, ticker,
                "Warning: Working capital data unavailable, using 0"
            )

        # =====================================================================
        # VALUATION CALCULATIONS
        # =====================================================================

        progress.update_status(agent_id, ticker, "Calculating WACC and DCF scenarios")

        # Calculate WACC
        wacc = calculate_wacc(
            market_cap=most_recent_metrics.market_cap or 0,
            total_debt=getattr(li_curr, 'total_debt', None),
            cash=getattr(li_curr, 'cash_and_equivalents', None),
            interest_coverage=most_recent_metrics.interest_coverage,
            debt_to_equity=most_recent_metrics.debt_to_equity,
            ticker=ticker,
            financial_metrics=financial_metrics,
            config=config
        )

        progress.update_status(agent_id, ticker, f"WACC calculated: {wacc:.2%}")

        # Prepare FCF history
        fcf_history = [
            li.free_cash_flow for li in line_items
            if hasattr(li, 'free_cash_flow') and li.free_cash_flow is not None
        ]

        # Enhanced DCF with scenarios
        dcf_results = calculate_dcf_scenarios(
            fcf_history=fcf_history,
            growth_metrics={
                'revenue_growth': most_recent_metrics.revenue_growth,
                'fcf_growth': most_recent_metrics.free_cash_flow_growth,
                'earnings_growth': most_recent_metrics.earnings_growth
            },
            wacc=wacc,
            market_cap=most_recent_metrics.market_cap or 0,
            revenue_growth=most_recent_metrics.revenue_growth,
            config=config
        )

        dcf_val = dcf_results['expected_value']

        # Owner Earnings
        progress.update_status(agent_id, ticker, "Calculating owner earnings value")

        owner_val = safe_calculate_valuation(
            calc_func=calculate_owner_earnings_value,
            method_name="Owner Earnings",
            agent_id=agent_id,
            ticker=ticker,
            net_income=li_curr.net_income,
            depreciation=li_curr.depreciation_and_amortization,
            capex=li_curr.capital_expenditure,
            working_capital_change=wc_change,
            growth_rate=most_recent_metrics.earnings_growth or config.default_growth_rate,
            config=config
        )

        # EV/EBITDA Valuation
        progress.update_status(agent_id, ticker, "Calculating EV/EBITDA value")

        ev_ebitda_val = safe_calculate_valuation(
            calc_func=calculate_ev_ebitda_value,
            method_name="EV/EBITDA",
            agent_id=agent_id,
            ticker=ticker,
            financial_metrics=financial_metrics
        )

        # Residual Income Model
        progress.update_status(agent_id, ticker, "Calculating residual income value")

        rim_val = safe_calculate_valuation(
            calc_func=calculate_residual_income_value,
            method_name="Residual Income",
            agent_id=agent_id,
            ticker=ticker,
            market_cap=most_recent_metrics.market_cap,
            net_income=li_curr.net_income,
            price_to_book_ratio=most_recent_metrics.price_to_book_ratio,
            book_value_growth=most_recent_metrics.book_value_growth or config.terminal_growth_rate,
            config=config
        )

        # =====================================================================
        # AGGREGATE RESULTS AND GENERATE SIGNAL
        # =====================================================================

        market_cap = get_market_cap(ticker, end_date, api_key=api_key)
        if not market_cap:
            progress.update_status(agent_id, ticker, "Failed: Market cap unavailable")
            continue

        # Configure method weights
        method_values = {
            "dcf": {"value": dcf_val, "weight": config.dcf_weight},
            "owner_earnings": {"value": owner_val, "weight": config.owner_earnings_weight},
            "ev_ebitda": {"value": ev_ebitda_val, "weight": config.ev_ebitda_weight},
            "residual_income": {"value": rim_val, "weight": config.residual_income_weight},
        }

        # Calculate total weight (only from valid methods)
        total_weight = sum(
            v["weight"] for v in method_values.values() if v["value"] > 0
        )

        if total_weight == 0:
            progress.update_status(agent_id, ticker, "Failed: All valuation methods returned zero")
            continue

        # Calculate valuation gaps
        for method, vals in method_values.items():
            if vals["value"] > 0:
                vals["gap"] = (vals["value"] - market_cap) / market_cap
            else:
                vals["gap"] = None

        # Calculate weighted gap
        weighted_gap = sum(
            v["weight"] * v["gap"]
            for v in method_values.values()
            if v["gap"] is not None
        ) / total_weight

        # Generate signal
        if weighted_gap > config.bullish_threshold:
            signal = "bullish"
        elif weighted_gap < config.bearish_threshold:
            signal = "bearish"
        else:
            signal = "neutral"

        # Calculate confidence
        confidence = round(min(abs(weighted_gap) / 0.30 * 100, 100))

        # Build reasoning with enhanced DCF details
        reasoning = {}

        for method, vals in method_values.items():
            if vals["value"] > 0:
                base_details = (
                    f"Value: ${vals['value']:,.2f}, "
                    f"Market Cap: ${market_cap:,.2f}, "
                    f"Gap: {vals['gap']:.1%}, "
                    f"Weight: {vals['weight']*100:.0f}%"
                )

                # Add enhanced DCF details
                if method == "dcf":
                    enhanced_details = (
                        f"{base_details}\n"
                        f"  WACC: {wacc:.1%}, "
                        f"Bear: ${dcf_results['downside']:,.2f}, "
                        f"Bull: ${dcf_results['upside']:,.2f}, "
                        f"Range: ${dcf_results['range']:,.2f}"
                    )
                else:
                    enhanced_details = base_details

                # Determine method-specific signal
                if vals["gap"] and vals["gap"] > config.bullish_threshold:
                    method_signal = "bullish"
                elif vals["gap"] and vals["gap"] < config.bearish_threshold:
                    method_signal = "bearish"
                else:
                    method_signal = "neutral"

                reasoning[f"{method}_analysis"] = {
                    "signal": method_signal,
                    "details": enhanced_details,
                }

        # Add DCF scenario summary
        reasoning["dcf_scenario_analysis"] = {
            "bear_case": f"${dcf_results['downside']:,.2f}",
            "base_case": f"${dcf_results['scenarios']['base']:,.2f}",
            "bull_case": f"${dcf_results['upside']:,.2f}",
            "wacc_used": f"{wacc:.1%}",
            "fcf_periods_analyzed": len(fcf_history)
        }

        # Add data quality summary
        if warnings:
            reasoning["data_quality_notes"] = {
                "warnings_count": len(warnings),
                "issues": warnings[:3]  # Include first 3 warnings
            }

        # Store analysis
        valuation_analysis[ticker] = {
            "signal": signal,
            "confidence": confidence,
            "reasoning": reasoning,
        }

        progress.update_status(
            agent_id, ticker, "Done",
            analysis=json.dumps(reasoning, indent=4)
        )

    # Emit message for LLM tool chain
    msg = HumanMessage(content=json.dumps(valuation_analysis), name=agent_id)

    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(valuation_analysis, "Valuation Analysis Agent")

    # Add signals to state
    state["data"]["analyst_signals"][agent_id] = valuation_analysis

    progress.update_status(agent_id, None, "Done")

    return {"messages": [msg], "data": data}
