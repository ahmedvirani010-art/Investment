"""
Production Deployment Package

Automated daily analysis system with scheduling and alerts.

Components:
- config: Production configuration management
- daily_analyzer: Automated daily analysis
- scheduler: Job scheduling system

Quick Start:
    # Run analysis once
    python -m production.scheduler --once

    # Start scheduler
    python -m production.scheduler

    # Configure
    from production.config import ProductionConfig
    config = ProductionConfig.load_from_file()
    config.watchlist.custom.append('MYSYMBOL')
    config.save_to_file()
"""

from production.config import (
    ProductionConfig,
    WatchlistConfig,
    AlertConfig,
    ScheduleConfig,
    StorageConfig
)

from production.daily_analyzer import DailyAnalyzer
from production.scheduler import ProductionScheduler


__all__ = [
    'ProductionConfig',
    'WatchlistConfig',
    'AlertConfig',
    'ScheduleConfig',
    'StorageConfig',
    'DailyAnalyzer',
    'ProductionScheduler',
]
