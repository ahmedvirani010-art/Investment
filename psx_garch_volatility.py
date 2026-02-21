"""
PSX GARCH Volatility Modeling Agent
=====================================
Implements GARCH(1,1) and EGARCH(1,1) for:
  - Conditional volatility estimation (today's expected vol)
  - Volatility forecasting (N-day ahead)
  - Volatility regime classification (low / normal / high / extreme)
  - Volatility risk premium (implied vs realised spread)
  - Term-structure: 1d / 5d / 21d / 63d vol forecasts

GARCH(1,1):
    σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}

EGARCH(1,1):  (captures asymmetric leverage effect)
    ln(σ²_t) = ω + α·(|z_{t-1}| - E[|z|]) + γ·z_{t-1} + β·ln(σ²_{t-1})

Uses only stdlib + numpy; no arch/statsmodels dependency.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_returns(closes: list[float]) -> np.ndarray:
    c = np.array(closes, dtype=float)
    return np.log(c[1:] / c[:-1])


def _realised_vol(returns: np.ndarray, window: int = 20) -> float:
    """Annualised realised volatility over last <window> observations."""
    if len(returns) < window:
        window = len(returns)
    return float(np.std(returns[-window:], ddof=1) * math.sqrt(252))


# ---------------------------------------------------------------------------
# GARCH(1,1)
# ---------------------------------------------------------------------------

class GARCH11:
    """
    GARCH(1,1) fitted via quasi-maximum-likelihood.
    Constraints: ω > 0, α >= 0, β >= 0, α + β < 1
    Uses gradient-free Nelder-Mead optimisation.
    """

    def __init__(self):
        self.omega  = None
        self.alpha  = None
        self.beta   = None
        self.sigma2_last = None
        self.log_likelihood = None
        self.fitted = False

    # ---- log-likelihood ----
    @staticmethod
    def _neg_loglik(params: np.ndarray, returns: np.ndarray) -> float:
        omega, alpha, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1.0:
            return 1e10

        T = len(returns)
        sigma2 = np.full(T, np.var(returns))
        ll = 0.0
        for t in range(1, T):
            sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
            if sigma2[t] <= 0:
                return 1e10
            ll += 0.5 * (math.log(2 * math.pi) + math.log(sigma2[t]) + returns[t] ** 2 / sigma2[t])
        return ll  # minimise

    # ---- Nelder-Mead ----
    @staticmethod
    def _nelder_mead(func, x0: np.ndarray, max_iter: int = 2000,
                     tol: float = 1e-8) -> np.ndarray:
        n = len(x0)
        # Build initial simplex
        simplex = [x0.copy()]
        for i in range(n):
            pt = x0.copy()
            pt[i] *= 1.05 if pt[i] != 0 else 0.00025
            simplex.append(pt)
        simplex = np.array(simplex)
        f = np.array([func(s) for s in simplex])

        alpha_r, gamma_e, rho_c, sigma_s = 1.0, 2.0, 0.5, 0.5

        for _ in range(max_iter):
            order = np.argsort(f)
            simplex, f = simplex[order], f[order]

            if f[-1] - f[0] < tol:
                break

            centroid = simplex[:-1].mean(axis=0)
            xr = centroid + alpha_r * (centroid - simplex[-1])
            fr = func(xr)

            if fr < f[0]:
                xe = centroid + gamma_e * (xr - centroid)
                fe = func(xe)
                if fe < fr:
                    simplex[-1], f[-1] = xe, fe
                else:
                    simplex[-1], f[-1] = xr, fr
            elif fr < f[-2]:
                simplex[-1], f[-1] = xr, fr
            else:
                xc = centroid + rho_c * (simplex[-1] - centroid)
                fc = func(xc)
                if fc < f[-1]:
                    simplex[-1], f[-1] = xc, fc
                else:
                    simplex[1:] = simplex[0] + sigma_s * (simplex[1:] - simplex[0])
                    f[1:] = np.array([func(s) for s in simplex[1:]])

        return simplex[0]

    def fit(self, returns: np.ndarray) -> "GARCH11":
        var0 = float(np.var(returns))
        x0 = np.array([var0 * 0.05, 0.10, 0.85])

        def neg_ll(p):
            return self._neg_loglik(p, returns)

        best = self._nelder_mead(neg_ll, x0)
        self.omega, self.alpha, self.beta = float(best[0]), float(best[1]), float(best[2])

        # Ensure constraints
        self.omega = max(self.omega, 1e-9)
        self.alpha = max(self.alpha, 0.0)
        self.beta  = max(self.beta,  0.0)
        if self.alpha + self.beta >= 1.0:
            total = self.alpha + self.beta
            self.alpha /= total * 1.01
            self.beta  /= total * 1.01

        # Re-run filter
        T = len(returns)
        sigma2 = np.full(T, np.var(returns))
        for t in range(1, T):
            sigma2[t] = self.omega + self.alpha * returns[t - 1] ** 2 + self.beta * sigma2[t - 1]

        self.sigma2_last = float(sigma2[-1])
        self.log_likelihood = -float(self._neg_loglik(best, returns))
        self.fitted = True
        return self

    def forecast(self, h: int = 1) -> list[float]:
        """Forecast conditional variance h steps ahead. Returns list of daily vols (annualised)."""
        if not self.fitted:
            raise RuntimeError("Model not fitted.")
        unconditional_var = self.omega / (1 - self.alpha - self.beta)
        forecasts = []
        sigma2_h = self.sigma2_last
        for _ in range(h):
            sigma2_h = self.omega + (self.alpha + self.beta) * sigma2_h
            # The forecast variance reverts to unconditional over longer horizons
            forecasts.append(math.sqrt(sigma2_h * 252))
        return forecasts

    @property
    def persistence(self) -> float:
        return self.alpha + self.beta

    @property
    def half_life(self) -> float:
        """Shocks half-life in days."""
        p = self.persistence
        if p >= 1.0:
            return float("inf")
        return math.log(0.5) / math.log(p)

    @property
    def long_run_vol(self) -> float:
        """Annualised long-run (unconditional) volatility."""
        denom = 1 - self.alpha - self.beta
        if denom <= 0:
            return float("nan")
        return math.sqrt(self.omega / denom * 252)


# ---------------------------------------------------------------------------
# EGARCH(1,1)
# ---------------------------------------------------------------------------

class EGARCH11:
    """
    Exponential GARCH(1,1) – captures the leverage effect (bad news → higher vol).
    ln(σ²_t) = ω + β·ln(σ²_{t-1}) + α·(|z_{t-1}| - √(2/π)) + γ·z_{t-1}
    """

    def __init__(self):
        self.omega = None; self.alpha = None
        self.gamma = None; self.beta  = None
        self.log_sigma2_last = None
        self.fitted = False
        self._E_abs_z = math.sqrt(2 / math.pi)  # E[|z|] for std normal

    @staticmethod
    def _neg_loglik(params: np.ndarray, returns: np.ndarray) -> float:
        omega, alpha, gamma, beta = params
        if abs(beta) >= 1.0:
            return 1e10
        T = len(returns)
        log_var = math.log(max(np.var(returns), 1e-9))
        E_abs = math.sqrt(2 / math.pi)
        ll = 0.0
        for t in range(1, T):
            sigma2 = math.exp(log_var)
            if sigma2 <= 0:
                return 1e10
            z = returns[t - 1] / math.sqrt(sigma2)
            log_var = omega + beta * log_var + alpha * (abs(z) - E_abs) + gamma * z
            sigma2_t = math.exp(log_var)
            if sigma2_t <= 0:
                return 1e10
            ll += 0.5 * (math.log(2 * math.pi) + log_var + returns[t] ** 2 / sigma2_t)
        return ll

    def fit(self, returns: np.ndarray) -> "EGARCH11":
        x0 = np.array([-0.1, 0.10, -0.05, 0.85])

        def neg_ll(p):
            return self._neg_loglik(p, returns)

        best = GARCH11._nelder_mead(GARCH11, neg_ll, x0)
        self.omega, self.alpha, self.gamma, self.beta = (
            float(best[0]), float(best[1]), float(best[2]), float(best[3]))

        # Re-run filter
        T = len(returns)
        log_var = math.log(max(np.var(returns), 1e-9))
        for t in range(1, T):
            sigma2 = math.exp(log_var)
            z = returns[t - 1] / math.sqrt(max(sigma2, 1e-9))
            log_var = self.omega + self.beta * log_var + self.alpha * (abs(z) - self._E_abs_z) + self.gamma * z

        self.log_sigma2_last = log_var
        self.fitted = True
        return self

    def forecast(self, h: int = 1) -> list[float]:
        if not self.fitted:
            raise RuntimeError("Model not fitted.")
        log_var = self.log_sigma2_last
        forecasts = []
        for _ in range(h):
            log_var = self.omega + self.beta * log_var + self.alpha * self._E_abs_z
            forecasts.append(math.sqrt(math.exp(log_var) * 252))
        return forecasts

    @property
    def leverage_effect(self) -> float:
        """γ < 0 indicates leverage (neg returns → higher vol)."""
        return self.gamma


# ---------------------------------------------------------------------------
# Volatility classifier
# ---------------------------------------------------------------------------

def _classify_vol(current_vol: float, long_run_vol: float) -> dict:
    ratio = current_vol / (long_run_vol + 1e-9)
    if ratio < 0.70:
        label   = "LOW"
        score   = 1 - ratio / 0.70
        meaning = "Volatility compression – potential breakout approaching"
    elif ratio < 1.30:
        label   = "NORMAL"
        score   = 0.0
        meaning = "Volatility near long-run average – no special regime"
    elif ratio < 2.00:
        label   = "HIGH"
        score   = (ratio - 1.30) / 0.70
        meaning = "Above-average volatility – reduce position sizes"
    else:
        label   = "EXTREME"
        score   = min(1.0, (ratio - 2.0) / 1.0)
        meaning = "Extreme volatility – consider exiting or tightening stops"

    return {
        "label":           label,
        "ratio_to_lr":     round(ratio, 3),
        "score":           round(score, 3),
        "interpretation":  meaning,
    }


# ---------------------------------------------------------------------------
# Main GARCHVolatilityAgent class
# ---------------------------------------------------------------------------

class PSXGARCHVolatilityAgent:
    """
    Full GARCH-based volatility analysis for PSX stocks.
    """

    LOOKBACK_GARCH  = 500   # bars for model fitting
    LOOKBACK_REALISED = 252 # bars for realised vol history
    MIN_BARS        = 60

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db

    def _load_closes(self, symbol: str) -> list[float]:
        cutoff = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(self.price_db)
            cur  = conn.cursor()
            cur.execute("""
                SELECT close FROM daily_prices
                WHERE  symbol = ? AND date >= ?
                ORDER  BY date ASC
            """, (symbol, cutoff))
            rows = cur.fetchall()
            conn.close()
            return [r[0] for r in rows if r[0] is not None]
        except Exception:
            return []

    def analyse(self, symbol: str) -> dict:
        """
        Run full GARCH volatility analysis.

        Returns:
            garch_params, egarch_params, vol_term_structure, vol_regime,
            realised_vol, conditional_vol, volatility_risk_premium
        """
        closes = self._load_closes(symbol)
        if len(closes) < self.MIN_BARS:
            return {
                "symbol": symbol,
                "error": f"Insufficient data: {len(closes)} bars",
                "timestamp": datetime.now().isoformat(),
            }

        returns = _log_returns(closes)
        r_fit   = returns[-self.LOOKBACK_GARCH:]

        # ---- Fit GARCH(1,1) ----
        garch = GARCH11()
        try:
            garch.fit(r_fit)
            garch_ok = True
        except Exception:
            garch_ok = False

        # ---- Fit EGARCH(1,1) ----
        egarch = EGARCH11()
        try:
            egarch.fit(r_fit)
            egarch_ok = True
        except Exception:
            egarch_ok = False

        # ---- Conditional vol (annualised) ----
        if garch_ok:
            cond_vol_1d = math.sqrt(garch.sigma2_last * 252)
        else:
            cond_vol_1d = _realised_vol(returns, 20)

        # ---- Realised vol history ----
        rv_5d  = _realised_vol(returns, 5)
        rv_20d = _realised_vol(returns, 20)
        rv_63d = _realised_vol(returns, 63)
        rv_252d = _realised_vol(returns, min(252, len(returns)))

        # ---- Forecast term structure ----
        term_structure = {}
        if garch_ok:
            fc_garch = garch.forecast(63)
            term_structure = {
                "1d":  round(fc_garch[0], 4),
                "5d":  round(fc_garch[4], 4),
                "21d": round(fc_garch[20], 4),
                "63d": round(fc_garch[62], 4),
            }
        else:
            term_structure = {
                "1d":  round(cond_vol_1d, 4),
                "5d":  round(rv_5d, 4),
                "21d": round(rv_20d, 4),
                "63d": round(rv_63d, 4),
            }

        # ---- Long-run vol ----
        long_run_vol = garch.long_run_vol if garch_ok else rv_252d

        # ---- Volatility regime ----
        vol_regime = _classify_vol(cond_vol_1d, long_run_vol)

        # ---- Volatility risk premium ----
        # (conditional vol - realised vol) normalised
        vol_rp = round((cond_vol_1d - rv_20d) / (rv_20d + 1e-9), 4)

        # ---- VaR estimates from GARCH vol ----
        # 1-day 95% / 99% VaR (parametric)
        garch_vol_1d = math.sqrt(garch.sigma2_last) if garch_ok else cond_vol_1d / math.sqrt(252)
        var_95 = round(1.645 * garch_vol_1d, 5)   # as fraction of price
        var_99 = round(2.326 * garch_vol_1d, 5)

        result: dict = {
            "symbol":           symbol,
            "conditional_vol":  round(cond_vol_1d, 4),
            "long_run_vol":     round(long_run_vol, 4),
            "vol_regime":       vol_regime,
            "term_structure":   term_structure,
            "realised_vol": {
                "5d":  round(rv_5d,   4),
                "20d": round(rv_20d,  4),
                "63d": round(rv_63d,  4),
                "252d": round(rv_252d, 4),
            },
            "vol_risk_premium":     vol_rp,
            "parametric_var": {
                "var_95_1d": var_95,
                "var_99_1d": var_99,
            },
            "timestamp": datetime.now().isoformat(),
        }

        if garch_ok:
            result["garch"] = {
                "omega":       round(garch.omega, 8),
                "alpha":       round(garch.alpha, 6),
                "beta":        round(garch.beta,  6),
                "persistence": round(garch.persistence, 6),
                "half_life_days": round(garch.half_life, 1),
                "log_likelihood": round(garch.log_likelihood, 2) if garch.log_likelihood else None,
            }

        if egarch_ok:
            result["egarch"] = {
                "omega":           round(egarch.omega, 8),
                "alpha":           round(egarch.alpha, 6),
                "gamma":           round(egarch.gamma, 6),
                "beta":            round(egarch.beta,  6),
                "leverage_effect": round(egarch.leverage_effect, 6),
                "has_leverage":    egarch.leverage_effect < -0.01,
            }

        # ---- Trading implications ----
        result["trading_implications"] = _vol_trading_implications(
            vol_regime["label"], garch.persistence if garch_ok else 0.95,
            egarch.leverage_effect if egarch_ok else 0.0)

        return result

    def analyse_multiple(self, symbols: list[str]) -> dict[str, dict]:
        return {sym: self.analyse(sym) for sym in symbols}


# ---------------------------------------------------------------------------
# Trading implications from volatility analysis
# ---------------------------------------------------------------------------

def _vol_trading_implications(regime: str, persistence: float,
                               leverage: float) -> dict:
    implications = []
    pos_mult = 1.0

    if regime == "LOW":
        implications.append("Consider long straddle / volatility breakout strategy.")
        implications.append("Stop-losses can be tighter due to low vol.")
        pos_mult = 1.10
    elif regime == "NORMAL":
        implications.append("Standard position sizing appropriate.")
    elif regime == "HIGH":
        implications.append("Reduce position size by 30-40%.")
        implications.append("Widen stop-losses to avoid noise-induced stops.")
        pos_mult = 0.65
    elif regime == "EXTREME":
        implications.append("Consider staying out or using very small positions.")
        implications.append("Maximum stop-loss discipline required.")
        pos_mult = 0.30

    if persistence > 0.97:
        implications.append("High volatility persistence – current vol likely to continue.")
    elif persistence < 0.80:
        implications.append("Low persistence – volatility mean-reverts quickly.")

    if leverage < -0.05:
        implications.append("Leverage effect detected: negative returns amplify future vol.")
        implications.append("Downside moves carry higher volatility risk than upside.")

    return {
        "position_size_multiplier": round(pos_mult, 2),
        "implications":             implications,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    agent = PSXGARCHVolatilityAgent()
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["LUCK.KA", "PPL.KA"]
    for sym in symbols:
        result = agent.analyse(sym)
        print(json.dumps(result, indent=2))
        print()
