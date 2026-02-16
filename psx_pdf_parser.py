"""
PSX PDF Announcement Parser

Extracts financial data from PSX company announcement PDFs:
- Financial results (revenue, profit, EPS)
- Dividend announcements
- Balance sheet data
- Cash flow information
- Material corporate actions
"""

import os
import re
import requests
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import hashlib

try:
    import PyPDF2
    import fitz  # PyMuPDF
except ImportError:
    print("Installing PDF parsing libraries...")
    os.system("pip3 install PyPDF2 pymupdf --quiet")
    import PyPDF2
    import fitz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FinancialMetrics:
    """Structured financial metrics extracted from PDFs"""
    symbol: str
    period: str  # e.g., "Q1 2026", "FY 2025"
    period_end_date: Optional[datetime] = None

    # Income Statement
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_profit: Optional[float] = None
    profit_before_tax: Optional[float] = None
    profit_after_tax: Optional[float] = None
    eps: Optional[float] = None  # Earnings per share

    # Growth rates
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None

    # Margins
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None

    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None

    # Ratios
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None  # Return on equity
    roa: Optional[float] = None  # Return on assets

    # Dividends
    dividend_per_share: Optional[float] = None
    dividend_percentage: Optional[float] = None

    # Metadata
    source_pdf: Optional[str] = None
    extracted_date: datetime = None
    raw_data: Dict = None  # Store raw extracted text

    def __post_init__(self):
        if self.extracted_date is None:
            self.extracted_date = datetime.now()
        if self.raw_data is None:
            self.raw_data = {}


class PSXPDFParser:
    """Parser for PSX announcement PDFs"""

    PDF_CACHE_DIR = "pdf_cache"

    def __init__(self):
        """Initialize PDF parser"""
        # Create cache directory
        os.makedirs(self.PDF_CACHE_DIR, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_pdf(self, url: str) -> Optional[str]:
        """
        Download PDF from URL and cache it

        Args:
            url: PDF URL (can be relative or absolute)

        Returns:
            Path to cached PDF file, or None if download failed
        """
        # Resolve URL
        if url.startswith('/'):
            url = f"https://dps.psx.com.pk{url}"

        # Generate cache filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.PDF_CACHE_DIR, f"{url_hash}.pdf")

        # Check if already cached
        if os.path.exists(cache_path):
            logger.info(f"Using cached PDF: {cache_path}")
            return cache_path

        # Download PDF
        try:
            logger.info(f"Downloading PDF: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"PDF cached: {cache_path} ({len(response.content)} bytes)")
            return cache_path

        except Exception as e:
            logger.error(f"Failed to download PDF {url}: {e}")
            return None

    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""

                for page in reader.pages:
                    text += page.extract_text() + "\n"

                return text

        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""

    def extract_text_pymupdf(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (better for complex PDFs)"""
        try:
            text = ""
            doc = fitz.open(pdf_path)

            for page in doc:
                text += page.get_text() + "\n"

            doc.close()
            return text

        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return ""

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from PDF using best available method

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        # Try PyMuPDF first (best for PSX PDFs)
        text = self.extract_text_pymupdf(pdf_path)

        # Fallback to PyPDF2
        if not text or len(text) < 100:
            logger.warning("PyMuPDF extraction poor, trying PyPDF2...")
            text = self.extract_text_pypdf2(pdf_path)

        return text

    def parse_financial_results(
        self,
        text: str,
        symbol: str,
        period: Optional[str] = None
    ) -> Optional[FinancialMetrics]:
        """
        Parse financial metrics from PDF text

        Args:
            text: Extracted PDF text
            symbol: Stock symbol
            period: Period identifier (e.g., "Q1 2026")

        Returns:
            FinancialMetrics object or None
        """
        metrics = FinancialMetrics(
            symbol=symbol,
            period=period or "Unknown",
            raw_data={"text_length": len(text)}
        )

        # Clean text for parsing
        text_upper = text.upper()

        # Extract period if not provided
        if not period or period == "Unknown":
            metrics.period = self._extract_period(text)

        # Extract financial metrics using regex patterns

        # Revenue / Sales / Turnover
        revenue = self._extract_currency_value(text, [
            r'REVENUE[:\s]+([0-9,]+)',
            r'SALES[:\s]+([0-9,]+)',
            r'TURNOVER[:\s]+([0-9,]+)',
            r'TOTAL\s+REVENUE[:\s]+([0-9,]+)',
        ])
        if revenue:
            metrics.revenue = revenue

        # Profit After Tax
        pat = self._extract_currency_value(text, [
            r'PROFIT\s+AFTER\s+TAX[:\s]+([0-9,]+)',
            r'NET\s+PROFIT[:\s]+([0-9,]+)',
            r'PROFIT\s+FOR\s+THE\s+(?:PERIOD|YEAR|QUARTER)[:\s]+([0-9,]+)',
        ])
        if pat:
            metrics.profit_after_tax = pat

        # Profit Before Tax
        pbt = self._extract_currency_value(text, [
            r'PROFIT\s+BEFORE\s+TAX[:\s]+([0-9,]+)',
            r'PBT[:\s]+([0-9,]+)',
        ])
        if pbt:
            metrics.profit_before_tax = pbt

        # Gross Profit
        gp = self._extract_currency_value(text, [
            r'GROSS\s+PROFIT[:\s]+([0-9,]+)',
        ])
        if gp:
            metrics.gross_profit = gp

        # EPS (Earnings Per Share)
        eps = self._extract_decimal_value(text, [
            r'EARNINGS?\s+PER\s+SHARE[:\s]+(?:RS\.?\s*)?([0-9.,-]+)',
            r'EPS[:\s]+(?:RS\.?\s*)?([0-9.,-]+)',
            r'BASIC\s+EARNINGS\s+PER\s+SHARE[:\s]+(?:RS\.?\s*)?([0-9.,-]+)',
        ])
        if eps is not None:
            metrics.eps = eps

        # Calculate margins if we have revenue
        if metrics.revenue and metrics.revenue > 0:
            if metrics.gross_profit:
                metrics.gross_margin = (metrics.gross_profit / metrics.revenue) * 100

            if metrics.profit_after_tax:
                metrics.net_margin = (metrics.profit_after_tax / metrics.revenue) * 100

        # Total Assets
        assets = self._extract_currency_value(text, [
            r'TOTAL\s+ASSETS[:\s]+([0-9,]+)',
        ])
        if assets:
            metrics.total_assets = assets

        # Total Liabilities
        liabilities = self._extract_currency_value(text, [
            r'TOTAL\s+LIABILITIES[:\s]+([0-9,]+)',
        ])
        if liabilities:
            metrics.total_liabilities = liabilities

        # Equity / Shareholders' Equity
        equity = self._extract_currency_value(text, [
            r'SHAREHOLDERS?\s*\'?\s*EQUITY[:\s]+([0-9,]+)',
            r'TOTAL\s+EQUITY[:\s]+([0-9,]+)',
        ])
        if equity:
            metrics.equity = equity

        # Current Assets
        current_assets = self._extract_currency_value(text, [
            r'CURRENT\s+ASSETS[:\s]+([0-9,]+)',
        ])
        if current_assets:
            metrics.current_assets = current_assets

        # Current Liabilities
        current_liabilities = self._extract_currency_value(text, [
            r'CURRENT\s+LIABILITIES[:\s]+([0-9,]+)',
        ])
        if current_liabilities:
            metrics.current_liabilities = current_liabilities

        # Calculate ratios
        if metrics.current_assets and metrics.current_liabilities and metrics.current_liabilities > 0:
            metrics.current_ratio = metrics.current_assets / metrics.current_liabilities

        if metrics.total_liabilities and metrics.equity and metrics.equity > 0:
            metrics.debt_to_equity = metrics.total_liabilities / metrics.equity

        if metrics.profit_after_tax and metrics.equity and metrics.equity > 0:
            metrics.roe = (metrics.profit_after_tax / metrics.equity) * 100

        if metrics.profit_after_tax and metrics.total_assets and metrics.total_assets > 0:
            metrics.roa = (metrics.profit_after_tax / metrics.total_assets) * 100

        # Dividend
        dividend = self._extract_decimal_value(text, [
            r'DIVIDEND[:\s]+(?:RS\.?\s*)?([0-9.]+)\s*PER\s+SHARE',
            r'CASH\s+DIVIDEND[:\s]+(?:RS\.?\s*)?([0-9.]+)',
            r'DIVIDEND\s+@\s*([0-9.]+)%',
        ])
        if dividend is not None:
            # Check if it's a percentage or per-share amount
            if 'DIVIDEND @' in text_upper or 'DIVIDEND:' in text_upper:
                metrics.dividend_percentage = dividend
            else:
                metrics.dividend_per_share = dividend

        return metrics

    def _extract_period(self, text: str) -> str:
        """Extract period from text (e.g., 'Q1 2026', 'FY 2025')"""
        # Look for common period patterns
        patterns = [
            r'(?:QUARTER|Q)[\s-]*([1-4])[\s,]*(\d{4})',  # Q1 2026
            r'(?:YEAR|FY)[\s-]*(?:ENDED?)?[\s]*(\d{4})',  # FY 2025
            r'(?:PERIOD|QUARTER)\s+ENDED?\s+(?:DECEMBER|MARCH|JUNE|SEPTEMBER)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})\s+MONTHS?\s+ENDED?\s+.*?(\d{4})',  # 6 months ended ... 2025
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'QUARTER' in pattern or 'Q' in pattern:
                    return f"Q{match.group(1)} {match.group(2)}"
                elif 'MONTHS' in pattern:
                    months = match.group(1)
                    year = match.group(2)
                    if months == '6':
                        return f"H1 {year}"
                    elif months == '9':
                        return f"9M {year}"
                    elif months == '3':
                        return f"Q1 {year}"
                    return f"{months}M {year}"
                else:
                    return f"FY {match.group(1)}"

        return "Unknown"

    def _extract_currency_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """
        Extract currency value from text (handles thousands/millions)

        Handles formats like:
        - 9,969,183 (thousands)
        - 9,969 (millions in some reports)
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    value = float(value_str)

                    # PSX reports are typically in thousands (PKR '000)
                    # So multiply by 1000 to get actual value
                    # Check context for "in thousands" or similar
                    context = text[max(0, match.start()-200):match.end()+50]

                    if '000' in context.upper() or 'THOUSAND' in context.upper():
                        value = value * 1000

                    return value
                except ValueError:
                    continue

        return None

    def _extract_decimal_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extract decimal value (for EPS, ratios, etc.)"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')

                # Handle negative values in parentheses: (0.14)
                if value_str.startswith('(') and value_str.endswith(')'):
                    value_str = '-' + value_str[1:-1]

                try:
                    return float(value_str)
                except ValueError:
                    continue

        return None

    def parse_pdf_from_url(
        self,
        url: str,
        symbol: str,
        period: Optional[str] = None
    ) -> Optional[FinancialMetrics]:
        """
        Download PDF from URL and extract financial metrics

        Args:
            url: PDF URL
            symbol: Stock symbol
            period: Optional period identifier

        Returns:
            FinancialMetrics or None
        """
        # Download PDF
        pdf_path = self.download_pdf(url)
        if not pdf_path:
            return None

        # Extract text
        text = self.extract_text(pdf_path)
        if not text or len(text) < 100:
            logger.warning(f"Insufficient text extracted from PDF: {len(text)} chars")
            return None

        # Parse financial metrics
        metrics = self.parse_financial_results(text, symbol, period)
        if metrics:
            metrics.source_pdf = url

        return metrics

    def to_dict(self, metrics: FinancialMetrics) -> Dict:
        """Convert FinancialMetrics to dictionary"""
        data = asdict(metrics)

        # Convert datetime to string
        if data.get('period_end_date'):
            data['period_end_date'] = data['period_end_date'].isoformat()
        if data.get('extracted_date'):
            data['extracted_date'] = data['extracted_date'].isoformat()

        return data

    def to_json(self, metrics: FinancialMetrics, filepath: Optional[str] = None) -> str:
        """
        Convert FinancialMetrics to JSON

        Args:
            metrics: FinancialMetrics object
            filepath: Optional path to save JSON

        Returns:
            JSON string
        """
        data = self.to_dict(metrics)
        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
            logger.info(f"Saved metrics to: {filepath}")

        return json_str


if __name__ == "__main__":
    # Test with PIBTL latest financial results
    print("=" * 70)
    print("PSX PDF PARSER - TEST")
    print("=" * 70)
    print()

    parser = PSXPDFParser()

    # Test with PIBTL Q1 2026 results
    pibtl_q1_2026_url = "https://dps.psx.com.pk/download/document/270247.pdf"

    print(f"Testing with PIBTL Q1 2026 Financial Results")
    print(f"URL: {pibtl_q1_2026_url}")
    print()

    metrics = parser.parse_pdf_from_url(
        url=pibtl_q1_2026_url,
        symbol="PIBTL",
        period="Q1 2026"
    )

    if metrics:
        print("✓ Successfully extracted financial metrics!")
        print("=" * 70)
        print()

        print(f"Company: {metrics.symbol}")
        print(f"Period: {metrics.period}")
        print()

        print("INCOME STATEMENT:")
        print(f"  Revenue: PKR {metrics.revenue:,.0f}" if metrics.revenue else "  Revenue: N/A")
        print(f"  Gross Profit: PKR {metrics.gross_profit:,.0f}" if metrics.gross_profit else "  Gross Profit: N/A")
        print(f"  Profit Before Tax: PKR {metrics.profit_before_tax:,.0f}" if metrics.profit_before_tax else "  Profit Before Tax: N/A")
        print(f"  Profit After Tax: PKR {metrics.profit_after_tax:,.0f}" if metrics.profit_after_tax else "  Profit After Tax: N/A")
        print(f"  EPS: Rs. {metrics.eps:.2f}" if metrics.eps else "  EPS: N/A")
        print()

        print("MARGINS:")
        print(f"  Gross Margin: {metrics.gross_margin:.2f}%" if metrics.gross_margin else "  Gross Margin: N/A")
        print(f"  Net Margin: {metrics.net_margin:.2f}%" if metrics.net_margin else "  Net Margin: N/A")
        print()

        print("BALANCE SHEET:")
        print(f"  Total Assets: PKR {metrics.total_assets:,.0f}" if metrics.total_assets else "  Total Assets: N/A")
        print(f"  Total Liabilities: PKR {metrics.total_liabilities:,.0f}" if metrics.total_liabilities else "  Total Liabilities: N/A")
        print(f"  Equity: PKR {metrics.equity:,.0f}" if metrics.equity else "  Equity: N/A")
        print()

        print("RATIOS:")
        print(f"  Current Ratio: {metrics.current_ratio:.2f}" if metrics.current_ratio else "  Current Ratio: N/A")
        print(f"  Debt-to-Equity: {metrics.debt_to_equity:.2f}" if metrics.debt_to_equity else "  Debt-to-Equity: N/A")
        print(f"  ROE: {metrics.roe:.2f}%" if metrics.roe else "  ROE: N/A")
        print(f"  ROA: {metrics.roa:.2f}%" if metrics.roa else "  ROA: N/A")
        print()

        # Save to JSON
        json_path = "pibtl_q1_2026_metrics.json"
        parser.to_json(metrics, json_path)
        print(f"✓ Metrics saved to: {json_path}")

    else:
        print("✗ Failed to extract metrics")
