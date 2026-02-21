"""
Optuna-based strategy optimization for HMM Regime backtester.
Outputs JSON to stdout: best_params, best_value, trials_summary.
Usage: python scripts/optimize_hmm_backtest.py [symbol] [--period 730d] [--interval 1h] [--n-trials 20] [--metric total_return]
"""
import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import optuna
from optuna.samplers import TPESampler

from backtester import run_backtest

# Suppress Optuna INFO logs so stderr is cleaner for API
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Penalty value when a trial fails (e.g. data fetch); optimizer maximizes so use very low value
FAILED_TRIAL_VALUE = -1e9


def _run_one(
    symbol: str,
    period: str,
    interval: str,
    n_components: int,
    cooldown_hours: float,
    leverage: float,
    min_confirmations: int,
) -> float:
    """Run backtest with given params; return total_return_pct (for maximization)."""
    result = run_backtest(
        symbol=symbol,
        period=period,
        interval=interval,
        n_components=n_components,
        cooldown_hours=cooldown_hours,
        leverage=leverage,
        min_confirmations=min_confirmations,
    )
    return result.total_return_pct


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="BTC-USD", help="e.g. BTC-USD")
    parser.add_argument("--period", default="730d")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--n-trials", type=int, default=20, help="Optuna trials")
    parser.add_argument(
        "--metric",
        choices=["total_return", "sharpe_like"],
        default="total_return",
        help="total_return = maximize return; sharpe_like = return - 0.1 * max_drawdown",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    def objective(trial: optuna.Trial) -> float:
        cooldown_hours = trial.suggest_int("cooldown_hours", 24, 72)
        leverage = trial.suggest_float("leverage", 1.0, 1.5)
        min_confirmations = trial.suggest_int("min_confirmations", 5, 8)
        n_components = trial.suggest_int("n_components", 5, 9)

        try:
            if args.metric == "total_return":
                return _run_one(
                    args.symbol,
                    args.period,
                    args.interval,
                    n_components,
                    float(cooldown_hours),
                    leverage,
                    min_confirmations,
                )

            # sharpe_like: run backtest and combine return with drawdown penalty
            result = run_backtest(
                symbol=args.symbol,
                period=args.period,
                interval=args.interval,
                n_components=n_components,
                cooldown_hours=float(cooldown_hours),
                leverage=leverage,
                min_confirmations=min_confirmations,
            )
            return result.total_return_pct - 0.1 * result.max_drawdown_pct
        except (ValueError, TypeError, KeyError) as e:
            # Data fetch or backtest failure (e.g. no data, rate limit); don't crash the study
            logging.warning("Trial %s failed: %s", trial.number, e)
            return FAILED_TRIAL_VALUE

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=args.seed, n_startup_trials=5),
    )
    study.optimize(objective, n_trials=args.n_trials, show_progress_bar=False)

    # Build trials summary (top 10 by value); exclude failed trials from "best"
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE and (t.value or 0) > FAILED_TRIAL_VALUE + 1]
    completed.sort(key=lambda t: t.value or -1e9, reverse=True)
    trials_summary = [
        {
            "number": t.number,
            "value": round(t.value, 4) if t.value is not None else None,
            "params": t.params,
        }
        for t in completed[:10]
    ]

    # If all trials failed, best_params may be from a failed trial; prefer best successful trial
    if completed:
        best_trial = completed[0]
        best_params = best_trial.params
        best_value = best_trial.value
    else:
        best_params = study.best_params
        best_value = study.best_value

    out = {
        "best_params": best_params,
        "best_value": round(best_value, 4) if best_value is not None else None,
        "n_trials": args.n_trials,
        "n_completed_ok": len(completed),
        "metric": args.metric,
        "symbol": args.symbol,
        "period": args.period,
        "interval": args.interval,
        "trials_summary": trials_summary,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
