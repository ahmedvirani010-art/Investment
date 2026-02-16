"""
PSX Portfolio Manager - Utility Functions

Helper functions for:
- Signal conversion (converting agent outputs to 0-100 scores)
- Score normalization
- Reasoning generation
"""

from typing import List, Dict, Optional
from psx_technical_agent import TechnicalSnapshot, SignalType
from psx_fundamental_agent import FundamentalScore, RedFlagSeverity
from psx_anomaly_agent import Anomaly, Severity


def convert_technical_to_score(snapshot: Optional[TechnicalSnapshot]) -> float:
    """
    Convert technical snapshot to 0-100 score

    Args:
        snapshot: TechnicalSnapshot from PSXTechnicalAgent

    Returns:
        Score (0-100)
    """
    if not snapshot or not snapshot.signals:
        return 50.0  # Neutral

    # Map overall bias to base score
    if snapshot.overall_bias == SignalType.BULLISH:
        # Bullish: 50-100 based on confidence
        base_score = 50.0 + (snapshot.confidence * 50.0)
    elif snapshot.overall_bias == SignalType.BEARISH:
        # Bearish: 0-50 based on confidence
        base_score = 50.0 - (snapshot.confidence * 50.0)
    elif snapshot.overall_bias == SignalType.OVERBOUGHT:
        # Overbought: slightly negative (40-45)
        base_score = 40.0 + (snapshot.confidence * 5.0)
    elif snapshot.overall_bias == SignalType.OVERSOLD:
        # Oversold: slightly positive (55-60)
        base_score = 55.0 + (snapshot.confidence * 5.0)
    else:  # NEUTRAL
        base_score = 50.0

    return max(0.0, min(100.0, base_score))


def convert_fundamental_to_score(fundamental: Optional[FundamentalScore]) -> float:
    """
    Convert fundamental score to 0-100 score

    Args:
        fundamental: FundamentalScore from PSXFundamentalAgent

    Returns:
        Score (0-100), already in this range
    """
    if not fundamental:
        return 50.0  # Neutral

    return fundamental.fundamental_score


def convert_anomaly_to_score(anomalies: List[Anomaly], symbol: str) -> float:
    """
    Convert anomaly detections to 0-100 score

    Lower score = more anomalies (anomalies are concerning)

    Args:
        anomalies: List of Anomaly objects
        symbol: Stock symbol to check

    Returns:
        Score (0-100)
    """
    if not anomalies:
        return 50.0  # Neutral (no anomalies)

    # Filter anomalies for this symbol
    symbol_anomalies = [a for a in anomalies if a.symbol == symbol]

    if not symbol_anomalies:
        return 50.0  # No anomalies for this symbol

    # Count anomalies by severity
    high_count = sum(1 for a in symbol_anomalies if a.severity == Severity.HIGH)
    medium_count = sum(1 for a in symbol_anomalies if a.severity == Severity.MEDIUM)
    low_count = sum(1 for a in symbol_anomalies if a.severity == Severity.LOW)

    # Calculate penalty
    penalty = (high_count * 20) + (medium_count * 10) + (low_count * 5)
    score = 50.0 - penalty

    # Cap at reasonable bounds
    return max(10.0, min(50.0, score))


def convert_news_to_score(correlations: List, symbol: str) -> float:
    """
    Convert news sentiment to 0-100 score

    Args:
        correlations: List of NewsAnomalyCorrelation objects (or empty)
        symbol: Stock symbol to check

    Returns:
        Score (0-100)
    """
    if not correlations:
        return 50.0  # Neutral (no news)

    # Filter correlations for this symbol
    symbol_correlations = [c for c in correlations if hasattr(c, 'symbol') and c.symbol == symbol]

    if not symbol_correlations:
        return 50.0  # No news for this symbol

    # Analyze sentiment from correlated news
    # This is a simplified version - real implementation would parse sentiment
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for corr in symbol_correlations:
        if hasattr(corr, 'articles'):
            for article in corr.articles:
                if hasattr(article, 'sentiment'):
                    if article.sentiment == 'positive':
                        positive_count += 1
                    elif article.sentiment == 'negative':
                        negative_count += 1
                    else:
                        neutral_count += 1

    total = positive_count + negative_count + neutral_count
    if total == 0:
        return 50.0

    # Calculate sentiment score
    # Positive: 50-100, Negative: 0-50, Neutral: 50
    positive_pct = positive_count / total
    negative_pct = negative_count / total

    score = 50.0 + (positive_pct * 50.0) - (negative_pct * 50.0)

    return max(0.0, min(100.0, score))


def extract_red_flags(fundamental: Optional[FundamentalScore]) -> List[str]:
    """
    Extract red flag descriptions from fundamental score

    Args:
        fundamental: FundamentalScore object

    Returns:
        List of red flag descriptions
    """
    if not fundamental or not fundamental.red_flags:
        return []

    return [f"{flag.flag}: {flag.description}" for flag in fundamental.red_flags]


def has_critical_red_flag(fundamental: Optional[FundamentalScore]) -> bool:
    """
    Check if there are critical red flags

    Args:
        fundamental: FundamentalScore object

    Returns:
        True if critical red flags exist
    """
    if not fundamental or not fundamental.red_flags:
        return False

    return any(flag.severity == RedFlagSeverity.CRITICAL for flag in fundamental.red_flags)


def has_high_red_flag(fundamental: Optional[FundamentalScore]) -> bool:
    """
    Check if there are high-severity red flags

    Args:
        fundamental: FundamentalScore object

    Returns:
        True if high red flags exist
    """
    if not fundamental or not fundamental.red_flags:
        return False

    return any(flag.severity == RedFlagSeverity.HIGH for flag in fundamental.red_flags)


def format_reasoning_buy(
    signal_breakdown: Dict[str, float],
    technical_bias: str,
    fundamental_rec: str,
    has_anomaly: bool,
    red_flags: List[str]
) -> List[str]:
    """
    Generate reasoning for BUY decision

    Args:
        signal_breakdown: Dictionary of component scores
        technical_bias: Technical bias (Bullish/Bearish/Neutral)
        fundamental_rec: Fundamental recommendation (BUY/HOLD/SELL)
        has_anomaly: Whether anomalies detected
        red_flags: List of red flags

    Returns:
        List of reasoning strings
    """
    reasons = []

    # Fundamental
    if fundamental_rec == "BUY" and signal_breakdown.get('fundamental', 0) >= 70:
        reasons.append(f"✓ Strong fundamental score ({signal_breakdown['fundamental']:.0f}/100) with BUY recommendation")
    elif signal_breakdown.get('fundamental', 0) >= 60:
        reasons.append(f"✓ Good fundamental score ({signal_breakdown['fundamental']:.0f}/100)")

    # Technical
    if technical_bias == "Bullish" and signal_breakdown.get('technical', 0) >= 70:
        reasons.append(f"✓ Strong technical bullish signal ({signal_breakdown['technical']:.0f}/100)")
    elif technical_bias == "Bullish":
        reasons.append(f"✓ Technical bullish bias ({signal_breakdown['technical']:.0f}/100)")

    # News sentiment
    if signal_breakdown.get('news', 0) >= 65:
        reasons.append(f"✓ Positive news sentiment ({signal_breakdown['news']:.0f}/100)")

    # Anomalies
    if not has_anomaly:
        reasons.append("✓ No unusual trading activity detected")
    else:
        reasons.append(f"⚠ Anomaly detected (score: {signal_breakdown.get('anomaly', 50):.0f}/100)")

    # Red flags
    if red_flags:
        for flag in red_flags[:2]:  # Show max 2 flags
            reasons.append(f"⚠ {flag}")

    return reasons if reasons else ["Composite score meets buy threshold"]


def format_reasoning_sell(
    signal_breakdown: Dict[str, float],
    technical_bias: str,
    fundamental_rec: str,
    has_anomaly: bool,
    red_flags: List[str]
) -> List[str]:
    """
    Generate reasoning for SELL decision

    Args:
        signal_breakdown: Dictionary of component scores
        technical_bias: Technical bias (Bullish/Bearish/Neutral)
        fundamental_rec: Fundamental recommendation (BUY/HOLD/SELL)
        has_anomaly: Whether anomalies detected
        red_flags: List of red flags

    Returns:
        List of reasoning strings
    """
    reasons = []

    # Fundamental
    if fundamental_rec == "SELL" or signal_breakdown.get('fundamental', 0) < 30:
        reasons.append(f"✗ Weak fundamental score ({signal_breakdown['fundamental']:.0f}/100)")

    # Technical
    if technical_bias == "Bearish":
        reasons.append(f"✗ Technical bearish signal ({signal_breakdown['technical']:.0f}/100)")
    elif technical_bias == "Overbought":
        reasons.append("✗ Technical overbought condition")

    # News sentiment
    if signal_breakdown.get('news', 0) < 35:
        reasons.append(f"✗ Negative news sentiment ({signal_breakdown['news']:.0f}/100)")

    # Anomalies
    if has_anomaly:
        reasons.append(f"✗ Unusual trading activity (score: {signal_breakdown.get('anomaly', 50):.0f}/100)")

    # Red flags
    if red_flags:
        for flag in red_flags[:3]:  # Show max 3 flags
            reasons.append(f"✗ {flag}")

    return reasons if reasons else ["Composite score below sell threshold"]


def format_reasoning_reduce(
    signal_breakdown: Dict[str, float],
    technical_bias: str,
    fundamental_rec: str
) -> List[str]:
    """
    Generate reasoning for REDUCE decision

    Args:
        signal_breakdown: Dictionary of component scores
        technical_bias: Technical bias
        fundamental_rec: Fundamental recommendation

    Returns:
        List of reasoning strings
    """
    reasons = []

    if signal_breakdown.get('fundamental', 0) < 50:
        reasons.append(f"⚠ Fundamental score weakening ({signal_breakdown['fundamental']:.0f}/100)")

    if technical_bias in ["Bearish", "Neutral"]:
        reasons.append(f"⚠ Technical bias shifted to {technical_bias}")

    reasons.append("⚠ Reducing exposure to manage risk")

    return reasons


def format_reasoning_hold(
    signal_breakdown: Dict[str, float],
    current_position: bool
) -> List[str]:
    """
    Generate reasoning for HOLD decision

    Args:
        signal_breakdown: Dictionary of component scores
        current_position: Whether currently holding position

    Returns:
        List of reasoning strings
    """
    if current_position:
        return [
            f"Composite score: {signal_breakdown.get('composite', 50):.0f}/100",
            "Signals not strong enough to sell",
            "Maintaining current position"
        ]
    else:
        return [
            f"Composite score: {signal_breakdown.get('composite', 50):.0f}/100",
            "Signals not strong enough to buy",
            "Staying on sidelines"
        ]


def calculate_signal_confidence(
    technical_score: float,
    fundamental_score: float,
    anomaly_score: float,
    news_score: float
) -> float:
    """
    Calculate confidence based on signal agreement

    High confidence = all signals agree (all high or all low)
    Low confidence = signals conflict

    Args:
        technical_score: Technical score (0-100)
        fundamental_score: Fundamental score (0-100)
        anomaly_score: Anomaly score (0-100)
        news_score: News score (0-100)

    Returns:
        Confidence (0-1)
    """
    scores = [technical_score, fundamental_score, anomaly_score, news_score]

    # Calculate standard deviation of scores
    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5

    # Convert std dev to confidence
    # Low std dev (agreement) = high confidence
    # High std dev (disagreement) = low confidence
    # Std dev ranges from 0 (perfect agreement) to ~50 (maximum disagreement)
    max_std_dev = 50.0
    confidence = 1.0 - (std_dev / max_std_dev)

    # Boost confidence if signals are extreme (very bullish or very bearish)
    if mean_score > 70 or mean_score < 30:
        confidence = min(1.0, confidence * 1.2)

    return max(0.0, min(1.0, confidence))


def format_price(price: float) -> str:
    """Format price for display"""
    return f"PKR {price:,.2f}"


def format_quantity(quantity: float) -> str:
    """Format quantity for display"""
    return f"{quantity:,.0f} shares"


def format_percentage(value: float) -> str:
    """Format percentage for display"""
    return f"{value:.1f}%"


def format_money(amount: float) -> str:
    """Format money amount for display"""
    return f"PKR {amount:,.0f}"
