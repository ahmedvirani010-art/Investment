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
from psx_announcement_storage import AnnouncementStorage, Announcement
import re


@dataclass
class NewsAnomalyCorrelation:
    """Represents a correlation between news/announcements and an anomaly"""
    anomaly: Anomaly
    related_news: List[NewsArticle]
    related_announcements: List[Announcement]  # PSX official announcements
    correlation_score: float
    explanation: str
    news_summary: List[str]
    announcement_summary: List[str]  # Official announcements summary


class NewsAnomalyCorrelator:
    """
    Correlates market anomalies with news events

    Analyzes detected anomalies and matches them with relevant news articles
    to provide context and potential explanations for unusual market behavior.
    """

    def __init__(
        self,
        news_storage: Optional[NewsStorage] = None,
        announcement_storage: Optional[AnnouncementStorage] = None
    ):
        """
        Initialize correlator

        Args:
            news_storage: NewsStorage instance (creates new if None)
            announcement_storage: AnnouncementStorage instance (creates new if None)
        """
        self.storage = news_storage or NewsStorage()
        self.announcement_storage = announcement_storage or AnnouncementStorage()

    def correlate_anomaly(self, anomaly: Anomaly, lookback_days: int = 3) -> NewsAnomalyCorrelation:
        """
        Find news articles and PSX announcements that may explain an anomaly

        PSX Context: Prioritize official announcements over media news

        Args:
            anomaly: Detected anomaly
            lookback_days: How many days back to search

        Returns:
            NewsAnomalyCorrelation with scored relevance
        """
        # STEP 1: Check PSX official announcements FIRST (primary source)
        announcements = self.announcement_storage.get_announcements_by_symbol(
            anomaly.symbol,
            days=lookback_days
        )

        # Score announcements (higher base score than news - authoritative source)
        scored_items = []

        for ann in announcements:
            # Base score depends on materiality tier
            if ann.materiality_tier == 1:  # Critical
                base_score = 0.8
            elif ann.materiality_tier == 2:  # Material
                base_score = 0.6
            else:  # Informational
                base_score = 0.3

            # Time proximity bonus
            time_score = self._time_proximity_score(anomaly, ann.announcement_date)

            # Anomaly type alignment bonus
            type_bonus = self._announcement_anomaly_alignment(anomaly, ann)

            total_score = min(base_score + time_score + type_bonus, 1.0)
            scored_items.append((total_score, 'announcement', ann))

        # STEP 2: Get news articles (secondary source)
        symbol_news = self.storage.get_articles_by_symbol(
            anomaly.symbol,
            days=lookback_days
        )

        # Get macro news that might affect the stock
        macro_news = self.storage.get_macro_news(hours=lookback_days * 24)

        # Score symbol-specific news (with penalty for being secondary source)
        for article in symbol_news:
            # Check materiality first
            if not self._is_news_material(article, anomaly):
                continue

            score = self._calculate_relevance_score(anomaly, article, is_direct=True)
            # 20% penalty for being secondary source vs official announcement
            if score > 0.4:
                scored_items.append((score * 0.8, 'news', article))

        # Add relevant macro news (with even higher penalty)
        for article in macro_news:
            if self._is_macro_relevant(anomaly, article):
                score = self._calculate_relevance_score(anomaly, article, is_direct=False)
                # 30% penalty for macro news
                if score > 0.5:
                    scored_items.append((score * 0.7, 'news', article))

        # Sort by score (announcements naturally rank higher)
        scored_items.sort(reverse=True, key=lambda x: x[0])

        # Separate announcements and news
        related_announcements = [
            item for score, source_type, item in scored_items
            if source_type == 'announcement'
        ][:3]  # Top 3 announcements

        related_news = [
            item for score, source_type, item in scored_items
            if source_type == 'news'
        ][:5]  # Top 5 news articles

        # Calculate overall correlation score (best item wins)
        if scored_items:
            correlation_score = scored_items[0][0]
        else:
            correlation_score = 0.0

        # Generate enhanced explanation (prioritizes announcements)
        explanation = self._generate_explanation_with_announcements(
            anomaly, related_announcements, related_news, correlation_score
        )

        # Create summaries
        announcement_summary = [
            f"{ann.title} ({ann.announcement_date.strftime('%Y-%m-%d')}) [Tier {ann.materiality_tier}]"
            for ann in related_announcements
        ]

        news_summary = [
            f"{article.title} ({article.source}, {article.published_date.strftime('%Y-%m-%d')})"
            for article in related_news[:3]
        ]

        return NewsAnomalyCorrelation(
            anomaly=anomaly,
            related_news=related_news,
            related_announcements=related_announcements,
            correlation_score=correlation_score,
            explanation=explanation,
            news_summary=news_summary,
            announcement_summary=announcement_summary
        )

    def _time_proximity_score(self, anomaly: Anomaly, announcement_date: datetime) -> float:
        """
        Calculate time proximity score for announcement

        Args:
            anomaly: The anomaly
            announcement_date: When announcement was made

        Returns:
            Score (0.0 to 0.3)
        """
        anomaly_date = datetime.strptime(anomaly.date, '%Y-%m-%d')
        days_diff = abs((anomaly_date - announcement_date).days)

        if days_diff == 0:
            return 0.3  # Same day - highest relevance
        elif days_diff == 1:
            return 0.2  # Day before/after
        elif days_diff <= 2:
            return 0.1  # Within 2 days
        else:
            return 0.0  # Too far

    def _announcement_anomaly_alignment(self, anomaly: Anomaly, announcement: Announcement) -> float:
        """
        Score how well announcement type aligns with anomaly type

        Args:
            anomaly: The anomaly
            announcement: The announcement

        Returns:
            Alignment bonus (0.0 to 0.2)
        """
        score = 0.0

        # Dividends cause volume spikes and price movements
        if announcement.category == 'dividend':
            if anomaly.anomaly_type in [AnomalyType.VOLUME_SPIKE, AnomalyType.PRICE_MOVEMENT]:
                score += 0.15
                # Large dividends create larger moves
                if announcement.dividend_amount and announcement.dividend_amount >= 30:
                    score += 0.05

        # Financial results cause all types of anomalies
        if announcement.category == 'financial_results':
            score += 0.1
            # Strong profit changes aligned with price movement
            if announcement.profit_change_pct and anomaly.anomaly_type == AnomalyType.PRICE_MOVEMENT:
                if (announcement.profit_change_pct > 0 and anomaly.value > 0) or \
                   (announcement.profit_change_pct < 0 and anomaly.value < 0):
                    score += 0.1

        # Major contracts cause positive price moves and volume
        if announcement.category == 'contract' and announcement.subcategory == 'major':
            if anomaly.anomaly_type in [AnomalyType.VOLUME_SPIKE, AnomalyType.PRICE_MOVEMENT]:
                score += 0.15

        # Corporate actions cause high volume and volatility
        if announcement.category == 'corporate_action':
            if anomaly.anomaly_type in [AnomalyType.VOLUME_SPIKE, AnomalyType.VOLATILITY_SPIKE]:
                score += 0.15

        # Material info typically negative
        if announcement.category == 'material_info':
            if anomaly.anomaly_type == AnomalyType.PRICE_MOVEMENT and anomaly.value < 0:
                score += 0.1

        return min(score, 0.2)

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

    def _generate_explanation_with_announcements(
        self,
        anomaly: Anomaly,
        announcements: List[Announcement],
        news_articles: List[NewsArticle],
        correlation_score: float
    ) -> str:
        """
        Generate human-readable explanation prioritizing official announcements

        PSX Context: Official announcements > Media news
        """

        if correlation_score < 0.3:
            # Check if it's a high-severity unexplained anomaly
            if anomaly.severity == Severity.HIGH:
                return ("⚠️  High-severity anomaly with no clear catalyst. "
                       "Possible insider activity, technical factors, or unreported news.")
            return "No material news or announcements found. May be technical/sector rotation."

        # Build explanation prioritizing announcements
        explanation_parts = []

        # Check if we have official announcement explaining this
        has_critical_announcement = any(
            ann.materiality_tier == 1 for ann in announcements
        )
        has_any_announcement = len(announcements) > 0

        # PRIORITY 1: Official PSX Announcement (authoritative)
        if has_critical_announcement and correlation_score >= 0.7:
            explanation_parts.append("🎯 OFFICIAL ANNOUNCEMENT (PSX):")
            explanation_parts.append("   " + "="*76)

            # Show top critical announcement
            critical = [ann for ann in announcements if ann.materiality_tier == 1][0]
            explanation_parts.append(f"   📋 {critical.title}")
            explanation_parts.append(f"   📅 {critical.announcement_date.strftime('%Y-%m-%d')}")
            explanation_parts.append(f"   🏷️  Category: {critical.category}")
            if critical.subcategory:
                explanation_parts.append(f"        Subcategory: {critical.subcategory}")
            explanation_parts.append(f"   ⭐ Materiality: Tier {critical.materiality_tier} (CRITICAL)")

            # Add financial details if available
            if critical.dividend_amount:
                explanation_parts.append(f"   💰 Dividend: {critical.dividend_amount}% ({critical.dividend_type})")
            if critical.eps:
                explanation_parts.append(f"   📊 EPS: Rs {critical.eps}")
            if critical.profit_change_pct:
                explanation_parts.append(f"   📈 Profit: {critical.profit_change_pct:+.1f}% YoY")

            explanation_parts.append("")
            explanation_parts.append("   💡 Action: Official catalyst identified - review fundamentals")

        # PRIORITY 2: Material announcement (tier 2) or multiple announcements
        elif has_any_announcement and correlation_score >= 0.5:
            explanation_parts.append("📋 PSX Announcement (Material):")

            for ann in announcements[:2]:
                tier_label = {1: "CRITICAL", 2: "MATERIAL", 3: "INFO"}[ann.materiality_tier]
                explanation_parts.append(f"   • {ann.title}")
                explanation_parts.append(f"     [{ann.category} | Tier {ann.materiality_tier}: {tier_label}]")

            explanation_parts.append("")
            explanation_parts.append("   💡 Action: Check announcement details for impact assessment")

        # PRIORITY 3: News-based explanation (no authoritative announcement)
        else:
            is_company_specific = any(
                article.primary_symbol == anomaly.symbol
                for article in news_articles
            )
            is_macro_driven = any(
                article.is_macro_news
                for article in news_articles
            )

            # Header based on correlation strength
            if correlation_score >= 0.7:
                if is_company_specific:
                    explanation_parts.append("📰 News Report (verify with PSX announcements):")
                elif is_macro_driven:
                    explanation_parts.append("📊 Macro News (sector/market-wide):")
                else:
                    explanation_parts.append("🔗 News Correlation:")
            elif correlation_score >= 0.5:
                if is_macro_driven:
                    explanation_parts.append("📊 Likely macro-driven (check sector peers):")
                else:
                    explanation_parts.append("🔍 Moderate news correlation:")
            else:
                explanation_parts.append("💭 Possible news-related (low confidence):")

            # Add top news
            for article in news_articles[:2]:
                sentiment_str = ""
                if article.sentiment_label and article.sentiment_score:
                    if abs(article.sentiment_score) > 0.5:
                        sentiment_str = f" [{article.sentiment_label.upper()}]"
                    else:
                        sentiment_str = f" [{article.sentiment_label}]"

                news_type = "📊" if article.is_macro_news else "📰"
                explanation_parts.append(f"   {news_type} {article.title}{sentiment_str}")

            # Add recommendation
            if not has_any_announcement:
                explanation_parts.append("")
                explanation_parts.append("   ⚠️  Note: Secondary source - check PSX for official announcement")

        # Supporting news (if we have announcements + news)
        if has_any_announcement and len(news_articles) > 0 and correlation_score >= 0.7:
            explanation_parts.append("")
            explanation_parts.append("   Supporting news coverage:")
            for article in news_articles[:2]:
                sentiment = f" ({article.sentiment_label})" if article.sentiment_label else ""
                explanation_parts.append(f"   📰 {article.title[:60]}...{sentiment}")

        return "\n".join(explanation_parts)

    def _generate_explanation(
        self,
        anomaly: Anomaly,
        news_articles: List[NewsArticle],
        correlation_score: float
    ) -> str:
        """
        Legacy method - calls enhanced version with no announcements

        Maintained for backward compatibility
        """
        return self._generate_explanation_with_announcements(
            anomaly, [], news_articles, correlation_score
        )

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
        print("PSX ANOMALY-ANNOUNCEMENT-NEWS CORRELATION REPORT")
        print("="*100)

        total_anomalies = sum(len(corrs) for corrs in correlations.values())
        explained_anomalies = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if corr.correlation_score >= 0.5
        )

        # Count anomalies explained by announcements
        announcement_explained = sum(
            1 for corrs in correlations.values()
            for corr in corrs
            if len(corr.related_announcements) > 0 and corr.correlation_score >= 0.5
        )

        print(f"\nTotal Anomalies: {total_anomalies}")
        print(f"Explained by Announcements (≥50%): {announcement_explained}")
        print(f"Explained by News/Announcements (≥50%): {explained_anomalies}")
        print(f"Coverage: {explained_anomalies/total_anomalies*100:.1f}%")
        print(f"Announcement Coverage: {announcement_explained/total_anomalies*100:.1f}%")

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

                # Correlation score
                correlation_emoji = "🔗" if corr.correlation_score >= 0.7 else "🔍" if corr.correlation_score >= 0.5 else "❓"
                print(f"\n   {correlation_emoji} Correlation Score: {corr.correlation_score*100:.0f}%")

                # Show PSX announcements FIRST (priority)
                if corr.related_announcements:
                    print(f"\n   🎯 PSX Announcements ({len(corr.related_announcements)}):")
                    print("   " + "="*76)

                    for i, ann in enumerate(corr.related_announcements, 1):
                        # Tier indicator
                        tier_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}[ann.materiality_tier]
                        tier_label = {1: "CRITICAL", 2: "MATERIAL", 3: "INFO"}[ann.materiality_tier]

                        print(f"   {i}. {tier_emoji} {ann.title}")
                        print(f"      Category: {ann.category}", end="")
                        if ann.subcategory:
                            print(f" ({ann.subcategory})", end="")
                        print(f" | Tier {ann.materiality_tier}: {tier_label}")
                        print(f"      Date: {ann.announcement_date.strftime('%Y-%m-%d')}")

                        # Financial data
                        if ann.dividend_amount:
                            print(f"      💰 Dividend: {ann.dividend_amount}% ({ann.dividend_type})")
                        if ann.eps:
                            print(f"      📊 EPS: Rs {ann.eps}")
                        if ann.profit_change_pct:
                            print(f"      📈 Profit: {ann.profit_change_pct:+.1f}% YoY")

                        if ann.source_url:
                            print(f"      🔗 {ann.source_url}")
                        print()

                # Show news articles (secondary source)
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
                    if not corr.related_announcements:
                        print(f"   ❌ No announcements or news found")

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
