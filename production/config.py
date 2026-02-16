"""
Production Configuration

Centralized configuration for production deployment.
Stores watchlists, alert settings, and scheduling parameters.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import json


@dataclass
class WatchlistConfig:
    """Configuration for stock watchlist"""

    # PSX Blue Chip stocks
    blue_chips: List[str] = field(default_factory=lambda: [
        'PPL',      # Pakistan Petroleum
        'OGDC',     # Oil & Gas Development Co
        'PSO',      # Pakistan State Oil
        'ENGRO',    # Engro Corporation
        'LUCK',     # Lucky Cement
        'MCB',      # MCB Bank
        'HBL',      # Habib Bank
        'UBL',      # United Bank
        'FFC',      # Fauji Fertilizer
        'HUBC',     # Hub Power Company
    ])

    # Custom watchlist (user-defined)
    custom: List[str] = field(default_factory=list)

    def get_all_symbols(self) -> List[str]:
        """Get all unique symbols from all watchlists"""
        all_symbols = set(self.blue_chips + self.custom)
        return sorted(list(all_symbols))


@dataclass
class AlertConfig:
    """Configuration for signal alerts"""

    # Alert thresholds
    min_confidence: float = 0.70  # Only alert if confidence >= 70%
    min_score: float = 0.50       # Only alert if abs(score) >= 0.5

    # Alert types
    alert_on_bullish: bool = True
    alert_on_bearish: bool = True
    alert_on_neutral: bool = False  # Usually don't alert on neutral

    # Alert on signal changes
    alert_on_change: bool = True  # Alert when signal changes from previous day

    # Notification channels
    enable_console: bool = True
    enable_email: bool = False
    enable_file: bool = True

    # Email settings (if enabled)
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None


@dataclass
class ScheduleConfig:
    """Configuration for automated scheduling"""

    # Run time (24-hour format)
    run_hour: int = 18  # 6 PM
    run_minute: int = 0

    # Days to run (Monday=0, Sunday=6)
    run_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Weekdays

    # Data collection
    history_days: int = 200  # Collect 200 days of history

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class StorageConfig:
    """Configuration for data storage"""

    # Base directory
    base_dir: str = "production_data"

    # Subdirectories
    results_dir: str = "results"        # Analysis results
    snapshots_dir: str = "snapshots"    # Daily snapshots
    alerts_dir: str = "alerts"          # Alert history
    logs_dir: str = "logs"              # Application logs

    # Retention (days)
    results_retention_days: int = 90
    logs_retention_days: int = 30

    # Database (SQLite for now)
    use_database: bool = True
    database_path: str = "production_data/signals.db"


@dataclass
class ProductionConfig:
    """Master production configuration"""

    watchlist: WatchlistConfig = field(default_factory=WatchlistConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    # Environment
    environment: str = "production"  # production, staging, development

    @classmethod
    def load_from_file(cls, config_path: str = "production/production_config.json") -> 'ProductionConfig':
        """
        Load configuration from JSON file

        Args:
            config_path: Path to config file

        Returns:
            ProductionConfig instance
        """
        path = Path(config_path)

        if not path.exists():
            # Create default config
            config = cls()
            config.save_to_file(config_path)
            return config

        with open(path, 'r') as f:
            data = json.load(f)

        # Parse nested configs
        config = cls(
            watchlist=WatchlistConfig(**data.get('watchlist', {})),
            alerts=AlertConfig(**data.get('alerts', {})),
            schedule=ScheduleConfig(**data.get('schedule', {})),
            storage=StorageConfig(**data.get('storage', {})),
            environment=data.get('environment', 'production')
        )

        return config

    def save_to_file(self, config_path: str = "production/production_config.json"):
        """
        Save configuration to JSON file

        Args:
            config_path: Path to save config
        """
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'watchlist': {
                'blue_chips': self.watchlist.blue_chips,
                'custom': self.watchlist.custom,
            },
            'alerts': {
                'min_confidence': self.alerts.min_confidence,
                'min_score': self.alerts.min_score,
                'alert_on_bullish': self.alerts.alert_on_bullish,
                'alert_on_bearish': self.alerts.alert_on_bearish,
                'alert_on_neutral': self.alerts.alert_on_neutral,
                'alert_on_change': self.alerts.alert_on_change,
                'enable_console': self.alerts.enable_console,
                'enable_email': self.alerts.enable_email,
                'enable_file': self.alerts.enable_file,
                'email_from': self.alerts.email_from,
                'email_to': self.alerts.email_to,
                'smtp_server': self.alerts.smtp_server,
                'smtp_port': self.alerts.smtp_port,
                'smtp_username': self.alerts.smtp_username,
                # Note: Don't save password to file in production
            },
            'schedule': {
                'run_hour': self.schedule.run_hour,
                'run_minute': self.schedule.run_minute,
                'run_days': self.schedule.run_days,
                'history_days': self.schedule.history_days,
                'max_retries': self.schedule.max_retries,
                'retry_delay_seconds': self.schedule.retry_delay_seconds,
            },
            'storage': {
                'base_dir': self.storage.base_dir,
                'results_dir': self.storage.results_dir,
                'snapshots_dir': self.storage.snapshots_dir,
                'alerts_dir': self.storage.alerts_dir,
                'logs_dir': self.storage.logs_dir,
                'results_retention_days': self.storage.results_retention_days,
                'logs_retention_days': self.storage.logs_retention_days,
                'use_database': self.storage.use_database,
                'database_path': self.storage.database_path,
            },
            'environment': self.environment,
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_storage_paths(self) -> Dict[str, Path]:
        """Get all storage paths"""
        base = Path(self.storage.base_dir)

        paths = {
            'base': base,
            'results': base / self.storage.results_dir,
            'snapshots': base / self.storage.snapshots_dir,
            'alerts': base / self.storage.alerts_dir,
            'logs': base / self.storage.logs_dir,
        }

        # Create directories
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        return paths


if __name__ == "__main__":
    """Test production config"""

    print("="*80)
    print("PRODUCTION CONFIG - TEST")
    print("="*80)

    # Create default config
    config = ProductionConfig()

    print(f"\nWatchlist ({len(config.watchlist.get_all_symbols())} symbols):")
    for symbol in config.watchlist.get_all_symbols():
        print(f"  - {symbol}")

    print(f"\nAlert Settings:")
    print(f"  Min Confidence: {config.alerts.min_confidence:.0%}")
    print(f"  Min Score: {config.alerts.min_score}")
    print(f"  Alert on Bullish: {config.alerts.alert_on_bullish}")
    print(f"  Alert on Bearish: {config.alerts.alert_on_bearish}")

    print(f"\nSchedule:")
    print(f"  Run Time: {config.schedule.run_hour:02d}:{config.schedule.run_minute:02d}")
    print(f"  Run Days: {config.schedule.run_days}")
    print(f"  History Days: {config.schedule.history_days}")

    print(f"\nStorage:")
    paths = config.get_storage_paths()
    for name, path in paths.items():
        print(f"  {name}: {path}")

    # Save to file
    config.save_to_file("production/production_config.json")
    print(f"\n✅ Config saved to production/production_config.json")

    # Load back
    loaded = ProductionConfig.load_from_file("production/production_config.json")
    print(f"✅ Config loaded successfully")

    print(f"\n{'='*80}")
