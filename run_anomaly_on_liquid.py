"""
Run Anomaly Detection on Top Liquid Stocks
"""
import json
from psx_anomaly_agent import PSXAnomalyAgent

# Load top liquid stocks
with open('top_liquid_stocks.json', 'r') as f:
    liquid_stocks = json.load(f)

print(f"Running anomaly detection on {len(liquid_stocks)} most liquid stocks...")
print(f"Stocks: {', '.join(liquid_stocks[:10])}... and {len(liquid_stocks)-10} more\n")

# Initialize anomaly agent
agent = PSXAnomalyAgent(lookback_days=60, z_threshold=2.5)

# Generate report
report = agent.generate_report(liquid_stocks)

# Print results
agent.print_report(report)
