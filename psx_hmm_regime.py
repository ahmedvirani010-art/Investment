"""
PSX HMM Regime Detection

Uses a 7-state Gaussian HMM with full covariance to identify market regimes.
Five engineered features: log returns, realized vol (20d), normalized RSI (14),
volume ratio (vs 20d avg), price momentum (20d). Robust training: 10 random
restarts, 200 EM iterations, best by log-likelihood. Supports rolling
retraining every 20 calendar days on 252 trading days. Built for the 7 assets:
Bitcoin, Gold, Crude Oil, Silver, NASDAQ, NIKKEI, S&P 500 (and any yfinance symbol).
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# Canonical 5 feature names for HMM (plan)
FEATURE_NAMES = [
    "LOG_RETURNS",
    "REALIZED_VOL_20D",
    "RSI_NORM",
    "VOLUME_RATIO_20D",
    "MOMENTUM_20D",
]

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
    # New fields (optional for backward compat)
    aic: Optional[float] = None
    bic: Optional[float] = None
    transition_matrix: Optional[List[List[float]]] = None
    days_in_current_regime: Optional[int] = None
    state_probabilities: Optional[List[float]] = None  # confidence per timestep for predicted state
    last_confidence: Optional[float] = None  # state_probabilities[-1] when available


def get_data(
    symbol: str,
    period: str = "730d",
    interval: str = "1h",
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


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (14) then clip to avoid inf; normalize to [0, 1] for HMM."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=1).mean()
    avg_loss = loss.rolling(period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    rsi_norm = (rsi - 50) / 50.0  # roughly [-1, 1], then clip
    return rsi_norm.clip(-1.5, 1.5)


def prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Five engineered features per timestep for 7-state GaussianHMM:
    log returns, realized vol (20d), normalized RSI (14), volume ratio (20d), momentum (20d).
    Also keeps Returns for regime labeling (mean return per state).
    """
    data = data.copy()
    # Returns for labeling (mean return per state)
    data["Returns"] = data["Close"].pct_change()
    # Log returns
    data["LOG_RETURNS"] = np.log(data["Close"] / data["Close"].shift(1))
    # Realized volatility 20d (rolling std of log returns)
    data["REALIZED_VOL_20D"] = data["LOG_RETURNS"].rolling(20, min_periods=5).std()
    # Normalized RSI (14)
    data["RSI_NORM"] = _rsi(data["Close"], 14)
    # Volume ratio vs 20d average
    vol_20 = data["Volume"].rolling(20, min_periods=1).mean().replace(0, np.nan)
    data["VOLUME_RATIO_20D"] = (data["Volume"] / vol_20).fillna(1.0)
    # Price momentum 20d: (Close - Close_20d_ago) / Close_20d_ago
    data["MOMENTUM_20D"] = (data["Close"] - data["Close"].shift(20)) / data["Close"].shift(20).replace(0, np.nan)
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data.dropna(inplace=True)
    # Clip extreme volume ratio for stability
    if "VOLUME_RATIO_20D" in data.columns:
        data["VOLUME_RATIO_20D"] = data["VOLUME_RATIO_20D"].clip(0.01, 10.0)
    return data


def prepare_features_legacy(data: pd.DataFrame) -> pd.DataFrame:
    """Legacy 3 features (Returns, Range, Vol_Change) for backward compatibility."""
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


def _confidence_from_posteriors(posteriors: np.ndarray, states: np.ndarray) -> List[float]:
    """Confidence at each timestep = posterior probability of the predicted state."""
    n = len(states)
    out: List[float] = []
    for i in range(n):
        s = int(states[i])
        if 0 <= s < posteriors.shape[1]:
            out.append(float(posteriors[i, s]))
        else:
            out.append(0.0)
    return out


def _fit_best_hmm(
    X: np.ndarray,
    n_components: int = 7,
    covariance_type: str = "full",
    n_iter: int = 200,
    n_restarts: int = 10,
) -> Tuple[Any, np.ndarray, Optional[float], Optional[float], Optional[List[List[float]]], Optional[List[float]]]:
    """
    Fit GaussianHMM with multiple random restarts; select best by log-likelihood.
    Returns (best_model, states, aic, bic, transition_matrix, confidences).
    """
    if GaussianHMM is None:
        return None, _fit_with_gmm(X, n_components, 42), None, None, None, None
    best_model = None
    best_score = -np.inf
    best_states = None
    best_confidences: Optional[List[float]] = None
    for seed in range(n_restarts):
        model = GaussianHMM(
            n_components=n_components,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=seed,
        )
        try:
            model.fit(X)
            score = model.score(X)
            if score > best_score:
                best_score = score
                best_model = model
                best_states = model.predict(X)
                posteriors = getattr(model, "predict_proba", None)
                if posteriors is not None:
                    try:
                        P = posteriors(X)
                        best_confidences = _confidence_from_posteriors(P, best_states)
                    except Exception:
                        best_confidences = None
                else:
                    best_confidences = None
        except Exception:
            continue
    if best_model is None:
        model = GaussianHMM(
            n_components=n_components,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=42,
        )
        best_model = model
        best_model.fit(X)
        best_states = best_model.predict(X)
        best_confidences = None
        posteriors = getattr(best_model, "predict_proba", None)
        if posteriors is not None:
            try:
                P = posteriors(X)
                best_confidences = _confidence_from_posteriors(P, best_states)
            except Exception:
                pass
    d = X.shape[1]
    n_params = (
        n_components * n_components  # transmat
        + n_components  # startprob
        + n_components * (d + d * (d + 1) // 2)  # means + cov full per state
    )
    n_obs = X.shape[0]
    log_lik = best_model.score(X)
    aic = 2 * n_params - 2 * log_lik
    bic = np.log(n_obs) * n_params - 2 * log_lik
    transmat: Optional[List[List[float]]] = None
    if hasattr(best_model, "transmat_"):
        transmat = best_model.transmat_.tolist()
    return best_model, best_states, float(aic), float(bic), transmat, best_confidences


def _days_in_current_regime(states: np.ndarray) -> int:
    """Count consecutive same state at the end of the sequence."""
    if len(states) == 0:
        return 0
    last = states[-1]
    n = 0
    for i in range(len(states) - 1, -1, -1):
        if states[i] != last:
            break
        n += 1
    return n


def fit_predict_slices(
    X_train: np.ndarray,
    X_test: np.ndarray,
    returns_train: np.ndarray,
    n_components: int = 7,
    covariance_type: str = "full",
    n_iter: int = 200,
    n_restarts: int = 10,
) -> Tuple[List[int], int, int, Optional[List[float]]]:
    """
    Fit HMM on train features (10 restarts, 200 EM), predict states on test.
    returns_train: 1d array of returns aligned with X_train (for bull/bear state ids).
    Returns:
        (states_test, bull_state_id, bear_state_id, confidence_test or None)
    """
    if X_train.shape[0] != len(returns_train):
        raise ValueError("X_train and returns_train must have same length")
    confidence_test: Optional[List[float]] = None
    if GaussianHMM is not None:
        model, states_train, _aic, _bic, _transmat, _ = _fit_best_hmm(
            X_train, n_components=n_components, covariance_type=covariance_type, n_iter=n_iter, n_restarts=n_restarts
        )
        states_test = model.predict(X_test)
        posteriors = getattr(model, "predict_proba", None)
        if posteriors is not None:
            try:
                P = posteriors(X_test)
                states_test_arr = np.asarray(states_test)
                confidence_test = _confidence_from_posteriors(P, states_test_arr)
            except Exception:
                pass
    else:
        states_train = _fit_with_gmm(X_train, n_components, 42)
        if _GMM_AVAILABLE and GaussianMixture is not None:
            gm = GaussianMixture(
                n_components=n_components,
                covariance_type="full",
                max_iter=200,
                random_state=42,
                n_init=3,
            )
            gm.fit(X_train)
            states_test = gm.predict(X_test)
            try:
                P = gm.predict_proba(X_test)
                confidence_test = _confidence_from_posteriors(P, np.asarray(states_test))
            except Exception:
                pass
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
    states_list = states_test.tolist() if hasattr(states_test, "tolist") else list(states_test)
    return states_list, bull_state_id, bear_state_id, confidence_test


def fit_and_predict(
    symbol: str = "BTC-USD",
    period: str = "730d",
    interval: str = "1h",
    n_components: int = 7,
    covariance_type: str = "full",
    n_iter: int = 200,
    n_restarts: int = 10,
) -> HMMRegimeResult:
    """
    Download data, engineer 5 features, fit 7-state GaussianHMM with 10 restarts and 200 EM
    (best by log-likelihood), and return regime summary + states. Regime labeling by mean return.
    """
    data = get_data(symbol, period=period, interval=interval)
    data = prepare_features(data)

    X = data[FEATURE_NAMES].values
    backend = "hmmlearn"
    aic, bic, transmat = None, None, None
    state_probabilities: Optional[List[float]] = None
    last_confidence: Optional[float] = None

    if GaussianHMM is not None:
        _model, states, aic, bic, transmat, state_probabilities = _fit_best_hmm(
            X, n_components=n_components, covariance_type=covariance_type, n_iter=n_iter, n_restarts=n_restarts
        )
        states = np.asarray(states)
        if state_probabilities:
            last_confidence = state_probabilities[-1]
    else:
        states = _fit_with_gmm(X, n_components, 42)
        states = np.asarray(states)
        backend = "gmm"
        if _GMM_AVAILABLE and GaussianMixture is not None:
            gm = GaussianMixture(
                n_components=n_components,
                covariance_type="full",
                max_iter=200,
                random_state=42,
                n_init=3,
            )
            gm.fit(X)
            proba = gm.predict_proba(X)
            state_probabilities = _confidence_from_posteriors(proba, states)
            last_confidence = state_probabilities[-1] if state_probabilities else None

    data = data.assign(State=states)
    days_in_regime = _days_in_current_regime(states)

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
        aic=aic,
        bic=bic,
        transition_matrix=transmat,
        days_in_current_regime=days_in_regime,
        state_probabilities=state_probabilities,
        last_confidence=last_confidence,
    )


def get_regime_risk_metrics(
    result: HMMRegimeResult,
    stop_multiplier: float = 2.0,
    high_vol_percentile: float = 90.0,
) -> Dict[str, Any]:
    """
    Derive regime-based risk metrics from an HMM result for display and sizing.

    Returns:
        dict with current_regime_volatility, suggested_stop_pct (volatility-implied stop %),
        risk_level ("high" | "medium" | "low" by current vol vs state vols).
    """
    vol_by_state = {r.state: r.volatility for r in result.summary}
    current_vol = vol_by_state.get(result.last_state, 0.0)
    vols = list(vol_by_state.values()) or [0.0]
    if not vols:
        return {
            "current_regime_volatility": current_vol,
            "suggested_stop_pct": stop_multiplier * current_vol * 100,
            "risk_level": "medium",
        }
    # 90th percentile of state volatilities
    p90 = float(np.percentile(vols, high_vol_percentile))
    if current_vol >= p90:
        risk_level = "high"
    elif current_vol <= float(np.percentile(vols, 50.0)):
        risk_level = "low"
    else:
        risk_level = "medium"
    return {
        "current_regime_volatility": current_vol,
        "suggested_stop_pct": stop_multiplier * current_vol * 100,
        "risk_level": risk_level,
    }


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
    out: Dict[str, Any] = {
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
    if result.aic is not None:
        out["aic"] = result.aic
    if result.bic is not None:
        out["bic"] = result.bic
    if result.transition_matrix is not None:
        out["transition_matrix"] = result.transition_matrix
    if result.days_in_current_regime is not None:
        out["days_in_current_regime"] = result.days_in_current_regime
    if result.state_probabilities is not None:
        out["state_probabilities"] = result.state_probabilities
    # Always send last_confidence when we have it or can derive from state_probabilities
    lc = result.last_confidence
    if lc is None and result.state_probabilities and len(result.state_probabilities) > 0:
        lc = result.state_probabilities[-1]
    if lc is not None:
        out["last_confidence"] = lc
    # Regime risk metrics for UI and risk-aware sizing
    out["risk"] = get_regime_risk_metrics(result)
    return out


def fit_rolling(
    symbol: str,
    as_of_date: Optional[pd.Timestamp] = None,
    calendar_days: int = 20,
    trading_days: int = 252,
    period: str = "730d",
    interval: str = "1d",
    n_components: int = 7,
) -> HMMRegimeResult:
    """
    Rolling retraining: train on last `trading_days` (252) bars as of `as_of_date`,
    return regime result for that window. For use when retraining every `calendar_days` (20).
    """
    data = get_data(symbol, period=period, interval=interval)
    data = prepare_features(data)
    if as_of_date is not None:
        data = data.loc[data.index <= as_of_date]
    if len(data) < trading_days:
        trading_days = max(60, len(data) // 2)
    train = data.iloc[-trading_days:]
    X = train[FEATURE_NAMES].values
    backend = "hmmlearn"
    aic, bic, transmat = None, None, None
    state_probabilities: Optional[List[float]] = None
    last_confidence: Optional[float] = None
    if GaussianHMM is not None:
        _model, states, aic, bic, transmat, state_probabilities = _fit_best_hmm(X, n_components=n_components, n_iter=200, n_restarts=10)
        states = np.asarray(states)
        if state_probabilities:
            last_confidence = state_probabilities[-1]
    else:
        states = _fit_with_gmm(X, n_components, 42)
        states = np.asarray(states)
        backend = "gmm"
        if _GMM_AVAILABLE and GaussianMixture is not None:
            gm = GaussianMixture(
                n_components=n_components,
                covariance_type="full",
                max_iter=200,
                random_state=42,
                n_init=3,
            )
            gm.fit(X)
            proba = gm.predict_proba(X)
            state_probabilities = _confidence_from_posteriors(proba, states)
            last_confidence = state_probabilities[-1] if state_probabilities else None
    train = train.assign(State=states)
    days_in_regime = _days_in_current_regime(states)
    summary_df = (
        train.groupby("State")
        .agg(Mean_Return=("Returns", "mean"), Volatility=("Returns", "std"), Count=("Returns", "count"))
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
        timestamps=[t.isoformat() if hasattr(t, "isoformat") else str(t) for t in train.index],
        close_prices=train["Close"].tolist(),
        last_state=int(states[-1]),
        backend=backend,
        aic=aic,
        bic=bic,
        transition_matrix=transmat,
        days_in_current_regime=days_in_regime,
        state_probabilities=state_probabilities,
        last_confidence=last_confidence,
    )


def regime_sync(results: List[HMMRegimeResult]) -> Dict[str, Any]:
    """
    Detect when multiple assets are in correlated regimes: compare last_state and
    optionally align timestamps to compute correlation of state sequences.
    Returns dict with last_states per symbol and a simple aligned flag (e.g. all in same quartile).
    """
    if not results:
        return {"symbols": [], "last_states": {}, "aligned": False}
    last_states = {r.symbol: r.last_state for r in results}
    states = list(last_states.values())
    # Consider "synchronized" if all in top half or all in bottom half of state ordering (by mean return)
    n = len(states)
    max_s, min_s = max(states), min(states)
    aligned = (max_s - min_s) <= 1  # within 1 state of each other
    return {
        "symbols": list(last_states.keys()),
        "last_states": last_states,
        "aligned": aligned,
        "min_state": min_s,
        "max_state": max_s,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hidden Markov Model market regime detection (yfinance symbols)."
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        default="BTC-USD",
        help="Symbol to analyze (e.g. BTC-USD or LUCK.PK)",
    )
    parser.add_argument(
        "--period",
        default="730d",
        help="yfinance period (e.g. 730d, 1y)",
    )
    parser.add_argument(
        "--interval",
        default="1h",
        help="yfinance interval (e.g. 1h, 1d)",
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
