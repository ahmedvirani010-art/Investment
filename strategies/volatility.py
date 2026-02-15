"""
Volatility Strategy

Uses volatility regime detection to identify market state and potential opportunities.

Logic:
- HIGH_VOL regime: Compressed volatility, potential breakout
- LOW_VOL regime: Expanded volatility, potential contraction
- ATR ratio determines regime
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


class VolatilityStrategy(BaseStrategy):
    """
    Volatility-based trading strategy using regime detection

    Trading logic:
    - LOW_VOL regime (compressed): Anticipate breakout, slight bullish bias
    - HIGH_VOL regime (expanded): Anticipate mean reversion, caution signal
    - NORMAL regime: Neutral, no strong signal
    """

    def get_required_days(self) -> int:
        """Require enough days for ATR + lookback"""
        return self.config.indicators.atr_period + self.config.indicators.atr_lookback + 20

    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze volatility regime and generate signal

        Returns:
            StrategySignal based on volatility state
        """
        components = []
        metadata = {}

        try:
            # Detect volatility regime
            regime, atr_ratio = AdvancedIndicators.compute_volatility_regime(
                df,
                self.config.indicators.atr_period,
                self.config.indicators.atr_lookback
            )

            metadata['regime'] = regime
            metadata['atr_ratio'] = atr_ratio

            # Get price info
            col_map = {col.lower(): col for col in df.columns}
            close = df[col_map.get('close', 'close')]
            current_price = close.iloc[-1]
            price_change = (current_price / close.iloc[-2] - 1) if len(close) >= 2 else 0.0

            metadata['price'] = current_price
            metadata['price_change'] = price_change

            # Signal logic based on regime
            if regime == "LOW_VOL":
                # Low volatility - potential for expansion/breakout
                # Slight bullish bias (volatility compression often precedes moves)
                signal_type = SignalType.BULLISH

                # Confidence based on how compressed volatility is
                compression = (1.0 - atr_ratio) / 0.3  # Normalize from 0.7 to 0
                confidence = min(compression, 0.6)  # Cap at 0.6 (moderate)

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Volatility_Regime",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.MODERATE,
                    value=atr_ratio,
                    threshold=self.config.strategies.volatility_low_regime_threshold,
                    description=f"Low volatility regime (ATR ratio: {atr_ratio:.2f}), potential breakout"
                ))

                metadata['signal_reason'] = "Volatility compression suggests potential breakout"

            elif regime == "HIGH_VOL":
                # High volatility - potential for contraction
                # Bearish bias (high vol often unsustainable, suggests risk)
                signal_type = SignalType.BEARISH

                # Confidence based on how extreme volatility is
                expansion = (atr_ratio - 1.5) / 0.5  # Normalize from 1.5 to 2.0
                confidence = min(expansion, 0.7)  # Cap at 0.7

                components.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Volatility_Regime",
                    signal_type=SignalType.BEARISH,
                    strength=SignalStrength.MODERATE,
                    value=atr_ratio,
                    threshold=self.config.strategies.volatility_high_regime_threshold,
                    description=f"High volatility regime (ATR ratio: {atr_ratio:.2f}), potential contraction"
                ))

                metadata['signal_reason'] = "Elevated volatility suggests risk/contraction ahead"

            else:
                # Normal volatility regime - neutral
                signal_type = SignalType.NEUTRAL
                confidence = 0.3

                metadata['signal_reason'] = f"Normal volatility regime (ATR ratio: {atr_ratio:.2f})"

            strength = self._determine_strength(confidence)

            return self._create_signal(
                strategy_name="Volatility",
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                weight=self.config.strategies.volatility_weight,
                components=components,
                metadata=metadata
            )

        except Exception as e:
            return self._create_signal(
                strategy_name="Volatility",
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                weight=self.config.strategies.volatility_weight,
                components=[],
                metadata={"error": str(e)}
            )


if __name__ == "__main__":
    """Test volatility strategy"""
    print("="*80)
    print("VOLATILITY STRATEGY - TEST")
    print("="*80)

    from test_strategy_synthetic import create_uptrend_data

    # Initialize
    config = TechnicalAgentConfig()
    strategy = VolatilityStrategy(config)

    print(f"\n📊 Strategy: {strategy.name}")
    print(f"   Weight: {config.strategies.volatility_weight:.0%}")
    print(f"   Required days: {strategy.get_required_days()}")
    print(f"   High vol threshold: >{config.strategies.volatility_high_regime_threshold}")
    print(f"   Low vol threshold: <{config.strategies.volatility_low_regime_threshold}")

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
    print(f"   Regime: {signal.metadata.get('regime', 'Unknown')}")
    print(f"   ATR Ratio: {signal.metadata.get('atr_ratio', 0):.2f}")
    print(f"   Price: {signal.metadata.get('price', 0):.2f}")
    print(f"   Reason: {signal.metadata.get('signal_reason', 'N/A')}")

    if signal.component_signals:
        print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
        for comp in signal.component_signals:
            print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Volatility strategy test complete")
    print("="*80)
