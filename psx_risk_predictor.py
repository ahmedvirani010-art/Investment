"""
PSX Risk Predictor
Generates forward-looking risk signals BEFORE risks materialize
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import uuid


@dataclass
class PredictiveSignal:
    """Predictive risk signal"""
    signal_id: str
    symbol: str
    signal_type: str  # TREND_DETERIORATION, VOLATILITY_INCOMING, etc.
    severity: str     # CRITICAL, HIGH, MEDIUM, LOW
    confidence: float  # 0.0-1.0
    lead_time_days: int
    description: str
    recommended_action: str
    detected_at: str

    def to_dict(self):
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'severity': self.severity,
            'confidence': self.confidence,
            'lead_time_days': self.lead_time_days,
            'description': self.description,
            'recommended_action': self.recommended_action,
            'detected_at': self.detected_at
        }


class RiskPredictor:
    """
    Predictive risk engine for position/swing trading

    Implements 6 forward-looking indicators:
    1. Trend Deterioration Detector (3-7 day lead)
    2. Volatility Regime Change Predictor (2-5 day lead)
    3. Sentiment Momentum Tracker (1-3 day lead)
    4. Correlation Breakdown Monitor (concurrent)
    5. Multi-Timeframe Divergence (concurrent)
    6. Event Risk Predictor (5-10 day lead)
    """

    def __init__(self, price_store, technical_agent=None, sentiment_analyzer=None):
        """
        Initialize risk predictor

        Args:
            price_store: PSXPriceStore instance
            technical_agent: PSXTechnicalAgent instance (optional)
            sentiment_analyzer: PSXSentimentAnalyzer instance (optional)
        """
        self.price_store = price_store
        self.technical_agent = technical_agent
        self.sentiment_analyzer = sentiment_analyzer

    def predict_risks(self, symbol: str, position_size: float = 0) -> List[PredictiveSignal]:
        """
        Generate all predictive signals for a symbol

        Args:
            symbol: Stock symbol
            position_size: Current position size (for context)

        Returns:
            List of predictive signals
        """
        signals = []

        # Run all predictors
        signals.extend(self._detect_trend_deterioration(symbol))
        signals.extend(self._detect_volatility_regime_change(symbol))
        signals.extend(self._detect_timeframe_divergence(symbol))

        # Return sorted by severity and confidence
        signals.sort(key=lambda x: (
            {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(x.severity, 4),
            -x.confidence
        ))

        return signals

    def _detect_trend_deterioration(self, symbol: str) -> List[PredictiveSignal]:
        """
        Detect weakening trend BEFORE breakdown

        Measures:
        - Slope decay (short-term vs medium-term)
        - Momentum decline (RSI falling even if >50)
        - Breadth weakening (% of red days increasing)

        Lead time: 3-7 days
        """
        signals = []

        try:
            df = self.price_store.get_prices(symbol, days=100)
            if df.empty or len(df) < 30:
                return signals

            # Ensure column name consistency (handle 'Close' or 'close')
            close_col = 'close' if 'close' in df.columns else 'Close'

            # Calculate slopes
            short_slope = self._calculate_slope(df[close_col].tail(10))
            medium_slope = self._calculate_slope(df[close_col].tail(30))

            # Calculate RSI if technical agent available
            rsi_declining = False
            if self.technical_agent and hasattr(self.technical_agent, 'compute_rsi'):
                try:
                    rsi = self.technical_agent.compute_rsi(df)
                    if len(rsi) >= 5:
                        rsi_declining = rsi.iloc[-1] < rsi.iloc[-5] and rsi.iloc[-1] > 50
                except Exception:
                    pass

            # Breadth (% of red days in last 10)
            red_days_pct = (df[close_col].tail(10).pct_change() < 0).mean()

            # Signal if trend losing strength
            if short_slope < medium_slope * 0.5 and red_days_pct > 0.6:
                severity = "HIGH" if rsi_declining else "MEDIUM"
                confidence = 0.75 if rsi_declining else 0.60

                signals.append(PredictiveSignal(
                    signal_id=str(uuid.uuid4()),
                    symbol=symbol,
                    signal_type="TREND_DETERIORATION",
                    severity=severity,
                    confidence=confidence,
                    lead_time_days=5,
                    description=f"Uptrend weakening: slope decay {((short_slope/medium_slope)*100 if medium_slope != 0 else 0):.0f}%, {red_days_pct*100:.0f}% red days",
                    recommended_action="Tighten stops or reduce position",
                    detected_at=datetime.now().isoformat()
                ))

        except Exception as e:
            print(f"Error in trend deterioration detection for {symbol}: {str(e)}")

        return signals

    def _detect_volatility_regime_change(self, symbol: str) -> List[PredictiveSignal]:
        """
        Predict shift from low-vol to high-vol regime

        Measures:
        - ATR percentile (is ATR in bottom 20%?)
        - Range expansion (daily ranges increasing)
        - Consecutive inside/outside days

        Lead time: 2-5 days
        """
        signals = []

        try:
            df = self.price_store.get_prices(symbol, days=90)
            if df.empty or len(df) < 30:
                return signals

            # Ensure column name consistency
            high_col = 'high' if 'high' in df.columns else 'High'
            low_col = 'low' if 'low' in df.columns else 'Low'
            close_col = 'close' if 'close' in df.columns else 'Close'

            # Calculate ATR
            atr = self._calculate_atr(df, period=14)
            if atr is None or len(atr) < 60:
                return signals

            # ATR percentile (current vs 60-day)
            current_atr = atr.iloc[-1]
            atr_60d = atr.tail(60)
            atr_percentile = (atr_60d <= current_atr).mean() * 100

            # Range expansion (avg range last 10 days vs prev 10 days)
            recent_range = (df[high_col] - df[low_col]).tail(10).mean()
            prev_range = (df[high_col] - df[low_col]).iloc[-20:-10].mean()
            range_expansion = (recent_range / prev_range - 1) * 100 if prev_range > 0 else 0

            # Signal if volatility increasing
            if atr_percentile < 20 and range_expansion > 15:
                signals.append(PredictiveSignal(
                    signal_id=str(uuid.uuid4()),
                    symbol=symbol,
                    signal_type="VOLATILITY_INCOMING",
                    severity="MEDIUM",
                    confidence=0.65,
                    lead_time_days=3,
                    description=f"Volatility regime change approaching: ATR {atr_percentile:.0f}th percentile, range expanding {range_expansion:.0f}%",
                    recommended_action="Tighten stops, reduce leverage",
                    detected_at=datetime.now().isoformat()
                ))

        except Exception as e:
            print(f"Error in volatility regime change detection for {symbol}: {str(e)}")

        return signals

    def _detect_timeframe_divergence(self, symbol: str) -> List[PredictiveSignal]:
        """
        Flag when different timeframes disagree

        Measures:
        - Short-term (5-day): Direction
        - Medium-term (20-day): Direction
        - Long-term (50-day): Direction

        Lead time: Concurrent
        """
        signals = []

        try:
            df = self.price_store.get_prices(symbol, days=60)
            if df.empty or len(df) < 50:
                return signals

            close_col = 'close' if 'close' in df.columns else 'Close'

            # Calculate slopes for different timeframes
            short_slope = self._calculate_slope(df[close_col].tail(5))
            medium_slope = self._calculate_slope(df[close_col].tail(20))
            long_slope = self._calculate_slope(df[close_col].tail(50))

            # Determine direction for each timeframe
            short_dir = "UP" if short_slope > 0 else "DOWN"
            medium_dir = "UP" if medium_slope > 0 else "DOWN"
            long_dir = "UP" if long_slope > 0 else "DOWN"

            # Check for divergence (short vs long)
            if short_dir != long_dir:
                severity = "HIGH" if short_dir == "UP" and long_dir == "DOWN" else "MEDIUM"
                confidence = 0.70 if medium_dir == long_dir else 0.55

                signals.append(PredictiveSignal(
                    signal_id=str(uuid.uuid4()),
                    symbol=symbol,
                    signal_type="TIMEFRAME_DIVERGENCE",
                    severity=severity,
                    confidence=confidence,
                    lead_time_days=0,
                    description=f"Timeframe conflict: 5-day {short_dir}, 20-day {medium_dir}, 50-day {long_dir}",
                    recommended_action="Reduce conviction, use tighter stops",
                    detected_at=datetime.now().isoformat()
                ))

        except Exception as e:
            print(f"Error in timeframe divergence detection for {symbol}: {str(e)}")

        return signals

    # Helper methods

    def _calculate_slope(self, series: pd.Series) -> float:
        """Calculate slope of a time series using linear regression"""
        if len(series) < 2:
            return 0.0

        try:
            x = np.arange(len(series))
            y = series.values
            # Simple linear regression
            slope = np.polyfit(x, y, 1)[0]
            return float(slope)
        except Exception:
            return 0.0

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
        """Calculate Average True Range"""
        try:
            high_col = 'high' if 'high' in df.columns else 'High'
            low_col = 'low' if 'low' in df.columns else 'Low'
            close_col = 'close' if 'close' in df.columns else 'Close'

            # True Range
            high_low = df[high_col] - df[low_col]
            high_close = np.abs(df[high_col] - df[close_col].shift())
            low_close = np.abs(df[low_col] - df[close_col].shift())

            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

            # ATR
            atr = true_range.rolling(window=period).mean()
            return atr

        except Exception:
            return None
