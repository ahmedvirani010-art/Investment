"""
Signal Aggregator v2 - Group-Based Hierarchical Ensemble

Intelligently combines signals from multiple strategies by grouping them
according to trading philosophy:
- Trend Group: Continuation-based (Trend Following, Momentum)
- Reversion Group: Mean-reversion based (Mean Reversion, Statistical Arbitrage)
- Regime Group: Context/risk management (Volatility)

Key Innovation: Resolves conflicts between opposing strategies (trend vs reversion)
using regime-weighted voting instead of naive averaging.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.base_strategy import StrategySignal, EnhancedSnapshot
from psx_technical_agent import SignalType, SignalStrength
from config.technical_config import TechnicalAgentConfig


@dataclass
class EnsembleSignal:
    """
    Aggregated signal with group-level breakdown

    Provides hierarchical view of how different strategy groups
    (trend vs reversion) contribute to final signal.
    """

    # Overall ensemble signal
    bias: SignalType
    bias_strength: SignalStrength
    bias_confidence: float

    # Strategy signals
    strategy_signals: List[StrategySignal]

    # NEW: Group-level consensus
    group_consensus: Dict[str, Dict] = field(default_factory=dict)
    # Example:
    # {
    #   'trend': {'score': 0.7, 'bias': BULLISH, 'confidence': 0.85, 'agreement': 1.0},
    #   'reversion': {'score': -0.4, 'bias': OVERBOUGHT, 'confidence': 0.75, 'agreement': 0.5},
    #   'regime': {'regime': 'NORMAL', 'atr_ratio': 1.0}
    # }

    # Voting breakdown (for backward compatibility)
    bullish_weight: float = 0.0
    bearish_weight: float = 0.0
    neutral_weight: float = 0.0
    total_weight: float = 0.0

    # Agreement metrics
    signal_agreement: float = 0.0  # 0-1, group agreement with final bias
    confidence_weighted_score: float = 0.0  # -1 to +1

    # Metadata
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/display"""
        return {
            'bias': self.bias.value,
            'bias_strength': self.bias_strength.value,
            'bias_confidence': self.bias_confidence,
            'bullish_weight': self.bullish_weight,
            'bearish_weight': self.bearish_weight,
            'neutral_weight': self.neutral_weight,
            'total_weight': self.total_weight,
            'signal_agreement': self.signal_agreement,
            'confidence_weighted_score': self.confidence_weighted_score,
            'num_strategies': len(self.strategy_signals),
            'group_consensus': self.group_consensus,
            'metadata': self.metadata
        }


class SignalAggregator:
    """
    Hierarchical ensemble aggregation with strategy grouping

    Algorithm:
    1. Group strategies by trading philosophy (trend vs reversion)
    2. Calculate consensus within each group
    3. Detect market regime (trending vs ranging)
    4. Weight groups based on regime
    5. Resolve inter-group conflicts intelligently
    """

    # Strategy groups by trading philosophy
    STRATEGY_GROUPS = {
        'trend': ['TrendFollowingStrategy', 'MomentumStrategy'],
        'reversion': ['MeanReversionStrategy', 'StatisticalArbitrageStrategy'],
        'regime': ['VolatilityStrategy']
    }

    def __init__(self, config: TechnicalAgentConfig):
        """
        Initialize aggregator

        Args:
            config: Configuration with strategy weights and thresholds
        """
        self.config = config

    def aggregate(
        self,
        strategy_signals: List[StrategySignal],
        symbol: str,
        date: str
    ) -> EnsembleSignal:
        """
        Aggregate with group-aware conflict resolution

        Steps:
        1. Separate signals by strategy group
        2. Calculate within-group consensus
        3. Detect market regime (trending vs ranging)
        4. Weight groups based on regime
        5. Resolve conflicts using conviction + regime

        Args:
            strategy_signals: List of signals from different strategies
            symbol: Stock symbol being analyzed
            date: Analysis date

        Returns:
            EnsembleSignal with overall bias and group breakdown
        """
        if not strategy_signals:
            return self._create_neutral_signal(strategy_signals, symbol, date, "No strategy signals")

        # Group signals by philosophy
        grouped_signals = self._group_signals(strategy_signals)

        # Calculate within-group consensus
        trend_consensus = self._calculate_group_consensus(grouped_signals['trend'])
        reversion_consensus = self._calculate_group_consensus(grouped_signals['reversion'])
        regime_signal = self._extract_regime_signal(grouped_signals['regime'])

        # Regime-based group weighting
        group_weights = self._calculate_regime_weights(regime_signal)

        # Resolve conflicts
        ensemble_score, overall_bias, confidence = self._resolve_conflicts(
            trend_consensus,
            reversion_consensus,
            group_weights
        )

        # Calculate agreement metrics
        agreement = self._calculate_group_agreement(
            trend_consensus,
            reversion_consensus,
            overall_bias
        )

        # Determine strength
        strength = self._determine_strength(confidence)

        # Calculate traditional voting breakdown (for compatibility)
        votes = self._calculate_traditional_votes(strategy_signals)

        # Build metadata
        metadata = self._build_metadata(
            strategy_signals,
            group_weights,
            trend_consensus,
            reversion_consensus,
            regime_signal,
            symbol,
            date
        )

        return EnsembleSignal(
            bias=overall_bias,
            bias_strength=strength,
            bias_confidence=confidence,
            strategy_signals=strategy_signals,
            group_consensus={
                'trend': trend_consensus,
                'reversion': reversion_consensus,
                'regime': regime_signal
            },
            bullish_weight=votes.get('bullish', 0.0),
            bearish_weight=votes.get('bearish', 0.0),
            neutral_weight=votes.get('neutral', 0.0),
            total_weight=votes.get('total', 0.0),
            signal_agreement=agreement,
            confidence_weighted_score=ensemble_score,
            metadata=metadata
        )

    def _group_signals(self, signals: List[StrategySignal]) -> Dict[str, List[StrategySignal]]:
        """Organize signals by strategy group"""
        grouped = {'trend': [], 'reversion': [], 'regime': []}

        for signal in signals:
            for group_name, strategies in self.STRATEGY_GROUPS.items():
                if signal.strategy_name in strategies:
                    grouped[group_name].append(signal)
                    break

        return grouped

    def _calculate_group_consensus(self, signals: List[StrategySignal]) -> Dict[str, Any]:
        """
        Calculate consensus within a strategy group

        Returns:
            {
                'score': -1.0 to +1.0,
                'confidence': 0.0 to 1.0,
                'bias': SignalType,
                'agreement': 0.0 to 1.0  # Within-group agreement
            }
        """
        if not signals:
            return {
                'score': 0.0,
                'confidence': 0.0,
                'bias': SignalType.NEUTRAL,
                'agreement': 0.0,
                'count': 0
            }

        # Weighted voting within group
        weighted_score = 0.0
        total_weight = 0.0

        for signal in signals:
            direction = self._signal_to_direction(signal.signal_type)
            effective_weight = signal.weight * signal.confidence
            weighted_score += direction * effective_weight
            total_weight += signal.weight

        # Normalize
        group_score = weighted_score / total_weight if total_weight > 0 else 0.0
        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        # Determine bias
        if group_score >= 0.3:
            bias = SignalType.BULLISH
        elif group_score <= -0.3:
            bias = SignalType.BEARISH
        else:
            bias = SignalType.NEUTRAL

        # Within-group agreement
        aligned = sum(1 for s in signals if self._aligns_with_bias(s.signal_type, bias))
        agreement = aligned / len(signals)

        return {
            'score': group_score,
            'confidence': avg_confidence,
            'bias': bias,
            'agreement': agreement,
            'count': len(signals)
        }

    def _extract_regime_signal(self, signals: List[StrategySignal]) -> Dict[str, Any]:
        """Extract volatility regime information"""
        if not signals:
            return {'regime': 'NORMAL', 'atr_ratio': 1.0}

        # Volatility strategy provides regime context
        vol_signal = signals[0]
        return {
            'regime': vol_signal.metadata.get('regime', 'NORMAL'),
            'atr_ratio': vol_signal.metadata.get('atr_ratio', 1.0)
        }

    def _calculate_regime_weights(self, regime_signal: Dict) -> Dict[str, float]:
        """
        Adjust group weights based on market regime

        Logic:
        - TRENDING regime (HIGH_VOL): Favor trend group
        - RANGING regime (LOW_VOL): Favor reversion group
        - NORMAL: Equal weighting
        """
        regime = regime_signal['regime']

        # Get configurable weights or use defaults
        if hasattr(self.config.strategies, 'high_vol_trend_weight'):
            high_vol_trend = self.config.strategies.high_vol_trend_weight
        else:
            high_vol_trend = 0.65

        if hasattr(self.config.strategies, 'low_vol_reversion_weight'):
            low_vol_reversion = self.config.strategies.low_vol_reversion_weight
        else:
            low_vol_reversion = 0.65

        if regime == 'HIGH_VOL':
            # High volatility often favors trend following
            trend_weight = high_vol_trend
            reversion_weight = 1.0 - high_vol_trend
        elif regime == 'LOW_VOL':
            # Low volatility favors mean reversion
            trend_weight = 1.0 - low_vol_reversion
            reversion_weight = low_vol_reversion
        else:  # NORMAL
            trend_weight = 0.5
            reversion_weight = 0.5

        return {
            'trend': trend_weight,
            'reversion': reversion_weight
        }

    def _resolve_conflicts(
        self,
        trend_consensus: Dict,
        reversion_consensus: Dict,
        group_weights: Dict
    ) -> Tuple[float, SignalType, float]:
        """
        Resolve conflicts between trend and reversion groups

        Resolution Strategy:
        1. If both groups agree (same bias): Amplify signal
        2. If groups conflict: Use regime-weighted combination
        3. If one group is neutral: Defer to active group
        4. Track conflict in metadata
        """
        trend_score = trend_consensus['score']
        reversion_score = reversion_consensus['score']
        trend_bias = trend_consensus['bias']
        reversion_bias = reversion_consensus['bias']

        # Get confidence damping/boost factors from config
        if hasattr(self.config.strategies, 'agreement_bonus'):
            agreement_bonus = self.config.strategies.agreement_bonus
        else:
            agreement_bonus = 1.2

        if hasattr(self.config.strategies, 'conflict_confidence_damping'):
            conflict_damping = self.config.strategies.conflict_confidence_damping
        else:
            conflict_damping = 0.7

        # Case 1: Both agree (same direction)
        if self._same_direction(trend_bias, reversion_bias):
            # Amplify: combine scores with regime weighting
            ensemble_score = (
                trend_score * group_weights['trend'] +
                reversion_score * group_weights['reversion']
            )

            # Higher confidence when groups agree
            confidence = min(
                (trend_consensus['confidence'] + reversion_consensus['confidence']) / 2 * agreement_bonus,
                1.0
            )

            overall_bias = trend_bias  # Same as reversion_bias

        # Case 2: Groups conflict (opposite directions)
        elif self._opposite_directions(trend_bias, reversion_bias):
            # Use regime-weighted combination
            ensemble_score = (
                trend_score * group_weights['trend'] +
                reversion_score * group_weights['reversion']
            )

            # Lower confidence during conflicts
            confidence = abs(ensemble_score) * conflict_damping

            # Determine bias from weighted score
            if ensemble_score >= 0.3:
                overall_bias = SignalType.BULLISH
            elif ensemble_score <= -0.3:
                overall_bias = SignalType.BEARISH
            else:
                overall_bias = SignalType.NEUTRAL

        # Case 3: One group neutral, other active
        else:
            if trend_bias != SignalType.NEUTRAL:
                ensemble_score = trend_score * group_weights['trend']
                overall_bias = trend_bias
                confidence = trend_consensus['confidence'] * 0.8
            else:
                ensemble_score = reversion_score * group_weights['reversion']
                overall_bias = reversion_bias
                confidence = reversion_consensus['confidence'] * 0.8

        return ensemble_score, overall_bias, confidence

    def _calculate_group_agreement(
        self,
        trend_consensus: Dict,
        reversion_consensus: Dict,
        overall_bias: SignalType
    ) -> float:
        """
        Calculate how well groups agree with final bias

        Returns: 0.0 to 1.0 (1.0 = perfect agreement)
        """
        trend_agrees = self._aligns_with_bias(trend_consensus['bias'], overall_bias)
        reversion_agrees = self._aligns_with_bias(reversion_consensus['bias'], overall_bias)

        # Weight by within-group agreement
        weighted_agreement = (
            (trend_agrees * trend_consensus['agreement']) +
            (reversion_agrees * reversion_consensus['agreement'])
        ) / 2

        return weighted_agreement

    def _calculate_traditional_votes(self, signals: List[StrategySignal]) -> Dict[str, float]:
        """Calculate traditional voting breakdown for backward compatibility"""
        votes = defaultdict(float)

        for signal in signals:
            effective_weight = signal.weight * signal.confidence

            if signal.signal_type == SignalType.BULLISH:
                votes['bullish'] += effective_weight
            elif signal.signal_type == SignalType.BEARISH:
                votes['bearish'] += effective_weight
            elif signal.signal_type == SignalType.OVERSOLD:
                votes['bullish'] += effective_weight
            elif signal.signal_type == SignalType.OVERBOUGHT:
                votes['bearish'] += effective_weight
            else:
                votes['neutral'] += effective_weight

            votes['total'] += effective_weight

        return dict(votes)

    def _build_metadata(
        self,
        strategy_signals: List[StrategySignal],
        group_weights: Dict,
        trend_consensus: Dict,
        reversion_consensus: Dict,
        regime_signal: Dict,
        symbol: str,
        date: str
    ) -> Dict:
        """Build comprehensive metadata"""

        # Strategy breakdown
        strategy_breakdown = []
        for signal in strategy_signals:
            strategy_breakdown.append({
                'name': signal.strategy_name,
                'signal': signal.signal_type.value,
                'strength': signal.strength.value,
                'confidence': signal.confidence,
                'weight': signal.weight,
                'effective_weight': signal.weight * signal.confidence
            })

        # Detect conflict
        conflict_detected = abs(trend_consensus['score'] - reversion_consensus['score']) > 0.5

        return {
            'symbol': symbol,
            'date': date,
            'num_strategies': len(strategy_signals),
            'strategies': strategy_breakdown,
            'group_weights': group_weights,
            'conflict_detected': conflict_detected,
            'regime': regime_signal['regime'],
            'timestamp': pd.Timestamp.now().isoformat()
        }

    def _determine_strength(self, confidence: float) -> SignalStrength:
        """Determine signal strength from confidence"""
        strong_threshold = getattr(self.config.strategies, 'strong_signal_threshold', 0.75)
        moderate_threshold = getattr(self.config.strategies, 'moderate_signal_threshold', 0.50)

        if confidence >= strong_threshold:
            return SignalStrength.STRONG
        elif confidence >= moderate_threshold:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    # Helper methods

    @staticmethod
    def _signal_to_direction(signal_type: SignalType) -> float:
        """Convert signal type to directional score"""
        return {
            SignalType.BULLISH: 1.0,
            SignalType.BEARISH: -1.0,
            SignalType.OVERSOLD: 1.0,
            SignalType.OVERBOUGHT: -1.0,
            SignalType.NEUTRAL: 0.0
        }[signal_type]

    @staticmethod
    def _same_direction(bias1: SignalType, bias2: SignalType) -> bool:
        """Check if two biases are in same direction"""
        bullish = {SignalType.BULLISH, SignalType.OVERSOLD}
        bearish = {SignalType.BEARISH, SignalType.OVERBOUGHT}

        return (bias1 in bullish and bias2 in bullish) or \
               (bias1 in bearish and bias2 in bearish)

    @staticmethod
    def _opposite_directions(bias1: SignalType, bias2: SignalType) -> bool:
        """Check if two biases are opposite"""
        bullish = {SignalType.BULLISH, SignalType.OVERSOLD}
        bearish = {SignalType.BEARISH, SignalType.OVERBOUGHT}

        return (bias1 in bullish and bias2 in bearish) or \
               (bias1 in bearish and bias2 in bullish)

    @staticmethod
    def _aligns_with_bias(signal_type: SignalType, bias: SignalType) -> bool:
        """Check if signal aligns with overall bias"""
        if bias == SignalType.BULLISH:
            return signal_type in {SignalType.BULLISH, SignalType.OVERSOLD}
        elif bias == SignalType.BEARISH:
            return signal_type in {SignalType.BEARISH, SignalType.OVERBOUGHT}
        else:
            return signal_type == SignalType.NEUTRAL

    def _create_neutral_signal(
        self,
        signals: List[StrategySignal],
        symbol: str,
        date: str,
        reason: str
    ) -> EnsembleSignal:
        """Create neutral ensemble signal"""
        return EnsembleSignal(
            bias=SignalType.NEUTRAL,
            bias_strength=SignalStrength.WEAK,
            bias_confidence=0.0,
            strategy_signals=signals,
            metadata={'reason': reason, 'symbol': symbol, 'date': date}
        )

    def create_enhanced_snapshot(
        self,
        ensemble: EnsembleSignal,
        symbol: str,
        date: str,
        df: pd.DataFrame
    ) -> EnhancedSnapshot:
        """
        Create enhanced snapshot from ensemble signal

        Args:
            ensemble: Aggregated ensemble signal
            symbol: Stock symbol
            date: Analysis date
            df: Price dataframe

        Returns:
            EnhancedSnapshot with full details
        """
        # Get current price for indicator values
        col_map = {col.lower(): col for col in df.columns}
        close = df[col_map.get('close', 'close')]
        current_price = close.iloc[-1]

        # Collect all component signals from all strategies
        all_components = []
        for strategy_signal in ensemble.strategy_signals:
            all_components.extend(strategy_signal.component_signals)

        # Build strategy weights dict
        strategy_weights = {}
        for strategy_signal in ensemble.strategy_signals:
            strategy_weights[strategy_signal.strategy_name] = strategy_signal.weight

        # Build indicator values dict (include current price)
        indicator_values = {
            'price': current_price,
            'ensemble_score': ensemble.confidence_weighted_score,
            'signal_agreement': ensemble.signal_agreement
        }

        # Detect regime from volatility strategy if available
        regime = ensemble.group_consensus.get('regime', {}).get('regime', 'NORMAL')

        return EnhancedSnapshot(
            symbol=symbol,
            date=date,
            signals=all_components,
            overall_bias=ensemble.bias,
            confidence=ensemble.bias_confidence,
            indicator_values=indicator_values,
            strategy_signals=ensemble.strategy_signals,
            strategy_weights=strategy_weights,
            ensemble_score=ensemble.confidence_weighted_score,
            regime=regime,
            ensemble_signal=ensemble  # Store full ensemble for group consensus access
        )


if __name__ == "__main__":
    """Test group-based signal aggregator"""
    print("="*80)
    print("GROUP-BASED SIGNAL AGGREGATOR - TEST")
    print("="*80)

    from strategies.trend_following import TrendFollowingStrategy
    from strategies.mean_reversion import MeanReversionStrategy
    from strategies.momentum import MomentumStrategy
    from strategies.volatility import VolatilityStrategy
    from strategies.statistical_arbitrage import StatisticalArbitrageStrategy
    from test_strategy_synthetic import create_uptrend_data

    # Initialize
    config = TechnicalAgentConfig()
    aggregator = SignalAggregator(config)

    # Create all strategies
    strategies = [
        TrendFollowingStrategy(config),
        MeanReversionStrategy(config),
        MomentumStrategy(config),
        VolatilityStrategy(config),
        StatisticalArbitrageStrategy(config)
    ]

    print(f"\n📊 Strategy Groups:")
    for group_name, strat_names in SignalAggregator.STRATEGY_GROUPS.items():
        print(f"   {group_name.upper()} Group: {', '.join(strat_names)}")

    # Create synthetic data
    df = create_uptrend_data(200)
    print(f"\n📈 Synthetic data: {len(df)} days")
    print(f"   Price: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")

    # Analyze with all strategies
    date = df.index[-1].strftime('%Y-%m-%d')
    signals = []

    print(f"\n🔍 Individual Strategy Signals:")
    for strategy in strategies:
        signal = strategy.analyze('TEST', df, date)
        signals.append(signal)
        print(f"   {strategy.name:25s}: {signal.signal_type.value:12s} "
              f"(conf: {signal.confidence:.0%}, weight: {signal.weight:.0%})")

    # Aggregate signals
    ensemble = aggregator.aggregate(signals, 'TEST', date)

    print(f"\n{'='*80}")
    print("🎯 GROUP-BASED ENSEMBLE SIGNAL")
    print(f"{'='*80}")
    print(f"Overall Bias:     {ensemble.bias.value}")
    print(f"Strength:         {ensemble.bias_strength.value}")
    print(f"Confidence:       {ensemble.bias_confidence:.0%}")
    print(f"Agreement:        {ensemble.signal_agreement:.0%}")
    print(f"Weighted Score:   {ensemble.confidence_weighted_score:+.2f}")

    print(f"\n📊 Group Consensus:")
    for group_name, consensus in ensemble.group_consensus.items():
        if group_name != 'regime':
            print(f"   {group_name.upper():10s}: {consensus.get('bias', 'N/A'):12s} "
                  f"(score: {consensus.get('score', 0):+.2f}, conf: {consensus.get('confidence', 0):.0%}, "
                  f"agree: {consensus.get('agreement', 0):.0%})")
        else:
            print(f"   REGIME:     {consensus.get('regime', 'NORMAL')} (ATR: {consensus.get('atr_ratio', 1.0):.2f})")

    if 'conflict_detected' in ensemble.metadata:
        if ensemble.metadata['conflict_detected']:
            print(f"\n⚠️  CONFLICT DETECTED between trend and reversion groups!")
            print(f"   Regime weights: Trend={ensemble.metadata['group_weights']['trend']:.0%}, "
                  f"Reversion={ensemble.metadata['group_weights']['reversion']:.0%}")

    print("\n" + "="*80)
    print("✅ Group-based aggregator test complete")
    print("="*80)
