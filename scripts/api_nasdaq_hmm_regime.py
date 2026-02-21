"""
Bridge script: runs NASDAQ HMM regime detection and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_nasdaq_hmm_regime.py [symbol] [--period 730d] [--interval 1d] [--n-components 7] [--last-n 500]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_hmm_regime import fit_and_predict, result_to_dict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="^IXIC", help="NASDAQ symbol (default ^IXIC for NASDAQ Composite)")
    parser.add_argument("--period", default="730d")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--n-components", type=int, default=7)
    parser.add_argument(
        "--last-n",
        type=int,
        default=500,
        help="Trim states/timestamps/close_prices to last N bars in JSON (0 = no trim)",
    )
    args = parser.parse_args()

    result = fit_and_predict(
        symbol=args.symbol or "^IXIC",
        period=args.period,
        interval=args.interval,
        n_components=args.n_components,
    )
    out = result_to_dict(result)
    if args.last_n > 0:
        n = min(args.last_n, len(out["states"]))
        out["states"] = out["states"][-n:]
        out["timestamps"] = out["timestamps"][-n:]
        out["close_prices"] = out["close_prices"][-n:]
        if "state_probabilities" in out and out["state_probabilities"] is not None:
            out["state_probabilities"] = out["state_probabilities"][-n:]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
