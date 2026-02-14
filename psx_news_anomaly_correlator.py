"""
PSX News-Anomaly Correlator
Correlates detected market anomalies with news events to find potential explanations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from psx_anomaly_agent import Anomaly, AnomalyType, Severity
from psx_news_storage import NewsStorage, NewsArticle
from psx_news_agent import PSXNewsAgent
import re


@dataclass
class NewsAnomalyCorrelation:
    """Represents a correlation between news and an anomaly"""
    anomaly: Anomaly
    related_news: List[NewsArticle]
    correlation_score: float
    explanation: str
    news_summary: List[str]


class NewsAnomalyCorrelator:
    """
    Correlates market anomalies with news events

    Analyzes detected anomalies and matches them with relevant news articles
    to provide context and potential explanations for unusual market behavior.
    """

    def __init__(self, news_storage: Optional[NewsStorage] = None):
        """
        Initialize correlator

        Args:
            news_storage: NewsStorage instance (creates new if None)
        """
        self.storage = news_storage or NewsStorage()

    def correlate_anomaly(self, anomaly: Anomaly, lookback_days: int = 3) -> NewsAnomalyCorrelation:
        """
        Find news articles that may explain an anomaly

        Args:
            anomaly: Detected anomaly
            lookback_days: How many days back to search for news

        Returns:
            NewsAnomalyCorrelation with scored relevance
        """
        # Get news for the specific symbol
        symbol_news = self.storage.get_articles_by_symbol(
            anomaly.symbol,
            days=lookback_days
        )

        # Get macro news that might affect the stock
        macro_news = self.storage.get_macro_news(hours=lookback_days * 24)

        # Score and filter relevant news
        scored_news = []

        for article in symbol_news:
            score = self._calculate_relevance_score(anomaly, article, is_direct=True)
            if score > 0.3:  # Relevance threshold
                scored_news.append((score, article))

        # Add relevant macro news
        for article in macro_news:
            # Check if macro category affects this anomaly type
            if self._is_macro_relevant(anomaly, article):
                score = self._calculate_relevance_score(anomaly, article, is_direct=False)
                if score > 0.4:  # Higher threshold for macro news
                    scored_news.append((score, article))

        # Sort by relevance score
        scored_news.sort(reverse=True, key=lambda x: x[0])

        # Get top articles
        top_news = [article for _, article in scored_news[:5]]

        # Calculate overall correlation score
        if scored_news:
            correlation_score = max(score for score, _ in scored_news)
        else:
            correlation_score = 0.0

        # Generate explanation
        explanation = self._generate_explanation(anomaly, top_news, correlation_score)

        # Create news summary
        news_summary = [
            f"{article.title} ({article.source}, {article.published_date.strftime('%Y-%m-%d')})"
            for article in top_news[:3]
        ]

        return NewsAnomalyCorrelation(
            anomaly=anomaly,
            related_news=top_news,
            correlation_score=correlation_score,
            explanation=explanation,
            news_summary=news_summary
        )

    def _calculate_relevance_score(
        self,
        anomaly: Anomaly,
        article: NewsArticle,
        is_direct: bool
    ) -> float:
        """
        Calculate how relevant a news article is to an anomaly

        Args:
            anomaly: The detected anomaly
            article: News article
            is_direct: True if article directly mentions the symbol

        Returns:
            Relevance score (0.0 to 1.0)
        """
        score = 0.0

        # Base score for direct mention
        if is_direct:
            score += 0.5
            # Bonus if it's the primary symbol
            if article.primary_symbol == anomaly.symbol:
                score += 0.1
        else:
            score += 0.2  # Macro news base score

        # Time relevance (fresher news scores higher)
        anomaly_date = datetime.strptime(anomaly.date, '%Y-%m-%d')
        days_diff = abs((anomaly_date - article.published_date).days)

        if days_diff == 0:
            score += 0.3  # Same day
        elif days_diff == 1:
            score += 0.2  # Previous day
        elif days_diff <= 2:
            score += 0.1  # Within 2 days

        # Sentiment alignment
        if article.sentiment_label and article.sentiment_score:
            score += self._sentiment_alignment_score(anomaly, article)

        # Anomaly type specific scoring
        score += self._anomaly_type_scoring(anomaly, article)

        return min(score, 1.0)  # Cap at 1.0

    def _sentiment_alignment_score(self, anomaly: Anomaly, article: NewsArticle) -> float:
        """Score based on sentiment-anomaly alignment"""
        score = 0.0

        # For price movements
        if anomaly.anomaly_type == AnomalyType.PRICE_MOVEMENT:
            if anomaly.value > 0 and article.sentiment_label == 'positive':
                score += 0.2
            elif anomaly.value < 0 and article.sentiment_label == 'negative':
                score += 0.2

            # Stronger sentiment = higher score
            if abs(article.sentiment_score) > 0.5:
                score += 0.1

        # For volume spikes, strong sentiment (either way) is relevant
        elif anomaly.anomaly_type == AnomalyType.VOLUME_SPIKE:
            if abs(article.sentiment_score) > 0.3:
                score += 0.15

        return score

    def _anomaly_type_scoring(self, anomaly: Anomaly, article: NewsArticle) -> float:
        """Score based on anomaly type and article content"""
        score = 0.0

        text_lower = (article.title + " " + article.summary).lower()

        # Volume spike keywords
        if anomaly.anomaly_type == AnomalyType.VOLUME_SPIKE:
            volume_keywords = ['trading', 'volume', 'activity', 'buying', 'selling',
                              'investors', 'stake', 'acquisition', 'merger']
            if any(keyword in text_lower for keyword in volume_keywords):
                score += 0.1

        # Price movement keywords
        elif anomaly.anomaly_type == AnomalyType.PRICE_MOVEMENT:
            price_keywords = ['price', 'gain', 'loss', 'surge', 'drop', 'rally',
                             'decline', 'profit', 'revenue', 'earnings']
            if any(keyword in text_lower for keyword in price_keywords):
                score += 0.1

        # Volatility keywords
        elif anomaly.anomaly_type == AnomalyType.VOLATILITY_SPIKE:
            volatility_keywords = ['volatile', 'uncertainty', 'swing', 'fluctuat',
                                  'unstable', 'concerns', 'risk']
            if any(keyword in text_lower for keyword in volatility_keywords):
                score += 0.1

        # Opening gap keywords
        elif anomaly.anomaly_type == AnomalyType.OPENING_GAP:
            gap_keywords = ['announcement', 'news', 'overnight', 'after market',
                           'breaking', 'decision', 'policy']
            if any(keyword in text_lower for keyword in gap_keywords):
                score += 0.1

        return score

    def _is_macro_relevant(self, anomaly: Anomaly, article: NewsArticle) -> bool:
        """Check if macro news is relevant to the anomaly"""
        if not article.is_macro_news or not article.macro_category:
            return False

        # Interest rate changes affect all stocks
        if article.macro_category in ['interest_rates', 'policy_rate', 'monetary_policy']:
            return True

        # Oil/gas prices affect energy sector
        if article.macro_category in ['oil_prices', 'gas_prices']:
            energy_symbols = ['PSO', 'APL', 'OGDC', 'PPL', 'POL', 'MARI', 'SSGC', 'SNGP']
            if anomaly.symbol in energy_symbols:
                return True

        # Exchange rate affects all importers/exporters
        if article.macro_category == 'usd_pkr':
            return True

        # Chemical prices
        if article.macro_category in ['propylene_prices', 'chemical_prices']:
            chemical_symbols = ['EPCL', 'LOTTE', 'ENGRO', 'ICI', 'LOTCHEM']
            if anomaly.symbol in chemical_symbols:
                return True

        # Inflation affects consumer goods
        if article.macro_category == 'inflation':
            consumer_symbols = ['NESTLE', 'UNITY', 'UNILEVER', 'COLG', 'EFOODS']
            if anomaly.symbol in consumer_symbols:
                return True

        # Check if symbol is indirectly affected
        if anomaly.symbol in article.indirectly_affected_symbols:
            return True

        return False

    def _generate_explanation(
        self,
        anomaly: Anomaly,
        news_articles: List[NewsArticle],
        correlation_score: float
    ) -> str:
        """Generate human-readable explanation for the anomaly"""

        if correlation_score < 0.3:
            return "No significant news found to explain this anomaly."

        # Build explanation
        explanation_parts = []

        if correlation_score >= 0.7:
            explanation_parts.append("Strong correlation with news:")
        elif correlation_score >= 0.5:
            explanation_parts.append("Moderate correlation with news:")
        else:
            explanation_parts.append("Possible correlation with news:")

        # Add top news headlines
        for article in news_articles[:2]:
            sentiment_str = ""
            if article.sentiment_label:
                sentiment_str = f" [{article.sentiment_label}]"

            explanation_parts.append(
                f"  • {article.title}{sentiment_str}"
            )

        return "\n".join(explanation_parts)

    def correlate_all(
        self,
        anomalies_by_symbol: Dict[str, List[Anomaly]],
        lookback_days: int = 3
    ) -> Dict[str, List[NewsAnomalyCorrelation]]:
        """
        Correlate all anomalies with news

        Args:
            anomalies_by_symbol: Dictionary of symbol -> anomalies
            lookback_days: Days to look back for news

        Returns:
            Dictionary of symbol -> correlations
        """
        correlations = {}

        for symbol, anomalies in anomalies_by_symbol.items():
            symbol_correlations = []
            for anomaly in anomalies:
                correlation = self.correlate_anomaly(anomaly, lookback_days)
                symbol_correlations.append(correlation)
            correlations[symbol] = symbol_correlations

        return correlations

    def print_correlation_report(
        self,
        correlations: Dict[str, List[NewsAnomalyCorrelation]]
    ):
        """Print formatted correlation report"""

        print("\n" + "="*100)
        print("PSX ANOMALY-NEWS CORRELATION REPORT")
        print("="*100)

        total_anomalies = sum(len(corrs) for corrs in correlations.values())
        explained_anomalies = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if corr.correlation_score >= 0.5
        )

        print(f"\nTotal Anomalies: {total_anomalies}")
        print(f"Anomalies with News Correlation (≥50%): {explained_anomalies}")
        print(f"Coverage: {explained_anomalies/total_anomalies*100:.1f}%")

        for symbol, symbol_correlations in correlations.items():
            print(f"\n{'='*100}")
            print(f"📊 {symbol} - {len(symbol_correlations)} Anomalies")
            print('='*100)

            # Sort by correlation score
            sorted_corrs = sorted(
                symbol_correlations,
                key=lambda x: (x.correlation_score, x.anomaly.severity == Severity.HIGH),
                reverse=True
            )

            for corr in sorted_corrs:
                anomaly = corr.anomaly

                # Severity symbol
                severity_symbol = {
                    Severity.HIGH: "🔴",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢"
                }[anomaly.severity]

                print(f"\n{severity_symbol} {anomaly.severity.value} - {anomaly.anomaly_type.value}")
                print(f"   Date: {anomaly.date}")
                print(f"   {anomaly.description}")
                print(f"   Z-Score: {anomaly.z_score:.2f}")

                # News correlation
                correlation_emoji = "🔗" if corr.correlation_score >= 0.7 else "🔍" if corr.correlation_score >= 0.5 else "❓"
                print(f"\n   {correlation_emoji} News Correlation: {corr.correlation_score*100:.0f}%")

                if corr.related_news:
                    print(f"   📰 Related News ({len(corr.related_news)} articles):")
                    for i, article in enumerate(corr.related_news[:3], 1):
                        sentiment = ""
                        if article.sentiment_label and article.sentiment_score:
                            sentiment = f" ({article.sentiment_label}: {article.sentiment_score:+.2f})"

                        # Time difference
                        anomaly_date = datetime.strptime(anomaly.date, '%Y-%m-%d')
                        days_diff = (anomaly_date - article.published_date).days
                        time_str = "same day" if days_diff == 0 else f"{days_diff}d before" if days_diff > 0 else f"{abs(days_diff)}d after"

                        print(f"      {i}. {article.title[:70]}...")
                        print(f"         Source: {article.source} | {article.published_date.strftime('%Y-%m-%d')} ({time_str}){sentiment}")

                        if article.is_macro_news:
                            print(f"         📊 Macro: {article.macro_category}")
                else:
                    print(f"   ❌ No related news found")

                print()

        print("="*100)

        # Summary statistics
        print(f"\n📈 Correlation Statistics:")

        all_correlations = [
            corr for corrs in correlations.values() for corr in corrs
        ]

        if all_correlations:
            avg_correlation = sum(c.correlation_score for c in all_correlations) / len(all_correlations)
            high_correlation = sum(1 for c in all_correlations if c.correlation_score >= 0.7)
            med_correlation = sum(1 for c in all_correlations if 0.5 <= c.correlation_score < 0.7)
            low_correlation = sum(1 for c in all_correlations if c.correlation_score < 0.5)

            print(f"   Average Correlation Score: {avg_correlation*100:.1f}%")
            print(f"   High Correlation (≥70%): {high_correlation} ({high_correlation/len(all_correlations)*100:.1f}%)")
            print(f"   Medium Correlation (50-70%): {med_correlation} ({med_correlation/len(all_correlations)*100:.1f}%)")
            print(f"   Low Correlation (<50%): {low_correlation} ({low_correlation/len(all_correlations)*100:.1f}%)")

        print()


def main():
    """Example usage"""
    from psx_anomaly_agent import PSXAnomalyAgent

    # Initialize components
    print("🔧 Initializing News-Anomaly Correlator...")
    correlator = NewsAnomalyCorrelator()

    # Run anomaly detection
    print("\n🔍 Detecting anomalies...")
    anomaly_agent = PSXAnomalyAgent(lookback_days=60, z_threshold=2.5)

    # Test with a few symbols
    test_symbols = ['HBL', 'PPL', 'OGDC', 'PSO', 'LUCK', 'ENGRO', 'UBL', 'MCB']

    anomalies_report = anomaly_agent.generate_report(test_symbols)

    if anomalies_report:
        # Correlate with news
        print("\n🔗 Correlating anomalies with news...")
        correlations = correlator.correlate_all(anomalies_report, lookback_days=3)

        # Print integrated report
        correlator.print_correlation_report(correlations)
    else:
        print("\n✅ No anomalies detected to correlate.")

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
