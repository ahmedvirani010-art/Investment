"""
PSX Risk Limits
Risk limit definitions and enforcement logic for position/swing trading
"""

from dataclasses import dataclass
from typing import List, Optional
from psx_risk_storage import AlertSeverity, Position


@dataclass
class PositionLimits:
    """Position-level risk limits"""
    # Size limits
    max_position_size_pct: float = 10.0  # Max 10% of portfolio per position
    max_position_value: float = 1_000_000  # Max Rs 1M per position

    # Loss limits
    stop_loss_pct: float = 5.0  # Exit if down 5% from entry
    daily_loss_pct: float = 2.0  # Max 2% daily loss per position
    trailing_stop_pct: float = 3.0  # Lock in profits with trailing stop

    # Risk score limits
    max_risk_score: float = 80.0  # Reduce if risk score > 80

    # Holding period
    max_holding_days: int = 90  # Review positions older than 90 days


@dataclass
class PortfolioLimits:
    """Portfolio-level risk limits"""
    # Concentration limits
    max_single_position_pct: float = 15.0  # Max 15% in single stock
    max_sector_exposure_pct: float = 40.0  # Max 40% in single sector
    max_correlated_exposure_pct: float = 50.0  # Max 50% in highly correlated stocks

    # Loss limits
    daily_portfolio_loss_pct: float = 3.0  # Max 3% portfolio loss per day
    weekly_portfolio_loss_pct: float = 7.0  # Max 7% portfolio loss per week
    drawdown_limit_pct: float = 15.0  # Max 15% drawdown from peak

    # Leverage limits
    max_leverage: float = 1.0  # No leverage (1.0 = fully invested)

    # Volatility limits
    max_portfolio_volatility: float = 0.20  # Max 20% annualized vol


@dataclass
class LimitBreach:
    """Limit breach notification"""
    limit_type: str
    severity: str  # AlertSeverity value
    description: str
    recommended_action: str
    current_value: float
    limit_value: float

    def to_dict(self):
        return {
            'limit_type': self.limit_type,
            'severity': self.severity,
            'description': self.description,
            'recommended_action': self.recommended_action,
            'current_value': self.current_value,
            'limit_value': self.limit_value
        }


class RiskLimitEnforcer:
    """
    Enforces risk limits for positions and portfolio

    Checks position-level and portfolio-level limits,
    generates breach notifications with recommended actions
    """

    def __init__(self,
                 position_limits: Optional[PositionLimits] = None,
                 portfolio_limits: Optional[PortfolioLimits] = None):
        """
        Initialize risk limit enforcer

        Args:
            position_limits: Position-level limits (uses defaults if None)
            portfolio_limits: Portfolio-level limits (uses defaults if None)
        """
        self.position_limits = position_limits or PositionLimits()
        self.portfolio_limits = portfolio_limits or PortfolioLimits()

    def check_position_limits(self, position: Position) -> List[LimitBreach]:
        """
        Check if position violates any limits

        Args:
            position: Position to check

        Returns:
            List of limit breaches
        """
        breaches = []

        # Check stop loss
        if position.stop_loss_price and position.current_price > 0:
            loss_from_stop = ((position.current_price - position.stop_loss_price) /
                             position.stop_loss_price) * 100
            if loss_from_stop < 0:  # Below stop loss
                breaches.append(LimitBreach(
                    limit_type="STOP_LOSS",
                    severity=AlertSeverity.CRITICAL.value,
                    description=f"Stop loss breached: {abs(loss_from_stop):.1f}% below stop",
                    recommended_action="EXIT_POSITION",
                    current_value=position.current_price,
                    limit_value=position.stop_loss_price
                ))

        # Check unrealized loss vs stop loss %
        if position.unrealized_pnl_pct < -self.position_limits.stop_loss_pct:
            breaches.append(LimitBreach(
                limit_type="STOP_LOSS_PCT",
                severity=AlertSeverity.CRITICAL.value,
                description=f"Loss exceeds stop loss limit: {position.unrealized_pnl_pct:.1f}%",
                recommended_action="EXIT_POSITION",
                current_value=abs(position.unrealized_pnl_pct),
                limit_value=self.position_limits.stop_loss_pct
            ))

        # Check risk score
        if position.risk_score > self.position_limits.max_risk_score:
            breaches.append(LimitBreach(
                limit_type="RISK_SCORE",
                severity=AlertSeverity.HIGH.value,
                description=f"Risk score too high: {position.risk_score:.0f}/100",
                recommended_action="REDUCE_POSITION_50PCT",
                current_value=position.risk_score,
                limit_value=self.position_limits.max_risk_score
            ))

        # Check approaching stop loss (within 1%)
        if position.unrealized_pnl_pct < -(self.position_limits.stop_loss_pct - 1.0):
            if not any(b.limit_type == "STOP_LOSS_PCT" for b in breaches):  # Don't duplicate
                breaches.append(LimitBreach(
                    limit_type="APPROACHING_STOP_LOSS",
                    severity=AlertSeverity.HIGH.value,
                    description=f"Approaching stop loss: {position.unrealized_pnl_pct:.1f}%",
                    recommended_action="MONITOR_CLOSELY",
                    current_value=abs(position.unrealized_pnl_pct),
                    limit_value=self.position_limits.stop_loss_pct
                ))

        return breaches

    def check_portfolio_limits(self,
                              positions: List[Position],
                              total_portfolio_value: float,
                              portfolio_pnl_pct: float = 0.0) -> List[LimitBreach]:
        """
        Check if portfolio violates any limits

        Args:
            positions: List of active positions
            total_portfolio_value: Total portfolio value
            portfolio_pnl_pct: Portfolio P&L percentage (for day/week)

        Returns:
            List of limit breaches
        """
        breaches = []

        if total_portfolio_value <= 0:
            return breaches

        # Check single position concentration
        for position in positions:
            position_value = position.quantity * position.current_price
            position_pct = (position_value / total_portfolio_value) * 100

            if position_pct > self.portfolio_limits.max_single_position_pct:
                breaches.append(LimitBreach(
                    limit_type="POSITION_CONCENTRATION",
                    severity=AlertSeverity.HIGH.value,
                    description=f"{position.symbol} exceeds single position limit: {position_pct:.1f}%",
                    recommended_action="REDUCE_POSITION",
                    current_value=position_pct,
                    limit_value=self.portfolio_limits.max_single_position_pct
                ))

        # Check daily portfolio loss
        if portfolio_pnl_pct < -self.portfolio_limits.daily_portfolio_loss_pct:
            breaches.append(LimitBreach(
                limit_type="DAILY_LOSS_LIMIT",
                severity=AlertSeverity.CRITICAL.value,
                description=f"Daily loss limit breached: {portfolio_pnl_pct:.1f}%",
                recommended_action="STOP_TRADING",
                current_value=abs(portfolio_pnl_pct),
                limit_value=self.portfolio_limits.daily_portfolio_loss_pct
            ))

        return breaches

    def adjust_limits_for_market_conditions(self, market_volatility: float) -> None:
        """
        Dynamically adjust limits based on market conditions

        Args:
            market_volatility: Current market volatility (annualized, e.g., 0.25 = 25%)
        """
        if market_volatility > 0.25:  # High volatility regime (>25%)
            # Tighten limits
            self.position_limits.stop_loss_pct = 3.0  # Tighter stops
            self.portfolio_limits.max_single_position_pct = 10.0  # Smaller positions
            self.portfolio_limits.daily_portfolio_loss_pct = 2.0  # Tighter daily limit

        elif market_volatility < 0.10:  # Low volatility regime (<10%)
            # Normal/relaxed limits
            self.position_limits.stop_loss_pct = 5.0
            self.portfolio_limits.max_single_position_pct = 15.0
            self.portfolio_limits.daily_portfolio_loss_pct = 3.0

        else:  # Medium volatility (10-25%)
            # Standard limits (defaults)
            self.position_limits.stop_loss_pct = 5.0
            self.portfolio_limits.max_single_position_pct = 15.0
            self.portfolio_limits.daily_portfolio_loss_pct = 3.0

    def get_position_size_recommendation(self,
                                        portfolio_value: float,
                                        stock_volatility: float) -> float:
        """
        Calculate recommended position size based on volatility

        Args:
            portfolio_value: Total portfolio value
            stock_volatility: Stock's annualized volatility (e.g., 0.20 = 20%)

        Returns:
            Recommended position size in PKR
        """
        # Base allocation: 10% for medium volatility stock (20%)
        base_pct = 10.0
        target_volatility = 0.20

        # Adjust based on stock volatility
        if stock_volatility <= 0:
            vol_multiplier = 1.0
        else:
            vol_multiplier = min(2.0, max(0.5, target_volatility / stock_volatility))

        # Calculate position size
        recommended_pct = base_pct * vol_multiplier
        recommended_pct = max(2.0, min(recommended_pct, 15.0))  # Between 2-15%

        return portfolio_value * (recommended_pct / 100.0)

    def get_stop_loss_price(self,
                           entry_price: float,
                           stop_loss_pct: Optional[float] = None) -> float:
        """
        Calculate stop loss price

        Args:
            entry_price: Entry price
            stop_loss_pct: Stop loss percentage (uses default if None)

        Returns:
            Stop loss price
        """
        pct = stop_loss_pct or self.position_limits.stop_loss_pct
        return entry_price * (1.0 - pct / 100.0)

    def get_trailing_stop_price(self,
                                current_price: float,
                                trailing_pct: Optional[float] = None) -> float:
        """
        Calculate trailing stop price

        Args:
            current_price: Current market price
            trailing_pct: Trailing stop percentage (uses default if None)

        Returns:
            Trailing stop price
        """
        pct = trailing_pct or self.position_limits.trailing_stop_pct
        return current_price * (1.0 - pct / 100.0)
