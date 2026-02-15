"""
Mean Reversion Strategy

Uses z-score, Bollinger Bands, dual RSI, and Hurst exponent to identify
mean-reversion opportunities.

Logic:
- Z-score measures price deviation from mean
- Bollinger Band position confirms extremes
- Dual RSI crossovers signal reversals
- Hurst < 0.5 confirms mean-reverting regime
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


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion using z-score + Bollinger Bands + dual RSI + Hurst exponent

    Strong mean-reversion signals occur when:
    1. Price is at extremes (z-score > 2 or < -2)
    2. Price at Bollinger Band edges
    3. Hurst exponent < 0.5 (mean-reverting regime)
    4. RSI confirms oversold/overbought
    """

    def get_required_days(self) -> int:
        """Require enough days for z-score + Bollinger + Hurst"""
        return max(
            self.config.indicators.zscore_window,
            self.config.indicators.bb_period,
            self.config.indicators.hurst_window
        ) + 20

    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze mean-reversion opportunities

        Returns:
            StrategySignal with OVERSOLD/OVERBOUGHT/NEUTRAL
        """
        components = []
        metadata = {}

        try:
            # Get close prices
            col_map = {col.lower(): col for col in df.columns}
            close = df[col_map.get('close', 'close')]

            # Calculate z-score
            window = self.config.indicators.zscore_window
            mean = close.rolling(window=window).mean()
            std = close.rolling(window=window).std()
            z_score = (close.iloc[-1] - mean.iloc[-1]) / std.iloc[-1] if std.iloc[-1] > 0 else 0.0

            metadata['z_score'] = z_score
            metadata['price'] = close.iloc[-1]
            metadata['mean'] = mean.iloc[-1]

            # Calculate Bollinger Bands
            bb_period = self.config.indicators.bb_period
            bb_std = self.config.indicators.bb_std
            bb_mean = close.rolling(window=bb_period).mean()
            bb_std_dev = close.rolling(window=bb_period).std()
            bb_upper = bb_mean + (bb_std_dev * bb_std)
            bb_lower = bb_mean - (bb_std_dev * bb_std)

            # Bollinger Band position (0 = lower band, 1 = upper band)
            bb_position = (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) \
                if (bb_upper.iloc[-1] - bb_lower.iloc[-1]) > 0 else 0.5

            metadata['bb_position'] = bb_position
            metadata['bb_upper'] = bb_upper.iloc[-1]
            metadata['bb_lower'] = bb_lower.iloc[-1]

            # Calculate dual RSI
            rsi_fast, rsi_smooth = AdvancedIndicators.compute_dual_rsi(
                df,
                self.config.indicators.rsi_period,
                self.config.indicators.rsi_smooth_period
            )

            metadata['rsi_fast'] = rsi_fast
            metadata['rsi_smooth'] = rsi_smooth

            # Calculate Hurst exponent
            hurst = AdvancedIndicators.compute_hurst_exponent(
                close,
                self.config.indicators.hurst_window
            )

            metadata['hurst'] = hurst
            is_mean_reverting = hurst < self.config.strategies.hurst_mean_reversion_threshold
            metadata['is_mean_reverting'] = is_mean_reverting

            # Determine signal based on mean-reversion indicators
            threshold = self.config.strategies.mean_reversion_zscore_threshold

            if is_mean_reverting and z_score < -threshold:
                # Oversold - potential buy
                signal_type = SignalType.OVERSOLD

                # Confidence based on multiple confirmations
                confirmations = []

                # Z-score extreme
                z_conf = min(abs(z_score) / 3.0, 1.0)
                confirmations.append(z_conf)

                # Bollinger Band position
                if bb_position < self.config.strategies.mean_reversion_bb_threshold:
                    confirmations.append(0.8)
                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="Bollinger_Bands",
                        signal_type=SignalType.OVERSOLD,
                        strength=SignalStrength.MODERATE,
                        value=bb_position,
                        threshold=self.config.strategies.mean_reversion_bb_threshold,
                        description=f"Price at lower BB ({bb_position:.2f})"
                    ))

                # RSI oversold
                if rsi_fast < self.config.indicators.rsi_oversold:
                    confirmations.append(0.7)
                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="RSI",
                        signal_type=SignalType.OVERSOLD,
                        strength=SignalStrength.MODERATE,
                        value=rsi_fast,
                        threshold=self.config.indicators.rsi_oversold,
                        description=f"RSI oversold ({rsi_fast:.1f})"
                    ))

                # Z-score component
                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Z_Score",
                    signal_type=SignalType.OVERSOLD,
                    strength=self._determine_strength(z_conf),
                    value=z_score,
                    threshold=-threshold,
                    description=f"Z-score {z_score:.2f} (oversold)"
                ))

                confidence = np.mean(confirmations)

            elif is_mean_reverting and z_score > threshold:
                # Overbought - potential sell
                signal_type = SignalType.OVERBOUGHT

                confirmations = []

                # Z-score extreme
                z_conf = min(abs(z_score) / 3.0, 1.0)
                confirmations.append(z_conf)

                # Bollinger Band position
                if bb_position > (1.0 - self.config.strategies.mean_reversion_bb_threshold):
                    confirmations.append(0.8)
                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="Bollinger_Bands",
                        signal_type=SignalType.OVERBOUGHT,
                        strength=SignalStrength.MODERATE,
                        value=bb_position,
                        threshold=1.0 - self.config.strategies.mean_reversion_bb_threshold,
                        description=f"Price at upper BB ({bb_position:.2f})"
                    ))

                # RSI overbought
                if rsi_fast > self.config.indicators.rsi_overbought:
                    confirmations.append(0.7)
                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="RSI",
                        signal_type=SignalType.OVERBOUGHT,
                        strength=SignalStrength.MODERATE,
                        value=rsi_fast,
                        threshold=self.config.indicators.rsi_overbought,
                        description=f"RSI overbought ({rsi_fast:.1f})"
                    ))

                # Z-score component
                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Z_Score",
                    signal_type=SignalType.OVERBOUGHT,
                    strength=self._determine_strength(z_conf),
                    value=z_score,
                    threshold=threshold,
                    description=f"Z-score {z_score:.2f} (overbought)"
                ))

                confidence = np.mean(confirmations)

            else:
                # Neutral - no mean-reversion opportunity
                signal_type = SignalType.NEUTRAL
                confidence = 0.3

                if not is_mean_reverting:
                    metadata['neutral_reason'] = f"Hurst {hurst:.2f} indicates trending regime"
                else:
                    metadata['neutral_reason'] = f"Z-score {z_score:.2f} not extreme enough"

            strength = self._determine_strength(confidence)

            return self._create_signal(
                strategy_name="MeanReversion",
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                weight=self.config.strategies.mean_reversion_weight,
                components=components,
                metadata=metadata
            )

        except Exception as e:
            return self._create_signal(
                strategy_name="MeanReversion",
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                weight=self.config.strategies.mean_reversion_weight,
                components=[],
                metadata={"error": str(e)}
            )


if __name__ == "__main__":
    """Test mean reversion strategy"""
    print("="*80)
    print("MEAN REVERSION STRATEGY - TEST")
    print("="*80)

    from test_strategy_synthetic import create_uptrend_data

    # Initialize
    config = TechnicalAgentConfig()
    strategy = MeanReversionStrategy(config)

    print(f"\n📊 Strategy: {strategy.name}")
    print(f"   Weight: {config.strategies.mean_reversion_weight:.0%}")
    print(f"   Required days: {strategy.get_required_days()}")
    print(f"   Z-score threshold: ±{config.strategies.mean_reversion_zscore_threshold}")
    print(f"   Hurst threshold: <{config.strategies.hurst_mean_reversion_threshold}")

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
    print(f"   Z-score: {signal.metadata.get('z_score', 0):.2f}")
    print(f"   BB Position: {signal.metadata.get('bb_position', 0):.2f}")
    print(f"   RSI (fast): {signal.metadata.get('rsi_fast', 0):.1f}")
    print(f"   RSI (smooth): {signal.metadata.get('rsi_smooth', 0):.1f}")
    print(f"   Hurst: {signal.metadata.get('hurst', 0):.3f}")
    print(f"   Mean-reverting: {'Yes' if signal.metadata.get('is_mean_reverting') else 'No'}")

    if 'neutral_reason' in signal.metadata:
        print(f"   Reason: {signal.metadata['neutral_reason']}")

    if signal.component_signals:
        print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
        for comp in signal.component_signals:
            print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Mean reversion strategy test complete")
    print("="*80)
