"""
Combined Analysis Report Generator
Combines liquidity screening with anomaly detection results
"""
import pandas as pd
import json
from datetime import datetime

# Load liquidity results
liquidity_df = pd.read_csv('psx_liquidity_top100.csv')

# Anomaly detection results (from the latest run)
anomaly_results = {
    'PPL': [
        {'type': 'Opening Gap', 'severity': 'LOW', 'description': 'Gap Down of -1.34%', 'z_score': -2.91, 'date': '2026-02-13'}
    ],
    'MLCF': [
        {'type': 'Opening Gap', 'severity': 'MEDIUM', 'description': 'Gap Down of -1.19%', 'z_score': -3.07, 'date': '2026-02-13'}
    ],
    'HMB': [
        {'type': 'Opening Gap', 'severity': 'MEDIUM', 'description': 'Gap Up of +2.64%', 'z_score': 3.59, 'date': '2026-02-13'},
        {'type': 'Price Movement', 'severity': 'LOW', 'description': 'Return +4.68% (avg: +0.19%)', 'z_score': 2.84, 'date': '2026-02-13'}
    ]
}

# Create combined report
combined_data = []

for _, row in liquidity_df.iterrows():
    symbol = row['Symbol']

    # Check if this stock has anomalies
    anomalies = anomaly_results.get(symbol, [])
    has_anomaly = len(anomalies) > 0

    # Count by severity
    high_count = sum(1 for a in anomalies if a['severity'] == 'HIGH')
    medium_count = sum(1 for a in anomalies if a['severity'] == 'MEDIUM')
    low_count = sum(1 for a in anomalies if a['severity'] == 'LOW')

    # Get latest anomaly details
    latest_anomaly = anomalies[0] if anomalies else None

    combined_data.append({
        'Rank': row['Rank'],
        'Symbol': symbol,
        'Company_Name': row['Company_Name'],
        'Avg_Traded_Value': row['Avg_Traded_Value_PKR'],
        'Current_Price': row['Current_Price_PKR'],
        'Has_Anomaly': '✓' if has_anomaly else '',
        'Total_Anomalies': len(anomalies),
        'High_Severity': high_count,
        'Medium_Severity': medium_count,
        'Low_Severity': low_count,
        'Latest_Anomaly_Type': latest_anomaly['type'] if latest_anomaly else '',
        'Latest_Anomaly_Severity': latest_anomaly['severity'] if latest_anomaly else '',
        'Latest_Anomaly_Description': latest_anomaly['description'] if latest_anomaly else '',
        'Latest_Z_Score': f"{latest_anomaly['z_score']:.2f}" if latest_anomaly else ''
    })

# Create DataFrame
combined_df = pd.DataFrame(combined_data)

# Save to CSV
filename = f"psx_combined_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
combined_df.to_csv(filename, index=False)

print("="*100)
print("PSX COMBINED LIQUIDITY + ANOMALY ANALYSIS REPORT")
print("="*100)
print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Total Stocks Analyzed: {len(combined_df)}")
print(f"Stocks with Anomalies: {combined_df['Has_Anomaly'].value_counts().get('✓', 0)}")
print(f"Total Anomalies Detected: {combined_df['Total_Anomalies'].sum()}")
print("\n" + "="*100)

# Show priority stocks (high liquidity + anomalies)
priority_stocks = combined_df[combined_df['Has_Anomaly'] == '✓'].head(10)

if not priority_stocks.empty:
    print("\n🎯 PRIORITY STOCKS (High Liquidity + Anomalies)")
    print("="*100)
    print(f"\n{'Rank':<6}{'Symbol':<10}{'Company':<35}{'Liquidity':<15}{'Anomalies':<12}{'Latest Type':<20}")
    print("-"*100)

    for _, stock in priority_stocks.iterrows():
        print(f"{stock['Rank']:<6}{stock['Symbol']:<10}{stock['Company_Name'][:33]:<35}"
              f"{stock['Avg_Traded_Value']:<15.0f}{stock['Total_Anomalies']:<12}"
              f"{stock['Latest_Anomaly_Type']:<20}")

    print("\n" + "="*100)

    # Detailed anomaly breakdown
    print("\n📊 DETAILED ANOMALY ANALYSIS")
    print("="*100)

    for _, stock in priority_stocks.iterrows():
        severity_icon = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(stock['Latest_Anomaly_Severity'], '⚪')

        print(f"\n{severity_icon} {stock['Symbol']} - {stock['Company_Name']}")
        print(f"   Liquidity Rank: #{stock['Rank']}")
        print(f"   Avg Traded Value: Rs {stock['Avg_Traded_Value']:,.0f}")
        print(f"   Current Price: Rs {stock['Current_Price']:.2f}")
        print(f"   Total Anomalies: {stock['Total_Anomalies']} (H:{stock['High_Severity']} M:{stock['Medium_Severity']} L:{stock['Low_Severity']})")
        print(f"   Latest: {stock['Latest_Anomaly_Type']} - {stock['Latest_Anomaly_Description']}")
        print(f"   Z-Score: {stock['Latest_Z_Score']}")

else:
    print("\n✅ No anomalies detected in liquid stocks. Market trading normally.")

# Top liquid stocks without anomalies
safe_stocks = combined_df[combined_df['Has_Anomaly'] == ''].head(10)

if not safe_stocks.empty:
    print("\n\n💚 SAFE LIQUID STOCKS (No Anomalies Detected)")
    print("="*100)
    print(f"\n{'Rank':<6}{'Symbol':<10}{'Company':<35}{'Avg Traded Value':<20}")
    print("-"*100)

    for _, stock in safe_stocks.iterrows():
        print(f"{stock['Rank']:<6}{stock['Symbol']:<10}{stock['Company_Name'][:33]:<35}"
              f"Rs {stock['Avg_Traded_Value']:,.0f}")

print("\n\n" + "="*100)
print(f"💾 Full report saved to: {filename}")
print("="*100)

# Trading recommendations
print("\n\n📋 TRADING RECOMMENDATIONS")
print("="*100)

if not priority_stocks.empty:
    print("\n🎯 HIGH PRIORITY (Liquid + Anomalies):")
    for _, stock in priority_stocks.head(5).iterrows():
        action = "⚠️ INVESTIGATE" if stock['Medium_Severity'] > 0 or stock['High_Severity'] > 0 else "👀 MONITOR"
        print(f"   {action} {stock['Symbol']:6s} - {stock['Latest_Anomaly_Type']}")

if not safe_stocks.empty:
    print("\n💚 SAFE HOLDINGS (Liquid, No Anomalies):")
    for _, stock in safe_stocks.head(5).iterrows():
        print(f"   ✅ HOLD    {stock['Symbol']:6s} - Trading normally")

print("\n" + "="*100)
