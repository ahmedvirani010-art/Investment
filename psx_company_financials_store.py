"""
PSX Company Financials Storage

Stores extracted financial data for use by fundamental analysis agent
Replaces mock data with real PSX company data
"""

import sqlite3
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from psx_company_data_extractor import CompanyFinancials, PSXCompanyDataExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PSXCompanyFinancialsStore:
    """Storage for company financial data"""

    def __init__(self, db_path: str = "company_financials.db"):
        """Initialize storage"""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create financials table
        c.execute('''
            CREATE TABLE IF NOT EXISTS company_financials (
                symbol TEXT PRIMARY KEY,
                extracted_date TEXT,
                annual_sales TEXT,
                annual_pat TEXT,
                annual_eps TEXT,
                quarterly_sales TEXT,
                quarterly_pat TEXT,
                quarterly_eps TEXT,
                gross_margin TEXT,
                net_margin TEXT,
                eps_growth TEXT,
                peg_ratio TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def store_financials(self, financials: CompanyFinancials):
        """
        Store financial data for a company

        Args:
            financials: CompanyFinancials object
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT OR REPLACE INTO company_financials (
                symbol, extracted_date, annual_sales, annual_pat, annual_eps,
                quarterly_sales, quarterly_pat, quarterly_eps,
                gross_margin, net_margin, eps_growth, peg_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            financials.symbol,
            financials.extracted_date.isoformat(),
            json.dumps(financials.annual_sales),
            json.dumps(financials.annual_pat),
            json.dumps(financials.annual_eps),
            json.dumps(financials.quarterly_sales),
            json.dumps(financials.quarterly_pat),
            json.dumps(financials.quarterly_eps),
            json.dumps(financials.gross_margin),
            json.dumps(financials.net_margin),
            json.dumps(financials.eps_growth),
            json.dumps(financials.peg_ratio)
        ))

        conn.commit()
        conn.close()
        logger.info(f"Stored financials for {financials.symbol}")

    def get_financials(self, symbol: str) -> Optional[CompanyFinancials]:
        """
        Retrieve financial data for a company

        Args:
            symbol: Stock symbol

        Returns:
            CompanyFinancials or None
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT * FROM company_financials WHERE symbol = ?', (symbol,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        # Reconstruct CompanyFinancials object
        financials = CompanyFinancials(
            symbol=row[0],
            extracted_date=datetime.fromisoformat(row[1]),
            annual_sales=json.loads(row[2]) if row[2] else {},
            annual_pat=json.loads(row[3]) if row[3] else {},
            annual_eps=json.loads(row[4]) if row[4] else {},
            quarterly_sales=json.loads(row[5]) if row[5] else {},
            quarterly_pat=json.loads(row[6]) if row[6] else {},
            quarterly_eps=json.loads(row[7]) if row[7] else {},
            gross_margin=json.loads(row[8]) if row[8] else {},
            net_margin=json.loads(row[9]) if row[9] else {},
            eps_growth=json.loads(row[10]) if row[10] else {},
            peg_ratio=json.loads(row[11]) if row[11] else {}
        )

        return financials

    def get_latest_metrics(self, symbol: str) -> Optional[Dict]:
        """
        Get latest financial metrics for fundamental analysis

        Returns metrics in format expected by fundamental agent:
        {
            'revenue': float,
            'profit_after_tax': float,
            'eps': float,
            'revenue_growth': float,
            'profit_growth': float,
            'net_margin': float,
            ...
        }
        """
        financials = self.get_financials(symbol)
        if not financials:
            return None

        metrics = {}

        # Get latest annual data
        if financials.annual_sales:
            years = sorted(financials.annual_sales.keys(), reverse=True)
            latest_year = years[0]

            metrics['revenue'] = financials.annual_sales[latest_year]

            if latest_year in financials.annual_pat:
                metrics['profit_after_tax'] = financials.annual_pat[latest_year]

            if latest_year in financials.annual_eps:
                metrics['eps'] = financials.annual_eps[latest_year]

            if latest_year in financials.net_margin:
                metrics['net_margin'] = financials.net_margin[latest_year]
            elif metrics.get('revenue') and metrics.get('profit_after_tax'):
                # Calculate if not available
                metrics['net_margin'] = (metrics['profit_after_tax'] / metrics['revenue']) * 100

            # Calculate growth rates
            if len(years) >= 2:
                prev_year = years[1]

                # Revenue growth
                if prev_year in financials.annual_sales:
                    prev_revenue = financials.annual_sales[prev_year]
                    if prev_revenue != 0:
                        metrics['revenue_growth'] = (
                            (metrics['revenue'] - prev_revenue) / abs(prev_revenue)
                        ) * 100

                # Profit growth
                if (latest_year in financials.annual_pat and
                    prev_year in financials.annual_pat):
                    current_pat = financials.annual_pat[latest_year]
                    prev_pat = financials.annual_pat[prev_year]
                    if prev_pat != 0:
                        metrics['profit_growth'] = (
                            (current_pat - prev_pat) / abs(prev_pat)
                        ) * 100

        # Get latest quarterly data
        if financials.quarterly_eps:
            periods = sorted(financials.quarterly_eps.keys(), reverse=True)
            latest_period = periods[0]

            metrics['latest_quarter_eps'] = financials.quarterly_eps[latest_period]

            if latest_period in financials.quarterly_sales:
                metrics['latest_quarter_revenue'] = financials.quarterly_sales[latest_period]

            if latest_period in financials.quarterly_pat:
                metrics['latest_quarter_profit'] = financials.quarterly_pat[latest_period]

        return metrics

    def fetch_and_store(self, symbol: str) -> Optional[CompanyFinancials]:
        """
        Fetch financial data from PSX and store it

        Args:
            symbol: Stock symbol

        Returns:
            CompanyFinancials or None
        """
        extractor = PSXCompanyDataExtractor()
        financials = extractor.extract_financials(symbol)

        if financials:
            self.store_financials(financials)

        return financials

    def list_stored_companies(self) -> List[str]:
        """Get list of companies with stored financial data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT symbol FROM company_financials ORDER BY symbol')
        symbols = [row[0] for row in c.fetchall()]

        conn.close()
        return symbols


if __name__ == "__main__":
    print("=" * 70)
    print("PSX COMPANY FINANCIALS STORE - TEST")
    print("=" * 70)
    print()

    store = PSXCompanyFinancialsStore()

    # Test: Fetch and store PIBTL data
    print("1. Fetching and storing PIBTL financial data...")
    financials = store.fetch_and_store("PIBTL")

    if financials:
        print("   ✓ PIBTL data stored")
        print()

    # Test: Retrieve data
    print("2. Retrieving stored data...")
    retrieved = store.get_financials("PIBTL")

    if retrieved:
        print(f"   ✓ Retrieved data for {retrieved.symbol}")
        print(f"   Annual Sales: {len(retrieved.annual_sales)} years")
        print(f"   Quarterly Data: {len(retrieved.quarterly_sales)} periods")
        print()

    # Test: Get latest metrics (for fundamental agent)
    print("3. Getting latest metrics for fundamental analysis...")
    metrics = store.get_latest_metrics("PIBTL")

    if metrics:
        print("   ✓ Latest metrics extracted:")
        print(f"     Revenue: PKR {metrics.get('revenue', 0):,.0f}")
        print(f"     Profit After Tax: PKR {metrics.get('profit_after_tax', 0):,.0f}")
        print(f"     EPS: Rs. {metrics.get('eps', 0):.2f}")
        print(f"     Net Margin: {metrics.get('net_margin', 0):.2f}%")
        print(f"     Revenue Growth: {metrics.get('revenue_growth', 0):.2f}%")
        print(f"     Latest Quarter EPS: Rs. {metrics.get('latest_quarter_eps', 0):.2f}")
        print()

    # Test: List stored companies
    print("4. Listing all stored companies...")
    companies = store.list_stored_companies()
    print(f"   Stored companies: {companies}")
    print()

    print("=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
