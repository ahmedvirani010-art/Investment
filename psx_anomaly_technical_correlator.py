"""
PSX Anomaly-Technical Correlation Module

Correlates anomaly detection signals with technical analysis signals
to identify high-confidence "confluence" scenarios.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from psx_anomaly_agent import Anomaly, AnomalyType, Severity
from psx_technical_agent import TechnicalSnapshot, SignalType


class ConfluenceStrength(Enum):
    """Strength of anomaly-technical correlation"""
    VERY_STRONG = "Very Strong"  # Both systems highly confident and aligned
    STRONG = "Strong"            # Both systems aligned with good confidence
    MODERATE = "Moderate"        # Both systems aligned but lower confidence
    WEAK = "Weak"                # Signals present but conflicting or low confidence
    NONE = "None"                # No meaningful correlation


@dataclass
class ConfluenceSignal:
    """Represents a confluence between anomaly and technical analysis"""
    symbol: str
    date: str

    # Anomaly info
    anomaly: Anomaly

    # Technical info
    technical_snapshot: TechnicalSnapshot

    # Correlation scoring
    confluence_strength: ConfluenceStrength
    correlation_score: float  # 0.0-1.0

    # Analysis
    signal_direction: str  # "BULLISH", "BEARISH", "NEUTRAL", "CONFLICTING"
    explanation: str
    key_factors: List[str]

    # Trading implications
    actionable: bool  # Whether this is a high-confidence tradeable signal


class AnomalyTechnicalCorrelator:
    """
    Correlates anomaly detection with technical analysis to identify confluence
    """

    def __init__(self):
        """Initialize correlator"""
        pass

    def correlate_all(
        self,
        anomalies_report: Dict[str, List[Anomaly]],
        technical_snapshots: Dict[str, TechnicalSnapshot]
    ) -> List[ConfluenceSignal]:
        """
        Correlate all anomalies with technical snapshots

        Args:
            anomalies_report: Dict of symbol -> list of anomalies
            technical_snapshots: Dict of symbol -> technical snapshot

        Returns:
            List of confluence signals
        """
        confluences = []

        for symbol, anomalies in anomalies_report.items():
            # Get technical snapshot for this symbol
            tech_snapshot = technical_snapshots.get(symbol)

            if not tech_snapshot:
                continue

            # Correlate each anomaly with the technical snapshot
            for anomaly in anomalies:
                confluence = self._correlate_single(anomaly, tech_snapshot)
                if confluence:
                    confluences.append(confluence)

        # Sort by correlation score (strongest first)
        confluences.sort(key=lambda x: x.correlation_score, reverse=True)

        return confluences

    def _correlate_single(
        self,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot
    ) -> Optional[ConfluenceSignal]:
        """
        Correlate a single anomaly with technical snapshot

        Returns:
            ConfluenceSignal or None if no meaningful correlation
        """
        # Determine signal direction from anomaly
        anomaly_direction = self._get_anomaly_direction(anomaly)

        # Technical direction
        tech_direction = tech_snapshot.overall_bias.value.upper()

        # Calculate correlation score
        score = self._calculate_correlation_score(
            anomaly, tech_snapshot, anomaly_direction, tech_direction
        )

        # Determine confluence strength
        strength = self._determine_confluence_strength(score, anomaly, tech_snapshot)

        # Determine final signal direction
        if anomaly_direction == tech_direction:
            signal_direction = anomaly_direction
        elif anomaly_direction == "NEUTRAL" or tech_direction == "NEUTRAL":
            signal_direction = anomaly_direction if anomaly_direction != "NEUTRAL" else tech_direction
        else:
            signal_direction = "CONFLICTING"

        # Build explanation and key factors
        explanation, key_factors = self._build_explanation(
            anomaly, tech_snapshot, anomaly_direction, tech_direction, signal_direction
        )

        # Determine if actionable (high-confidence trade signal)
        actionable = self._is_actionable(score, strength, signal_direction, anomaly, tech_snapshot)

        return ConfluenceSignal(
            symbol=anomaly.symbol,
            date=anomaly.date,
            anomaly=anomaly,
            technical_snapshot=tech_snapshot,
            confluence_strength=strength,
            correlation_score=score,
            signal_direction=signal_direction,
            explanation=explanation,
            key_factors=key_factors,
            actionable=actionable
        )

    def _get_anomaly_direction(self, anomaly: Anomaly) -> str:
        """
        Determine bullish/bearish direction from anomaly

        Returns:
            "BULLISH", "BEARISH", or "NEUTRAL"
        """
        atype = anomaly.anomaly_type
        z = anomaly.z_score

        # Volume spike is directionally neutral (could be buying or selling)
        if atype == AnomalyType.VOLUME_SPIKE:
            return "NEUTRAL"

        # Price movement - positive z-score is bullish, negative is bearish
        elif atype == AnomalyType.PRICE_MOVEMENT:
            return "BULLISH" if z > 0 else "BEARISH"

        # Opening gap - positive is bullish, negative is bearish
        elif atype == AnomalyType.OPENING_GAP:
            return "BULLISH" if z > 0 else "BEARISH"

        # Volatility spike is neutral (high volatility can go either way)
        elif atype == AnomalyType.VOLATILITY_SPIKE:
            return "NEUTRAL"

        # Liquidity change - high turnover suggests interest (slightly bullish)
        elif atype == AnomalyType.LIQUIDITY_CHANGE:
            return "BULLISH" if z > 0 else "BEARISH"

        return "NEUTRAL"

    def _calculate_correlation_score(
        self,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot,
        anomaly_direction: str,
        tech_direction: str
    ) -> float:
        """
        Calculate correlation score between anomaly and technical

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Base score from anomaly severity
        if anomaly.severity == Severity.HIGH:
            score += 0.3
        elif anomaly.severity == Severity.MEDIUM:
            score += 0.2
        else:
            score += 0.1

        # Add score from technical confidence
        score += tech_snapshot.confidence * 0.3

        # Bonus for directional alignment
        if anomaly_direction == tech_direction and anomaly_direction != "NEUTRAL":
            score += 0.3
        elif anomaly_direction != "CONFLICTING" and tech_direction != "NEUTRAL":
            score += 0.1

        # Bonus for specific anomaly-technical combinations
        combo_bonus = self._get_combination_bonus(anomaly, tech_snapshot)
        score += combo_bonus

        return min(1.0, score)

    def _get_combination_bonus(
        self,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot
    ) -> float:
        """
        Award bonus points for specific powerful combinations
        """
        bonus = 0.0
        atype = anomaly.anomaly_type

        # Volume spike + Breakout (price above resistance)
        if atype == AnomalyType.VOLUME_SPIKE:
            indicators = tech_snapshot.indicator_values

            # Check if price broke above SMA(200) with volume
            if 'Close' in indicators and 'SMA_200' in indicators:
                if indicators['Close'] > indicators['SMA_200']:
                    bonus += 0.15

            # Check for momentum confirmation
            if 'RSI' in indicators:
                rsi = indicators['RSI']
                if 50 < rsi < 70:  # Bullish but not overbought
                    bonus += 0.10

        # Price movement + Trend confirmation
        elif atype == AnomalyType.PRICE_MOVEMENT:
            # Strong price move confirmed by technical trend
            if tech_snapshot.overall_bias != SignalType.NEUTRAL:
                bonus += 0.10

        # Opening gap + Technical momentum
        elif atype == AnomalyType.OPENING_GAP:
            # Gap confirmed by momentum indicators
            if tech_snapshot.overall_bias != SignalType.NEUTRAL:
                bonus += 0.10

        return bonus

    def _determine_confluence_strength(
        self,
        score: float,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot
    ) -> ConfluenceStrength:
        """Determine confluence strength category"""
        if score >= 0.80:
            return ConfluenceStrength.VERY_STRONG
        elif score >= 0.65:
            return ConfluenceStrength.STRONG
        elif score >= 0.45:
            return ConfluenceStrength.MODERATE
        elif score >= 0.25:
            return ConfluenceStrength.WEAK
        else:
            return ConfluenceStrength.NONE

    def _build_explanation(
        self,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot,
        anomaly_direction: str,
        tech_direction: str,
        signal_direction: str
    ) -> tuple[str, List[str]]:
        """
        Build human-readable explanation and key factors list
        """
        key_factors = []

        # Add anomaly description
        key_factors.append(f"Anomaly: {anomaly.description} (z={anomaly.z_score:.2f})")

        # Add technical bias
        conf_pct = tech_snapshot.confidence * 100
        key_factors.append(f"Technical: {tech_direction} bias ({conf_pct:.0f}% confidence)")

        # Add specific indicator values
        indicators = tech_snapshot.indicator_values

        if 'RSI' in indicators:
            rsi = indicators['RSI']
            if rsi >= 70:
                key_factors.append(f"RSI overbought at {rsi:.1f}")
            elif rsi <= 30:
                key_factors.append(f"RSI oversold at {rsi:.1f}")
            else:
                key_factors.append(f"RSI at {rsi:.1f}")

        if 'Close' in indicators and 'SMA_200' in indicators:
            price = indicators['Close']
            sma200 = indicators['SMA_200']
            position = "above" if price > sma200 else "below"
            key_factors.append(f"Price {position} SMA(200)")

        # Build explanation summary
        if signal_direction == "CONFLICTING":
            explanation = (
                f"{anomaly.anomaly_type.value} detected but technical analysis shows "
                f"{tech_direction.lower()} bias - signals are conflicting. "
                f"Exercise caution."
            )
        elif signal_direction == "BULLISH":
            explanation = (
                f"Strong BULLISH confluence: {anomaly.anomaly_type.value} "
                f"({anomaly.severity.value} severity) aligns with bullish technical setup. "
                f"Multiple indicators support upward movement."
            )
        elif signal_direction == "BEARISH":
            explanation = (
                f"Strong BEARISH confluence: {anomaly.anomaly_type.value} "
                f"({anomaly.severity.value} severity) aligns with bearish technical setup. "
                f"Multiple indicators suggest downward pressure."
            )
        else:
            explanation = (
                f"{anomaly.anomaly_type.value} detected ({anomaly.severity.value} severity). "
                f"Technical analysis shows {tech_direction.lower()} bias. "
                f"Monitor for direction confirmation."
            )

        return explanation, key_factors

    def _is_actionable(
        self,
        score: float,
        strength: ConfluenceStrength,
        signal_direction: str,
        anomaly: Anomaly,
        tech_snapshot: TechnicalSnapshot
    ) -> bool:
        """
        Determine if this is a high-confidence actionable trading signal

        Criteria for actionable:
        - Strong or Very Strong confluence
        - Clear directional signal (not neutral or conflicting)
        - High severity anomaly OR high technical confidence
        """
        # Must be strong confluence
        if strength not in [ConfluenceStrength.STRONG, ConfluenceStrength.VERY_STRONG]:
            return False

        # Must have clear direction
        if signal_direction in ["NEUTRAL", "CONFLICTING"]:
            return False

        # Must have either high severity anomaly OR high technical confidence
        high_anomaly = anomaly.severity in [Severity.HIGH, Severity.MEDIUM]
        high_technical = tech_snapshot.confidence >= 0.6

        return high_anomaly or high_technical

    def print_confluence_report(self, confluences: List[ConfluenceSignal]):
        """Print formatted confluence analysis report"""
        if not confluences:
            print("\n" + "="*100)
            print("🔗 ANOMALY-TECHNICAL CORRELATION")
            print("="*100)
            print("ℹ️  No significant correlations found")
            print("="*100)
            return

        # Count by strength
        actionable_count = sum(1 for c in confluences if c.actionable)
        strong_count = sum(
            1 for c in confluences
            if c.confluence_strength in [ConfluenceStrength.STRONG, ConfluenceStrength.VERY_STRONG]
        )

        print("\n" + "="*100)
        print("🔗 ANOMALY-TECHNICAL CORRELATION")
        print("="*100)
        print(f"Total Correlations: {len(confluences)}")
        print(f"Strong Confluences: {strong_count}")
        print(f"Actionable Signals: {actionable_count}")
        print("="*100)

        # Print actionable signals first
        if actionable_count > 0:
            print("\n" + "🎯 ACTIONABLE SIGNALS (High Confidence)")
            print("-"*100)

            for conf in [c for c in confluences if c.actionable]:
                self._print_single_confluence(conf)

        # Print other strong signals
        other_strong = [
            c for c in confluences
            if not c.actionable and c.confluence_strength in [
                ConfluenceStrength.STRONG, ConfluenceStrength.VERY_STRONG
            ]
        ]

        if other_strong:
            print("\n" + "📊 OTHER STRONG SIGNALS")
            print("-"*100)

            for conf in other_strong:
                self._print_single_confluence(conf)

        # Print moderate signals (condensed)
        moderate = [
            c for c in confluences
            if c.confluence_strength == ConfluenceStrength.MODERATE
        ]

        if moderate:
            print("\n" + "📈 MODERATE CORRELATIONS")
            print("-"*100)
            print(f"   {len(moderate)} moderate-strength correlations detected:")
            for conf in moderate:
                print(f"   • {conf.symbol}: {conf.anomaly.anomaly_type.value} + "
                      f"{conf.signal_direction} technical (score: {conf.correlation_score:.2f})")

        print("\n" + "="*100)

    def _print_single_confluence(self, conf: ConfluenceSignal):
        """Print details of a single confluence signal"""
        # Emoji based on signal direction
        emoji_map = {
            "BULLISH": "📈",
            "BEARISH": "📉",
            "NEUTRAL": "↔️",
            "CONFLICTING": "⚠️"
        }
        emoji = emoji_map.get(conf.signal_direction, "•")

        print(f"\n{emoji} {conf.symbol} - {conf.signal_direction}")
        print(f"   Confluence: {conf.confluence_strength.value} (score: {conf.correlation_score:.2f})")
        if conf.actionable:
            print(f"   🎯 ACTIONABLE SIGNAL - High confidence trade setup")

        print(f"\n   {conf.explanation}")

        print(f"\n   Key Factors:")
        for factor in conf.key_factors:
            print(f"     • {factor}")

        print()
