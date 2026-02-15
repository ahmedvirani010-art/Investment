"""
Advanced Technical Indicators

Implements sophisticated indicators not in the base PSX technical agent:
- ADX (Average Directional Index): Trend strength measurement
- Hurst Exponent: Mean-reversion vs trending detection
- Dual RSI: Fast RSI vs smoothed RSI crossovers
- Volatility Regime Detection: High/low volatility identification
- Volume Momentum: Volume confirmation signals
- Multi-Period Returns: Momentum across timeframes
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import math


class AdvancedIndicators:
    """
    Collection of advanced technical indicators for multi-strategy analysis
    """

    @staticmethod
    def compute_adx(df: pd.DataFrame, period: int = 14) -> Tuple[float, float, float]:
        """
        Compute ADX (Average Directional Index) and directional indicators

        ADX measures trend strength on a scale of 0-100:
        - ADX < 20: Weak or no trend
        - ADX 20-25: Developing trend
        - ADX 25-50: Strong trend
        - ADX > 50: Very strong trend

        Args:
            df: DataFrame with 'high', 'low', 'close' columns (case-insensitive)
            period: ADX smoothing period (default 14)

        Returns:
            Tuple of (adx, di_plus, di_minus)
            - adx: Average Directional Index (0-100)
            - di_plus: Positive Directional Indicator
            - di_minus: Negative Directional Indicator
        """
        # Handle both uppercase and lowercase column names
        df_copy = df.copy()

        # Map column names (case-insensitive)
        col_map = {col.lower(): col for col in df_copy.columns}

        high = df_copy[col_map.get('high', 'high')]
        low = df_copy[col_map.get('low', 'low')]
        close = df_copy[col_map.get('close', 'close')]

        # Calculate True Range components
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())

        # True Range is the maximum of the three
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # Calculate Directional Movement
        up_move = high.diff()
        down_move = -low.diff()

        # Positive and Negative Directional Movement
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=df_copy.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=df_copy.index)

        # Smooth the True Range and Directional Movements using EMA
        # Add small epsilon to avoid division by zero
        atr = tr.ewm(span=period, adjust=False).mean() + 1e-10
        plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()

        # Calculate Directional Indicators
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)

        # Calculate DX (Directional Index)
        # Avoid division by zero
        di_sum = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / di_sum.replace(0, np.nan)

        # Calculate ADX (smoothed DX)
        adx = dx.ewm(span=period, adjust=False).mean()

        # Return latest values, handle NaN
        adx_val = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0
        plus_di_val = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0.0
        minus_di_val = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0.0

        return float(adx_val), float(plus_di_val), float(minus_di_val)

    @staticmethod
    def compute_hurst_exponent(prices: pd.Series, window: int = 100) -> float:
        """
        Compute Hurst Exponent to determine mean-reversion vs trending behavior

        The Hurst exponent indicates:
        - H < 0.5: Mean-reverting (anti-persistent) series
        - H = 0.5: Random walk (geometric Brownian motion)
        - H > 0.5: Trending (persistent) series

        Args:
            prices: Series of price data
            window: Lookback window for calculation (default 100)

        Returns:
            float: Hurst exponent (0-1)
            Returns 0.5 (random walk) if calculation fails or insufficient data
        """
        if len(prices) < window:
            return 0.5

        # Use last 'window' prices
        series = prices.iloc[-window:].values

        # Create lags from 2 to min(20, window/5)
        max_lag = min(20, window // 5)
        if max_lag < 2:
            return 0.5

        lags = range(2, max_lag + 1)

        # Calculate tau (standard deviation of differences) for each lag
        tau = []
        for lag in lags:
            # Calculate price differences at this lag
            diffs = np.subtract(series[lag:], series[:-lag])

            # Standard deviation (add epsilon to avoid log(0))
            std_dev = np.std(diffs)
            if std_dev == 0:
                std_dev = 1e-8

            tau.append(std_dev)

        # Perform linear regression in log-log space
        # Hurst exponent is the slope of log(tau) vs log(lag)
        try:
            tau = np.array(tau)
            # Filter out zeros and negative values
            valid_indices = tau > 0
            if np.sum(valid_indices) < 3:
                return 0.5

            log_lags = np.log(list(lags))[valid_indices]
            log_tau = np.log(tau[valid_indices])

            # Linear fit: log(tau) = H * log(lag) + c
            coeffs = np.polyfit(log_lags, log_tau, 1)
            hurst = coeffs[0]  # Slope is the Hurst exponent

            # Clamp to valid range [0, 1]
            hurst = np.clip(hurst, 0.0, 1.0)

            return float(hurst)

        except (ValueError, RuntimeWarning, FloatingPointError):
            # Return 0.5 (random walk) if calculation fails
            return 0.5

    @staticmethod
    def compute_dual_rsi(df: pd.DataFrame,
                        period: int = 14,
                        smooth_period: int = 3) -> Tuple[float, float]:
        """
        Compute dual RSI: fast RSI and smoothed RSI

        Crossovers between fast and smooth RSI can indicate:
        - Fast RSI crossing above smooth: Bullish momentum
        - Fast RSI crossing below smooth: Bearish momentum

        Args:
            df: DataFrame with 'close' column (case-insensitive)
            period: RSI calculation period (default 14)
            smooth_period: Smoothing period for RSI (default 3)

        Returns:
            Tuple of (rsi_fast, rsi_smooth)
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}
        close = df_copy[col_map.get('close', 'close')]
        delta = close.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()

        # Relative Strength
        rs = avg_gains / avg_losses

        # RSI formula
        rsi = 100 - (100 / (1 + rs))

        # Smoothed RSI
        rsi_smooth = rsi.rolling(window=smooth_period).mean()

        return rsi.iloc[-1], rsi_smooth.iloc[-1]

    @staticmethod
    def compute_volatility_regime(df: pd.DataFrame,
                                  atr_period: int = 14,
                                  lookback: int = 20) -> Tuple[str, float]:
        """
        Detect volatility regime using ATR ratio

        Identifies market volatility state:
        - HIGH_VOL: ATR ratio > 1.5 (expanded volatility, caution)
        - NORMAL: 0.7 <= ATR ratio <= 1.5 (normal conditions)
        - LOW_VOL: ATR ratio < 0.7 (compressed volatility, breakout potential)

        Args:
            df: DataFrame with OHLC data
            atr_period: Period for ATR calculation (default 14)
            lookback: Lookback for average ATR (default 20)

        Returns:
            Tuple of (regime, atr_ratio)
            - regime: "HIGH_VOL", "NORMAL", or "LOW_VOL"
            - atr_ratio: Current ATR / Average ATR
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}

        high = df_copy[col_map.get('high', 'high')]
        low = df_copy[col_map.get('low', 'low')]
        close = df_copy[col_map.get('close', 'close')]

        # Calculate True Range
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # Calculate ATR
        atr = tr.rolling(window=atr_period).mean()

        # Current ATR vs average ATR over lookback period
        current_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-lookback:].mean()

        atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        # Determine regime
        if atr_ratio > 1.5:
            regime = "HIGH_VOL"
        elif atr_ratio < 0.7:
            regime = "LOW_VOL"
        else:
            regime = "NORMAL"

        return regime, float(atr_ratio)

    @staticmethod
    def compute_volume_momentum(df: pd.DataFrame, period: int = 20) -> float:
        """
        Compute volume momentum: current volume vs average volume

        Volume confirmation is critical for validating price movements:
        - Ratio > 1.5: High volume, strong signal confirmation
        - Ratio 0.8-1.2: Normal volume
        - Ratio < 0.8: Low volume, weak signal

        Args:
            df: DataFrame with 'volume' column
            period: Period for average volume (default 20)

        Returns:
            float: Volume momentum ratio (current / average)
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}
        volume = df_copy[col_map.get('volume', 'volume')]

        # Average volume over period
        avg_volume = volume.rolling(window=period).mean()

        # Current volume
        current_volume = volume.iloc[-1]

        # Volume momentum ratio
        ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1.0

        return float(ratio)

    @staticmethod
    def compute_multi_period_returns(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Compute returns over multiple periods for momentum analysis

        Multi-timeframe momentum helps identify:
        - Short-term (1 month): Recent trend
        - Medium-term (3 months): Established trend
        - Long-term (6 months): Major trend

        Args:
            df: DataFrame with 'close' column

        Returns:
            Tuple of (ret_1m, ret_3m, ret_6m)
            - ret_1m: 1-month (21 trading days) return
            - ret_3m: 3-month (63 trading days) return
            - ret_6m: 6-month (126 trading days) return
            Returns None for periods with insufficient data
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}
        close = df_copy[col_map.get('close', 'close')]

        # Calculate returns for different periods
        ret_1m = (close.iloc[-1] / close.iloc[-22] - 1) if len(close) >= 22 else None
        ret_3m = (close.iloc[-1] / close.iloc[-66] - 1) if len(close) >= 66 else None
        ret_6m = (close.iloc[-1] / close.iloc[-132] - 1) if len(close) >= 132 else None

        return ret_1m, ret_3m, ret_6m

    @staticmethod
    def compute_skewness(df: pd.DataFrame, window: int = 63) -> float:
        """
        Compute rolling skewness of returns

        Skewness indicates asymmetry in the return distribution:
        - Positive skew: More extreme positive returns (bullish bias)
        - Negative skew: More extreme negative returns (bearish bias)
        - Near zero: Symmetric distribution

        Args:
            df: DataFrame with 'close' column
            window: Rolling window for skewness (default 63 days ~3 months)

        Returns:
            float: Skewness coefficient
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}
        close = df_copy[col_map.get('close', 'close')]
        returns = close.pct_change()

        skew = returns.rolling(window=window).skew()

        return float(skew.iloc[-1]) if not pd.isna(skew.iloc[-1]) else 0.0

    @staticmethod
    def compute_kurtosis(df: pd.DataFrame, window: int = 63) -> float:
        """
        Compute rolling kurtosis of returns

        Kurtosis measures tail risk (fat tails):
        - Kurtosis > 3: Fat tails (higher extreme event probability)
        - Kurtosis = 3: Normal distribution
        - Kurtosis < 3: Thin tails

        Args:
            df: DataFrame with 'close' column
            window: Rolling window for kurtosis (default 63 days)

        Returns:
            float: Excess kurtosis (kurtosis - 3)
        """
        df_copy = df.copy()
        col_map = {col.lower(): col for col in df_copy.columns}
        close = df_copy[col_map.get('close', 'close')]
        returns = close.pct_change()

        kurt = returns.rolling(window=window).kurt()

        return float(kurt.iloc[-1]) if not pd.isna(kurt.iloc[-1]) else 0.0


if __name__ == "__main__":
    """
    Test advanced indicators with sample data
    """
    print("="*80)
    print("ADVANCED INDICATORS - TEST")
    print("="*80)

    # Create sample price data (uptrend with some volatility)
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=200, freq='D')

    # Generate uptrending price with noise
    trend = np.linspace(100, 150, 200)
    noise = np.random.randn(200) * 5
    close_prices = trend + noise

    # Generate OHLC data
    df = pd.DataFrame({
        'date': dates,
        'open': close_prices * 0.995,
        'high': close_prices * 1.01,
        'low': close_prices * 0.99,
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, 200)
    })

    print("\n📊 Testing on synthetic data (200 days, uptrend)")
    print(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # Test ADX
    print("\n1. ADX (Average Directional Index)")
    adx, di_plus, di_minus = AdvancedIndicators.compute_adx(df)
    print(f"   ADX: {adx:.2f}")
    print(f"   DI+: {di_plus:.2f}")
    print(f"   DI-: {di_minus:.2f}")
    if adx >= 25:
        print(f"   → Strong trend detected")
    else:
        print(f"   → Weak or no trend")

    # Test Hurst Exponent
    print("\n2. Hurst Exponent")
    hurst = AdvancedIndicators.compute_hurst_exponent(df['close'])
    print(f"   H: {hurst:.3f}")
    if hurst < 0.5:
        print(f"   → Mean-reverting behavior")
    elif hurst > 0.5:
        print(f"   → Trending behavior")
    else:
        print(f"   → Random walk")

    # Test Dual RSI
    print("\n3. Dual RSI")
    rsi_fast, rsi_smooth = AdvancedIndicators.compute_dual_rsi(df)
    print(f"   RSI (fast): {rsi_fast:.2f}")
    print(f"   RSI (smooth): {rsi_smooth:.2f}")
    if rsi_fast > rsi_smooth:
        print(f"   → Bullish momentum")
    else:
        print(f"   → Bearish momentum")

    # Test Volatility Regime
    print("\n4. Volatility Regime Detection")
    regime, atr_ratio = AdvancedIndicators.compute_volatility_regime(df)
    print(f"   Regime: {regime}")
    print(f"   ATR Ratio: {atr_ratio:.2f}")

    # Test Volume Momentum
    print("\n5. Volume Momentum")
    vol_momentum = AdvancedIndicators.compute_volume_momentum(df)
    print(f"   Volume Ratio: {vol_momentum:.2f}")
    if vol_momentum > 1.5:
        print(f"   → High volume confirmation")
    elif vol_momentum > 0.8:
        print(f"   → Normal volume")
    else:
        print(f"   → Low volume, weak signal")

    # Test Multi-Period Returns
    print("\n6. Multi-Period Returns")
    ret_1m, ret_3m, ret_6m = AdvancedIndicators.compute_multi_period_returns(df)
    if ret_1m:
        print(f"   1-month: {ret_1m*100:+.2f}%")
    if ret_3m:
        print(f"   3-month: {ret_3m*100:+.2f}%")
    if ret_6m:
        print(f"   6-month: {ret_6m*100:+.2f}%")

    # Test Skewness and Kurtosis
    print("\n7. Statistical Properties")
    skew = AdvancedIndicators.compute_skewness(df)
    kurt = AdvancedIndicators.compute_kurtosis(df)
    print(f"   Skewness: {skew:.3f}")
    print(f"   Kurtosis: {kurt:.3f}")

    print("\n" + "="*80)
    print("✅ All indicators computed successfully")
    print("="*80)
