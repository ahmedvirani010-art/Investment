"""
Bridge script: runs multivariate (multi-asset) backtest and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_multivariate_backtest.py [--assets BTC-USD,GC=F] [--period 730d] [--n-components 7]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multivariate_config import get_assets
from multivariate_loader import load_and_align_assets
from multivariate_backtester import run_multivariate_backtest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assets",
        default=None,
        help="Comma-separated symbols to override default (e.g. BTC-USD,GC=F)",
    )
    parser.add_argument("--period", default="730d", help="yfinance period")
    parser.add_argument("--n-components", type=int, default=7, help="HMM components")
    args = parser.parse_args()

    assets = get_assets(args.assets)
    aligned = load_and_align_assets(
        assets,
        period=args.period,
        interval="1d",
        n_components=args.n_components,
    )
    result = run_multivariate_backtest(aligned)

    trades_payload = [
        {
            "asset": t.asset,
            "label": t.label,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "return_pct": t.return_pct,
            "leveraged_return_pct": t.leveraged_return_pct,
        }
        for t in result.trades
    ]

    out = {
        "current_signal": result.current_signal,
        "current_asset": result.current_asset,
        "current_asset_label": result.current_asset_label,
        "assets": result.assets,
        "timestamps": result.timestamps,
        "equity_curve": result.equity_curve,
        "trades": trades_payload,
        "total_return_pct": result.total_return_pct,
        "buy_hold_return_pct": result.buy_hold_return_pct,
        "alpha_pct": result.alpha_pct,
        "win_rate": result.win_rate,
        "max_drawdown_pct": result.max_drawdown_pct,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
