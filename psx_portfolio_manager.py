"""
PSX Portfolio Manager Agent

Main portfolio management logic:
- Aggregates signals from all agents (Technical, Fundamental, Anomaly, News)
- Generates trading decisions (BUY/SELL/REDUCE/HOLD)
- Applies portfolio constraints (position limits, cash reserves)
- Supports multiple investment models (Conservative, Balanced, Aggressive)
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

from psx_portfolio_models import (
    PortfolioModel, PortfolioConfig, PortfolioSnapshot,
    TradingSignal, TradeDecision, PortfolioManagerOutput,
    ActionType, get_model
)
from psx_portfolio_store import PSXPortfolioStore
from psx_portfolio_utils import (
    convert_technical_to_score,
    convert_fundamental_to_score,
    convert_anomaly_to_score,
    convert_news_to_score,
    extract_red_flags,
    has_critical_red_flag,
    has_high_red_flag,
    format_reasoning_buy,
    format_reasoning_sell,
    format_reasoning_reduce,
    format_reasoning_hold,
    calculate_signal_confidence
)
from psx_technical_agent import TechnicalSnapshot
from psx_fundamental_agent import FundamentalScore


class PSXPortfolioManager:
    """
    Portfolio Manager Agent for Pakistan Stock Exchange

    Generates trading recommendations based on:
    - Technical analysis signals
    - Fundamental analysis scores
    - Anomaly detections
    - News sentiment

    Applies portfolio constraints and risk management.
    """

    def __init__(
        self,
        portfolio_store: PSXPortfolioStore,
        config: PortfolioConfig
    ):
        """
        Initialize portfolio manager

        Args:
            portfolio_store: PSXPortfolioStore instance
            config: PortfolioConfig for constraints
        """
        self.portfolio_store = portfolio_store
        self.config = config

        # Ensure portfolio is initialized in store
        if not self.portfolio_store.get_config(config.name):
            self.portfolio_store.initialize_portfolio(config)

    def analyze_portfolio(
        self,
        model_name: str,
        symbols: List[str],
        current_prices: Dict[str, float],
        technical_snapshots: Dict[str, TechnicalSnapshot],
        fundamental_scores: Dict[str, FundamentalScore],
        anomalies: List = None,
        correlations: List = None
    ) -> PortfolioManagerOutput:
        """
        Main analysis method - generates trading decisions for all symbols

        Args:
            model_name: Model to use ("conservative", "balanced", "aggressive")
            symbols: List of stock symbols to analyze
            current_prices: Dictionary of symbol -> current price
            technical_snapshots: Dictionary of symbol -> TechnicalSnapshot
            fundamental_scores: Dictionary of symbol -> FundamentalScore
            anomalies: List of Anomaly objects (optional)
            correlations: List of NewsAnomalyCorrelation objects (optional)

        Returns:
            PortfolioManagerOutput with decisions for all symbols
        """
        start_time = time.time()

        # Get portfolio model
        model = get_model(model_name)

        # Get current portfolio state
        portfolio = self.portfolio_store.get_portfolio_snapshot(
            self.config.name,
            current_prices
        )

        # Generate signals and decisions for each symbol
        signals = {}
        decisions = {}

        for symbol in symbols:
            # Skip if no current price
            if symbol not in current_prices:
                continue

            # Aggregate signal from all agents
            signal = self._aggregate_signal(
                symbol=symbol,
                technical=technical_snapshots.get(symbol),
                fundamental=fundamental_scores.get(symbol),
                anomalies=anomalies or [],
                correlations=correlations or [],
                current_price=current_prices[symbol],
                model=model
            )
            signals[symbol] = signal

            # Get current position (if any)
            current_position = portfolio.positions.get(symbol)

            # Generate trading decision
            decision = self._generate_decision(
                signal=signal,
                current_position=current_position,
                portfolio=portfolio,
                model=model
            )
            decisions[symbol] = decision

        # Create output
        output = PortfolioManagerOutput(
            portfolio_name=self.config.name,
            model_name=model.name,
            portfolio_snapshot=portfolio,
            signals=signals,
            decisions=decisions,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

        # Calculate summary statistics
        output.calculate_summary()

        # Save decisions to database (for audit trail)
        for decision in decisions.values():
            self.portfolio_store.save_decision(
                self.config.name,
                model.name,
                decision
            )

        return output

    def _aggregate_signal(
        self,
        symbol: str,
        technical: Optional[TechnicalSnapshot],
        fundamental: Optional[FundamentalScore],
        anomalies: List,
        correlations: List,
        current_price: float,
        model: PortfolioModel
    ) -> TradingSignal:
        """
        Aggregate signals from all agents into composite score

        Args:
            symbol: Stock symbol
            technical: TechnicalSnapshot from technical agent
            fundamental: FundamentalScore from fundamental agent
            anomalies: List of Anomaly objects
            correlations: List of NewsAnomalyCorrelation objects
            current_price: Current stock price
            model: PortfolioModel to use for weighting

        Returns:
            TradingSignal with composite score
        """
        # Convert each agent output to 0-100 score
        technical_score = convert_technical_to_score(technical)
        fundamental_score = convert_fundamental_to_score(fundamental)
        anomaly_score = convert_anomaly_to_score(anomalies, symbol)
        news_score = convert_news_to_score(correlations, symbol)

        # Apply model weights to get composite score
        composite_score = (
            technical_score * model.technical_weight +
            fundamental_score * model.fundamental_weight +
            anomaly_score * model.anomaly_weight +
            news_score * model.news_weight
        )

        # Apply red flag penalties
        red_flags = extract_red_flags(fundamental)
        if has_critical_red_flag(fundamental):
            if model.critical_red_flag_action == "reject":
                composite_score = min(composite_score, 30.0)  # Cap at 30
            elif model.critical_red_flag_action == "cap_score":
                composite_score = min(composite_score, 40.0)  # Lighter cap

        if has_high_red_flag(fundamental):
            composite_score *= model.high_red_flag_penalty

        # Calculate confidence based on signal agreement
        confidence = calculate_signal_confidence(
            technical_score,
            fundamental_score,
            anomaly_score,
            news_score
        )

        # Create trading signal
        signal = TradingSignal(
            symbol=symbol,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            anomaly_score=anomaly_score,
            news_sentiment_score=news_score,
            composite_score=composite_score,
            confidence=confidence,
            technical_bias=technical.overall_bias.value if technical else "Neutral",
            fundamental_rec=fundamental.recommendation.value if fundamental else "HOLD",
            has_anomaly=any(a.symbol == symbol for a in anomalies) if anomalies else False,
            anomaly_severity=self._get_anomaly_severity(anomalies, symbol),
            red_flags=red_flags,
            current_price=current_price
        )

        return signal

    def _generate_decision(
        self,
        signal: TradingSignal,
        current_position: Optional,
        portfolio: PortfolioSnapshot,
        model: PortfolioModel
    ) -> TradeDecision:
        """
        Generate trading decision based on signal and current position

        Args:
            signal: TradingSignal
            current_position: Current Position (or None)
            portfolio: Current PortfolioSnapshot
            model: PortfolioModel

        Returns:
            TradeDecision
        """
        decision = TradeDecision(
            symbol=signal.symbol,
            composite_score=signal.composite_score,
            confidence=signal.confidence,
            signal_breakdown={
                'technical': signal.technical_score,
                'fundamental': signal.fundamental_score,
                'anomaly': signal.anomaly_score,
                'news': signal.news_sentiment_score,
                'composite': signal.composite_score
            }
        )

        # Set current position info
        if current_position:
            decision.current_quantity = current_position.quantity
            decision.current_value = current_position.market_value

        # Decision logic based on current position
        if not current_position:
            # No position - consider buying
            decision = self._decide_buy(signal, portfolio, model, decision)
        else:
            # Have position - consider selling, reducing, or holding
            decision = self._decide_sell_or_hold(signal, current_position, portfolio, model, decision)

        # Validate constraints
        decision = self._validate_constraints(decision, portfolio, model)

        return decision

    def _decide_buy(
        self,
        signal: TradingSignal,
        portfolio: PortfolioSnapshot,
        model: PortfolioModel,
        decision: TradeDecision
    ) -> TradeDecision:
        """
        Decide whether to buy (when no current position)

        Args:
            signal: TradingSignal
            portfolio: PortfolioSnapshot
            model: PortfolioModel
            decision: TradeDecision to update

        Returns:
            Updated TradeDecision
        """
        # Check if composite score meets buy threshold
        if signal.composite_score >= model.buy_threshold and signal.confidence >= model.min_confidence:
            # Calculate position size
            quantity = self._calculate_position_size(
                signal=signal,
                portfolio=portfolio,
                model=model
            )

            if quantity > 0:
                decision.action = ActionType.BUY
                decision.quantity = quantity
                decision.target_price = signal.current_price
                decision.position_value = quantity * signal.current_price
                decision.position_size_pct = (decision.position_value / portfolio.total_equity) * 100

                # Generate reasoning
                decision.reasoning = format_reasoning_buy(
                    signal_breakdown=decision.signal_breakdown,
                    technical_bias=signal.technical_bias,
                    fundamental_rec=signal.fundamental_rec,
                    has_anomaly=signal.has_anomaly,
                    red_flags=signal.red_flags
                )
            else:
                # Want to buy but can't (insufficient funds, etc.)
                decision.action = ActionType.HOLD
                decision.reasoning = ["Insufficient funds or position size too small"]
        else:
            # Don't buy
            decision.action = ActionType.HOLD
            decision.reasoning = format_reasoning_hold(
                signal_breakdown=decision.signal_breakdown,
                current_position=False
            )

        return decision

    def _decide_sell_or_hold(
        self,
        signal: TradingSignal,
        current_position,
        portfolio: PortfolioSnapshot,
        model: PortfolioModel,
        decision: TradeDecision
    ) -> TradeDecision:
        """
        Decide whether to sell, reduce, or hold current position

        Args:
            signal: TradingSignal
            current_position: Current Position
            portfolio: PortfolioSnapshot
            model: PortfolioModel
            decision: TradeDecision to update

        Returns:
            Updated TradeDecision
        """
        # Check if should sell entire position
        if signal.composite_score <= model.sell_threshold:
            decision.action = ActionType.SELL
            decision.quantity = current_position.quantity
            decision.target_price = signal.current_price
            decision.position_value = current_position.market_value
            decision.reasoning = format_reasoning_sell(
                signal_breakdown=decision.signal_breakdown,
                technical_bias=signal.technical_bias,
                fundamental_rec=signal.fundamental_rec,
                has_anomaly=signal.has_anomaly,
                red_flags=signal.red_flags
            )

        # Check if should reduce position (partial sell)
        elif signal.composite_score <= model.reduce_threshold:
            decision.action = ActionType.REDUCE
            decision.quantity = current_position.quantity * 0.5  # Reduce by 50%
            decision.target_price = signal.current_price
            decision.position_value = decision.quantity * signal.current_price
            decision.reasoning = format_reasoning_reduce(
                signal_breakdown=decision.signal_breakdown,
                technical_bias=signal.technical_bias,
                fundamental_rec=signal.fundamental_rec
            )

        else:
            # Hold current position
            decision.action = ActionType.HOLD
            decision.reasoning = format_reasoning_hold(
                signal_breakdown=decision.signal_breakdown,
                current_position=True
            )

        return decision

    def _calculate_position_size(
        self,
        signal: TradingSignal,
        portfolio: PortfolioSnapshot,
        model: PortfolioModel
    ) -> float:
        """
        Calculate appropriate position size for a BUY decision

        Uses signal strength to scale position size within constraints

        Args:
            signal: TradingSignal
            portfolio: PortfolioSnapshot
            model: PortfolioModel

        Returns:
            Number of shares to buy (0 if can't buy)
        """
        # Calculate available cash (minus reserve)
        min_cash_reserve = portfolio.total_equity * (self.config.min_cash_reserve_pct / 100)
        available_cash = portfolio.cash - min_cash_reserve

        if available_cash <= 0:
            return 0.0

        # Max position value based on % of total equity
        max_position_value = portfolio.total_equity * (model.max_position_pct / 100)

        # Scale position based on signal strength
        # Higher composite score and confidence = larger position
        signal_factor = signal.composite_score / 100  # 0-1
        confidence_factor = signal.confidence  # 0-1
        sizing_factor = min(signal_factor * confidence_factor, 0.8)  # Cap at 80%

        # Target position value
        target_value = min(
            max_position_value * sizing_factor,
            available_cash,
            self.config.max_single_order_value
        )

        # Convert to shares
        if signal.current_price <= 0:
            return 0.0

        quantity = target_value / signal.current_price

        # Round to lot size (PSX typically 500 shares per lot)
        lot_size = self.config.lot_size
        quantity = (quantity // lot_size) * lot_size

        return quantity

    def _validate_constraints(
        self,
        decision: TradeDecision,
        portfolio: PortfolioSnapshot,
        model: PortfolioModel
    ) -> TradeDecision:
        """
        Validate decision against portfolio constraints

        Args:
            decision: TradeDecision
            portfolio: PortfolioSnapshot
            model: PortfolioModel

        Returns:
            Updated TradeDecision with constraint violations flagged
        """
        violations = []

        # Only validate BUY decisions (SELL/REDUCE always allowed)
        if decision.action == ActionType.BUY:
            # Check if would exceed max positions
            if portfolio.position_count >= self.config.max_positions:
                # Only violation if this is a new position (not adding to existing)
                if decision.symbol not in portfolio.positions:
                    violations.append(f"Would exceed max positions ({self.config.max_positions})")

            # Check if would exceed max position percentage
            position_pct = (decision.position_value / portfolio.total_equity) * 100
            if position_pct > model.max_position_pct:
                violations.append(f"Position size {position_pct:.1f}% exceeds limit {model.max_position_pct}%")

            # Check cash reserve
            cost = decision.quantity * decision.target_price
            fees = cost * (self.config.transaction_fee_pct / 100)
            total_cost = cost + fees
            remaining_cash = portfolio.cash - total_cost
            min_reserve = portfolio.total_equity * (self.config.min_cash_reserve_pct / 100)

            if remaining_cash < min_reserve:
                violations.append(f"Would violate cash reserve requirement ({self.config.min_cash_reserve_pct}%)")

        # Update decision with violations
        if violations:
            decision.violates_constraints = True
            decision.constraint_violations = violations

        return decision

    def _get_anomaly_severity(self, anomalies: List, symbol: str) -> str:
        """Get highest anomaly severity for a symbol"""
        if not anomalies:
            return ""

        symbol_anomalies = [a for a in anomalies if a.symbol == symbol]
        if not symbol_anomalies:
            return ""

        # Get highest severity
        from psx_anomaly_agent import Severity
        if any(a.severity == Severity.HIGH for a in symbol_anomalies):
            return "HIGH"
        elif any(a.severity == Severity.MEDIUM for a in symbol_anomalies):
            return "MEDIUM"
        elif any(a.severity == Severity.LOW for a in symbol_anomalies):
            return "LOW"

        return ""
