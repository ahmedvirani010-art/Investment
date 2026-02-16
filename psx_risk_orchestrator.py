"""
PSX Risk Orchestrator
Main control loop coordinating all risk management components
"""

import time
import yaml
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional, Dict
from pathlib import Path

from psx_price_store import PSXPriceStore
from psx_technical_agent import PSXTechnicalAgent
from psx_anomaly_agent import PSXAnomalyAgent
from psx_risk_storage import RiskStorage
from psx_risk_limits import RiskLimitEnforcer, PositionLimits, PortfolioLimits
from psx_risk_predictor import RiskPredictor
from psx_alert_engine import AlertEngine
from psx_position_manager import PositionManager
from psx_risk_monitor import RiskMonitor


class RiskOrchestrator:
    """
    Main orchestrator for proactive risk management

    Coordinates:
    - EOD analysis (daily at 4:00 PM)
    - Morning news brief (daily at 9:00 AM)
    - All risk management components
    """

    def __init__(self, config_path: str = "risk_config.yaml"):
        """
        Initialize risk orchestrator

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        print("Initializing PSX Risk Management System...")

        # Storage layer
        self.storage = RiskStorage()

        # Price store
        self.price_store = PSXPriceStore()

        # Existing agents
        self.technical_agent = PSXTechnicalAgent(self.price_store)
        self.anomaly_agent = PSXAnomalyAgent(self.price_store)

        # Risk limits
        position_limits = PositionLimits(**self.config.get('position_limits', {}))
        portfolio_limits = PortfolioLimits(**self.config.get('portfolio_limits', {}))
        self.limit_enforcer = RiskLimitEnforcer(position_limits, portfolio_limits)

        # Predictive engine
        self.predictor = RiskPredictor(
            self.price_store,
            self.technical_agent
        )

        # Alert engine
        alert_config = self.config.get('alerts', {})
        alert_config['eod_digest_mode'] = True  # Always use digest for position/swing
        self.alert_engine = AlertEngine(self.storage, alert_config)

        # Position manager
        auto_execute = self.config.get('execution', {}).get('auto_execute', False)
        self.position_manager = PositionManager(
            self.storage,
            self.alert_engine,
            self.limit_enforcer,
            self.price_store,
            auto_execute=auto_execute
        )

        # Risk monitor
        self.monitor = RiskMonitor(
            self.position_manager,
            self.alert_engine,
            self.limit_enforcer,
            self.predictor,
            self.anomaly_agent,
            self.technical_agent
        )

        # Scheduler
        self.scheduler = BackgroundScheduler()

        # Watchlist
        self.watchlist = self.config.get('watchlist', [])

        print("✓ Initialization complete\n")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found at {config_path}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'monitoring': {
                'eod_analysis_time': '16:00',
                'morning_brief_time': '09:00',
                'timezone': 'Asia/Karachi'
            },
            'position_limits': {},
            'portfolio_limits': {},
            'alerts': {
                'file_path': 'alerts/risk_alerts.log'
            },
            'execution': {
                'auto_execute': False,
                'dry_run': True
            },
            'watchlist': ['HBL', 'UBL', 'MCB', 'LUCK', 'ENGRO', 'PSO', 'OGDC', 'PPL']
        }

    def start(self) -> None:
        """Start continuous monitoring"""
        print("="*80)
        print("PSX PROACTIVE RISK MANAGEMENT SYSTEM")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"EOD Analysis: Daily at {self.config.get('monitoring', {}).get('eod_analysis_time', '16:00')}")
        print(f"Morning Brief: Daily at {self.config.get('monitoring', {}).get('morning_brief_time', '09:00')}")
        print(f"Auto-execute: {self.position_manager.auto_execute}")
        print(f"Watchlist: {len(self.watchlist)} symbols")
        print("="*80)
        print()

        # Schedule EOD analysis
        hour, minute = self._parse_time(
            self.config.get('monitoring', {}).get('eod_analysis_time', '16:00')
        )
        self.scheduler.add_job(
            self._run_eod_analysis,
            'cron',
            hour=hour,
            minute=minute,
            id='eod_analysis',
            timezone=self.config.get('monitoring', {}).get('timezone', 'Asia/Karachi')
        )
        print(f"✓ Scheduled EOD analysis: Daily at {hour:02d}:{minute:02d}")

        # Schedule morning news brief
        hour, minute = self._parse_time(
            self.config.get('monitoring', {}).get('morning_brief_time', '09:00')
        )
        self.scheduler.add_job(
            self._send_morning_brief,
            'cron',
            hour=hour,
            minute=minute,
            id='morning_brief',
            timezone=self.config.get('monitoring', {}).get('timezone', 'Asia/Karachi')
        )
        print(f"✓ Scheduled morning brief: Daily at {hour:02d}:{minute:02d}")

        # Start scheduler
        self.scheduler.start()
        print("\n✓ Scheduler started\n")

        # Run initial analysis
        print("Running initial EOD analysis...")
        self._run_eod_analysis()

        # Keep running
        try:
            print("\nSystem running. Press Ctrl+C to stop.\n")
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self) -> None:
        """Graceful shutdown"""
        print("\nShutting down risk management system...")
        self.scheduler.shutdown()
        print("✓ Shutdown complete")

    def _run_eod_analysis(self) -> None:
        """Execute EOD monitoring cycle"""
        print(f"\n{'#'*80}")
        print(f"# EOD ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        # Update prices for watchlist (bulk update)
        print("Updating prices for watchlist...")
        self.price_store.bulk_update(self.watchlist, days=100)

        # Run monitoring cycle
        self.monitor.run_eod_monitoring_cycle()

        # Send EOD digest
        print("\nPreparing EOD digest...")
        digest = self.alert_engine.send_eod_digest()
        print("\n" + "="*80)
        print("EOD DIGEST:")
        print("="*80)
        print(digest)
        print("="*80 + "\n")

        # Save digest to file
        digest_path = Path("alerts/eod_digest.txt")
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(digest_path, 'w') as f:
            f.write(digest)
        print(f"✓ EOD digest saved to {digest_path}\n")

    def _send_morning_brief(self) -> None:
        """Send morning news brief"""
        print(f"\n{'#'*80}")
        print(f"# MORNING NEWS BRIEF - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        # TODO: Integrate with PSXNewsAgent to fetch overnight news
        # For now, placeholder
        print("Morning news brief: Feature coming soon")
        print("Will scan overnight news for watchlist symbols\n")

    def _parse_time(self, time_str: str) -> tuple:
        """Parse time string (HH:MM) to hour, minute"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return hour, minute
        except Exception:
            return 16, 0  # Default to 4:00 PM

    def run_manual_analysis(self) -> None:
        """Run a manual analysis cycle (for testing)"""
        print("Running manual analysis cycle...\n")
        self._run_eod_analysis()


if __name__ == "__main__":
    # Allow running directly
    import argparse

    parser = argparse.ArgumentParser(description='PSX Proactive Risk Management System')
    parser.add_argument('--config', default='risk_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--manual', action='store_true',
                       help='Run manual analysis once and exit')

    args = parser.parse_args()

    orchestrator = RiskOrchestrator(config_path=args.config)

    if args.manual:
        orchestrator.run_manual_analysis()
    else:
        orchestrator.start()
