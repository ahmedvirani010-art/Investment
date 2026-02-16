"""
PSX Sentiment Momentum Tracker
Analyzes sentiment trends over time and generates momentum-based signals
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from scipy import stats

from psx_sentiment_momentum_store import (
    SentimentMomentumStore,
    SentimentMomentum,
    DailySentiment
)


@dataclass
class MomentumSignal:
    """Trading signal based on sentiment momentum."""
    symbol: str
    date: str
    signal_type: str            # 'buy', 'sell', 'hold'
    strength: str               # 'strong', 'moderate', 'weak'
    reasons: List[str]          # List of reasons for the signal
    sentiment_score: float      # Current sentiment
    momentum_7d: float
    momentum_14d: float
    momentum_30d: float
    price_sentiment_correlation: Optional[float]
    confidence: float
    trend: str
    reversal_signal: Optional[str]
    divergence_type: Optional[str]


class SentimentMomentumTracker:
    """
    Analyzes sentiment momentum and generates trading signals
    """

    def __init__(self, sentiment_store: SentimentMomentumStore,
                 price_store=None):
        """
        Initialize sentiment momentum tracker

        Args:
            sentiment_store: SentimentMomentumStore instance
            price_store: Optional PSXPriceStore instance for divergence detection
        """
        self.sentiment_store = sentiment_store
        self.price_store = price_store

        # Thresholds for signal generation
        self.momentum_threshold_strong = 0.015      # Strong momentum change
        self.momentum_threshold_moderate = 0.008    # Moderate momentum change
        self.reversal_threshold = 0.0               # Cross from negative to positive or vice versa
        self.stable_threshold = 0.005               # Within this range = stable

    def analyze_symbol(self, symbol: str, date: str = None) -> Optional[MomentumSignal]:
        """
        Full momentum analysis for one stock

        Args:
            symbol: Stock symbol
            date: Date to analyze (defaults to latest)

        Returns:
            MomentumSignal object or None if insufficient data
        """
        if not date:
            date = self.sentiment_store.get_latest_date(symbol)
            if not date:
                return None

        # Get sentiment history (30 days for 30-day momentum)
        sentiment_history = self.sentiment_store.get_sentiment_history(symbol, days=35)

        if len(sentiment_history) < 7:
            # Need at least 7 days for basic momentum
            return None

        # Compute momentum indicators
        momentum_data = self.compute_momentum(sentiment_history)

        # Get current sentiment
        current_sentiment = sentiment_history.iloc[-1]['avg_sentiment']

        # Detect reversals
        reversal_signal = self.detect_reversals(sentiment_history)

        # Detect divergences (if price store available)
        divergence_type = None
        price_sentiment_correlation = None
        if self.price_store:
            try:
                price_history = self.price_store.get_prices(symbol, days=30)
                if not price_history.empty:
                    divergence_type = self.detect_divergences(
                        symbol, sentiment_history, price_history
                    )
                    price_sentiment_correlation = self._compute_correlation(
                        sentiment_history, price_history
                    )
            except:
                pass  # Price data not available, skip divergence

        # Determine trend
        trend = self._determine_trend(
            momentum_data['momentum_7d'],
            momentum_data['momentum_14d'],
            momentum_data['momentum_30d']
        )

        # Determine strength
        strength = self._determine_strength(
            momentum_data['momentum_7d'],
            momentum_data['momentum_14d'],
            reversal_signal,
            divergence_type
        )

        # Generate signal
        signal_type, reasons = self._generate_signal(
            current_sentiment,
            momentum_data,
            trend,
            reversal_signal,
            divergence_type,
            sentiment_history
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            momentum_data,
            len(sentiment_history),
            sentiment_history.iloc[-1]['article_count'],
            reversal_signal,
            divergence_type
        )

        # Create and save momentum record
        momentum = SentimentMomentum(
            symbol=symbol,
            date=date,
            momentum_7d=momentum_data['momentum_7d'],
            momentum_14d=momentum_data['momentum_14d'],
            momentum_30d=momentum_data['momentum_30d'],
            trend=trend,
            strength=strength,
            reversal_signal=reversal_signal,
            divergence_type=divergence_type,
            signal_type=signal_type,
            computed_at=datetime.now().isoformat()
        )
        self.sentiment_store.save_momentum(momentum)

        # Create signal
        signal = MomentumSignal(
            symbol=symbol,
            date=date,
            signal_type=signal_type,
            strength=strength,
            reasons=reasons,
            sentiment_score=current_sentiment,
            momentum_7d=momentum_data['momentum_7d'],
            momentum_14d=momentum_data['momentum_14d'],
            momentum_30d=momentum_data['momentum_30d'],
            price_sentiment_correlation=price_sentiment_correlation,
            confidence=confidence,
            trend=trend,
            reversal_signal=reversal_signal,
            divergence_type=divergence_type
        )

        return signal

    def analyze_batch(self, symbols: List[str], date: str = None) -> Dict[str, MomentumSignal]:
        """
        Analyze multiple stocks

        Args:
            symbols: List of stock symbols
            date: Date to analyze (defaults to latest)

        Returns:
            Dictionary mapping symbol to MomentumSignal
        """
        results = {}
        for symbol in symbols:
            signal = self.analyze_symbol(symbol, date)
            if signal:
                results[symbol] = signal
        return results

    def compute_momentum(self, sentiment_history: pd.DataFrame) -> Dict[str, float]:
        """
        Compute momentum indicators from sentiment history

        Args:
            sentiment_history: DataFrame with sentiment data

        Returns:
            Dictionary with momentum values
        """
        momentum = {
            'momentum_7d': 0.0,
            'momentum_14d': 0.0,
            'momentum_30d': 0.0
        }

        # Need at least minimum periods
        if len(sentiment_history) >= 7:
            momentum['momentum_7d'] = self._compute_slope(
                sentiment_history['avg_sentiment'].tail(7)
            )

        if len(sentiment_history) >= 14:
            momentum['momentum_14d'] = self._compute_slope(
                sentiment_history['avg_sentiment'].tail(14)
            )

        if len(sentiment_history) >= 30:
            momentum['momentum_30d'] = self._compute_slope(
                sentiment_history['avg_sentiment'].tail(30)
            )

        return momentum

    def _compute_slope(self, series: pd.Series) -> float:
        """
        Compute linear regression slope

        Args:
            series: Pandas series of values

        Returns:
            Slope value
        """
        if len(series) < 2:
            return 0.0

        x = np.arange(len(series))
        y = series.values

        # Handle NaN values
        mask = ~np.isnan(y)
        if mask.sum() < 2:
            return 0.0

        x = x[mask]
        y = y[mask]

        slope, _, _, _, _ = stats.linregress(x, y)
        return slope

    def detect_reversals(self, sentiment_history: pd.DataFrame) -> Optional[str]:
        """
        Detect sentiment reversals

        Args:
            sentiment_history: DataFrame with sentiment data

        Returns:
            'bullish_reversal', 'bearish_reversal', or None
        """
        if len(sentiment_history) < 3:
            return None

        # Look at last 3 days
        recent = sentiment_history.tail(3)
        sentiments = recent['avg_sentiment'].values

        # Current sentiment
        current = sentiments[-1]
        previous = sentiments[-2] if len(sentiments) > 1 else 0.0

        # Bullish reversal: was negative, now positive
        if previous < -0.05 and current > 0.05:
            return 'bullish_reversal'

        # Bearish reversal: was positive, now negative
        if previous > 0.05 and current < -0.05:
            return 'bearish_reversal'

        # Check for trend reversal (crossing zero)
        if len(sentiments) >= 3:
            older = sentiments[-3]

            # Crossing from negative to positive territory
            if older < 0 and previous < 0 and current > 0:
                return 'bullish_reversal'

            # Crossing from positive to negative territory
            if older > 0 and previous > 0 and current < 0:
                return 'bearish_reversal'

        return None

    def detect_divergences(self, symbol: str,
                          sentiment_history: pd.DataFrame,
                          price_history: pd.DataFrame) -> Optional[str]:
        """
        Detect sentiment-price divergences

        Args:
            symbol: Stock symbol
            sentiment_history: DataFrame with sentiment data
            price_history: DataFrame with price data

        Returns:
            'bullish_divergence', 'bearish_divergence', or None
        """
        if len(sentiment_history) < 14 or len(price_history) < 14:
            return None

        # Align dates
        sentiment_history = sentiment_history.copy()
        price_history = price_history.copy()

        # Convert dates to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(sentiment_history['date']):
            sentiment_history['date'] = pd.to_datetime(sentiment_history['date'])
        if 'Date' in price_history.columns:
            price_history['date'] = pd.to_datetime(price_history['Date'])
        elif not pd.api.types.is_datetime64_any_dtype(price_history.index):
            price_history['date'] = pd.to_datetime(price_history.index)
        else:
            price_history['date'] = price_history.index

        # Get last 14 days
        recent_sentiment = sentiment_history.tail(14)
        recent_price = price_history.tail(14)

        # Compute sentiment momentum (last 7 days vs previous 7 days)
        if len(recent_sentiment) >= 14:
            sentiment_recent = recent_sentiment['avg_sentiment'].tail(7).mean()
            sentiment_older = recent_sentiment['avg_sentiment'].head(7).mean()
            sentiment_change = sentiment_recent - sentiment_older
        else:
            return None

        # Compute price momentum (last 7 days vs previous 7 days)
        if len(recent_price) >= 14:
            if 'Close' in recent_price.columns:
                price_col = 'Close'
            elif 'close' in recent_price.columns:
                price_col = 'close'
            else:
                return None

            price_recent = recent_price[price_col].tail(7).mean()
            price_older = recent_price[price_col].head(7).mean()
            price_change_pct = (price_recent - price_older) / price_older * 100
        else:
            return None

        # Bullish divergence: price declining but sentiment improving
        if price_change_pct < -3.0 and sentiment_change > 0.1:
            return 'bullish_divergence'

        # Bearish divergence: price rising but sentiment declining
        if price_change_pct > 3.0 and sentiment_change < -0.1:
            return 'bearish_divergence'

        return None

    def _compute_correlation(self, sentiment_history: pd.DataFrame,
                            price_history: pd.DataFrame) -> Optional[float]:
        """
        Compute correlation between sentiment and price

        Args:
            sentiment_history: DataFrame with sentiment data
            price_history: DataFrame with price data

        Returns:
            Correlation coefficient or None
        """
        try:
            # Align dates and compute correlation
            # This is simplified - in production would do proper date alignment
            if len(sentiment_history) < 10 or len(price_history) < 10:
                return None

            sentiment_values = sentiment_history['avg_sentiment'].tail(14).values
            if 'Close' in price_history.columns:
                price_values = price_history['Close'].tail(14).values
            elif 'close' in price_history.columns:
                price_values = price_history['close'].tail(14).values
            else:
                return None

            min_len = min(len(sentiment_values), len(price_values))
            if min_len < 5:
                return None

            correlation = np.corrcoef(
                sentiment_values[-min_len:],
                price_values[-min_len:]
            )[0, 1]

            return correlation if not np.isnan(correlation) else None
        except:
            return None

    def _determine_trend(self, momentum_7d: float, momentum_14d: float,
                        momentum_30d: float) -> str:
        """
        Determine sentiment trend

        Args:
            momentum_7d: 7-day momentum
            momentum_14d: 14-day momentum
            momentum_30d: 30-day momentum

        Returns:
            'improving', 'declining', or 'stable'
        """
        # Count positive vs negative momentum indicators
        positive_count = sum([
            momentum_7d > self.stable_threshold,
            momentum_14d > self.stable_threshold,
            momentum_30d > self.stable_threshold
        ])

        negative_count = sum([
            momentum_7d < -self.stable_threshold,
            momentum_14d < -self.stable_threshold,
            momentum_30d < -self.stable_threshold
        ])

        if positive_count >= 2:
            return 'improving'
        elif negative_count >= 2:
            return 'declining'
        else:
            return 'stable'

    def _determine_strength(self, momentum_7d: float, momentum_14d: float,
                           reversal_signal: Optional[str],
                           divergence_type: Optional[str]) -> str:
        """
        Determine signal strength

        Args:
            momentum_7d: 7-day momentum
            momentum_14d: 14-day momentum
            reversal_signal: Reversal signal type
            divergence_type: Divergence type

        Returns:
            'strong', 'moderate', or 'weak'
        """
        strong_indicators = 0

        # Strong momentum changes
        if abs(momentum_7d) > self.momentum_threshold_strong:
            strong_indicators += 1
        if abs(momentum_14d) > self.momentum_threshold_strong:
            strong_indicators += 1

        # Reversals and divergences add to strength
        if reversal_signal:
            strong_indicators += 1
        if divergence_type:
            strong_indicators += 1

        if strong_indicators >= 3:
            return 'strong'
        elif strong_indicators >= 2:
            return 'moderate'
        else:
            return 'weak'

    def _generate_signal(self, current_sentiment: float,
                        momentum_data: Dict[str, float],
                        trend: str,
                        reversal_signal: Optional[str],
                        divergence_type: Optional[str],
                        sentiment_history: pd.DataFrame) -> Tuple[str, List[str]]:
        """
        Generate trading signal

        Args:
            current_sentiment: Current sentiment score
            momentum_data: Momentum indicators
            trend: Trend direction
            reversal_signal: Reversal signal type
            divergence_type: Divergence type
            sentiment_history: Sentiment history

        Returns:
            (signal_type, reasons) tuple
        """
        reasons = []
        buy_score = 0
        sell_score = 0

        # Current sentiment bias
        if current_sentiment > 0.3:
            buy_score += 1
            reasons.append(f"Positive sentiment ({current_sentiment:.2f})")
        elif current_sentiment < -0.3:
            sell_score += 1
            reasons.append(f"Negative sentiment ({current_sentiment:.2f})")

        # Momentum trend
        if trend == 'improving':
            buy_score += 2
            reasons.append("Sentiment momentum improving")
        elif trend == 'declining':
            sell_score += 2
            reasons.append("Sentiment momentum declining")

        # Reversals
        if reversal_signal == 'bullish_reversal':
            buy_score += 2
            reasons.append("Bullish sentiment reversal detected")
        elif reversal_signal == 'bearish_reversal':
            sell_score += 2
            reasons.append("Bearish sentiment reversal detected")

        # Divergences
        if divergence_type == 'bullish_divergence':
            buy_score += 2
            reasons.append("Bullish divergence: Sentiment improving while price falling")
        elif divergence_type == 'bearish_divergence':
            sell_score += 2
            reasons.append("Bearish divergence: Sentiment declining while price rising")

        # Strong short-term momentum
        if momentum_data['momentum_7d'] > self.momentum_threshold_strong:
            buy_score += 1
            reasons.append("Strong positive 7-day momentum")
        elif momentum_data['momentum_7d'] < -self.momentum_threshold_strong:
            sell_score += 1
            reasons.append("Strong negative 7-day momentum")

        # Determine signal
        if buy_score > sell_score and buy_score >= 2:
            return 'buy', reasons
        elif sell_score > buy_score and sell_score >= 2:
            return 'sell', reasons
        else:
            if not reasons:
                reasons.append("No clear momentum signal")
            return 'hold', reasons

    def _calculate_confidence(self, momentum_data: Dict[str, float],
                             history_length: int, article_count: int,
                             reversal_signal: Optional[str],
                             divergence_type: Optional[str]) -> float:
        """
        Calculate signal confidence

        Args:
            momentum_data: Momentum indicators
            history_length: Length of sentiment history
            article_count: Number of articles for current day
            reversal_signal: Reversal signal type
            divergence_type: Divergence type

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.5  # Base confidence

        # More history = more confidence
        if history_length >= 30:
            confidence += 0.15
        elif history_length >= 14:
            confidence += 0.1
        elif history_length >= 7:
            confidence += 0.05

        # More articles = more confidence
        if article_count >= 5:
            confidence += 0.15
        elif article_count >= 3:
            confidence += 0.1
        elif article_count >= 1:
            confidence += 0.05

        # Aligned momentum = more confidence
        momentum_7d = momentum_data['momentum_7d']
        momentum_14d = momentum_data['momentum_14d']
        momentum_30d = momentum_data['momentum_30d']

        same_sign = (
            (momentum_7d > 0 and momentum_14d > 0 and momentum_30d > 0) or
            (momentum_7d < 0 and momentum_14d < 0 and momentum_30d < 0)
        )
        if same_sign:
            confidence += 0.1

        # Reversals and divergences add confidence
        if reversal_signal:
            confidence += 0.05
        if divergence_type:
            confidence += 0.05

        return min(confidence, 1.0)

    def get_buy_signals(self, date: str = None) -> List[MomentumSignal]:
        """
        Get all stocks with buy signals

        Args:
            date: Date to filter by (defaults to latest)

        Returns:
            List of MomentumSignal objects
        """
        symbols = self.sentiment_store.get_symbols_by_signal('buy', date)
        signals = []

        for symbol in symbols:
            momentum = self.sentiment_store.get_momentum(symbol, date)
            if momentum:
                # Reconstruct signal from stored momentum
                # (simplified - in production would store full signal)
                signals.append(momentum)

        return signals

    def get_sell_signals(self, date: str = None) -> List[MomentumSignal]:
        """
        Get all stocks with sell signals

        Args:
            date: Date to filter by (defaults to latest)

        Returns:
            List of MomentumSignal objects
        """
        symbols = self.sentiment_store.get_symbols_by_signal('sell', date)
        signals = []

        for symbol in symbols:
            momentum = self.sentiment_store.get_momentum(symbol, date)
            if momentum:
                signals.append(momentum)

        return signals

    def print_signal(self, signal: MomentumSignal):
        """
        Print formatted signal report

        Args:
            signal: MomentumSignal object
        """
        print("=" * 80)
        print(f"SENTIMENT MOMENTUM SIGNAL: {signal.symbol}")
        print("=" * 80)
        print(f"\n📊 SIGNAL: {signal.signal_type.upper()} ({signal.strength.upper()})")
        print(f"   Date: {signal.date}")
        print(f"   Confidence: {signal.confidence:.1%}")

        print(f"\n💭 CURRENT SENTIMENT: {signal.sentiment_score:+.3f} ({signal.trend})")

        print(f"\n📈 MOMENTUM INDICATORS:")
        print(f"   7-Day:  {signal.momentum_7d:+.4f}")
        print(f"   14-Day: {signal.momentum_14d:+.4f}")
        print(f"   30-Day: {signal.momentum_30d:+.4f}")

        if signal.reversal_signal:
            print(f"\n🔄 REVERSAL: {signal.reversal_signal.replace('_', ' ').title()}")

        if signal.divergence_type:
            print(f"\n⚠️  DIVERGENCE: {signal.divergence_type.replace('_', ' ').title()}")

        if signal.price_sentiment_correlation is not None:
            print(f"\n🔗 PRICE-SENTIMENT CORRELATION: {signal.price_sentiment_correlation:.2f}")

        print(f"\n💡 REASONS:")
        for reason in signal.reasons:
            print(f"   • {reason}")

        print("=" * 80)
        print()
