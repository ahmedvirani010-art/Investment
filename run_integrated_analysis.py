#!/usr/bin/env python3
"""
PSX Integrated Analysis
Runs news fetching, anomaly detection, and correlation analysis
"""

from datetime import datetime
from psx_news_agent import PSXNewsAgent
from psx_anomaly_agent import PSXAnomalyAgent
from psx_news_anomaly_correlator import NewsAnomalyCorrelator
from psx_liquidity_screener import PSXLiquidityScreener
from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_technical_store import TechnicalStore
import argparse


def run_full_analysis(
    use_liquid_stocks: bool = True,
    top_n: int = 30,
    fetch_news: bool = True,
    news_hours: int = 48,
    z_threshold: float = 2.5,
    lookback_days: int = 60,
    skip_technicals: bool = False,
    ta_lookback: int = 250,
    save_technicals: bool = False,
    run_portfolio_manager: bool = False,
    portfolio_initial_cash: float = 1_000_000.0,
    portfolio_models: str = "all"
):
    """
    Run complete integrated analysis

    Args:
        use_liquid_stocks: Use liquidity screener for stock selection
        top_n: Number of top liquid stocks to analyze
        fetch_news: Whether to fetch fresh news
        news_hours: Hours to look back for news
        z_threshold: Z-score threshold for anomaly detection
        lookback_days: Days to look back for baseline calculation
        skip_technicals: Skip technical analysis computation
        ta_lookback: Days of price history for indicators (default: 250)
        save_technicals: Persist computed indicators to database
        run_portfolio_manager: Run portfolio management analysis
        portfolio_initial_cash: Initial portfolio cash (PKR)
        portfolio_models: Models to run (conservative, balanced, aggressive, all)
    """

    print("="*100)
    print("PSX INTEGRATED ANALYSIS")
    print("="*100)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Analysis Period: {lookback_days} days")
    print(f"News Window: {news_hours} hours")
    print(f"Anomaly Threshold: {z_threshold}σ")
    print("="*100)

    # Step 1: Get stock symbols to analyze
    print("\n📋 STEP 1: Stock Selection")
    print("-"*100)

    if use_liquid_stocks:
        print(f"🔍 Using liquidity screener to select top {top_n} stocks...")
        screener = PSXLiquidityScreener(lookback_days=30, min_price=20.0)

        # Quick screen without full report
        liquid_stocks = screener.screen_stocks(top_n=top_n)
        symbols = [stock.symbol for stock in liquid_stocks]

        print(f"✅ Selected {len(symbols)} liquid stocks")
        print(f"   Top 10: {symbols[:10]}")
    else:
        # Use predefined list
        symbols = [
            'HBL', 'UBL', 'MCB', 'BAFL', 'ABL', 'BAHL', 'MEBL', 'NBP',
            'OGDC', 'PPL', 'PSO', 'APL', 'POL', 'MARI',
            'LUCK', 'DGKC', 'MLCF', 'FCCL',
            'FFC', 'EFERT', 'FATIMA',
            'HUBC', 'KAPCO',
            'ENGRO', 'ICI', 'EPCL',
            'INDU', 'PSMC', 'HCAR'
        ]
        print(f"✅ Using predefined list of {len(symbols)} stocks")

    # Step 2: Price Data Sync
    print(f"\n💾 STEP 2: Price Data Sync")
    print("-"*100)
    print(f"🔍 Updating price store with {ta_lookback} days of history...")

    price_store = PSXPriceStore()
    price_store.bulk_update(symbols, days=ta_lookback)

    stats = price_store.get_stats()
    print(f"✅ Price store updated")
    print(f"   Total records: {stats['total_records']:,}")
    print(f"   Symbols: {stats['num_symbols']}")
    print(f"   Date range: {stats['earliest_date']} to {stats['latest_date']}")

    # Step 3: News Collection
    if fetch_news:
        print(f"\n📰 STEP 3: News Collection")
        print("-"*100)
        print(f"🔍 Fetching news from last {news_hours} hours...")

        news_agent = PSXNewsAgent()
        articles = news_agent.fetch_recent_news(hours=news_hours)
        summary = news_agent.process_articles(articles)

        print(f"✅ Fetched {summary.total_fetched} articles")
        print(f"   New: {summary.new_articles}, Duplicates: {summary.duplicates}")
        print(f"   Stock-specific: {summary.stock_news}")
        print(f"   Macro news: {summary.macro_news}")
    else:
        print(f"\n📰 STEP 3: News Collection")
        print("-"*100)
        print("⏭️  Skipping news fetch, using existing database")

    # Step 4: Technical Analysis
    technical_snapshots = {}
    if not skip_technicals:
        print(f"\n📊 STEP 4: Technical Analysis")
        print("-"*100)
        print(f"🔍 Computing technical indicators for {len(symbols)} stocks...")

        tech_agent = PSXTechnicalAgent(price_store)
        technical_snapshots = tech_agent.analyze_batch(symbols)

        # Count signals
        total_signals = sum(len(snap.signals) for snap in technical_snapshots.values())
        bullish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bullish")
        bearish = sum(1 for snap in technical_snapshots.values() if snap.overall_bias.value == "Bearish")

        print(f"✅ Technical analysis complete")
        print(f"   Total signals: {total_signals}")
        print(f"   Bullish: {bullish}, Bearish: {bearish}, Neutral: {len(symbols) - bullish - bearish}")

        # Save to database if requested
        if save_technicals:
            print(f"\n💾 Saving technical indicators to database...")
            tech_store = TechnicalStore()
            for snapshot in technical_snapshots.values():
                tech_store.save_snapshot(snapshot)
            print(f"✅ Saved {len(technical_snapshots)} snapshots")
    else:
        print(f"\n📊 STEP 4: Technical Analysis")
        print("-"*100)
        print("⏭️  Skipping technical analysis")

    # Step 5: Anomaly Detection
    print(f"\n🔍 STEP 5: Anomaly Detection")
    print("-"*100)
    print(f"🔍 Analyzing {len(symbols)} stocks for anomalies...")
    print(f"   Baseline period: {lookback_days} days")
    print(f"   Threshold: {z_threshold}σ")

    # Use price store in anomaly agent
    anomaly_agent = PSXAnomalyAgent(lookback_days=lookback_days, z_threshold=z_threshold, price_store=price_store)
    anomalies_report = anomaly_agent.generate_report(symbols)

    total_anomalies = sum(len(anomalies) for anomalies in anomalies_report.values())
    print(f"✅ Detected {total_anomalies} anomalies in {len(anomalies_report)} stocks")

    # Step 6: News-Anomaly Correlation
    print(f"\n🔗 STEP 6: News-Anomaly Correlation")
    print("-"*100)

    if anomalies_report:
        print(f"🔍 Correlating {total_anomalies} anomalies with news...")
        correlator = NewsAnomalyCorrelator()
        correlations = correlator.correlate_all(anomalies_report, lookback_days=3)

        explained = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if corr.correlation_score >= 0.5
        )

        print(f"✅ Correlation complete")
        print(f"   Anomalies with news explanation (≥50%): {explained}/{total_anomalies} ({explained/total_anomalies*100:.1f}%)")

        # Print full correlation report
        correlator.print_correlation_report(correlations)

        # Print technical summary if available
        if technical_snapshots:
            print_technical_summary(technical_snapshots, anomalies_report)

    else:
        print("ℹ️  No anomalies detected - nothing to correlate")
        print("\n" + "="*100)
        print("✅ No market anomalies detected in analyzed stocks")
        print("="*100)

        # Still print technical summary if available
        if technical_snapshots:
            print_technical_summary(technical_snapshots, {})

    # Step 7: Portfolio Manager (Optional)
    if run_portfolio_manager and technical_snapshots:
        print(f"\n💼 STEP 7: Portfolio Management")
        print("-"*100)

        # Import portfolio manager components
        from psx_portfolio_manager import PSXPortfolioManager
        from psx_portfolio_store import PSXPortfolioStore
        from psx_portfolio_models import PortfolioConfig
        from psx_fundamental_agent import PSXFundamentalAgent

        # Parse models
        if portfolio_models == "all":
            models = ["conservative", "balanced", "aggressive"]
        else:
            models = [m.strip() for m in portfolio_models.split(",")]

        # Get current prices
        current_prices = {}
        for symbol in symbols:
            df = price_store.get_prices(symbol, days=1)
            if not df.empty:
                current_prices[symbol] = float(df['Close'].iloc[-1])

        # Run fundamental analysis if not already done
        print(f"🔍 Running fundamental analysis for portfolio decisions...")
        fund_agent = PSXFundamentalAgent(price_store=price_store)
        fundamental_scores = {}
        for symbol in symbols:
            try:
                fundamental_scores[symbol] = fund_agent.quick_analysis(symbol)
            except Exception as e:
                pass  # Skip symbols with errors

        # Initialize portfolio
        config = PortfolioConfig(
            name="default",
            initial_cash=portfolio_initial_cash
        )
        portfolio_store = PSXPortfolioStore()
        portfolio_manager = PSXPortfolioManager(portfolio_store, config)

        # Run analysis for each model
        print(f"🔍 Generating recommendations for {len(models)} model(s)...")
        portfolio_outputs = {}
        for model_name in models:
            output = portfolio_manager.analyze_portfolio(
                model_name=model_name,
                symbols=symbols,
                current_prices=current_prices,
                technical_snapshots=technical_snapshots,
                fundamental_scores=fundamental_scores,
                anomalies=list(anomalies_report.values()) if anomalies_report else [],
                correlations=correlations if 'correlations' in locals() else None
            )
            portfolio_outputs[model_name] = output

        # Print summary
        print(f"✅ Portfolio analysis complete")
        for model_name, output in portfolio_outputs.items():
            print(f"   {model_name.upper()}: {len(output.recommended_trades)} recommendations, {len(output.excluded_trades)} excluded")

        # Print brief recommendations for each model
        for model_name, output in portfolio_outputs.items():
            if output.recommended_trades:
                print(f"\n   {model_name.upper()} Top Recommendations:")
                for decision in output.recommended_trades[:3]:  # Top 3
                    print(f"      {decision.symbol}: {decision.action.value} {int(decision.quantity):,} shares (Score: {decision.composite_score:.0f}/100)")

    # Summary
    print("\n" + "="*100)
    print("📊 ANALYSIS SUMMARY")
    print("="*100)
    print(f"Stocks Analyzed: {len(symbols)}")
    print(f"Price Records: {stats['total_records']:,}")
    if fetch_news:
        print(f"News Articles Fetched: {summary.total_fetched}")
    if not skip_technicals:
        print(f"Technical Signals: {sum(len(snap.signals) for snap in technical_snapshots.values())}")
    print(f"Anomalies Detected: {total_anomalies}")
    if anomalies_report:
        print(f"News Explanations Found: {explained} ({explained/total_anomalies*100:.1f}%)")
    if run_portfolio_manager:
        print(f"Portfolio Models Run: {', '.join(models)}")
    print("="*100)
    print(f"\n✅ Analysis complete at {datetime.now().strftime('%H:%M:%S')}")


def print_technical_summary(technical_snapshots, anomalies_report):
    """Print technical analysis summary"""
    print("\n" + "="*100)
    print("📊 TECHNICAL ANALYSIS SUMMARY")
    print("="*100)

    # Overbought stocks (RSI > 70)
    overbought = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                  if 'RSI' in snap.indicator_values and snap.indicator_values['RSI'] >= 70]

    if overbought:
        print(f"\n🔴 OVERBOUGHT (RSI > 70):")
        for symbol, snap in sorted(overbought, key=lambda x: x[1].indicator_values['RSI'], reverse=True):
            rsi = snap.indicator_values['RSI']
            bias = snap.overall_bias.value
            conf = snap.confidence * 100
            sma200_status = ""
            if 'SMA_200' in snap.indicator_values:
                price = snap.indicator_values.get('Close', 0)
                sma200 = snap.indicator_values['SMA_200']
                if price > sma200:
                    sma200_status = "above SMA(200)"
                else:
                    sma200_status = "below SMA(200)"

            print(f"   {symbol:8s} RSI: {rsi:5.1f}  |  Bias: {bias:8s} ({conf:.0f}%)  |  {sma200_status}")
    else:
        print(f"\n🔴 OVERBOUGHT (RSI > 70): None")

    # Oversold stocks (RSI < 30)
    oversold = [(symbol, snap) for symbol, snap in technical_snapshots.items()
                if 'RSI' in snap.indicator_values and snap.indicator_values['RSI'] <= 30]

    if oversold:
        print(f"\n🟢 OVERSOLD (RSI < 30):")
        for symbol, snap in sorted(oversold, key=lambda x: x[1].indicator_values['RSI']):
            rsi = snap.indicator_values['RSI']
            bias = snap.overall_bias.value
            conf = snap.confidence * 100
            sma200_status = ""
            if 'SMA_200' in snap.indicator_values:
                price = snap.indicator_values.get('Close', 0)
                sma200 = snap.indicator_values['SMA_200']
                if price > sma200:
                    sma200_status = "above SMA(200)"
                else:
                    sma200_status = "below SMA(200)"

            print(f"   {symbol:8s} RSI: {rsi:5.1f}  |  Bias: {bias:8s} ({conf:.0f}%)  |  {sma200_status}")
    else:
        print(f"\n🟢 OVERSOLD (RSI < 30): None")

    # Bullish crossovers
    bullish_crossovers = []
    for symbol, snap in technical_snapshots.items():
        for signal in snap.signals:
            if signal.signal_type.value == "Bullish" and "cross" in signal.description.lower():
                bullish_crossovers.append((symbol, signal))

    if bullish_crossovers:
        print(f"\n📈 BULLISH CROSSOVERS (today):")
        for symbol, signal in bullish_crossovers:
            print(f"   {symbol:8s} {signal.indicator}: {signal.description}")
    else:
        print(f"\n📈 BULLISH CROSSOVERS (today): None")

    # Bearish crossovers
    bearish_crossovers = []
    for symbol, snap in technical_snapshots.items():
        for signal in snap.signals:
            if signal.signal_type.value == "Bearish" and "cross" in signal.description.lower():
                bearish_crossovers.append((symbol, signal))

    if bearish_crossovers:
        print(f"\n📉 BEARISH CROSSOVERS (today):")
        for symbol, signal in bearish_crossovers:
            print(f"   {symbol:8s} {signal.indicator}: {signal.description}")
    else:
        print(f"\n📉 BEARISH CROSSOVERS (today): None")

    print("\n" + "="*100)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='PSX Integrated Analysis - News, Anomalies, and Correlations'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        default='liquid',
        choices=['liquid', 'preset'],
        help='Stock selection method: liquid (screener) or preset (hardcoded list)'
    )

    parser.add_argument(
        '--top',
        type=int,
        default=30,
        help='Number of top liquid stocks to analyze (default: 30)'
    )

    parser.add_argument(
        '--skip-news',
        action='store_true',
        help='Skip news fetching, use existing database'
    )

    parser.add_argument(
        '--news-hours',
        type=int,
        default=48,
        help='Hours to look back for news (default: 48)'
    )

    parser.add_argument(
        '--z-threshold',
        type=float,
        default=2.5,
        help='Z-score threshold for anomaly detection (default: 2.5)'
    )

    parser.add_argument(
        '--lookback',
        type=int,
        default=60,
        help='Days to look back for baseline (default: 60)'
    )

    parser.add_argument(
        '--skip-technicals',
        action='store_true',
        help='Skip technical analysis computation'
    )

    parser.add_argument(
        '--ta-lookback',
        type=int,
        default=250,
        help='Days of price history for indicators (default: 250)'
    )

    parser.add_argument(
        '--save-technicals',
        action='store_true',
        help='Persist computed indicators to database'
    )

    parser.add_argument(
        '--portfolio-manager',
        action='store_true',
        help='Run portfolio management analysis'
    )

    parser.add_argument(
        '--portfolio-cash',
        type=float,
        default=1_000_000.0,
        help='Initial portfolio cash in PKR (default: 1,000,000)'
    )

    parser.add_argument(
        '--portfolio-models',
        type=str,
        default='all',
        help='Portfolio models to run: conservative, balanced, aggressive, or all (default: all)'
    )

    args = parser.parse_args()

    run_full_analysis(
        use_liquid_stocks=(args.stocks == 'liquid'),
        top_n=args.top,
        fetch_news=(not args.skip_news),
        news_hours=args.news_hours,
        z_threshold=args.z_threshold,
        lookback_days=args.lookback,
        skip_technicals=args.skip_technicals,
        ta_lookback=args.ta_lookback,
        save_technicals=args.save_technicals,
        run_portfolio_manager=args.portfolio_manager,
        portfolio_initial_cash=args.portfolio_cash,
        portfolio_models=args.portfolio_models
    )


if __name__ == "__main__":
    main()
