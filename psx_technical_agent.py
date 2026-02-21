"""
PSX Technical Analysis Agent
Computes standard technical indicators on stored price data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import sys

# Optional import for divergence detection
try:
    from psx_divergence_detector import Divergence
    DIVERGENCE_AVAILABLE = True
except ImportError:
    DIVERGENCE_AVAILABLE = False
    Divergence = None

# Optional import for pattern recognition
try:
    from psx_pattern_recognizer import ChartPattern
    PATTERN_AVAILABLE = True
except ImportError:
    PATTERN_AVAILABLE = False
    ChartPattern = None


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


# Indicator classification for trend vs mean-reversion scoring
TREND_INDICATORS = {"MACD", "SMA_Crossover", "SMA_200_Trend", "Fibonacci", "Elliott_Wave"}
MEAN_REVERSION_INDICATORS = {"RSI", "Bollinger_Bands", "Stochastic"}


@dataclass
class TechnicalSnapshot:
    """Complete technical picture for one stock on one date"""
    symbol: str
    date: str
    signals: List[TechnicalSignal] = field(default_factory=list)
    overall_bias: SignalType = SignalType.NEUTRAL
    confidence: float = 0.0  # 0.0-1.0 based on signal agreement
    indicator_values: Dict[str, float] = field(default_factory=dict)
    divergences: List = field(default_factory=list)  # List[Divergence] if available
    patterns: List = field(default_factory=list)  # List[ChartPattern] if available
    # Fibonacci retracement/extension levels (optional structured output)
    fibonacci_levels: Optional[Dict] = None
    # Elliott Wave phase and structure (optional; simplified rule-based)
    elliott_wave: Optional[Dict] = None
    # Scores 1-100 (50 = neutral): trend-following strength, mean-reversion strength, overall
    trend_score: int = 50
    mean_reversion_score: int = 50
    technical_score: int = 50
    # AI-generated technical summary and buy/sell call (when LLM or rule-based generator runs)
    ai_summary: Optional[str] = None
    ai_call: Optional[str] = None       # "Buy", "Hold", or "Sell"
    ai_call_rationale: Optional[str] = None


@dataclass
class MultiTimeframeSnapshot:
    """Multi-timeframe analysis combining daily and weekly views"""
    symbol: str
    date: str
    daily: TechnicalSnapshot
    weekly: TechnicalSnapshot
    confirmation_score: float = 0.0  # 0.0-1.0 based on timeframe agreement
    aligned_signals: List[str] = field(default_factory=list)
    conflicting_signals: List[str] = field(default_factory=list)


class PSXTechnicalAgent:
    """
    Technical analysis agent for Pakistan Stock Exchange

    Computes standard technical indicators and generates trading signals:
    - Trend: SMA/EMA crossovers, price vs SMA(200)
    - Momentum: RSI, MACD, Stochastic
    - Volatility: Bollinger Bands, ATR
    - Volume: OBV
    """

    def __init__(self, price_store, divergence_detector=None, pattern_recognizer=None, llm_client=None):
        """
        Initialize technical agent

        Args:
            price_store: PSXPriceStore instance for reading price data
            divergence_detector: Optional PSXDivergenceDetector instance
            pattern_recognizer: Optional PSXPatternRecognizer instance
            llm_client: Optional callable(messages, system_prompt=None, **kwargs) -> str for AI summary/call.
                        Example: llm_client from llm_client.chat_completion (with messages=[], system_prompt=).
                        If None, a rule-based summary and call are still generated.
        """
        self.price_store = price_store
        self.divergence_detector = divergence_detector
        self.pattern_recognizer = pattern_recognizer
        self.llm_client = llm_client

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
                indicator_values={},
                trend_score=50,
                mean_reversion_score=50,
                technical_score=50,
                ai_summary="Insufficient price data for technical analysis (need at least 50 days).",
                ai_call="Hold",
                ai_call_rationale="Not enough price history to generate a technical view. Wait for more data or check the symbol.",
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

        # Fibonacci retracement and extension
        fibonacci_levels = None
        fib_signals, fib_values, fibonacci_levels = self._analyze_fibonacci(symbol, df, latest_date)
        signals.extend(fib_signals)
        indicator_values.update(fib_values)

        # Elliott Wave (simplified rule-based)
        elliott_wave = None
        ew_signals, ew_values, elliott_wave = self._analyze_elliott_wave(symbol, df, latest_date)
        signals.extend(ew_signals)
        indicator_values.update(ew_values)

        # Divergence detection (if detector is available)
        divergences = []
        if self.divergence_detector and DIVERGENCE_AVAILABLE:
            # Add RSI and MACD to dataframe for divergence detection
            df_with_indicators = df.copy()
            df_with_indicators['RSI'] = pd.Series(dtype=float)
            df_with_indicators['MACD'] = pd.Series(dtype=float)

            # Compute RSI for entire dataframe
            if len(df) >= 14:
                delta = df['Close'].diff()
                gains = delta.where(delta > 0, 0)
                losses = -delta.where(delta < 0, 0)
                avg_gains = gains.rolling(window=14, min_periods=14).mean()
                avg_losses = losses.rolling(window=14, min_periods=14).mean()
                rs = avg_gains / avg_losses
                df_with_indicators['RSI'] = 100 - (100 / (1 + rs))

            # Compute MACD for entire dataframe
            if len(df) >= 35:
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df_with_indicators['MACD'] = ema12 - ema26

            # Detect divergences
            try:
                divergences = self.divergence_detector.detect_all_divergences(symbol, df_with_indicators)

                # Convert divergences to signals for aggregation
                for div in divergences:
                    # Bullish divergences are oversold-like signals (reversal up expected)
                    if "Bullish" in div.divergence_type.value:
                        signal_type = SignalType.OVERSOLD
                    # Bearish divergences are overbought-like signals (reversal down expected)
                    else:
                        signal_type = SignalType.OVERBOUGHT

                    signal_strength = SignalStrength.STRONG if div.strength == "Strong" else SignalStrength.MODERATE

                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        date=latest_date,
                        indicator="Divergence",
                        signal_type=signal_type,
                        strength=signal_strength,
                        value=0.0,  # Divergence doesn't have a single value
                        description=div.divergence_type.value
                    ))
            except Exception as e:
                print(f"  Warning: Error detecting divergences for {symbol}: {str(e)}", file=sys.stderr)

        # Pattern recognition (if recognizer is available)
        patterns = []
        if self.pattern_recognizer and PATTERN_AVAILABLE:
            try:
                patterns = self.pattern_recognizer.detect_all_patterns(symbol, df)

                # Convert patterns to signals for aggregation
                for pattern in patterns:
                    # Only add signals for confirmed patterns (more weight)
                    if pattern.status.value == "Confirmed":
                        # Bearish patterns (H&S, Double Top) are overbought-like signals
                        if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                            signal_type = SignalType.BEARISH
                            signal_strength = SignalStrength.STRONG
                        # Bullish patterns (Inverse H&S, Double Bottom) are oversold-like signals
                        else:
                            signal_type = SignalType.BULLISH
                            signal_strength = SignalStrength.STRONG

                        signals.append(TechnicalSignal(
                            symbol=symbol,
                            date=latest_date,
                            indicator="Pattern",
                            signal_type=signal_type,
                            strength=signal_strength,
                            value=0.0,  # Patterns don't have a single value
                            description=f"{pattern.pattern_type.value} ({pattern.status.value})"
                        ))
                    # Forming patterns get weaker signal weight
                    elif pattern.status.value == "Forming":
                        if pattern.pattern_type.value in ["Head and Shoulders", "Double Top"]:
                            signal_type = SignalType.BEARISH
                        else:
                            signal_type = SignalType.BULLISH

                        signals.append(TechnicalSignal(
                            symbol=symbol,
                            date=latest_date,
                            indicator="Pattern",
                            signal_type=signal_type,
                            strength=SignalStrength.WEAK,
                            value=0.0,
                            description=f"{pattern.pattern_type.value} ({pattern.status.value})"
                        ))
            except Exception as e:
                print(f"  Warning: Error detecting patterns for {symbol}: {str(e)}", file=sys.stderr)

        # Aggregate signals into overall bias
        overall_bias, confidence = self._aggregate_signals(signals)
        current_price = float(df["Close"].iloc[-1]) if len(df) > 0 else None
        trend_score, mean_reversion_score, technical_score = self._compute_scores(
            signals, indicator_values=indicator_values, current_price=current_price
        )

        snapshot = TechnicalSnapshot(
            symbol=symbol,
            date=latest_date,
            signals=signals,
            overall_bias=overall_bias,
            confidence=confidence,
            indicator_values=indicator_values,
            divergences=divergences,
            patterns=patterns,
            fibonacci_levels=fibonacci_levels,
            elliott_wave=elliott_wave,
            trend_score=trend_score,
            mean_reversion_score=mean_reversion_score,
            technical_score=technical_score,
        )
        summary, call, rationale = self._generate_summary_and_call(snapshot)
        snapshot.ai_summary = summary
        snapshot.ai_call = call
        snapshot.ai_call_rationale = rationale
        return snapshot

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
                print(f"Error analyzing {symbol}: {str(e)}", file=sys.stderr)

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
    # SWING POINTS (for Fibonacci & Elliott Wave)
    # ===================================================================

    def _get_swing_points(
        self, df: pd.DataFrame, window: int = 5, lookback_bars: int = 120
    ) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """
        Detect swing highs and swing lows (local extrema) over a rolling window.

        A swing high is a bar whose High is the max of High over `window` bars centered.
        A swing low is a bar whose Low is the min of Low over the same window.
        Returns lists of (date_str, price) in chronological order for the last lookback_bars.

        Args:
            df: DataFrame with DatetimeIndex and High, Low columns
            window: Number of bars on each side for local max/min (default 5)
            lookback_bars: Use only the last N bars (default 120)

        Returns:
            (swing_highs, swing_lows), each a list of (date_str, price)
        """
        if len(df) < 2 * window + 1:
            return [], []

        use = df.tail(lookback_bars).copy()
        if len(use) < 2 * window + 1:
            return [], []

        high_roll = use['High'].rolling(window=2 * window + 1, center=True).max()
        low_roll = use['Low'].rolling(window=2 * window + 1, center=True).min()

        swing_highs = []
        swing_lows = []
        for i in range(window, len(use) - window):
            idx = use.index[i]
            if use['High'].iloc[i] == high_roll.iloc[i] and pd.notna(high_roll.iloc[i]):
                swing_highs.append((idx.strftime('%Y-%m-%d'), float(use['High'].iloc[i])))
            if use['Low'].iloc[i] == low_roll.iloc[i] and pd.notna(low_roll.iloc[i]):
                swing_lows.append((idx.strftime('%Y-%m-%d'), float(use['Low'].iloc[i])))

        return swing_highs, swing_lows

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

    def _analyze_fibonacci(
        self, symbol: str, df: pd.DataFrame, date: str
    ) -> Tuple[List[TechnicalSignal], Dict[str, float], Optional[Dict]]:
        """
        Compute Fibonacci retracement levels from last significant swing and optionally
        emit signals when price is near key levels (38.2, 50, 61.8).
        """
        signals: List[TechnicalSignal] = []
        values: Dict[str, float] = {}
        fib_levels: Optional[Dict] = None

        swing_highs, swing_lows = self._get_swing_points(df, window=5, lookback_bars=100)
        if not swing_highs or not swing_lows:
            return signals, values, fib_levels

        # Last significant swing high and low (most recent of each)
        sh_date, swing_high = swing_highs[-1]
        sl_date, swing_low = swing_lows[-1]
        price_range = abs(swing_high - swing_low)
        if price_range < 1e-9:
            return signals, values, fib_levels

        # Trend: if swing low is before swing high → uptrend (retracement from high)
        uptrend = sl_date < sh_date
        low_price = min(swing_high, swing_low)
        high_price = max(swing_high, swing_low)

        # Retracement levels (0, 23.6, 38.2, 50, 61.8, 78.6, 100)
        retrace_pcts = (0.0, 23.6, 38.2, 50.0, 61.8, 78.6, 100.0)
        levels = {}
        for pct in retrace_pcts:
            level = low_price + (pct / 100.0) * (high_price - low_price)
            key = f"Fib_Retrace_{int(pct) if pct == int(pct) else str(pct).replace('.', '')}"
            levels[key] = level
            values[key] = level

        values['Fib_SwingHigh'] = swing_high
        values['Fib_SwingLow'] = swing_low
        values['Fib_Trend'] = 1.0 if uptrend else -1.0

        # Extensions (127.2%, 161.8% beyond the range)
        if uptrend:
            values['Fib_Ext_1272'] = high_price + 0.272 * price_range
            values['Fib_Ext_1618'] = high_price + 0.618 * price_range
        else:
            values['Fib_Ext_1272'] = low_price - 0.272 * price_range
            values['Fib_Ext_1618'] = low_price - 0.618 * price_range

        current_price = float(df['Close'].iloc[-1])
        tolerance_pct = 0.02  # 2% of price for "at level"
        key_levels = [(38.2, 38.2), (50.0, 50.0), (61.8, 61.8)]
        nearest_pct = None
        for pct, _ in key_levels:
            level = low_price + (pct / 100.0) * (high_price - low_price)
            if abs(current_price - level) / (current_price or 1) <= tolerance_pct:
                nearest_pct = pct
                if uptrend:
                    # In uptrend, price near support (e.g. 61.8) is bullish
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="Fibonacci",
                        signal_type=SignalType.BULLISH,
                        strength=SignalStrength.MODERATE,
                        value=current_price,
                        threshold=level,
                        description=f"At {pct}% Fibonacci support"
                    ))
                else:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        date=date,
                        indicator="Fibonacci",
                        signal_type=SignalType.BEARISH,
                        strength=SignalStrength.MODERATE,
                        value=current_price,
                        threshold=level,
                        description=f"At {pct}% Fibonacci resistance"
                    ))
                break
        if nearest_pct is not None:
            values['Fib_NearestLevel'] = float(nearest_pct)

        fib_levels = {
            "swing_high": swing_high,
            "swing_low": swing_low,
            "trend": "up" if uptrend else "down",
            "levels": {k: v for k, v in levels.items()},
            "current_price": current_price,
        }
        return signals, values, fib_levels

    def _analyze_elliott_wave(
        self, symbol: str, df: pd.DataFrame, date: str
    ) -> Tuple[List[TechnicalSignal], Dict[str, float], Optional[Dict]]:
        """
        Simplified rule-based Elliott Wave interpretation from swing points.
        Classifies current phase (e.g. Wave 3, Wave 5, Corrective) and emits optional signals.
        """
        signals: List[TechnicalSignal] = []
        values: Dict[str, float] = {}
        ew: Optional[Dict] = None

        swing_highs, swing_lows = self._get_swing_points(df, window=5, lookback_bars=120)
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return signals, values, ew

        # Build alternating pivot list (date, price, is_high) chronological
        pivots: List[Tuple[str, float, bool]] = []
        seen_dates = set()
        for d, p in swing_highs:
            if d not in seen_dates:
                pivots.append((d, p, True))
                seen_dates.add(d)
        for d, p in swing_lows:
            if d not in seen_dates:
                pivots.append((d, p, False))
                seen_dates.add(d)
        pivots.sort(key=lambda x: x[0])
        if len(pivots) < 3:
            return signals, values, ew

        # Classify: try to see last move as impulse (5 waves) or corrective (3)
        current_price = float(df['Close'].iloc[-1])
        phase = "Unclear"
        direction = 0  # 1 up, -1 down
        confidence = 0.0
        wave_label = ""

        # Last few pivots
        last = pivots[-7:]
        # Check if we end on a high or low
        last_is_high = last[-1][2]
        prev_low = next((p[1] for p in reversed(last) if not p[2]), None)
        prev_high = next((p[1] for p in reversed(last) if p[2]), None)
        if prev_low is None or prev_high is None:
            values['Elliott_Confidence'] = 0.0
            ew = {"phase": phase, "direction": direction, "confidence": confidence, "wave_label": wave_label}
            return signals, values, ew

        last_high = last[-1][1] if last[-1][2] else prev_high
        last_low = last[-1][1] if not last[-1][2] else prev_low

        # Simple heuristic: compare last swing range to previous
        if last_is_high:
            move_up = last_high - prev_low
            move_down_prior = prev_high - prev_low if prev_high else 0
            if move_down_prior > 1e-9 and move_up > move_down_prior * 0.6:
                # Possible impulse up: wave 3 or 5
                direction = 1
                if move_up >= move_down_prior:
                    phase = "Impulse"
                    wave_label = "Wave 3 or 5 (up)"
                    confidence = 0.5
                else:
                    phase = "Impulse"
                    wave_label = "Wave 1 or 3 (up)"
                    confidence = 0.4
        else:
            move_down = prev_high - last_low
            move_up_prior = prev_high - prev_low if prev_low else 0
            if move_up_prior > 1e-9 and move_down > move_up_prior * 0.38 and move_down < move_up_prior:
                # Possible pullback (wave 2 or 4)
                direction = -1
                phase = "Corrective"
                wave_label = "Wave 2 or 4 (pullback)"
                confidence = 0.45
            elif move_down > move_up_prior:
                direction = -1
                phase = "Corrective"
                wave_label = "Corrective A or C"
                confidence = 0.4

        values['Elliott_Confidence'] = confidence
        if direction != 0:
            values['Elliott_Direction'] = float(direction)

        ew = {
            "phase": phase,
            "direction": direction,
            "confidence": confidence,
            "wave_label": wave_label or phase,
        }

        # Actionable signals
        if "Wave 3" in wave_label or "Wave 5" in wave_label:
            if direction == 1:
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    date=date,
                    indicator="Elliott_Wave",
                    signal_type=SignalType.BULLISH,
                    strength=SignalStrength.MODERATE,
                    value=current_price,
                    description=f"Elliott: {wave_label}"
                ))
        if "Wave 5 complete" in wave_label:
            # Caution: wave 5 complete often precedes pullback
            signals.append(TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Elliott_Wave",
                signal_type=SignalType.BEARISH,
                strength=SignalStrength.WEAK,
                value=current_price,
                description="Elliott: Wave 5 complete (caution)"
            ))
        if "Wave 2 or 4" in wave_label and direction == -1:
            signals.append(TechnicalSignal(
                symbol=symbol,
                date=date,
                indicator="Elliott_Wave",
                signal_type=SignalType.BULLISH,
                strength=SignalStrength.WEAK,
                value=current_price,
                description=f"Elliott: {wave_label} (potential reversal)"
            ))

        return signals, values, ew

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

        # Confidence (0.0 to 1.0): agreement among *directional* signals only.
        # Use directional weight in denominator so NEUTRAL signals don't dilute confidence.
        # When all directional signals agree, confidence = 1.0; when split, proportionally lower.
        total_directional = bullish_weight + bearish_weight
        if total_directional > 0:
            confidence = abs(bullish_weight - bearish_weight) / total_directional
            # Scale by fraction of weight that is directional (1 signal among many neutrals = lower confidence)
            if total_weight > 0:
                directional_fraction = total_directional / total_weight
                confidence = confidence * (0.6 + 0.4 * directional_fraction)
        else:
            # All signals NEUTRAL: use a small non-zero confidence when we had signals (indicators were checked, no clear direction)
            confidence = 0.15 if total_weight > 0 else 0.0

        return overall_bias, min(1.0, confidence)

    def _compute_scores(
        self,
        signals: List[TechnicalSignal],
        indicator_values: Optional[Dict[str, float]] = None,
        current_price: Optional[float] = None,
    ) -> Tuple[int, int, int]:
        """
        Compute trend-following score, mean-reversion score, and overall technical score (1-100).
        50 = neutral; >50 = bullish strength; <50 = bearish strength.
        When indicator_values is provided, blends signal-based scores with value-based contributions
        (RSI, MACD, price vs SMAs, Fib, Elliott) so the score reflects state even without discrete signals.
        """
        strength_weights = {
            SignalStrength.STRONG: 3,
            SignalStrength.MODERATE: 2,
            SignalStrength.WEAK: 1,
        }

        def net_for_indicators(indicators: set) -> Tuple[float, float]:
            """Returns (net_direction -1..1, total_weight)."""
            bullish_w = 0.0
            bearish_w = 0.0
            for s in signals:
                if s.indicator not in indicators:
                    continue
                w = strength_weights.get(s.strength, 1)
                if s.signal_type in (SignalType.BULLISH, SignalType.OVERSOLD):
                    bullish_w += w
                elif s.signal_type in (SignalType.BEARISH, SignalType.OVERBOUGHT):
                    bearish_w += w
            total = bullish_w + bearish_w
            if total <= 0:
                return 0.0, 0.0
            net = (bullish_w - bearish_w) / total
            return net, total

        trend_net, trend_w = net_for_indicators(TREND_INDICATORS)
        mr_net, mr_w = net_for_indicators(MEAN_REVERSION_INDICATORS)

        trend_score = 50 + int(round(50 * trend_net)) if trend_w > 0 else 50
        mean_reversion_score = 50 + int(round(50 * mr_net)) if mr_w > 0 else 50

        # Value-based contribution from raw indicators (when provided)
        iv = indicator_values or {}
        trend_value = 50.0
        mr_value = 50.0

        def _safe(v: Optional[float]) -> float:
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                return np.nan
            return float(v)

        # Mean-reversion: RSI and Stochastic (0-100 scale; <40 bullish, >60 bearish)
        rsi = _safe(iv.get("RSI"))
        if not np.isnan(rsi):
            mr_value = 50.0 + (50 - rsi) * 0.5  # RSI 0 -> 75, RSI 100 -> 25
        stoch_k = _safe(iv.get("Stochastic_K"))
        if not np.isnan(stoch_k):
            stoch_contrib = (50 - stoch_k) * 0.3
            mr_value = 50.0 + (mr_value - 50.0) * 0.6 + stoch_contrib * 0.4 if not np.isnan(rsi) else 50.0 + stoch_contrib
        if not np.isnan(mr_value):
            mr_value = max(1.0, min(100.0, mr_value))

        # Trend: MACD histogram, price vs SMAs, Fib_Trend, Elliott
        macd_hist = _safe(iv.get("MACD_Histogram"))
        if not np.isnan(macd_hist):
            trend_value = 50.0 + np.sign(macd_hist) * min(25, abs(macd_hist) * 10)
        sma20 = _safe(iv.get("SMA_20"))
        sma50 = _safe(iv.get("SMA_50"))
        sma200 = _safe(iv.get("SMA_200"))
        price = _safe(current_price) if current_price is not None else np.nan
        if not np.isnan(price) and (not np.isnan(sma20) or not np.isnan(sma50) or not np.isnan(sma200)):
            above = 0
            if not np.isnan(sma200) and sma200 != 0:
                above += 1 if price > sma200 else -1
            if not np.isnan(sma50) and sma50 != 0:
                above += 1 if price > sma50 else -1
            if not np.isnan(sma20) and sma20 != 0:
                above += 1 if price > sma20 else -1
            if above != 0:
                sma_contrib = 50.0 + above * 10.0
                trend_value = (trend_value + sma_contrib) / 2.0 if not np.isnan(macd_hist) else sma_contrib
        fib_trend = _safe(iv.get("Fib_Trend"))
        if not np.isnan(fib_trend) and fib_trend != 0:
            trend_value = trend_value + np.sign(fib_trend) * 5.0
        elliott_conf = _safe(iv.get("Elliott_Confidence"))
        elliott_dir = _safe(iv.get("Elliott_Direction"))
        if not np.isnan(elliott_conf) and not np.isnan(elliott_dir) and elliott_conf > 0:
            trend_value = trend_value + elliott_dir * 5.0 * elliott_conf
        if not np.isnan(trend_value):
            trend_value = max(1.0, min(100.0, trend_value))

        # Blend: 60% signal-based, 40% value-based when value contribution is available
        use_trend_value = indicator_values and not np.isnan(trend_value) and (not np.isnan(macd_hist) or not np.isnan(price) or not np.isnan(_safe(iv.get("Fib_Trend"))) or not np.isnan(elliott_conf))
        use_mr_value = indicator_values and (not np.isnan(rsi) or not np.isnan(stoch_k)) and not np.isnan(mr_value)
        if use_trend_value:
            trend_score = int(round(0.6 * trend_score + 0.4 * trend_value))
        if use_mr_value:
            mean_reversion_score = int(round(0.6 * mean_reversion_score + 0.4 * mr_value))

        # Overall: average of the two category scores (each 1-100), clamped
        technical_score = (trend_score + mean_reversion_score) // 2
        trend_score = max(1, min(100, trend_score))
        mean_reversion_score = max(1, min(100, mean_reversion_score))
        technical_score = max(1, min(100, technical_score))

        return trend_score, mean_reversion_score, technical_score

    # ===================================================================
    # AI SUMMARY AND BUY/SELL CALL
    # ===================================================================

    def _build_technical_context(self, snapshot: TechnicalSnapshot) -> str:
        """Build a concise text description of the snapshot for LLM or rule-based summary."""
        lines = [
            f"Symbol: {snapshot.symbol}, Date: {snapshot.date}",
            f"Overall bias: {snapshot.overall_bias.value}, Confidence: {snapshot.confidence:.0%}",
            f"Scores (1-100): technical={snapshot.technical_score}, trend={snapshot.trend_score}, mean_reversion={snapshot.mean_reversion_score}",
        ]
        key_inds = ["RSI", "MACD", "SMA_20", "SMA_50", "SMA_200", "Fib_SwingHigh", "Fib_SwingLow", "Fib_Trend", "Elliott_Confidence"]
        for k in key_inds:
            v = snapshot.indicator_values.get(k)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                lines.append(f"  {k}: {v}")
        if snapshot.signals:
            lines.append("Signals:")
            for s in snapshot.signals[:12]:
                lines.append(f"  - {s.indicator}: {s.signal_type.value} ({s.strength.value}) — {s.description or s.value}")
        if snapshot.fibonacci_levels:
            fl = snapshot.fibonacci_levels
            lines.append(f"Fibonacci: trend={fl.get('trend')}, swing_high={fl.get('swing_high')}, swing_low={fl.get('swing_low')}")
        if snapshot.elliott_wave:
            ew = snapshot.elliott_wave
            lines.append(f"Elliott: {ew.get('wave_label') or ew.get('phase')} (confidence={ew.get('confidence')})")
        return "\n".join(lines)

    def _generate_summary_and_call(
        self, snapshot: TechnicalSnapshot
    ) -> Tuple[str, str, str]:
        """
        Generate a short technical summary and a Buy/Hold/Sell call with rationale.
        Uses LLM when self.llm_client is set; otherwise uses rule-based logic.
        Returns (ai_summary, ai_call, ai_call_rationale).
        """
        context = self._build_technical_context(snapshot)
        if self.llm_client:
            try:
                return self._generate_summary_and_call_llm(context, snapshot)
            except Exception as e:
                if hasattr(e, "args") and e.args:
                    print(f"  Warning: LLM technical summary failed ({e.args[0]}), using rule-based.", file=sys.stderr)
                else:
                    print(f"  Warning: LLM technical summary failed, using rule-based.", file=sys.stderr)
        return self._generate_summary_and_call_rule_based(snapshot)

    def _generate_summary_and_call_llm(
        self, context: str, snapshot: TechnicalSnapshot
    ) -> Tuple[str, str, str]:
        """Use LLM to produce technical summary and call with rationale."""
        system = (
            "You are a technical analyst for the Pakistan Stock Exchange (PSX). "
            "Given a technical snapshot (indicators, signals, scores), respond with a technical summary that "
            "references specific indicator levels (e.g. RSI value, price vs SMA(200), MACD state, Fibonacci level), "
            "a single call (Buy, Hold, or Sell), and a rationale that cites which indicators support the call "
            "and which are mixed or against. Be evidence-based and concise."
        )
        user = (
            "Technical snapshot:\n" + context + "\n\n"
            "Respond in JSON only, with exactly these keys (no other text):\n"
            '"summary": "2-4 sentences describing the technical picture. Reference specific levels: e.g. RSI at X, '
            'price above/below SMA(200), MACD positive/negative, Fibonacci trend, key signals.",\n'
            '"call": "Buy" or "Hold" or "Sell",\n'
            '"rationale": "2-3 sentences. Cite which indicators support this call and which are mixed or against. '
            'Optionally add a brief risk note (e.g. stop level or what would add conviction)."'
        )
        try:
            reply = self.llm_client(
                messages=[{"role": "user", "content": user}],
                system_prompt=system,
                temperature=0.3,
                max_tokens=600,
            )
        except TypeError:
            reply = self.llm_client(messages=[{"role": "user", "content": user}], system_prompt=system)
        reply = reply.strip()
        # Try to parse JSON (handle markdown code block)
        json_str = reply
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", reply)
        if m:
            json_str = m.group(1).strip()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            data = {}
        summary = (data.get("summary") or "").strip() or "Technical summary could not be generated."
        call_raw = (data.get("call") or "").strip().capitalize()
        if call_raw not in ("Buy", "Hold", "Sell"):
            call_raw = "Hold"
        rationale = (data.get("rationale") or "").strip() or "See indicator scores and signals above."
        return summary, call_raw, rationale

    def _generate_summary_and_call_rule_based(self, snapshot: TechnicalSnapshot) -> Tuple[str, str, str]:
        """Rule-based technical summary and Buy/Hold/Sell call with rationale.
        Builds indicator-specific sentences and rationale that cite specific levels and signals.
        """
        def _v(k: str):
            val = snapshot.indicator_values.get(k)
            if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
                return None
            return val

        bias = snapshot.overall_bias.value
        conf = snapshot.confidence
        ts = snapshot.technical_score
        trend = snapshot.trend_score
        parts = []

        # Indicator-specific sentences (2-4)
        rsi = _v("RSI")
        if rsi is not None:
            if rsi < 35:
                parts.append(f"RSI at {rsi:.0f} suggests oversold and potential mean reversion up.")
            elif rsi > 65:
                parts.append(f"RSI at {rsi:.0f} suggests overbought; watch for pullback.")
            else:
                parts.append(f"RSI at {rsi:.0f} is in neutral territory.")

        price = _v("Close")
        if price is None and snapshot.fibonacci_levels:
            price = snapshot.fibonacci_levels.get("current_price")
        sma20, sma50, sma200 = _v("SMA_20"), _v("SMA_50"), _v("SMA_200")
        if price is not None and (sma200 is not None or sma50 is not None):
            above = []
            if sma200 is not None and price > sma200:
                above.append("above SMA(200)")
            elif sma200 is not None:
                above.append("below SMA(200)")
            if sma50 is not None and price > sma50:
                above.append("above SMA(50)")
            elif sma50 is not None:
                above.append("below SMA(50)")
            if above:
                parts.append(f"Price holds {', '.join(above)}.")

        macd_hist = _v("MACD_Histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                parts.append("MACD histogram is positive, supporting short-term momentum.")
            else:
                parts.append("MACD histogram is negative; momentum is weak or fading.")

        if snapshot.fibonacci_levels:
            fl = snapshot.fibonacci_levels
            tr = fl.get("trend")
            parts.append(f"Fibonacci context: trend {tr or 'N/A'} from recent swing; price near key retracement levels.")

        if snapshot.elliott_wave and snapshot.elliott_wave.get("wave_label"):
            parts.append(f"Elliott Wave: {snapshot.elliott_wave.get('wave_label')} (confidence {snapshot.elliott_wave.get('confidence', 0):.0%}).")

        if getattr(snapshot, "divergences", None) and len(snapshot.divergences) > 0:
            parts.append("Divergence(s) present between price and indicator(s), which can precede reversals.")

        if getattr(snapshot, "patterns", None) and len(snapshot.patterns) > 0:
            parts.append("Chart pattern(s) detected; consider pattern implications for target and invalidation.")

        # Overall and key signals
        parts.append(f"Overall bias is {bias} with {conf:.0%} confidence; technical score {ts}/100 (trend {trend}/100).")
        bullet_signals = [s for s in snapshot.signals if s.signal_type != SignalType.NEUTRAL][:5]
        if bullet_signals:
            parts.append("Key signals: " + "; ".join(s.description or f"{s.indicator} {s.signal_type.value}" for s in bullet_signals) + ".")
        else:
            parts.append("No strong discrete signals; view is driven by indicator levels and structure.")

        summary = " ".join(parts)

        # Call: nuanced thresholds (strong Buy/Sell when score and confidence higher)
        if bias == "Bullish" and conf >= 0.5 and ts >= 55:
            call = "Buy"
            support = []
            if rsi is not None and rsi < 45:
                support.append("oversold or neutral RSI")
            if macd_hist is not None and macd_hist > 0:
                support.append("positive MACD")
            if price is not None and sma200 is not None and price > sma200:
                support.append("price above SMA(200)")
            if snapshot.fibonacci_levels and snapshot.fibonacci_levels.get("trend") == "up":
                support.append("Fibonacci uptrend structure")
            support_str = "; ".join(support) if support else "bias and score"
            contradict = []
            if rsi is not None and rsi > 70:
                contradict.append("RSI overbought—wait for pullback")
            if macd_hist is not None and macd_hist < 0:
                contradict.append("MACD negative—crossover would add conviction")
            rationale = f"Technical score {ts} and {conf:.0%} confidence support a buy. Supporting factors: {support_str}."
            if contradict:
                rationale += f" Mixed: {contradict[0]}."
            rationale += " Consider stop below recent swing low."
        elif bias == "Bearish" and conf >= 0.5 and ts <= 45:
            call = "Sell"
            support = []
            if rsi is not None and rsi > 55:
                support.append("overbought or weak RSI")
            if macd_hist is not None and macd_hist < 0:
                support.append("negative MACD")
            if price is not None and sma200 is not None and price < sma200:
                support.append("price below SMA(200)")
            support_str = "; ".join(support) if support else "bias and score"
            rationale = f"Technical score {ts} and {conf:.0%} confidence suggest caution or reduction. Supporting factors: {support_str}."
            rationale += " Wait for improvement (e.g. RSI oversold or MACD bullish crossover) before adding."
        else:
            call = "Hold"
            rationale = f"Technical picture is mixed or neutral (bias {bias}, score {ts})."
            if rsi is not None or macd_hist is not None:
                mixed = []
                if rsi is not None:
                    mixed.append(f"RSI {rsi:.0f}")
                if macd_hist is not None:
                    mixed.append("MACD " + ("positive" if macd_hist > 0 else "negative"))
                rationale += f" Indicators are mixed ({', '.join(mixed)})."
            rationale += " Wait for clearer alignment of signals or confirmation before committing."

        return summary, call, rationale

    # ===================================================================
    # MULTI-TIMEFRAME ANALYSIS METHODS
    # ===================================================================

    def analyze_symbol_weekly(self, symbol: str) -> TechnicalSnapshot:
        """
        Full technical analysis for one stock using weekly data

        Args:
            symbol: Stock symbol

        Returns:
            TechnicalSnapshot with all indicators computed on weekly timeframe
        """
        # Fetch weekly price data (need 52 weeks for SMA(50))
        df = self.price_store.get_weekly_prices(symbol, weeks=70)

        if df.empty or len(df) < 20:
            # Not enough weekly data for meaningful analysis
            return TechnicalSnapshot(
                symbol=symbol,
                date=datetime.now().strftime('%Y-%m-%d'),
                signals=[],
                overall_bias=SignalType.NEUTRAL,
                confidence=0.0,
                indicator_values={},
                trend_score=50,
                mean_reversion_score=50,
                technical_score=50,
            )

        # Compute all indicators on weekly data
        signals = []
        indicator_values = {}

        latest_date = df.index[-1].strftime('%Y-%m-%d')

        # RSI on weekly
        rsi_signal, rsi_value = self._analyze_rsi(symbol, df, latest_date)
        if rsi_signal:
            signals.append(rsi_signal)
        indicator_values['RSI_Weekly'] = rsi_value

        # MACD on weekly
        macd_signal, macd_values = self._analyze_macd(symbol, df, latest_date)
        if macd_signal:
            signals.append(macd_signal)
        indicator_values['MACD_Weekly'] = macd_values.get('MACD', np.nan)

        # SMA Crossovers on weekly (use smaller periods for weekly)
        sma_signals, sma_values = self._analyze_sma(symbol, df, latest_date)
        signals.extend(sma_signals)
        # Rename SMA values to indicate weekly
        for key, value in sma_values.items():
            indicator_values[f"{key}_Weekly"] = value

        # Fibonacci and Elliott on weekly
        fibonacci_levels = None
        elliott_wave = None
        fib_signals, fib_values, fibonacci_levels = self._analyze_fibonacci(symbol, df, latest_date)
        signals.extend(fib_signals)
        for key, value in fib_values.items():
            indicator_values[f"{key}_Weekly"] = value
        ew_signals, ew_values, elliott_wave = self._analyze_elliott_wave(symbol, df, latest_date)
        signals.extend(ew_signals)
        for key, value in ew_values.items():
            indicator_values[f"{key}_Weekly"] = value

        # Aggregate signals into overall bias
        overall_bias, confidence = self._aggregate_signals(signals)
        current_price_weekly = float(df["Close"].iloc[-1]) if len(df) > 0 else None
        trend_score, mean_reversion_score, technical_score = self._compute_scores(
            signals, indicator_values=indicator_values, current_price=current_price_weekly
        )

        return TechnicalSnapshot(
            symbol=symbol,
            date=latest_date,
            signals=signals,
            overall_bias=overall_bias,
            confidence=confidence,
            indicator_values=indicator_values,
            fibonacci_levels=fibonacci_levels,
            elliott_wave=elliott_wave,
            trend_score=trend_score,
            mean_reversion_score=mean_reversion_score,
            technical_score=technical_score,
        )

    def analyze_multi_timeframe(self, symbol: str) -> MultiTimeframeSnapshot:
        """
        Analyze a stock across multiple timeframes (daily and weekly)

        Args:
            symbol: Stock symbol

        Returns:
            MultiTimeframeSnapshot with daily, weekly, and confirmation analysis
        """
        # Get daily analysis
        daily_snapshot = self.analyze_symbol(symbol)

        # Get weekly analysis
        weekly_snapshot = self.analyze_symbol_weekly(symbol)

        # Calculate confirmation score
        confirmation_score, aligned, conflicting = self._calculate_confirmation_score(
            daily_snapshot, weekly_snapshot
        )

        return MultiTimeframeSnapshot(
            symbol=symbol,
            date=daily_snapshot.date,
            daily=daily_snapshot,
            weekly=weekly_snapshot,
            confirmation_score=confirmation_score,
            aligned_signals=aligned,
            conflicting_signals=conflicting
        )

    def _calculate_confirmation_score(
        self,
        daily: TechnicalSnapshot,
        weekly: TechnicalSnapshot
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate how well daily and weekly signals align

        Args:
            daily: Daily technical snapshot
            weekly: Weekly technical snapshot

        Returns:
            Tuple of (confirmation_score, aligned_signals, conflicting_signals)
            - confirmation_score: 0.0-1.0 where 1.0 = perfect alignment
            - aligned_signals: List of indicators that agree across timeframes
            - conflicting_signals: List of indicators that disagree
        """
        daily_bias = daily.overall_bias
        weekly_bias = weekly.overall_bias

        aligned = []
        conflicting = []

        # Perfect alignment: both bullish or both bearish
        if daily_bias == weekly_bias:
            if daily_bias == SignalType.BULLISH:
                confirmation_score = 1.0
                aligned.append("Both timeframes are BULLISH")
            elif daily_bias == SignalType.BEARISH:
                confirmation_score = 1.0
                aligned.append("Both timeframes are BEARISH")
            else:  # Both neutral
                confirmation_score = 0.5
                aligned.append("Both timeframes are NEUTRAL")

        # Partial alignment: one bullish/bearish, other neutral
        elif daily_bias == SignalType.NEUTRAL or weekly_bias == SignalType.NEUTRAL:
            confirmation_score = 0.7
            if daily_bias == SignalType.NEUTRAL:
                aligned.append(f"Daily neutral, Weekly {weekly_bias.value}")
            else:
                aligned.append(f"Daily {daily_bias.value}, Weekly neutral")

        # Conflicting: bullish vs bearish
        else:
            confirmation_score = 0.3
            conflicting.append(f"Daily {daily_bias.value} vs Weekly {weekly_bias.value}")

        # Add confidence weighting
        avg_confidence = (daily.confidence + weekly.confidence) / 2
        confirmation_score = confirmation_score * (0.7 + 0.3 * avg_confidence)

        # Check for specific indicator alignment
        # RSI alignment
        daily_rsi = daily.indicator_values.get('RSI', np.nan)
        weekly_rsi = weekly.indicator_values.get('RSI_Weekly', np.nan)

        if not pd.isna(daily_rsi) and not pd.isna(weekly_rsi):
            rsi_diff = abs(daily_rsi - weekly_rsi)
            if rsi_diff < 10:
                aligned.append(f"RSI aligned: Daily {daily_rsi:.1f}, Weekly {weekly_rsi:.1f}")
            elif rsi_diff > 30:
                conflicting.append(f"RSI diverging: Daily {daily_rsi:.1f}, Weekly {weekly_rsi:.1f}")

        # Trend alignment (SMA positioning)
        daily_sma50 = daily.indicator_values.get('SMA_50', np.nan)
        daily_sma200 = daily.indicator_values.get('SMA_200', np.nan)
        weekly_sma20 = weekly.indicator_values.get('SMA_20_Weekly', np.nan)
        weekly_sma50 = weekly.indicator_values.get('SMA_50_Weekly', np.nan)

        daily_trend_up = not pd.isna(daily_sma50) and not pd.isna(daily_sma200) and daily_sma50 > daily_sma200
        weekly_trend_up = not pd.isna(weekly_sma20) and not pd.isna(weekly_sma50) and weekly_sma20 > weekly_sma50

        if daily_trend_up and weekly_trend_up:
            aligned.append("Both timeframes in uptrend (SMA)")
        elif not daily_trend_up and not weekly_trend_up:
            aligned.append("Both timeframes in downtrend (SMA)")
        elif daily_trend_up != weekly_trend_up:
            conflicting.append("Trend direction differs between timeframes")

        return confirmation_score, aligned, conflicting


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
