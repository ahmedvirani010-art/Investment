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

        PSX Context: Focus on material news that moves markets

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
            # Check materiality first
            if not self._is_news_material(article, anomaly):
                continue

            score = self._calculate_relevance_score(anomaly, article, is_direct=True)
            if score > 0.4:  # Higher threshold for quality
                scored_news.append((score, article))

        # Add relevant macro news
        for article in macro_news:
            # Check if macro category affects this anomaly type
            if self._is_macro_relevant(anomaly, article):
                # Macro news already has materiality check in _is_macro_relevant
                score = self._calculate_relevance_score(anomaly, article, is_direct=False)
                if score > 0.5:  # Even higher threshold for macro
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

    def _is_news_material(self, article: NewsArticle, anomaly: Anomaly) -> bool:
        """
        Check if stock-specific news is material enough to move the stock

        PSX Context: Filter out noise, focus on real catalysts
        """
        text = (article.title + " " + article.summary).lower()

        # TIER 1: Always material events
        # ================================

        high_impact_keywords = [
            # Corporate actions
            'dividend', 'bonus', 'right issue', 'stock split',
            'merger', 'acquisition', 'takeover', 'buyback',

            # Financial results
            'profit', 'loss', 'earnings', 'results', 'quarterly',
            'annual results', 'financial results', 'net profit',

            # Major contracts/deals
            'contract', 'award', 'wins', 'agreement', 'deal',
            'project', 'expansion', 'investment',

            # Management changes
            'ceo', 'chairman', 'board', 'director', 'appoint',
            'resign', 'management',

            # Regulatory/legal
            'secp', 'investigation', 'penalty', 'fine',
            'approval', 'license', 'compliance',

            # Operations
            'production', 'capacity', 'plant', 'shutdown',
            'restart', 'maintenance', 'discovery',

            # Debt/financing
            'loan', 'financing', 'debt', 'sukuk', 'tfc',
            'credit rating', 'default', 'restructuring'
        ]

        if any(keyword in text for keyword in high_impact_keywords):
            return True

        # TIER 2: Context-dependent materiality
        # ======================================

        # Large volume anomalies need strong catalysts
        if anomaly.anomaly_type == AnomalyType.VOLUME_SPIKE:
            # Volume spike without clear catalyst is less reliable
            volume_catalysts = [
                'stake', 'shareholding', 'block trade', 'institutional',
                'foreign investment', 'divestment', 'placement'
            ]
            if any(keyword in text for keyword in volume_catalysts):
                return True

            # High severity volume spike without news is suspicious
            if anomaly.severity == Severity.HIGH:
                return True  # Flag it anyway for investigation

        # Price movements need clear drivers
        if anomaly.anomaly_type == AnomalyType.PRICE_MOVEMENT:
            price_drivers = [
                'upgrade', 'downgrade', 'target price', 'recommendation',
                'analyst', 'rating', 'buy', 'sell'
            ]
            if any(keyword in text for keyword in price_drivers):
                return True

        # TIER 3: Filter out noise
        # =========================

        # General market commentary without specifics
        noise_keywords = [
            'market watch', 'market roundup', 'trading summary',
            'weekly review', 'daily brief', 'market close'
        ]
        if any(keyword in text for keyword in noise_keywords):
            return False

        # Speculation without substance
        speculation_keywords = [
            'rumor', 'rumour', 'speculation', 'unconfirmed',
            'sources say', 'alleged'
        ]
        if any(keyword in text for keyword in speculation_keywords):
            # Only allow if high-confidence sentiment
            if article.sentiment_confidence and article.sentiment_confidence < 0.7:
                return False

        # TIER 4: Sentiment-based materiality
        # ====================================

        # Strong sentiment with weak relevance = noise
        if article.sentiment_score:
            # Very strong sentiment (|score| > 0.7) with substance is material
            if abs(article.sentiment_score) > 0.7 and len(article.summary) > 100:
                return True

        # Default: conservative filter
        # If article relevance score was already high, it passed
        if article.relevance_score > 0.7:
            return True

        return False

    def _is_macro_relevant(self, anomaly: Anomaly, article: NewsArticle) -> bool:
        """
        Check if macro news is material and relevant to the anomaly

        PSX Context: Focus on structural changes, not daily noise
        """
        if not article.is_macro_news or not article.macro_category:
            return False

        text = (article.title + " " + article.summary).lower()

        # TIER 1: High-impact macro news (always relevant to PSX)
        # ========================================================

        # Monetary policy changes - affects ALL stocks, highly material
        if article.macro_category in ['interest_rates', 'policy_rate', 'monetary_policy']:
            # Must be actual policy decisions, not speculation
            material_keywords = [
                'sbp', 'state bank', 'cuts rate', 'raises rate', 'policy rate',
                'monetary policy', 'rate decision', 'rate cut', 'rate hike',
                'basis points', 'bps', 'discount rate'
            ]
            if any(keyword in text for keyword in material_keywords):
                return True
            # Filter out daily interest rate speculation
            noise_keywords = ['may', 'could', 'might', 'expected to', 'likely to']
            if any(keyword in text for keyword in noise_keywords):
                return False
            return True

        # Major fiscal policy - budget, taxation, super tax
        if article.macro_category in ['fiscal_policy', 'taxation']:
            fiscal_keywords = [
                'budget', 'super tax', 'taxation', 'tax rate', 'finance bill',
                'tax amendment', 'capital gains', 'withholding tax', 'sales tax'
            ]
            if any(keyword in text for keyword in fiscal_keywords):
                return True

        # Exchange rate - only major moves matter (>1% single day or new policy)
        if article.macro_category == 'usd_pkr':
            # Check for materiality
            material_fx_keywords = [
                'devaluation', 'revaluation', 'exchange rate policy',
                'rupee crashes', 'rupee surges', 'all-time', 'record',
                'imf', 'current account', 'reserves'
            ]
            if any(keyword in text for keyword in material_fx_keywords):
                return True

            # Check for significant % change mentioned
            if article.price_change_mentioned and abs(article.price_change_mentioned) >= 1.0:
                return True

            # Filter daily PKR fluctuations
            return False

        # TIER 2: Sector-specific macro (only if material)
        # ==================================================

        # Oil/Gas prices - only SIGNIFICANT changes matter
        if article.macro_category in ['oil_prices', 'gas_prices']:
            energy_symbols = ['PSO', 'APL', 'OGDC', 'PPL', 'POL', 'MARI', 'SSGC', 'SNGP', 'HUBC', 'KAPCO']

            if anomaly.symbol not in energy_symbols:
                return False  # Not relevant to non-energy stocks

            # Must be material change (>5% or structural policy)
            material_energy_keywords = [
                'ogra', 'petroleum levy', 'price increase', 'price cut',
                'oil discovery', 'gas discovery', 'exploration',
                'pricing formula', 'tariff', 'circular debt',
                'refinery', 'pipeline', 'lpg price', 'rlng price'
            ]

            # Check for materiality signals
            if any(keyword in text for keyword in material_energy_keywords):
                return True

            # Check for significant price change
            if article.price_change_mentioned and abs(article.price_change_mentioned) >= 5.0:
                return True

            # Filter daily international oil price noise
            noise_keywords = ['brent crude', 'wti', 'global oil', 'international']
            if any(keyword in text for keyword in noise_keywords):
                # Only relevant if it's a massive move (>10%)
                if article.price_change_mentioned and abs(article.price_change_mentioned) >= 10.0:
                    return True
                return False

            return False

        # Chemical prices - only consistent trends or major shifts
        if article.macro_category in ['propylene_prices', 'chemical_prices']:
            chemical_symbols = ['EPCL', 'LOTTE', 'ENGRO', 'ICI', 'LOTCHEM']

            if anomaly.symbol not in chemical_symbols:
                return False

            # Must indicate structural change, not daily volatility
            material_chemical_keywords = [
                'capacity', 'plant', 'margin', 'feedstock',
                'propylene shortage', 'import', 'local production',
                'polymer prices', 'pvc prices', 'pricing mechanism'
            ]

            if any(keyword in text for keyword in material_chemical_keywords):
                return True

            # Check for significant sustained change
            trend_keywords = ['consecutive', 'months', 'sustained', 'trend', 'continuous']
            if any(keyword in text for keyword in trend_keywords):
                if article.price_change_mentioned and abs(article.price_change_mentioned) >= 8.0:
                    return True

            # Filter daily chemical price noise
            return False

        # Inflation - only if official data or major shift
        if article.macro_category == 'inflation':
            consumer_symbols = ['NESTLE', 'UNITY', 'UNILEVER', 'COLG', 'EFOODS']

            # Inflation affects many stocks, but focus on official data
            material_inflation_keywords = [
                'pbs', 'pakistan bureau of statistics', 'cpi',
                'inflation rate', 'inflation data', 'price index',
                'food inflation', 'core inflation'
            ]

            if any(keyword in text for keyword in material_inflation_keywords):
                return True

            # Consumer sector always cares about inflation
            if anomaly.symbol in consumer_symbols:
                return True

            return False

        # TIER 3: PSX-specific events
        # ============================

        # SECP/PSX regulatory changes
        psx_regulatory_keywords = [
            'secp', 'psx', 'kse', 'stock exchange', 'securities',
            'listing', 'delisting', 'trading halt', 'circuit breaker',
            'margin', 'short selling', 'regulatory'
        ]
        if any(keyword in text for keyword in psx_regulatory_keywords):
            return True

        # Political/geopolitical events affecting economy
        major_political_keywords = [
            'election', 'government', 'imf program', 'imf bailout',
            'political crisis', 'default risk', 'credit rating',
            'moody', 'fitch', 's&p', 'sovereign'
        ]
        if any(keyword in text for keyword in major_political_keywords):
            return True

        # Check if symbol is directly mentioned as affected
        if anomaly.symbol in article.indirectly_affected_symbols:
            return True

        # Default: filter out
        return False

    def _generate_explanation(
        self,
        anomaly: Anomaly,
        news_articles: List[NewsArticle],
        correlation_score: float
    ) -> str:
        """
        Generate human-readable explanation for the anomaly

        PSX Context: Provide actionable insights, not just correlation
        """

        if correlation_score < 0.3:
            # Check if it's a high-severity unexplained anomaly
            if anomaly.severity == Severity.HIGH:
                return ("⚠️  High-severity anomaly with no clear news catalyst. "
                       "Possible insider activity, technical factors, or unreported news.")
            return "No material news found. May be technical/sector rotation."

        # Categorize the explanation type
        is_company_specific = any(
            article.primary_symbol == anomaly.symbol
            for article in news_articles
        )
        is_macro_driven = any(
            article.is_macro_news
            for article in news_articles
        )

        # Build contextual explanation
        explanation_parts = []

        # Header based on correlation strength and type
        if correlation_score >= 0.7:
            if is_company_specific:
                explanation_parts.append("🎯 Strong catalyst identified (company-specific):")
            elif is_macro_driven:
                explanation_parts.append("📊 Strong macro driver (sector/market-wide):")
            else:
                explanation_parts.append("🔗 Strong correlation with news:")
        elif correlation_score >= 0.5:
            if is_macro_driven:
                explanation_parts.append("📊 Likely macro-driven (check sector peers):")
            else:
                explanation_parts.append("🔍 Moderate news correlation:")
        else:
            explanation_parts.append("💭 Possible news-related (low confidence):")

        # Add top news with context
        for i, article in enumerate(news_articles[:2], 1):
            sentiment_str = ""
            if article.sentiment_label and article.sentiment_score:
                if abs(article.sentiment_score) > 0.5:
                    sentiment_str = f" [{article.sentiment_label.upper()}]"
                else:
                    sentiment_str = f" [{article.sentiment_label}]"

            # Add materiality indicator
            news_type = "📰"
            if article.is_macro_news:
                news_type = "📊"
            if article.primary_symbol == anomaly.symbol:
                news_type = "🎯"

            explanation_parts.append(
                f"  {news_type} {article.title}{sentiment_str}"
            )

        # Add trading recommendation context
        if correlation_score >= 0.7 and is_company_specific:
            explanation_parts.append(
                "\n  💡 Action: Review company fundamentals - news-driven move may create opportunity"
            )
        elif correlation_score >= 0.7 and is_macro_driven:
            explanation_parts.append(
                "\n  💡 Action: Check sector peers - macro news affects multiple stocks"
            )
        elif anomaly.severity == Severity.HIGH and correlation_score < 0.5:
            explanation_parts.append(
                "\n  ⚠️  Action: Investigate - large move without clear catalyst"
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
