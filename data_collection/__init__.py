"""
Data Collection Package

Provides tools for collecting historical price data from multiple sources.

Main Components:
- DataCollectionManager: High-level interface for data collection
- BaseDataCollector: Abstract base for implementing collectors
- CSVCollector: Import from CSV files
- YahooFinanceCollector: Fetch from Yahoo Finance API
- InvestingComCollector: Web scraper for investing.com

Quick Start:
    from data_collection import DataCollectionManager

    manager = DataCollectionManager()

    # Collect 1 year of data
    df = manager.collect('PPL', days=365)

    # Import from CSV
    result = manager.import_csv_text('PPL', csv_content)

    # Batch collection
    results = manager.collect_batch(['PPL', 'OGDC', 'PSO'])
"""

from data_collection.base_collector import (
    BaseDataCollector,
    CollectionResult,
    DataCollectorRegistry
)

from data_collection.csv_collector import CSVCollector
from data_collection.yahoo_finance_collector import YahooFinanceCollector
from data_collection.investing_com_collector import InvestingComCollector
from data_collection.data_manager import DataCollectionManager


__all__ = [
    'DataCollectionManager',
    'BaseDataCollector',
    'CollectionResult',
    'DataCollectorRegistry',
    'CSVCollector',
    'YahooFinanceCollector',
    'InvestingComCollector',
]
