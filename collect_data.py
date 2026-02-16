#!/usr/bin/env python3
"""
CLI tool for collecting historical price data

Usage:
    # Collect single symbol
    python collect_data.py PPL --days 365

    # Collect multiple symbols
    python collect_data.py PPL OGDC PSO --days 180

    # Import from CSV
    python collect_data.py PPL --import-csv data/ppl_prices.csv

    # Force refresh (skip cache)
    python collect_data.py PPL --days 365 --force

    # Show cache info
    python collect_data.py --cache-info PPL

    # Clear cache
    python collect_data.py --clear-cache PPL
"""

import argparse
from datetime import datetime, timedelta
import sys
from pathlib import Path

from data_collection import DataCollectionManager


def collect_symbols(manager, symbols, days, force):
    """Collect data for symbols"""

    if len(symbols) == 1:
        # Single symbol
        symbol = symbols[0]
        print(f"\n{'='*80}")
        print(f"COLLECTING: {symbol}")
        print(f"{'='*80}\n")

        df = manager.collect(symbol, days=days, force_refresh=force)

        if df is not None:
            print(f"\n✅ Success!")
            print(f"   Symbol: {symbol}")
            print(f"   Rows: {len(df)}")
            print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"   Latest close: {df['Close'].iloc[-1]:.2f}")

            print(f"\nFirst 5 days:")
            print(df.head())

            print(f"\nLast 5 days:")
            print(df.tail())

            return 0
        else:
            print(f"\n❌ Failed to collect {symbol}")
            return 1

    else:
        # Batch collection
        results = manager.collect_batch(symbols, days=days)

        successful = sum(1 for df in results.values() if df is not None)

        if successful == len(symbols):
            print(f"\n✅ All {len(symbols)} symbols collected successfully")
            return 0
        else:
            failed = len(symbols) - successful
            print(f"\n⚠️  {successful}/{len(symbols)} symbols collected ({failed} failed)")
            return 1


def import_csv(manager, symbol, csv_path):
    """Import data from CSV file"""

    print(f"\n{'='*80}")
    print(f"IMPORTING CSV: {symbol}")
    print(f"{'='*80}\n")

    csv_file = Path(csv_path)

    if not csv_file.exists():
        print(f"❌ File not found: {csv_path}")
        return 1

    # Read CSV content
    with open(csv_file, 'r') as f:
        csv_text = f.read()

    # Import
    result = manager.import_csv_text(symbol, csv_text)

    if result.success:
        print(f"\n✅ Import successful!")
        print(f"   Symbol: {symbol}")
        print(f"   Rows: {result.rows_collected}")
        print(f"   Date range: {result.start_date.date()} to {result.end_date.date()}")
        return 0
    else:
        print(f"\n❌ Import failed: {result.error}")
        return 1


def show_cache_info(manager, symbol):
    """Show cache information"""

    print(f"\n{'='*80}")
    print(f"CACHE INFO: {symbol}")
    print(f"{'='*80}\n")

    info = manager.get_cache_info(symbol)

    if info:
        print(f"Symbol:        {info['symbol']}")
        print(f"Rows:          {info['rows']}")
        print(f"Start Date:    {info['start_date'].date()}")
        print(f"End Date:      {info['end_date'].date()}")
        print(f"Days:          {(info['end_date'] - info['start_date']).days}")
        print(f"File Size:     {info['file_size']:,} bytes")
        print(f"Last Modified: {info['last_modified']}")
        return 0
    else:
        print(f"❌ No cache found for {symbol}")
        return 1


def clear_cache(manager, symbol):
    """Clear cache for symbol"""

    print(f"\n{'='*80}")
    print(f"CLEAR CACHE: {symbol}")
    print(f"{'='*80}\n")

    manager.clear_cache(symbol)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical price data for PSX stocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Collect 1 year of PPL data:
    python collect_data.py PPL --days 365

  Collect multiple symbols:
    python collect_data.py PPL OGDC PSO --days 180

  Import from CSV:
    python collect_data.py PPL --import-csv data/ppl.csv

  Show cache info:
    python collect_data.py --cache-info PPL

  Clear cache:
    python collect_data.py --clear-cache PPL

  Force refresh (skip cache):
    python collect_data.py PPL --days 365 --force
        """
    )

    parser.add_argument(
        'symbols',
        nargs='*',
        help='Stock symbols to collect (e.g., PPL OGDC PSO)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days of history to collect (default: 365)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force refresh (skip cache)'
    )

    parser.add_argument(
        '--import-csv',
        metavar='CSV_FILE',
        help='Import data from CSV file (requires single symbol)'
    )

    parser.add_argument(
        '--cache-info',
        metavar='SYMBOL',
        help='Show cache information for symbol'
    )

    parser.add_argument(
        '--clear-cache',
        metavar='SYMBOL',
        help='Clear cache for symbol (or "all" for all symbols)'
    )

    parser.add_argument(
        '--storage-dir',
        default='data',
        help='Data storage directory (default: data)'
    )

    args = parser.parse_args()

    # Initialize manager
    manager = DataCollectionManager(storage_dir=args.storage_dir)

    # Handle different modes
    if args.cache_info:
        return show_cache_info(manager, args.cache_info)

    elif args.clear_cache:
        if args.clear_cache.lower() == 'all':
            manager.clear_cache(None)
            print("✅ Cleared all cache")
            return 0
        else:
            return clear_cache(manager, args.clear_cache)

    elif args.import_csv:
        if not args.symbols or len(args.symbols) != 1:
            print("❌ Error: --import-csv requires exactly one symbol")
            return 1

        return import_csv(manager, args.symbols[0], args.import_csv)

    elif args.symbols:
        return collect_symbols(manager, args.symbols, args.days, args.force)

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
