"""
PSX Sentiment Analyzer
Analyzes sentiment of financial news using VADER
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Tuple, List, Optional
from dataclasses import dataclass
import re


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    score: float  # -1 to +1
    label: str  # 'positive', 'negative', 'neutral'
    confidence: float  # 0 to 1
    scores_breakdown: dict  # Raw scores from analyzer


class PSXSentimentAnalyzer:
    """
    Sentiment analyzer for financial news
    Uses VADER (Valence Aware Dictionary and sEntiment Reasoner)
    """

    def __init__(self):
        """Initialize VADER analyzer with financial lexicon"""
        self.analyzer = SentimentIntensityAnalyzer()

        # Enhance VADER with financial keywords
        self._add_financial_lexicon()

    def _add_financial_lexicon(self):
        """Add Pakistani/financial specific terms to VADER lexicon"""
        # Positive financial terms
        financial_positive = {
            'profit': 2.0,
            'gain': 2.0,
            'surge': 2.5,
            'rally': 2.5,
            'boost': 2.0,
            'growth': 2.0,
            'increase': 1.5,
            'strong': 1.5,
            'bullish': 2.5,
            'upgrade': 2.0,
            'outperform': 2.5,
            'dividend': 1.5,
            'bonus': 2.0,
            'expansion': 1.5,
            'record': 2.0,
            'beat': 2.0,
            'exceed': 2.0,
        }

        # Negative financial terms
        financial_negative = {
            'loss': -2.0,
            'decline': -2.0,
            'fall': -2.0,
            'drop': -2.0,
            'crash': -3.0,
            'plunge': -3.0,
            'weak': -1.5,
            'bearish': -2.5,
            'downgrade': -2.5,
            'underperform': -2.5,
            'deficit': -2.0,
            'debt': -1.5,
            'crisis': -2.5,
            'concern': -1.5,
            'worry': -1.5,
            'miss': -2.0,
            'shortfall': -2.0,
        }

        # Update VADER lexicon
        self.analyzer.lexicon.update(financial_positive)
        self.analyzer.lexicon.update(financial_negative)

    def extract_price_change(self, text: str) -> Tuple[Optional[float], str]:
        """
        Extract price change percentage from text

        Returns:
            (percentage_change, direction) tuple
        """
        # Patterns for price changes
        patterns = [
            (r'(?:up|rose|gained?|increased?)\s+(?:by\s+)?(\d+\.?\d*)%', 'positive'),
            (r'(?:down|fell|dropped?|decreased?)\s+(?:by\s+)?(\d+\.?\d*)%', 'negative'),
            (r'([+-]?\d+\.?\d*)%', 'neutral'),
        ]

        for pattern, direction in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    change = float(match.group(1))
                    return (change, direction)
                except (ValueError, AttributeError):
                    pass

        return (None, 'neutral')

    def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with score, label, and confidence
        """
        # Get VADER scores
        scores = self.analyzer.polarity_scores(text)

        # Compound score is the normalized score (-1 to +1)
        compound = scores['compound']

        # Determine label based on thresholds
        if compound >= 0.05:
            label = 'positive'
            confidence = min(abs(compound), 1.0)
        elif compound <= -0.05:
            label = 'negative'
            confidence = min(abs(compound), 1.0)
        else:
            label = 'neutral'
            confidence = 1.0 - abs(compound)

        # Check for price changes to adjust sentiment
        price_change, direction = self.extract_price_change(text)
        if price_change:
            # Large price changes increase confidence
            if price_change > 5.0:
                confidence = min(confidence * 1.2, 1.0)

            # Adjust sentiment based on direction
            if direction == 'positive' and compound < 0.5:
                compound = max(compound, 0.3)
                label = 'positive'
            elif direction == 'negative' and compound > -0.5:
                compound = min(compound, -0.3)
                label = 'negative'

        return SentimentResult(
            score=compound,
            label=label,
            confidence=confidence,
            scores_breakdown=scores
        )

    def analyze_article(self, title: str, text: str, weight_title: float = 2.0) -> SentimentResult:
        """
        Analyze sentiment of an article (title + body)

        Args:
            title: Article title
            text: Article body
            weight_title: How much more to weight title sentiment (default: 2.0)

        Returns:
            Combined SentimentResult
        """
        # Analyze title and body separately
        title_result = self.analyze_text(title)
        body_result = self.analyze_text(text[:1000])  # First 1000 chars of body

        # Weighted average (title has more weight)
        combined_score = (
            (title_result.score * weight_title + body_result.score) /
            (weight_title + 1)
        )

        # Determine label
        if combined_score >= 0.05:
            label = 'positive'
        elif combined_score <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'

        # Average confidence
        confidence = (title_result.confidence + body_result.confidence) / 2

        return SentimentResult(
            score=combined_score,
            label=label,
            confidence=confidence,
            scores_breakdown={
                'title': title_result.scores_breakdown,
                'body': body_result.scores_breakdown,
                'combined_compound': combined_score
            }
        )

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts

        Args:
            texts: List of texts to analyze

        Returns:
            List of SentimentResults
        """
        return [self.analyze_text(text) for text in texts]

    def get_sentiment_summary(self, results: List[SentimentResult]) -> dict:
        """
        Get summary statistics for a batch of sentiment results

        Args:
            results: List of SentimentResults

        Returns:
            Dictionary with summary stats
        """
        if not results:
            return {
                'count': 0,
                'avg_score': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'positive_pct': 0.0,
                'negative_pct': 0.0,
                'neutral_pct': 0.0
            }

        scores = [r.score for r in results]
        labels = [r.label for r in results]

        positive_count = labels.count('positive')
        negative_count = labels.count('negative')
        neutral_count = labels.count('neutral')
        total = len(results)

        return {
            'count': total,
            'avg_score': sum(scores) / total if total > 0 else 0.0,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_pct': (positive_count / total * 100) if total > 0 else 0.0,
            'negative_pct': (negative_count / total * 100) if total > 0 else 0.0,
            'neutral_pct': (neutral_count / total * 100) if total > 0 else 0.0
        }
