"""
Signal Aggregator

Combines signals from multiple strategies into a unified ensemble signal.

Features:
- Weighted voting based on strategy confidence
- Signal conflict resolution
- Overall bias calculation (BULLISH/BEARISH/NEUTRAL)
- Comprehensive metadata for transparency
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
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
    """Aggregated signal from multiple strategies"""

    # Overall bias
    bias: SignalType
    bias_strength: SignalStrength
    bias_confidence: float

    # Strategy signals
    strategy_signals: List[StrategySignal]

    # Voting breakdown
    bullish_weight: float = 0.0
    bearish_weight: float = 0.0
    neutral_weight: float = 0.0
    total_weight: float = 0.0

    # Agreement metrics
    signal_agreement: float = 0.0  # 0-1, how much strategies agree
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
            'metadata': self.metadata
        }


class SignalAggregator:
    """
    Aggregates signals from multiple trading strategies

    Uses weighted voting where each strategy contributes:
    - Its configured weight (from config)
    - Scaled by its confidence level (0-1)

    Final bias determined by majority weighted vote.
    """

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
        Aggregate multiple strategy signals into unified signal

        Args:
            strategy_signals: List of signals from different strategies
            symbol: Stock symbol being analyzed
            date: Analysis date

        Returns:
            EnsembleSignal with overall bias and voting breakdown
        """
        if not strategy_signals:
            return self._create_neutral_signal(strategy_signals, "No strategy signals")

        # Calculate weighted votes
        votes = self._calculate_weighted_votes(strategy_signals)

        # Determine overall bias
        bias, bias_strength, bias_confidence = self._determine_bias(votes)

        # Calculate agreement metrics
        agreement = self._calculate_agreement(strategy_signals, bias)
        confidence_score = self._calculate_confidence_score(votes)

        # Build metadata
        metadata = self._build_metadata(strategy_signals, votes, symbol, date)

        return EnsembleSignal(
            bias=bias,
            bias_strength=bias_strength,
            bias_confidence=bias_confidence,
            strategy_signals=strategy_signals,
            bullish_weight=votes.get('bullish', 0.0),
            bearish_weight=votes.get('bearish', 0.0),
            neutral_weight=votes.get('neutral', 0.0),
            total_weight=votes.get('total', 0.0),
            signal_agreement=agreement,
            confidence_weighted_score=confidence_score,
            metadata=metadata
        )

    def _calculate_weighted_votes(
        self,
        signals: List[StrategySignal]
    ) -> Dict[str, float]:
        """
        Calculate weighted votes for each signal type

        Weight = strategy_weight * confidence

        Returns:
            Dict with bullish/bearish/neutral/total weights
        """
        votes = defaultdict(float)

        for signal in signals:
            # Calculate effective weight
            effective_weight = signal.weight * signal.confidence

            # Add to appropriate bucket
            if signal.signal_type == SignalType.BULLISH:
                votes['bullish'] += effective_weight
            elif signal.signal_type == SignalType.BEARISH:
                votes['bearish'] += effective_weight
            elif signal.signal_type == SignalType.OVERSOLD:
                # Oversold = bullish bias (buy opportunity)
                votes['bullish'] += effective_weight
            elif signal.signal_type == SignalType.OVERBOUGHT:
                # Overbought = bearish bias (sell opportunity)
                votes['bearish'] += effective_weight
            else:
                # Neutral or unknown
                votes['neutral'] += effective_weight

            votes['total'] += effective_weight

        return dict(votes)

    def _determine_bias(
        self,
        votes: Dict[str, float]
    ) -> Tuple[SignalType, SignalStrength, float]:
        """
        Determine overall bias from weighted votes

        Args:
            votes: Weighted votes dict

        Returns:
            (bias, strength, confidence) tuple
        """
        total = votes.get('total', 0)

        if total == 0:
            return SignalType.NEUTRAL, SignalStrength.WEAK, 0.0

        bullish = votes.get('bullish', 0)
        bearish = votes.get('bearish', 0)
        neutral = votes.get('neutral', 0)

        # Calculate percentages
        bullish_pct = bullish / total
        bearish_pct = bearish / total
        neutral_pct = neutral / total

        # Minimum threshold for non-neutral signal
        min_threshold = self.config.strategies.ensemble_min_confidence

        # Determine bias
        if bullish_pct > bearish_pct and bullish_pct >= min_threshold:
            bias = SignalType.BULLISH
            confidence = bullish_pct

        elif bearish_pct > bullish_pct and bearish_pct >= min_threshold:
            bias = SignalType.BEARISH
            confidence = bearish_pct

        else:
            # Either neutral is strongest, or no signal meets threshold
            bias = SignalType.NEUTRAL
            confidence = max(neutral_pct, 0.3)

        # Determine strength based on confidence
        if confidence >= 0.7:
            strength = SignalStrength.STRONG
        elif confidence >= 0.5:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        return bias, strength, confidence

    def _calculate_agreement(
        self,
        signals: List[StrategySignal],
        overall_bias: SignalType
    ) -> float:
        """
        Calculate how much strategies agree with overall bias

        Args:
            signals: Strategy signals
            overall_bias: Determined overall bias

        Returns:
            Agreement score 0-1 (1 = all agree)
        """
        if not signals:
            return 0.0

        # Count strategies that align with overall bias
        aligned = 0
        total = len(signals)

        for signal in signals:
            # Map signal types to bias
            if overall_bias == SignalType.BULLISH:
                if signal.signal_type in [SignalType.BULLISH, SignalType.OVERSOLD]:
                    aligned += 1
            elif overall_bias == SignalType.BEARISH:
                if signal.signal_type in [SignalType.BEARISH, SignalType.OVERBOUGHT]:
                    aligned += 1
            else:  # NEUTRAL
                if signal.signal_type == SignalType.NEUTRAL:
                    aligned += 1

        return aligned / total

    def _calculate_confidence_score(
        self,
        votes: Dict[str, float]
    ) -> float:
        """
        Calculate confidence-weighted score (-1 to +1)

        Positive = bullish bias
        Negative = bearish bias

        Args:
            votes: Weighted votes

        Returns:
            Score from -1 (max bearish) to +1 (max bullish)
        """
        total = votes.get('total', 0)
        if total == 0:
            return 0.0

        bullish = votes.get('bullish', 0)
        bearish = votes.get('bearish', 0)

        # Net score
        net = (bullish - bearish) / total

        return np.clip(net, -1.0, 1.0)

    def _build_metadata(
        self,
        signals: List[StrategySignal],
        votes: Dict[str, float],
        symbol: str,
        date: str
    ) -> Dict:
        """Build comprehensive metadata"""

        # Strategy breakdown
        strategy_breakdown = []
        for signal in signals:
            strategy_breakdown.append({
                'name': signal.strategy_name,
                'signal': signal.signal_type.value,
                'strength': signal.strength.value,
                'confidence': signal.confidence,
                'weight': signal.weight,
                'effective_weight': signal.weight * signal.confidence
            })

        # Vote percentages
        total = votes.get('total', 1)  # Avoid division by zero
        vote_pcts = {
            'bullish_pct': votes.get('bullish', 0) / total,
            'bearish_pct': votes.get('bearish', 0) / total,
            'neutral_pct': votes.get('neutral', 0) / total
        }

        return {
            'symbol': symbol,
            'date': date,
            'num_strategies': len(signals),
            'strategies': strategy_breakdown,
            'vote_percentages': vote_pcts,
            'timestamp': pd.Timestamp.now().isoformat()
        }

    def _create_neutral_signal(
        self,
        signals: List[StrategySignal],
        reason: str
    ) -> EnsembleSignal:
        """Create neutral ensemble signal"""
        return EnsembleSignal(
            bias=SignalType.NEUTRAL,
            bias_strength=SignalStrength.WEAK,
            bias_confidence=0.0,
            strategy_signals=signals,
            metadata={'reason': reason}
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
        regime = "NORMAL"
        for strategy_signal in ensemble.strategy_signals:
            if strategy_signal.strategy_name == "Volatility":
                regime = strategy_signal.metadata.get('regime', 'NORMAL')
                break

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
            regime=regime
        )


if __name__ == "__main__":
    """Test signal aggregator"""
    print("="*80)
    print("SIGNAL AGGREGATOR - TEST")
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

    print(f"\n📊 Testing with {len(strategies)} strategies:")
    weight_map = {
        'TrendFollowingStrategy': config.strategies.trend_following_weight,
        'MeanReversionStrategy': config.strategies.mean_reversion_weight,
        'MomentumStrategy': config.strategies.momentum_weight,
        'VolatilityStrategy': config.strategies.volatility_weight,
        'StatisticalArbitrageStrategy': config.strategies.statistical_arb_weight
    }
    for s in strategies:
        print(f"   • {s.name} (weight: {weight_map.get(s.name, 0):.0%})")

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
              f"(confidence: {signal.confidence:.0%}, weight: {signal.weight:.0%})")

    # Aggregate signals
    ensemble = aggregator.aggregate(signals, 'TEST', date)

    print(f"\n{'='*80}")
    print("🎯 ENSEMBLE SIGNAL")
    print(f"{'='*80}")
    print(f"Overall Bias:     {ensemble.bias.value}")
    print(f"Strength:         {ensemble.bias_strength.value}")
    print(f"Confidence:       {ensemble.bias_confidence:.0%}")
    print(f"Agreement:        {ensemble.signal_agreement:.0%}")
    print(f"Weighted Score:   {ensemble.confidence_weighted_score:+.2f}")

    print(f"\n📊 Vote Breakdown:")
    print(f"   Bullish: {ensemble.bullish_weight:.3f} ({ensemble.bullish_weight/ensemble.total_weight*100:.1f}%)")
    print(f"   Bearish: {ensemble.bearish_weight:.3f} ({ensemble.bearish_weight/ensemble.total_weight*100:.1f}%)")
    print(f"   Neutral: {ensemble.neutral_weight:.3f} ({ensemble.neutral_weight/ensemble.total_weight*100:.1f}%)")
    print(f"   Total:   {ensemble.total_weight:.3f}")

    print(f"\n📋 Strategy Details:")
    for strat in ensemble.metadata['strategies']:
        print(f"   {strat['name']:25s}: {strat['signal']:12s} "
              f"(eff_weight: {strat['effective_weight']:.3f})")

    # Create enhanced snapshot
    snapshot = aggregator.create_enhanced_snapshot(ensemble, 'TEST', date, df)

    print(f"\n📸 Enhanced Snapshot:")
    print(f"   Symbol: {snapshot.symbol}")
    print(f"   Date: {snapshot.date}")
    print(f"   Price: {snapshot.indicator_values.get('price', 0):.2f}")
    print(f"   Signal: {snapshot.overall_bias.value} (confidence: {snapshot.confidence:.0%})")
    print(f"   Ensemble score: {snapshot.ensemble_score:+.2f}")
    print(f"   Regime: {snapshot.regime}")
    print(f"   Strategy signals: {len(snapshot.strategy_signals)}")
    print(f"   Component signals: {len(snapshot.signals)}")

    print("\n" + "="*80)
    print("✅ Signal aggregator test complete")
    print("="*80)
