"""
PSX Cointegration & Pairs Trading Agent
=========================================
Implements statistical pairs trading for PSX using:

1. COINTEGRATION TESTING
   - Engle-Granger two-step cointegration test (pure Python ADF)
   - Finds statistically cointegrated pairs from a universe of stocks

2. SPREAD ANALYSIS
   - Compute hedge ratio via OLS regression
   - Track spread z-score (mean-reverting signal)
   - Estimate mean reversion half-life (Ornstein-Uhlenbeck)

3. PAIRS TRADING SIGNALS
   - Z > +2.0 → Short spread (sell stock A, buy stock B)
   - Z < -2.0 → Long spread (buy stock A, sell stock B)
   - |Z| < 0.5 → Exit / neutral

4. PAIR STATISTICS
   - Correlation, cointegration p-value, hedge ratio
   - Spread volatility, half-life, current z-score
   - Historical profit potential (Sharpe of spread strategy)

Uses only stdlib + numpy. ADF test implemented analytically.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_closes(symbol: str, price_db: str = "price_data/prices.db",
                 days: int = 600) -> np.ndarray:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(price_db)
        rows = conn.execute("""
            SELECT date, close FROM daily_prices
            WHERE  symbol = ? AND date >= ?
            ORDER  BY date ASC
        """, (symbol, cutoff)).fetchall()
        conn.close()
        return np.array([r[1] for r in rows if r[1] is not None], dtype=float)
    except Exception:
        return np.array([])


def _align_series(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trim to common length (assuming same end date)."""
    n = min(len(a), len(b))
    return a[-n:], b[-n:]


# ---------------------------------------------------------------------------
# ADF (Augmented Dickey-Fuller) test – pure Python
# ---------------------------------------------------------------------------

def _ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, float]:
    """OLS: beta = (X'X)^{-1} X'y, returns (beta, sigma2_residuals)."""
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return np.zeros(X.shape[1]), 1.0
    resid  = y - X @ beta
    sigma2 = float(np.var(resid, ddof=X.shape[1]))
    return beta, sigma2


def adf_test(series: np.ndarray, max_lags: int = 1) -> dict:
    """
    Augmented Dickey-Fuller test.
    H0: unit root (non-stationary)
    H1: stationary (mean-reverting)

    Returns: {statistic, p_value_approx, is_stationary (at 5%)}
    """
    y    = series
    dy   = np.diff(y)
    n    = len(dy)

    # Build regression: Δy_t = α + β·y_{t-1} + Σγ_i·Δy_{t-i} + ε
    lags = min(max_lags, n // 5)
    T    = n - lags

    y_lag = y[lags:-1]               # y_{t-1}
    dys   = dy[lags:]                # Δy_t (response)

    # Regressors: const, y_{t-1}, [Δy_{t-1}, ..., Δy_{t-lags}]
    cols  = [np.ones(T), y_lag]
    for k in range(1, lags + 1):
        cols.append(dy[lags - k : n - k])
    X = np.column_stack(cols)

    beta, sigma2 = _ols(dys, X)
    rho = beta[1]   # coefficient on y_{t-1}

    # Standard error of rho
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        se_rho  = math.sqrt(max(sigma2 * XtX_inv[1, 1], 1e-12))
    except Exception:
        se_rho = 1.0

    stat = rho / se_rho if se_rho > 0 else 0.0

    # MacKinnon critical values (approximate for n >= 100, with constant)
    crit_1pct  = -3.43
    crit_5pct  = -2.86
    crit_10pct = -2.57

    # Approximate p-value from linear interpolation of MacKinnon table
    if stat < crit_1pct:
        p_approx = 0.005
    elif stat < crit_5pct:
        p_approx = 0.025
    elif stat < crit_10pct:
        p_approx = 0.075
    elif stat < -2.0:
        p_approx = 0.15
    elif stat < -1.5:
        p_approx = 0.30
    else:
        p_approx = 0.50

    return {
        "statistic":     round(stat, 4),
        "p_value_approx": p_approx,
        "critical_1pct": crit_1pct,
        "critical_5pct": crit_5pct,
        "is_stationary_5pct": stat < crit_5pct,
        "rho":           round(rho, 6),
    }


# ---------------------------------------------------------------------------
# Engle-Granger two-step cointegration
# ---------------------------------------------------------------------------

def engle_granger(y: np.ndarray, x: np.ndarray) -> dict:
    """
    Step 1: OLS regression y = α + β·x + ε
    Step 2: ADF test on residuals ε
    If residuals are stationary → y and x are cointegrated.

    Returns:
        hedge_ratio, intercept, residuals, adf_result, is_cointegrated
    """
    n = min(len(y), len(x))
    y, x = y[-n:], x[-n:]

    # OLS: y = α + β·x
    X    = np.column_stack([np.ones(n), x])
    beta, _ = _ols(y, X)
    intercept, hedge_ratio = float(beta[0]), float(beta[1])

    resid = y - (intercept + hedge_ratio * x)

    # ADF on residuals (no constant needed – already demeaned)
    adf_res = adf_test(resid, max_lags=1)

    is_coint = adf_res["is_stationary_5pct"]

    return {
        "hedge_ratio":    round(hedge_ratio, 6),
        "intercept":      round(intercept,   4),
        "residuals":      resid,
        "adf":            adf_res,
        "is_cointegrated": is_coint,
    }


# ---------------------------------------------------------------------------
# Ornstein-Uhlenbeck half-life estimation
# ---------------------------------------------------------------------------

def ou_half_life(spread: np.ndarray) -> float:
    """
    Estimate OU mean-reversion half-life in days.
    dS = κ(μ - S)dt + σ·dW
    Half-life = ln(2) / κ
    Estimated via OLS: ΔS_t = a + b·S_{t-1} + ε → κ = -b
    """
    ds   = np.diff(spread)
    s_lag = spread[:-1]
    X    = np.column_stack([np.ones(len(s_lag)), s_lag])
    beta, _ = _ols(ds, X)
    kappa = -beta[1]
    if kappa <= 0:
        return float("inf")   # not mean-reverting
    return round(math.log(2) / kappa, 1)


# ---------------------------------------------------------------------------
# Spread z-score and signal generation
# ---------------------------------------------------------------------------

def compute_spread(y: np.ndarray, x: np.ndarray,
                   hedge_ratio: float, intercept: float,
                   window: int = 60) -> dict:
    """
    Compute spread series, z-score, and trading signal.
    """
    spread = y - hedge_ratio * x - intercept

    # Rolling mean and std (window bars)
    n = len(spread)
    if n < window:
        window = n

    roll_mean = []
    roll_std  = []
    for i in range(n):
        s = max(0, i - window + 1)
        chunk = spread[s : i + 1]
        roll_mean.append(float(np.mean(chunk)))
        roll_std.append(float(np.std(chunk, ddof=1)) if len(chunk) > 1 else 1.0)

    z_scores = [(spread[i] - roll_mean[i]) / (roll_std[i] + 1e-9) for i in range(n)]
    current_z = z_scores[-1]

    # Trading signal
    entry_threshold = 2.0
    exit_threshold  = 0.5

    if current_z > entry_threshold:
        signal = "SHORT_SPREAD"    # sell y, buy x
        direction = -1
    elif current_z < -entry_threshold:
        signal = "LONG_SPREAD"     # buy y, sell x
        direction = 1
    elif abs(current_z) < exit_threshold:
        signal = "EXIT_NEUTRAL"
        direction = 0
    else:
        signal = "HOLD"
        direction = 0

    return {
        "current_spread":    round(float(spread[-1]), 4),
        "spread_mean_60d":   round(float(np.mean(spread[-60:])), 4),
        "spread_std_60d":    round(float(np.std(spread[-60:], ddof=1)), 4),
        "z_score":           round(current_z, 4),
        "signal":            signal,
        "direction":         direction,
        "entry_threshold":   entry_threshold,
        "exit_threshold":    exit_threshold,
    }


# ---------------------------------------------------------------------------
# Pair summary statistics
# ---------------------------------------------------------------------------

def pair_stats(sym_a: str, closes_a: np.ndarray,
               sym_b: str, closes_b: np.ndarray) -> dict:
    """Full cointegration & spread analysis for a pair."""
    a, b = _align_series(closes_a, closes_b)
    n    = len(a)
    if n < 60:
        return {"error": f"Insufficient data ({n} bars). Need >= 60."}

    log_a = np.log(a)
    log_b = np.log(b)

    # Correlation
    corr = float(np.corrcoef(log_a, log_b)[0, 1])

    # Cointegration (A on B)
    eg_ab = engle_granger(log_a, log_b)
    # Cointegration (B on A) – for robustness
    eg_ba = engle_granger(log_b, log_a)

    # Use whichever direction has lower ADF statistic (more stationary)
    if eg_ab["adf"]["statistic"] < eg_ba["adf"]["statistic"]:
        eg = eg_ab
        direction = f"{sym_a} = α + β·{sym_b}"
        y_arr, x_arr = log_a, log_b
        y_sym, x_sym = sym_a, sym_b
    else:
        eg = eg_ba
        direction = f"{sym_b} = α + β·{sym_a}"
        y_arr, x_arr = log_b, log_a
        y_sym, x_sym = sym_b, sym_a

    # Half-life
    half_life = ou_half_life(eg["residuals"])

    # Spread analysis
    spread_info = compute_spread(y_arr, x_arr,
                                  eg["hedge_ratio"], eg["intercept"])

    # Historical spread Sharpe (simple mean-reversion strategy)
    spread = eg["residuals"]
    spread_returns = np.diff(spread)
    if spread_info["spread_std_60d"] > 0:
        spread_sharpe = (float(np.mean(spread_returns)) /
                         float(np.std(spread_returns, ddof=1)) * math.sqrt(252))
    else:
        spread_sharpe = 0.0

    return {
        "pair":              f"{sym_a}/{sym_b}",
        "sym_a":             sym_a,
        "sym_b":             sym_b,
        "n_bars":            n,
        "correlation":       round(corr, 4),
        "cointegration": {
            "is_cointegrated":   eg["is_cointegrated"],
            "adf_statistic":     eg["adf"]["statistic"],
            "adf_p_value":       eg["adf"]["p_value_approx"],
            "regression_direction": direction,
            "hedge_ratio":       eg["hedge_ratio"],
            "intercept":         eg["intercept"],
        },
        "spread":            spread_info,
        "half_life_days":    half_life,
        "spread_sharpe_ann": round(spread_sharpe, 4),
        "pair_quality":      _rate_pair(corr, eg["is_cointegrated"],
                                        half_life, abs(spread_info["z_score"])),
        "timestamp":         datetime.now().isoformat(),
    }


def _rate_pair(corr: float, is_coint: bool, half_life: float,
               abs_z: float) -> dict:
    if not is_coint:
        return {"grade": "F", "tradeable": False,
                "reason": "Pair is NOT cointegrated – spread not mean-reverting."}

    score = 0
    reasons = []

    if corr > 0.80:
        score += 3; reasons.append("High correlation (>0.80).")
    elif corr > 0.60:
        score += 1; reasons.append("Moderate correlation (0.60–0.80).")

    if 5 <= half_life <= 30:
        score += 3; reasons.append(f"Ideal half-life ({half_life}d) for active trading.")
    elif half_life < 5:
        score += 1; reasons.append(f"Very short half-life ({half_life}d) – high turnover required.")
    elif half_life <= 60:
        score += 2; reasons.append(f"Manageable half-life ({half_life}d).")
    else:
        reasons.append(f"Long half-life ({half_life}d) – slow mean reversion.")

    if abs_z > 2.0:
        score += 2; reasons.append(f"|Z-score|={abs_z:.2f} – trade signal active.")
    elif abs_z > 1.5:
        score += 1; reasons.append(f"|Z-score|={abs_z:.2f} – approaching trade zone.")

    if score >= 7:
        grade = "A"
    elif score >= 5:
        grade = "B"
    elif score >= 3:
        grade = "C"
    else:
        grade = "D"

    return {
        "grade":     grade,
        "tradeable": score >= 3,
        "score":     score,
        "reasons":   reasons,
    }


# ---------------------------------------------------------------------------
# Universe screener
# ---------------------------------------------------------------------------

class PSXCointegrationScanner:
    """
    Scans a universe of symbols for cointegrated pairs.
    """

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db

    def _load(self, symbol: str) -> np.ndarray:
        return _load_closes(symbol, self.price_db)

    def find_pairs(self, symbols: list[str],
                   min_corr: float = 0.60,
                   require_cointegrated: bool = True) -> list[dict]:
        """
        Scan all pairs in <symbols> universe.
        Returns sorted list of viable pairs (best first).
        """
        # Load data
        data = {}
        for sym in symbols:
            c = self._load(sym)
            if len(c) >= 60:
                data[sym] = c

        valid_syms = list(data.keys())
        n = len(valid_syms)

        results = []
        for i in range(n):
            for j in range(i + 1, n):
                sym_a, sym_b = valid_syms[i], valid_syms[j]
                a, b = _align_series(data[sym_a], data[sym_b])
                if len(a) < 60:
                    continue

                # Quick correlation filter
                corr = float(np.corrcoef(np.log(a), np.log(b))[0, 1])
                if corr < min_corr:
                    continue

                ps = pair_stats(sym_a, data[sym_a], sym_b, data[sym_b])
                if "error" in ps:
                    continue
                if require_cointegrated and not ps["cointegration"]["is_cointegrated"]:
                    continue

                results.append(ps)

        # Sort by grade then |z-score|
        grade_order = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        results.sort(key=lambda x: (
            grade_order.get(x["pair_quality"]["grade"], 0),
            abs(x["spread"]["z_score"])
        ), reverse=True)

        return results

    def get_active_signals(self, symbols: list[str]) -> list[dict]:
        """Return only pairs with active trade signals (|z| > 2.0)."""
        pairs = self.find_pairs(symbols, require_cointegrated=True)
        return [p for p in pairs if p["spread"]["signal"] != "HOLD"
                and p["spread"]["signal"] != "EXIT_NEUTRAL"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    scanner = PSXCointegrationScanner()

    psx_energy = ["PPL.KA", "OGDC.KA", "POL.KA", "PSO.KA"]
    psx_cement = ["LUCK.KA", "DGKC.KA", "MLCF.KA", "CHCC.KA"]
    psx_banks  = ["HBL.KA", "MCB.KA", "UBL.KA", "ABL.KA"]

    symbols = sys.argv[1:] if len(sys.argv) > 1 else psx_energy + psx_cement

    print("Scanning for cointegrated pairs...")
    pairs = scanner.find_pairs(symbols, min_corr=0.50)

    # Print without residuals (too verbose)
    for p in pairs:
        p_clean = {k: v for k, v in p.items() if k != "residuals"}
        if "cointegration" in p_clean:
            p_clean["cointegration"] = {k: v for k, v in p_clean["cointegration"].items()
                                         if k != "residuals"}
        print(json.dumps(p_clean, indent=2))
