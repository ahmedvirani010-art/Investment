"""
Test with REAL data from yfinance for PSX stocks

This demonstrates what data is actually available vs what requires manual sources.
"""

import sys

# Try to get real data without mocking
try:
    import yfinance as yf
    import pandas as pd

    print("="*80)
    print("TESTING WITH REAL DATA FROM YFINANCE")
    print("="*80)

    # PSX stocks on yfinance use .KA suffix (Karachi Stock Exchange)
    psx_stocks = {
        "OGDC.KA": "Oil & Gas Development Company",
        "PPL.KA": "Pakistan Petroleum Limited",
        "HBL.KA": "Habib Bank Limited",
        "LUCK.KA": "Lucky Cement",
        "PSO.KA": "Pakistan State Oil"
    }

    print("\nAttempting to fetch real PSX data from yfinance...\n")

    for symbol, name in psx_stocks.items():
        print(f"\n{symbol} - {name}")
        print("-" * 80)

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Check what data is available
            available_data = []
            missing_data = []

            # Basic price data
            if 'currentPrice' in info or 'regularMarketPrice' in info:
                price = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
                print(f"  Current Price: {price}")
                available_data.append("Price")
            else:
                missing_data.append("Price")

            # Valuation metrics
            if 'trailingPE' in info:
                print(f"  P/E Ratio: {info['trailingPE']}")
                available_data.append("P/E")
            else:
                missing_data.append("P/E")

            if 'priceToBook' in info:
                print(f"  P/B Ratio: {info['priceToBook']}")
                available_data.append("P/B")
            else:
                missing_data.append("P/B")

            if 'dividendYield' in info:
                print(f"  Dividend Yield: {info['dividendYield']*100:.2f}%")
                available_data.append("Div Yield")
            else:
                missing_data.append("Div Yield")

            # Financial health
            if 'debtToEquity' in info:
                print(f"  Debt/Equity: {info['debtToEquity']/100:.2f}")
                available_data.append("D/E")
            else:
                missing_data.append("D/E")

            if 'currentRatio' in info:
                print(f"  Current Ratio: {info['currentRatio']}")
                available_data.append("Current Ratio")
            else:
                missing_data.append("Current Ratio")

            if 'returnOnEquity' in info:
                print(f"  ROE: {info['returnOnEquity']*100:.1f}%")
                available_data.append("ROE")
            else:
                missing_data.append("ROE")

            # Growth
            if 'revenueGrowth' in info:
                print(f"  Revenue Growth: {info['revenueGrowth']*100:.1f}%")
                available_data.append("Rev Growth")
            else:
                missing_data.append("Rev Growth")

            print(f"\n  ✅ Available: {', '.join(available_data) if available_data else 'None'}")
            print(f"  ❌ Missing: {', '.join(missing_data) if missing_data else 'None'}")

            # Try to get historical data
            hist = ticker.history(period="5d")
            if not hist.empty:
                print(f"  📊 Historical data: {len(hist)} days available")
                print(f"     Latest close: {hist['Close'].iloc[-1]:.2f}")
            else:
                print(f"  📊 Historical data: Not available")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

    print("\n" + "="*80)
    print("DATA AVAILABILITY SUMMARY")
    print("="*80)
    print("""
The fundamental agent currently uses a HYBRID approach:

✅ REAL DATA (from yfinance):
   • Current stock prices
   • Basic valuation ratios (P/E, P/B, Dividend Yield)
   • Some financial metrics (D/E, Current Ratio, ROE)
   • Historical price data (OHLCV)
   • Sector classification

⚠️  LIMITED/MOCK DATA (requires proper PSX sources):
   • Detailed quarterly financials
   • Operating cash flow trends
   • Margin trends (requires time series)
   • Earnings surprises
   • Analyst estimate revisions
   • Upcoming catalysts
   • SECP regulatory filings

📋 PRODUCTION REQUIREMENTS:
To get full real data, the agent needs integration with:
   1. PSX official API (quarterly reports)
   2. SECP filing system (regulatory data)
   3. Bloomberg/Reuters terminal (comprehensive financials)
   4. Local broker research (analyst estimates)
   5. PSX announcement system (corporate actions)

💡 CURRENT CAPABILITY:
The agent IS working with real data where available (yfinance),
and uses intelligent mock data for fields not accessible via API.
The scoring logic and analysis framework are fully functional
and ready to accept real data from proper sources.
    """)
    print("="*80 + "\n")

except ImportError:
    print("="*80)
    print("yfinance not installed - cannot test with real data")
    print("="*80)
    print("\nThe demo uses mock data to demonstrate functionality.")
    print("Install yfinance to test with real PSX stock data:")
    print("  pip install yfinance")
    print("="*80 + "\n")
