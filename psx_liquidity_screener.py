"""
PSX Liquidity Screener Agent

Identifies the most liquid stocks on Pakistan Stock Exchange (PSX) based on
30-day average traded value (volume × price). This helps identify stocks with
sufficient liquidity for trading and investment.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json
import time


@dataclass
class StockLiquidity:
    """Represents liquidity metrics for a stock"""
    symbol: str
    name: str
    avg_traded_value: float  # 30-day average (volume × price)
    avg_volume: float
    avg_price: float
    total_traded_value: float
    trading_days: int
    current_price: float
    rank: int = 0


class PSXLiquidityScreener:
    """
    Screens Pakistan Stock Exchange for most liquid stocks

    Liquidity is measured by average daily traded value over 30 days:
    Traded Value = Volume × Price
    """

    def __init__(self, lookback_days: int = 30, min_price: float = 0.0):
        """
        Initialize the liquidity screener

        Args:
            lookback_days: Number of days to calculate average liquidity (default: 30)
            min_price: Minimum current price filter in PKR (default: 0.0 for no filter)
        """
        self.lookback_days = lookback_days
        self.min_price = min_price
        self.results = []

    def get_psx_stocks(self) -> List[Tuple[str, str]]:
        """
        Get comprehensive list of PSX stocks

        Returns:
            List of tuples (symbol, company_name)
        """
        # Comprehensive list of major PSX stocks
        # This list includes KSE-100 components and other actively traded stocks
        psx_stocks = [
            # Banks
            ("HBL", "Habib Bank Limited"),
            ("UBL", "United Bank Limited"),
            ("MCB", "MCB Bank Limited"),
            ("BAFL", "Bank Alfalah Limited"),
            ("ABL", "Allied Bank Limited"),
            ("BAHL", "Bank Al-Habib Limited"),
            ("MEBL", "Meezan Bank Limited"),
            ("NBP", "National Bank of Pakistan"),
            ("AKBL", "Askari Bank Limited"),
            ("FABL", "Faysal Bank Limited"),
            ("SNBL", "Soneri Bank Limited"),
            ("BOP", "Bank of Punjab"),
            ("HMB", "Habib Metropolitan Bank"),
            ("SCBPL", "Standard Chartered Bank Pakistan"),
            ("JSBL", "JS Bank Limited"),
            ("SNGP", "Sui Northern Gas Pipelines Limited"),

            # Oil & Gas
            ("OGDC", "Oil & Gas Development Company"),
            ("PPL", "Pakistan Petroleum Limited"),
            ("POL", "Pakistan Oilfields Limited"),
            ("MARI", "Mari Petroleum Company Limited"),
            ("PSO", "Pakistan State Oil"),
            ("APL", "Attock Petroleum Limited"),
            ("SSGC", "Sui Southern Gas Company"),

            # Cement
            ("LUCK", "Lucky Cement Limited"),
            ("DGKC", "D.G. Khan Cement Company"),
            ("MLCF", "Maple Leaf Cement Factory"),
            ("PIOC", "Pioneer Cement Limited"),
            ("CHCC", "Cherat Cement Company"),
            ("FCCL", "Fauji Cement Company Limited"),
            ("KOHC", "Kohat Cement Company Limited"),
            ("ACPL", "Attock Cement Pakistan Limited"),

            # Fertilizer
            ("FFC", "Fauji Fertilizer Company"),
            ("EFERT", "Engro Fertilizers Limited"),
            ("FATIMA", "Fatima Fertilizer Company"),

            # Power
            ("HUBC", "Hub Power Company"),
            ("KAPCO", "Kot Addu Power Company"),
            ("NPCC", "Nishat Power Limited"),
            ("LALPIR", "Lalpir Power Limited"),

            # Textile
            ("GATM", "Gul Ahmed Textile Mills"),
            ("NCL", "Nishat Chunian Limited"),
            ("NML", "Nishat Mills Limited"),
            ("KTML", "Kohinoor Textile Mills"),
            ("ADMM", "Adamjee Insurance Company"),

            # Food & Personal Care
            ("NESTLE", "Nestle Pakistan Limited"),
            ("EFOODS", "Engro Foods Limited"),
            ("UNITY", "Unity Foods Limited"),
            ("NATF", "Natco Pharma Limited"),

            # Automobiles & Parts
            ("INDU", "Indus Motor Company"),
            ("PSMC", "Pak Suzuki Motor Company"),
            ("HCAR", "Honda Atlas Cars Pakistan"),
            ("ATLH", "Atlas Honda Limited"),
            ("MTL", "Millat Tractors Limited"),
            ("GADT", "Ghandhara Automobiles Limited"),

            # Chemicals
            ("ENGRO", "Engro Corporation Limited"),
            ("ICI", "ICI Pakistan Limited"),
            ("EPCL", "Engro Polymer & Chemicals"),
            ("LOTTE", "Lotte Chemical Pakistan"),

            # Pharmaceuticals
            ("GLAXO", "GlaxoSmithKline Pakistan"),
            ("ABBOTT", "Abbott Laboratories Pakistan"),
            ("SEARL", "Searle Company Limited"),
            ("HINOON", "Hinopak Motors Limited"),

            # Technology & Communication
            ("TRG", "The Resource Group"),
            ("SYS", "Systems Limited"),
            ("NETSOL", "NetSol Technologies"),
            ("AVN", "Avanceon Limited"),
            ("PTCL", "Pakistan Telecommunication Company"),
            ("PTC", "Pakistan Tobacco Company"),

            # Steel & Engineering
            ("ASTL", "Amreli Steels Limited"),
            ("ISL", "International Steels Limited"),
            ("ASL", "Aisha Steel Mills Limited"),
            ("MUGHAL", "Mughal Iron & Steel Industries"),

            # Paper & Board
            ("CPPL", "Century Paper & Board Mills"),
            ("CHERAT", "Cherat Packaging Limited"),

            # Investment Companies
            ("PAEL", "Pakistan Aluminium Beverage Cans"),
            ("PIAA", "Pakistan International Airlines"),
            ("PKGS", "Packages Limited"),
            ("LOTCHEM", "Lotte Chemical Pakistan Limited"),

            # Miscellaneous
            ("PIA", "Pakistan International Airlines"),
            ("LOADS", "Loads Limited"),
            ("DAWH", "Dawood Hercules Corporation"),
            ("SHEL", "Shell Pakistan Limited"),
            ("COLG", "Colgate Palmolive Pakistan"),
            ("UNILEVER", "Unilever Pakistan Limited"),
            ("JPGL", "Jubilee Life Insurance"),
            ("SIEM", "Siemens Pakistan Engineering"),
            ("RMPL", "Rafhan Maize Products"),
            ("FLYNG", "Faysal Bank Limited"),
            ("BNWM", "Bannu Woollen Mills Limited"),
            ("AICL", "Archroma Pakistan Limited"),
            ("AKZO", "AkzoNobel Pakistan Limited"),
            ("GTYR", "General Tyre & Rubber Company"),
            ("BRRGM", "Berger Paints Pakistan Limited"),
            ("SHFA", "Shifa International Hospital"),
            ("ABOT", "Abbott Laboratories Pakistan"),
            ("HINOPAK", "Hinopak Motors Limited"),
            ("WAVES", "Waves Singer Pakistan Limited"),
            ("AIRLINK", "Airlink Communication Limited"),
            ("WTL", "WorldCall Telecom Limited"),
            ("PACE", "Pace Pakistan Limited"),

            # Additional KSE-100 components
            ("SILK", "Silk Bank Limited"),
            ("FEROZ", "Ferozsons Laboratories Limited"),
            ("FHAM", "Fauji Foods Limited"),
            ("ADOS", "Ados Pakistan Limited"),
            ("CLOV", "Clover Pakistan Limited"),
            ("AGTL", "AGP Limited"),
            ("THALL", "Thal Limited"),
            ("THCCL", "Thal Cement Limited"),
            ("RMPL", "Rafhan Maize Products Company"),
        ]

        return psx_stocks

    def fetch_liquidity_data(self, symbol: str, name: str) -> StockLiquidity:
        """
        Fetch and calculate liquidity metrics for a stock

        Args:
            symbol: Stock symbol
            name: Company name

        Returns:
            StockLiquidity object with calculated metrics
        """
        ticker_symbol = f"{symbol}.KA"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 10)

        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df.empty or len(df) < 5:  # Need at least 5 days of data
                return None

            # Calculate traded value for each day
            df['Traded_Value'] = df['Volume'] * df['Close']

            # Calculate metrics
            avg_traded_value = df['Traded_Value'].mean()
            avg_volume = df['Volume'].mean()
            avg_price = df['Close'].mean()
            total_traded_value = df['Traded_Value'].sum()
            trading_days = len(df)
            current_price = df['Close'].iloc[-1]

            return StockLiquidity(
                symbol=symbol,
                name=name,
                avg_traded_value=avg_traded_value,
                avg_volume=avg_volume,
                avg_price=avg_price,
                total_traded_value=total_traded_value,
                trading_days=trading_days,
                current_price=current_price
            )

        except Exception as e:
            print(f"  ⚠️  Error fetching {symbol}: {str(e)[:50]}")
            return None

    def screen_stocks(self, top_n: int = 100) -> List[StockLiquidity]:
        """
        Screen all PSX stocks and return top N by liquidity

        Args:
            top_n: Number of top stocks to return (default: 100)

        Returns:
            List of StockLiquidity objects sorted by traded value
        """
        stocks = self.get_psx_stocks()
        total_stocks = len(stocks)

        print(f"\n🔍 Screening {total_stocks} PSX stocks for liquidity...")
        print(f"📊 Period: {self.lookback_days} days")
        if self.min_price > 0:
            print(f"💰 Price Filter: Minimum Rs {self.min_price:.2f}")
        print(f"🎯 Target: Top {top_n} most liquid stocks\n")

        liquidity_data = []
        filtered_count = 0

        for idx, (symbol, name) in enumerate(stocks, 1):
            print(f"[{idx}/{total_stocks}] Analyzing {symbol:10s} - {name[:40]:<40s}", end='\r')

            result = self.fetch_liquidity_data(symbol, name)

            if result:
                # Apply price filter
                if self.min_price > 0 and result.current_price < self.min_price:
                    filtered_count += 1
                    continue

                liquidity_data.append(result)

            # Rate limiting to avoid API throttling
            time.sleep(0.1)

        print("\n")

        if filtered_count > 0:
            print(f"🔍 Filtered out {filtered_count} stocks below Rs {self.min_price:.2f}\n")

        # Sort by average traded value
        liquidity_data.sort(key=lambda x: x.avg_traded_value, reverse=True)

        # Assign ranks
        for rank, stock in enumerate(liquidity_data, 1):
            stock.rank = rank

        # Return top N
        top_stocks = liquidity_data[:top_n]

        self.results = top_stocks
        return top_stocks

    def print_report(self, stocks: List[StockLiquidity], top_n: int = 100):
        """Print formatted liquidity report"""
        if not stocks:
            print("❌ No stocks found with sufficient data.")
            return

        print("\n" + "="*100)
        print(f"PSX TOP {min(top_n, len(stocks))} MOST LIQUID STOCKS")
        print("="*100)
        print(f"Analysis Period: {self.lookback_days} days")
        print(f"Metric: Average Daily Traded Value (Volume × Price)")
        if self.min_price > 0:
            print(f"Price Filter: Minimum Rs {self.min_price:.2f}")
        print(f"Total Stocks Analyzed: {len(stocks)}")
        print("="*100)

        print(f"\n{'Rank':<6}{'Symbol':<10}{'Company Name':<40}{'Avg Traded Value':<18}{'Avg Volume':<15}{'Price':<10}")
        print("-"*100)

        for stock in stocks:
            avg_value_str = self._format_currency(stock.avg_traded_value)
            avg_volume_str = self._format_number(stock.avg_volume)
            price_str = f"Rs {stock.current_price:.2f}"

            print(f"{stock.rank:<6}{stock.symbol:<10}{stock.name[:38]:<40}{avg_value_str:<18}{avg_volume_str:<15}{price_str:<10}")

        print("="*100)

        # Summary statistics
        total_avg_value = sum(s.avg_traded_value for s in stocks)
        print(f"\n📊 Summary Statistics:")
        print(f"   Total Combined Daily Traded Value: {self._format_currency(total_avg_value)}")
        print(f"   Average per Stock: {self._format_currency(total_avg_value / len(stocks))}")
        print(f"   Top Stock ({stocks[0].symbol}): {self._format_currency(stocks[0].avg_traded_value)}")
        print(f"   #{len(stocks)} Stock ({stocks[-1].symbol}): {self._format_currency(stocks[-1].avg_traded_value)}")
        print()

    def save_to_csv(self, stocks: List[StockLiquidity], filename: str = "psx_liquidity_top100.csv"):
        """Save results to CSV file"""
        if not stocks:
            print("❌ No data to save.")
            return

        data = {
            'Rank': [s.rank for s in stocks],
            'Symbol': [s.symbol for s in stocks],
            'Company_Name': [s.name for s in stocks],
            'Avg_Traded_Value_PKR': [s.avg_traded_value for s in stocks],
            'Avg_Volume': [s.avg_volume for s in stocks],
            'Avg_Price_PKR': [s.avg_price for s in stocks],
            'Current_Price_PKR': [s.current_price for s in stocks],
            'Total_30Day_Value_PKR': [s.total_traded_value for s in stocks],
            'Trading_Days': [s.trading_days for s in stocks],
        }

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"💾 Results saved to: {filename}")

    def save_to_json(self, stocks: List[StockLiquidity], filename: str = "psx_liquidity_top100.json"):
        """Save results to JSON file"""
        if not stocks:
            print("❌ No data to save.")
            return

        data = {
            'generated_at': datetime.now().isoformat(),
            'lookback_days': self.lookback_days,
            'total_stocks': len(stocks),
            'stocks': [
                {
                    'rank': s.rank,
                    'symbol': s.symbol,
                    'name': s.name,
                    'avg_traded_value': s.avg_traded_value,
                    'avg_volume': s.avg_volume,
                    'avg_price': s.avg_price,
                    'current_price': s.current_price,
                    'total_traded_value': s.total_traded_value,
                    'trading_days': s.trading_days,
                }
                for s in stocks
            ]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 Results saved to: {filename}")

    def get_symbols_list(self, stocks: List[StockLiquidity]) -> List[str]:
        """Get list of symbols for easy integration with other tools"""
        return [stock.symbol for stock in stocks]

    @staticmethod
    def _format_currency(value: float) -> str:
        """Format value as Pakistani Rupees"""
        if value >= 1_000_000_000:
            return f"Rs {value/1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"Rs {value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"Rs {value/1_000:.2f}K"
        else:
            return f"Rs {value:.2f}"

    @staticmethod
    def _format_number(value: float) -> str:
        """Format large numbers with M/K suffix"""
        if value >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value/1_000:.2f}K"
        else:
            return f"{value:.0f}"


def main():
    """Run the PSX liquidity screener"""

    # Initialize screener with price filter
    screener = PSXLiquidityScreener(lookback_days=30, min_price=20.0)

    # Screen stocks and get top 100
    top_100 = screener.screen_stocks(top_n=100)

    # Print report
    screener.print_report(top_100, top_n=100)

    # Save results
    screener.save_to_csv(top_100)
    screener.save_to_json(top_100)

    # Print symbols list for easy copy-paste
    symbols = screener.get_symbols_list(top_100)
    print(f"\n📋 Top 100 Symbols (for use in other tools):")
    print(f"   {symbols[:20]}")  # Show first 20
    print(f"   ... and {len(symbols)-20} more")
    print(f"\n✅ Screening complete! Found {len(top_100)} liquid stocks.")


if __name__ == "__main__":
    main()
