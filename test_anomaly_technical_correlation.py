#!/usr/bin/env python3
"""
Test Anomaly-Technical Correlation

Quick test to demonstrate the new correlation feature
"""

from psx_anomaly_agent import Anomaly, AnomalyType, Severity
from psx_technical_agent import TechnicalSnapshot, TechnicalSignal, SignalType, SignalStrength
from psx_anomaly_technical_correlator import AnomalyTechnicalCorrelator


def create_test_scenario_1():
    """
    Scenario 1: BULLISH CONFLUENCE
    - Volume spike (HIGH severity)
    - Bullish technical setup (70% confidence)
    - Price above SMA(200)
    - RSI at 65 (bullish but not overbought)
    """
    # Create anomaly: HIGH severity volume spike
    anomaly = Anomaly(
        symbol="LUCK",
        date="2026-02-14",
        anomaly_type=AnomalyType.VOLUME_SPIKE,
        severity=Severity.HIGH,
        value=5_000_000,
        baseline=1_000_000,
        z_score=4.5,
        description="Extreme volume spike: 5.0M vs baseline 1.0M (4.5σ)"
    )

    # Create technical snapshot: Bullish
    tech_snapshot = TechnicalSnapshot(
        symbol="LUCK",
        date="2026-02-14",
        signals=[
            TechnicalSignal(
                symbol="LUCK",
                date="2026-02-14",
                indicator="SMA_Crossover",
                signal_type=SignalType.BULLISH,
                strength=SignalStrength.STRONG,
                value=465.0,
                description="Price crossed above SMA(50)"
            ),
            TechnicalSignal(
                symbol="LUCK",
                date="2026-02-14",
                indicator="RSI",
                signal_type=SignalType.BULLISH,
                strength=SignalStrength.MODERATE,
                value=65.0,
                description="RSI in bullish zone"
            )
        ],
        overall_bias=SignalType.BULLISH,
        confidence=0.70,
        indicator_values={
            'Close': 465.0,
            'SMA_50': 450.0,
            'SMA_200': 430.0,
            'RSI': 65.0,
            'MACD': 2.5
        }
    )

    return anomaly, tech_snapshot


def create_test_scenario_2():
    """
    Scenario 2: CONFLICTING SIGNALS
    - Bearish price movement (MEDIUM severity)
    - Bullish technical setup (60% confidence)
    - Classic divergence scenario
    """
    # Create anomaly: Bearish price movement
    anomaly = Anomaly(
        symbol="PSO",
        date="2026-02-14",
        anomaly_type=AnomalyType.PRICE_MOVEMENT,
        severity=Severity.MEDIUM,
        value=-5.2,
        baseline=0.5,
        z_score=-3.2,
        description="Unusual price drop: -5.2% (3.2σ below mean)"
    )

    # Create technical snapshot: Bullish (creating conflict)
    tech_snapshot = TechnicalSnapshot(
        symbol="PSO",
        date="2026-02-14",
        signals=[
            TechnicalSignal(
                symbol="PSO",
                date="2026-02-14",
                indicator="RSI",
                signal_type=SignalType.BULLISH,
                strength=SignalStrength.STRONG,
                value=28.0,
                description="RSI oversold"
            )
        ],
        overall_bias=SignalType.BULLISH,
        confidence=0.60,
        indicator_values={
            'Close': 180.0,
            'SMA_200': 185.0,
            'RSI': 28.0
        }
    )

    return anomaly, tech_snapshot


def create_test_scenario_3():
    """
    Scenario 3: BEARISH CONFLUENCE
    - Opening gap down (HIGH severity)
    - Bearish technical setup (75% confidence)
    - Price below SMA(200)
    """
    # Create anomaly: Gap down
    anomaly = Anomaly(
        symbol="HBL",
        date="2026-02-14",
        anomaly_type=AnomalyType.OPENING_GAP,
        severity=Severity.HIGH,
        value=-3.8,
        baseline=0.2,
        z_score=-4.2,
        description="Large opening gap down: -3.8% (4.2σ)"
    )

    # Create technical snapshot: Bearish
    tech_snapshot = TechnicalSnapshot(
        symbol="HBL",
        date="2026-02-14",
        signals=[
            TechnicalSignal(
                symbol="HBL",
                date="2026-02-14",
                indicator="SMA_Crossover",
                signal_type=SignalType.BEARISH,
                strength=SignalStrength.STRONG,
                value=155.0,
                description="Death cross: SMA(50) crossed below SMA(200)"
            ),
            TechnicalSignal(
                symbol="HBL",
                date="2026-02-14",
                indicator="RSI",
                signal_type=SignalType.BEARISH,
                strength=SignalStrength.MODERATE,
                value=35.0,
                description="RSI weakening"
            )
        ],
        overall_bias=SignalType.BEARISH,
        confidence=0.75,
        indicator_values={
            'Close': 155.0,
            'SMA_50': 158.0,
            'SMA_200': 160.0,
            'RSI': 35.0
        }
    )

    return anomaly, tech_snapshot


def main():
    """Run test scenarios"""
    print("="*100)
    print("ANOMALY-TECHNICAL CORRELATION TEST")
    print("="*100)
    print("\nTesting 3 scenarios:")
    print("  1. Bullish confluence (volume spike + bullish technicals)")
    print("  2. Conflicting signals (bearish price + bullish technicals)")
    print("  3. Bearish confluence (gap down + bearish technicals)")
    print("="*100)

    # Create correlator
    correlator = AnomalyTechnicalCorrelator()

    # Test Scenario 1: Bullish Confluence
    print("\n" + "="*100)
    print("TEST SCENARIO 1: BULLISH CONFLUENCE")
    print("="*100)

    anomaly1, tech1 = create_test_scenario_1()
    anomalies_report1 = {"LUCK": [anomaly1]}
    tech_snapshots1 = {"LUCK": tech1}

    confluences1 = correlator.correlate_all(anomalies_report1, tech_snapshots1)
    correlator.print_confluence_report(confluences1)

    # Test Scenario 2: Conflicting Signals
    print("\n" + "="*100)
    print("TEST SCENARIO 2: CONFLICTING SIGNALS")
    print("="*100)

    anomaly2, tech2 = create_test_scenario_2()
    anomalies_report2 = {"PSO": [anomaly2]}
    tech_snapshots2 = {"PSO": tech2}

    confluences2 = correlator.correlate_all(anomalies_report2, tech_snapshots2)
    correlator.print_confluence_report(confluences2)

    # Test Scenario 3: Bearish Confluence
    print("\n" + "="*100)
    print("TEST SCENARIO 3: BEARISH CONFLUENCE")
    print("="*100)

    anomaly3, tech3 = create_test_scenario_3()
    anomalies_report3 = {"HBL": [anomaly3]}
    tech_snapshots3 = {"HBL": tech3}

    confluences3 = correlator.correlate_all(anomalies_report3, tech_snapshots3)
    correlator.print_confluence_report(confluences3)

    # Combined test
    print("\n" + "="*100)
    print("COMBINED SCENARIO: All 3 signals together")
    print("="*100)

    all_anomalies = {
        "LUCK": [anomaly1],
        "PSO": [anomaly2],
        "HBL": [anomaly3]
    }
    all_tech = {
        "LUCK": tech1,
        "PSO": tech2,
        "HBL": tech3
    }

    all_confluences = correlator.correlate_all(all_anomalies, all_tech)
    correlator.print_confluence_report(all_confluences)

    print("\n" + "="*100)
    print("✅ TEST COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
