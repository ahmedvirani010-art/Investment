"""
PSX Pattern Recognizer
Detects classic chart patterns (Head & Shoulders, Double Tops/Bottoms)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    """Type of chart pattern detected"""
    HEAD_SHOULDERS = "Head and Shoulders"
    INV_HEAD_SHOULDERS = "Inverse Head and Shoulders"
    DOUBLE_TOP = "Double Top"
    DOUBLE_BOTTOM = "Double Bottom"


class PatternStatus(Enum):
    """Status of the pattern"""
    FORMING = "Forming"
    CONFIRMED = "Confirmed"
    BROKEN = "Broken"


@dataclass
class ChartPattern:
    """Detected chart pattern"""
    symbol: str
    pattern_type: PatternType
    status: PatternStatus
    start_date: str
    end_date: str
    key_points: Dict[str, Tuple[str, float]]  # {label: (date, price)}
    neckline: Optional[float] = None
    target_price: Optional[float] = None
    description: str = ""


class PSXPatternRecognizer:
    """
    Detects classic chart patterns for trend reversal analysis

    Patterns detected:
    - Head & Shoulders (bearish): Three peaks with center peak highest
    - Inverse Head & Shoulders (bullish): Three troughs with center trough lowest
    - Double Top (bearish): Two peaks at similar level
    - Double Bottom (bullish): Two troughs at similar level
    """

    def __init__(
        self,
        hs_lookback_days: int = 60,
        hs_min_pattern_days: int = 20,
        hs_head_prominence: float = 0.03,
        hs_shoulder_tolerance: float = 0.05,
        dt_lookback_days: int = 50,
        dt_peak_tolerance: float = 0.03,
        dt_min_trough_depth: float = 0.05,
        dt_max_pattern_days: int = 40
    ):
        """
        Initialize pattern recognizer

        Args:
            hs_lookback_days: Days to look back for H&S patterns
            hs_min_pattern_days: Minimum days for H&S pattern formation
            hs_head_prominence: Min % head must be above shoulders (3%)
            hs_shoulder_tolerance: Max % difference between shoulders (5%)
            dt_lookback_days: Days to look back for double tops/bottoms
            dt_peak_tolerance: Max % difference between peaks (3%)
            dt_min_trough_depth: Min % depth of trough between peaks (5%)
            dt_max_pattern_days: Max days between peaks (40)
        """
        self.hs_lookback_days = hs_lookback_days
        self.hs_min_pattern_days = hs_min_pattern_days
        self.hs_head_prominence = hs_head_prominence
        self.hs_shoulder_tolerance = hs_shoulder_tolerance

        self.dt_lookback_days = dt_lookback_days
        self.dt_peak_tolerance = dt_peak_tolerance
        self.dt_min_trough_depth = dt_min_trough_depth
        self.dt_max_pattern_days = dt_max_pattern_days

    def _find_peak_sequence(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """
        Find sequence of peaks (local maxima) in price data

        Args:
            df: DataFrame with Close prices
            window: Rolling window for peak detection

        Returns:
            List of (index, price) tuples for peaks
        """
        if len(df) < window * 2:
            return []

        peaks = []
        half_window = window // 2

        for i in range(half_window, len(df) - half_window):
            window_slice = df['Close'].iloc[i - half_window:i + half_window + 1]
            if df['Close'].iloc[i] == window_slice.max():
                # Check prominence (at least 2% higher than average)
                avg_surrounding = window_slice.mean()
                if df['Close'].iloc[i] > avg_surrounding * 1.02:
                    peaks.append((i, df['Close'].iloc[i]))

        # Filter adjacent peaks (keep highest within window distance)
        if len(peaks) > 1:
            filtered_peaks = [peaks[0]]
            for peak_idx, peak_price in peaks[1:]:
                last_idx, last_price = filtered_peaks[-1]
                if peak_idx - last_idx < window:
                    # Adjacent - keep higher
                    if peak_price > last_price:
                        filtered_peaks[-1] = (peak_idx, peak_price)
                else:
                    filtered_peaks.append((peak_idx, peak_price))
            peaks = filtered_peaks

        return peaks

    def _find_trough_sequence(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """
        Find sequence of troughs (local minima) in price data

        Args:
            df: DataFrame with Close prices
            window: Rolling window for trough detection

        Returns:
            List of (index, price) tuples for troughs
        """
        if len(df) < window * 2:
            return []

        troughs = []
        half_window = window // 2

        for i in range(half_window, len(df) - half_window):
            window_slice = df['Close'].iloc[i - half_window:i + half_window + 1]
            if df['Close'].iloc[i] == window_slice.min():
                # Check prominence (at least 2% lower than average)
                avg_surrounding = window_slice.mean()
                if df['Close'].iloc[i] < avg_surrounding * 0.98:
                    troughs.append((i, df['Close'].iloc[i]))

        # Filter adjacent troughs (keep lowest within window distance)
        if len(troughs) > 1:
            filtered_troughs = [troughs[0]]
            for trough_idx, trough_price in troughs[1:]:
                last_idx, last_price = filtered_troughs[-1]
                if trough_idx - last_idx < window:
                    # Adjacent - keep lower
                    if trough_price < last_price:
                        filtered_troughs[-1] = (trough_idx, trough_price)
                else:
                    filtered_troughs.append((trough_idx, trough_price))
            troughs = filtered_troughs

        return troughs

    def _calculate_neckline(self, trough1: Tuple[int, float], trough2: Tuple[int, float]) -> float:
        """
        Calculate neckline level (average of two troughs)

        Args:
            trough1: First trough (index, price)
            trough2: Second trough (index, price)

        Returns:
            Neckline price level
        """
        _, price1 = trough1
        _, price2 = trough2
        return (price1 + price2) / 2

    def detect_head_and_shoulders(self, df: pd.DataFrame) -> List[ChartPattern]:
        """
        Detect Head and Shoulders pattern (bearish)

        Pattern structure:
        - Left shoulder (peak)
        - Head (higher peak)
        - Right shoulder (peak similar to left)
        - Neckline (line connecting troughs)

        Args:
            df: DataFrame with price data

        Returns:
            List of detected H&S patterns
        """
        patterns = []

        if len(df) < self.hs_lookback_days:
            return patterns

        # Use recent data
        recent_df = df.tail(self.hs_lookback_days).reset_index(drop=False)
        symbol = df.attrs.get('symbol', 'UNKNOWN')

        # Find peaks and troughs
        peaks = self._find_peak_sequence(recent_df, window=5)
        troughs = self._find_trough_sequence(recent_df, window=5)

        if len(peaks) < 3 or len(troughs) < 2:
            return patterns

        # Look for H&S pattern: 3 consecutive peaks where middle is highest
        for i in range(len(peaks) - 2):
            left_shoulder_idx, left_shoulder_price = peaks[i]
            head_idx, head_price = peaks[i + 1]
            right_shoulder_idx, right_shoulder_price = peaks[i + 2]

            # Check pattern validity:
            # 1. Head must be higher than both shoulders
            if head_price <= left_shoulder_price or head_price <= right_shoulder_price:
                continue

            # 2. Head must be at least hs_head_prominence % higher
            if head_price < left_shoulder_price * (1 + self.hs_head_prominence):
                continue

            # 3. Shoulders must be within hs_shoulder_tolerance % of each other
            shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / left_shoulder_price
            if shoulder_diff > self.hs_shoulder_tolerance:
                continue

            # 4. Pattern must span at least hs_min_pattern_days days
            pattern_days = right_shoulder_idx - left_shoulder_idx
            if pattern_days < self.hs_min_pattern_days:
                continue

            # Find troughs between peaks (for neckline)
            trough1 = None
            trough2 = None
            for t_idx, t_price in troughs:
                if left_shoulder_idx < t_idx < head_idx and trough1 is None:
                    trough1 = (t_idx, t_price)
                elif head_idx < t_idx < right_shoulder_idx and trough2 is None:
                    trough2 = (t_idx, t_price)

            if trough1 is None or trough2 is None:
                continue

            # Calculate neckline
            neckline = self._calculate_neckline(trough1, trough2)

            # Determine status: Forming if price > neckline, Confirmed if broken
            current_price = recent_df['Close'].iloc[-1]
            if current_price < neckline:
                status = PatternStatus.CONFIRMED
            else:
                status = PatternStatus.FORMING

            # Calculate target (head to neckline distance projected down)
            target_distance = head_price - neckline
            target_price = neckline - target_distance

            # Dates
            start_date = recent_df.iloc[left_shoulder_idx]['date'].strftime('%Y-%m-%d')
            end_date = recent_df.iloc[right_shoulder_idx]['date'].strftime('%Y-%m-%d')
            latest_date = recent_df.iloc[-1]['date'].strftime('%Y-%m-%d')

            patterns.append(ChartPattern(
                symbol=symbol,
                pattern_type=PatternType.HEAD_SHOULDERS,
                status=status,
                start_date=start_date,
                end_date=end_date,
                key_points={
                    'left_shoulder': (recent_df.iloc[left_shoulder_idx]['date'].strftime('%Y-%m-%d'), left_shoulder_price),
                    'head': (recent_df.iloc[head_idx]['date'].strftime('%Y-%m-%d'), head_price),
                    'right_shoulder': (recent_df.iloc[right_shoulder_idx]['date'].strftime('%Y-%m-%d'), right_shoulder_price),
                    'trough1': (recent_df.iloc[trough1[0]]['date'].strftime('%Y-%m-%d'), trough1[1]),
                    'trough2': (recent_df.iloc[trough2[0]]['date'].strftime('%Y-%m-%d'), trough2[1])
                },
                neckline=neckline,
                target_price=target_price,
                description=f"Bearish H&S: Head at {head_price:.2f}, Neckline at {neckline:.2f}, Target {target_price:.2f}"
            ))

        return patterns

    def detect_inverse_head_and_shoulders(self, df: pd.DataFrame) -> List[ChartPattern]:
        """
        Detect Inverse Head and Shoulders pattern (bullish)

        Pattern structure (mirror of H&S):
        - Left shoulder (trough)
        - Head (lower trough)
        - Right shoulder (trough similar to left)
        - Neckline (line connecting peaks)

        Args:
            df: DataFrame with price data

        Returns:
            List of detected Inverse H&S patterns
        """
        patterns = []

        if len(df) < self.hs_lookback_days:
            return patterns

        # Use recent data
        recent_df = df.tail(self.hs_lookback_days).reset_index(drop=False)
        symbol = df.attrs.get('symbol', 'UNKNOWN')

        # Find peaks and troughs
        peaks = self._find_peak_sequence(recent_df, window=5)
        troughs = self._find_trough_sequence(recent_df, window=5)

        if len(troughs) < 3 or len(peaks) < 2:
            return patterns

        # Look for Inverse H&S: 3 consecutive troughs where middle is lowest
        for i in range(len(troughs) - 2):
            left_shoulder_idx, left_shoulder_price = troughs[i]
            head_idx, head_price = troughs[i + 1]
            right_shoulder_idx, right_shoulder_price = troughs[i + 2]

            # Check pattern validity:
            # 1. Head must be lower than both shoulders
            if head_price >= left_shoulder_price or head_price >= right_shoulder_price:
                continue

            # 2. Head must be at least hs_head_prominence % lower
            if head_price > left_shoulder_price * (1 - self.hs_head_prominence):
                continue

            # 3. Shoulders must be within hs_shoulder_tolerance % of each other
            shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / left_shoulder_price
            if shoulder_diff > self.hs_shoulder_tolerance:
                continue

            # 4. Pattern must span at least hs_min_pattern_days days
            pattern_days = right_shoulder_idx - left_shoulder_idx
            if pattern_days < self.hs_min_pattern_days:
                continue

            # Find peaks between troughs (for neckline)
            peak1 = None
            peak2 = None
            for p_idx, p_price in peaks:
                if left_shoulder_idx < p_idx < head_idx and peak1 is None:
                    peak1 = (p_idx, p_price)
                elif head_idx < p_idx < right_shoulder_idx and peak2 is None:
                    peak2 = (p_idx, p_price)

            if peak1 is None or peak2 is None:
                continue

            # Calculate neckline (average of two peaks)
            neckline = (peak1[1] + peak2[1]) / 2

            # Determine status: Forming if price < neckline, Confirmed if broken
            current_price = recent_df['Close'].iloc[-1]
            if current_price > neckline:
                status = PatternStatus.CONFIRMED
            else:
                status = PatternStatus.FORMING

            # Calculate target (neckline to head distance projected up)
            target_distance = neckline - head_price
            target_price = neckline + target_distance

            # Dates
            start_date = recent_df.iloc[left_shoulder_idx]['date'].strftime('%Y-%m-%d')
            end_date = recent_df.iloc[right_shoulder_idx]['date'].strftime('%Y-%m-%d')

            patterns.append(ChartPattern(
                symbol=symbol,
                pattern_type=PatternType.INV_HEAD_SHOULDERS,
                status=status,
                start_date=start_date,
                end_date=end_date,
                key_points={
                    'left_shoulder': (recent_df.iloc[left_shoulder_idx]['date'].strftime('%Y-%m-%d'), left_shoulder_price),
                    'head': (recent_df.iloc[head_idx]['date'].strftime('%Y-%m-%d'), head_price),
                    'right_shoulder': (recent_df.iloc[right_shoulder_idx]['date'].strftime('%Y-%m-%d'), right_shoulder_price),
                    'peak1': (recent_df.iloc[peak1[0]]['date'].strftime('%Y-%m-%d'), peak1[1]),
                    'peak2': (recent_df.iloc[peak2[0]]['date'].strftime('%Y-%m-%d'), peak2[1])
                },
                neckline=neckline,
                target_price=target_price,
                description=f"Bullish Inv H&S: Head at {head_price:.2f}, Neckline at {neckline:.2f}, Target {target_price:.2f}"
            ))

        return patterns

    def detect_double_top(self, df: pd.DataFrame) -> List[ChartPattern]:
        """
        Detect Double Top pattern (bearish)

        Pattern structure:
        - Two peaks at similar price level
        - Trough between peaks (at least dt_min_trough_depth % deep)
        - Confirmed on break below trough

        Args:
            df: DataFrame with price data

        Returns:
            List of detected Double Top patterns
        """
        patterns = []

        if len(df) < self.dt_lookback_days:
            return patterns

        # Use recent data
        recent_df = df.tail(self.dt_lookback_days).reset_index(drop=False)
        symbol = df.attrs.get('symbol', 'UNKNOWN')

        # Find peaks and troughs
        peaks = self._find_peak_sequence(recent_df, window=5)
        troughs = self._find_trough_sequence(recent_df, window=5)

        if len(peaks) < 2:
            return patterns

        # Look for double top: two peaks at similar level
        for i in range(len(peaks) - 1):
            peak1_idx, peak1_price = peaks[i]
            peak2_idx, peak2_price = peaks[i + 1]

            # Check pattern validity:
            # 1. Peaks must be within dt_peak_tolerance % of each other
            peak_diff = abs(peak1_price - peak2_price) / peak1_price
            if peak_diff > self.dt_peak_tolerance:
                continue

            # 2. Pattern must be within dt_max_pattern_days days
            pattern_days = peak2_idx - peak1_idx
            if pattern_days > self.dt_max_pattern_days:
                continue

            # 3. Find trough between peaks
            trough_between = None
            for t_idx, t_price in troughs:
                if peak1_idx < t_idx < peak2_idx:
                    if trough_between is None or t_price < trough_between[1]:
                        trough_between = (t_idx, t_price)

            if trough_between is None:
                continue

            # 4. Trough must be at least dt_min_trough_depth % below peaks
            avg_peak_price = (peak1_price + peak2_price) / 2
            trough_depth = (avg_peak_price - trough_between[1]) / avg_peak_price
            if trough_depth < self.dt_min_trough_depth:
                continue

            # Determine status: Forming if price > trough, Confirmed if broken
            current_price = recent_df['Close'].iloc[-1]
            if current_price < trough_between[1]:
                status = PatternStatus.CONFIRMED
            else:
                status = PatternStatus.FORMING

            # Calculate target (peak to trough distance projected down)
            target_distance = avg_peak_price - trough_between[1]
            target_price = trough_between[1] - target_distance

            # Dates
            start_date = recent_df.iloc[peak1_idx]['date'].strftime('%Y-%m-%d')
            end_date = recent_df.iloc[peak2_idx]['date'].strftime('%Y-%m-%d')

            patterns.append(ChartPattern(
                symbol=symbol,
                pattern_type=PatternType.DOUBLE_TOP,
                status=status,
                start_date=start_date,
                end_date=end_date,
                key_points={
                    'peak1': (recent_df.iloc[peak1_idx]['date'].strftime('%Y-%m-%d'), peak1_price),
                    'peak2': (recent_df.iloc[peak2_idx]['date'].strftime('%Y-%m-%d'), peak2_price),
                    'trough': (recent_df.iloc[trough_between[0]]['date'].strftime('%Y-%m-%d'), trough_between[1])
                },
                neckline=trough_between[1],  # Neckline is the trough level
                target_price=target_price,
                description=f"Bearish Double Top: Peaks at {avg_peak_price:.2f}, Support at {trough_between[1]:.2f}, Target {target_price:.2f}"
            ))

        return patterns

    def detect_double_bottom(self, df: pd.DataFrame) -> List[ChartPattern]:
        """
        Detect Double Bottom pattern (bullish)

        Pattern structure:
        - Two troughs at similar price level
        - Peak between troughs (at least dt_min_trough_depth % high)
        - Confirmed on break above peak

        Args:
            df: DataFrame with price data

        Returns:
            List of detected Double Bottom patterns
        """
        patterns = []

        if len(df) < self.dt_lookback_days:
            return patterns

        # Use recent data
        recent_df = df.tail(self.dt_lookback_days).reset_index(drop=False)
        symbol = df.attrs.get('symbol', 'UNKNOWN')

        # Find peaks and troughs
        peaks = self._find_peak_sequence(recent_df, window=5)
        troughs = self._find_trough_sequence(recent_df, window=5)

        if len(troughs) < 2:
            return patterns

        # Look for double bottom: two troughs at similar level
        for i in range(len(troughs) - 1):
            trough1_idx, trough1_price = troughs[i]
            trough2_idx, trough2_price = troughs[i + 1]

            # Check pattern validity:
            # 1. Troughs must be within dt_peak_tolerance % of each other
            trough_diff = abs(trough1_price - trough2_price) / trough1_price
            if trough_diff > self.dt_peak_tolerance:
                continue

            # 2. Pattern must be within dt_max_pattern_days days
            pattern_days = trough2_idx - trough1_idx
            if pattern_days > self.dt_max_pattern_days:
                continue

            # 3. Find peak between troughs
            peak_between = None
            for p_idx, p_price in peaks:
                if trough1_idx < p_idx < trough2_idx:
                    if peak_between is None or p_price > peak_between[1]:
                        peak_between = (p_idx, p_price)

            if peak_between is None:
                continue

            # 4. Peak must be at least dt_min_trough_depth % above troughs
            avg_trough_price = (trough1_price + trough2_price) / 2
            peak_height = (peak_between[1] - avg_trough_price) / avg_trough_price
            if peak_height < self.dt_min_trough_depth:
                continue

            # Determine status: Forming if price < peak, Confirmed if broken
            current_price = recent_df['Close'].iloc[-1]
            if current_price > peak_between[1]:
                status = PatternStatus.CONFIRMED
            else:
                status = PatternStatus.FORMING

            # Calculate target (trough to peak distance projected up)
            target_distance = peak_between[1] - avg_trough_price
            target_price = peak_between[1] + target_distance

            # Dates
            start_date = recent_df.iloc[trough1_idx]['date'].strftime('%Y-%m-%d')
            end_date = recent_df.iloc[trough2_idx]['date'].strftime('%Y-%m-%d')

            patterns.append(ChartPattern(
                symbol=symbol,
                pattern_type=PatternType.DOUBLE_BOTTOM,
                status=status,
                start_date=start_date,
                end_date=end_date,
                key_points={
                    'trough1': (recent_df.iloc[trough1_idx]['date'].strftime('%Y-%m-%d'), trough1_price),
                    'trough2': (recent_df.iloc[trough2_idx]['date'].strftime('%Y-%m-%d'), trough2_price),
                    'peak': (recent_df.iloc[peak_between[0]]['date'].strftime('%Y-%m-%d'), peak_between[1])
                },
                neckline=peak_between[1],  # Neckline is the peak level
                target_price=target_price,
                description=f"Bullish Double Bottom: Troughs at {avg_trough_price:.2f}, Resistance at {peak_between[1]:.2f}, Target {target_price:.2f}"
            ))

        return patterns

    def detect_all_patterns(self, symbol: str, df: pd.DataFrame) -> List[ChartPattern]:
        """
        Detect all chart patterns for a symbol

        Args:
            symbol: Stock symbol
            df: DataFrame with price data

        Returns:
            List of all detected patterns
        """
        # Store symbol in DataFrame attrs for reference
        df.attrs['symbol'] = symbol

        patterns = []

        # Detect Head & Shoulders
        try:
            hs_patterns = self.detect_head_and_shoulders(df)
            patterns.extend(hs_patterns)
        except Exception as e:
            print(f"  Warning: Error detecting H&S for {symbol}: {str(e)}")

        # Detect Inverse Head & Shoulders
        try:
            inv_hs_patterns = self.detect_inverse_head_and_shoulders(df)
            patterns.extend(inv_hs_patterns)
        except Exception as e:
            print(f"  Warning: Error detecting Inverse H&S for {symbol}: {str(e)}")

        # Detect Double Top
        try:
            dt_patterns = self.detect_double_top(df)
            patterns.extend(dt_patterns)
        except Exception as e:
            print(f"  Warning: Error detecting Double Top for {symbol}: {str(e)}")

        # Detect Double Bottom
        try:
            db_patterns = self.detect_double_bottom(df)
            patterns.extend(db_patterns)
        except Exception as e:
            print(f"  Warning: Error detecting Double Bottom for {symbol}: {str(e)}")

        return patterns
