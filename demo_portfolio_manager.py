#!/usr/bin/env python3
"""
Demo: PSX Portfolio Manager

Demonstrates portfolio manager with real data for a small set of stocks.
Shows all three models side-by-side with detailed reasoning.
"""

from datetime import datetime

from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_fundamental_agent import PSXFundamentalAgent
from psx_portfolio_manager import PSXPortfolioManager
from psx_portfolio_store import PSXPortfolioStore
from psx_portfolio_models import PortfolioConfig
from psx_portfolio_utils import format_money, format_percentage


def demo_portfolio_manager():
    """Demo portfolio manager with real data"""

    print("="*100)
    print("💼 PSX PORTFOLIO MANAGER DEMO")
    print("="*100)
    print(f"Demo Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)

    # Select a small set of stocks for demo
    symbols = ['HBL', 'LUCK', 'OGDC', 'ENGRO', 'PPL']

    print(f"\nDemo Portfolio:")
    print(f"   Initial Cash: PKR 1,000,000")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Models: Conservative, Balanced, Aggressive")

    # Step 1: Price Data
    print(f"\n📊 STEP 1: Fetching Price Data")
    print("-"*100)

    price_store = PSXPriceStore()
    print(f"Updating price store for {len(symbols)} stocks...")
    price_store.bulk_update(symbols, days=250)
    print(f"✅ Price data loaded")

    # Step 2: Technical Analysis
    print(f"\n📈 STEP 2: Technical Analysis")
    print("-"*100)

    tech_agent = PSXTechnicalAgent(price_store)
    technical_snapshots = {}

    for symbol in symbols:
        print(f"   Analyzing {symbol}...", end=" ")
        snapshot = tech_agent.analyze_symbol(symbol)
        technical_snapshots[symbol] = snapshot
        print(f"{snapshot.overall_bias.value} ({snapshot.confidence:.0%})")

    print(f"✅ Technical analysis complete")

    # Step 3: Fundamental Analysis
    print(f"\n📊 STEP 3: Fundamental Analysis")
    print("-"*100)

    fund_agent = PSXFundamentalAgent(price_store=price_store)
    fundamental_scores = {}

    for symbol in symbols:
        print(f"   Analyzing {symbol}...", end=" ")
        try:
            score = fund_agent.quick_analysis(symbol)
            fundamental_scores[symbol] = score
            print(f"{score.recommendation.value} (Score: {score.fundamental_score:.0f}/100)")
        except Exception as e:
            print(f"ERROR: {str(e)}")

    print(f"✅ Fundamental analysis complete")

    # Step 4: Get Current Prices
    print(f"\n💰 STEP 4: Current Prices")
    print("-"*100)

    current_prices = {}
    for symbol in symbols:
        df = price_store.get_prices(symbol, days=1)
        if not df.empty:
            price = float(df['Close'].iloc[-1])
            current_prices[symbol] = price
            print(f"   {symbol}: {format_money(price)}")

    print(f"✅ Current prices retrieved")

    # Step 5: Portfolio Manager
    print(f"\n💼 STEP 5: Portfolio Manager Analysis")
    print("-"*100)

    # Initialize portfolio
    config = PortfolioConfig(
        name="demo",
        initial_cash=1_000_000.0
    )

    portfolio_store = PSXPortfolioStore()
    portfolio_manager = PSXPortfolioManager(portfolio_store, config)

    # Run all three models
    models = ["conservative", "balanced", "aggressive"]
    outputs = {}

    for model_name in models:
        print(f"\nRunning {model_name.upper()} model...")
        output = portfolio_manager.analyze_portfolio(
            model_name=model_name,
            symbols=symbols,
            current_prices=current_prices,
            technical_snapshots=technical_snapshots,
            fundamental_scores=fundamental_scores,
            anomalies=[],
            correlations=None
        )
        outputs[model_name] = output
        print(f"   Recommendations: {len(output.recommended_trades)}")
        print(f"   Excluded: {len(output.excluded_trades)}")

    print(f"\n✅ Portfolio analysis complete")

    # Print Results
    print_detailed_results(outputs, symbols, current_prices)

    print("\n" + "="*100)
    print("✅ DEMO COMPLETE")
    print("="*100)
    print(f"Database: {portfolio_store.db_path}")
    print(f"View decisions with: sqlite3 {portfolio_store.db_path}")
    print("="*100)


def print_detailed_results(outputs, symbols, current_prices):
    """Print detailed comparison of all models"""

    print("\n" + "="*100)
    print("📈 MODEL COMPARISON")
    print("="*100)

    # Header
    print(f"\n{'Symbol':<10} {'Price':<12} {'Conservative':<22} {'Balanced':<22} {'Aggressive':<22}")
    print("-"*100)

    # Each symbol
    for symbol in symbols:
        row = f"{symbol:<10} {format_money(current_prices.get(symbol, 0)):<12}"

        for model_name in ["conservative", "balanced", "aggressive"]:
            output = outputs[model_name]
            decision = output.decisions.get(symbol)

            if decision:
                if decision.action.value == "HOLD":
                    cell = "HOLD"
                else:
                    cell = f"{decision.action.value} {int(decision.quantity)}"
                cell += f" ({decision.composite_score:.0f})"
            else:
                cell = "---"

            row += f" {cell:<22}"

        print(row)

    # Detailed recommendations for each model
    for model_name in ["conservative", "balanced", "aggressive"]:
        output = outputs[model_name]

        print("\n" + "="*100)
        print(f"🎯 {model_name.upper()} MODEL - DETAILED RECOMMENDATIONS")
        print("="*100)

        if output.recommended_trades:
            print(f"\n📋 RECOMMENDED TRADES ({len(output.recommended_trades)}):")

            for i, decision in enumerate(output.recommended_trades, 1):
                signal = output.signals[decision.symbol]

                print(f"\n{i}. {decision.symbol} - {decision.action.value} {int(decision.quantity):,} shares")
                print(f"   Target Price: {format_money(decision.target_price)}")
                print(f"   Position Value: {format_money(decision.position_value)}")
                print(f"   Position Size: {format_percentage(decision.position_size_pct)} of portfolio")
                print(f"   Composite Score: {decision.composite_score:.1f}/100")
                print(f"   Confidence: {decision.confidence:.0%}")

                print(f"\n   Signal Breakdown:")
                print(f"      Technical:   {signal.technical_score:>5.0f}/100  ({signal.technical_bias})")
                print(f"      Fundamental: {signal.fundamental_score:>5.0f}/100  ({signal.fundamental_rec})")
                print(f"      Anomaly:     {signal.anomaly_score:>5.0f}/100")
                print(f"      News:        {signal.news_sentiment_score:>5.0f}/100")

                print(f"\n   Reasoning:")
                for reason in decision.reasoning:
                    print(f"      {reason}")

                if signal.red_flags:
                    print(f"\n   ⚠️  Red Flags:")
                    for flag in signal.red_flags:
                        print(f"      • {flag}")

        else:
            print("\n   No actionable recommendations for this model")

        # Show HOLDs
        holds = [d for d in output.decisions.values() if d.action.value == "HOLD"]
        if holds:
            print(f"\n   📊 HOLD Decisions ({len(holds)}):")
            for decision in holds:
                print(f"      {decision.symbol}: Score {decision.composite_score:.0f}/100, Confidence {decision.confidence:.0%}")
                print(f"         Reason: {decision.reasoning[0] if decision.reasoning else 'Insufficient signal strength'}")

        # Show excluded
        if output.excluded_trades:
            print(f"\n   ⚠️  EXCLUDED (Constraint Violations):")
            for decision in output.excluded_trades:
                print(f"      {decision.symbol}: {decision.action.value} (Score: {decision.composite_score:.0f}/100)")
                for violation in decision.constraint_violations:
                    print(f"         • {violation}")


if __name__ == "__main__":
    demo_portfolio_manager()
