"""
Portfolio-Risk Integration Module

Integrates PSXRiskAgent with portfolio management system.
Provides utilities for:
- Converting portfolio data to risk-compatible formats
- Pre-trade risk validation
- Real-time portfolio risk monitoring
- Risk-adjusted position recommendations
- Integration with fundamental and technical analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import json

# Import agents
from psx_risk_agent import (
    PSXRiskAgent, RiskSettings, TradeRiskAnalysis, PositionRisk,
    PortfolioRiskMetrics, RiskViolation, TradeDirection, RiskLevel,
    create_default_risk_settings, create_aggressive_risk_settings
)

# Import fundamental agent if available
try:
    from psx_fundamental_agent import PSXFundamentalAgent, FundamentalScore, Recommendation
    HAS_FUNDAMENTAL_AGENT = True
except ImportError:
    HAS_FUNDAMENTAL_AGENT = False
    print("Warning: psx_fundamental_agent not found. Fundamental analysis integration disabled.")


@dataclass
class EnhancedTradeRecommendation:
    """Trade recommendation with risk and fundamental analysis"""
    symbol: str
    recommendation: str  # BUY, HOLD, SELL, REJECT
    confidence: str  # high, medium, low

    # Risk analysis
    risk_analysis: TradeRiskAnalysis
    risk_approved: bool

    # Fundamental analysis (if available)
    fundamental_score: Optional[float] = None
    fundamental_recommendation: Optional[str] = None

    # Combined scoring
    combined_score: float = 0.0  # 0-100
    priority_rank: int = 0

    # Reasons
    approval_reasons: List[str] = None
    rejection_reasons: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.approval_reasons is None:
            self.approval_reasons = []
        if self.rejection_reasons is None:
            self.rejection_reasons = []
        if self.warnings is None:
            self.warnings = []


class PortfolioRiskManager:
    """
    Unified portfolio and risk management system

    Integrates risk management with portfolio tracking and analysis agents.
    """

    def __init__(
        self,
        risk_agent: PSXRiskAgent,
        fundamental_agent: Optional['PSXFundamentalAgent'] = None
    ):
        """
        Initialize portfolio risk manager

        Args:
            risk_agent: PSX risk management agent
            fundamental_agent: Optional fundamental analysis agent
        """
        self.risk_agent = risk_agent
        self.fundamental_agent = fundamental_agent
        self._portfolio_cache: Dict[str, PositionRisk] = {}

    def load_portfolio_from_prisma_data(
        self,
        user_stocks: List[Dict],
        stock_info: Dict[str, Dict],
        current_prices: Dict[str, float]
    ) -> List[PositionRisk]:
        """
        Convert Prisma UserStock data to PositionRisk format

        Args:
            user_stocks: List of UserStock records from Prisma
            stock_info: Dict of stock info {ticker: {sector, name, etc}}
            current_prices: Dict of current prices {ticker: price}

        Returns:
            List of PositionRisk objects
        """
        positions = []

        for user_stock in user_stocks:
            ticker = user_stock.get('stock', {}).get('ticker', 'UNKNOWN')
            quantity = user_stock.get('totalQuantity', 0)
            avg_cost = user_stock.get('averageCost', 0)
            current_price = current_prices.get(ticker, avg_cost)

            # Calculate stop loss (default 5% below entry)
            stop_loss = avg_cost * 0.95

            # Calculate risk
            risk_per_share = avg_cost - stop_loss
            risk_amount = quantity * risk_per_share

            # Calculate position metrics
            current_value = quantity * current_price
            unrealized_pl = (current_price - avg_cost) * quantity
            unrealized_pl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0

            # Get sector info
            sector = stock_info.get(ticker, {}).get('sector', 'Unknown')

            # Calculate days held
            created_at = user_stock.get('createdAt')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_held = (datetime.now() - created_at).days if created_at else 0

            position = PositionRisk(
                symbol=ticker,
                quantity=quantity,
                entry_price=avg_cost,
                current_price=current_price,
                current_value=current_value,
                stop_loss=stop_loss,
                risk_amount=risk_amount,
                risk_percentage=(risk_amount / self.risk_agent.risk_settings.account_value) * 100,
                position_size_pct=(current_value / self.risk_agent.risk_settings.account_value) * 100,
                unrealized_pl=unrealized_pl,
                unrealized_pl_pct=unrealized_pl_pct,
                sector=sector,
                days_held=days_held
            )

            positions.append(position)
            self._portfolio_cache[ticker] = position

        return positions

    def evaluate_trade_with_risk_and_fundamentals(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        target_price: Optional[float] = None,
        direction: TradeDirection = TradeDirection.LONG,
        analyze_fundamentals: bool = True
    ) -> EnhancedTradeRecommendation:
        """
        Evaluate a potential trade using both risk and fundamental analysis

        Args:
            symbol: Stock ticker
            entry_price: Planned entry price
            stop_loss: Stop loss price
            target_price: Target price (optional)
            direction: Trade direction
            analyze_fundamentals: Whether to include fundamental analysis

        Returns:
            EnhancedTradeRecommendation with combined analysis
        """
        # Step 1: Risk analysis
        risk_analysis = self.risk_agent.calculate_position_size(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            direction=direction
        )

        # Step 2: Validate against current portfolio
        current_portfolio = list(self._portfolio_cache.values())
        is_valid, violations, warnings = self.risk_agent.validate_trade(
            risk_analysis,
            current_portfolio
        )

        # Step 3: Fundamental analysis (if enabled and available)
        fundamental_score_val = None
        fundamental_rec = None

        if analyze_fundamentals and self.fundamental_agent and HAS_FUNDAMENTAL_AGENT:
            try:
                fund_result = self.fundamental_agent.analyze(symbol, mode="quick")
                fundamental_score_val = fund_result.fundamental_score
                fundamental_rec = fund_result.recommendation.value

                # Add fundamental insights to warnings
                if fund_result.red_flags:
                    warnings.extend([f"Fundamental: {flag.description}" for flag in fund_result.red_flags[:3]])

            except Exception as e:
                warnings.append(f"Fundamental analysis failed: {str(e)}")

        # Step 4: Combined decision
        approval_reasons = []
        rejection_reasons = []

        # Risk-based decision
        if is_valid:
            approval_reasons.append(f"Risk parameters acceptable ({risk_analysis.risk_percentage:.2f}% account risk)")
        else:
            rejection_reasons.extend([v.message for v in violations if v.auto_reject])

        # Fundamental-based decision
        if fundamental_score_val:
            if fundamental_score_val >= 70:
                approval_reasons.append(f"Strong fundamentals (score: {fundamental_score_val:.1f}/100)")
            elif fundamental_score_val < 40:
                rejection_reasons.append(f"Weak fundamentals (score: {fundamental_score_val:.1f}/100)")

        if risk_analysis.reward_risk_ratio and risk_analysis.reward_risk_ratio >= self.risk_agent.risk_settings.min_reward_risk_ratio:
            approval_reasons.append(f"Good reward/risk ratio ({risk_analysis.reward_risk_ratio:.2f}:1)")

        # Final recommendation
        if rejection_reasons:
            recommendation = "REJECT"
            confidence = "high"
        elif is_valid and (not fundamental_score_val or fundamental_score_val >= 50):
            recommendation = "BUY"
            confidence = "high" if fundamental_score_val and fundamental_score_val >= 70 else "medium"
        elif is_valid:
            recommendation = "HOLD"
            confidence = "medium"
        else:
            recommendation = "REJECT"
            confidence = "high"

        # Calculate combined score (weighted average)
        risk_score = 100 if is_valid else 0
        fund_score = fundamental_score_val if fundamental_score_val else 50
        combined_score = (risk_score * 0.4) + (fund_score * 0.6)

        return EnhancedTradeRecommendation(
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            risk_analysis=risk_analysis,
            risk_approved=is_valid,
            fundamental_score=fundamental_score_val,
            fundamental_recommendation=fundamental_rec,
            combined_score=combined_score,
            approval_reasons=approval_reasons,
            rejection_reasons=rejection_reasons,
            warnings=warnings
        )

    def batch_evaluate_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        max_recommendations: int = 5
    ) -> List[EnhancedTradeRecommendation]:
        """
        Evaluate multiple trading opportunities and rank them

        Args:
            opportunities: List of dicts with keys: symbol, entry_price, stop_loss, target_price
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of top recommendations, sorted by combined score
        """
        recommendations = []

        for opp in opportunities:
            try:
                rec = self.evaluate_trade_with_risk_and_fundamentals(
                    symbol=opp['symbol'],
                    entry_price=opp['entry_price'],
                    stop_loss=opp['stop_loss'],
                    target_price=opp.get('target_price'),
                    direction=TradeDirection[opp.get('direction', 'LONG')]
                )
                recommendations.append(rec)
            except Exception as e:
                print(f"Error evaluating {opp.get('symbol', 'UNKNOWN')}: {e}")
                continue

        # Sort by combined score (descending)
        recommendations.sort(key=lambda x: x.combined_score, reverse=True)

        # Assign priority ranks
        for i, rec in enumerate(recommendations[:max_recommendations], 1):
            rec.priority_rank = i

        return recommendations[:max_recommendations]

    def monitor_portfolio_risk_realtime(
        self,
        current_prices: Dict[str, float],
        alert_threshold: RiskLevel = RiskLevel.HIGH
    ) -> Tuple[PortfolioRiskMetrics, List[str]]:
        """
        Monitor portfolio risk in real-time and generate alerts

        Args:
            current_prices: Current market prices {symbol: price}
            alert_threshold: Minimum risk level to generate alerts

        Returns:
            Tuple of (portfolio metrics, list of alert messages)
        """
        # Update position prices
        positions = []
        for symbol, position in self._portfolio_cache.items():
            if symbol in current_prices:
                updated_pos = PositionRisk(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    current_price=current_prices[symbol],
                    current_value=position.quantity * current_prices[symbol],
                    stop_loss=position.stop_loss,
                    risk_amount=position.risk_amount,
                    risk_percentage=position.risk_percentage,
                    position_size_pct=(position.quantity * current_prices[symbol] /
                                     self.risk_agent.risk_settings.account_value) * 100,
                    unrealized_pl=(current_prices[symbol] - position.entry_price) * position.quantity,
                    unrealized_pl_pct=((current_prices[symbol] - position.entry_price) /
                                      position.entry_price) * 100 if position.entry_price > 0 else 0,
                    sector=position.sector,
                    days_held=position.days_held
                )
                positions.append(updated_pos)
            else:
                positions.append(position)

        # Analyze portfolio risk
        metrics = self.risk_agent.analyze_portfolio_risk(positions)

        # Generate alerts
        alerts = []

        if metrics.risk_level.value in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
            alerts.append(f"⚠️ Portfolio risk level: {metrics.risk_level.value.upper()}")

        if metrics.total_portfolio_risk_pct > self.risk_agent.risk_settings.max_total_risk_pct:
            alerts.append(
                f"⚠️ Total portfolio risk ({metrics.total_portfolio_risk_pct:.2f}%) exceeds limit "
                f"({self.risk_agent.risk_settings.max_total_risk_pct}%)"
            )

        # Check for positions hitting stop losses
        for pos in positions:
            if pos.stop_loss and pos.current_price <= pos.stop_loss:
                alerts.append(f"🛑 {pos.symbol} has hit stop loss at PKR {pos.stop_loss}")

        # Check for violations
        for violation in metrics.current_violations:
            if violation.severity == RiskLevel.HIGH or violation.severity == RiskLevel.CRITICAL:
                alerts.append(f"⚠️ {violation.message}")

        return metrics, alerts

    def generate_rebalancing_recommendations(
        self,
        target_risk_level: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Generate portfolio rebalancing recommendations

        Args:
            target_risk_level: Target risk level (0-1, where 0.5 = moderate)

        Returns:
            List of rebalancing actions
        """
        positions = list(self._portfolio_cache.values())
        metrics = self.risk_agent.analyze_portfolio_risk(positions)

        recommendations = []

        # If concentration is too high, recommend reducing largest positions
        if metrics.concentration_score > 70:
            for pos in sorted(positions, key=lambda x: x.position_size_pct, reverse=True)[:3]:
                if pos.position_size_pct > self.risk_agent.risk_settings.max_single_position_pct:
                    reduce_pct = pos.position_size_pct - self.risk_agent.risk_settings.max_single_position_pct
                    reduce_shares = int((reduce_pct / 100) * self.risk_agent.risk_settings.account_value / pos.current_price)

                    recommendations.append({
                        'action': 'REDUCE',
                        'symbol': pos.symbol,
                        'current_shares': pos.quantity,
                        'reduce_shares': reduce_shares,
                        'reason': f'Position size ({pos.position_size_pct:.1f}%) exceeds limit',
                        'priority': 'high'
                    })

        # If total risk is too high, recommend tightening stop losses
        if metrics.total_portfolio_risk_pct > self.risk_agent.risk_settings.max_total_risk_pct:
            for pos in positions:
                # Suggest tightening stop loss by 20%
                current_risk = pos.entry_price - pos.stop_loss if pos.stop_loss else 0
                new_stop = pos.current_price - (current_risk * 0.8)

                recommendations.append({
                    'action': 'TIGHTEN_STOP',
                    'symbol': pos.symbol,
                    'current_stop': pos.stop_loss,
                    'suggested_stop': new_stop,
                    'reason': 'Total portfolio risk exceeds limit',
                    'priority': 'medium'
                })

        # If diversification is poor, recommend adding positions
        if metrics.number_of_positions < self.risk_agent.risk_settings.min_positions:
            recommendations.append({
                'action': 'ADD_POSITION',
                'symbol': 'NEW',
                'quantity': 0,
                'reason': f'Only {metrics.number_of_positions} positions, need {self.risk_agent.risk_settings.min_positions} for diversification',
                'priority': 'high'
            })

        return recommendations

    def export_risk_report(
        self,
        format: str = "json",
        include_positions: bool = True
    ) -> str:
        """
        Export comprehensive risk report

        Args:
            format: Output format ("json" or "text")
            include_positions: Include individual position details

        Returns:
            Formatted risk report
        """
        positions = list(self._portfolio_cache.values())
        metrics = self.risk_agent.analyze_portfolio_risk(positions)

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "risk_settings": asdict(self.risk_agent.risk_settings),
            "portfolio_metrics": asdict(metrics),
            "positions": [asdict(pos) for pos in positions] if include_positions else [],
            "recommendations": self.generate_rebalancing_recommendations()
        }

        if format == "json":
            return json.dumps(report, indent=2)
        else:
            return self._format_text_report(report)

    def _format_text_report(self, report: Dict) -> str:
        """Format report as text"""
        lines = [
            "=" * 100,
            "PORTFOLIO & RISK MANAGEMENT REPORT",
            "=" * 100,
            f"Generated: {report['report_timestamp']}",
            "",
            "=" * 100,
            "PORTFOLIO OVERVIEW",
            "=" * 100,
            f"Total Positions: {report['portfolio_metrics']['number_of_positions']}",
            f"Total Value: PKR {report['portfolio_metrics']['total_value']:,.2f}",
            f"Invested: PKR {report['portfolio_metrics']['total_invested']:,.2f}",
            f"Cash: PKR {report['portfolio_metrics']['cash_balance']:,.2f}",
            "",
            "=" * 100,
            "RISK METRICS",
            "=" * 100,
            f"Portfolio Risk Level: {report['portfolio_metrics']['risk_level'].upper()}",
            f"Total Risk: {report['portfolio_metrics']['total_portfolio_risk_pct']:.2f}%",
            f"Diversification Score: {report['portfolio_metrics']['diversification_score']:.1f}/100",
            f"Concentration Score: {report['portfolio_metrics']['concentration_score']:.1f}/100",
            "",
        ]

        if report['portfolio_metrics']['current_violations']:
            lines.append("=" * 100)
            lines.append("RISK VIOLATIONS")
            lines.append("=" * 100)
            for v in report['portfolio_metrics']['current_violations']:
                lines.append(f"  • [{v['severity'].upper()}] {v['message']}")
            lines.append("")

        if report['recommendations']:
            lines.append("=" * 100)
            lines.append("REBALANCING RECOMMENDATIONS")
            lines.append("=" * 100)
            for i, rec in enumerate(report['recommendations'], 1):
                lines.append(f"{i}. {rec['action']} - {rec['symbol']}: {rec['reason']}")
            lines.append("")

        lines.append("=" * 100)

        return "\n".join(lines)


# Utility functions

def create_portfolio_manager_with_defaults(
    account_value: float,
    risk_profile: str = "moderate"
) -> PortfolioRiskManager:
    """
    Create portfolio risk manager with default settings

    Args:
        account_value: Total account value
        risk_profile: "conservative", "moderate", or "aggressive"

    Returns:
        Configured PortfolioRiskManager
    """
    if risk_profile == "conservative":
        risk_settings = create_default_risk_settings(account_value)
        risk_settings.max_risk_per_trade_pct = 1.0
        risk_settings.max_position_size_pct = 8.0
    elif risk_profile == "aggressive":
        risk_settings = create_aggressive_risk_settings(account_value)
    else:  # moderate
        risk_settings = create_default_risk_settings(account_value)

    risk_agent = PSXRiskAgent(risk_settings)

    # Initialize fundamental agent if available
    fundamental_agent = None
    if HAS_FUNDAMENTAL_AGENT:
        try:
            fundamental_agent = PSXFundamentalAgent()
        except:
            pass

    return PortfolioRiskManager(risk_agent, fundamental_agent)


if __name__ == "__main__":
    print("Portfolio-Risk Integration Module - Example Usage\n")
    print("=" * 100)

    # Example: Create portfolio manager
    manager = create_portfolio_manager_with_defaults(
        account_value=2_000_000,  # 2M PKR
        risk_profile="moderate"
    )

    print("✓ Portfolio Risk Manager created with moderate risk profile")
    print(f"  Account Value: PKR 2,000,000")
    print(f"  Max Risk Per Trade: {manager.risk_agent.risk_settings.max_risk_per_trade_pct}%")
    print(f"  Max Position Size: {manager.risk_agent.risk_settings.max_position_size_pct}%")

    # Example: Evaluate a trade
    print("\n" + "=" * 100)
    print("EXAMPLE: Trade Evaluation with Risk Analysis")
    print("=" * 100)

    recommendation = manager.evaluate_trade_with_risk_and_fundamentals(
        symbol="ENGRO",
        entry_price=300.0,
        stop_loss=285.0,
        target_price=345.0,
        analyze_fundamentals=False  # Set to True if fundamental agent is available
    )

    print(f"\nSymbol: {recommendation.symbol}")
    print(f"Recommendation: {recommendation.recommendation} (Confidence: {recommendation.confidence})")
    print(f"Combined Score: {recommendation.combined_score:.1f}/100")
    print(f"Risk Approved: {recommendation.risk_approved}")
    print(f"Position Size: {recommendation.risk_analysis.recommended_shares} shares")
    print(f"Position Value: PKR {recommendation.risk_analysis.position_value:,.0f}")
    print(f"Risk Amount: PKR {recommendation.risk_analysis.risk_amount:,.0f}")
    print(f"Reward/Risk: {recommendation.risk_analysis.reward_risk_ratio:.2f}:1")

    if recommendation.approval_reasons:
        print("\n✓ Approval Reasons:")
        for reason in recommendation.approval_reasons:
            print(f"  • {reason}")

    if recommendation.rejection_reasons:
        print("\n✗ Rejection Reasons:")
        for reason in recommendation.rejection_reasons:
            print(f"  • {reason}")

    if recommendation.warnings:
        print("\n⚠ Warnings:")
        for warning in recommendation.warnings:
            print(f"  • {warning}")

    print("\n" + "=" * 100)
    print("✓ Integration module loaded successfully")
    print("=" * 100)
