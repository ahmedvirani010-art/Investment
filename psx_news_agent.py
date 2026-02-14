"""
PSX News Agent
Fetches, analyzes, and stores news for Pakistan Stock Exchange
"""

try:
    import feedparser
except ImportError:
    # Fallback to simple RSS parser if feedparser not available
    import simple_rss_parser as feedparser

import time
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from psx_news_sources import (
    get_stock_sources,
    get_macro_sources,
    identify_macro_category,
    MACRO_CATEGORIES
)
from psx_news_storage import NewsStorage, NewsArticle
from psx_symbol_matcher import PSXSymbolMatcher
from psx_sentiment_analyzer import PSXSentimentAnalyzer, SentimentResult


@dataclass
class NewsSummary:
    """Summary of news fetching results"""
    total_fetched: int
    stock_news: int
    macro_news: int
    new_articles: int
    duplicates: int
    symbols_mentioned: List[str]
    macro_categories: List[str]


class PSXNewsAgent:
    """Main news agent for PSX"""

    def __init__(self, storage_path: str = "news_data/news.db"):
        """
        Initialize PSX News Agent

        Args:
            storage_path: Path to SQLite database
        """
        self.storage = NewsStorage(storage_path)
        self.symbol_matcher = PSXSymbolMatcher()
        self.sentiment_analyzer = PSXSentimentAnalyzer()

    def fetch_recent_news(self, hours: int = 48) -> List[NewsArticle]:
        """
        Fetch news from all sources from last N hours

        Args:
            hours: Lookback period in hours

        Returns:
            List of NewsArticle objects
        """
        print(f"\n🔍 Fetching news from last {hours} hours...")

        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Fetch stock-specific news
        stock_sources = get_stock_sources()
        print(f"📰 Fetching from {len(stock_sources)} stock news sources...")

        for source in stock_sources:
            try:
                time.sleep(source.rate_limit)  # Rate limiting
                articles = self._fetch_rss_feed(source, cutoff_time, is_macro=False)
                all_articles.extend(articles)
                print(f"   ✓ {source.name}: {len(articles)} articles")
            except Exception as e:
                print(f"   ✗ {source.name}: {str(e)}")

        # Fetch macro economic news
        macro_sources = get_macro_sources()
        print(f"\n📊 Fetching from {len(macro_sources)} macro news sources...")

        for source in macro_sources:
            try:
                time.sleep(source.rate_limit)  # Rate limiting
                articles = self._fetch_rss_feed(source, cutoff_time, is_macro=True)
                all_articles.extend(articles)
                print(f"   ✓ {source.name}: {len(articles)} articles")
            except Exception as e:
                print(f"   ✗ {source.name}: {str(e)}")

        print(f"\n✅ Total articles fetched: {len(all_articles)}")
        return all_articles

    def _fetch_rss_feed(self, source, cutoff_time: datetime, is_macro: bool = False) -> List[NewsArticle]:
        """Fetch articles from RSS feed"""
        articles = []

        try:
            feed = feedparser.parse(source.url)

            for entry in feed.entries:
                try:
                    # Parse published date
                    if hasattr(entry, 'published_parsed'):
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        pub_date = datetime(*entry.updated_parsed[:6])
                    else:
                        pub_date = datetime.now()

                    # Skip if older than cutoff
                    if pub_date < cutoff_time:
                        continue

                    # Extract article details
                    title = entry.get('title', '')
                    url = entry.get('link', '')
                    summary = entry.get('summary', entry.get('description', ''))

                    # Clean HTML tags from summary
                    summary = re.sub(r'<[^>]+>', '', summary)

                    # Generate article ID
                    article_id = NewsStorage.generate_article_id(url, pub_date)

                    # Create article
                    article = NewsArticle(
                        article_id=article_id,
                        title=title,
                        url=url,
                        source=source.name,
                        published_date=pub_date,
                        fetched_date=datetime.now(),
                        language=source.language,
                        full_text=summary,  # RSS feeds usually don't have full text
                        summary=summary[:200],
                        is_macro_news=is_macro
                    )

                    articles.append(article)

                except Exception as e:
                    continue

        except Exception as e:
            raise Exception(f"Failed to parse feed: {str(e)}")

        return articles

    def process_articles(self, articles: List[NewsArticle]) -> NewsSummary:
        """
        Process articles: match symbols, identify macro news, analyze sentiment

        Args:
            articles: List of NewsArticle objects

        Returns:
            NewsSummary with processing results
        """
        print(f"\n⚙️  Processing {len(articles)} articles...")

        new_articles = 0
        duplicates = 0
        stock_news = 0
        macro_news = 0
        all_symbols = set()
        all_macro_categories = set()

        for i, article in enumerate(articles, 1):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(articles)}")

            # Step 1: Match stock symbols
            text = f"{article.title} {article.full_text}"
            mentions = self.symbol_matcher.find_mentioned_symbols(text)

            if mentions:
                article.mentioned_symbols = [sym for sym, conf in mentions]
                article.primary_symbol = self.symbol_matcher.determine_primary_symbol(mentions, text)
                all_symbols.update(article.mentioned_symbols)
                stock_news += 1

            # Step 2: Identify macro news
            macro_category = identify_macro_category(text)
            if macro_category:
                article.is_macro_news = True
                article.macro_category = macro_category.category_id
                article.affected_sectors = macro_category.affected_sectors
                article.impact_type = macro_category.impact_type

                # Determine affected symbols
                if macro_category.affected_symbols == ['ALL']:
                    article.indirectly_affected_symbols = ['ALL']
                else:
                    article.indirectly_affected_symbols = macro_category.affected_symbols

                all_macro_categories.add(macro_category.category_id)
                macro_news += 1

            # Step 3: Analyze sentiment
            sentiment = self.sentiment_analyzer.analyze_article(article.title, article.full_text)
            article.sentiment_score = sentiment.score
            article.sentiment_label = sentiment.label
            article.sentiment_confidence = sentiment.confidence

            # Step 4: Calculate relevance score
            article.relevance_score = self._calculate_relevance(article)

            # Step 5: Save to database
            saved = self.storage.save_article(article)
            if saved:
                new_articles += 1
            else:
                duplicates += 1

        print(f"   ✅ Processed: {len(articles)}")
        print(f"   📊 New articles: {new_articles}")
        print(f"   🔄 Duplicates: {duplicates}")
        print(f"   📈 Stock news: {stock_news}")
        print(f"   🌐 Macro news: {macro_news}")

        return NewsSummary(
            total_fetched=len(articles),
            stock_news=stock_news,
            macro_news=macro_news,
            new_articles=new_articles,
            duplicates=duplicates,
            symbols_mentioned=list(all_symbols),
            macro_categories=list(all_macro_categories)
        )

    def _calculate_relevance(self, article: NewsArticle) -> float:
        """Calculate relevance score (0-1) for an article"""
        score = 0.5  # Base score

        # Has stock mentions
        if article.mentioned_symbols:
            score += 0.2

        # Has primary symbol
        if article.primary_symbol:
            score += 0.1

        # Is macro news
        if article.is_macro_news:
            score += 0.1

        # Strong sentiment
        if article.sentiment_score and abs(article.sentiment_score) > 0.5:
            score += 0.1

        return min(score, 1.0)

    def get_news_for_symbols(self, symbols: List[str], days: int = 7) -> Dict[str, List[NewsArticle]]:
        """
        Get news for specific symbols

        Args:
            symbols: List of stock symbols
            days: Lookback period in days

        Returns:
            Dictionary mapping symbol -> list of articles
        """
        news_by_symbol = {}

        for symbol in symbols:
            articles = self.storage.get_articles_by_symbol(symbol, days=days)
            if articles:
                news_by_symbol[symbol] = articles

        return news_by_symbol

    def get_macro_news_summary(self, hours: int = 48) -> Dict[str, List[NewsArticle]]:
        """
        Get macro news grouped by category

        Args:
            hours: Lookback period in hours

        Returns:
            Dictionary mapping category -> list of articles
        """
        summary = {}

        for category_id in MACRO_CATEGORIES.keys():
            articles = self.storage.get_macro_news(category=category_id, hours=hours)
            if articles:
                summary[category_id] = articles

        return summary

    def print_summary(self, summary: NewsSummary):
        """Print news fetching summary"""
        print("\n" + "="*80)
        print("PSX NEWS AGENT - SUMMARY")
        print("="*80)
        print(f"\n📊 Fetching Results:")
        print(f"   Total Articles Fetched: {summary.total_fetched}")
        print(f"   New Articles: {summary.new_articles}")
        print(f"   Duplicates: {summary.duplicates}")
        print(f"\n📰 Content Analysis:")
        print(f"   Stock-Specific News: {summary.stock_news}")
        print(f"   Macro Economic News: {summary.macro_news}")
        print(f"\n📈 Stocks Mentioned: {len(summary.symbols_mentioned)}")
        if summary.symbols_mentioned:
            print(f"   Top 20: {', '.join(list(summary.symbols_mentioned)[:20])}")
        print(f"\n🌐 Macro Categories: {len(summary.macro_categories)}")
        if summary.macro_categories:
            print(f"   Categories: {', '.join(summary.macro_categories)}")
        print("\n" + "="*80)


def main():
    """Main execution function"""
    print("="*80)
    print("PSX NEWS AGENT")
    print("="*80)

    # Initialize agent
    agent = PSXNewsAgent()

    # Fetch news from last 48 hours
    articles = agent.fetch_recent_news(hours=48)

    # Process articles
    summary = agent.process_articles(articles)

    # Print summary
    agent.print_summary(summary)

    # Show some example articles
    print("\n📄 Recent Articles Sample:")
    print("-"*80)

    recent = agent.storage.get_recent_articles(hours=48, limit=5)
    for i, article in enumerate(recent, 1):
        print(f"\n{i}. {article.title}")
        print(f"   Source: {article.source} | Published: {article.published_date.strftime('%Y-%m-%d %H:%M')}")
        if article.mentioned_symbols:
            print(f"   Symbols: {', '.join(article.mentioned_symbols[:5])}")
        if article.is_macro_news:
            print(f"   Macro: {article.macro_category}")
        print(f"   Sentiment: {article.sentiment_label} ({article.sentiment_score:.2f})")

    print("\n" + "="*80)
    print("✅ News agent execution complete!")
    print("="*80)


if __name__ == "__main__":
    main()
