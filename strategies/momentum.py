"""
Momentum Strategy

Uses multi-period returns (1m/3m/6m) with volume confirmation to identify
strong momentum.

Logic:
- Weighted composite of 1/3/6 month returns
- Volume momentum confirms price movement
- Strong momentum = high returns + high volume
"""

import pandas as pd
import numpy as np
from typing import List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.base_strategy import BaseStrategy, StrategySignal
from psx_technical_agent import TechnicalSignal, SignalType, SignalStrength
from indicators.advanced_indicators import AdvancedIndicators
from config.technical_config import TechnicalAgentConfig


class MomentumStrategy(BaseStrategy):
    """
    Multi-factor momentum strategy with volume confirmation

    Strong momentum signals occur when:
    1. Positive returns across multiple timeframes (1m/3m/6m)
    2. Volume momentum > threshold (confirms trend)
    3. Weighted score exceeds minimum threshold
    """

    def get_required_days(self) -> int:
        """Require 6 months of data for long-term momentum"""
        return 132  # ~6 months of trading days

    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze momentum across multiple timeframes

        Returns:
            StrategySignal with BULLISH/BEARISH/NEUTRAL based on momentum
        """
        components = []
        metadata = {}

        try:
            # Calculate multi-period returns
            ret_1m, ret_3m, ret_6m = AdvancedIndicators.compute_multi_period_returns(df)

            metadata['ret_1m'] = ret_1m if ret_1m is not None else 0.0
            metadata['ret_3m'] = ret_3m if ret_3m is not None else 0.0
            metadata['ret_6m'] = ret_6m if ret_6m is not None else 0.0

            # Calculate weighted momentum score
            weights = [
                self.config.strategies.momentum_1m_weight,
                self.config.strategies.momentum_3m_weight,
                self.config.strategies.momentum_6m_weight
            ]

            # Only use available returns
            returns = []
            used_weights = []

            if ret_1m is not None:
                returns.append(ret_1m)
                used_weights.append(weights[0])

            if ret_3m is not None:
                returns.append(ret_3m)
                used_weights.append(weights[1])

            if ret_6m is not None:
                returns.append(ret_6m)
                used_weights.append(weights[2])

            if not returns:
                # Not enough data
                return self._create_signal(
                    strategy_name="Momentum",
                    signal_type=SignalType.NEUTRAL,
                    strength=SignalStrength.WEAK,
                    confidence=0.0,
                    weight=self.config.strategies.momentum_weight,
                    components=[],
                    metadata={"error": "Insufficient data for momentum calculation"}
                )

            # Normalize weights
            total_weight = sum(used_weights)
            normalized_weights = [w / total_weight for w in used_weights]

            # Calculate weighted momentum score
            momentum_score = sum(r * w for r, w in zip(returns, normalized_weights))
            metadata['momentum_score'] = momentum_score

            # Calculate volume momentum
            volume_momentum = AdvancedIndicators.compute_volume_momentum(
                df,
                self.config.indicators.volume_period
            )

            metadata['volume_momentum'] = volume_momentum
            has_volume_confirmation = volume_momentum >= self.config.strategies.momentum_min_volume_ratio
            metadata['has_volume_confirmation'] = has_volume_confirmation

            # Determine signal based on momentum and volume
            min_return = self.config.strategies.momentum_min_return

            if momentum_score > min_return and has_volume_confirmation:
                # Strong bullish momentum
                signal_type = SignalType.BULLISH

                # Confidence based on momentum strength and volume
                momentum_conf = min(abs(momentum_score) / 0.15, 1.0)  # Cap at 15% return
                volume_conf = min((volume_momentum - 1.0) / 1.0, 1.0)  # Normalize from 1.0-2.0
                confidence = (momentum_conf + volume_conf) / 2.0

                # Add component signals
                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Momentum_Score",
                    signal_type=SignalType.BULLISH,
                    strength=self._determine_strength(momentum_conf),
                    value=momentum_score,
                    threshold=min_return,
                    description=f"Positive momentum: {momentum_score*100:+.1f}%"
                ))

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Volume_Momentum",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.MODERATE,
                    value=volume_momentum,
                    threshold=self.config.strategies.momentum_min_volume_ratio,
                    description=f"Volume confirmation: {volume_momentum:.2f}x average"
                ))

            elif momentum_score < -min_return and has_volume_confirmation:
                # Strong bearish momentum
                signal_type = SignalType.BEARISH

                momentum_conf = min(abs(momentum_score) / 0.15, 1.0)
                volume_conf = min((volume_momentum - 1.0) / 1.0, 1.0)
                confidence = (momentum_conf + volume_conf) / 2.0

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Momentum_Score",
                    signal_type=SignalType.BEARISH,
                    strength=self._determine_strength(momentum_conf),
                    value=momentum_score,
                    threshold=-min_return,
                    description=f"Negative momentum: {momentum_score*100:+.1f}%"
                ))

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Volume_Momentum",
                    signal_type=SignalType.BEARISH,
                    strength=SignalStrength.MODERATE,
                    value=volume_momentum,
                    threshold=self.config.strategies.momentum_min_volume_ratio,
                    description=f"Volume confirmation: {volume_momentum:.2f}x average"
                ))

            else:
                # Weak or no momentum
                signal_type = SignalType.NEUTRAL
                confidence = 0.3

                if not has_volume_confirmation:
                    metadata['neutral_reason'] = f"Volume {volume_momentum:.2f}x too low for confirmation"
                else:
                    metadata['neutral_reason'] = f"Momentum {momentum_score*100:+.1f}% below threshold"

            strength = self._determine_strength(confidence)

            return self._create_signal(
                strategy_name="Momentum",
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                weight=self.config.strategies.momentum_weight,
                components=components,
                metadata=metadata
            )

        except Exception as e:
            return self._create_signal(
                strategy_name="Momentum",
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                weight=self.config.strategies.momentum_weight,
                components=[],
                metadata={"error": str(e)}
            )


if __name__ == "__main__":
    """Test momentum strategy"""
    print("="*80)
    print("MOMENTUM STRATEGY - TEST")
    print("="*80)

    from test_strategy_synthetic import create_uptrend_data

    # Initialize
    config = TechnicalAgentConfig()
    strategy = MomentumStrategy(config)

    print(f"\n📊 Strategy: {strategy.name}")
    print(f"   Weight: {config.strategies.momentum_weight:.0%}")
    print(f"   Required days: {strategy.get_required_days()}")
    print(f"   Min return: {config.strategies.momentum_min_return*100:.1f}%")
    print(f"   Min volume ratio: {config.strategies.momentum_min_volume_ratio:.1f}x")

    # Create synthetic data
    df = create_uptrend_data(200)
    print(f"\n📈 Testing with synthetic data: {len(df)} days")
    print(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # Analyze
    date = df.index[-1].strftime('%Y-%m-%d')
    signal = strategy.analyze('TEST', df, date)

    # Display results
    print(f"\n🔔 Signal: {signal.signal_type.value}")
    print(f"   Strength: {signal.strength.value}")
    print(f"   Confidence: {signal.confidence:.0%}")

    print(f"\n📊 Indicators:")
    print(f"   1-month return: {signal.metadata.get('ret_1m', 0)*100:+.2f}%")
    print(f"   3-month return: {signal.metadata.get('ret_3m', 0)*100:+.2f}%")
    print(f"   6-month return: {signal.metadata.get('ret_6m', 0)*100:+.2f}%")
    print(f"   Momentum score: {signal.metadata.get('momentum_score', 0)*100:+.2f}%")
    print(f"   Volume momentum: {signal.metadata.get('volume_momentum', 0):.2f}x")
    print(f"   Volume confirmation: {'Yes' if signal.metadata.get('has_volume_confirmation') else 'No'}")

    if 'neutral_reason' in signal.metadata:
        print(f"   Reason: {signal.metadata['neutral_reason']}")

    if signal.component_signals:
        print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
        for comp in signal.component_signals:
            print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Momentum strategy test complete")
    print("="*80)
