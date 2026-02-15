"""
Trend Following Strategy

Uses EMA(8/21/55) alignment and ADX strength filter to identify strong trends.

Logic:
- EMA alignment: EMA8 > EMA21 > EMA55 = perfect bullish
- ADX >= threshold: Trend has strength
- Combined score determines signal and confidence
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


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend following using EMA(8/21/55) alignment + ADX strength filter

    Strong trends occur when:
    1. EMAs are aligned (8 > 21 > 55 for bullish, reverse for bearish)
    2. ADX indicates trend strength (default >= 25)
    3. Price confirms the trend direction
    """

    def get_required_days(self) -> int:
        """Require enough days for longest EMA + ADX"""
        return max(
            self.config.indicators.ema_long,
            self.config.indicators.adx_period
        ) + 20  # Buffer

    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze trend using EMA alignment and ADX strength

        Returns:
            StrategySignal with trend direction and confidence
        """
        components = []
        metadata = {}

        try:
            # Compute EMAs
            ema8 = df['close'].ewm(span=self.config.indicators.ema_fast, adjust=False).mean()
            ema21 = df['close'].ewm(span=self.config.indicators.ema_medium, adjust=False).mean()
            ema55 = df['close'].ewm(span=self.config.indicators.ema_long, adjust=False).mean()

            current_price = df['close'].iloc[-1]
            ema8_val = ema8.iloc[-1]
            ema21_val = ema21.iloc[-1]
            ema55_val = ema55.iloc[-1]

            metadata['ema8'] = ema8_val
            metadata['ema21'] = ema21_val
            metadata['ema55'] = ema55_val
            metadata['price'] = current_price

            # Compute ADX
            adx, di_plus, di_minus = AdvancedIndicators.compute_adx(
                df, self.config.indicators.adx_period
            )
            metadata['adx'] = adx
            metadata['di_plus'] = di_plus
            metadata['di_minus'] = di_minus

            # Calculate EMA alignment score (-1 to +1)
            if ema8_val > ema21_val > ema55_val:
                ema_alignment = 1.0  # Perfect bullish alignment
            elif ema8_val < ema21_val < ema55_val:
                ema_alignment = -1.0  # Perfect bearish alignment
            else:
                # Partial alignment - count bullish conditions
                bullish_count = sum([
                    ema8_val > ema21_val,
                    ema21_val > ema55_val,
                    current_price > ema21_val
                ])
                # Map 0,1,2,3 to -1,-0.33,+0.33,+1
                ema_alignment = (bullish_count / 3.0) * 2 - 1

            metadata['ema_alignment'] = ema_alignment

            # Check trend strength via ADX
            has_trend_strength = adx >= self.config.strategies.trend_min_adx
            metadata['has_trend_strength'] = has_trend_strength

            # Determine signal based on alignment and strength
            if has_trend_strength:
                if ema_alignment >= self.config.strategies.trend_ema_alignment_threshold:
                    # Strong bullish trend
                    signal_type = SignalType.BULLISH
                    # Confidence based on alignment strength and ADX
                    confidence = min(
                        abs(ema_alignment),
                        adx / 50.0  # Normalize ADX to 0-1 (50+ is very strong)
                    )

                    # Add component signal
                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="EMA_Alignment",
                        signal_type=SignalType.BULLISH,
                        strength=self._determine_strength(confidence),
                        value=ema_alignment,
                        threshold=self.config.strategies.trend_ema_alignment_threshold,
                        description=f"EMA bullish alignment: {ema_alignment:.2f}"
                    ))

                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="ADX",
                        signal_type=SignalType.BULLISH,
                        strength=SignalStrength.MODERATE,
                        value=adx,
                        threshold=self.config.strategies.trend_min_adx,
                        description=f"ADX {adx:.1f} indicates strong trend"
                    ))

                elif ema_alignment <= -self.config.strategies.trend_ema_alignment_threshold:
                    # Strong bearish trend
                    signal_type = SignalType.BEARISH
                    confidence = min(
                        abs(ema_alignment),
                        adx / 50.0
                    )

                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="EMA_Alignment",
                        signal_type=SignalType.BEARISH,
                        strength=self._determine_strength(confidence),
                        value=ema_alignment,
                        threshold=-self.config.strategies.trend_ema_alignment_threshold,
                        description=f"EMA bearish alignment: {ema_alignment:.2f}"
                    ))

                    components.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="ADX",
                        signal_type=SignalType.BEARISH,
                        strength=SignalStrength.MODERATE,
                        value=adx,
                        threshold=self.config.strategies.trend_min_adx,
                        description=f"ADX {adx:.1f} indicates strong trend"
                    ))

                else:
                    # Trend strength but no clear direction
                    signal_type = SignalType.NEUTRAL
                    confidence = 0.3
            else:
                # No trend strength (ADX too low)
                signal_type = SignalType.NEUTRAL
                confidence = 0.2
                metadata['no_trend_reason'] = f"ADX {adx:.1f} below threshold {self.config.strategies.trend_min_adx}"

            # Determine strength based on confidence
            strength = self._determine_strength(confidence)

            return self._create_signal(
                strategy_name="TrendFollowing",
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                weight=self.config.strategies.trend_following_weight,
                components=components,
                metadata=metadata
            )

        except Exception as e:
            # Fallback to neutral on error
            return self._create_signal(
                strategy_name="TrendFollowing",
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                weight=self.config.strategies.trend_following_weight,
                components=[],
                metadata={"error": str(e)}
            )


if __name__ == "__main__":
    """Test trend following strategy"""
    print("="*80)
    print("TREND FOLLOWING STRATEGY - TEST")
    print("="*80)

    from psx_price_store import PSXPriceStore

    # Initialize
    price_store = PSXPriceStore()
    config = TechnicalAgentConfig()
    strategy = TrendFollowingStrategy(config)

    print(f"\n📊 Strategy: {strategy.name}")
    print(f"   Weight: {config.strategies.trend_following_weight:.0%}")
    print(f"   Required days: {strategy.get_required_days()}")
    print(f"   ADX threshold: {config.strategies.trend_min_adx}")
    print(f"   EMA periods: {config.indicators.ema_fast}/{config.indicators.ema_medium}/{config.indicators.ema_long}")

    # Test with real PSX data
    test_symbols = ['HBL', 'LUCK', 'PSO']

    for symbol in test_symbols:
        print(f"\n{'='*80}")
        print(f"📈 Analyzing {symbol}")
        print(f"{'='*80}")

        # Fetch data
        df = price_store.get_prices(symbol, days=250)

        if df.empty or len(df) < strategy.get_required_days():
            print(f"   ⚠️  Insufficient data")
            continue

        # Analyze
        date = df.index[-1].strftime('%Y-%m-%d')
        signal = strategy.analyze(symbol, df, date)

        # Display results
        print(f"\n🔔 Signal: {signal.signal_type.value}")
        print(f"   Strength: {signal.strength.value}")
        print(f"   Confidence: {signal.confidence:.0%}")

        print(f"\n📊 Indicators:")
        print(f"   EMA(8):  {signal.metadata.get('ema8', 0):.2f}")
        print(f"   EMA(21): {signal.metadata.get('ema21', 0):.2f}")
        print(f"   EMA(55): {signal.metadata.get('ema55', 0):.2f}")
        print(f"   Price:   {signal.metadata.get('price', 0):.2f}")
        print(f"   ADX:     {signal.metadata.get('adx', 0):.2f}")
        print(f"   Alignment: {signal.metadata.get('ema_alignment', 0):+.2f}")
        print(f"   Trend Strength: {'Yes' if signal.metadata.get('has_trend_strength') else 'No'}")

        if signal.component_signals:
            print(f"\n🔍 Component Signals ({len(signal.component_signals)}):")
            for comp in signal.component_signals:
                print(f"   • {comp.indicator}: {comp.description}")

    print("\n" + "="*80)
    print("✅ Trend following strategy test complete")
    print("="*80)
