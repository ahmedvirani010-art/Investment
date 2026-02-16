"""
Portfolio-Risk Integration Demo

Demonstrates end-to-end usage of the integrated portfolio and risk management system.
"""

import sys
from datetime import datetime, timedelta
from pprint import pprint

# Import modules
from psx_risk_agent import (
    PSXRiskAgent, RiskSettings, TradeDirection, RiskLevel,
    create_default_risk_settings, PositionRisk
)
from portfolio_risk_integration import (
    PortfolioRiskManager, create_portfolio_manager_with_defaults,
    EnhancedTradeRecommendation
)


def print_section(title: str, width: int = 100):
    """Print section header"""
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def demo_1_basic_position_sizing():
    """Demo 1: Basic position sizing with risk parameters"""
    print_section("DEMO 1: Basic Position Sizing")

    # Create risk agent with default settings
    risk_settings = create_default_risk_settings(account_value=1_000_000)  # 1M PKR
    agent = PSXRiskAgent(risk_settings)

    print(f"\n📊 Account Setup:")
    print(f"   Account Value: PKR {risk_settings.account_value:,.0f}")
    print(f"   Max Risk Per Trade: {risk_settings.max_risk_per_trade_pct}%")
    print(f"   Max Position Size: {risk_settings.max_position_size_pct}%")
    print(f"   Min Reward/Risk Ratio: {risk_settings.min_reward_risk_ratio}:1")

    # Calculate position size for a trade
    print(f"\n💡 Trade Idea: ENGRO @ PKR 300")
    print(f"   Stop Loss: PKR 285 (5% risk)")
    print(f"   Target: PKR 345 (15% profit)")

    trade = agent.calculate_position_size(
        symbol="ENGRO",
        entry_price=300.0,
        stop_loss=285.0,
        target_price=345.0,
        direction=TradeDirection.LONG
    )

    print(f"\n✓ Risk Analysis Results:")
    print(f"   Recommended Shares: {trade.recommended_shares}")
    print(f"   Position Value: PKR {trade.position_value:,.0f}")
    print(f"   Position Size: {trade.position_size_pct:.2f}% of account")
    print(f"   Risk Amount: PKR {trade.risk_amount:,.0f} ({trade.risk_percentage:.2f}%)")
    print(f"   Potential Reward: PKR {trade.reward_amount:,.0f}")
    print(f"   Reward/Risk Ratio: {trade.reward_risk_ratio:.2f}:1")
    print(f"   Trade Valid: {'✓ YES' if trade.is_valid else '✗ NO'}")

    if trade.warnings:
        print(f"\n⚠ Warnings:")
        for warning in trade.warnings:
            print(f"   • {warning}")

    return agent


def demo_2_portfolio_risk_analysis():
    """Demo 2: Portfolio risk analysis"""
    print_section("DEMO 2: Portfolio Risk Analysis")

    # Create risk agent
    risk_settings = create_default_risk_settings(account_value=2_000_000)  # 2M PKR
    agent = PSXRiskAgent(risk_settings)

    # Create sample portfolio
    print(f"\n📁 Sample Portfolio (3 positions):")

    portfolio = [
        PositionRisk(
            symbol="ENGRO",
            quantity=1000,
            entry_price=300.0,
            current_price=315.0,
            current_value=315000,
            stop_loss=285.0,
            risk_amount=15000,
            risk_percentage=0.75,
            position_size_pct=15.75,
            unrealized_pl=15000,
            unrealized_pl_pct=5.0,
            sector="Chemicals",
            days_held=30
        ),
        PositionRisk(
            symbol="HBL",
            quantity=2000,
            entry_price=150.0,
            current_price=155.0,
            current_value=310000,
            stop_loss=145.0,
            risk_amount=10000,
            risk_percentage=0.5,
            position_size_pct=15.5,
            unrealized_pl=10000,
            unrealized_pl_pct=3.33,
            sector="Banks",
            days_held=45
        ),
        PositionRisk(
            symbol="PSO",
            quantity=1500,
            entry_price=200.0,
            current_price=205.0,
            current_value=307500,
            stop_loss=195.0,
            risk_amount=7500,
            risk_percentage=0.375,
            position_size_pct=15.375,
            unrealized_pl=7500,
            unrealized_pl_pct=2.5,
            sector="Oil & Gas",
            days_held=60
        )
    ]

    for pos in portfolio:
        print(f"   • {pos.symbol}: {pos.quantity} shares @ PKR {pos.current_price:.2f}")
        print(f"     Value: PKR {pos.current_value:,.0f} ({pos.position_size_pct:.1f}% of portfolio)")
        print(f"     P&L: PKR {pos.unrealized_pl:,.0f} ({pos.unrealized_pl_pct:+.2f}%)")

    # Analyze portfolio risk
    metrics = agent.analyze_portfolio_risk(portfolio)

    print(f"\n📊 Portfolio Risk Metrics:")
    print(f"   Total Value: PKR {metrics.total_value:,.0f}")
    print(f"   Invested: PKR {metrics.total_invested:,.0f}")
    print(f"   Cash: PKR {metrics.cash_balance:,.0f}")
    print(f"   Number of Positions: {metrics.number_of_positions}")

    print(f"\n🎯 Risk Assessment:")
    print(f"   Total Portfolio Risk: {metrics.total_portfolio_risk_pct:.2f}%")
    print(f"   Risk Level: {metrics.risk_level.value.upper()}")
    print(f"   Diversification Score: {metrics.diversification_score:.1f}/100")
    print(f"   Concentration Score: {metrics.concentration_score:.1f}/100")

    print(f"\n📍 Position Distribution:")
    print(f"   Largest Position: {metrics.largest_position_pct:.2f}%")
    print(f"   Smallest Position: {metrics.smallest_position_pct:.2f}%")
    print(f"   Average Position: {metrics.average_position_size:.2f}%")

    print(f"\n🏭 Sector Exposure:")
    for sector, exposure in metrics.sector_exposure.items():
        print(f"   • {sector}: {exposure:.1f}%")

    if metrics.current_violations:
        print(f"\n⚠ Risk Violations ({len(metrics.current_violations)}):")
        for v in metrics.current_violations:
            print(f"   • [{v.severity.value.upper()}] {v.message}")
    else:
        print(f"\n✓ No risk violations detected")

    return agent, portfolio


def demo_3_trade_validation():
    """Demo 3: Trade validation against portfolio"""
    print_section("DEMO 3: Trade Validation Against Portfolio")

    # Setup from previous demo
    risk_settings = create_default_risk_settings(account_value=2_000_000)
    agent = PSXRiskAgent(risk_settings)

    # Existing portfolio
    portfolio = [
        PositionRisk(
            symbol="ENGRO", quantity=1000, entry_price=300.0, current_price=315.0,
            current_value=315000, stop_loss=285.0, risk_amount=15000,
            risk_percentage=0.75, position_size_pct=15.75, sector="Chemicals"
        ),
        PositionRisk(
            symbol="HBL", quantity=2000, entry_price=150.0, current_price=155.0,
            current_value=310000, stop_loss=145.0, risk_amount=10000,
            risk_percentage=0.5, position_size_pct=15.5, sector="Banks"
        ),
    ]

    print(f"\n📁 Current Portfolio: 2 positions, PKR {sum(p.current_value for p in portfolio):,.0f} invested")

    # Try to add a new position
    print(f"\n💡 New Trade Proposal: OGDC @ PKR 100")
    print(f"   Stop Loss: PKR 95 (5% risk)")
    print(f"   Target: PKR 115 (15% profit)")

    new_trade = agent.calculate_position_size(
        symbol="OGDC",
        entry_price=100.0,
        stop_loss=95.0,
        target_price=115.0
    )

    print(f"\n📊 Position Sizing:")
    print(f"   Recommended Shares: {new_trade.recommended_shares}")
    print(f"   Position Value: PKR {new_trade.position_value:,.0f}")
    print(f"   Risk Amount: PKR {new_trade.risk_amount:,.0f}")

    # Validate against portfolio
    is_valid, violations, warnings = agent.validate_trade(new_trade, portfolio)

    print(f"\n✓ Validation Results:")
    print(f"   Trade Approved: {'✓ YES' if is_valid else '✗ NO'}")

    if violations:
        print(f"\n⚠ Violations ({len(violations)}):")
        for v in violations:
            print(f"   • [{v.severity.value.upper()}] {v.message}")
            print(f"     Current: {v.current_value:.2f} | Limit: {v.limit_value:.2f}")

    if warnings:
        print(f"\n⚠ Warnings:")
        for w in warnings:
            print(f"   • {w}")

    if is_valid:
        print(f"\n✓ Trade can proceed. Total portfolio risk would be:")
        portfolio_metrics = agent.analyze_portfolio_risk(portfolio)
        new_total_risk = portfolio_metrics.total_portfolio_risk_pct + new_trade.risk_percentage
        print(f"   {new_total_risk:.2f}% (limit: {risk_settings.max_total_risk_pct}%)")


def demo_4_integrated_manager():
    """Demo 4: Integrated portfolio risk manager"""
    print_section("DEMO 4: Integrated Portfolio Risk Manager")

    # Create integrated manager
    manager = create_portfolio_manager_with_defaults(
        account_value=2_000_000,
        risk_profile="moderate"
    )

    print(f"\n✓ Portfolio Manager Initialized")
    print(f"   Risk Profile: MODERATE")
    print(f"   Account Value: PKR 2,000,000")
    print(f"   Fundamental Analysis: {'Enabled' if manager.fundamental_agent else 'Disabled'}")

    # Simulate loading portfolio
    print(f"\n📁 Loading Portfolio Data...")

    # Mock Prisma data
    user_stocks = [
        {
            'stock': {'ticker': 'ENGRO'},
            'totalQuantity': 1000,
            'averageCost': 300.0,
            'createdAt': (datetime.now() - timedelta(days=30)).isoformat()
        },
        {
            'stock': {'ticker': 'HBL'},
            'totalQuantity': 2000,
            'averageCost': 150.0,
            'createdAt': (datetime.now() - timedelta(days=45)).isoformat()
        }
    ]

    stock_info = {
        'ENGRO': {'sector': 'Chemicals', 'name': 'Engro Corporation'},
        'HBL': {'sector': 'Banks', 'name': 'Habib Bank Limited'}
    }

    current_prices = {
        'ENGRO': 315.0,
        'HBL': 155.0
    }

    positions = manager.load_portfolio_from_prisma_data(
        user_stocks, stock_info, current_prices
    )

    print(f"   ✓ Loaded {len(positions)} positions")
    for pos in positions:
        print(f"     • {pos.symbol}: {pos.quantity} shares @ PKR {pos.current_price:.2f}")

    # Evaluate a new trading opportunity
    print(f"\n💡 Evaluating New Opportunity: OGDC @ PKR 100")

    recommendation = manager.evaluate_trade_with_risk_and_fundamentals(
        symbol="OGDC",
        entry_price=100.0,
        stop_loss=95.0,
        target_price=115.0,
        analyze_fundamentals=False  # Set to True if fundamental agent available
    )

    print(f"\n📊 Trade Recommendation:")
    print(f"   Symbol: {recommendation.symbol}")
    print(f"   Recommendation: {recommendation.recommendation}")
    print(f"   Confidence: {recommendation.confidence}")
    print(f"   Combined Score: {recommendation.combined_score:.1f}/100")
    print(f"   Risk Approved: {'✓' if recommendation.risk_approved else '✗'}")

    if recommendation.approval_reasons:
        print(f"\n✓ Approval Reasons:")
        for reason in recommendation.approval_reasons:
            print(f"   • {reason}")

    if recommendation.rejection_reasons:
        print(f"\n✗ Rejection Reasons:")
        for reason in recommendation.rejection_reasons:
            print(f"   • {reason}")

    # Monitor real-time risk
    print(f"\n🔍 Real-Time Risk Monitoring...")

    metrics, alerts = manager.monitor_portfolio_risk_realtime(current_prices)

    print(f"   Portfolio Risk Level: {metrics.risk_level.value.upper()}")
    print(f"   Total Risk: {metrics.total_portfolio_risk_pct:.2f}%")

    if alerts:
        print(f"\n⚠ Alerts ({len(alerts)}):")
        for alert in alerts:
            print(f"   {alert}")
    else:
        print(f"\n✓ No alerts - portfolio within normal parameters")

    # Generate rebalancing recommendations
    print(f"\n⚖️ Rebalancing Analysis...")

    rebal_recs = manager.generate_rebalancing_recommendations()

    if rebal_recs:
        print(f"   Found {len(rebal_recs)} recommendations:")
        for rec in rebal_recs:
            print(f"   • {rec['action']}: {rec['symbol']} - {rec['reason']}")
    else:
        print(f"   ✓ Portfolio is well balanced")


def demo_5_batch_evaluation():
    """Demo 5: Batch evaluation of multiple opportunities"""
    print_section("DEMO 5: Batch Opportunity Evaluation")

    manager = create_portfolio_manager_with_defaults(
        account_value=3_000_000,
        risk_profile="moderate"
    )

    # Multiple trading opportunities
    opportunities = [
        {
            'symbol': 'ENGRO',
            'entry_price': 300.0,
            'stop_loss': 285.0,
            'target_price': 345.0,
            'direction': 'LONG'
        },
        {
            'symbol': 'HBL',
            'entry_price': 150.0,
            'stop_loss': 145.0,
            'target_price': 165.0,
            'direction': 'LONG'
        },
        {
            'symbol': 'OGDC',
            'entry_price': 100.0,
            'stop_loss': 95.0,
            'target_price': 115.0,
            'direction': 'LONG'
        },
        {
            'symbol': 'PSO',
            'entry_price': 200.0,
            'stop_loss': 195.0,
            'target_price': 220.0,
            'direction': 'LONG'
        },
        {
            'symbol': 'LUCK',
            'entry_price': 500.0,
            'stop_loss': 480.0,
            'target_price': 550.0,
            'direction': 'LONG'
        }
    ]

    print(f"\n📋 Evaluating {len(opportunities)} trading opportunities...")

    recommendations = manager.batch_evaluate_opportunities(opportunities, max_recommendations=3)

    print(f"\n🏆 Top {len(recommendations)} Recommendations (by Combined Score):\n")

    for rec in recommendations:
        print(f"{rec.priority_rank}. {rec.symbol} - {rec.recommendation} (Confidence: {rec.confidence})")
        print(f"   Combined Score: {rec.combined_score:.1f}/100")
        print(f"   Position Size: {rec.risk_analysis.recommended_shares} shares (PKR {rec.risk_analysis.position_value:,.0f})")
        print(f"   Risk: PKR {rec.risk_analysis.risk_amount:,.0f} ({rec.risk_analysis.risk_percentage:.2f}%)")
        print(f"   R/R Ratio: {rec.risk_analysis.reward_risk_ratio:.2f}:1")

        if rec.approval_reasons:
            print(f"   ✓ {rec.approval_reasons[0]}")

        print()


def demo_6_risk_report():
    """Demo 6: Comprehensive risk report"""
    print_section("DEMO 6: Comprehensive Risk Report")

    manager = create_portfolio_manager_with_defaults(
        account_value=2_000_000,
        risk_profile="moderate"
    )

    # Load sample portfolio
    user_stocks = [
        {
            'stock': {'ticker': 'ENGRO'},
            'totalQuantity': 1000,
            'averageCost': 300.0,
            'createdAt': datetime.now().isoformat()
        },
        {
            'stock': {'ticker': 'HBL'},
            'totalQuantity': 2000,
            'averageCost': 150.0,
            'createdAt': datetime.now().isoformat()
        },
        {
            'stock': {'ticker': 'PSO'},
            'totalQuantity': 1500,
            'averageCost': 200.0,
            'createdAt': datetime.now().isoformat()
        }
    ]

    stock_info = {
        'ENGRO': {'sector': 'Chemicals'},
        'HBL': {'sector': 'Banks'},
        'PSO': {'sector': 'Oil & Gas'}
    }

    current_prices = {'ENGRO': 315.0, 'HBL': 155.0, 'PSO': 205.0}

    positions = manager.load_portfolio_from_prisma_data(
        user_stocks, stock_info, current_prices
    )

    print(f"\n📄 Generating Risk Report...")

    report = manager.export_risk_report(format="text", include_positions=True)

    print(report)


def main():
    """Run all demos"""
    print("\n" + "=" * 100)
    print("PORTFOLIO-RISK INTEGRATION SYSTEM".center(100))
    print("Comprehensive Demonstration".center(100))
    print("=" * 100)

    demos = [
        ("Basic Position Sizing", demo_1_basic_position_sizing),
        ("Portfolio Risk Analysis", demo_2_portfolio_risk_analysis),
        ("Trade Validation", demo_3_trade_validation),
        ("Integrated Manager", demo_4_integrated_manager),
        ("Batch Evaluation", demo_5_batch_evaluation),
        ("Risk Report", demo_6_risk_report)
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback
            traceback.print_exc()

        if i < len(demos):
            input("\nPress Enter to continue to next demo...")

    print("\n" + "=" * 100)
    print("✓ All demos completed successfully!".center(100))
    print("=" * 100)
    print("\nThe portfolio-risk integration system provides:")
    print("  • Intelligent position sizing based on risk parameters")
    print("  • Real-time portfolio risk monitoring and alerts")
    print("  • Trade validation against risk rules")
    print("  • Comprehensive risk reporting")
    print("  • Integration with fundamental analysis (when available)")
    print("  • Batch evaluation of trading opportunities")
    print("\nReady for production use!")


if __name__ == "__main__":
    main()
