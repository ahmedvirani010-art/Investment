"""
Direct Demonstration: Group-Based Conflict Resolution

Shows exactly how the SignalAggregator resolves conflicts between
Trend Following and Mean Reversion strategies.

Creates strategy signals manually to demonstrate the three key scenarios.
"""

from strategies.base_strategy import StrategySignal
from strategies.signal_aggregator import SignalAggregator
from psx_technical_agent import SignalType, SignalStrength, TechnicalSignal
from config.technical_config import TechnicalAgentConfig


def create_conflict_scenario():
    """
    Scenario 1: CONFLICT - Strong Uptrend + Overbought

    Trend Following: BULLISH (high conviction)
    Momentum: BULLISH
    Mean Reversion: OVERBOUGHT (high conviction)
    Stat Arb: BULLISH
    Volatility: NORMAL regime
    """
    print("\n" + "="*80)
    print("SCENARIO 1: CONFLICT - Strong Uptrend + Overbought")
    print("="*80)
    print("Market: Price up 15% in 5 days, clear uptrend but extreme RSI\n")

    config = TechnicalAgentConfig()

    signals = [
        # Trend group
        StrategySignal(
            strategy_name="TrendFollowingStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.STRONG,
            confidence=0.90,
            weight=config.strategies.trend_following_weight,
            component_signals=[
                TechnicalSignal('TEST', '2026-02-16', 'EMA_Alignment', SignalType.BULLISH,
                               SignalStrength.STRONG, 0.85, description="EMA(8)>EMA(21)>EMA(55)"),
                TechnicalSignal('TEST', '2026-02-16', 'ADX', SignalType.BULLISH,
                               SignalStrength.STRONG, 38.0, 25.0, "ADX=38.0 (strong trend)")
            ],
            metadata={'ema8': 155, 'ema21': 153, 'ema55': 150, 'adx': 38.0}
        ),
        StrategySignal(
            strategy_name="MomentumStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=0.75,
            weight=config.strategies.momentum_weight,
            component_signals=[],
            metadata={'ret_1m': 0.08, 'ret_3m': 0.15, 'momentum_score': 0.10}
        ),

        # Reversion group
        StrategySignal(
            strategy_name="MeanReversionStrategy",
            signal_type=SignalType.OVERBOUGHT,
            strength=SignalStrength.STRONG,
            confidence=0.88,
            weight=config.strategies.mean_reversion_weight,
            component_signals=[
                TechnicalSignal('TEST', '2026-02-16', 'Z_Score', SignalType.OVERBOUGHT,
                               SignalStrength.STRONG, 2.8, 2.0, "Z-score +2.8 (extreme)"),
                TechnicalSignal('TEST', '2026-02-16', 'RSI', SignalType.OVERBOUGHT,
                               SignalStrength.STRONG, 78.0, 70.0, "RSI=78 (overbought)")
            ],
            metadata={'z_score': 2.8, 'rsi_fast': 78.0, 'hurst': 0.45}
        ),
        StrategySignal(
            strategy_name="StatisticalArbitrageStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=0.70,
            weight=config.strategies.statistical_arb_weight,
            component_signals=[],
            metadata={'hurst': 0.48, 'skewness': 0.8}
        ),

        # Regime
        StrategySignal(
            strategy_name="VolatilityStrategy",
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.MODERATE,
            confidence=0.50,
            weight=config.strategies.volatility_weight,
            component_signals=[],
            metadata={'regime': 'NORMAL', 'atr_ratio': 1.0}
        )
    ]

    return signals


def create_agreement_scenario():
    """
    Scenario 2: AGREEMENT - Oversold + Emerging Uptrend

    Both groups agree: BULLISH
    """
    print("\n" + "="*80)
    print("SCENARIO 2: AGREEMENT - Oversold + Emerging Uptrend")
    print("="*80)
    print("Market: Oversold RSI + emerging uptrend formation\n")

    config = TechnicalAgentConfig()

    signals = [
        # Trend group
        StrategySignal(
            strategy_name="TrendFollowingStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=0.70,
            weight=config.strategies.trend_following_weight,
            component_signals=[],
            metadata={'adx': 28.0}
        ),
        StrategySignal(
            strategy_name="MomentumStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=0.65,
            weight=config.strategies.momentum_weight,
            component_signals=[],
            metadata={'momentum_score': 0.07}
        ),

        # Reversion group (also bullish via OVERSOLD)
        StrategySignal(
            strategy_name="MeanReversionStrategy",
            signal_type=SignalType.OVERSOLD,  # OVERSOLD → bullish bias
            strength=SignalStrength.STRONG,
            confidence=0.82,
            weight=config.strategies.mean_reversion_weight,
            component_signals=[],
            metadata={'z_score': -2.3, 'rsi_fast': 28.0}
        ),
        StrategySignal(
            strategy_name="StatisticalArbitrageStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=0.75,
            weight=config.strategies.statistical_arb_weight,
            component_signals=[],
            metadata={'hurst': 0.42, 'skewness': 1.2}
        ),

        # Regime
        StrategySignal(
            strategy_name="VolatilityStrategy",
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.MODERATE,
            confidence=0.50,
            weight=config.strategies.volatility_weight,
            component_signals=[],
            metadata={'regime': 'LOW_VOL', 'atr_ratio': 0.65}
        )
    ]

    return signals


def create_high_vol_scenario():
    """
    Scenario 3: HIGH VOLATILITY - Regime Favors Trend

    Conflict, but HIGH_VOL regime favors trend group
    """
    print("\n" + "="*80)
    print("SCENARIO 3: HIGH VOLATILITY - Regime Favors Trend Following")
    print("="*80)
    print("Market: Strong uptrend + high volatility + overbought\n")

    config = TechnicalAgentConfig()

    signals = [
        # Trend group (very bullish)
        StrategySignal(
            strategy_name="TrendFollowingStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.STRONG,
            confidence=0.95,
            weight=config.strategies.trend_following_weight,
            component_signals=[],
            metadata={'adx': 42.0}
        ),
        StrategySignal(
            strategy_name="MomentumStrategy",
            signal_type=SignalType.BULLISH,
            strength=SignalStrength.STRONG,
            confidence=0.88,
            weight=config.strategies.momentum_weight,
            component_signals=[],
            metadata={'momentum_score': 0.12}
        ),

        # Reversion group (bearish due to overbought)
        StrategySignal(
            strategy_name="MeanReversionStrategy",
            signal_type=SignalType.OVERBOUGHT,
            strength=SignalStrength.MODERATE,
            confidence=0.70,
            weight=config.strategies.mean_reversion_weight,
            component_signals=[],
            metadata={'z_score': 2.2, 'rsi_fast': 75.0}
        ),
        StrategySignal(
            strategy_name="StatisticalArbitrageStrategy",
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=0.50,
            weight=config.strategies.statistical_arb_weight,
            component_signals=[],
            metadata={'hurst': 0.55}
        ),

        # Regime (HIGH_VOL)
        StrategySignal(
            strategy_name="VolatilityStrategy",
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.MODERATE,
            confidence=0.50,
            weight=config.strategies.volatility_weight,
            component_signals=[],
            metadata={'regime': 'HIGH_VOL', 'atr_ratio': 1.8}
        )
    ]

    return signals


def analyze_scenario(signals, scenario_num):
    """Analyze and display results"""

    config = TechnicalAgentConfig()
    aggregator = SignalAggregator(config)

    # Aggregate
    ensemble = aggregator.aggregate(signals, 'TEST', '2026-02-16')

    print("📊 INDIVIDUAL STRATEGY SIGNALS:")
    for s in signals:
        print(f"  {s.strategy_name:25s}: {s.signal_type.value:12s} "
              f"(conf: {s.confidence:.0%}, weight: {s.weight:.0%})")

    print(f"\n📊 GROUP CONSENSUS:")
    for group_name, consensus in ensemble.group_consensus.items():
        if group_name != 'regime':
            print(f"  {group_name.upper():10s}: "
                  f"bias={consensus.get('bias', 'N/A'):12s}, "
                  f"score={consensus.get('score', 0):+.2f}, "
                  f"conf={consensus.get('confidence', 0):.0%}, "
                  f"agree={consensus.get('agreement', 0):.0%}")
        else:
            print(f"  REGIME:     {consensus.get('regime', 'NORMAL')} "
                  f"(ATR ratio: {consensus.get('atr_ratio', 1.0):.2f})")

    print(f"\n🎯 ENSEMBLE RESULT:")
    print(f"  Overall Bias:     {ensemble.bias.value}")
    print(f"  Strength:         {ensemble.bias_strength.value}")
    print(f"  Confidence:       {ensemble.bias_confidence:.0%}")
    print(f"  Ensemble Score:   {ensemble.confidence_weighted_score:+.3f}")
    print(f"  Agreement:        {ensemble.signal_agreement:.0%}")

    if ensemble.metadata.get('conflict_detected'):
        print(f"\n⚠️  CONFLICT DETECTED")
        print(f"  Group Weights: Trend={ensemble.metadata['group_weights']['trend']:.0%}, "
              f"Reversion={ensemble.metadata['group_weights']['reversion']:.0%}")

    print(f"\n💡 INTERPRETATION:")

    trend_consensus = ensemble.group_consensus['trend']
    reversion_consensus = ensemble.group_consensus['reversion']
    regime = ensemble.group_consensus['regime']['regime']

    if ensemble.metadata.get('conflict_detected'):
        print(f"  → Trend group says: {trend_consensus['bias']:12s} (score: {trend_consensus['score']:+.2f})")
        print(f"  → Reversion says:   {reversion_consensus['bias']:12s} (score: {reversion_consensus['score']:+.2f})")

        if regime == 'HIGH_VOL':
            print(f"  → Regime: {regime} favors TREND (65% weight)")
            print(f"  → Result: Trend group dominates despite conflict")
        elif regime == 'LOW_VOL':
            print(f"  → Regime: {regime} favors REVERSION (65% weight)")
            print(f"  → Result: Reversion group dominates despite conflict")
        else:
            print(f"  → Regime: {regime} (equal 50/50 weighting)")
            if ensemble.bias.value == 'Neutral':
                print(f"  → Result: Conflict unresolved, stay NEUTRAL")
            else:
                print(f"  → Result: Slight edge to {ensemble.bias.value}")
    else:
        if trend_consensus['bias'] == reversion_consensus['bias']:
            print(f"  → Both groups agree: {ensemble.bias.value}")
            print(f"  → Confidence BOOSTED by {config.strategies.agreement_bonus}x")
            print(f"  → Strong conviction signal")
        else:
            print(f"  → Mixed or weak signals")
            print(f"  → Moderate {ensemble.bias.value} bias")

    print("\n" + "-"*80)


if __name__ == "__main__":
    print("="*80)
    print("GROUP-BASED CONFLICT RESOLUTION - DIRECT DEMONSTRATION")
    print("="*80)
    print("\nShowing exactly how the aggregator resolves conflicts between")
    print("Trend Following and Mean Reversion strategies.\n")

    # Scenario 1: Conflict with normal volatility
    signals1 = create_conflict_scenario()
    analyze_scenario(signals1, 1)

    # Scenario 2: Agreement
    signals2 = create_agreement_scenario()
    analyze_scenario(signals2, 2)

    # Scenario 3: Conflict with high volatility
    signals3 = create_high_vol_scenario()
    analyze_scenario(signals3, 3)

    print("\n" + "="*80)
    print("✅ Demonstration Complete")
    print("="*80)
    print("\nKey Insights:")
    print("  1. Conflicts are detected when trend and reversion disagree")
    print("  2. Market regime determines which group gets more weight")
    print("  3. Confidence is damped during conflicts (0.7x)")
    print("  4. Confidence is boosted when groups agree (1.2x)")
    print("  5. System respects trading philosophy differences")
