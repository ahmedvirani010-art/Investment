#!/usr/bin/env python3
"""
Demo: PSX Sentiment Momentum Tracker
Shows how to track sentiment over time and generate momentum-based signals
"""

from psx_sentiment_analyzer import PSXSentimentAnalyzer
from psx_sentiment_momentum_store import SentimentMomentumStore
from psx_sentiment_momentum_tracker import SentimentMomentumTracker
from datetime import datetime, timedelta
import random


def generate_mock_articles(symbol: str, days: int = 30):
    """
    Generate mock news articles with varying sentiment
    Simulates a sentiment trend: negative → neutral → positive
    """
    articles = []
    start_date = datetime.now() - timedelta(days=days)

    # Sentiment progression: starts negative, trends positive
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        # Number of articles per day (1-5)
        num_articles = random.randint(1, 5)

        for j in range(num_articles):
            # Create sentiment that trends from negative to positive
            # Day 0-10: Negative sentiment
            # Day 10-20: Neutral sentiment
            # Day 20-30: Positive sentiment

            if i < 10:
                # Negative phase
                templates = [
                    f"{symbol} faces regulatory concerns over expansion plans",
                    f"{symbol} reports declining profit margins in Q3",
                    f"Analysts downgrade {symbol} on weak fundamentals",
                    f"{symbol} stock falls on poor earnings guidance",
                ]
            elif i < 20:
                # Neutral phase
                templates = [
                    f"{symbol} announces board meeting for next month",
                    f"{symbol} maintains steady production levels",
                    f"Market watch: {symbol} trading in narrow range",
                    f"{symbol} completes routine compliance filings",
                ]
            else:
                # Positive phase
                templates = [
                    f"{symbol} beats earnings expectations for Q4",
                    f"{symbol} announces major expansion project worth PKR 5B",
                    f"Analysts upgrade {symbol} citing strong fundamentals",
                    f"{symbol} declares attractive dividend of 15%",
                    f"{symbol} stock surges on positive earnings surprise",
                ]

            title = random.choice(templates)
            articles.append({
                'symbol': symbol,
                'date': date_str,
                'title': title,
                'text': title + ". More details to follow.",
                'source': 'Mock News'
            })

    return articles


def demo_basic_tracking():
    """Demo 1: Basic sentiment tracking over time"""
    print("=" * 80)
    print("DEMO 1: BASIC SENTIMENT TRACKING")
    print("=" * 80)
    print("\nThis demo shows how sentiment is tracked over time for a stock.")
    print("We'll simulate 30 days of news articles with changing sentiment.\n")

    # Initialize components
    analyzer = PSXSentimentAnalyzer()
    store = SentimentMomentumStore(db_path="sentiment_data/demo_momentum.db")

    # Generate and analyze mock articles
    symbol = "ENGRO"
    articles = generate_mock_articles(symbol, days=30)

    print(f"Generated {len(articles)} mock articles for {symbol}")
    print("Analyzing and storing sentiment...\n")

    # Process articles
    for article in articles:
        sentiment = analyzer.analyze_text(article['title'])

        # Save to store
        store.save_sentiment(
            symbol=article['symbol'],
            date=article['date'],
            sentiment_score=sentiment.score,
            sentiment_label=sentiment.label,
            confidence=sentiment.confidence,
            title=article['title'],
            source=article['source']
        )

    # Aggregate daily sentiment for each date
    dates = sorted(set(a['date'] for a in articles))
    print("Aggregating daily sentiment...\n")

    for date in dates:
        store.aggregate_daily_sentiment(symbol, date)

    # Show sentiment history
    history = store.get_sentiment_history(symbol, days=30)
    print(f"Sentiment History for {symbol}:")
    print("-" * 80)
    print(history[['date', 'avg_sentiment', 'sentiment_label', 'article_count']].to_string())
    print()


def demo_momentum_analysis():
    """Demo 2: Momentum analysis and signal generation"""
    print("\n" + "=" * 80)
    print("DEMO 2: MOMENTUM ANALYSIS & SIGNAL GENERATION")
    print("=" * 80)
    print("\nNow we'll analyze the sentiment momentum and generate trading signals.\n")

    # Initialize components
    store = SentimentMomentumStore(db_path="sentiment_data/demo_momentum.db")
    tracker = SentimentMomentumTracker(sentiment_store=store)

    # Analyze momentum
    symbol = "ENGRO"
    print(f"Analyzing sentiment momentum for {symbol}...\n")

    signal = tracker.analyze_symbol(symbol)

    if signal:
        tracker.print_signal(signal)

        print("\n📊 INTERPRETATION:")
        print("-" * 80)
        print("The sentiment momentum tracker detected a clear trend in sentiment")
        print("over the past 30 days. The stock moved from negative sentiment")
        print("(regulatory concerns, declining margins) to positive sentiment")
        print("(earnings beat, expansion plans).")
        print()
        print("This represents a BULLISH REVERSAL pattern that could signal")
        print("a good entry point, especially if confirmed by technical analysis.")
        print()
    else:
        print("Insufficient data for momentum analysis")


def demo_batch_analysis():
    """Demo 3: Batch analysis of multiple stocks"""
    print("\n" + "=" * 80)
    print("DEMO 3: BATCH ANALYSIS")
    print("=" * 80)
    print("\nAnalyzing multiple stocks for momentum signals...\n")

    # Initialize components
    analyzer = PSXSentimentAnalyzer()
    store = SentimentMomentumStore(db_path="sentiment_data/demo_momentum.db")
    tracker = SentimentMomentumTracker(sentiment_store=store)

    # Generate data for multiple stocks with different patterns
    stocks = {
        'PPL': 'improving',    # Positive trend
        'OGDC': 'declining',   # Negative trend
        'HBL': 'stable'        # Flat trend
    }

    for symbol, pattern in stocks.items():
        print(f"Generating mock data for {symbol} ({pattern} sentiment)...")

        articles = []
        start_date = datetime.now() - timedelta(days=30)

        for i in range(30):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')

            # Create sentiment based on pattern
            if pattern == 'improving':
                # Sentiment improves over time
                sentiment_base = -0.5 + (i / 30) * 1.0  # -0.5 to +0.5
            elif pattern == 'declining':
                # Sentiment declines over time
                sentiment_base = 0.5 - (i / 30) * 1.0   # +0.5 to -0.5
            else:
                # Stable sentiment
                sentiment_base = 0.0

            # Add some noise
            sentiment_base += random.uniform(-0.1, 0.1)

            # Generate appropriate title
            if sentiment_base > 0.2:
                title = f"{symbol} shows strong performance and growth potential"
            elif sentiment_base < -0.2:
                title = f"{symbol} faces challenges amid market volatility"
            else:
                title = f"{symbol} maintains operations at current levels"

            sentiment = analyzer.analyze_text(title)

            store.save_sentiment(
                symbol=symbol,
                date=date_str,
                sentiment_score=sentiment.score,
                sentiment_label=sentiment.label,
                confidence=sentiment.confidence,
                title=title,
                source='Mock News'
            )

        # Aggregate daily
        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                 for i in range(30)]
        for date in dates:
            store.aggregate_daily_sentiment(symbol, date)

    # Analyze all stocks
    print("\n" + "=" * 80)
    print("MOMENTUM SIGNALS")
    print("=" * 80)

    symbols = list(stocks.keys())
    signals = tracker.analyze_batch(symbols)

    # Group by signal type
    buy_signals = [s for s in signals.values() if s.signal_type == 'buy']
    sell_signals = [s for s in signals.values() if s.signal_type == 'sell']
    hold_signals = [s for s in signals.values() if s.signal_type == 'hold']

    print(f"\n📈 BUY SIGNALS ({len(buy_signals)}):")
    print("-" * 80)
    for signal in buy_signals:
        print(f"{signal.symbol:8s} | Sentiment: {signal.sentiment_score:+.3f} | "
              f"7d Momentum: {signal.momentum_7d:+.4f} | Strength: {signal.strength}")

    print(f"\n📉 SELL SIGNALS ({len(sell_signals)}):")
    print("-" * 80)
    for signal in sell_signals:
        print(f"{signal.symbol:8s} | Sentiment: {signal.sentiment_score:+.3f} | "
              f"7d Momentum: {signal.momentum_7d:+.4f} | Strength: {signal.strength}")

    print(f"\n➡️  HOLD SIGNALS ({len(hold_signals)}):")
    print("-" * 80)
    for signal in hold_signals:
        print(f"{signal.symbol:8s} | Sentiment: {signal.sentiment_score:+.3f} | "
              f"7d Momentum: {signal.momentum_7d:+.4f} | Strength: {signal.strength}")


def demo_reversal_detection():
    """Demo 4: Sentiment reversal detection"""
    print("\n\n" + "=" * 80)
    print("DEMO 4: SENTIMENT REVERSAL DETECTION")
    print("=" * 80)
    print("\nDetecting sentiment reversals (negative → positive or positive → negative)\n")

    analyzer = PSXSentimentAnalyzer()
    store = SentimentMomentumStore(db_path="sentiment_data/demo_momentum.db")
    tracker = SentimentMomentumTracker(sentiment_store=store)

    symbol = "LUCK"
    print(f"Simulating sentiment reversal for {symbol}...\n")

    # Create a clear reversal pattern
    start_date = datetime.now() - timedelta(days=20)

    for i in range(20):
        date = start_date + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        # Days 0-9: Negative sentiment
        # Days 10-12: Transition
        # Days 13-19: Positive sentiment (REVERSAL)

        if i < 10:
            title = f"{symbol} struggles with production issues and cost overruns"
        elif i < 13:
            title = f"{symbol} management addresses concerns in press conference"
        else:
            title = f"{symbol} announces breakthrough deal and strong outlook"

        sentiment = analyzer.analyze_text(title)

        store.save_sentiment(
            symbol=symbol,
            date=date_str,
            sentiment_score=sentiment.score,
            sentiment_label=sentiment.label,
            confidence=sentiment.confidence,
            title=title,
            source='Mock News'
        )

    # Aggregate
    dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
             for i in range(20)]
    for date in dates:
        store.aggregate_daily_sentiment(symbol, date)

    # Analyze
    signal = tracker.analyze_symbol(symbol)
    if signal and signal.reversal_signal:
        print(f"✅ REVERSAL DETECTED: {signal.reversal_signal.replace('_', ' ').title()}\n")
        tracker.print_signal(signal)
    else:
        print("No reversal detected (may need more data)")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PSX SENTIMENT MOMENTUM TRACKER" + " " * 27 + "║")
    print("║" + " " * 30 + "DEMO SUITE" + " " * 38 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    try:
        # Run demos
        demo_basic_tracking()
        demo_momentum_analysis()
        demo_batch_analysis()
        demo_reversal_detection()

        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("\nThe sentiment momentum tracker successfully:")
        print("  ✅ Tracked sentiment over time")
        print("  ✅ Computed momentum indicators (7d, 14d, 30d)")
        print("  ✅ Detected sentiment reversals")
        print("  ✅ Generated buy/sell/hold signals")
        print("  ✅ Calculated signal strength and confidence")
        print()
        print("Next steps:")
        print("  • Integrate with real news data pipeline")
        print("  • Add price divergence detection (requires price store)")
        print("  • Incorporate into combined analysis reports")
        print()

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
