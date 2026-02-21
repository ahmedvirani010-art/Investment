"""
PSX Portfolio Optimization Agent
==================================
Implements Modern Portfolio Theory (MPT) portfolio optimization:

1. Efficient Frontier construction (mean-variance optimization)
2. Maximum Sharpe Ratio portfolio (Tangency portfolio)
3. Minimum Variance portfolio
4. Risk Parity portfolio (equal risk contribution)
5. Black-Litterman framework (views + equilibrium)
6. Portfolio rebalancing recommendations

Mathematical approach:
  - Markowitz mean-variance: min w'Σw s.t. w'μ = target_return
  - Tangency:  max (μ_p - rf) / σ_p  (Sharpe maximization)
  - Min-Var:   min w'Σw
  - Risk Parity: RC_i = w_i(Σw)_i / (w'Σw) = 1/n  for all i

Uses only stdlib + numpy (no scipy.optimize required).
Optimisation via Sequential Least Squares (implemented in pure numpy).
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RISK_FREE_RATE = 0.22   # Annualised PKR risk-free rate
TRADING_DAYS   = 252


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_closes(symbol: str, price_db: str = "price_data/prices.db",
                 days: int = 800) -> list[float]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(price_db)
        rows = conn.execute("""
            SELECT close FROM daily_prices
            WHERE  symbol = ? AND date >= ?
            ORDER  BY date ASC
        """, (symbol, cutoff)).fetchall()
        conn.close()
        return [r[0] for r in rows if r[0] is not None]
    except Exception:
        return []


def _log_returns(closes: list[float]) -> np.ndarray:
    c = np.array(closes, dtype=float)
    return np.log(c[1:] / c[:-1])


def _build_return_matrix(symbols: list[str],
                          price_db: str = "price_data/prices.db") -> tuple[list[str], np.ndarray]:
    """Align log-return series for all symbols → (valid_symbols, return_matrix T×N)."""
    series = {}
    for sym in symbols:
        closes = _load_closes(sym, price_db)
        if len(closes) >= 60:
            series[sym] = _log_returns(closes)

    if len(series) < 2:
        return [], np.array([])

    min_len = min(len(r) for r in series.values())
    min_len = min(min_len, 252 * 3)  # cap at 3 years
    valid   = list(series.keys())
    mat     = np.column_stack([series[s][-min_len:] for s in valid])
    return valid, mat


# ---------------------------------------------------------------------------
# Portfolio statistics
# ---------------------------------------------------------------------------

def portfolio_stats(weights: np.ndarray, mu: np.ndarray,
                    cov: np.ndarray) -> tuple[float, float, float]:
    """Return (ann_return, ann_vol, sharpe)."""
    ret  = float(weights @ mu) * TRADING_DAYS
    var  = float(weights @ cov @ weights) * TRADING_DAYS
    vol  = math.sqrt(max(var, 0))
    sh   = (ret - RISK_FREE_RATE) / (vol + 1e-9)
    return round(ret, 6), round(vol, 6), round(sh, 6)


# ---------------------------------------------------------------------------
# Simple constrained optimizer (gradient-based, no scipy)
# ---------------------------------------------------------------------------

class _ConstrainedOptimizer:
    """
    Projected gradient descent for portfolio optimization.
    Constraints: weights sum to 1, weights >= min_w, weights <= max_w
    """

    def __init__(self, min_w: float = 0.0, max_w: float = 1.0,
                 lr: float = 0.1, max_iter: int = 5000, tol: float = 1e-9):
        self.min_w    = min_w
        self.max_w    = max_w
        self.lr       = lr
        self.max_iter = max_iter
        self.tol      = tol

    def _project(self, w: np.ndarray) -> np.ndarray:
        """Project onto simplex w in [min_w, max_w], sum=1."""
        n = len(w)
        w = np.clip(w, self.min_w, self.max_w)
        # Euclidean projection onto sum=1 simplex with box constraints
        for _ in range(100):
            s = w.sum()
            if abs(s - 1.0) < 1e-12:
                break
            w = w - (s - 1.0) / n
            w = np.clip(w, self.min_w, self.max_w)
        return w

    def minimize(self, grad_fn, x0: np.ndarray) -> np.ndarray:
        """Projected gradient descent with Armijo line-search."""
        x = self._project(x0.copy())
        lr = self.lr
        prev_f = 1e20

        for i in range(self.max_iter):
            g = grad_fn(x)
            x_new = self._project(x - lr * g)
            f_new = float(x_new @ x_new)  # placeholder; actual fn in wrapper
            change = float(np.linalg.norm(x_new - x))
            x = x_new
            if change < self.tol:
                break
        return x

    def minimize_fn(self, fn, grad_fn, x0: np.ndarray) -> np.ndarray:
        """Generic minimization with gradient and line-search."""
        x  = self._project(x0.copy())
        lr = self.lr
        f  = fn(x)

        for _ in range(self.max_iter):
            g     = grad_fn(x)
            # Line search
            step  = lr
            for _ in range(20):
                x_new = self._project(x - step * g)
                f_new = fn(x_new)
                if f_new <= f - 1e-4 * step * float(g @ g):
                    break
                step *= 0.5
            change = float(np.linalg.norm(x_new - x))
            x, f   = x_new, f_new
            if change < self.tol:
                break
        return x


# ---------------------------------------------------------------------------
# Optimization functions
# ---------------------------------------------------------------------------

def _min_var(mu: np.ndarray, cov: np.ndarray,
             min_w: float = 0.0, max_w: float = 0.40) -> np.ndarray:
    """Minimum variance portfolio via projected gradient descent."""
    n   = len(mu)
    opt = _ConstrainedOptimizer(min_w, max_w)
    x0  = np.ones(n) / n

    def fn(w):
        return float(w @ cov @ w)

    def gf(w):
        return 2 * cov @ w

    return opt.minimize_fn(fn, gf, x0)


def _max_sharpe(mu: np.ndarray, cov: np.ndarray,
                min_w: float = 0.0, max_w: float = 0.40) -> np.ndarray:
    """Max Sharpe (Tangency) portfolio via gradient descent on negative Sharpe."""
    n   = len(mu)
    opt = _ConstrainedOptimizer(min_w, max_w)
    x0  = np.ones(n) / n
    rf  = RISK_FREE_RATE / TRADING_DAYS

    def fn(w):
        ret  = float(w @ mu)
        var  = float(w @ cov @ w)
        vol  = math.sqrt(max(var, 1e-12))
        return -(ret - rf) / vol   # negative Sharpe

    def gf(w):
        ret  = float(w @ mu)
        var  = float(w @ cov @ w)
        vol  = math.sqrt(max(var, 1e-12))
        ex   = ret - rf
        # dSharpe/dw
        dret = mu
        dvol = (cov @ w) / vol
        return -(dret * vol - ex * dvol) / (vol ** 2)

    return opt.minimize_fn(fn, gf, x0)


def _risk_parity(cov: np.ndarray,
                 min_w: float = 0.0, max_w: float = 0.50) -> np.ndarray:
    """
    Risk Parity: each asset contributes equal risk (1/n fraction).
    Uses Newton iterations on the Euler condition.
    """
    n   = len(cov)
    w   = np.ones(n) / n

    for _ in range(2000):
        sigma2  = float(w @ cov @ w)
        sigma   = math.sqrt(max(sigma2, 1e-12))
        mrc     = cov @ w / sigma          # marginal risk contributions
        rc      = w * mrc                  # risk contributions
        target  = sigma / n                # equal target
        grad    = 2 * (rc - target) * mrc  # gradient
        w       = w - 0.01 * grad
        w       = np.clip(w, min_w, max_w)
        s       = w.sum()
        w      /= s
        if np.linalg.norm(grad) < 1e-9:
            break

    return w


def _efficient_frontier(mu: np.ndarray, cov: np.ndarray,
                        n_points: int = 20,
                        min_w: float = 0.0, max_w: float = 0.40) -> list[dict]:
    """
    Efficient frontier: solve min-var portfolio for each target return level.
    Returns list of {return, vol, sharpe, weights} dicts.
    """
    ret_min = float(mu.min()) * TRADING_DAYS
    ret_max = float(mu.max()) * TRADING_DAYS
    targets = np.linspace(ret_min, ret_max, n_points)

    frontier = []
    opt      = _ConstrainedOptimizer(min_w, max_w)
    n        = len(mu)

    for target_ret in targets:
        target_daily = target_ret / TRADING_DAYS

        def fn(w):
            return float(w @ cov @ w)

        def gf(w):
            # penalised gradient: minimize vol + penalty for return deviation
            penalty = 1e4 * (float(w @ mu) - target_daily) ** 2
            return 2 * cov @ w + 1e4 * 2 * (float(w @ mu) - target_daily) * mu

        x0 = np.ones(n) / n
        w  = opt.minimize_fn(fn, gf, x0)

        p_ret, p_vol, p_sh = portfolio_stats(w, mu, cov)
        frontier.append({
            "target_return": round(target_ret, 4),
            "realised_return": round(p_ret, 4),
            "volatility": round(p_vol, 4),
            "sharpe":     round(p_sh,  4),
            "weights":    {sym: round(float(w[i]), 4)
                           for i, sym in enumerate(range(n))},
        })

    return frontier


# ---------------------------------------------------------------------------
# Black-Litterman
# ---------------------------------------------------------------------------

def black_litterman(mu_eq: np.ndarray, cov: np.ndarray,
                    P: np.ndarray, Q: np.ndarray,
                    omega: Optional[np.ndarray] = None,
                    tau: float = 0.05) -> np.ndarray:
    """
    Black-Litterman posterior expected returns.

    Args:
        mu_eq : equilibrium returns (N,)
        cov   : covariance matrix (N×N)
        P     : pick matrix (K×N) – K views on N assets
        Q     : view expected returns (K,)
        omega : view uncertainty (K×K); if None, proportional to P cov P'
        tau   : scaling factor (typically 1/T or 0.05)
    """
    if omega is None:
        omega = np.diag(np.diag(tau * P @ cov @ P.T))

    prior_cov = tau * cov
    M = np.linalg.inv(np.linalg.inv(prior_cov) + P.T @ np.linalg.inv(omega) @ P)
    mu_bl = M @ (np.linalg.inv(prior_cov) @ mu_eq + P.T @ np.linalg.inv(omega) @ Q)
    return mu_bl


# ---------------------------------------------------------------------------
# Main Portfolio Optimizer
# ---------------------------------------------------------------------------

class PSXPortfolioOptimizer:

    MIN_STOCKS = 2

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db

    def optimize(self, symbols: list[str],
                 min_weight: float = 0.0,
                 max_weight: float = 0.40,
                 views: Optional[dict] = None) -> dict:
        """
        Full portfolio optimization.

        Args:
            symbols    : list of PSX symbols
            min_weight : minimum weight per asset (0 = allow zero)
            max_weight : maximum weight per asset (0.40 = max 40% in one stock)
            views      : optional Black-Litterman views
                         {"LUCK.KA": 0.25, "PPL.KA": -0.10}  (expected annual returns)

        Returns:
            Comprehensive optimization results.
        """
        valid_syms, ret_mat = _build_return_matrix(symbols, self.price_db)
        if len(valid_syms) < self.MIN_STOCKS:
            return {"error": f"Need >= {self.MIN_STOCKS} symbols with data. Got {len(valid_syms)}."}

        n   = len(valid_syms)
        mu  = np.mean(ret_mat, axis=0)   # daily mean returns
        cov = np.cov(ret_mat.T)          # daily covariance

        # ---- Equal-weight benchmark ----
        eq_w   = np.ones(n) / n
        eq_ret, eq_vol, eq_sh = portfolio_stats(eq_w, mu, cov)

        # ---- Minimum Variance ----
        mv_w   = _min_var(mu, cov, min_weight, max_weight)
        mv_ret, mv_vol, mv_sh = portfolio_stats(mv_w, mu, cov)

        # ---- Maximum Sharpe (Tangency) ----
        ms_w   = _max_sharpe(mu, cov, min_weight, max_weight)
        ms_ret, ms_vol, ms_sh = portfolio_stats(ms_w, mu, cov)

        # ---- Risk Parity ----
        rp_w   = _risk_parity(cov, min_weight, max_weight)
        rp_ret, rp_vol, rp_sh = portfolio_stats(rp_w, mu, cov)

        # ---- Black-Litterman (if views provided) ----
        bl_result = None
        if views:
            view_symbols = [s for s in views if s in valid_syms]
            if view_symbols:
                K   = len(view_symbols)
                P   = np.zeros((K, n))
                Q   = np.zeros(K)
                for ki, sym in enumerate(view_symbols):
                    idx = valid_syms.index(sym)
                    P[ki, idx] = 1.0
                    Q[ki] = views[sym] / TRADING_DAYS  # daily

                # Market-cap-weight equilibrium returns (assume equal here)
                market_weights = np.ones(n) / n
                lam = (eq_sh * eq_vol) / (eq_vol ** 2 + 1e-9)
                mu_eq = lam * cov @ market_weights * TRADING_DAYS

                try:
                    mu_bl = black_litterman(mu_eq / TRADING_DAYS, cov, P, Q)
                    bl_w  = _max_sharpe(mu_bl, cov, min_weight, max_weight)
                    bl_ret, bl_vol, bl_sh = portfolio_stats(bl_w, mu_bl, cov)
                    bl_result = {
                        "weights":   {valid_syms[i]: round(float(bl_w[i]), 4) for i in range(n)},
                        "return":    bl_ret,
                        "vol":       bl_vol,
                        "sharpe":    bl_sh,
                        "views_applied": views,
                    }
                except Exception:
                    bl_result = None

        # ---- Correlation matrix ----
        corr = np.corrcoef(ret_mat.T)
        corr_dict = {}
        for i in range(n):
            for j in range(i + 1, n):
                corr_dict[f"{valid_syms[i]}:{valid_syms[j]}"] = round(float(corr[i, j]), 4)

        # ---- Individual asset stats ----
        asset_stats = {}
        for i, sym in enumerate(valid_syms):
            a_ret = float(mu[i]) * TRADING_DAYS
            a_vol = float(math.sqrt(cov[i, i] * TRADING_DAYS))
            a_sh  = (a_ret - RISK_FREE_RATE) / (a_vol + 1e-9)
            asset_stats[sym] = {
                "ann_return": round(a_ret, 4),
                "ann_vol":    round(a_vol, 4),
                "sharpe":     round(a_sh,  4),
            }

        # ---- Efficient frontier (quick, 15 points) ----
        frontier = _efficient_frontier(mu, cov, n_points=15,
                                       min_w=min_weight, max_w=max_weight)
        # Replace numeric weight keys with symbol names
        for pt in frontier:
            pt["weights"] = {valid_syms[i]: pt["weights"][i] for i in range(n)}

        def _wdict(w):
            return {valid_syms[i]: round(float(w[i]), 4) for i in range(n)}

        result = {
            "symbols": valid_syms,
            "n_bars":  ret_mat.shape[0],

            "portfolios": {
                "equal_weight": {
                    "weights": _wdict(eq_w),
                    "return":  eq_ret,
                    "vol":     eq_vol,
                    "sharpe":  eq_sh,
                },
                "minimum_variance": {
                    "weights": _wdict(mv_w),
                    "return":  mv_ret,
                    "vol":     mv_vol,
                    "sharpe":  mv_sh,
                },
                "maximum_sharpe": {
                    "weights": _wdict(ms_w),
                    "return":  ms_ret,
                    "vol":     ms_vol,
                    "sharpe":  ms_sh,
                },
                "risk_parity": {
                    "weights": _wdict(rp_w),
                    "return":  rp_ret,
                    "vol":     rp_vol,
                    "sharpe":  rp_sh,
                },
            },

            "asset_stats":         asset_stats,
            "pairwise_correlations": corr_dict,
            "efficient_frontier":  frontier,
            "timestamp": datetime.now().isoformat(),
        }

        if bl_result:
            result["portfolios"]["black_litterman"] = bl_result

        # ---- Recommendation ----
        result["recommendation"] = _recommend(
            result["portfolios"]["maximum_sharpe"],
            result["portfolios"]["minimum_variance"],
            result["portfolios"]["risk_parity"],
        )

        return result

    def rebalance_trades(self, current_weights: dict[str, float],
                         target_weights: dict[str, float],
                         portfolio_value: float,
                         min_trade_pct: float = 0.01) -> list[dict]:
        """
        Calculate trades needed to rebalance from current to target weights.
        Ignores trades < min_trade_pct of portfolio value.
        """
        trades = []
        all_syms = set(current_weights) | set(target_weights)

        for sym in all_syms:
            cur = current_weights.get(sym, 0.0)
            tgt = target_weights.get(sym, 0.0)
            diff = tgt - cur
            trade_value = diff * portfolio_value
            if abs(trade_value) < min_trade_pct * portfolio_value:
                continue
            trades.append({
                "symbol":           sym,
                "current_weight":   round(cur, 4),
                "target_weight":    round(tgt, 4),
                "weight_change":    round(diff, 4),
                "trade_value_pkr":  round(trade_value, 0),
                "direction":        "BUY" if diff > 0 else "SELL",
            })

        trades.sort(key=lambda x: abs(x["weight_change"]), reverse=True)
        return trades


def _recommend(ms: dict, mv: dict, rp: dict) -> dict:
    """Pick the recommended portfolio and give reasoning."""
    if ms["sharpe"] > mv["sharpe"] * 1.1 and ms["vol"] < 0.50:
        choice = "maximum_sharpe"
        reason = ("Max-Sharpe portfolio delivers meaningfully higher risk-adjusted "
                  "returns without excessive volatility.")
    elif mv["vol"] < 0.20:
        choice = "minimum_variance"
        reason = "Low-vol environment – minimum variance portfolio suits capital preservation."
    else:
        choice = "risk_parity"
        reason = ("Risk parity ensures balanced contribution from each asset, "
                  "robust across volatile regimes.")
    return {"recommended_portfolio": choice, "rationale": reason}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    optimizer = PSXPortfolioOptimizer()
    symbols   = sys.argv[1:] if len(sys.argv) > 1 else [
        "LUCK.KA", "PPL.KA", "OGDC.KA", "HBL.KA", "MCB.KA"]
    result = optimizer.optimize(symbols)
    # Print without efficient frontier (verbose) for CLI readability
    compact = {k: v for k, v in result.items() if k != "efficient_frontier"}
    print(json.dumps(compact, indent=2))
