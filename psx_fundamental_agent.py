"""
PSX Fundamental Analysis Agent

Validates momentum signals with financial health assessment for PSX stocks and commodities.
Performs comprehensive fundamental analysis including valuation, financial health, growth,
and momentum metrics to generate actionable investment recommendations.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import yfinance as yf

# Import PSX company financials store for real data
try:
    from psx_company_financials_store import PSXCompanyFinancialsStore
    PSX_REAL_DATA_AVAILABLE = True
except ImportError:
    PSXCompanyFinancialsStore = None
    PSX_REAL_DATA_AVAILABLE = False


class Recommendation(Enum):
    """Investment recommendation"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class Confidence(Enum):
    """Analysis confidence level"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RedFlagSeverity(Enum):
    """Severity of red flags"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RedFlagAction(Enum):
    """Action to take when red flag is detected"""
    AUTO_REJECT = "auto_reject"
    REDUCE_SCORE_50PCT = "reduce_score_50pct"
    REDUCE_SCORE_30PCT = "reduce_score_30pct"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ValuationMetrics:
    """Valuation metrics for a stock"""
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    enterprise_value: Optional[float] = None


@dataclass
class FinancialHealthMetrics:
    """Financial health metrics"""
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    roa: Optional[float] = None
    roe: Optional[float] = None
    interest_coverage: Optional[float] = None
    operating_cash_flow: Optional[float] = None


@dataclass
class GrowthMetrics:
    """Growth metrics"""
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None
    revenue_cagr_3y: Optional[float] = None
    earnings_cagr_3y: Optional[float] = None
    margin_trend: Optional[str] = None  # "expanding", "stable", "contracting"
    margin_change_pct: Optional[float] = None


@dataclass
class MomentumMetrics:
    """Earnings and estimate momentum"""
    earnings_surprise_pct: Optional[float] = None
    estimate_revision_trend: Optional[float] = None  # -1 to 1
    upcoming_catalysts: List[str] = field(default_factory=list)


@dataclass
class RedFlag:
    """Detected red flag"""
    flag: str
    severity: RedFlagSeverity
    action: RedFlagAction
    description: str


@dataclass
class FundamentalScore:
    """Complete fundamental analysis result"""
    symbol: str
    fundamental_score: float  # 0-100 scale
    recommendation: Recommendation
    confidence: Confidence

    valuation: ValuationMetrics
    financial_health: FinancialHealthMetrics
    growth_metrics: GrowthMetrics
    momentum_metrics: MomentumMetrics

    red_flags: List[RedFlag] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)

    analyst_consensus: Optional[str] = None
    fair_value: Optional[float] = None
    upside_pct: Optional[float] = None

    data_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data_quality: float = 1.0  # 0-1 scale

    # Component scores (0-100)
    valuation_score: float = 50.0
    health_score: float = 50.0
    growth_score: float = 50.0
    momentum_score: float = 50.0

    processing_time_ms: Optional[int] = None
    analysis_mode: str = "quick"  # "quick" or "deep"


class PSXFundamentalAgent:
    """
    Fundamental analysis agent for Pakistan Stock Exchange

    Validates momentum signals with comprehensive financial analysis:
    - Valuation: PE, PB, Dividend Yield, EV/EBITDA
    - Financial Health: Debt ratios, liquidity, profitability
    - Growth: Revenue/earnings growth, margin trends
    - Momentum: Earnings surprises, analyst revisions
    """

    # Red flag definitions
    RED_FLAGS = {
        "debt_spike": {
            "severity": RedFlagSeverity.HIGH,
            "action": RedFlagAction.AUTO_REJECT,
            "description": "Debt-to-equity > 1.5 with >50% YoY growth"
        },
        "declining_margins": {
            "severity": RedFlagSeverity.MEDIUM,
            "action": RedFlagAction.REDUCE_SCORE_50PCT,
            "description": "Gross margin down >5% for 2+ quarters"
        },
        "negative_cash_flow": {
            "severity": RedFlagSeverity.HIGH,
            "action": RedFlagAction.AUTO_REJECT,
            "description": "Negative operating cash flow for 2+ quarters"
        },
        "revenue_decline": {
            "severity": RedFlagSeverity.MEDIUM,
            "action": RedFlagAction.REDUCE_SCORE_30PCT,
            "description": "Revenue growth < -10% YoY"
        },
        "low_liquidity": {
            "severity": RedFlagSeverity.MEDIUM,
            "action": RedFlagAction.REDUCE_SCORE_30PCT,
            "description": "Current ratio < 1.0 indicating liquidity issues"
        },
        "negative_equity": {
            "severity": RedFlagSeverity.CRITICAL,
            "action": RedFlagAction.AUTO_REJECT,
            "description": "Negative shareholder equity"
        }
    }

    # PSX sector-specific adjustments
    PSX_SECTOR_BENCHMARKS = {
        "Energy": {
            "pe_avg": 5.0,
            "pb_avg": 1.2,
            "dividend_yield_avg": 8.0,
            "debt_to_equity_avg": 0.3
        },
        "Banking": {
            "pe_avg": 4.0,
            "pb_avg": 0.8,
            "dividend_yield_avg": 6.0,
            "debt_to_equity_avg": 5.0  # Banks naturally have higher leverage
        },
        "Cement": {
            "pe_avg": 6.0,
            "pb_avg": 1.5,
            "dividend_yield_avg": 5.0,
            "debt_to_equity_avg": 0.6
        },
        "Fertilizer": {
            "pe_avg": 7.0,
            "pb_avg": 1.8,
            "dividend_yield_avg": 4.5,
            "debt_to_equity_avg": 0.4
        },
        "Default": {
            "pe_avg": 6.0,
            "pb_avg": 1.5,
            "dividend_yield_avg": 5.0,
            "debt_to_equity_avg": 0.5
        }
    }

    def __init__(self, cache_ttl_hours: int = 24, price_store=None):
        """
        Initialize the fundamental analysis agent

        Args:
            cache_ttl_hours: Hours to cache fundamental data before refresh
            price_store: Optional PSXPriceStore instance for price data
        """
        self.cache_ttl_hours = cache_ttl_hours
        self.price_store = price_store
        self.metrics_cache: Dict[str, Tuple[Dict, datetime]] = {}

        # Initialize company financials store for real PSX data
        self.financials_store = None
        self.using_real_data = False

        if PSX_REAL_DATA_AVAILABLE:
            try:
                self.financials_store = PSXCompanyFinancialsStore()
                self.using_real_data = True
                print("✓ Fundamental Agent: Using REAL PSX financial data from company pages")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize PSX financials store: {e}")
                print("  Falling back to mock data for enhanced metrics")
        else:
            print("⚠ PSX Company Financials Store not available")
            print("  Using mock data for enhanced metrics")

    def quick_analysis(self, symbol: str) -> FundamentalScore:
        """
        Fast validation using cached/computed metrics (< 2 minutes)

        Used when Technical + Sentiment agents already flagged a signal.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            FundamentalScore with recommendation
        """
        start_time = datetime.now()

        # Check cache first
        cached_data = self._get_cached_metrics(symbol)

        if cached_data:
            metrics = cached_data
            data_age_hours = (datetime.now() - metrics.get('_cached_at', datetime.now())).total_seconds() / 3600
            confidence = Confidence.HIGH if data_age_hours < 24 else Confidence.MEDIUM
        else:
            # Fetch fresh data
            metrics = self._fetch_fundamentals(symbol)
            self._cache_metrics(symbol, metrics)
            confidence = Confidence.MEDIUM

        # Calculate component scores
        valuation_score = self._score_valuation(metrics)
        health_score = self._score_financial_health(metrics)
        growth_score = self._score_growth(metrics)
        momentum_score = self._score_momentum(metrics)

        # Calculate composite fundamental score
        fundamental_score = self._calculate_fundamental_score(
            valuation_score, health_score, growth_score, momentum_score
        )

        # Check red flags
        red_flags = self._check_red_flags(metrics)

        # Apply red flag penalties
        fundamental_score = self._apply_red_flag_penalties(fundamental_score, red_flags)

        # Generate recommendation
        recommendation = self._generate_recommendation(fundamental_score, red_flags)

        # Calculate upside/downside
        current_price = metrics.get('current_price', 0)
        fair_value = self._calculate_fair_value(metrics)
        upside_pct = None
        if fair_value and current_price and current_price > 0:
            upside_pct = ((fair_value - current_price) / current_price) * 100

        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return FundamentalScore(
            symbol=symbol,
            fundamental_score=round(fundamental_score, 1),
            recommendation=recommendation,
            confidence=confidence,
            valuation=self._extract_valuation_metrics(metrics),
            financial_health=self._extract_health_metrics(metrics),
            growth_metrics=self._extract_growth_metrics(metrics),
            momentum_metrics=self._extract_momentum_metrics(metrics),
            red_flags=red_flags,
            catalysts=self._identify_catalysts(metrics),
            analyst_consensus=metrics.get('analyst_consensus'),
            fair_value=fair_value,
            upside_pct=upside_pct,
            data_quality=self._assess_data_quality(metrics),
            valuation_score=valuation_score,
            health_score=health_score,
            growth_score=growth_score,
            momentum_score=momentum_score,
            processing_time_ms=processing_time_ms,
            analysis_mode="quick"
        )

    def deep_analysis(self, symbol: str) -> FundamentalScore:
        """
        Comprehensive research with fresh data fetching (5-10 minutes)

        Used for weekly scans or conflicting signals.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            FundamentalScore with detailed analysis
        """
        start_time = datetime.now()

        # Always fetch fresh data for deep analysis
        metrics = self._fetch_fundamentals(symbol, force_refresh=True)

        # Perform comprehensive analysis
        metrics = self._enhance_with_peer_comparison(symbol, metrics)
        metrics = self._enhance_with_dcf_valuation(metrics)

        # Calculate component scores with enhanced data
        valuation_score = self._score_valuation(metrics)
        health_score = self._score_financial_health(metrics)
        growth_score = self._score_growth(metrics)
        momentum_score = self._score_momentum(metrics)

        # Calculate composite fundamental score
        fundamental_score = self._calculate_fundamental_score(
            valuation_score, health_score, growth_score, momentum_score
        )

        # Check red flags
        red_flags = self._check_red_flags(metrics)

        # Apply red flag penalties
        fundamental_score = self._apply_red_flag_penalties(fundamental_score, red_flags)

        # Generate recommendation
        recommendation = self._generate_recommendation(fundamental_score, red_flags)

        # Calculate upside/downside
        current_price = metrics.get('current_price', 0)
        fair_value = metrics.get('dcf_fair_value') or self._calculate_fair_value(metrics)
        upside_pct = None
        if fair_value and current_price and current_price > 0:
            upside_pct = ((fair_value - current_price) / current_price) * 100

        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return FundamentalScore(
            symbol=symbol,
            fundamental_score=round(fundamental_score, 1),
            recommendation=recommendation,
            confidence=Confidence.HIGH,  # Deep analysis always high confidence
            valuation=self._extract_valuation_metrics(metrics),
            financial_health=self._extract_health_metrics(metrics),
            growth_metrics=self._extract_growth_metrics(metrics),
            momentum_metrics=self._extract_momentum_metrics(metrics),
            red_flags=red_flags,
            catalysts=self._identify_catalysts(metrics),
            analyst_consensus=metrics.get('analyst_consensus'),
            fair_value=fair_value,
            upside_pct=upside_pct,
            data_quality=self._assess_data_quality(metrics),
            valuation_score=valuation_score,
            health_score=health_score,
            growth_score=growth_score,
            momentum_score=momentum_score,
            processing_time_ms=processing_time_ms,
            analysis_mode="deep"
        )

    def analyze_symbol(self, symbol: str, mode: str = "quick") -> FundamentalScore:
        """
        Analyze a symbol (convenience method)

        Args:
            symbol: Stock symbol to analyze
            mode: "quick" or "deep"

        Returns:
            FundamentalScore
        """
        if mode == "deep":
            return self.deep_analysis(symbol)
        else:
            return self.quick_analysis(symbol)

    def screen_universe(self, symbols: List[str]) -> Dict[str, FundamentalScore]:
        """
        Screen multiple stocks for fundamental quality

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to FundamentalScore
        """
        results = {}

        for symbol in symbols:
            try:
                score = self.quick_analysis(symbol)
                results[symbol] = score
            except Exception as e:
                print(f"Error analyzing {symbol}: {str(e)}")

        return results

    # ===================================================================
    # SCORING METHODS
    # ===================================================================

    def _calculate_fundamental_score(
        self,
        valuation_score: float,
        health_score: float,
        growth_score: float,
        momentum_score: float
    ) -> float:
        """
        Calculate weighted composite fundamental score

        Weights:
        - Valuation: 30%
        - Financial Health: 40%
        - Growth: 20%
        - Momentum: 10%
        """
        weights = {
            "valuation": 0.30,
            "health": 0.40,
            "growth": 0.20,
            "momentum": 0.10
        }

        composite = (
            valuation_score * weights["valuation"] +
            health_score * weights["health"] +
            growth_score * weights["growth"] +
            momentum_score * weights["momentum"]
        )

        return composite

    def _score_valuation(self, metrics: Dict) -> float:
        """
        Score valuation metrics (0-100)
        Lower valuation = higher score (value investing bias)
        """
        scores = []

        # PE Ratio (lower is better, PSX average ~6)
        pe = metrics.get('pe_ratio')
        if pe and pe > 0:
            # PE < 5 = high score, PE > 15 = low score
            pe_score = max(0, min(100, 100 - ((pe - 5) * 10)))
            scores.append(pe_score)

        # PB Ratio (lower is better, PSX average ~1.5)
        pb = metrics.get('pb_ratio')
        if pb and pb > 0:
            # PB < 1 = high score, PB > 3 = low score
            pb_score = max(0, min(100, 100 - ((pb - 1) * 33)))
            scores.append(pb_score)

        # Dividend Yield (higher is better)
        dy = metrics.get('dividend_yield')
        if dy and dy >= 0:
            # DY > 5% = high score
            dy_score = min(100, dy * 10)
            scores.append(dy_score)

        # EV/EBITDA (lower is better)
        ev_ebitda = metrics.get('ev_ebitda')
        if ev_ebitda and ev_ebitda > 0:
            # EV/EBITDA < 5 = high score, > 12 = low score
            ev_score = max(0, min(100, 100 - ((ev_ebitda - 5) * 12)))
            scores.append(ev_score)

        if not scores:
            return 50.0  # Neutral if no valuation data

        return np.mean(scores)

    def _score_financial_health(self, metrics: Dict) -> float:
        """
        Score financial health (0-100)
        Balance sheet strength and profitability
        """
        scores = []

        # Debt-to-Equity (lower is better, except for banks)
        debt_to_equity = metrics.get('debt_to_equity')
        if debt_to_equity is not None:
            sector = metrics.get('sector', 'Default')
            if sector == 'Banking':
                # Banks naturally have higher leverage
                debt_score = max(0, 100 - max(0, (debt_to_equity - 5) * 10))
            else:
                # Lower is better
                debt_score = max(0, 100 - (debt_to_equity * 50))
            scores.append(debt_score)

        # Current Ratio (higher is better, > 1.5 is good)
        current_ratio = metrics.get('current_ratio')
        if current_ratio and current_ratio > 0:
            liquidity_score = min(100, current_ratio * 50)
            scores.append(liquidity_score)

        # ROA (higher is better, >10% is excellent)
        roa = metrics.get('roa')
        if roa is not None:
            roa_score = min(100, max(0, roa * 5))
            scores.append(roa_score)

        # ROE (higher is better, >15% is excellent)
        roe = metrics.get('roe')
        if roe is not None:
            roe_score = min(100, max(0, roe * 4))
            scores.append(roe_score)

        # Interest Coverage (higher is better, >5 is safe)
        interest_coverage = metrics.get('interest_coverage')
        if interest_coverage and interest_coverage > 0:
            coverage_score = min(100, interest_coverage * 20)
            scores.append(coverage_score)

        # Operating Cash Flow (positive is essential)
        ocf = metrics.get('operating_cash_flow')
        if ocf is not None:
            if ocf > 0:
                scores.append(80)  # Positive cash flow is good
            else:
                scores.append(20)  # Negative is concerning

        if not scores:
            return 50.0  # Neutral if no health data

        return np.mean(scores)

    def _score_growth(self, metrics: Dict) -> float:
        """
        Score growth trajectory (0-100)
        Revenue and earnings growth
        """
        scores = []

        # Revenue Growth YoY
        revenue_growth = metrics.get('revenue_growth_yoy')
        if revenue_growth is not None:
            # 15%+ growth = high score
            revenue_score = min(100, max(0, 50 + (revenue_growth * 3)))
            scores.append(revenue_score)

        # Earnings Growth YoY
        earnings_growth = metrics.get('earnings_growth_yoy')
        if earnings_growth is not None:
            # 20%+ growth = high score
            earnings_score = min(100, max(0, 50 + (earnings_growth * 2.5)))
            scores.append(earnings_score)

        # Revenue CAGR 3Y
        revenue_cagr = metrics.get('revenue_cagr_3y')
        if revenue_cagr is not None:
            cagr_score = min(100, max(0, 50 + (revenue_cagr * 3)))
            scores.append(cagr_score)

        # Margin Trend
        margin_trend = metrics.get('margin_trend')
        if margin_trend == 'expanding':
            scores.append(80)
        elif margin_trend == 'stable':
            scores.append(60)
        elif margin_trend == 'contracting':
            scores.append(30)

        if not scores:
            return 50.0  # Neutral if no growth data

        return np.mean(scores)

    def _score_momentum(self, metrics: Dict) -> float:
        """
        Score earnings momentum (0-100)
        Earnings surprises and estimate revisions
        """
        scores = []

        # Earnings Surprise
        surprise = metrics.get('earnings_surprise_pct')
        if surprise is not None:
            # Positive surprise = good
            surprise_score = min(100, max(0, 50 + (surprise * 2)))
            scores.append(surprise_score)

        # Estimate Revisions (-1 to 1)
        revisions = metrics.get('estimate_revision_trend')
        if revisions is not None:
            # Upgrades = good
            revision_score = 50 + (revisions * 50)
            scores.append(revision_score)

        # Upcoming Catalysts
        catalysts = metrics.get('upcoming_catalysts', [])
        catalyst_score = min(100, len(catalysts) * 20)  # Max 5 catalysts
        if catalyst_score > 0:
            scores.append(catalyst_score)

        if not scores:
            return 50.0  # Neutral if no momentum data

        return np.mean(scores)

    # ===================================================================
    # RED FLAG DETECTION
    # ===================================================================

    def _check_red_flags(self, metrics: Dict) -> List[RedFlag]:
        """
        Check for red flags in financial data

        Returns:
            List of detected RedFlag objects
        """
        flags = []

        # Debt Spike
        debt_to_equity = metrics.get('debt_to_equity', 0)
        debt_growth = metrics.get('debt_growth_yoy', 0)
        if debt_to_equity > 1.5 and debt_growth > 50:
            flags.append(RedFlag(
                flag="debt_spike",
                severity=self.RED_FLAGS["debt_spike"]["severity"],
                action=self.RED_FLAGS["debt_spike"]["action"],
                description=f"D/E ratio {debt_to_equity:.2f} with {debt_growth:.1f}% growth"
            ))

        # Declining Margins
        margin_change = metrics.get('margin_change_pct', 0)
        quarters_declining = metrics.get('quarters_margin_declining', 0)
        if margin_change < -5 and quarters_declining >= 2:
            flags.append(RedFlag(
                flag="declining_margins",
                severity=self.RED_FLAGS["declining_margins"]["severity"],
                action=self.RED_FLAGS["declining_margins"]["action"],
                description=f"Margins down {abs(margin_change):.1f}% for {quarters_declining} quarters"
            ))

        # Negative Cash Flow
        ocf = metrics.get('operating_cash_flow', 0)
        quarters_negative = metrics.get('quarters_negative_ocf', 0)
        if ocf < 0 and quarters_negative >= 2:
            flags.append(RedFlag(
                flag="negative_cash_flow",
                severity=self.RED_FLAGS["negative_cash_flow"]["severity"],
                action=self.RED_FLAGS["negative_cash_flow"]["action"],
                description=f"Negative operating cash flow for {quarters_negative} quarters"
            ))

        # Revenue Decline
        revenue_growth = metrics.get('revenue_growth_yoy', 0)
        if revenue_growth < -10:
            flags.append(RedFlag(
                flag="revenue_decline",
                severity=self.RED_FLAGS["revenue_decline"]["severity"],
                action=self.RED_FLAGS["revenue_decline"]["action"],
                description=f"Revenue declined {abs(revenue_growth):.1f}% YoY"
            ))

        # Low Liquidity
        current_ratio = metrics.get('current_ratio', 2.0)
        if current_ratio < 1.0:
            flags.append(RedFlag(
                flag="low_liquidity",
                severity=self.RED_FLAGS["low_liquidity"]["severity"],
                action=self.RED_FLAGS["low_liquidity"]["action"],
                description=f"Current ratio {current_ratio:.2f} < 1.0"
            ))

        # Negative Equity
        equity = metrics.get('total_equity', 1)
        if equity < 0:
            flags.append(RedFlag(
                flag="negative_equity",
                severity=self.RED_FLAGS["negative_equity"]["severity"],
                action=self.RED_FLAGS["negative_equity"]["action"],
                description="Negative shareholder equity"
            ))

        return flags

    def _apply_red_flag_penalties(self, score: float, red_flags: List[RedFlag]) -> float:
        """
        Apply penalties based on red flags

        Args:
            score: Base fundamental score
            red_flags: List of detected red flags

        Returns:
            Adjusted score
        """
        adjusted_score = score

        for flag in red_flags:
            if flag.action == RedFlagAction.AUTO_REJECT:
                adjusted_score = min(adjusted_score, 30)  # Cap at 30
            elif flag.action == RedFlagAction.REDUCE_SCORE_50PCT:
                adjusted_score *= 0.5
            elif flag.action == RedFlagAction.REDUCE_SCORE_30PCT:
                adjusted_score *= 0.7

        return adjusted_score

    # ===================================================================
    # DATA FETCHING AND CACHING
    # ===================================================================

    def _fetch_fundamentals(self, symbol: str, force_refresh: bool = False) -> Dict:
        """
        Fetch fundamental data for a symbol

        In production, this would fetch from:
        - PSX website (quarterly/annual reports)
        - SECP filings
        - Bloomberg/Reuters APIs

        For now, uses yfinance and generates mock data for missing fields.

        Args:
            symbol: Stock symbol
            force_refresh: Force fresh data fetch

        Returns:
            Dictionary with fundamental metrics
        """
        metrics = {}

        try:
            # Fetch from yfinance
            ticker_symbol = f"{symbol}.KA"
            ticker = yf.Ticker(ticker_symbol)

            # Get info
            info = ticker.info

            # Current price
            if self.price_store:
                df = self.price_store.get_prices(symbol, days=5)
                if not df.empty:
                    metrics['current_price'] = df['Close'].iloc[-1]
            else:
                metrics['current_price'] = info.get('currentPrice') or info.get('regularMarketPrice', 0)

            # Valuation metrics
            metrics['pe_ratio'] = info.get('trailingPE') or info.get('forwardPE')
            metrics['pb_ratio'] = info.get('priceToBook')
            metrics['dividend_yield'] = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
            metrics['ev_ebitda'] = info.get('enterpriseToEbitda')
            metrics['price_to_sales'] = info.get('priceToSalesTrailing12Months')
            metrics['enterprise_value'] = info.get('enterpriseValue')

            # Financial health metrics
            metrics['debt_to_equity'] = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else None
            metrics['current_ratio'] = info.get('currentRatio')
            metrics['quick_ratio'] = info.get('quickRatio')
            metrics['roa'] = info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else None
            metrics['roe'] = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None

            # Growth metrics
            metrics['revenue_growth_yoy'] = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else None
            metrics['earnings_growth'] = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else None

            # Sector
            metrics['sector'] = self._map_sector(info.get('sector', 'Default'))

            # Get financial statements for more detailed analysis
            try:
                balance_sheet = ticker.balance_sheet
                if not balance_sheet.empty and balance_sheet.shape[1] >= 2:
                    # Most recent two periods
                    recent = balance_sheet.iloc[:, 0]
                    previous = balance_sheet.iloc[:, 1]

                    # Operating cash flow
                    cash_flow = ticker.cashflow
                    if not cash_flow.empty:
                        if 'Operating Cash Flow' in cash_flow.index:
                            metrics['operating_cash_flow'] = cash_flow.loc['Operating Cash Flow'].iloc[0]
                        elif 'Total Cash From Operating Activities' in cash_flow.index:
                            metrics['operating_cash_flow'] = cash_flow.loc['Total Cash From Operating Activities'].iloc[0]

                    # Total equity
                    if 'Total Stockholder Equity' in balance_sheet.index:
                        metrics['total_equity'] = recent['Total Stockholder Equity']
                    elif 'Stockholders Equity' in balance_sheet.index:
                        metrics['total_equity'] = recent['Stockholders Equity']
            except:
                pass

            # Add enhanced metrics: Try real PSX data first, fallback to mock
            psx_real_metrics = self._get_psx_real_metrics(symbol)

            if psx_real_metrics:
                metrics.update(psx_real_metrics)
                metrics['_data_source'] = 'PSX_Real_Data'
            else:
                # Fallback to mock data
                metrics.update(self._generate_mock_enhanced_metrics(symbol))
                metrics['_data_source'] = 'Mock_Data'

            metrics['_cached_at'] = datetime.now()

        except Exception as e:
            print(f"Warning: Error fetching fundamentals for {symbol}: {str(e)}")
            # Return default metrics
            metrics = self._generate_mock_enhanced_metrics(symbol)
            metrics['current_price'] = 100
            metrics['_cached_at'] = datetime.now()

        return metrics

    def _get_psx_real_metrics(self, symbol: str) -> Optional[Dict]:
        """
        Get real financial metrics from PSX company pages

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with real financial metrics, or None if not available
        """
        if not self.using_real_data or not self.financials_store:
            return None

        try:
            # Try to get existing data
            latest_metrics = self.financials_store.get_latest_metrics(symbol)

            if not latest_metrics:
                # Fetch and store new data
                print(f"  Fetching fresh PSX data for {symbol}...")
                financials = self.financials_store.fetch_and_store(symbol)

                if financials:
                    latest_metrics = self.financials_store.get_latest_metrics(symbol)

            if not latest_metrics:
                return None

            # Convert PSX data to format expected by fundamental agent
            psx_metrics = {}

            # Revenue and profit metrics
            if 'revenue' in latest_metrics:
                psx_metrics['psx_revenue'] = latest_metrics['revenue']

            if 'profit_after_tax' in latest_metrics:
                psx_metrics['psx_profit_after_tax'] = latest_metrics['profit_after_tax']

            if 'eps' in latest_metrics:
                psx_metrics['psx_eps'] = latest_metrics['eps']

            # Growth rates (REAL data, not mock!)
            if 'revenue_growth' in latest_metrics:
                psx_metrics['revenue_cagr_3y'] = latest_metrics['revenue_growth']
                psx_metrics['earnings_growth_yoy'] = latest_metrics.get('profit_growth', 0)

            # Margins (REAL data!)
            if 'net_margin' in latest_metrics:
                psx_metrics['margin_trend'] = (
                    'expanding' if latest_metrics['net_margin'] > 0
                    else 'contracting'
                )
                psx_metrics['margin_change_pct'] = latest_metrics['net_margin']

            # Quarterly data
            if 'latest_quarter_eps' in latest_metrics:
                psx_metrics['psx_latest_quarter_eps'] = latest_metrics['latest_quarter_eps']

            if 'latest_quarter_revenue' in latest_metrics:
                psx_metrics['psx_latest_quarter_revenue'] = latest_metrics['latest_quarter_revenue']

            # Set defaults for fields we don't have (better than random mock data)
            psx_metrics.update({
                'interest_coverage': 5.0,  # Conservative default
                'earnings_cagr_3y': latest_metrics.get('profit_growth', 0),
                'earnings_surprise_pct': 0,
                'estimate_revision_trend': 0,
                'upcoming_catalysts': [],
                'debt_growth_yoy': 0,
                'quarters_margin_declining': 0,
            })

            print(f"  ✓ Using REAL PSX data for {symbol}")
            return psx_metrics

        except Exception as e:
            print(f"  ⚠ Error getting PSX real metrics for {symbol}: {e}")
            return None

    def _generate_mock_enhanced_metrics(self, symbol: str) -> Dict:
        """
        Generate mock data for metrics not available via standard APIs

        This is a FALLBACK when real PSX data is not available.

        In production, these would be fetched from:
        - Company quarterly reports
        - Analyst research
        - SECP filings

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with mock metrics
        """
        # Use symbol hash for deterministic but varied mock data
        seed = sum(ord(c) for c in symbol)
        np.random.seed(seed)

        return {
            'interest_coverage': np.random.uniform(3, 10),
            'earnings_growth_yoy': np.random.uniform(-5, 25),
            'revenue_cagr_3y': np.random.uniform(5, 15),
            'earnings_cagr_3y': np.random.uniform(3, 20),
            'margin_trend': np.random.choice(['expanding', 'stable', 'contracting'], p=[0.4, 0.4, 0.2]),
            'margin_change_pct': np.random.uniform(-3, 5),
            'earnings_surprise_pct': np.random.uniform(-2, 5),
            'estimate_revision_trend': np.random.uniform(-0.3, 0.5),
            'upcoming_catalysts': [],
            'debt_growth_yoy': np.random.uniform(-10, 20),
            'quarters_margin_declining': 0 if np.random.rand() > 0.2 else np.random.randint(1, 3),
            'quarters_negative_ocf': 0 if np.random.rand() > 0.15 else np.random.randint(1, 3),
            'analyst_consensus': np.random.choice(['buy', 'hold', 'sell'], p=[0.5, 0.4, 0.1])
        }

    def _map_sector(self, sector: str) -> str:
        """Map sector names to PSX standard sectors"""
        sector_mapping = {
            'Energy': 'Energy',
            'Oil & Gas': 'Energy',
            'Financial Services': 'Banking',
            'Financial': 'Banking',
            'Basic Materials': 'Cement',
            'Materials': 'Cement',
            'Consumer Defensive': 'Fertilizer',
            'Agriculture': 'Fertilizer'
        }
        return sector_mapping.get(sector, 'Default')

    def _get_cached_metrics(self, symbol: str) -> Optional[Dict]:
        """Get cached metrics if still valid"""
        if symbol in self.metrics_cache:
            cached_data, cached_time = self.metrics_cache[symbol]
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600

            if age_hours < self.cache_ttl_hours:
                return cached_data

        return None

    def _cache_metrics(self, symbol: str, metrics: Dict):
        """Cache metrics with timestamp"""
        self.metrics_cache[symbol] = (metrics, datetime.now())

    # ===================================================================
    # UTILITY METHODS
    # ===================================================================

    def _extract_valuation_metrics(self, metrics: Dict) -> ValuationMetrics:
        """Extract valuation metrics into dataclass"""
        return ValuationMetrics(
            pe_ratio=metrics.get('pe_ratio'),
            pb_ratio=metrics.get('pb_ratio'),
            dividend_yield=metrics.get('dividend_yield'),
            ev_ebitda=metrics.get('ev_ebitda'),
            price_to_sales=metrics.get('price_to_sales'),
            enterprise_value=metrics.get('enterprise_value')
        )

    def _extract_health_metrics(self, metrics: Dict) -> FinancialHealthMetrics:
        """Extract financial health metrics into dataclass"""
        return FinancialHealthMetrics(
            debt_to_equity=metrics.get('debt_to_equity'),
            current_ratio=metrics.get('current_ratio'),
            quick_ratio=metrics.get('quick_ratio'),
            roa=metrics.get('roa'),
            roe=metrics.get('roe'),
            interest_coverage=metrics.get('interest_coverage'),
            operating_cash_flow=metrics.get('operating_cash_flow')
        )

    def _extract_growth_metrics(self, metrics: Dict) -> GrowthMetrics:
        """Extract growth metrics into dataclass"""
        return GrowthMetrics(
            revenue_growth_yoy=metrics.get('revenue_growth_yoy'),
            earnings_growth_yoy=metrics.get('earnings_growth_yoy'),
            revenue_cagr_3y=metrics.get('revenue_cagr_3y'),
            earnings_cagr_3y=metrics.get('earnings_cagr_3y'),
            margin_trend=metrics.get('margin_trend'),
            margin_change_pct=metrics.get('margin_change_pct')
        )

    def _extract_momentum_metrics(self, metrics: Dict) -> MomentumMetrics:
        """Extract momentum metrics into dataclass"""
        return MomentumMetrics(
            earnings_surprise_pct=metrics.get('earnings_surprise_pct'),
            estimate_revision_trend=metrics.get('estimate_revision_trend'),
            upcoming_catalysts=metrics.get('upcoming_catalysts', [])
        )

    def _identify_catalysts(self, metrics: Dict) -> List[str]:
        """Identify potential catalysts for the stock"""
        catalysts = []

        # Earnings surprise
        if metrics.get('earnings_surprise_pct', 0) > 10:
            catalysts.append("Recent earnings beat")

        # Strong growth
        if metrics.get('revenue_growth_yoy', 0) > 20:
            catalysts.append("Strong revenue growth")

        # Improving margins
        if metrics.get('margin_trend') == 'expanding':
            catalysts.append("Expanding profit margins")

        # Add any upcoming catalysts from data
        catalysts.extend(metrics.get('upcoming_catalysts', []))

        return catalysts

    def _calculate_fair_value(self, metrics: Dict) -> Optional[float]:
        """
        Calculate fair value estimate using PE-based approach

        In production, would use DCF or other valuation models.
        """
        current_price = metrics.get('current_price', 0)
        pe_ratio = metrics.get('pe_ratio')

        if not current_price or not pe_ratio or pe_ratio <= 0:
            return None

        # Get sector benchmark PE
        sector = metrics.get('sector', 'Default')
        benchmark = self.PSX_SECTOR_BENCHMARKS.get(sector, self.PSX_SECTOR_BENCHMARKS['Default'])
        target_pe = benchmark['pe_avg']

        # Fair value = current price * (target PE / current PE)
        # Add 10% margin of safety
        fair_value = current_price * (target_pe / pe_ratio) * 1.1

        return round(fair_value, 2)

    def _enhance_with_peer_comparison(self, symbol: str, metrics: Dict) -> Dict:
        """
        Enhance metrics with peer comparison

        In production, would compare against sector peers.
        """
        # Mock implementation
        metrics['peer_comparison'] = {
            'pe_percentile': 50,  # 50th percentile
            'growth_percentile': 60,
            'profitability_percentile': 55
        }
        return metrics

    def _enhance_with_dcf_valuation(self, metrics: Dict) -> Dict:
        """
        Enhance with DCF valuation model

        In production, would use full DCF model with projections.
        """
        # Simplified mock DCF
        fair_value = self._calculate_fair_value(metrics)
        if fair_value:
            metrics['dcf_fair_value'] = fair_value * 1.05  # Slight adjustment

        return metrics

    def _assess_data_quality(self, metrics: Dict) -> float:
        """
        Assess quality of data (0-1 scale)

        Based on completeness and recency.
        """
        quality = 1.0

        # Check completeness
        required_fields = ['pe_ratio', 'pb_ratio', 'current_ratio', 'roe', 'revenue_growth_yoy']
        missing = sum(1 for field in required_fields if metrics.get(field) is None)

        if missing > 0:
            quality -= (missing / len(required_fields)) * 0.3

        # Check recency
        cached_at = metrics.get('_cached_at')
        if cached_at:
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600
            if age_hours > 48:
                quality -= 0.2
            elif age_hours > 24:
                quality -= 0.1

        return max(0.0, min(1.0, quality))

    def _generate_recommendation(self, score: float, red_flags: List[RedFlag]) -> Recommendation:
        """
        Generate buy/hold/sell recommendation based on score and red flags

        Args:
            score: Fundamental score (0-100)
            red_flags: List of detected red flags

        Returns:
            Recommendation enum
        """
        # Auto-reject if critical red flags
        for flag in red_flags:
            if flag.severity == RedFlagSeverity.CRITICAL:
                return Recommendation.SELL

        # Score-based recommendation
        if score >= 70:
            return Recommendation.BUY
        elif score >= 50:
            return Recommendation.HOLD
        else:
            return Recommendation.SELL

    # ===================================================================
    # REPORTING
    # ===================================================================

    def print_analysis(self, score: FundamentalScore):
        """Print formatted fundamental analysis"""
        print("\n" + "="*80)
        print(f"FUNDAMENTAL ANALYSIS: {score.symbol}")
        print("="*80)

        # Summary
        print(f"\n📊 SUMMARY")
        print(f"   Score: {score.fundamental_score:.1f}/100")
        print(f"   Recommendation: {score.recommendation.value}")
        print(f"   Confidence: {score.confidence.value.upper()}")
        print(f"   Analysis Mode: {score.analysis_mode}")
        print(f"   Processing Time: {score.processing_time_ms}ms")

        # Component Scores
        print(f"\n📈 COMPONENT SCORES")
        print(f"   Valuation:        {score.valuation_score:.1f}/100 (30% weight)")
        print(f"   Financial Health: {score.health_score:.1f}/100 (40% weight)")
        print(f"   Growth:           {score.growth_score:.1f}/100 (20% weight)")
        print(f"   Momentum:         {score.momentum_score:.1f}/100 (10% weight)")

        # Valuation
        print(f"\n💰 VALUATION")
        v = score.valuation
        if v.pe_ratio:
            print(f"   P/E Ratio:       {v.pe_ratio:.2f}")
        if v.pb_ratio:
            print(f"   P/B Ratio:       {v.pb_ratio:.2f}")
        if v.dividend_yield:
            print(f"   Dividend Yield:  {v.dividend_yield:.2f}%")
        if v.ev_ebitda:
            print(f"   EV/EBITDA:       {v.ev_ebitda:.2f}")

        # Financial Health
        print(f"\n💪 FINANCIAL HEALTH")
        h = score.financial_health
        if h.debt_to_equity is not None:
            print(f"   Debt/Equity:     {h.debt_to_equity:.2f}")
        if h.current_ratio:
            print(f"   Current Ratio:   {h.current_ratio:.2f}")
        if h.roa is not None:
            print(f"   ROA:             {h.roa:.1f}%")
        if h.roe is not None:
            print(f"   ROE:             {h.roe:.1f}%")
        if h.interest_coverage:
            print(f"   Interest Cover:  {h.interest_coverage:.2f}x")

        # Growth
        print(f"\n📈 GROWTH")
        g = score.growth_metrics
        if g.revenue_growth_yoy is not None:
            print(f"   Revenue Growth:  {g.revenue_growth_yoy:+.1f}% YoY")
        if g.earnings_growth_yoy is not None:
            print(f"   Earnings Growth: {g.earnings_growth_yoy:+.1f}% YoY")
        if g.margin_trend:
            print(f"   Margin Trend:    {g.margin_trend.title()}")

        # Red Flags
        if score.red_flags:
            print(f"\n🚩 RED FLAGS ({len(score.red_flags)})")
            for flag in score.red_flags:
                severity_emoji = {
                    RedFlagSeverity.CRITICAL: "🔴",
                    RedFlagSeverity.HIGH: "🟠",
                    RedFlagSeverity.MEDIUM: "🟡",
                    RedFlagSeverity.LOW: "🟢"
                }
                emoji = severity_emoji.get(flag.severity, "⚠️")
                print(f"   {emoji} {flag.severity.value.upper()}: {flag.description}")

        # Catalysts
        if score.catalysts:
            print(f"\n✨ CATALYSTS")
            for catalyst in score.catalysts:
                print(f"   • {catalyst}")

        # Price Target
        if score.fair_value and score.upside_pct is not None:
            print(f"\n🎯 PRICE TARGET")
            print(f"   Fair Value:      {score.fair_value:.2f}")
            print(f"   Upside/Downside: {score.upside_pct:+.1f}%")

        print(f"\n   Data Quality:    {score.data_quality*100:.0f}%")
        print("="*80 + "\n")


def main():
    """Example usage of PSX Fundamental Agent"""

    # Top PSX stocks for testing
    test_stocks = [
        "OGDC",   # Oil & Gas Development Company
        "PPL",    # Pakistan Petroleum Limited
        "HBL",    # Habib Bank Limited
        "LUCK",   # Lucky Cement
        "ENGRO"   # Engro Corporation
    ]

    print("="*80)
    print("PSX FUNDAMENTAL ANALYSIS AGENT - DEMO")
    print("="*80)
    print(f"\nAnalyzing {len(test_stocks)} stocks...\n")

    # Initialize agent
    agent = PSXFundamentalAgent(cache_ttl_hours=24)

    # Quick analysis examples
    print("\n" + "="*80)
    print("QUICK ANALYSIS MODE (< 2 minutes)")
    print("="*80)

    for symbol in test_stocks[:2]:  # Analyze first 2 stocks
        score = agent.quick_analysis(symbol)
        agent.print_analysis(score)

    # Deep analysis example
    print("\n" + "="*80)
    print("DEEP ANALYSIS MODE (Comprehensive)")
    print("="*80)

    deep_symbol = test_stocks[2]
    deep_score = agent.deep_analysis(deep_symbol)
    agent.print_analysis(deep_score)

    # Screen universe
    print("\n" + "="*80)
    print("UNIVERSE SCREENING")
    print("="*80)

    results = agent.screen_universe(test_stocks)

    # Sort by score
    sorted_results = sorted(results.items(), key=lambda x: x[1].fundamental_score, reverse=True)

    print(f"\nTop Ranked Stocks by Fundamental Score:\n")
    print(f"{'Rank':<6} {'Symbol':<10} {'Score':<10} {'Rec':<8} {'Conf':<10} {'Red Flags'}")
    print("-" * 80)

    for rank, (symbol, score) in enumerate(sorted_results, 1):
        rec_emoji = {
            Recommendation.BUY: "🟢",
            Recommendation.HOLD: "🟡",
            Recommendation.SELL: "🔴"
        }
        emoji = rec_emoji.get(score.recommendation, "")

        print(f"{rank:<6} {symbol:<10} {score.fundamental_score:<10.1f} "
              f"{emoji} {score.recommendation.value:<6} {score.confidence.value:<10} "
              f"{len(score.red_flags)}")

    print("\n" + "="*80)
    print("✅ Fundamental analysis complete")
    print("="*80)


if __name__ == "__main__":
    main()
