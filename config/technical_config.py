"""
Technical Analysis Agent Configuration

Externalized configuration for all technical indicators, strategies, and thresholds.
Allows for easy parameter tuning and A/B testing without code changes.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import yaml
import json
from pathlib import Path


@dataclass
class IndicatorConfig:
    """Configuration for individual technical indicators"""

    # RSI (Relative Strength Index)
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_smooth_period: int = 3  # For dual RSI

    # MACD (Moving Average Convergence Divergence)
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # SMA (Simple Moving Average)
    sma_short: int = 20
    sma_medium: int = 50
    sma_long: int = 200

    # EMA (Exponential Moving Average) - Multi-timeframe
    ema_fast: int = 8
    ema_medium: int = 21
    ema_long: int = 55

    # ADX (Average Directional Index)
    adx_period: int = 14
    adx_threshold: float = 25.0  # Minimum for strong trend

    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0

    # Stochastic Oscillator
    stochastic_k_period: int = 14
    stochastic_d_period: int = 3
    stochastic_overbought: float = 80.0
    stochastic_oversold: float = 20.0

    # ATR (Average True Range)
    atr_period: int = 14
    atr_lookback: int = 20  # For regime detection

    # Volume indicators
    volume_period: int = 20

    # Statistical indicators
    hurst_window: int = 100
    zscore_window: int = 20
    skew_window: int = 63
    kurt_window: int = 63


@dataclass
class StrategyConfig:
    """Configuration for trading strategies and ensemble weights"""

    # Ensemble weights (should sum to 1.0)
    trend_following_weight: float = 0.25
    mean_reversion_weight: float = 0.20
    momentum_weight: float = 0.20
    volatility_weight: float = 0.15
    statistical_arb_weight: float = 0.20

    # Trend Following thresholds
    trend_min_adx: float = 25.0
    trend_ema_alignment_threshold: float = 0.5  # Minimum for strong trend

    # Mean Reversion thresholds
    mean_reversion_zscore_threshold: float = 2.0
    mean_reversion_bb_threshold: float = 0.2  # Distance from bands
    hurst_mean_reversion_threshold: float = 0.5  # H < 0.5 = mean reverting

    # Momentum thresholds
    momentum_min_return: float = 0.05  # 5% minimum for signal
    momentum_min_volume_ratio: float = 1.5  # Volume confirmation
    momentum_1m_weight: float = 0.4
    momentum_3m_weight: float = 0.3
    momentum_6m_weight: float = 0.3

    # Volatility thresholds
    volatility_high_regime_threshold: float = 1.5  # ATR ratio
    volatility_low_regime_threshold: float = 0.7   # ATR ratio

    # Statistical Arbitrage thresholds
    stat_arb_hurst_threshold: float = 0.4
    stat_arb_skew_threshold: float = 1.0

    # Signal strength thresholds
    strong_signal_threshold: float = 0.75
    moderate_signal_threshold: float = 0.50

    # Ensemble aggregation
    ensemble_bullish_threshold: float = 0.3   # Score > 0.3 = bullish
    ensemble_bearish_threshold: float = -0.3  # Score < -0.3 = bearish


@dataclass
class TechnicalAgentConfig:
    """
    Master configuration for PSX Technical Analysis Agent

    Attributes:
        indicators: Indicator-specific parameters
        strategies: Strategy weights and thresholds
        use_strategy_ensemble: Enable multi-strategy ensemble mode
        min_data_days: Minimum days of data required for analysis
        enable_backtesting: Enable backtesting framework
        backtest_window_days: Lookback window for backtesting
        backtest_forward_days: Hold period for return calculation
    """

    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    strategies: StrategyConfig = field(default_factory=StrategyConfig)

    # Analysis settings
    use_strategy_ensemble: bool = True
    min_data_days: int = 250  # Required for SMA(200) + buffer

    # Validation settings
    enable_backtesting: bool = False
    backtest_window_days: int = 60
    backtest_forward_days: int = 5  # Hold period

    @classmethod
    def load_from_yaml(cls, path: str) -> 'TechnicalAgentConfig':
        """
        Load configuration from YAML file

        Args:
            path: Path to YAML configuration file

        Returns:
            TechnicalAgentConfig instance

        Example YAML:
            indicators:
              rsi_period: 14
              adx_threshold: 30.0
            strategies:
              trend_following_weight: 0.30
              mean_reversion_weight: 0.20
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        if data is None:
            return cls()

        # Parse nested structures
        indicators_data = data.get('indicators', {})
        strategies_data = data.get('strategies', {})

        indicators = IndicatorConfig(**indicators_data)
        strategies = StrategyConfig(**strategies_data)

        # Parse top-level settings
        return cls(
            indicators=indicators,
            strategies=strategies,
            use_strategy_ensemble=data.get('use_strategy_ensemble', True),
            min_data_days=data.get('min_data_days', 250),
            enable_backtesting=data.get('enable_backtesting', False),
            backtest_window_days=data.get('backtest_window_days', 60),
            backtest_forward_days=data.get('backtest_forward_days', 5)
        )

    @classmethod
    def load_from_json(cls, path: str) -> 'TechnicalAgentConfig':
        """
        Load configuration from JSON file

        Args:
            path: Path to JSON configuration file

        Returns:
            TechnicalAgentConfig instance
        """
        with open(path, 'r') as f:
            data = json.load(f)

        if data is None:
            return cls()

        indicators_data = data.get('indicators', {})
        strategies_data = data.get('strategies', {})

        indicators = IndicatorConfig(**indicators_data)
        strategies = StrategyConfig(**strategies_data)

        return cls(
            indicators=indicators,
            strategies=strategies,
            use_strategy_ensemble=data.get('use_strategy_ensemble', True),
            min_data_days=data.get('min_data_days', 250),
            enable_backtesting=data.get('enable_backtesting', False),
            backtest_window_days=data.get('backtest_window_days', 60),
            backtest_forward_days=data.get('backtest_forward_days', 5)
        )

    def save_to_yaml(self, path: str):
        """
        Save configuration to YAML file

        Args:
            path: Path to save YAML file
        """
        data = {
            'indicators': asdict(self.indicators),
            'strategies': asdict(self.strategies),
            'use_strategy_ensemble': self.use_strategy_ensemble,
            'min_data_days': self.min_data_days,
            'enable_backtesting': self.enable_backtesting,
            'backtest_window_days': self.backtest_window_days,
            'backtest_forward_days': self.backtest_forward_days
        }

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_to_json(self, path: str):
        """
        Save configuration to JSON file

        Args:
            path: Path to save JSON file
        """
        data = {
            'indicators': asdict(self.indicators),
            'strategies': asdict(self.strategies),
            'use_strategy_ensemble': self.use_strategy_ensemble,
            'min_data_days': self.min_data_days,
            'enable_backtesting': self.enable_backtesting,
            'backtest_window_days': self.backtest_window_days,
            'backtest_forward_days': self.backtest_forward_days
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def validate(self) -> bool:
        """
        Validate configuration parameters

        Returns:
            True if valid, raises ValueError otherwise
        """
        # Validate ensemble weights sum to ~1.0
        total_weight = (
            self.strategies.trend_following_weight +
            self.strategies.mean_reversion_weight +
            self.strategies.momentum_weight +
            self.strategies.volatility_weight +
            self.strategies.statistical_arb_weight
        )

        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Strategy weights must sum to 1.0, got {total_weight}")

        # Validate thresholds are reasonable
        if not (0 < self.indicators.rsi_overbought <= 100):
            raise ValueError(f"RSI overbought must be 0-100, got {self.indicators.rsi_overbought}")

        if not (0 <= self.indicators.rsi_oversold < 100):
            raise ValueError(f"RSI oversold must be 0-100, got {self.indicators.rsi_oversold}")

        if self.indicators.rsi_oversold >= self.indicators.rsi_overbought:
            raise ValueError("RSI oversold must be less than overbought")

        if self.min_data_days < 200:
            raise ValueError(f"min_data_days must be >= 200 for SMA(200), got {self.min_data_days}")

        return True


# Pre-defined configurations for different trading styles
CONSERVATIVE_CONFIG = TechnicalAgentConfig(
    strategies=StrategyConfig(
        trend_following_weight=0.35,  # Emphasize trend following
        mean_reversion_weight=0.10,   # De-emphasize mean reversion
        momentum_weight=0.25,
        volatility_weight=0.20,
        statistical_arb_weight=0.10,
        trend_min_adx=30.0,           # Higher ADX threshold
        ensemble_bullish_threshold=0.4,  # Require stronger signals
        ensemble_bearish_threshold=-0.4
    )
)

AGGRESSIVE_CONFIG = TechnicalAgentConfig(
    strategies=StrategyConfig(
        trend_following_weight=0.15,
        mean_reversion_weight=0.30,   # Emphasize mean reversion
        momentum_weight=0.25,
        volatility_weight=0.15,
        statistical_arb_weight=0.15,
        trend_min_adx=20.0,           # Lower ADX threshold
        mean_reversion_zscore_threshold=1.5,  # More sensitive
        ensemble_bullish_threshold=0.2,  # Lower thresholds
        ensemble_bearish_threshold=-0.2
    )
)

BALANCED_CONFIG = TechnicalAgentConfig()  # Uses defaults


if __name__ == "__main__":
    """
    Test configuration creation and serialization
    """
    print("="*80)
    print("TECHNICAL AGENT CONFIGURATION - TEST")
    print("="*80)

    # Create default config
    config = TechnicalAgentConfig()

    # Validate
    try:
        config.validate()
        print("\n✅ Default configuration is valid")
    except ValueError as e:
        print(f"\n❌ Validation failed: {e}")

    # Display key parameters
    print("\n📊 Indicator Parameters:")
    print(f"   RSI: period={config.indicators.rsi_period}, "
          f"overbought={config.indicators.rsi_overbought}, "
          f"oversold={config.indicators.rsi_oversold}")
    print(f"   MACD: fast={config.indicators.macd_fast}, "
          f"slow={config.indicators.macd_slow}, "
          f"signal={config.indicators.macd_signal}")
    print(f"   EMA: {config.indicators.ema_fast}/"
          f"{config.indicators.ema_medium}/"
          f"{config.indicators.ema_long}")
    print(f"   ADX: period={config.indicators.adx_period}, "
          f"threshold={config.indicators.adx_threshold}")

    print("\n⚖️  Strategy Weights:")
    print(f"   Trend Following: {config.strategies.trend_following_weight:.0%}")
    print(f"   Mean Reversion:  {config.strategies.mean_reversion_weight:.0%}")
    print(f"   Momentum:        {config.strategies.momentum_weight:.0%}")
    print(f"   Volatility:      {config.strategies.volatility_weight:.0%}")
    print(f"   Statistical Arb: {config.strategies.statistical_arb_weight:.0%}")
    total = (config.strategies.trend_following_weight +
             config.strategies.mean_reversion_weight +
             config.strategies.momentum_weight +
             config.strategies.volatility_weight +
             config.strategies.statistical_arb_weight)
    print(f"   Total:           {total:.0%}")

    # Save to YAML
    output_dir = Path(__file__).parent
    yaml_path = output_dir / "default_config.yaml"
    config.save_to_yaml(str(yaml_path))
    print(f"\n💾 Saved default config to: {yaml_path}")

    # Test loading
    loaded_config = TechnicalAgentConfig.load_from_yaml(str(yaml_path))
    print(f"✅ Successfully loaded config from YAML")

    # Save pre-defined configs
    conservative_path = output_dir / "conservative_config.yaml"
    CONSERVATIVE_CONFIG.save_to_yaml(str(conservative_path))
    print(f"💾 Saved conservative config to: {conservative_path}")

    aggressive_path = output_dir / "aggressive_config.yaml"
    AGGRESSIVE_CONFIG.save_to_yaml(str(aggressive_path))
    print(f"💾 Saved aggressive config to: {aggressive_path}")

    print("\n" + "="*80)
    print("✅ Configuration system ready")
    print("="*80)
