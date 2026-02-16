"""
Daily Analysis Automation

Automated system for running daily technical analysis on watchlist stocks.
Collects data, runs analysis, stores results, and generates alerts.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import json
import time

from production.config import ProductionConfig
from data_collection import DataCollectionManager
from psx_technical_agent import PSXTechnicalAgent
from config.technical_config import TechnicalAgentConfig
from strategies.base_strategy import EnhancedSnapshot


class DataFramePriceStore:
    """Wrapper to make DataFrame compatible with PSXTechnicalAgent"""

    def __init__(self, symbol: str, data):
        self.symbol = symbol
        self.data = data

    def get_prices(self, symbol, days=250):
        return self.data


class DailyAnalyzer:
    """
    Automated daily analysis system

    Workflow:
    1. Load configuration
    2. Collect price data for watchlist
    3. Run technical analysis on each symbol
    4. Store results
    5. Generate alerts
    6. Create daily report
    """

    def __init__(self, config: Optional[ProductionConfig] = None):
        """
        Args:
            config: Production configuration (loads from file if not provided)
        """
        self.config = config or ProductionConfig.load_from_file()
        self.storage_paths = self.config.get_storage_paths()

        # Initialize managers
        self.data_manager = DataCollectionManager(storage_dir="data")
        self.tech_config = TechnicalAgentConfig()

        # Run timestamp
        self.run_timestamp = None
        self.run_date = None

    def run_daily_analysis(self) -> Dict[str, EnhancedSnapshot]:
        """
        Run daily analysis on all watchlist symbols

        Returns:
            Dictionary mapping symbol to EnhancedSnapshot
        """
        self.run_timestamp = datetime.now()
        self.run_date = self.run_timestamp.date()

        print("="*80)
        print(f"DAILY TECHNICAL ANALYSIS - {self.run_date}")
        print("="*80)

        symbols = self.config.watchlist.get_all_symbols()

        print(f"\n📋 Watchlist: {len(symbols)} symbols")
        print(f"   {', '.join(symbols)}")

        # Step 1: Collect data
        print(f"\n{'='*80}")
        print("STEP 1: Data Collection")
        print(f"{'='*80}\n")

        price_data = self._collect_price_data(symbols)

        successful_count = sum(1 for df in price_data.values() if df is not None)
        print(f"\n✅ Collected {successful_count}/{len(symbols)} symbols")

        # Step 2: Run analysis
        print(f"\n{'='*80}")
        print("STEP 2: Technical Analysis")
        print(f"{'='*80}\n")

        snapshots = self._run_analysis(price_data)

        print(f"\n✅ Analyzed {len(snapshots)}/{len(symbols)} symbols")

        # Step 3: Store results
        print(f"\n{'='*80}")
        print("STEP 3: Store Results")
        print(f"{'='*80}\n")

        self._store_results(snapshots)

        # Step 4: Generate alerts
        print(f"\n{'='*80}")
        print("STEP 4: Generate Alerts")
        print(f"{'='*80}\n")

        alerts = self._generate_alerts(snapshots)

        print(f"\n✅ Generated {len(alerts)} alerts")

        # Step 5: Create report
        print(f"\n{'='*80}")
        print("STEP 5: Daily Report")
        print(f"{'='*80}\n")

        self._create_daily_report(snapshots, alerts)

        print(f"\n{'='*80}")
        print(f"✅ Daily Analysis Complete - {self.run_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        return snapshots

    def _collect_price_data(self, symbols: List[str]) -> Dict:
        """Collect price data for all symbols"""

        history_days = self.config.schedule.history_days

        print(f"Collecting {history_days} days of history for {len(symbols)} symbols...")

        price_data = self.data_manager.collect_batch(
            symbols,
            days=history_days,
            delay_seconds=1.0  # Rate limiting
        )

        return price_data

    def _run_analysis(self, price_data: Dict) -> Dict[str, EnhancedSnapshot]:
        """Run technical analysis on collected data"""

        snapshots = {}

        for i, (symbol, df) in enumerate(price_data.items(), 1):
            if df is None or df.empty:
                print(f"[{i}/{len(price_data)}] {symbol}: ⏭️  SKIPPED (no data)")
                continue

            print(f"[{i}/{len(price_data)}] {symbol}: ", end='', flush=True)

            try:
                # Create price store
                price_store = DataFramePriceStore(symbol, df)

                # Run analysis
                agent = PSXTechnicalAgent(price_store, config=self.tech_config)
                snapshot = agent.analyze_symbol_enhanced(symbol)

                snapshots[symbol] = snapshot

                # Display result
                bias_emoji = {
                    'Bullish': '📈',
                    'Bearish': '📉',
                    'Neutral': '↔️'
                }.get(snapshot.overall_bias.value, '❓')

                print(f"{bias_emoji} {snapshot.overall_bias.value} "
                      f"({snapshot.confidence:.0%} confidence)")

            except Exception as e:
                print(f"❌ ERROR: {str(e)}")

        return snapshots

    def _store_results(self, snapshots: Dict[str, EnhancedSnapshot]):
        """Store analysis results"""

        # Create snapshot for this run
        snapshot_file = (
            self.storage_paths['snapshots'] /
            f"snapshot_{self.run_date.strftime('%Y%m%d')}.json"
        )

        snapshot_data = {}

        for symbol, snapshot in snapshots.items():
            snapshot_data[symbol] = {
                'symbol': symbol,
                'date': snapshot.date,
                'overall_bias': snapshot.overall_bias.value,
                'confidence': snapshot.confidence,
                'ensemble_score': snapshot.ensemble_score,
                'regime': snapshot.regime,
                'strategy_signals': [
                    {
                        'strategy_name': sig.strategy_name,
                        'signal_type': sig.signal_type.value,
                        'confidence': sig.confidence,
                        'strength': sig.strength.value,
                    }
                    for sig in snapshot.strategy_signals
                ],
                'indicator_values': snapshot.indicator_values,
            }

        # Save to JSON
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f, indent=2)

        print(f"✅ Saved snapshot: {snapshot_file}")

        # Also save to database if enabled
        if self.config.storage.use_database:
            self._save_to_database(snapshots)

    def _save_to_database(self, snapshots: Dict[str, EnhancedSnapshot]):
        """Save results to SQLite database"""
        import sqlite3

        db_path = Path(self.config.storage.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                overall_bias TEXT,
                confidence REAL,
                ensemble_score REAL,
                regime TEXT,
                created_at TEXT,
                UNIQUE(date, symbol)
            )
        ''')

        # Insert/update records
        for symbol, snapshot in snapshots.items():
            cursor.execute('''
                INSERT OR REPLACE INTO daily_signals
                (date, symbol, overall_bias, confidence, ensemble_score, regime, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.date,
                symbol,
                snapshot.overall_bias.value,
                snapshot.confidence,
                snapshot.ensemble_score,
                snapshot.regime,
                self.run_timestamp.isoformat()
            ))

        conn.commit()
        conn.close()

        print(f"✅ Saved to database: {db_path}")

    def _generate_alerts(self, snapshots: Dict[str, EnhancedSnapshot]) -> List[Dict]:
        """Generate alerts based on signals"""

        alerts = []

        for symbol, snapshot in snapshots.items():
            # Check if meets alert criteria
            if snapshot.confidence < self.config.alerts.min_confidence:
                continue

            if abs(snapshot.ensemble_score) < self.config.alerts.min_score:
                continue

            # Check signal type
            if snapshot.overall_bias.value == 'Bullish' and not self.config.alerts.alert_on_bullish:
                continue
            if snapshot.overall_bias.value == 'Bearish' and not self.config.alerts.alert_on_bearish:
                continue
            if snapshot.overall_bias.value == 'Neutral' and not self.config.alerts.alert_on_neutral:
                continue

            # Create alert
            alert = {
                'symbol': symbol,
                'date': self.run_date.strftime('%Y-%m-%d'),
                'bias': snapshot.overall_bias.value,
                'confidence': snapshot.confidence,
                'score': snapshot.ensemble_score,
                'regime': snapshot.regime,
                'timestamp': self.run_timestamp.isoformat(),
            }

            alerts.append(alert)

            # Print to console
            if self.config.alerts.enable_console:
                self._print_alert(alert)

        # Save to file
        if self.config.alerts.enable_file and alerts:
            alert_file = (
                self.storage_paths['alerts'] /
                f"alerts_{self.run_date.strftime('%Y%m%d')}.json"
            )

            with open(alert_file, 'w') as f:
                json.dump(alerts, f, indent=2)

        return alerts

    def _print_alert(self, alert: Dict):
        """Print alert to console"""

        emoji = {
            'Bullish': '🔔 📈',
            'Bearish': '🔔 📉',
            'Neutral': '🔔 ↔️'
        }.get(alert['bias'], '🔔')

        print(f"{emoji} ALERT: {alert['symbol']}")
        print(f"   Signal: {alert['bias']}")
        print(f"   Confidence: {alert['confidence']:.0%}")
        print(f"   Score: {alert['score']:+.2f}")
        print(f"   Regime: {alert['regime']}")
        print()

    def _create_daily_report(self, snapshots: Dict[str, EnhancedSnapshot], alerts: List[Dict]):
        """Create daily summary report"""

        report_file = (
            self.storage_paths['results'] /
            f"report_{self.run_date.strftime('%Y%m%d')}.txt"
        )

        with open(report_file, 'w') as f:
            # Header
            f.write("="*80 + "\n")
            f.write(f"DAILY TECHNICAL ANALYSIS REPORT\n")
            f.write(f"Date: {self.run_date}\n")
            f.write(f"Generated: {self.run_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")

            # Summary statistics
            f.write("SUMMARY\n")
            f.write("-"*80 + "\n")

            total = len(snapshots)
            bullish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bullish')
            bearish = sum(1 for s in snapshots.values() if s.overall_bias.value == 'Bearish')
            neutral = total - bullish - bearish

            f.write(f"Total Analyzed:  {total}\n")
            f.write(f"Bullish:         {bullish} ({bullish/total*100:.1f}%)\n")
            f.write(f"Bearish:         {bearish} ({bearish/total*100:.1f}%)\n")
            f.write(f"Neutral:         {neutral} ({neutral/total*100:.1f}%)\n")
            f.write(f"Alerts:          {len(alerts)}\n\n")

            # Top signals
            f.write("TOP SIGNALS\n")
            f.write("-"*80 + "\n\n")

            # Bullish
            bullish_signals = [(sym, snap) for sym, snap in snapshots.items()
                             if snap.overall_bias.value == 'Bullish']
            bullish_signals.sort(key=lambda x: x[1].confidence, reverse=True)

            f.write(f"Bullish ({len(bullish_signals)}):\n")
            for i, (symbol, snapshot) in enumerate(bullish_signals[:10], 1):
                f.write(f"  {i:2d}. {symbol:8s}: {snapshot.confidence:5.0%} confidence, "
                       f"score: {snapshot.ensemble_score:+.2f}\n")
            f.write("\n")

            # Bearish
            bearish_signals = [(sym, snap) for sym, snap in snapshots.items()
                             if snap.overall_bias.value == 'Bearish']
            bearish_signals.sort(key=lambda x: x[1].confidence, reverse=True)

            f.write(f"Bearish ({len(bearish_signals)}):\n")
            for i, (symbol, snapshot) in enumerate(bearish_signals[:10], 1):
                f.write(f"  {i:2d}. {symbol:8s}: {snapshot.confidence:5.0%} confidence, "
                       f"score: {snapshot.ensemble_score:+.2f}\n")
            f.write("\n")

            # Detailed results
            f.write("="*80 + "\n")
            f.write("DETAILED RESULTS\n")
            f.write("="*80 + "\n\n")

            for symbol in sorted(snapshots.keys()):
                snapshot = snapshots[symbol]

                f.write(f"{symbol}\n")
                f.write(f"  Signal:     {snapshot.overall_bias.value}\n")
                f.write(f"  Confidence: {snapshot.confidence:.0%}\n")
                f.write(f"  Score:      {snapshot.ensemble_score:+.3f}\n")
                f.write(f"  Regime:     {snapshot.regime}\n")

                f.write(f"  Strategies:\n")
                for strat in snapshot.strategy_signals:
                    f.write(f"    - {strat.strategy_name:25s}: {strat.signal_type.value:12s} "
                           f"({strat.confidence:.0%})\n")

                f.write("\n")

        print(f"✅ Saved report: {report_file}")


if __name__ == "__main__":
    """Run daily analysis"""

    print("="*80)
    print("DAILY ANALYZER - TEST RUN")
    print("="*80)

    # Create analyzer
    analyzer = DailyAnalyzer()

    # Run analysis
    snapshots = analyzer.run_daily_analysis()

    print(f"\n{'='*80}")
    print(f"Test run complete!")
    print(f"Results saved to: {analyzer.storage_paths['base']}")
    print(f"{'='*80}")
