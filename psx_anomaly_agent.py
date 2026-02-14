"""
PSX Anomaly Detection Agent

Monitors Pakistan Stock Exchange (PSX) for unusual trading patterns and price movements.
Uses statistical analysis to detect anomalies in volume, price, volatility, and liquidity.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Anomaly severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyType(Enum):
    """Types of anomalies detected"""
    VOLUME_SPIKE = "Volume Spike"
    PRICE_MOVEMENT = "Price Movement"
    OPENING_GAP = "Opening Gap"
    VOLATILITY_SPIKE = "Volatility Spike"
    LIQUIDITY_CHANGE = "Liquidity Change"


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    symbol: str
    date: str
    anomaly_type: AnomalyType
    severity: Severity
    value: float
    baseline: float
    z_score: float
    description: str


class PSXAnomalyAgent:
    """
    Anomaly detection agent for Pakistan Stock Exchange (PSX)

    Monitors and detects unusual trading patterns using statistical analysis:
    - Volume spikes (unusual trading activity)
    - Price movements (abnormal returns)
    - Opening gaps (gap up/down detection)
    - Volatility spikes (unusual price ranges)
    - Liquidity changes (turnover anomalies)
    """

    def __init__(self, lookback_days: int = 60, z_threshold: float = 2.5):
        """
        Initialize the anomaly detection agent

        Args:
            lookback_days: Number of days to use for baseline calculation
            z_threshold: Z-score threshold for anomaly detection (default: 2.5σ)
        """
        self.lookback_days = lookback_days
        self.z_threshold = z_threshold

    def _calculate_z_score(self, value: float, series: pd.Series) -> float:
        """Calculate z-score for a value against a series"""
        mean = series.mean()
        std = series.std()
        if std == 0:
            return 0
        return (value - mean) / std

    def _determine_severity(self, z_score: float) -> Severity:
        """Determine severity based on z-score"""
        abs_z = abs(z_score)
        if abs_z >= 4.0:
            return Severity.HIGH
        elif abs_z >= 3.0:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _fetch_stock_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetch stock data from yfinance for PSX symbol

        Args:
            symbol: Stock symbol (e.g., 'LUCK', 'PSO', 'HBL')

        Returns:
            DataFrame with stock data
        """
        # PSX symbols need .KA suffix for yfinance
        ticker_symbol = f"{symbol}.KA"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 10)

        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                print(f"Warning: No data found for {symbol}")
                return pd.DataFrame()

            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def detect_volume_spikes(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
        """Detect unusual volume spikes"""
        anomalies = []

        if len(df) < 2:
            return anomalies

        # Calculate baseline volume statistics
        volumes = df['Volume'].iloc[:-1]  # Exclude most recent day for baseline
        current_volume = df['Volume'].iloc[-1]

        z_score = self._calculate_z_score(current_volume, volumes)

        if abs(z_score) >= self.z_threshold:
            severity = self._determine_severity(z_score)
            baseline = volumes.mean()

            pct_change = ((current_volume - baseline) / baseline) * 100

            anomalies.append(Anomaly(
                symbol=symbol,
                date=df.index[-1].strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                severity=severity,
                value=current_volume,
                baseline=baseline,
                z_score=z_score,
                description=f"Volume {pct_change:+.1f}% from average ({current_volume:,.0f} vs {baseline:,.0f})"
            ))

        return anomalies

    def detect_price_movements(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
        """Detect abnormal price returns"""
        anomalies = []

        if len(df) < 2:
            return anomalies

        # Calculate daily returns
        df['Returns'] = df['Close'].pct_change() * 100

        # Baseline returns (excluding most recent)
        returns = df['Returns'].iloc[:-1].dropna()
        current_return = df['Returns'].iloc[-1]

        if pd.isna(current_return):
            return anomalies

        z_score = self._calculate_z_score(current_return, returns)

        if abs(z_score) >= self.z_threshold:
            severity = self._determine_severity(z_score)
            baseline = returns.mean()

            anomalies.append(Anomaly(
                symbol=symbol,
                date=df.index[-1].strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.PRICE_MOVEMENT,
                severity=severity,
                value=current_return,
                baseline=baseline,
                z_score=z_score,
                description=f"Return {current_return:+.2f}% (avg: {baseline:+.2f}%)"
            ))

        return anomalies

    def detect_opening_gaps(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
        """Detect gap up/down patterns"""
        anomalies = []

        if len(df) < 2:
            return anomalies

        # Calculate gap percentage
        prev_close = df['Close'].iloc[-2]
        current_open = df['Open'].iloc[-1]
        gap_pct = ((current_open - prev_close) / prev_close) * 100

        # Calculate historical gaps for baseline
        df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
        historical_gaps = df['Gap'].iloc[:-1].dropna()

        z_score = self._calculate_z_score(gap_pct, historical_gaps)

        if abs(z_score) >= self.z_threshold:
            severity = self._determine_severity(z_score)
            baseline = historical_gaps.mean()

            gap_type = "Gap Up" if gap_pct > 0 else "Gap Down"

            anomalies.append(Anomaly(
                symbol=symbol,
                date=df.index[-1].strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.OPENING_GAP,
                severity=severity,
                value=gap_pct,
                baseline=baseline,
                z_score=z_score,
                description=f"{gap_type} of {gap_pct:+.2f}%"
            ))

        return anomalies

    def detect_volatility_spikes(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
        """Detect unusual price range volatility"""
        anomalies = []

        if len(df) < 2:
            return anomalies

        # Calculate daily volatility as (High - Low) / Close percentage
        df['Volatility'] = ((df['High'] - df['Low']) / df['Close']) * 100

        volatilities = df['Volatility'].iloc[:-1]
        current_volatility = df['Volatility'].iloc[-1]

        z_score = self._calculate_z_score(current_volatility, volatilities)

        if abs(z_score) >= self.z_threshold:
            severity = self._determine_severity(z_score)
            baseline = volatilities.mean()

            anomalies.append(Anomaly(
                symbol=symbol,
                date=df.index[-1].strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.VOLATILITY_SPIKE,
                severity=severity,
                value=current_volatility,
                baseline=baseline,
                z_score=z_score,
                description=f"Volatility {current_volatility:.2f}% (avg: {baseline:.2f}%)"
            ))

        return anomalies

    def detect_liquidity_changes(self, symbol: str, df: pd.DataFrame) -> List[Anomaly]:
        """Detect unusual turnover changes"""
        anomalies = []

        if len(df) < 2:
            return anomalies

        # Calculate turnover (Volume * Close)
        df['Turnover'] = df['Volume'] * df['Close']

        turnovers = df['Turnover'].iloc[:-1]
        current_turnover = df['Turnover'].iloc[-1]

        z_score = self._calculate_z_score(current_turnover, turnovers)

        if abs(z_score) >= self.z_threshold:
            severity = self._determine_severity(z_score)
            baseline = turnovers.mean()

            pct_change = ((current_turnover - baseline) / baseline) * 100

            anomalies.append(Anomaly(
                symbol=symbol,
                date=df.index[-1].strftime('%Y-%m-%d'),
                anomaly_type=AnomalyType.LIQUIDITY_CHANGE,
                severity=severity,
                value=current_turnover,
                baseline=baseline,
                z_score=z_score,
                description=f"Turnover {pct_change:+.1f}% from average"
            ))

        return anomalies

    def analyze_symbol(self, symbol: str) -> List[Anomaly]:
        """
        Analyze a single stock symbol for all types of anomalies

        Args:
            symbol: Stock symbol to analyze

        Returns:
            List of detected anomalies
        """
        print(f"Analyzing {symbol}...")

        df = self._fetch_stock_data(symbol)

        if df.empty:
            return []

        all_anomalies = []

        # Run all detection methods
        all_anomalies.extend(self.detect_volume_spikes(symbol, df))
        all_anomalies.extend(self.detect_price_movements(symbol, df))
        all_anomalies.extend(self.detect_opening_gaps(symbol, df))
        all_anomalies.extend(self.detect_volatility_spikes(symbol, df))
        all_anomalies.extend(self.detect_liquidity_changes(symbol, df))

        return all_anomalies

    def generate_report(self, symbols: List[str]) -> Dict[str, List[Anomaly]]:
        """
        Generate anomaly detection report for multiple symbols

        Args:
            symbols: List of stock symbols to analyze

        Returns:
            Dictionary mapping symbols to their anomalies
        """
        report = {}

        for symbol in symbols:
            anomalies = self.analyze_symbol(symbol)
            if anomalies:
                report[symbol] = anomalies

        return report

    def print_report(self, report: Dict[str, List[Anomaly]]):
        """Print formatted anomaly report"""
        if not report:
            print("\n✓ No anomalies detected.")
            return

        print("\n" + "="*80)
        print("PSX ANOMALY DETECTION REPORT")
        print("="*80)

        total_anomalies = sum(len(anomalies) for anomalies in report.values())
        print(f"\nTotal Anomalies Detected: {total_anomalies}")
        print(f"Symbols with Anomalies: {len(report)}")
        print()

        for symbol, anomalies in report.items():
            print(f"\n{symbol} ({len(anomalies)} anomalies)")
            print("-" * 80)

            # Sort by severity
            sorted_anomalies = sorted(
                anomalies,
                key=lambda x: (x.severity == Severity.HIGH, x.severity == Severity.MEDIUM, abs(x.z_score)),
                reverse=True
            )

            for anomaly in sorted_anomalies:
                severity_symbol = {
                    Severity.HIGH: "🔴",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢"
                }[anomaly.severity]

                print(f"\n  {severity_symbol} {anomaly.severity.value} - {anomaly.anomaly_type.value}")
                print(f"     Date: {anomaly.date}")
                print(f"     {anomaly.description}")
                print(f"     Z-Score: {anomaly.z_score:.2f}")

        print("\n" + "="*80)


def main():
    """Example usage of PSX Anomaly Agent"""

    # Top PSX stocks to monitor
    psx_stocks = [
        "LUCK",  # Lucky Cement
        "PSO",   # Pakistan State Oil
        "HBL",   # Habib Bank Limited
        "ENGRO", # Engro Corporation
        "MCB",   # MCB Bank
        "OGDC",  # Oil & Gas Development Company
        "PPL",   # Pakistan Petroleum Limited
        "UBL",   # United Bank Limited
        "HUBC",  # Hub Power Company
        "FFC"    # Fauji Fertilizer Company
    ]

    # Initialize agent
    print("Initializing PSX Anomaly Detection Agent...")
    print(f"Lookback Period: 60 days")
    print(f"Z-Score Threshold: 2.5σ")

    agent = PSXAnomalyAgent(lookback_days=60, z_threshold=2.5)

    # Generate report
    report = agent.generate_report(psx_stocks)

    # Print results
    agent.print_report(report)


if __name__ == "__main__":
    main()
