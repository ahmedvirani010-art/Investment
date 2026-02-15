"""
Statistical Arbitrage Strategy

Uses Hurst exponent and return distribution properties (skewness, kurtosis)
to identify statistical trading opportunities.

Logic:
- Hurst < 0.4: Strong mean-reversion regime
- Skewness indicates asymmetric distribution
- Combined with Hurst for directional signals
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


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Statistical arbitrage using Hurst exponent and distribution properties

    Trading logic:
    - Hurst < 0.4 + positive skew: Mean reversion to upside (bullish)
    - Hurst < 0.4 + negative skew: Mean reversion to downside (bearish)
    - Kurtosis provides confirmation of tail risk
    """

    def get_required_days(self) -> int:
        """Require enough days for Hurst + skewness/kurtosis"""
        return max(
            self.config.indicators.hurst_window,
            self.config.indicators.skew_window,
            self.config.indicators.kurt_window
        ) + 20

    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze statistical properties for arbitrage opportunities

        Returns:
            StrategySignal based on mean-reversion + distribution asymmetry
        """
        components = []
        metadata = {}

        try:
            # Get close prices
            col_map = {col.lower(): col for col in df.columns}
            close = df[col_map.get('close', 'close')]

            # Calculate Hurst exponent
            hurst = AdvancedIndicators.compute_hurst_exponent(
                close,
                self.config.indicators.hurst_window
            )

            metadata['hurst'] = hurst
            is_mean_reverting = hurst < self.config.strategies.stat_arb_hurst_threshold
            metadata['is_mean_reverting'] = is_mean_reverting

            # Calculate skewness
            skew = AdvancedIndicators.compute_skewness(
                df,
                self.config.indicators.skew_window
            )

            metadata['skewness'] = skew

            # Calculate kurtosis
            kurt = AdvancedIndicators.compute_kurtosis(
                df,
                self.config.indicators.kurt_window
            )

            metadata['kurtosis'] = kurt
            has_fat_tails = kurt > 0  # Positive excess kurtosis
            metadata['has_fat_tails'] = has_fat_tails

            # Signal logic
            skew_threshold = self.config.strategies.stat_arb_skew_threshold

            if is_mean_reverting and skew > skew_threshold:
                # Strong mean reversion + positive skew
                # = Market has been making extreme positive moves
                # = Expect mean reversion = BULLISH opportunity
                signal_type = SignalType.BULLISH

                # Confidence based on how strong the mean reversion is
                hurst_conf = (self.config.strategies.stat_arb_hurst_threshold - hurst) / \
                            self.config.strategies.stat_arb_hurst_threshold
                skew_conf = min(abs(skew) / 2.0, 1.0)  # Normalize skewness

                confidence = (hurst_conf + skew_conf) / 2.0
                confidence = min(confidence, 0.7)  # Cap at 0.7 (this is statistical, not guaranteed)

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Hurst_Exponent",
                    signal_type=SignalType.BULLISH,
                    strength=self._determine_strength(hurst_conf),
                    value=hurst,
                    threshold=self.config.strategies.stat_arb_hurst_threshold,
                    description=f"Mean-reverting regime (H={hurst:.3f})"
                ))

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Skewness",
                    signal_type=SignalType.BULLISH,
                    strength=self._determine_strength(skew_conf),
                    value=skew,
                    threshold=skew_threshold,
                    description=f"Positive skew ({skew:.2f}) suggests upside potential"
                ))

                metadata['signal_reason'] = "Mean-reverting + positive skew = bullish opportunity"

            elif is_mean_reverting and skew < -skew_threshold:
                # Strong mean reversion + negative skew
                # = Market has been making extreme negative moves
                # = Expect mean reversion = BEARISH signal (caution)
                signal_type = SignalType.BEARISH

                hurst_conf = (self.config.strategies.stat_arb_hurst_threshold - hurst) / \
                            self.config.strategies.stat_arb_hurst_threshold
                skew_conf = min(abs(skew) / 2.0, 1.0)

                confidence = (hurst_conf + skew_conf) / 2.0
                confidence = min(confidence, 0.7)

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Hurst_Exponent",
                    signal_type=SignalType.BEARISH,
                    strength=self._determine_strength(hurst_conf),
                    value=hurst,
                    threshold=self.config.strategies.stat_arb_hurst_threshold,
                    description=f"Mean-reverting regime (H={hurst:.3f})"
                ))

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Skewness",
                    signal_type=SignalType.BEARISH,
                    strength=self._determine_strength(skew_conf),
                    value=skew,
                    threshold=-skew_threshold,
                    description=f"Negative skew ({skew:.2f}) suggests downside risk"
                ))

                metadata['signal_reason'] = "Mean-reverting + negative skew = bearish signal"

            else:
                # No strong statistical opportunity
                signal_type = SignalType.NEUTRAL
                confidence = 0.2

                if not is_mean_reverting:
                    metadata['signal_reason'] = f"Hurst {hurst:.3f} indicates trending, not mean-reverting"
                else:
                    metadata['signal_reason'] = f"Skewness {skew:.2f} not extreme enough"

            strength = self._determine_strength(confidence)

            return self._create_signal(
                strategy_name="StatisticalArbitrage",
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                weight=self.config.strategies.statistical_arb_weight,
                components=components,
                metadata=metadata
            )

        except Exception as e:
            return self._create_signal(
                strategy_name="StatisticalArbitrage",
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                weight=self.config.strategies.statistical_arb_weight,
                components=[],
                metadata={"error": str(e)}
            )


if __name__ == "__main__":
    """Test statistical arbitrage strategy"""
    print("="*80)
    print("STATISTICAL ARBITRAGE STRATEGY - TEST")
    print("="*80)

    from test_strategy_synthetic import create_uptrend_data

    # Initialize
    config = TechnicalAgentConfig()
    strategy = StatisticalArbitrageStrategy(config)

    print(f"\n📊 Strategy: {strategy.name}")
    print(f"   Weight: {config.strategies.statistical_arb_weight:.0%}")
    print(f"   Required days: {strategy.get_required_days()}")
    print(f"   Hurst threshold: <{config.strategies.stat_arb_hurst_threshold}")
    print(f"   Skew threshold: ±{config.strategies.stat_arb_skew_threshold}")

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
    print(f"   Hurst: {signal.metadata.get('hurst', 0):.3f}")
    print(f"   Skewness: {signal.metadata.get('skewness', 0):.3f}")
    print(f"   Kurtosis: {signal.metadata.get('kurtosis', 0):.3f}")
    print(f"   Mean-reverting: {'Yes' if signal.metadata.get('is_mean_reverting') else 'No'}")
    print(f"   Fat tails: {'Yes' if signal.metadata.get('has_fat_tails') else 'No'}")
    print(f"   Reason: {signal.metadata.get('signal_reason', 'N/A')}")

    if signal.component_signals:
        print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
        for comp in signal.component_signals:
            print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Statistical arbitrage strategy test complete")
    print("="*80)
