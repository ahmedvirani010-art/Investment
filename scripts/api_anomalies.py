"""
Bridge script: runs PSXAnomalyAgent and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_anomalies.py [lookback_days] [z_threshold] [symbol1,symbol2,...]
Symbols optional; if omitted uses default list of liquid PSX stocks.
"""
import sys
import os
import json
from datetime import datetime

# Ensure project root is on the path so psx_anomaly_agent can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_anomaly_agent import PSXAnomalyAgent, Anomaly, Severity, AnomalyType

def main():
    lookback_days = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    z_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
    symbols_arg = sys.argv[3] if len(sys.argv) > 3 else ""

    if symbols_arg.strip():
        symbols_list = [s.strip().upper().replace(".KA", "") for s in symbols_arg.split(",") if s.strip()]
    else:
        symbols_list = [
            "LUCK", "PSO", "HBL", "ENGRO", "MCB",
            "OGDC", "PPL", "UBL", "HUBC", "FFC",
        ]

    try:
        # Suppress "Analyzing..." prints
        devnull = open(os.devnull, "w", encoding="utf-8")
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            agent = PSXAnomalyAgent(lookback_days=lookback_days, z_threshold=z_threshold)
            report = agent.generate_report(symbols_list)
        finally:
            sys.stdout = old_stdout
            devnull.close()

        anomalies_flat = []
        for symbol, anomalies in report.items():
            for a in anomalies:
                anomalies_flat.append({
                    "symbol": a.symbol,
                    "date": a.date,
                    "type": a.anomaly_type.value if hasattr(a.anomaly_type, "value") else str(a.anomaly_type),
                    "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                    "value": a.value,
                    "baseline": a.baseline,
                    "z_score": a.z_score,
                    "description": a.description,
                })

        severity_counts = {}
        for a in anomalies_flat:
            s = a["severity"]
            severity_counts[s] = severity_counts.get(s, 0) + 1

        symbol_counts = {}
        for a in anomalies_flat:
            sym = a["symbol"]
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        top_anomalous = sorted(symbol_counts.items(), key=lambda x: -x[1])[:10]
        top_anomalous_stocks = [s[0] for s in top_anomalous]

        summary = {
            "total_anomalies": len(anomalies_flat),
            "severity_distribution": severity_counts,
            "top_anomalous_stocks": top_anomalous_stocks,
            "symbols_analyzed": len(symbols_list),
        }

        out = {
            "success": True,
            "data": {
                "anomalies": anomalies_flat,
                "summary": summary,
                "report_metadata": {
                    "lookback_days": lookback_days,
                    "z_threshold": z_threshold,
                    "analysis_date": datetime.now().isoformat(),
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
