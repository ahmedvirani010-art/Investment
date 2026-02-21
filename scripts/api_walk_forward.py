"""
Bridge script: runs walk-forward validation and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_walk_forward.py [symbol] [--period 365d] [--interval 1h] [--n-folds 4] [--n-components 7]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from walk_forward import run_walk_forward


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="BTC-USD", help="e.g. BTC-USD")
    parser.add_argument("--period", default="365d")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--n-folds", type=int, default=4)
    parser.add_argument("--n-components", type=int, default=7)
    args = parser.parse_args()

    result = run_walk_forward(
        symbol=args.symbol,
        period=args.period,
        interval=args.interval,
        n_components=args.n_components,
        n_folds=args.n_folds,
    )

    folds_payload = [
        {
            "fold": f.fold,
            "test_start": f.test_start,
            "test_end": f.test_end,
            "total_return_pct": f.total_return_pct,
            "buy_hold_return_pct": f.buy_hold_return_pct,
            "alpha_pct": f.alpha_pct,
            "win_rate": f.win_rate,
            "max_drawdown_pct": f.max_drawdown_pct,
            "n_trades": f.n_trades,
        }
        for f in result.folds
    ]

    out = {
        "folds": folds_payload,
        "mean_return_pct": result.mean_return_pct,
        "std_return_pct": result.std_return_pct,
        "min_return_pct": result.min_return_pct,
        "max_return_pct": result.max_return_pct,
        "mean_alpha_pct": result.mean_alpha_pct,
        "wins_vs_bh": result.wins_vs_bh,
        "n_folds": result.n_folds,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
