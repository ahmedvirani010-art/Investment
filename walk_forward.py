"""
Walk-forward validation for HMM Regime backtester.

Splits data into train/test folds (time-based), fits HMM on train, runs backtest on test.
Returns per-fold metrics and aggregates (mean, std, min, max).
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from backtester import run_backtest
from psx_hmm_regime import FEATURE_NAMES, get_data, prepare_features, fit_predict_slices


@dataclass
class WalkForwardFoldResult:
    fold: int
    test_start: str
    test_end: str
    total_return_pct: float
    buy_hold_return_pct: float
    alpha_pct: float
    win_rate: float
    max_drawdown_pct: float
    n_trades: int


@dataclass
class WalkForwardResult:
    folds: List[WalkForwardFoldResult]
    mean_return_pct: float
    std_return_pct: float
    min_return_pct: float
    max_return_pct: float
    mean_alpha_pct: float
    wins_vs_bh: int
    n_folds: int


def run_walk_forward(
    symbol: str = "BTC-USD",
    period: str = "365d",
    interval: str = "1h",
    n_components: int = 7,
    n_folds: int = 4,
    train_bars_ratio: float = 0.75,
    cooldown_hours: Optional[float] = None,
    leverage: Optional[float] = None,
    min_confirmations: Optional[int] = None,
) -> WalkForwardResult:
    """
    Run walk-forward validation: for each fold, fit HMM on train window, run backtest on test window.

    Folds are non-overlapping test windows at the end of the data. Train window is the preceding
    train_bars_ratio of the data before each test window (rolling).

    Returns:
        WalkForwardResult with per-fold metrics and aggregates.
    """
    df = get_data(symbol, period=period, interval=interval)
    df = prepare_features(df)
    n_total = len(df)
    if n_total < 500:
        raise ValueError(f"Not enough bars after prepare_features: {n_total}")

    if not all(c in df.columns for c in FEATURE_NAMES):
        raise ValueError(f"DataFrame must have {FEATURE_NAMES}")

    # Test window size: leave at least 2 folds of test data; train is the rest before it
    test_bars = max(24 * 14, n_total // (n_folds + 1))
    train_bars = int((n_total - test_bars * n_folds) * train_bars_ratio) if n_folds > 1 else int(n_total * train_bars_ratio)
    train_bars = max(200, train_bars)

    folds_out: List[WalkForwardFoldResult] = []
    for fold in range(n_folds):
        test_end = n_total - fold * test_bars
        test_start = test_end - test_bars
        train_end = test_start
        train_start = max(0, train_end - train_bars)
        if test_start < 0 or train_start >= train_end:
            break

        train_df = df.iloc[train_start:train_end]
        test_df = df.iloc[test_start:test_end].copy()

        X_train = train_df[FEATURE_NAMES].values
        X_test = test_df[FEATURE_NAMES].values
        returns_train = train_df["Returns"].values

        states_test, bull_id, bear_id, _ = fit_predict_slices(
            X_train, X_test, returns_train, n_components=n_components
        )
        test_df = test_df.assign(State=states_test)

        result = run_backtest(
            cooldown_hours=cooldown_hours,
            leverage=leverage,
            min_confirmations=min_confirmations,
            df=test_df,
            bull_state_id=bull_id,
            bear_state_id=bear_id,
        )

        test_start_ts = test_df.index[0]
        test_end_ts = test_df.index[-1]
        folds_out.append(
            WalkForwardFoldResult(
                fold=fold + 1,
                test_start=test_start_ts.isoformat() if hasattr(test_start_ts, "isoformat") else str(test_start_ts),
                test_end=test_end_ts.isoformat() if hasattr(test_end_ts, "isoformat") else str(test_end_ts),
                total_return_pct=result.total_return_pct,
                buy_hold_return_pct=result.buy_hold_return_pct,
                alpha_pct=result.alpha_pct,
                win_rate=result.win_rate,
                max_drawdown_pct=result.max_drawdown_pct,
                n_trades=len(result.trades),
            )
        )

    if not folds_out:
        raise ValueError("No folds produced; try fewer n_folds or longer period")

    returns = [f.total_return_pct for f in folds_out]
    alphas = [f.alpha_pct for f in folds_out]
    wins_vs_bh = sum(1 for f in folds_out if f.total_return_pct > f.buy_hold_return_pct)

    return WalkForwardResult(
        folds=folds_out,
        mean_return_pct=sum(returns) / len(returns),
        std_return_pct=pd.Series(returns).std() if len(returns) > 1 else 0.0,
        min_return_pct=min(returns),
        max_return_pct=max(returns),
        mean_alpha_pct=sum(alphas) / len(alphas),
        wins_vs_bh=wins_vs_bh,
        n_folds=len(folds_out),
    )
