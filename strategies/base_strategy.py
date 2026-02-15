"""
Base Strategy Class

Abstract base class for all trading strategies in the ensemble.
Each strategy analyzes price data and generates strategy-level signals.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from psx_technical_agent import TechnicalSignal, SignalType, SignalStrength
from config.technical_config import TechnicalAgentConfig


@dataclass
class StrategySignal:
    """
    Strategy-level signal from a complete trading strategy

    A strategy combines multiple indicators to produce a unified signal.
    Component signals show the individual indicators that contributed.
    """
    strategy_name: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0.0-1.0
    weight: float      # Strategy weight in ensemble
    component_signals: List[TechnicalSignal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedSnapshot:
    """
    Enhanced technical snapshot with strategy-level breakdown

    Extends TechnicalSnapshot with additional fields for multi-strategy analysis.
    Maintains backward compatibility by inheriting all base fields.
    """
    symbol: str
    date: str
    signals: List[TechnicalSignal] = field(default_factory=list)
    overall_bias: SignalType = SignalType.NEUTRAL
    confidence: float = 0.0
    indicator_values: Dict[str, float] = field(default_factory=dict)

    # Enhanced fields
    strategy_signals: List[StrategySignal] = field(default_factory=list)
    strategy_weights: Dict[str, float] = field(default_factory=dict)
    ensemble_score: float = 0.0  # -1.0 (bearish) to +1.0 (bullish)
    regime: str = "NORMAL"  # Volatility regime: HIGH_VOL, NORMAL, LOW_VOL


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies

    Each strategy implements analyze() to generate strategy-level signals
    based on multiple technical indicators and market conditions.
    """

    def __init__(self, config: TechnicalAgentConfig):
        """
        Initialize strategy with configuration

        Args:
            config: TechnicalAgentConfig with indicator and strategy parameters
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, symbol: str, df: pd.DataFrame, date: str) -> StrategySignal:
        """
        Analyze price data and generate strategy signal

        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data (sufficient history required)
            date: Analysis date (YYYY-MM-DD)

        Returns:
            StrategySignal with signal type, strength, confidence, and components
        """
        pass

    @abstractmethod
    def get_required_days(self) -> int:
        """
        Minimum days of price data required for this strategy

        Returns:
            int: Minimum number of days needed
        """
        pass

    def _create_signal(self,
                      strategy_name: str,
                      signal_type: SignalType,
                      strength: SignalStrength,
                      confidence: float,
                      weight: float,
                      components: List[TechnicalSignal],
                      metadata: Dict[str, Any]) -> StrategySignal:
        """
        Helper to create standardized StrategySignal

        Args:
            strategy_name: Name of the strategy
            signal_type: Type of signal (BULLISH, BEARISH, etc.)
            strength: Signal strength (STRONG, MODERATE, WEAK)
            confidence: Confidence level (0.0-1.0)
            weight: Weight in ensemble
            components: List of component TechnicalSignals
            metadata: Strategy-specific metadata

        Returns:
            StrategySignal instance
        """
        return StrategySignal(
            strategy_name=strategy_name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            weight=weight,
            component_signals=components,
            metadata=metadata
        )

    def _determine_strength(self, confidence: float) -> SignalStrength:
        """
        Determine signal strength based on confidence level

        Args:
            confidence: Confidence value (0.0-1.0)

        Returns:
            SignalStrength enum
        """
        if confidence >= self.config.strategies.strong_signal_threshold:
            return SignalStrength.STRONG
        elif confidence >= self.config.strategies.moderate_signal_threshold:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


if __name__ == "__main__":
    """
    Test base strategy infrastructure
    """
    print("="*80)
    print("BASE STRATEGY - TEST")
    print("="*80)

    # Create test config
    config = TechnicalAgentConfig()

    print("\n📋 Configuration loaded:")
    print(f"   Strong threshold: {config.strategies.strong_signal_threshold}")
    print(f"   Moderate threshold: {config.strategies.moderate_signal_threshold}")

    # Test signal creation
    test_signal = TechnicalSignal(
        symbol="TEST",
        date="2026-02-15",
        indicator="RSI",
        signal_type=SignalType.OVERSOLD,
        strength=SignalStrength.MODERATE,
        value=28.5,
        threshold=30.0,
        description="RSI oversold"
    )

    print("\n✅ TechnicalSignal created:")
    print(f"   {test_signal.indicator}: {test_signal.signal_type.value}")
    print(f"   Strength: {test_signal.strength.value}")
    print(f"   Value: {test_signal.value:.2f}")

    # Test strategy signal
    test_strategy_signal = StrategySignal(
        strategy_name="TestStrategy",
        signal_type=SignalType.BULLISH,
        strength=SignalStrength.STRONG,
        confidence=0.85,
        weight=0.25,
        component_signals=[test_signal],
        metadata={"test_key": "test_value"}
    )

    print("\n✅ StrategySignal created:")
    print(f"   Strategy: {test_strategy_signal.strategy_name}")
    print(f"   Signal: {test_strategy_signal.signal_type.value}")
    print(f"   Confidence: {test_strategy_signal.confidence:.0%}")
    print(f"   Weight: {test_strategy_signal.weight:.0%}")
    print(f"   Components: {len(test_strategy_signal.component_signals)}")

    # Test EnhancedSnapshot
    test_snapshot = EnhancedSnapshot(
        symbol="TEST",
        date="2026-02-15",
        signals=[test_signal],
        overall_bias=SignalType.BULLISH,
        confidence=0.75,
        indicator_values={"RSI": 28.5},
        strategy_signals=[test_strategy_signal],
        strategy_weights={"TestStrategy": 0.25},
        ensemble_score=0.65,
        regime="NORMAL"
    )

    print("\n✅ EnhancedSnapshot created:")
    print(f"   Symbol: {test_snapshot.symbol}")
    print(f"   Overall Bias: {test_snapshot.overall_bias.value}")
    print(f"   Confidence: {test_snapshot.confidence:.0%}")
    print(f"   Ensemble Score: {test_snapshot.ensemble_score:+.2f}")
    print(f"   Regime: {test_snapshot.regime}")
    print(f"   Strategy Signals: {len(test_snapshot.strategy_signals)}")

    print("\n" + "="*80)
    print("✅ Base strategy infrastructure ready")
    print("="*80)
