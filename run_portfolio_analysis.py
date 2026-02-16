#!/usr/bin/env python3
"""
PSX Portfolio Analysis
Runs full analysis pipeline and generates portfolio recommendations
"""

import argparse
from datetime import datetime
from typing import List

from psx_liquidity_screener import PSXLiquidityScreener
from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_fundamental_agent import PSXFundamentalAgent
from psx_anomaly_agent import PSXAnomalyAgent
from psx_news_agent import PSXNewsAgent
from psx_news_anomaly_correlator import NewsAnomalyCorrelator
from psx_portfolio_manager import PSXPortfolioManager
from psx_portfolio_store import PSXPortfolioStore
from psx_portfolio_models import PortfolioConfig, PORTFOLIO_MODELS
from psx_portfolio_utils import format_money, format_percentage, format_price


def print_model_comparison(outputs: dict):
    """
    Print side-by-side comparison of all models

    Args:
        outputs: Dictionary of model_name -> PortfolioManagerOutput
    """
    print("\n" + "="*100)
    print("📈 MODEL COMPARISON")
    print("="*100)

    # Get all symbols (union of all models' decisions)
    all_symbols = set()
    for output in outputs.values():
        all_symbols.update(output.decisions.keys())
    all_symbols = sorted(all_symbols)

    # Print header
    print(f"\n{'Symbol':<10} {'Conservative':<25} {'Balanced':<25} {'Aggressive':<25}")
    print("-"*100)

    # Print each symbol
    for symbol in all_symbols:
        row = f"{symbol:<10}"

        for model_name in ["conservative", "balanced", "aggressive"]:
            output = outputs.get(model_name)
            if not output or symbol not in output.decisions:
                row += f"{'---':<25}"
                continue

            decision = output.decisions[symbol]

            if decision.action.value == "HOLD":
                cell = "HOLD"
            else:
                qty_str = f"{int(decision.quantity)}"
                cell = f"{decision.action.value} {qty_str}"

            # Add score
            cell += f" (Score: {decision.composite_score:.0f})"

            # Truncate if too long
            cell = cell[:24]
            row += f"{cell:<25}"

        print(row)

    print()


def print_recommendations(output, model_name: str):
    """
    Print detailed recommendations for one model

    Args:
        output: PortfolioManagerOutput
        model_name: Model name
    """
    print("\n" + "="*100)
    print(f"🎯 {model_name.upper()} MODEL RECOMMENDATIONS")
    print("="*100)

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total Symbols Analyzed: {len(output.decisions)}")
    print(f"   BUY Signals:    {output.total_buy_signals}")
    print(f"   SELL Signals:   {output.total_sell_signals}")
    print(f"   REDUCE Signals: {output.total_reduce_signals}")
    print(f"   HOLD Signals:   {output.total_hold_signals}")
    print(f"   Recommended Trades (actionable): {len(output.recommended_trades)}")
    print(f"   Excluded Trades (constraint violations): {len(output.excluded_trades)}")

    # Print actionable recommendations
    if output.recommended_trades:
        print(f"\n📋 RECOMMENDED TRADES ({len(output.recommended_trades)}):")
        print("-"*100)

        for i, decision in enumerate(output.recommended_trades, 1):
            print(f"\n{i}. {decision.symbol} - {decision.action.value} {int(decision.quantity):,} shares @ {format_price(decision.target_price)}")
            print(f"   Composite Score: {decision.composite_score:.1f}/100 | Confidence: {decision.confidence:.0%} | Position Size: {format_percentage(decision.position_size_pct)}")

            # Signal breakdown
            signal = output.signals.get(decision.symbol)
            if signal:
                print(f"\n   Signal Breakdown:")
                print(f"   • Technical:   {signal.technical_score:>5.0f}/100 ({signal.technical_bias})")
                print(f"   • Fundamental: {signal.fundamental_score:>5.0f}/100 ({signal.fundamental_rec})")
                print(f"   • Anomaly:     {signal.anomaly_score:>5.0f}/100 {'(Detected: ' + signal.anomaly_severity + ')' if signal.has_anomaly else '(None)'}")
                print(f"   • News:        {signal.news_sentiment_score:>5.0f}/100")

            # Reasoning
            print(f"\n   Reasoning:")
            for reason in decision.reasoning:
                print(f"   {reason}")

            # Red flags
            if signal and signal.red_flags:
                print(f"\n   ⚠️  Red Flags:")
                for flag in signal.red_flags[:3]:  # Show max 3
                    print(f"   • {flag}")

            if i < len(output.recommended_trades):
                print()

    # Print excluded trades
    if output.excluded_trades:
        print(f"\n⚠️  EXCLUDED TRADES (Constraint Violations):")
        print("-"*100)

        for decision in output.excluded_trades:
            print(f"\n{decision.symbol} - {decision.action.value} (Score: {decision.composite_score:.0f}/100, Confidence: {decision.confidence:.0%})")
            print(f"   Violations:")
            for violation in decision.constraint_violations:
                print(f"   • {violation}")

    print()


def run_portfolio_analysis(
    use_liquid_stocks: bool = True,
    top_n: int = 20,
    initial_cash: float = 1_000_000.0,
    portfolio_name: str = "default",
    models: List[str] = None,
    symbols: List[str] = None
):
    """
    Run complete portfolio analysis with multiple models

    Args:
        use_liquid_stocks: Use liquidity screener for stock selection
        top_n: Number of top liquid stocks to analyze
        initial_cash: Initial portfolio cash (PKR)
        portfolio_name: Portfolio name
        models: List of models to run (default: all three)
        symbols: Optional list of specific symbols to analyze
    """
    print("="*100)
    print("💼 PSX PORTFOLIO ANALYSIS")
    print("="*100)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Portfolio: {portfolio_name}")
    print(f"Initial Cash: {format_money(initial_cash)}")
    print("="*100)

    # Default to all models if not specified
    if not models:
        models = ["conservative", "balanced", "aggressive"]

    # Step 1: Get stock symbols to analyze
    print("\n📋 STEP 1: Stock Selection")
    print("-"*100)

    if symbols:
        # Use provided symbols
        print(f"✅ Using provided list of {len(symbols)} stocks")
        print(f"   Symbols: {', '.join(symbols[:10])}")
        if len(symbols) > 10:
            print(f"   ... and {len(symbols) - 10} more")
    elif use_liquid_stocks:
        print(f"🔍 Using liquidity screener to select top {top_n} stocks...")
        screener = PSXLiquidityScreener(lookback_days=30, min_price=20.0)
        liquid_stocks = screener.screen_stocks(top_n=top_n)
        symbols = [stock.symbol for stock in liquid_stocks]
        print(f"✅ Selected {len(symbols)} liquid stocks")
        print(f"   Top 10: {', '.join(symbols[:10])}")
    else:
        # Use predefined list
        symbols = [
            'HBL', 'UBL', 'MCB', 'BAFL', 'ABL',
            'OGDC', 'PPL', 'PSO', 'APL', 'POL',
            'LUCK', 'DGKC', 'MLCF', 'FCCL',
            'FFC', 'EFERT', 'FATIMA',
            'HUBC', 'KAPCO', 'ENGRO'
        ]
        print(f"✅ Using predefined list of {len(symbols)} stocks")

    # Step 2: Price Data Sync
    print(f"\n💾 STEP 2: Price Data Sync")
    print("-"*100)
    print(f"🔍 Updating price store with 250 days of history...")

    price_store = PSXPriceStore()
    price_store.bulk_update(symbols, days=250)

    stats = price_store.get_stats()
    print(f"✅ Price store updated")
    print(f"   Total records: {stats['total_records']:,}")
    print(f"   Symbols: {stats['num_symbols']}")
    print(f"   Date range: {stats['earliest_date']} to {stats['latest_date']}")

    # Step 3: Technical Analysis
    print(f"\n📈 STEP 3: Technical Analysis")
    print("-"*100)
    print(f"🔍 Computing technical indicators for {len(symbols)} stocks...")

    tech_agent = PSXTechnicalAgent(price_store)
    technical_snapshots = tech_agent.analyze_batch(symbols)

    print(f"✅ Technical analysis complete")
    print(f"   Analyzed: {len(technical_snapshots)} stocks")

    bullish_count = sum(1 for s in technical_snapshots.values() if s.overall_bias.value == "Bullish")
    bearish_count = sum(1 for s in technical_snapshots.values() if s.overall_bias.value == "Bearish")
    print(f"   Bullish: {bullish_count}, Bearish: {bearish_count}, Neutral: {len(technical_snapshots) - bullish_count - bearish_count}")

    # Step 4: Fundamental Analysis
    print(f"\n📊 STEP 4: Fundamental Analysis")
    print("-"*100)
    print(f"🔍 Computing fundamental scores for {len(symbols)} stocks...")

    fund_agent = PSXFundamentalAgent(price_store=price_store)
    fundamental_scores = {}
    for symbol in symbols:
        try:
            fundamental_scores[symbol] = fund_agent.quick_analysis(symbol)
        except Exception as e:
            print(f"   Warning: Error analyzing {symbol}: {str(e)}")

    print(f"✅ Fundamental analysis complete")
    print(f"   Analyzed: {len(fundamental_scores)} stocks")

    buy_count = sum(1 for f in fundamental_scores.values() if f.recommendation.value == "BUY")
    sell_count = sum(1 for f in fundamental_scores.values() if f.recommendation.value == "SELL")
    print(f"   BUY: {buy_count}, HOLD: {len(fundamental_scores) - buy_count - sell_count}, SELL: {sell_count}")

    # Step 5: Anomaly Detection
    print(f"\n🔍 STEP 5: Anomaly Detection")
    print("-"*100)
    print(f"🔍 Detecting unusual trading patterns...")

    anomaly_agent = PSXAnomalyAgent(price_store=price_store)
    anomalies_report = anomaly_agent.generate_report(symbols, lookback_days=60, z_threshold=2.5)

    print(f"✅ Anomaly detection complete")
    print(f"   Anomalies detected: {len(anomalies_report)}")

    # Step 6: Get Current Prices
    print(f"\n💰 STEP 6: Current Prices")
    print("-"*100)

    current_prices = {}
    for symbol in symbols:
        df = price_store.get_prices(symbol, days=1)
        if not df.empty:
            current_prices[symbol] = float(df['Close'].iloc[-1])

    print(f"✅ Retrieved current prices for {len(current_prices)} stocks")

    # Step 7: Portfolio Manager Analysis
    print(f"\n💼 STEP 7: Portfolio Manager Analysis")
    print("-"*100)

    # Initialize portfolio
    config = PortfolioConfig(
        name=portfolio_name,
        initial_cash=initial_cash
    )

    portfolio_store = PSXPortfolioStore()
    portfolio_manager = PSXPortfolioManager(portfolio_store, config)

    # Run analysis for each model
    outputs = {}
    for model_name in models:
        print(f"\n🔍 Running {model_name.upper()} model...")

        output = portfolio_manager.analyze_portfolio(
            model_name=model_name,
            symbols=symbols,
            current_prices=current_prices,
            technical_snapshots=technical_snapshots,
            fundamental_scores=fundamental_scores,
            anomalies=anomalies_report,
            correlations=None  # We're not fetching news in this script
        )

        outputs[model_name] = output

        print(f"✅ {model_name.upper()} model complete")
        print(f"   Recommendations: {len(output.recommended_trades)} actionable, {len(output.excluded_trades)} excluded")
        print(f"   Processing time: {output.processing_time_ms}ms")

    # Print results
    print_model_comparison(outputs)

    for model_name in models:
        print_recommendations(outputs[model_name], model_name)

    print("\n" + "="*100)
    print("✅ PORTFOLIO ANALYSIS COMPLETE")
    print("="*100)
    print(f"Total processing time: {sum(o.processing_time_ms for o in outputs.values())}ms")
    print(f"Results saved to: {portfolio_store.db_path}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSX Portfolio Analysis")

    parser.add_argument(
        "--use-liquid-stocks",
        action="store_true",
        default=True,
        help="Use liquidity screener for stock selection"
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of top liquid stocks to analyze"
    )

    parser.add_argument(
        "--initial-cash",
        type=float,
        default=1_000_000.0,
        help="Initial portfolio cash (PKR)"
    )

    parser.add_argument(
        "--portfolio-name",
        type=str,
        default="default",
        help="Portfolio name"
    )

    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        choices=["conservative", "balanced", "aggressive", "all"],
        default=["all"],
        help="Models to run"
    )

    parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        help="Specific symbols to analyze (overrides liquidity screening)"
    )

    args = parser.parse_args()

    # Handle "all" models
    if "all" in args.models:
        models = ["conservative", "balanced", "aggressive"]
    else:
        models = args.models

    run_portfolio_analysis(
        use_liquid_stocks=args.use_liquid_stocks and not args.symbols,
        top_n=args.top_n,
        initial_cash=args.initial_cash,
        portfolio_name=args.portfolio_name,
        models=models,
        symbols=args.symbols
    )
