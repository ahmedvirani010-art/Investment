"""
PSX Portfolio Manager - Data Models

Defines all data structures for portfolio management:
- Portfolio configuration and constraints
- Position and portfolio state
- Trading signals and decisions
- Portfolio models (Conservative, Balanced, Aggressive)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class ActionType(Enum):
    """Type of trading action"""
    BUY = "BUY"
    SELL = "SELL"
    REDUCE = "REDUCE"  # Partial sell
    HOLD = "HOLD"


class ModelType(Enum):
    """Portfolio model types"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class PortfolioConfig:
    """Portfolio configuration and constraints"""
    name: str = "default"
    initial_cash: float = 1_000_000.0  # PKR
    max_position_pct: float = 15.0     # Max % per stock
    max_positions: int = 10            # Max number of stocks
    min_cash_reserve_pct: float = 10.0  # Keep 10% cash
    max_single_order_value: float = 200_000.0  # PKR
    lot_size: int = 500                # PSX lot size
    transaction_fee_pct: float = 0.35  # ~0.35% total fees (brokerage + tax)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Position:
    """Current position in a stock"""
    symbol: str
    quantity: float
    average_cost: float
    current_price: float = 0.0

    # Calculated fields
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0

    # Timestamps
    opened_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    last_updated: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))

    def update_market_value(self, current_price: float):
        """Update market value and P&L based on current price"""
        self.current_price = current_price
        self.market_value = self.quantity * current_price
        self.unrealized_pl = (current_price - self.average_cost) * self.quantity
        if self.average_cost > 0:
            self.unrealized_pl_pct = (current_price - self.average_cost) / self.average_cost * 100
        else:
            self.unrealized_pl_pct = 0.0
        self.last_updated = datetime.now().strftime('%Y-%m-%d')

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class PortfolioSnapshot:
    """Current portfolio state"""
    portfolio_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Cash and equity
    cash: float = 0.0
    total_equity: float = 0.0
    total_market_value: float = 0.0
    total_unrealized_pl: float = 0.0

    # Positions
    positions: Dict[str, Position] = field(default_factory=dict)
    position_count: int = 0

    # Percentages
    cash_pct: float = 0.0
    invested_pct: float = 0.0

    def calculate_totals(self):
        """Calculate total values from positions"""
        self.position_count = len(self.positions)
        self.total_market_value = sum(pos.market_value for pos in self.positions.values())
        self.total_unrealized_pl = sum(pos.unrealized_pl for pos in self.positions.values())
        self.total_equity = self.cash + self.total_market_value

        if self.total_equity > 0:
            self.cash_pct = (self.cash / self.total_equity) * 100
            self.invested_pct = (self.total_market_value / self.total_equity) * 100
        else:
            self.cash_pct = 0.0
            self.invested_pct = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'portfolio_name': self.portfolio_name,
            'timestamp': self.timestamp,
            'cash': self.cash,
            'total_equity': self.total_equity,
            'total_market_value': self.total_market_value,
            'total_unrealized_pl': self.total_unrealized_pl,
            'position_count': self.position_count,
            'cash_pct': self.cash_pct,
            'invested_pct': self.invested_pct,
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()}
        }


@dataclass
class TradingSignal:
    """Aggregated signal from all agents for one stock"""
    symbol: str
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))

    # Component scores (0-100)
    technical_score: float = 50.0
    fundamental_score: float = 50.0
    anomaly_score: float = 50.0
    news_sentiment_score: float = 50.0

    # Aggregated
    composite_score: float = 50.0
    confidence: float = 0.0  # 0-1

    # Source data summaries
    technical_bias: str = "Neutral"
    fundamental_rec: str = "HOLD"
    has_anomaly: bool = False
    anomaly_severity: str = ""
    red_flags: List[str] = field(default_factory=list)

    # Current price
    current_price: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TradeDecision:
    """Portfolio manager decision for one symbol"""
    symbol: str
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))

    # Decision
    action: ActionType = ActionType.HOLD
    quantity: float = 0.0  # Shares to trade (0 for HOLD)
    target_price: Optional[float] = None

    # Scores and confidence
    composite_score: float = 50.0
    confidence: float = 0.0  # 0-1

    # Reasoning
    reasoning: List[str] = field(default_factory=list)
    signal_breakdown: Dict[str, float] = field(default_factory=dict)

    # Constraints
    violates_constraints: bool = False
    constraint_violations: List[str] = field(default_factory=list)

    # Risk metrics
    position_size_pct: float = 0.0  # % of portfolio
    position_value: float = 0.0     # PKR value

    # Current position (if exists)
    current_quantity: float = 0.0
    current_value: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['action'] = self.action.value
        return data


@dataclass
class PortfolioManagerOutput:
    """Complete portfolio manager output for one model"""
    portfolio_name: str
    model_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Portfolio state
    portfolio_snapshot: Optional[PortfolioSnapshot] = None

    # Signals and decisions
    signals: Dict[str, TradingSignal] = field(default_factory=dict)
    decisions: Dict[str, TradeDecision] = field(default_factory=dict)

    # Summary statistics
    total_buy_signals: int = 0
    total_sell_signals: int = 0
    total_reduce_signals: int = 0
    total_hold_signals: int = 0

    # Actionable recommendations (excludes HOLDs and constraint violations)
    recommended_trades: List[TradeDecision] = field(default_factory=list)
    excluded_trades: List[TradeDecision] = field(default_factory=list)

    # Performance
    processing_time_ms: Optional[int] = None

    def calculate_summary(self):
        """Calculate summary statistics"""
        self.total_buy_signals = sum(1 for d in self.decisions.values() if d.action == ActionType.BUY)
        self.total_sell_signals = sum(1 for d in self.decisions.values() if d.action == ActionType.SELL)
        self.total_reduce_signals = sum(1 for d in self.decisions.values() if d.action == ActionType.REDUCE)
        self.total_hold_signals = sum(1 for d in self.decisions.values() if d.action == ActionType.HOLD)

        # Separate actionable vs excluded trades
        self.recommended_trades = []
        self.excluded_trades = []

        for decision in self.decisions.values():
            if decision.action == ActionType.HOLD:
                continue  # Skip holds

            if decision.violates_constraints:
                self.excluded_trades.append(decision)
            else:
                self.recommended_trades.append(decision)

        # Sort by confidence (highest first)
        self.recommended_trades.sort(key=lambda d: d.confidence, reverse=True)
        self.excluded_trades.sort(key=lambda d: d.confidence, reverse=True)


@dataclass
class PortfolioModel:
    """Portfolio model configuration (Conservative, Balanced, Aggressive)"""
    name: str
    model_type: ModelType

    # Signal weights (must sum to 1.0)
    technical_weight: float
    fundamental_weight: float
    anomaly_weight: float
    news_weight: float

    # Decision thresholds
    buy_threshold: float      # Composite score >= this to buy
    sell_threshold: float     # Composite score <= this to sell
    reduce_threshold: float   # Composite score <= this to reduce position
    min_confidence: float     # Minimum confidence to act (0-1)

    # Position constraints
    max_position_pct: float   # Max % per stock

    # Red flag filtering
    critical_red_flag_action: str = "reject"  # "reject" or "cap_score"
    high_red_flag_penalty: float = 0.5        # Multiply score by this
    medium_red_flag_penalty: float = 0.7

    # Description
    description: str = ""

    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total_weight = (self.technical_weight + self.fundamental_weight +
                       self.anomaly_weight + self.news_weight)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")


# Predefined Portfolio Models

CONSERVATIVE_MODEL = PortfolioModel(
    name="Conservative",
    model_type=ModelType.CONSERVATIVE,
    technical_weight=0.20,
    fundamental_weight=0.50,
    anomaly_weight=0.15,
    news_weight=0.15,
    buy_threshold=70.0,
    sell_threshold=30.0,
    reduce_threshold=45.0,
    min_confidence=0.75,
    max_position_pct=10.0,
    critical_red_flag_action="reject",
    high_red_flag_penalty=0.5,
    medium_red_flag_penalty=0.7,
    description="Conservative model: Fundamentals-focused, high confidence threshold, strong red flag filtering"
)

BALANCED_MODEL = PortfolioModel(
    name="Balanced",
    model_type=ModelType.BALANCED,
    technical_weight=0.30,
    fundamental_weight=0.40,
    anomaly_weight=0.15,
    news_weight=0.15,
    buy_threshold=65.0,
    sell_threshold=35.0,
    reduce_threshold=47.5,
    min_confidence=0.65,
    max_position_pct=15.0,
    critical_red_flag_action="reject",
    high_red_flag_penalty=0.6,
    medium_red_flag_penalty=0.8,
    description="Balanced model: Equal weight to fundamentals and technicals, moderate thresholds"
)

AGGRESSIVE_MODEL = PortfolioModel(
    name="Aggressive",
    model_type=ModelType.AGGRESSIVE,
    technical_weight=0.40,
    fundamental_weight=0.30,
    anomaly_weight=0.20,
    news_weight=0.10,
    buy_threshold=55.0,
    sell_threshold=40.0,
    reduce_threshold=47.5,
    min_confidence=0.55,
    max_position_pct=20.0,
    critical_red_flag_action="cap_score",  # Don't auto-reject, just cap
    high_red_flag_penalty=0.7,
    medium_red_flag_penalty=0.85,
    description="Aggressive model: Momentum-focused, lower thresholds, lighter red flag filtering"
)


# Model registry
PORTFOLIO_MODELS = {
    "conservative": CONSERVATIVE_MODEL,
    "balanced": BALANCED_MODEL,
    "aggressive": AGGRESSIVE_MODEL,
}


def get_model(model_name: str) -> PortfolioModel:
    """
    Get portfolio model by name

    Args:
        model_name: Model name ("conservative", "balanced", "aggressive")

    Returns:
        PortfolioModel instance

    Raises:
        ValueError if model not found
    """
    model_name_lower = model_name.lower()
    if model_name_lower not in PORTFOLIO_MODELS:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(PORTFOLIO_MODELS.keys())}")
    return PORTFOLIO_MODELS[model_name_lower]
