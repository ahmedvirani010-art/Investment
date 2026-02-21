"""
Bridge script: runs PSXLiquidityScreener and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_liquidity.py [lookback_days] [min_price] [top_n]
Stocks list: if stdin is not a TTY, read one line of JSON array of {ticker, name}.
If provided and non-empty, screen those stocks (e.g. from DB); else use built-in list.
"""
import sys
import os
import json
from datetime import datetime

# Ensure project root is on the path so psx_liquidity_screener can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import before redirecting stdout
from psx_liquidity_screener import PSXLiquidityScreener, StockLiquidity


def read_stocks_from_stdin():
    """Read optional list of {ticker, name} from stdin (one JSON line). Return None to use built-in list."""
    if sys.stdin.isatty():
        return None
    try:
        line = sys.stdin.readline()
        if not line or not line.strip():
            return None
        data = json.loads(line.strip())
        if not isinstance(data, list) or len(data) == 0:
            return None
        out = []
        for item in data:
            t = item.get("ticker") or item.get("symbol")
            n = item.get("name") or ""
            if t:
                out.append((str(t).strip().upper(), str(n).strip() or t))
        return out if out else None
    except (json.JSONDecodeError, TypeError):
        return None


def main():
    lookback_days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    min_price = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    stocks_override = read_stocks_from_stdin()

    try:
        # Suppress progress prints so only JSON is printed at the end
        devnull = open(os.devnull, "w", encoding="utf-8")
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            screener = PSXLiquidityScreener(lookback_days=lookback_days, min_price=min_price)
            results = screener.screen_stocks(top_n=top_n, stocks_override=stocks_override)
        finally:
            sys.stdout = old_stdout
            devnull.close()

        data = []
        for s in results:
            data.append({
                "symbol": s.symbol,
                "name": s.name,
                "avg_traded_value": s.avg_traded_value,
                "avg_volume": s.avg_volume,
                "avg_price": s.avg_price,
                "total_traded_value": s.total_traded_value,
                "current_price": s.current_price,
                "rank": s.rank,
                "trading_days": getattr(s, "trading_days", 0),
            })

        summary = {
            "total_stocks": len(data),
            "stocks_screened": getattr(screener, "last_screened_count", len(data)),
            "avg_traded_value": sum(r["avg_traded_value"] for r in data) / len(data) if data else 0,
            "top_stock": data[0] if data else None,
            "total_daily_value": sum(r["avg_traded_value"] for r in data),
        }

        out = {
            "success": True,
            "data": {"liquidity_analysis": data, "summary": summary},
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
