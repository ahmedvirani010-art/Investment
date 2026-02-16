"""
PSX Risk Management Agent

Provides comprehensive risk management for Pakistan Stock Exchange trading:
- Position sizing based on risk parameters
- Trade validation against risk rules
- Portfolio risk analysis and diversification monitoring
- Real-time risk limit enforcement
- Risk-adjusted performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RiskViolationType(Enum):
    """Types of risk violations"""
    MAX_RISK_PER_TRADE = "max_risk_per_trade"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_TOTAL_RISK = "max_total_risk"
    CONCENTRATION_RISK = "concentration_risk"
    SECTOR_CONCENTRATION = "sector_concentration"
    CORRELATION_RISK = "correlation_risk"
    INSUFFICIENT_CAPITAL = "insufficient_capital"


class TradeDirection(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class RiskSettings:
    """Risk management settings"""
    # Account settings
    account_value: float  # Total account value in PKR
    max_risk_per_trade_pct: float = 2.0  # Maximum % of account to risk per trade
    max_position_size_pct: float = 10.0  # Maximum % of account per position
    max_total_risk_pct: float = 6.0  # Maximum total portfolio risk %

    # Diversification settings
    max_sector_exposure_pct: float = 30.0  # Maximum exposure to single sector
    max_single_position_pct: float = 15.0  # Maximum size of single position
    min_positions: int = 5  # Minimum number of positions for diversification
    max_positions: int = 20  # Maximum number of positions

    # Stop loss settings
    default_stop_loss_pct: float = 3.0  # Default stop loss percentage
    min_reward_risk_ratio: float = 2.0  # Minimum reward-to-risk ratio

    # Advanced settings
    use_kelly_criterion: bool = False  # Use Kelly Criterion for position sizing
    kelly_fraction: float = 0.25  # Fraction of Kelly to use (for safety)
    allow_pyramiding: bool = True  # Allow adding to winning positions
    max_correlated_positions: int = 3  # Max positions in correlated assets

    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TradeRiskAnalysis:
    """Risk analysis for a potential trade"""
    symbol: str
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    target_price: Optional[float] = None

    # Risk calculations
    risk_per_share: float = 0.0
    risk_amount: float = 0.0
    risk_percentage: float = 0.0
    position_size_shares: int = 0
    position_value: float = 0.0
    position_size_pct: float = 0.0

    # Reward calculations
    reward_per_share: Optional[float] = None
    reward_amount: Optional[float] = None
    reward_risk_ratio: Optional[float] = None

    # Validation
    is_valid: bool = True
    violations: List['RiskViolation'] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Recommendations
    recommended_shares: int = 0
    recommended_value: float = 0.0
    max_affordable_shares: int = 0

    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RiskViolation:
    """Risk rule violation"""
    violation_type: RiskViolationType
    severity: RiskLevel
    message: str
    current_value: float
    limit_value: float
    auto_reject: bool = False


@dataclass
class PortfolioRiskMetrics:
    """Overall portfolio risk metrics"""
    total_value: float
    total_invested: float
    cash_balance: float

    # Position metrics
    number_of_positions: int
    largest_position_pct: float
    smallest_position_pct: float
    average_position_size: float

    # Risk metrics
    total_portfolio_risk_pct: float
    total_risk_amount: float
    risk_per_position: Dict[str, float] = field(default_factory=dict)

    # Diversification
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    concentration_score: float = 0.0  # 0-100, lower is more diversified
    diversification_score: float = 0.0  # 0-100, higher is better

    # Performance-adjusted risk
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    volatility: Optional[float] = None

    # Violations
    current_violations: List[RiskViolation] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW

    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PositionRisk:
    """Risk analysis for an individual position"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    current_value: float

    stop_loss: Optional[float] = None
    risk_amount: float = 0.0
    risk_percentage: float = 0.0

    position_size_pct: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0

    sector: Optional[str] = None
    days_held: int = 0


class PSXRiskAgent:
    """
    Risk Management Agent for Pakistan Stock Exchange

    Features:
    - Position sizing based on risk parameters
    - Trade validation against risk rules
    - Portfolio diversification monitoring
    - Real-time risk limit enforcement
    - Kelly Criterion position sizing (optional)
    """

    def __init__(self, risk_settings: Optional[RiskSettings] = None):
        """
        Initialize risk agent

        Args:
            risk_settings: Risk management settings. If None, uses defaults
        """
        self.risk_settings = risk_settings or RiskSettings(account_value=1000000.0)
        self._portfolio_cache: Optional[PortfolioRiskMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def update_risk_settings(self, **kwargs) -> RiskSettings:
        """
        Update risk settings

        Args:
            **kwargs: Risk setting parameters to update

        Returns:
            Updated risk settings
        """
        for key, value in kwargs.items():
            if hasattr(self.risk_settings, key):
                setattr(self.risk_settings, key, value)

        self.risk_settings.updated_at = datetime.now().isoformat()
        self._invalidate_cache()
        return self.risk_settings

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        target_price: Optional[float] = None,
        direction: TradeDirection = TradeDirection.LONG,
        account_value: Optional[float] = None
    ) -> TradeRiskAnalysis:
        """
        Calculate recommended position size based on risk parameters

        Args:
            symbol: Stock ticker symbol
            entry_price: Planned entry price
            stop_loss: Stop loss price
            target_price: Target exit price (optional)
            direction: Trade direction (LONG or SHORT)
            account_value: Override account value (uses settings if None)

        Returns:
            TradeRiskAnalysis with position sizing recommendations
        """
        account_val = account_value or self.risk_settings.account_value

        # Calculate risk per share
        if direction == TradeDirection.LONG:
            risk_per_share = entry_price - stop_loss
            reward_per_share = (target_price - entry_price) if target_price else None
        else:  # SHORT
            risk_per_share = stop_loss - entry_price
            reward_per_share = (entry_price - target_price) if target_price else None

        # Validate stop loss
        if risk_per_share <= 0:
            return TradeRiskAnalysis(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                is_valid=False,
                violations=[RiskViolation(
                    violation_type=RiskViolationType.MAX_RISK_PER_TRADE,
                    severity=RiskLevel.CRITICAL,
                    message="Stop loss must be set to limit downside risk",
                    current_value=0,
                    limit_value=0,
                    auto_reject=True
                )]
            )

        # Calculate maximum risk amount based on settings
        max_risk_amount = account_val * (self.risk_settings.max_risk_per_trade_pct / 100)

        # Calculate position size based on risk
        position_size_shares = int(max_risk_amount / risk_per_share)
        position_value = position_size_shares * entry_price
        position_size_pct = (position_value / account_val) * 100

        # Calculate actual risk
        risk_amount = position_size_shares * risk_per_share
        risk_percentage = (risk_amount / account_val) * 100

        # Calculate reward metrics
        reward_amount = None
        reward_risk_ratio = None
        if reward_per_share:
            reward_amount = position_size_shares * reward_per_share
            reward_risk_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0

        # Calculate max affordable shares (based on capital)
        max_affordable = int((account_val * self.risk_settings.max_position_size_pct / 100) / entry_price)

        # Adjust position size if it exceeds position size limit
        violations = []
        warnings = []
        is_valid = True

        if position_size_pct > self.risk_settings.max_position_size_pct:
            violations.append(RiskViolation(
                violation_type=RiskViolationType.MAX_POSITION_SIZE,
                severity=RiskLevel.HIGH,
                message=f"Position size ({position_size_pct:.2f}%) exceeds limit ({self.risk_settings.max_position_size_pct}%)",
                current_value=position_size_pct,
                limit_value=self.risk_settings.max_position_size_pct,
                auto_reject=True
            ))
            # Adjust to max allowed
            position_size_shares = int((account_val * self.risk_settings.max_position_size_pct / 100) / entry_price)
            position_value = position_size_shares * entry_price
            position_size_pct = (position_value / account_val) * 100
            risk_amount = position_size_shares * risk_per_share
            risk_percentage = (risk_amount / account_val) * 100
            is_valid = False

        # Check reward/risk ratio
        if reward_risk_ratio and reward_risk_ratio < self.risk_settings.min_reward_risk_ratio:
            warnings.append(
                f"Reward/Risk ratio ({reward_risk_ratio:.2f}) is below recommended minimum "
                f"({self.risk_settings.min_reward_risk_ratio})"
            )

        # Check if position is too large for account
        if position_value > account_val:
            violations.append(RiskViolation(
                violation_type=RiskViolationType.INSUFFICIENT_CAPITAL,
                severity=RiskLevel.CRITICAL,
                message=f"Insufficient capital for position (needs {position_value:,.0f}, have {account_val:,.0f})",
                current_value=position_value,
                limit_value=account_val,
                auto_reject=True
            ))
            is_valid = False

        return TradeRiskAnalysis(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            risk_per_share=risk_per_share,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            position_size_shares=position_size_shares,
            position_value=position_value,
            position_size_pct=position_size_pct,
            reward_per_share=reward_per_share,
            reward_amount=reward_amount,
            reward_risk_ratio=reward_risk_ratio,
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            recommended_shares=position_size_shares,
            recommended_value=position_value,
            max_affordable_shares=max_affordable
        )

    def validate_trade(
        self,
        trade_analysis: TradeRiskAnalysis,
        current_portfolio: Optional[List[PositionRisk]] = None
    ) -> Tuple[bool, List[RiskViolation], List[str]]:
        """
        Validate trade against risk rules and current portfolio

        Args:
            trade_analysis: Trade risk analysis to validate
            current_portfolio: List of current positions (optional)

        Returns:
            Tuple of (is_valid, violations, warnings)
        """
        violations = list(trade_analysis.violations)
        warnings = list(trade_analysis.warnings)

        # If trade already has critical violations, reject immediately
        if any(v.auto_reject for v in violations):
            return False, violations, warnings

        # Validate against portfolio if provided
        if current_portfolio:
            portfolio_metrics = self.analyze_portfolio_risk(current_portfolio)

            # Check total portfolio risk
            new_total_risk = portfolio_metrics.total_portfolio_risk_pct + trade_analysis.risk_percentage
            if new_total_risk > self.risk_settings.max_total_risk_pct:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.MAX_TOTAL_RISK,
                    severity=RiskLevel.HIGH,
                    message=f"Total portfolio risk ({new_total_risk:.2f}%) would exceed limit ({self.risk_settings.max_total_risk_pct}%)",
                    current_value=new_total_risk,
                    limit_value=self.risk_settings.max_total_risk_pct,
                    auto_reject=True
                ))

            # Check number of positions
            if portfolio_metrics.number_of_positions >= self.risk_settings.max_positions:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.CONCENTRATION_RISK,
                    severity=RiskLevel.MODERATE,
                    message=f"Maximum number of positions ({self.risk_settings.max_positions}) reached",
                    current_value=portfolio_metrics.number_of_positions,
                    limit_value=self.risk_settings.max_positions,
                    auto_reject=True
                ))

            # Warn if insufficient diversification
            if portfolio_metrics.number_of_positions < self.risk_settings.min_positions:
                warnings.append(
                    f"Portfolio has fewer positions ({portfolio_metrics.number_of_positions}) than recommended "
                    f"minimum ({self.risk_settings.min_positions}) for proper diversification"
                )

        is_valid = len([v for v in violations if v.auto_reject]) == 0
        return is_valid, violations, warnings

    def analyze_portfolio_risk(
        self,
        positions: List[PositionRisk],
        price_data: Optional[Dict[str, float]] = None
    ) -> PortfolioRiskMetrics:
        """
        Analyze overall portfolio risk and diversification

        Args:
            positions: List of current positions
            price_data: Current prices for positions (symbol -> price)

        Returns:
            PortfolioRiskMetrics with comprehensive risk analysis
        """
        if not positions:
            return PortfolioRiskMetrics(
                total_value=self.risk_settings.account_value,
                total_invested=0,
                cash_balance=self.risk_settings.account_value,
                number_of_positions=0,
                largest_position_pct=0,
                smallest_position_pct=0,
                average_position_size=0,
                total_portfolio_risk_pct=0,
                total_risk_amount=0,
                concentration_score=0,
                diversification_score=100
            )

        # Calculate total portfolio value
        total_invested = sum(p.current_value for p in positions)
        cash_balance = self.risk_settings.account_value - total_invested
        total_value = self.risk_settings.account_value

        # Position size analysis
        position_percentages = [(p.current_value / total_value) * 100 for p in positions]
        largest_position_pct = max(position_percentages) if position_percentages else 0
        smallest_position_pct = min(position_percentages) if position_percentages else 0
        average_position_size = sum(position_percentages) / len(positions) if positions else 0

        # Risk analysis
        total_risk_amount = sum(p.risk_amount for p in positions)
        total_portfolio_risk_pct = (total_risk_amount / total_value) * 100
        risk_per_position = {p.symbol: p.risk_percentage for p in positions}

        # Sector diversification
        sector_exposure = {}
        for pos in positions:
            if pos.sector:
                sector_exposure[pos.sector] = sector_exposure.get(pos.sector, 0) + pos.position_size_pct

        # Calculate concentration score (Herfindahl-Hirschman Index)
        # HHI = sum of squared market shares, ranges from 0 to 10,000
        # We normalize to 0-100 scale
        hhi = sum(pct ** 2 for pct in position_percentages)
        concentration_score = min(hhi / 100, 100)  # Normalize to 0-100

        # Diversification score (inverse of concentration)
        diversification_score = 100 - concentration_score

        # Check for violations
        violations = []

        if total_portfolio_risk_pct > self.risk_settings.max_total_risk_pct:
            violations.append(RiskViolation(
                violation_type=RiskViolationType.MAX_TOTAL_RISK,
                severity=RiskLevel.HIGH,
                message=f"Total portfolio risk ({total_portfolio_risk_pct:.2f}%) exceeds limit",
                current_value=total_portfolio_risk_pct,
                limit_value=self.risk_settings.max_total_risk_pct
            ))

        if largest_position_pct > self.risk_settings.max_single_position_pct:
            violations.append(RiskViolation(
                violation_type=RiskViolationType.MAX_POSITION_SIZE,
                severity=RiskLevel.MODERATE,
                message=f"Largest position ({largest_position_pct:.2f}%) exceeds single position limit",
                current_value=largest_position_pct,
                limit_value=self.risk_settings.max_single_position_pct
            ))

        for sector, exposure in sector_exposure.items():
            if exposure > self.risk_settings.max_sector_exposure_pct:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.SECTOR_CONCENTRATION,
                    severity=RiskLevel.MODERATE,
                    message=f"Sector {sector} exposure ({exposure:.2f}%) exceeds limit",
                    current_value=exposure,
                    limit_value=self.risk_settings.max_sector_exposure_pct
                ))

        # Determine overall risk level
        risk_level = RiskLevel.LOW
        if total_portfolio_risk_pct > self.risk_settings.max_total_risk_pct * 0.8:
            risk_level = RiskLevel.HIGH
        elif total_portfolio_risk_pct > self.risk_settings.max_total_risk_pct * 0.6:
            risk_level = RiskLevel.MODERATE

        if len(violations) > 3:
            risk_level = RiskLevel.CRITICAL

        return PortfolioRiskMetrics(
            total_value=total_value,
            total_invested=total_invested,
            cash_balance=cash_balance,
            number_of_positions=len(positions),
            largest_position_pct=largest_position_pct,
            smallest_position_pct=smallest_position_pct,
            average_position_size=average_position_size,
            total_portfolio_risk_pct=total_portfolio_risk_pct,
            total_risk_amount=total_risk_amount,
            risk_per_position=risk_per_position,
            sector_exposure=sector_exposure,
            concentration_score=concentration_score,
            diversification_score=diversification_score,
            current_violations=violations,
            risk_level=risk_level
        )

    def calculate_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        account_value: Optional[float] = None
    ) -> float:
        """
        Calculate position size using Kelly Criterion

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade percentage
            avg_loss: Average losing trade percentage (positive value)
            account_value: Account value (uses settings if None)

        Returns:
            Recommended position size as percentage of account
        """
        account_val = account_value or self.risk_settings.account_value

        # Kelly formula: f* = (bp - q) / b
        # where b = win/loss ratio, p = win probability, q = loss probability
        if avg_loss == 0:
            return 0

        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate

        kelly_pct = (b * p - q) / b

        # Apply Kelly fraction for safety (typically 0.25 or 0.5)
        adjusted_kelly = kelly_pct * self.risk_settings.kelly_fraction

        # Cap at max position size setting
        final_pct = min(adjusted_kelly * 100, self.risk_settings.max_position_size_pct)

        return max(0, final_pct)  # Ensure non-negative

    def generate_risk_report(
        self,
        portfolio: List[PositionRisk],
        format: str = "dict"
    ) -> Any:
        """
        Generate comprehensive risk report

        Args:
            portfolio: List of current positions
            format: Output format ("dict", "json", or "text")

        Returns:
            Risk report in specified format
        """
        metrics = self.analyze_portfolio_risk(portfolio)

        report = {
            "report_date": datetime.now().isoformat(),
            "risk_settings": asdict(self.risk_settings),
            "portfolio_metrics": asdict(metrics),
            "recommendations": self._generate_recommendations(metrics),
            "summary": {
                "risk_level": metrics.risk_level.value,
                "number_of_violations": len(metrics.current_violations),
                "diversification_score": metrics.diversification_score,
                "total_risk_percentage": metrics.total_portfolio_risk_pct
            }
        }

        if format == "json":
            return json.dumps(report, indent=2)
        elif format == "text":
            return self._format_text_report(report)
        else:
            return report

    def _generate_recommendations(self, metrics: PortfolioRiskMetrics) -> List[str]:
        """Generate actionable recommendations based on risk analysis"""
        recommendations = []

        if metrics.number_of_positions < self.risk_settings.min_positions:
            recommendations.append(
                f"Increase diversification: Add {self.risk_settings.min_positions - metrics.number_of_positions} "
                f"more positions to reach minimum recommended diversification"
            )

        if metrics.concentration_score > 70:
            recommendations.append(
                "High concentration risk detected. Consider rebalancing to reduce largest positions"
            )

        if metrics.total_portfolio_risk_pct > self.risk_settings.max_total_risk_pct * 0.8:
            recommendations.append(
                "Portfolio risk is approaching limit. Avoid new positions or tighten stop losses"
            )

        for violation in metrics.current_violations:
            if violation.violation_type == RiskViolationType.SECTOR_CONCENTRATION:
                recommendations.append(
                    f"Reduce sector concentration: {violation.message}"
                )

        if not recommendations:
            recommendations.append("Portfolio risk parameters are within acceptable limits")

        return recommendations

    def _format_text_report(self, report: Dict) -> str:
        """Format risk report as readable text"""
        lines = [
            "=" * 80,
            "PORTFOLIO RISK ANALYSIS REPORT",
            "=" * 80,
            f"Report Date: {report['report_date']}",
            "",
            "RISK SETTINGS:",
            f"  Account Value: PKR {report['risk_settings']['account_value']:,.2f}",
            f"  Max Risk Per Trade: {report['risk_settings']['max_risk_per_trade_pct']}%",
            f"  Max Position Size: {report['risk_settings']['max_position_size_pct']}%",
            f"  Max Total Risk: {report['risk_settings']['max_total_risk_pct']}%",
            "",
            "PORTFOLIO METRICS:",
            f"  Number of Positions: {report['portfolio_metrics']['number_of_positions']}",
            f"  Total Invested: PKR {report['portfolio_metrics']['total_invested']:,.2f}",
            f"  Cash Balance: PKR {report['portfolio_metrics']['cash_balance']:,.2f}",
            f"  Total Portfolio Risk: {report['portfolio_metrics']['total_portfolio_risk_pct']:.2f}%",
            f"  Diversification Score: {report['portfolio_metrics']['diversification_score']:.1f}/100",
            "",
            "RISK SUMMARY:",
            f"  Risk Level: {report['summary']['risk_level'].upper()}",
            f"  Active Violations: {report['summary']['number_of_violations']}",
            "",
            "RECOMMENDATIONS:",
        ]

        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"  {i}. {rec}")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _invalidate_cache(self):
        """Invalidate portfolio risk cache"""
        self._portfolio_cache = None
        self._cache_timestamp = None


# Utility functions for easy integration

def create_default_risk_settings(account_value: float) -> RiskSettings:
    """Create risk settings with conservative defaults for PSX trading"""
    return RiskSettings(
        account_value=account_value,
        max_risk_per_trade_pct=2.0,
        max_position_size_pct=10.0,
        max_total_risk_pct=6.0,
        max_sector_exposure_pct=30.0,
        max_single_position_pct=15.0,
        min_positions=5,
        max_positions=20,
        default_stop_loss_pct=3.0,
        min_reward_risk_ratio=2.0,
        use_kelly_criterion=False,
        allow_pyramiding=True,
        max_correlated_positions=3
    )


def create_aggressive_risk_settings(account_value: float) -> RiskSettings:
    """Create risk settings with aggressive parameters"""
    return RiskSettings(
        account_value=account_value,
        max_risk_per_trade_pct=5.0,
        max_position_size_pct=20.0,
        max_total_risk_pct=15.0,
        max_sector_exposure_pct=50.0,
        max_single_position_pct=25.0,
        min_positions=3,
        max_positions=15,
        default_stop_loss_pct=5.0,
        min_reward_risk_ratio=1.5,
        use_kelly_criterion=True,
        kelly_fraction=0.5,
        allow_pyramiding=True,
        max_correlated_positions=5
    )


if __name__ == "__main__":
    # Example usage
    print("PSX Risk Management Agent - Example Usage\n")

    # Create risk agent with default settings
    risk_settings = create_default_risk_settings(account_value=1_000_000)  # 1M PKR
    agent = PSXRiskAgent(risk_settings)

    print("Risk Settings:")
    print(f"  Account Value: PKR {risk_settings.account_value:,.0f}")
    print(f"  Max Risk Per Trade: {risk_settings.max_risk_per_trade_pct}%")
    print(f"  Max Position Size: {risk_settings.max_position_size_pct}%\n")

    # Example: Calculate position size for a trade
    print("=" * 80)
    print("EXAMPLE 1: Position Sizing")
    print("=" * 80)

    trade = agent.calculate_position_size(
        symbol="ENGRO",
        entry_price=300.0,
        stop_loss=285.0,  # 5% stop loss
        target_price=345.0,  # 15% target
        direction=TradeDirection.LONG
    )

    print(f"Trade: {trade.symbol} @ PKR {trade.entry_price}")
    print(f"Stop Loss: PKR {trade.stop_loss} (Risk: PKR {trade.risk_per_share}/share)")
    print(f"Target: PKR {trade.target_price}")
    print(f"Recommended Position: {trade.recommended_shares} shares (PKR {trade.position_value:,.0f})")
    print(f"Position Size: {trade.position_size_pct:.2f}% of account")
    print(f"Risk Amount: PKR {trade.risk_amount:,.0f} ({trade.risk_percentage:.2f}% of account)")
    print(f"Reward/Risk Ratio: {trade.reward_risk_ratio:.2f}")
    print(f"Valid Trade: {trade.is_valid}")

    if trade.warnings:
        print("\nWarnings:")
        for warning in trade.warnings:
            print(f"  - {warning}")

    # Example: Portfolio risk analysis
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Portfolio Risk Analysis")
    print("=" * 80)

    # Simulate a portfolio
    portfolio = [
        PositionRisk(
            symbol="ENGRO", quantity=1000, entry_price=300, current_price=315,
            current_value=315000, stop_loss=285, risk_amount=15000,
            risk_percentage=1.5, position_size_pct=31.5, sector="Chemicals"
        ),
        PositionRisk(
            symbol="HBL", quantity=2000, entry_price=150, current_price=155,
            current_value=310000, stop_loss=145, risk_amount=10000,
            risk_percentage=1.0, position_size_pct=31.0, sector="Banks"
        ),
        PositionRisk(
            symbol="PSO", quantity=1500, entry_price=200, current_price=205,
            current_value=307500, stop_loss=195, risk_amount=7500,
            risk_percentage=0.75, position_size_pct=30.75, sector="Oil & Gas"
        ),
    ]

    metrics = agent.analyze_portfolio_risk(portfolio)

    print(f"Portfolio Positions: {metrics.number_of_positions}")
    print(f"Total Invested: PKR {metrics.total_invested:,.0f}")
    print(f"Cash Balance: PKR {metrics.cash_balance:,.0f}")
    print(f"Total Portfolio Risk: {metrics.total_portfolio_risk_pct:.2f}%")
    print(f"Diversification Score: {metrics.diversification_score:.1f}/100")
    print(f"Concentration Score: {metrics.concentration_score:.1f}/100")
    print(f"Risk Level: {metrics.risk_level.value.upper()}")

    if metrics.current_violations:
        print(f"\nRisk Violations ({len(metrics.current_violations)}):")
        for violation in metrics.current_violations:
            print(f"  - [{violation.severity.value.upper()}] {violation.message}")

    # Generate full report
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Risk Report")
    print("=" * 80)

    report = agent.generate_risk_report(portfolio, format="text")
    print(report)
