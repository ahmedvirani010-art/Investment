"""
NASDAQ HMM Regime Detection

Uses a Gaussian Hidden Markov Model to identify market regimes (e.g. bull, bear,
high/low volatility) from price and volume. Built for NASDAQ Composite (^IXIC)
and other NASDAQ-related yfinance symbols (e.g. QQQ). Same algorithm as the
generic engine: features are Returns, Range, Vol_Change from OHLCV.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_BACKEND = "hmmlearn"
except ImportError:
    GaussianHMM = None
    _HMM_BACKEND = None

try:
    from sklearn.mixture import GaussianMixture
    _GMM_AVAILABLE = True
except ImportError:
    GaussianMixture = None
    _GMM_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@dataclass
class RegimeSummaryRow:
    """Per-state regime statistics."""
    state: int
    mean_return: float
    volatility: float
    count: int


@dataclass
class HMMRegimeResult:
    """Result of fitting HMM and predicting states."""
    symbol: str
    period: str
    interval: str
    n_components: int
    summary: List[RegimeSummaryRow]
    states: List[int]
    timestamps: List[str]
    close_prices: List[float]
    last_state: int
    backend: str  # "hmmlearn" (true HMM) or "gmm" (fallback)


def get_data(
    symbol: str,
    period: str = "730d",
    interval: str = "1d",
) -> pd.DataFrame:
    """Download OHLCV and flatten MultiIndex columns if present. Retries once on failure."""
    import time
    required = ["Open", "High", "Low", "Close", "Volume"]
    for attempt in range(2):
        raw = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if raw is None or not isinstance(raw, pd.DataFrame):
            if attempt == 0:
                time.sleep(2)
                continue
            raise ValueError(
                f"No data returned for symbol {symbol!r} (period={period}, interval={interval}); download returned None or non-DataFrame)"
            )
        if raw.empty:
            if attempt == 0:
                time.sleep(2)
                continue
            raise ValueError(f"No data returned for symbol {symbol!r} (period={period}, interval={interval})")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        missing = [c for c in required if c not in raw.columns]
        if missing:
            if attempt == 0:
                time.sleep(2)
                continue
            raise ValueError(
                f"Missing columns {missing} for symbol {symbol!r} (period={period}, interval={interval})"
            )
        return raw[required].copy()
    raise ValueError(f"No data returned for symbol {symbol!r} (period={period}, interval={interval})")


def prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    """Compute Returns, Range, Vol_Change and drop inf/nan."""
    data = data.copy()
    data["Returns"] = data["Close"].pct_change()
    data["Range"] = (data["High"] - data["Low"]) / data["Close"].replace(0, np.nan)
    data["Vol_Change"] = data["Volume"].pct_change()
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data.dropna(inplace=True)
    return data


def _fit_with_gmm(X: np.ndarray, n_components: int, random_state: int) -> np.ndarray:
    """Fallback: use Gaussian Mixture Model when hmmlearn is not available (no C++ build)."""
    if not _GMM_AVAILABLE or GaussianMixture is None:
        raise ImportError(
            "Neither hmmlearn nor scikit-learn is available. "
            "Install with: pip install hmmlearn  OR  pip install scikit-learn"
        )
    model = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        max_iter=200,
        random_state=random_state,
        n_init=3,
    )
    model.fit(X)
    return model.predict(X)


def fit_predict_slices(
    X_train: np.ndarray,
    X_test: np.ndarray,
    returns_train: np.ndarray,
    n_components: int = 7,
    covariance_type: str = "full",
    n_iter: int = 1000,
    random_state: int = 42,
) -> tuple:
    """
    Fit HMM on train features, predict states on test features.
    returns_train: 1d array of returns aligned with X_train (for bull/bear state ids).

    Returns:
        (states_test, bull_state_id, bear_state_id)
    """
    if X_train.shape[0] != len(returns_train):
        raise ValueError("X_train and returns_train must have same length")
    if GaussianHMM is not None:
        model = GaussianHMM(
            n_components=n_components,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=random_state,
        )
        model.fit(X_train)
        states_train = model.predict(X_train)
        states_test = model.predict(X_test)
    else:
        states_train = _fit_with_gmm(X_train, n_components, random_state)
        model = None
        if _GMM_AVAILABLE and GaussianMixture is not None:
            gm = GaussianMixture(
                n_components=n_components,
                covariance_type="full",
                max_iter=200,
                random_state=random_state,
                n_init=3,
            )
            gm.fit(X_train)
            states_test = gm.predict(X_test)
        else:
            raise ImportError("Need hmmlearn or sklearn for fit_predict_slices")

    summary_df = (
        pd.DataFrame({"State": states_train, "Returns": returns_train})
        .groupby("State")
        .agg(Mean_Return=("Returns", "mean"), Count=("Returns", "count"))
        .sort_values("Mean_Return", ascending=False)
        .reset_index()
    )
    bull_state_id = int(summary_df["State"].iloc[0])
    bear_state_id = int(summary_df["State"].iloc[-1])
    return states_test.tolist() if hasattr(states_test, "tolist") else list(states_test), bull_state_id, bear_state_id


def fit_and_predict(
    symbol: str = "^IXIC",
    period: str = "730d",
    interval: str = "1d",
    n_components: int = 7,
    covariance_type: str = "full",
    n_iter: int = 1000,
    random_state: int = 42,
) -> HMMRegimeResult:
    """
    Download NASDAQ data, engineer features, fit Gaussian HMM (or GMM fallback), and return regime summary + states.
    Uses hmmlearn if available; otherwise uses sklearn GaussianMixture so no C++ build is required.
    """
    data = get_data(symbol, period=period, interval=interval)
    data = prepare_features(data)

    X = data[["Returns", "Range", "Vol_Change"]].values
    backend = "hmmlearn"

    if GaussianHMM is not None:
        model = GaussianHMM(
            n_components=n_components,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=random_state,
        )
        model.fit(X)
        states = model.predict(X)
    else:
        states = _fit_with_gmm(X, n_components, random_state)
        backend = "gmm"

    data = data.assign(State=states)

    summary_df = (
        data.groupby("State")
        .agg(
            Mean_Return=("Returns", "mean"),
            Volatility=("Returns", "std"),
            Count=("Returns", "count"),
        )
        .sort_values("Mean_Return", ascending=False)
        .reset_index()
    )

    summary = [
        RegimeSummaryRow(
            state=int(row["State"]),
            mean_return=float(row["Mean_Return"]),
            volatility=float(row["Volatility"]) if pd.notna(row["Volatility"]) else 0.0,
            count=int(row["Count"]),
        )
        for _, row in summary_df.iterrows()
    ]

    return HMMRegimeResult(
        symbol=symbol,
        period=period,
        interval=interval,
        n_components=n_components,
        summary=summary,
        states=states.tolist(),
        timestamps=[t.isoformat() if hasattr(t, "isoformat") else str(t) for t in data.index],
        close_prices=data["Close"].tolist(),
        last_state=int(states[-1]),
        backend=backend,
    )


def plot_regimes(
    result: HMMRegimeResult,
    last_n: int = 500,
    title: Optional[str] = None,
    out_path: Optional[str] = None,
) -> None:
    """Plot close price with points colored by HMM state (last_n bars)."""
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

    n = min(last_n, len(result.timestamps))
    if n <= 0:
        return
    ts = result.timestamps[-n:]
    close = result.close_prices[-n:]
    states = result.states[-n:]
    states_arr = np.array(states)
    unique_states = sorted(np.unique(states_arr))
    n_states = len(unique_states)
    colors = plt.cm.tab10(np.linspace(0, 1, max(n_states, 1)))
    state_color_map = {s: colors[i % len(colors)] for i, s in enumerate(unique_states)}

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(range(n), close, color="gray", linewidth=0.8, alpha=0.6, label="Close Price")
    for state in unique_states:
        mask = states_arr == state
        ax.scatter(
            np.where(mask)[0],
            np.array(close)[mask],
            color=state_color_map[state],
            s=10,
            label=f"State {state}",
            zorder=3,
        )
    ax.set_title(
        title or f"{result.symbol} Close — Market Regimes (Last {n} bars)",
        fontsize=14,
    )
    ax.set_xlabel("Bar index")
    ax.set_ylabel(f"{result.symbol} Price")
    ax.legend(loc="upper left", markerscale=2, fontsize=8)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=150)
        plt.close()
    else:
        plt.show()


def result_to_dict(result: HMMRegimeResult) -> Dict[str, Any]:
    """Serialize HMMRegimeResult to a JSON-serializable dict."""
    return {
        "symbol": result.symbol,
        "period": result.period,
        "interval": result.interval,
        "n_components": result.n_components,
        "last_state": result.last_state,
        "backend": result.backend,
        "summary": [
            {
                "state": r.state,
                "mean_return": r.mean_return,
                "volatility": r.volatility,
                "count": r.count,
            }
            for r in result.summary
        ],
        "states": result.states,
        "timestamps": result.timestamps,
        "close_prices": result.close_prices,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hidden Markov Model market regime detection for NASDAQ (yfinance: ^IXIC, QQQ, etc.)."
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        default="^IXIC",
        help="NASDAQ symbol to analyze (default ^IXIC for NASDAQ Composite, or QQQ)",
    )
    parser.add_argument(
        "--period",
        default="730d",
        help="yfinance period (e.g. 730d, 1y)",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        help="yfinance interval (e.g. 1d, 1h)",
    )
    parser.add_argument(
        "--n-components",
        type=int,
        default=7,
        help="Number of HMM states",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Show matplotlib plot of last N bars colored by regime",
    )
    parser.add_argument(
        "--plot-bars",
        type=int,
        default=500,
        help="Number of bars to include in plot (default 500)",
    )
    parser.add_argument(
        "--plot-save",
        metavar="PATH",
        help="Save plot to file instead of showing",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output full result as JSON to stdout",
    )
    args = parser.parse_args()

    try:
        result = fit_and_predict(
            symbol=args.symbol,
            period=args.period,
            interval=args.interval,
            n_components=args.n_components,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result_to_dict(result), indent=2))
        return 0

    print("\n=== Market Regime Summary ===")
    print(
        pd.DataFrame(
            [
                {
                    "State": r.state,
                    "Mean_Return": r.mean_return,
                    "Volatility": r.volatility,
                    "Count": r.count,
                }
                for r in result.summary
            ]
        ).to_string(index=False)
    )
    print(f"\nCurrent regime (last bar): state {result.last_state}")

    if args.plot or args.plot_save:
        plot_regimes(
            result,
            last_n=args.plot_bars,
            out_path=args.plot_save,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
