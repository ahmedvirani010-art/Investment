"""
PSX Technical Analysis Agent
Computes standard technical indicators on stored price data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class SignalType(Enum):
    """Type of technical signal"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    OVERBOUGHT = "Overbought"
    OVERSOLD = "Oversold"


class SignalStrength(Enum):
    """Strength of technical signal"""
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"


@dataclass
class TechnicalSignal:
    """Individual technical signal from one indicator"""
    symbol: str
    date: str
    indicator: str          # "RSI", "MACD", "SMA_crossover", etc.
    signal_type: SignalType
    strength: SignalStrength
    value: float            # Current indicator value
    threshold: Optional[float] = None  # Threshold that triggered the signal
    description: str = ""   # Human-readable description


@dataclass
class TechnicalSnapshot:
    """Complete technical picture for one stock on one date"""
    symbol: str
    date: str
    signals: List[TechnicalSignal] = field(default_factory=list)
    overall_bias: SignalType = SignalType.NEUTRAL
    confidence: float = 0.0  # 0.0-1.0 based on signal agreement
    indicator_values: Dict[str, float] = field(default_factory=dict)


class PSXTechnicalAgent:
    """
    Technical analysis agent for Pakistan Stock Exchange

    Computes standard technical indicators and generates trading signals:
    - Trend: SMA/EMA crossovers, price vs SMA(200)
    - Momentum: RSI, MACD, Stochastic
    - Volatility: Bollinger Bands, ATR
    - Volume: OBV
    """

    def __init__(self, price_store):
        """
        Initialize technical agent

        Args:
            price_store: PSXPriceStore instance for reading price data
        """
        self.price_store = price_store

    def analyze_symbol(self, symbol: str) -> TechnicalSnapshot:
        """
        Full technical analysis for one stock

        Args:
            symbol: Stock symbol

        Returns:
            TechnicalSnapshot with all indicators and signals
        """
        # Fetch price data (need 250 days for SMA(200))
        df = self.price_store.get_prices(symbol, days=250)

        if df.empty or len(df) < 50:
            # Not enough data for meaningful analysis
            return TechnicalSnapshot(
                symbol=symbol,
                date=datetime.now().strftime('%Y-%m-%d'),
                signals=[],
                overall_bias=SignalType.NEUTRAL,
                confidence=0.0,
                indicator_values={}
            )

        # Compute all indicators
        signals = []
        indicator_values = {}

        latest_date = df.index[-1].strftime('%Y-%m-%d')

        # RSI
        rsi_signal, rsi_value = self._analyze_rsi(symbol, df, latest_date)
        if rsi_signal:
            signals.append(rsi_signal)
        indicator_values['RSI'] = rsi_value

        # MACD
        macd_signal, macd_values = self._analyze_macd(symbol, df, latest_date)
        if macd_signal:
            signals.append(macd_signal)
        indicator_values.update(macd_values)

        # SMA Crossovers
        sma_signals, sma_values = self._analyze_sma(symbol, df, latest_date)
        signals.extend(sma_signals)
        indicator_values.update(sma_values)

        # Bollinger Bands
        bb_signal, bb_values = self._analyze_bollinger(symbol, df, latest_date)
        if bb_signal:
            signals.append(bb_signal)
        indicator_values.update(bb_values)

        # Stochastic
        stoch_signal, stoch_values = self._analyze_stochastic(symbol, df, latest_date)
        if stoch_signal:
            signals.append(stoch_signal)
        indicator_values.update(stoch_values)

        # ATR (volatility, no direct signal)
        atr_value = self.compute_atr(df)
        if not pd.isna(atr_value):
            indicator_values['ATR'] = atr_value

        # OBV (volume trend, no direct signal yet)
        obv_value = self.compute_obv(df)
        if not pd.isna(obv_value):
            indicator_values['OBV'] = obv_value

        # Aggregate signals into overall bias
        overall_bias, confidence = self._aggregate_signals(signals)

        return TechnicalSnapshot(
            symbol=symbol,
            date=latest_date,
            signals=signals,
            overall_bias=overall_bias,
            confidence=confidence,
            indicator_values=indicator_values
        )

    def analyze_batch(self, symbols: List[str]) -> Dict[str, TechnicalSnapshot]:
        """
        Analyze multiple stocks

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to TechnicalSnapshot
        """
        results = {}

        for symbol in symbols:
            try:
                snapshot = self.analyze_symbol(symbol)
                results[symbol] = snapshot
            except Exception as e:
                print(f"Error analyzing {symbol}: {str(e)}")

        return results

    def get_signals(self, symbol: str) -> List[TechnicalSignal]:
        """
        Get only actionable signals (non-neutral) for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            List of TechnicalSignal objects
        """
        snapshot = self.analyze_symbol(symbol)
        return [s for s in snapshot.signals if s.signal_type != SignalType.NEUTRAL]

    # ===================================================================
    # INDICATOR COMPUTATION METHODS
    # ===================================================================

    def compute_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Compute RSI (Relative Strength Index)

        Args:
            df: DataFrame with Close prices
            period: RSI period (default 14)

        Returns:
            Current RSI value (0-100)
        """
        if len(df) < period + 1:
            return np.nan

        # Calculate price changes
        delta = df['Close'].diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period, min_periods=period).mean()
        avg_losses = losses.rolling(window=period, min_periods=period).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def compute_macd(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Compute MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with Close prices

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        if len(df) < 35:  # Need 26 + 9 days minimum
            return np.nan, np.nan, np.nan

        # Calculate EMAs
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()

        # MACD line
        macd_line = ema12 - ema26

        # Signal line (9-day EMA of MACD)
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # Histogram
        histogram = macd_line - signal_line

        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

    def compute_bollinger(self, df: pd.DataFrame, period: int = 20) -> Tuple[float, float, float]:
        """
        Compute Bollinger Bands

        Args:
            df: DataFrame with Close prices
            period: Period for SMA and standard deviation

        Returns:
            Tuple of (Middle band, Upper band, Lower band)
        """
        if len(df) < period:
            return np.nan, np.nan, np.nan

        # Middle band (SMA)
        middle = df['Close'].rolling(window=period).mean()

        # Standard deviation
        std = df['Close'].rolling(window=period).std()

        # Upper and lower bands
        upper = middle + (2 * std)
        lower = middle - (2 * std)

        return middle.iloc[-1], upper.iloc[-1], lower.iloc[-1]

    def compute_stochastic(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, float]:
        """
        Compute Stochastic Oscillator (%K and %D)

        Args:
            df: DataFrame with High, Low, Close
            period: Lookback period

        Returns:
            Tuple of (%K, %D) values (0-100)
        """
        if len(df) < period:
            return np.nan, np.nan

        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        low_min = df['Low'].rolling(window=period).min()
        high_max = df['High'].rolling(window=period).max()

        k_percent = 100 * ((df['Close'] - low_min) / (high_max - low_min))

        # %D = 3-day SMA of %K
        d_percent = k_percent.rolling(window=3).mean()

        return k_percent.iloc[-1], d_percent.iloc[-1]

    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Compute ATR (Average True Range)

        Args:
            df: DataFrame with High, Low, Close
            period: ATR period

        Returns:
            Current ATR value
        """
        if len(df) < period + 1:
            return np.nan

        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # ATR = average of true range
        atr = true_range.rolling(window=period).mean()

        return atr.iloc[-1]

    def compute_obv(self, df: pd.DataFrame) -> float:
        """
        Compute OBV (On-Balance Volume)

        Args:
            df: DataFrame with Close and Volume

        Returns:
            Current OBV value
        """
        if len(df) < 2:
            return np.nan

        # OBV = cumulative sum of volume when price rises, minus when falls
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()

        return obv.iloc[-1]

    # ===================================================================
    # SIGNAL ANALYSIS METHODS
    # ===================================================================

    def _analyze_rsi(self, symbol: str, df: pd.DataFrame, date: str) -> Tuple[Optional[TechnicalSignal], float]:
        """Analyze RSI and generate signal if overbought/oversold"""
        rsi = self.compute_rsi(df)

        if pd.isna(rsi):
            return None, np.nan

        signal = None

        if rsi >= 70:
            signal = TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="RSI",
                signal_type=SignalType.OVERBOUGHT,
                strength=SignalStrength.STRONG if rsi >= 80 else SignalStrength.MODERATE,
                value=rsi,
                threshold=70,
                description=f"RSI at {rsi:.1f} (overbought)"
            )
        elif rsi <= 30:
            signal = TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="RSI",
                signal_type=SignalType.OVERSOLD,
                strength=SignalStrength.STRONG if rsi <= 20 else SignalStrength.MODERATE,
                value=rsi,
                threshold=30,
                description=f"RSI at {rsi:.1f} (oversold)"
            )

        return signal, rsi

    def _analyze_macd(self, symbol: str, df: pd.DataFrame, date: str) -> Tuple[Optional[TechnicalSignal], Dict[str, float]]:
        """Analyze MACD and generate crossover signals"""
        macd, signal_line, histogram = self.compute_macd(df)

        values = {
            'MACD': macd,
            'MACD_Signal': signal_line,
            'MACD_Histogram': histogram
        }

        if pd.isna(macd):
            return None, values

        # Check for crossover (comparing current vs previous)
        if len(df) >= 36:
            prev_macd = df['Close'].ewm(span=12, adjust=False).mean().iloc[-2] - \
                       df['Close'].ewm(span=26, adjust=False).mean().iloc[-2]
            prev_signal = (df['Close'].ewm(span=12, adjust=False).mean() - \
                          df['Close'].ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean().iloc[-2]

            # Bullish crossover: MACD crosses above signal
            if prev_macd <= prev_signal and macd > signal_line:
                return TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="MACD",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.MODERATE,
                    value=macd,
                    threshold=signal_line,
                    description=f"MACD bullish crossover ({macd:.2f} > {signal_line:.2f})"
                ), values

            # Bearish crossover: MACD crosses below signal
            elif prev_macd >= prev_signal and macd < signal_line:
                return TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="MACD",
                    signal_type=SignalType.BEARISH,
                    strength=SignalStrength.MODERATE,
                    value=macd,
                    threshold=signal_line,
                    description=f"MACD bearish crossover ({macd:.2f} < {signal_line:.2f})"
                ), values

        return None, values

    def _analyze_sma(self, symbol: str, df: pd.DataFrame, date: str) -> Tuple[List[TechnicalSignal], Dict[str, float]]:
        """Analyze SMA crossovers and trend"""
        signals = []
        values = {}

        # Calculate SMAs
        if len(df) >= 20:
            sma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            values['SMA_20'] = sma20
        else:
            sma20 = np.nan

        if len(df) >= 50:
            sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
            values['SMA_50'] = sma50
        else:
            sma50 = np.nan

        if len(df) >= 200:
            sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
            values['SMA_200'] = sma200
        else:
            sma200 = np.nan

        current_price = df['Close'].iloc[-1]

        # SMA(20) vs SMA(50) crossover
        if not pd.isna(sma20) and not pd.isna(sma50) and len(df) >= 51:
            prev_sma20 = df['Close'].rolling(window=20).mean().iloc[-2]
            prev_sma50 = df['Close'].rolling(window=50).mean().iloc[-2]

            # Golden cross: SMA20 crosses above SMA50
            if prev_sma20 <= prev_sma50 and sma20 > sma50:
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="SMA_Crossover",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.STRONG,
                    value=sma20,
                    threshold=sma50,
                    description=f"Golden cross: SMA(20) crossed above SMA(50)"
                ))

            # Death cross: SMA20 crosses below SMA50
            elif prev_sma20 >= prev_sma50 and sma20 < sma50:
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="SMA_Crossover",
                    signal_type=SignalType.BEARISH,
                    strength=SignalStrength.STRONG,
                    value=sma20,
                    threshold=sma50,
                    description=f"Death cross: SMA(20) crossed below SMA(50)"
                ))

        # Price vs SMA(200) - long-term trend
        if not pd.isna(sma200):
            if current_price > sma200 * 1.05:  # More than 5% above
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="SMA_200_Trend",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.MODERATE,
                    value=current_price,
                    threshold=sma200,
                    description=f"Price above SMA(200): uptrend intact"
                ))
            elif current_price < sma200 * 0.95:  # More than 5% below
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="SMA_200_Trend",
                    signal_type=SignalType.BEARISH,
                    strength=SignalStrength.MODERATE,
                    value=current_price,
                    threshold=sma200,
                    description=f"Price below SMA(200): downtrend"
                ))

        return signals, values

    def _analyze_bollinger(self, symbol: str, df: pd.DataFrame, date: str) -> Tuple[Optional[TechnicalSignal], Dict[str, float]]:
        """Analyze Bollinger Bands"""
        middle, upper, lower = self.compute_bollinger(df)

        values = {
            'BB_Middle': middle,
            'BB_Upper': upper,
            'BB_Lower': lower
        }

        if pd.isna(middle):
            return None, values

        current_price = df['Close'].iloc[-1]

        # At or above upper band - overbought
        if current_price >= upper:
            return TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Bollinger_Bands",
                signal_type=SignalType.OVERBOUGHT,
                strength=SignalStrength.MODERATE,
                value=current_price,
                threshold=upper,
                description=f"Price at upper Bollinger Band ({current_price:.2f} >= {upper:.2f})"
            ), values

        # At or below lower band - oversold
        elif current_price <= lower:
            return TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Bollinger_Bands",
                signal_type=SignalType.OVERSOLD,
                strength=SignalStrength.MODERATE,
                value=current_price,
                threshold=lower,
                description=f"Price at lower Bollinger Band ({current_price:.2f} <= {lower:.2f})"
            ), values

        return None, values

    def _analyze_stochastic(self, symbol: str, df: pd.DataFrame, date: str) -> Tuple[Optional[TechnicalSignal], Dict[str, float]]:
        """Analyze Stochastic Oscillator"""
        k, d = self.compute_stochastic(df)

        values = {
            'Stochastic_K': k,
            'Stochastic_D': d
        }

        if pd.isna(k):
            return None, values

        # Overbought: %K > 80
        if k >= 80:
            return TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Stochastic",
                signal_type=SignalType.OVERBOUGHT,
                strength=SignalStrength.MODERATE,
                value=k,
                threshold=80,
                description=f"Stochastic overbought (%K={k:.1f})"
            ), values

        # Oversold: %K < 20
        elif k <= 20:
            return TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Stochastic",
                signal_type=SignalType.OVERSOLD,
                strength=SignalStrength.MODERATE,
                value=k,
                threshold=20,
                description=f"Stochastic oversold (%K={k:.1f})"
            ), values

        return None, values

    def _aggregate_signals(self, signals: List[TechnicalSignal]) -> Tuple[SignalType, float]:
        """
        Aggregate multiple signals into overall bias and confidence

        Args:
            signals: List of TechnicalSignal objects

        Returns:
            Tuple of (overall_bias, confidence)
        """
        if not signals:
            return SignalType.NEUTRAL, 0.0

        # Weight signals by strength
        strength_weights = {
            SignalStrength.STRONG: 3,
            SignalStrength.MODERATE: 2,
            SignalStrength.WEAK: 1
        }

        bullish_weight = 0
        bearish_weight = 0
        total_weight = 0

        for signal in signals:
            weight = strength_weights[signal.strength]
            total_weight += weight

            if signal.signal_type == SignalType.BULLISH:
                bullish_weight += weight
            elif signal.signal_type == SignalType.BEARISH:
                bearish_weight += weight
            elif signal.signal_type == SignalType.OVERSOLD:
                # Oversold is bullish (potential reversal)
                bullish_weight += weight
            elif signal.signal_type == SignalType.OVERBOUGHT:
                # Overbought is bearish (potential reversal)
                bearish_weight += weight

        # Determine overall bias
        if bullish_weight > bearish_weight:
            overall_bias = SignalType.BULLISH
        elif bearish_weight > bullish_weight:
            overall_bias = SignalType.BEARISH
        else:
            overall_bias = SignalType.NEUTRAL

        # Calculate confidence (0.0 to 1.0)
        if total_weight > 0:
            confidence = abs(bullish_weight - bearish_weight) / total_weight
        else:
            confidence = 0.0

        return overall_bias, confidence


def main():
    """Example usage of PSXTechnicalAgent"""
    from psx_price_store import PSXPriceStore

    print("="*80)
    print("PSX TECHNICAL ANALYSIS AGENT - DEMO")
    print("="*80)

    # Initialize price store and technical agent
    print("\nInitializing components...")
    price_store = PSXPriceStore()
    tech_agent = PSXTechnicalAgent(price_store)

    # Test symbols
    test_symbols = ['HBL', 'LUCK', 'PSO']

    print(f"\nFetching price data for {test_symbols}...")
    price_store.bulk_update(test_symbols, days=250)

    print("\nRunning technical analysis...\n")

    for symbol in test_symbols:
        print(f"\n{'='*80}")
        print(f"📊 {symbol}")
        print('='*80)

        snapshot = tech_agent.analyze_symbol(symbol)

        # Indicator values
        print(f"\n📈 Key Indicators:")
        for indicator, value in sorted(snapshot.indicator_values.items()):
            if not pd.isna(value):
                print(f"   {indicator:20s}: {value:>10.2f}")

        # Signals
        print(f"\n🔔 Signals ({len(snapshot.signals)}):")
        for signal in snapshot.signals:
            strength_emoji = {"Strong": "🔴", "Moderate": "🟡", "Weak": "🟢"}
            emoji = strength_emoji.get(signal.strength.value, "")
            print(f"   {emoji} [{signal.strength.value}] {signal.indicator}: {signal.description}")

        # Overall bias
        bias_emoji = {
            "Bullish": "📈",
            "Bearish": "📉",
            "Neutral": "➖"
        }
        print(f"\n💡 Overall Bias: {bias_emoji.get(snapshot.overall_bias.value, '')} {snapshot.overall_bias.value}")
        print(f"   Confidence: {snapshot.confidence*100:.0f}%")

    print(f"\n{'='*80}")
    print("✅ Technical analysis complete")
    print("="*80)


if __name__ == "__main__":
    main()
