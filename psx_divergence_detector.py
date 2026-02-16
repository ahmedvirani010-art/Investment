"""
PSX Divergence Detector
Detects price vs indicator divergences (bullish/bearish)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DivergenceType(Enum):
    """Type of divergence detected"""
    BULLISH_RSI = "Bullish RSI Divergence"
    BEARISH_RSI = "Bearish RSI Divergence"
    BULLISH_MACD = "Bullish MACD Divergence"
    BEARISH_MACD = "Bearish MACD Divergence"


@dataclass
class Divergence:
    """Detected divergence between price and indicator"""
    symbol: str
    date: str
    divergence_type: DivergenceType
    strength: str  # "Strong" or "Weak"
    price_peaks: List[Tuple[str, float]]  # [(date, price), ...]
    indicator_peaks: List[Tuple[str, float]]  # [(date, indicator_value), ...]
    description: str


class PSXDivergenceDetector:
    """
    Detects divergences between price and technical indicators

    Divergences occur when price and indicators move in opposite directions,
    often signaling potential trend reversals:
    - Bullish divergence: Price makes lower low, indicator makes higher low
    - Bearish divergence: Price makes higher high, indicator makes lower high
    """

    def __init__(self, lookback_days: int = 30, window: int = 5, min_prominence: float = 0.02):
        """
        Initialize divergence detector

        Args:
            lookback_days: Days to look back for divergence patterns
            window: Rolling window for peak/trough detection
            min_prominence: Minimum % change to qualify as peak/trough (default 2%)
        """
        self.lookback_days = lookback_days
        self.window = window
        self.min_prominence = min_prominence

    def _find_peaks(self, series: pd.Series, window: int = None) -> List[int]:
        """
        Find peaks (local maxima) in a series

        Args:
            series: Time series data
            window: Rolling window size (default: use self.window)

        Returns:
            List of indices where peaks occur
        """
        if window is None:
            window = self.window

        if len(series) < window * 2:
            return []

        peaks = []
        half_window = window // 2

        # Use rolling max to identify local maxima
        for i in range(half_window, len(series) - half_window):
            # Check if this point is higher than surrounding points
            window_slice = series.iloc[i - half_window:i + half_window + 1]
            if series.iloc[i] == window_slice.max():
                # Check prominence (must be at least min_prominence % higher than average)
                avg_surrounding = window_slice.mean()
                if series.iloc[i] > avg_surrounding * (1 + self.min_prominence):
                    peaks.append(i)

        # Remove adjacent peaks (keep only the highest within window distance)
        if len(peaks) > 1:
            filtered_peaks = [peaks[0]]
            for peak in peaks[1:]:
                if peak - filtered_peaks[-1] < window:
                    # Adjacent peaks - keep the higher one
                    if series.iloc[peak] > series.iloc[filtered_peaks[-1]]:
                        filtered_peaks[-1] = peak
                else:
                    filtered_peaks.append(peak)
            peaks = filtered_peaks

        return peaks

    def _find_troughs(self, series: pd.Series, window: int = None) -> List[int]:
        """
        Find troughs (local minima) in a series

        Args:
            series: Time series data
            window: Rolling window size (default: use self.window)

        Returns:
            List of indices where troughs occur
        """
        if window is None:
            window = self.window

        if len(series) < window * 2:
            return []

        troughs = []
        half_window = window // 2

        # Use rolling min to identify local minima
        for i in range(half_window, len(series) - half_window):
            # Check if this point is lower than surrounding points
            window_slice = series.iloc[i - half_window:i + half_window + 1]
            if series.iloc[i] == window_slice.min():
                # Check prominence (must be at least min_prominence % lower than average)
                avg_surrounding = window_slice.mean()
                if series.iloc[i] < avg_surrounding * (1 - self.min_prominence):
                    troughs.append(i)

        # Remove adjacent troughs (keep only the lowest within window distance)
        if len(troughs) > 1:
            filtered_troughs = [troughs[0]]
            for trough in troughs[1:]:
                if trough - filtered_troughs[-1] < window:
                    # Adjacent troughs - keep the lower one
                    if series.iloc[trough] < series.iloc[filtered_troughs[-1]]:
                        filtered_troughs[-1] = trough
                else:
                    filtered_troughs.append(trough)
            troughs = filtered_troughs

        return troughs

    def detect_rsi_divergence(self, df: pd.DataFrame) -> List[Divergence]:
        """
        Detect divergences between price and RSI

        Args:
            df: DataFrame with Close prices and RSI computed

        Returns:
            List of Divergence objects
        """
        divergences = []

        if len(df) < self.lookback_days or 'RSI' not in df.columns:
            return divergences

        # Use only recent data
        recent_df = df.tail(self.lookback_days).copy()

        # Find peaks and troughs in price
        price_peaks = self._find_peaks(recent_df['Close'])
        price_troughs = self._find_troughs(recent_df['Close'])

        # Find peaks and troughs in RSI
        rsi_peaks = self._find_peaks(recent_df['RSI'])
        rsi_troughs = self._find_troughs(recent_df['RSI'])

        symbol = df.attrs.get('symbol', 'UNKNOWN')
        latest_date = recent_df.index[-1].strftime('%Y-%m-%d')

        # Bullish RSI Divergence: Price lower low + RSI higher low
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            # Compare last two troughs
            last_price_trough_idx = price_troughs[-1]
            prev_price_trough_idx = price_troughs[-2]
            last_price_trough = recent_df['Close'].iloc[last_price_trough_idx]
            prev_price_trough = recent_df['Close'].iloc[prev_price_trough_idx]

            # Find closest RSI troughs
            last_rsi_trough_idx = rsi_troughs[-1]
            prev_rsi_trough_idx = rsi_troughs[-2] if len(rsi_troughs) >= 2 else rsi_troughs[-1]
            last_rsi_trough = recent_df['RSI'].iloc[last_rsi_trough_idx]
            prev_rsi_trough = recent_df['RSI'].iloc[prev_rsi_trough_idx]

            # Check for bullish divergence
            if last_price_trough < prev_price_trough and last_rsi_trough > prev_rsi_trough:
                strength = "Strong" if (prev_rsi_trough - last_rsi_trough) > 5 else "Weak"
                divergences.append(Divergence(
                    symbol=symbol,
                    date=latest_date,
                    divergence_type=DivergenceType.BULLISH_RSI,
                    strength=strength,
                    price_peaks=[
                        (recent_df.index[prev_price_trough_idx].strftime('%Y-%m-%d'), prev_price_trough),
                        (recent_df.index[last_price_trough_idx].strftime('%Y-%m-%d'), last_price_trough)
                    ],
                    indicator_peaks=[
                        (recent_df.index[prev_rsi_trough_idx].strftime('%Y-%m-%d'), prev_rsi_trough),
                        (recent_df.index[last_rsi_trough_idx].strftime('%Y-%m-%d'), last_rsi_trough)
                    ],
                    description=f"Price lower low ({prev_price_trough:.2f} → {last_price_trough:.2f}), "
                               f"RSI higher low ({prev_rsi_trough:.1f} → {last_rsi_trough:.1f})"
                ))

        # Bearish RSI Divergence: Price higher high + RSI lower high
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            # Compare last two peaks
            last_price_peak_idx = price_peaks[-1]
            prev_price_peak_idx = price_peaks[-2]
            last_price_peak = recent_df['Close'].iloc[last_price_peak_idx]
            prev_price_peak = recent_df['Close'].iloc[prev_price_peak_idx]

            # Find closest RSI peaks
            last_rsi_peak_idx = rsi_peaks[-1]
            prev_rsi_peak_idx = rsi_peaks[-2] if len(rsi_peaks) >= 2 else rsi_peaks[-1]
            last_rsi_peak = recent_df['RSI'].iloc[last_rsi_peak_idx]
            prev_rsi_peak = recent_df['RSI'].iloc[prev_rsi_peak_idx]

            # Check for bearish divergence
            if last_price_peak > prev_price_peak and last_rsi_peak < prev_rsi_peak:
                strength = "Strong" if (prev_rsi_peak - last_rsi_peak) > 5 else "Weak"
                divergences.append(Divergence(
                    symbol=symbol,
                    date=latest_date,
                    divergence_type=DivergenceType.BEARISH_RSI,
                    strength=strength,
                    price_peaks=[
                        (recent_df.index[prev_price_peak_idx].strftime('%Y-%m-%d'), prev_price_peak),
                        (recent_df.index[last_price_peak_idx].strftime('%Y-%m-%d'), last_price_peak)
                    ],
                    indicator_peaks=[
                        (recent_df.index[prev_rsi_peak_idx].strftime('%Y-%m-%d'), prev_rsi_peak),
                        (recent_df.index[last_rsi_peak_idx].strftime('%Y-%m-%d'), last_rsi_peak)
                    ],
                    description=f"Price higher high ({prev_price_peak:.2f} → {last_price_peak:.2f}), "
                               f"RSI lower high ({prev_rsi_peak:.1f} → {last_rsi_peak:.1f})"
                ))

        return divergences

    def detect_macd_divergence(self, df: pd.DataFrame) -> List[Divergence]:
        """
        Detect divergences between price and MACD

        Args:
            df: DataFrame with Close prices and MACD computed

        Returns:
            List of Divergence objects
        """
        divergences = []

        if len(df) < self.lookback_days or 'MACD' not in df.columns:
            return divergences

        # Use only recent data
        recent_df = df.tail(self.lookback_days).copy()

        # Find peaks and troughs in price
        price_peaks = self._find_peaks(recent_df['Close'])
        price_troughs = self._find_troughs(recent_df['Close'])

        # Find peaks and troughs in MACD
        macd_peaks = self._find_peaks(recent_df['MACD'])
        macd_troughs = self._find_troughs(recent_df['MACD'])

        symbol = df.attrs.get('symbol', 'UNKNOWN')
        latest_date = recent_df.index[-1].strftime('%Y-%m-%d')

        # Bullish MACD Divergence: Price lower low + MACD higher low
        if len(price_troughs) >= 2 and len(macd_troughs) >= 2:
            last_price_trough_idx = price_troughs[-1]
            prev_price_trough_idx = price_troughs[-2]
            last_price_trough = recent_df['Close'].iloc[last_price_trough_idx]
            prev_price_trough = recent_df['Close'].iloc[prev_price_trough_idx]

            last_macd_trough_idx = macd_troughs[-1]
            prev_macd_trough_idx = macd_troughs[-2] if len(macd_troughs) >= 2 else macd_troughs[-1]
            last_macd_trough = recent_df['MACD'].iloc[last_macd_trough_idx]
            prev_macd_trough = recent_df['MACD'].iloc[prev_macd_trough_idx]

            # Check for bullish divergence
            if last_price_trough < prev_price_trough and last_macd_trough > prev_macd_trough:
                strength = "Strong" if abs(prev_macd_trough - last_macd_trough) > 0.5 else "Weak"
                divergences.append(Divergence(
                    symbol=symbol,
                    date=latest_date,
                    divergence_type=DivergenceType.BULLISH_MACD,
                    strength=strength,
                    price_peaks=[
                        (recent_df.index[prev_price_trough_idx].strftime('%Y-%m-%d'), prev_price_trough),
                        (recent_df.index[last_price_trough_idx].strftime('%Y-%m-%d'), last_price_trough)
                    ],
                    indicator_peaks=[
                        (recent_df.index[prev_macd_trough_idx].strftime('%Y-%m-%d'), prev_macd_trough),
                        (recent_df.index[last_macd_trough_idx].strftime('%Y-%m-%d'), last_macd_trough)
                    ],
                    description=f"Price lower low ({prev_price_trough:.2f} → {last_price_trough:.2f}), "
                               f"MACD higher low ({prev_macd_trough:.2f} → {last_macd_trough:.2f})"
                ))

        # Bearish MACD Divergence: Price higher high + MACD lower high
        if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
            last_price_peak_idx = price_peaks[-1]
            prev_price_peak_idx = price_peaks[-2]
            last_price_peak = recent_df['Close'].iloc[last_price_peak_idx]
            prev_price_peak = recent_df['Close'].iloc[prev_price_peak_idx]

            last_macd_peak_idx = macd_peaks[-1]
            prev_macd_peak_idx = macd_peaks[-2] if len(macd_peaks) >= 2 else macd_peaks[-1]
            last_macd_peak = recent_df['MACD'].iloc[last_macd_peak_idx]
            prev_macd_peak = recent_df['MACD'].iloc[prev_macd_peak_idx]

            # Check for bearish divergence
            if last_price_peak > prev_price_peak and last_macd_peak < prev_macd_peak:
                strength = "Strong" if abs(prev_macd_peak - last_macd_peak) > 0.5 else "Weak"
                divergences.append(Divergence(
                    symbol=symbol,
                    date=latest_date,
                    divergence_type=DivergenceType.BEARISH_MACD,
                    strength=strength,
                    price_peaks=[
                        (recent_df.index[prev_price_peak_idx].strftime('%Y-%m-%d'), prev_price_peak),
                        (recent_df.index[last_price_peak_idx].strftime('%Y-%m-%d'), last_price_peak)
                    ],
                    indicator_peaks=[
                        (recent_df.index[prev_macd_peak_idx].strftime('%Y-%m-%d'), prev_macd_peak),
                        (recent_df.index[last_macd_peak_idx].strftime('%Y-%m-%d'), last_macd_peak)
                    ],
                    description=f"Price higher high ({prev_price_peak:.2f} → {last_price_peak:.2f}), "
                               f"MACD lower high ({prev_macd_peak:.2f} → {last_macd_peak:.2f})"
                ))

        return divergences

    def detect_all_divergences(self, symbol: str, df: pd.DataFrame) -> List[Divergence]:
        """
        Detect all divergences (RSI and MACD) for a symbol

        Args:
            symbol: Stock symbol
            df: DataFrame with price data and computed indicators

        Returns:
            List of all detected divergences
        """
        # Store symbol in DataFrame attrs for reference
        df.attrs['symbol'] = symbol

        divergences = []

        # Detect RSI divergences
        try:
            rsi_divs = self.detect_rsi_divergence(df)
            divergences.extend(rsi_divs)
        except Exception as e:
            print(f"  Warning: Error detecting RSI divergence for {symbol}: {str(e)}")

        # Detect MACD divergences
        try:
            macd_divs = self.detect_macd_divergence(df)
            divergences.extend(macd_divs)
        except Exception as e:
            print(f"  Warning: Error detecting MACD divergence for {symbol}: {str(e)}")

        return divergences
