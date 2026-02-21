"""
PSX Advanced Risk Metrics Agent
=================================
Computes a comprehensive suite of risk/performance metrics beyond the
basic position-sizing already in psx_risk_agent.py:

RISK METRICS:
  - Historical VaR (95%, 99%, 99.5%)
  - Parametric VaR (Gaussian + Cornish-Fisher adjustment)
  - Conditional VaR (CVaR / Expected Shortfall)
  - Maximum Drawdown (MDD) + recovery time
  - Ulcer Index (pain of drawdowns)
  - Calmar Ratio (return / MDD)

RETURN / PERFORMANCE METRICS:
  - Sharpe Ratio          (excess return / total vol)
  - Sortino Ratio         (excess return / downside vol)
  - Omega Ratio           (probability-weighted gain / loss)
  - Information Ratio     (alpha / tracking error vs KSE-100)
  - Beta, Alpha (CAPM)

TAIL RISK METRICS:
  - Skewness, Excess Kurtosis
  - Cornish-Fisher VaR adjustment
  - Tail Ratio            (95th pct gain / 5th pct loss)

HOLDING-PERIOD METRICS:
  - 1-day, 5-day, 21-day VaR & CVaR
  - Annualised vol term structure
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
RISK_FREE_RATE = 0.22   # Pakistan 1-year T-bill ~22% (annualised)
TRADING_DAYS   = 252
KSE100_SYMBOL  = "^KSE100"


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _log_returns(closes: list[float]) -> np.ndarray:
    c = np.array(closes, dtype=float)
    return np.log(c[1:] / c[:-1])


def _percentile(data: np.ndarray, p: float) -> float:
    """Linear interpolation percentile."""
    s = np.sort(data)
    n = len(s)
    idx = p / 100 * (n - 1)
    lo  = int(idx)
    hi  = min(lo + 1, n - 1)
    return float(s[lo] + (idx - lo) * (s[hi] - s[lo]))


# ---------------------------------------------------------------------------
# VaR / CVaR
# ---------------------------------------------------------------------------

def historical_var(returns: np.ndarray, confidence: float = 0.95,
                   horizon: int = 1) -> float:
    """
    Historical simulation VaR.
    Returns a positive loss fraction (e.g. 0.032 = 3.2% loss).
    """
    scaled = returns * math.sqrt(horizon)
    return -_percentile(scaled, (1 - confidence) * 100)


def parametric_var(returns: np.ndarray, confidence: float = 0.95,
                   horizon: int = 1) -> float:
    """Parametric Gaussian VaR."""
    mu  = float(np.mean(returns))
    sig = float(np.std(returns, ddof=1))
    z   = _z_score(confidence)
    return -(mu * horizon - z * sig * math.sqrt(horizon))


def cornish_fisher_var(returns: np.ndarray, confidence: float = 0.95,
                       horizon: int = 1) -> float:
    """
    Cornish-Fisher expansion adjusts for skewness & kurtosis.
    More accurate than plain Gaussian for fat-tailed financial returns.
    """
    mu  = float(np.mean(returns))
    sig = float(np.std(returns, ddof=1))
    z   = _z_score(confidence)
    sk  = float(_skewness(returns))
    ex_kurt = float(_excess_kurtosis(returns))

    # Cornish-Fisher adjustment
    z_cf = (z
            + (z ** 2 - 1) / 6 * sk
            + (z ** 3 - 3 * z) / 24 * ex_kurt
            - (2 * z ** 3 - 5 * z) / 36 * sk ** 2)

    return -(mu * horizon - z_cf * sig * math.sqrt(horizon))


def conditional_var(returns: np.ndarray, confidence: float = 0.95,
                    horizon: int = 1) -> float:
    """CVaR (Expected Shortfall) – mean of losses beyond VaR."""
    scaled = returns * math.sqrt(horizon)
    cutoff = _percentile(scaled, (1 - confidence) * 100)
    tail   = scaled[scaled <= cutoff]
    return float(-np.mean(tail)) if len(tail) > 0 else 0.0


def _z_score(confidence: float) -> float:
    """Approximate inverse normal CDF via Rational approximation."""
    p = confidence
    c = [2.515517, 0.802853, 0.010328]
    d = [1.432788, 0.189269, 0.001308]
    t = math.sqrt(-2 * math.log(1 - p))
    num = c[0] + c[1] * t + c[2] * t ** 2
    den = 1 + d[0] * t + d[1] * t ** 2 + d[2] * t ** 3
    return t - num / den


# ---------------------------------------------------------------------------
# Drawdown metrics
# ---------------------------------------------------------------------------

def maximum_drawdown(closes: list[float]) -> dict:
    """
    MDD, drawdown duration (bars), recovery time (bars).
    Returns positive fraction (e.g. 0.35 = 35% drawdown).
    """
    highs = [closes[0]]
    for c in closes[1:]:
        highs.append(max(highs[-1], c))
    drawdowns = [(closes[i] - highs[i]) / highs[i] for i in range(len(closes))]
    mdd = abs(min(drawdowns))

    # Peak and trough indices
    trough_idx = drawdowns.index(min(drawdowns))
    # Find peak before trough
    peak_val = closes[0]
    peak_idx = 0
    for i in range(trough_idx + 1):
        if closes[i] >= peak_val:
            peak_val = closes[i]
            peak_idx = i

    # Recovery: first bar after trough where price >= peak
    recovery_idx = None
    for i in range(trough_idx, len(closes)):
        if closes[i] >= peak_val:
            recovery_idx = i
            break

    duration  = trough_idx - peak_idx
    recovery  = (recovery_idx - trough_idx) if recovery_idx else None
    still_underwater = recovery_idx is None

    return {
        "mdd":              round(mdd, 5),
        "peak_idx":         peak_idx,
        "trough_idx":       trough_idx,
        "duration_bars":    duration,
        "recovery_bars":    recovery,
        "still_underwater": still_underwater,
    }


def ulcer_index(closes: list[float], window: int = 14) -> float:
    """
    Ulcer Index over trailing <window> bars.
    UI = sqrt(mean(max(0, (close - rolling_high) / rolling_high)^2))
    Lower is better; high UI = painful drawdowns.
    """
    if len(closes) < window:
        window = len(closes)
    c = closes[-window:]
    rolling_high = c[0]
    squares = []
    for price in c:
        rolling_high = max(rolling_high, price)
        dd = (price - rolling_high) / rolling_high
        squares.append(dd ** 2)
    return round(math.sqrt(sum(squares) / window) * 100, 4)  # expressed as %


# ---------------------------------------------------------------------------
# Return / performance metrics
# ---------------------------------------------------------------------------

def _skewness(returns: np.ndarray) -> float:
    n  = len(returns)
    m  = float(np.mean(returns))
    s  = float(np.std(returns, ddof=1))
    if s == 0:
        return 0.0
    return float(np.mean(((returns - m) / s) ** 3))


def _excess_kurtosis(returns: np.ndarray) -> float:
    m = float(np.mean(returns))
    s = float(np.std(returns, ddof=1))
    if s == 0:
        return 0.0
    return float(np.mean(((returns - m) / s) ** 4)) - 3.0


def sharpe_ratio(returns: np.ndarray, rf_daily: float = None) -> float:
    if rf_daily is None:
        rf_daily = RISK_FREE_RATE / TRADING_DAYS
    excess = returns - rf_daily
    sig    = float(np.std(excess, ddof=1))
    if sig == 0:
        return 0.0
    return round(float(np.mean(excess)) / sig * math.sqrt(TRADING_DAYS), 4)


def sortino_ratio(returns: np.ndarray, rf_daily: float = None,
                  mar: float = 0.0) -> float:
    """Sortino: excess return over target / downside std."""
    if rf_daily is None:
        rf_daily = RISK_FREE_RATE / TRADING_DAYS
    excess    = returns - rf_daily
    downside  = returns[returns < mar] - mar
    d_std     = float(np.std(downside, ddof=1)) if len(downside) >= 2 else 0.0
    if d_std == 0:
        return 0.0
    return round(float(np.mean(excess)) / d_std * math.sqrt(TRADING_DAYS), 4)


def omega_ratio(returns: np.ndarray, threshold: float = 0.0) -> float:
    """
    Omega ratio = E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
    > 1 is desirable.
    """
    gains  = returns[returns > threshold] - threshold
    losses = threshold - returns[returns <= threshold]
    if losses.sum() == 0:
        return float("inf")
    return round(float(gains.sum() / losses.sum()), 4)


def calmar_ratio(ann_return: float, mdd: float) -> float:
    if mdd == 0:
        return float("inf")
    return round(ann_return / mdd, 4)


def tail_ratio(returns: np.ndarray) -> float:
    """95th percentile gain / |5th percentile loss|."""
    p95  = _percentile(returns, 95)
    p5   = abs(_percentile(returns, 5))
    return round(p95 / (p5 + 1e-9), 4)


def beta_alpha(stock_returns: np.ndarray,
               market_returns: np.ndarray) -> tuple[float, float]:
    """OLS regression of stock on market returns → (beta, alpha_annual)."""
    if len(stock_returns) != len(market_returns) or len(stock_returns) < 10:
        return 1.0, 0.0
    cov = float(np.cov(stock_returns, market_returns)[0, 1])
    var = float(np.var(market_returns, ddof=1))
    beta  = cov / (var + 1e-9)
    alpha = float(np.mean(stock_returns) - beta * np.mean(market_returns)) * TRADING_DAYS
    return round(beta, 4), round(alpha, 4)


def information_ratio(stock_returns: np.ndarray,
                      benchmark_returns: np.ndarray) -> float:
    """IR = mean(active_return) / std(active_return) * sqrt(252)."""
    if len(stock_returns) != len(benchmark_returns):
        n = min(len(stock_returns), len(benchmark_returns))
        stock_returns     = stock_returns[-n:]
        benchmark_returns = benchmark_returns[-n:]
    active = stock_returns - benchmark_returns
    te     = float(np.std(active, ddof=1))
    if te == 0:
        return 0.0
    return round(float(np.mean(active)) / te * math.sqrt(TRADING_DAYS), 4)


# ---------------------------------------------------------------------------
# Risk score aggregation
# ---------------------------------------------------------------------------

def _compute_risk_score(var_99: float, mdd: float, vol_ann: float,
                         sharpe: float, sortino: float) -> dict:
    """
    Composite Risk Score (0-100, higher = riskier).
    """
    # Normalise each component to 0-100
    var_score    = min(100, var_99 / 0.06 * 100)        # 6% daily VaR = max risk
    mdd_score    = min(100, mdd / 0.60 * 100)           # 60% MDD = max risk
    vol_score    = min(100, vol_ann / 0.80 * 100)       # 80% annualised vol = max risk
    perf_score   = max(0, min(100, (2 - sharpe) / 4 * 100))  # Sharpe 2+ = low risk

    composite = (var_score * 0.30
                 + mdd_score * 0.30
                 + vol_score * 0.25
                 + perf_score * 0.15)

    if composite < 25:
        label = "LOW"
    elif composite < 50:
        label = "MODERATE"
    elif composite < 75:
        label = "HIGH"
    else:
        label = "VERY HIGH"

    return {
        "composite_score": round(composite, 2),
        "label":           label,
        "components": {
            "var_score":   round(var_score,  2),
            "mdd_score":   round(mdd_score,  2),
            "vol_score":   round(vol_score,  2),
            "perf_score":  round(perf_score, 2),
        },
    }


# ---------------------------------------------------------------------------
# Position sizing recommendations
# ---------------------------------------------------------------------------

def _position_sizing(var_99_1d: float, portfolio_value: float,
                     risk_budget_pct: float = 0.01) -> dict:
    """
    Kelly-inspired position sizing based on 99% 1-day VaR.
    risk_budget_pct: fraction of portfolio to risk per position per day (default 1%).
    """
    risk_budget_pkr = portfolio_value * risk_budget_pct
    if var_99_1d > 0:
        max_position_pkr = risk_budget_pkr / var_99_1d
        max_position_pct = min(0.20, max_position_pkr / portfolio_value)  # cap at 20%
    else:
        max_position_pkr = portfolio_value * 0.05
        max_position_pct = 0.05

    return {
        "max_position_pkr": round(max_position_pkr, 0),
        "max_position_pct": round(max_position_pct, 4),
        "risk_budget_pkr":  round(risk_budget_pkr,  0),
        "method":           "var99_budget",
    }


# ---------------------------------------------------------------------------
# Main agent
# ---------------------------------------------------------------------------

class PSXAdvancedRiskMetrics:
    """
    Computes a full suite of risk and performance metrics for a PSX symbol.
    """

    LOOKBACK = 500  # bars for computation
    MIN_BARS  = 30

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db

    def _load_closes(self, symbol: str) -> list[float]:
        cutoff = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(self.price_db)
            cur  = conn.cursor()
            cur.execute("""
                SELECT close FROM daily_prices
                WHERE  symbol = ? AND date >= ?
                ORDER  BY date ASC
            """, (symbol, cutoff))
            rows = conn.execute("""
                SELECT close FROM daily_prices
                WHERE  symbol = ? AND date >= ?
                ORDER  BY date ASC
            """, (symbol, cutoff)).fetchall()
            conn.close()
            return [r[0] for r in rows if r[0] is not None]
        except Exception:
            return []

    def _load_market_closes(self) -> list[float]:
        """Load KSE-100 proxy (use most liquid stock as proxy if index missing)."""
        return self._load_closes("^KSE100") or self._load_closes("HBL.KA") or []

    def compute(self, symbol: str, portfolio_value: float = 1_000_000,
                risk_budget_pct: float = 0.01) -> dict:
        """
        Full risk metric computation for one symbol.
        """
        closes = self._load_closes(symbol)
        if len(closes) < self.MIN_BARS:
            return {
                "symbol": symbol,
                "error": f"Insufficient data: {len(closes)} bars",
                "timestamp": datetime.now().isoformat(),
            }

        closes = closes[-self.LOOKBACK:]
        returns = _log_returns(closes)

        # ---- Volatility ----
        vol_ann   = float(np.std(returns, ddof=1)) * math.sqrt(TRADING_DAYS)
        vol_daily = float(np.std(returns, ddof=1))

        # ---- Annualised return ----
        total_ret = math.log(closes[-1] / closes[0]) * (TRADING_DAYS / len(closes))
        ann_ret   = round(total_ret, 4)

        # ---- VaR / CVaR (multiple confidence levels & horizons) ----
        var_section: dict = {}
        for conf in [0.95, 0.99, 0.995]:
            key = f"{int(conf*100)}"
            var_section[key] = {
                "hist_1d":   round(historical_var(returns, conf, 1),    5),
                "hist_5d":   round(historical_var(returns, conf, 5),    5),
                "hist_21d":  round(historical_var(returns, conf, 21),   5),
                "param_1d":  round(parametric_var(returns, conf, 1),    5),
                "cf_1d":     round(cornish_fisher_var(returns, conf, 1), 5),
                "cvar_1d":   round(conditional_var(returns, conf, 1),   5),
                "cvar_5d":   round(conditional_var(returns, conf, 5),   5),
            }

        # ---- Drawdown ----
        dd_info = maximum_drawdown(closes)
        ui       = ulcer_index(closes, 14)

        # ---- Performance ratios ----
        sh  = sharpe_ratio(returns)
        so  = sortino_ratio(returns)
        om  = omega_ratio(returns)
        cal = calmar_ratio(ann_ret, dd_info["mdd"])
        tr  = tail_ratio(returns)

        # ---- Distribution stats ----
        sk  = round(_skewness(returns), 4)
        kurt = round(_excess_kurtosis(returns), 4)

        # ---- Market beta / alpha ----
        mkt_closes = self._load_market_closes()
        beta_val, alpha_val, ir_val = 1.0, 0.0, 0.0
        if len(mkt_closes) >= 30:
            n = min(len(returns), len(mkt_closes) - 1)
            mkt_returns = _log_returns(mkt_closes)[-n:]
            stk_returns = returns[-n:]
            beta_val, alpha_val = beta_alpha(stk_returns, mkt_returns)
            ir_val = information_ratio(stk_returns, mkt_returns)

        # ---- Composite risk score ----
        risk_score = _compute_risk_score(
            var_99  = var_section["99"]["hist_1d"],
            mdd     = dd_info["mdd"],
            vol_ann = vol_ann,
            sharpe  = sh,
            sortino = so,
        )

        # ---- Position sizing ----
        pos_size = _position_sizing(
            var_99_1d       = var_section["99"]["hist_1d"],
            portfolio_value = portfolio_value,
            risk_budget_pct = risk_budget_pct,
        )

        return {
            "symbol": symbol,
            "n_bars": len(closes),
            "period_days": len(closes),

            "return_metrics": {
                "ann_return":     ann_ret,
                "sharpe_ratio":   sh,
                "sortino_ratio":  so,
                "calmar_ratio":   cal,
                "omega_ratio":    om,
                "tail_ratio":     tr,
                "information_ratio": ir_val,
            },

            "risk_metrics": {
                "vol_daily":  round(vol_daily, 6),
                "vol_ann":    round(vol_ann, 4),
                "var":        var_section,
                "mdd":        dd_info,
                "ulcer_index": ui,
            },

            "distribution": {
                "skewness":         sk,
                "excess_kurtosis":  kurt,
                "fat_tails":        abs(kurt) > 1.0,
                "negative_skew":    sk < -0.5,
            },

            "market_sensitivity": {
                "beta":  beta_val,
                "alpha_ann": alpha_val,
            },

            "risk_score":     risk_score,
            "position_sizing": pos_size,
            "timestamp": datetime.now().isoformat(),
        }

    def compute_multiple(self, symbols: list[str],
                         portfolio_value: float = 1_000_000) -> dict[str, dict]:
        return {sym: self.compute(sym, portfolio_value) for sym in symbols}

    def portfolio_var(self, symbols: list[str],
                      weights: Optional[list[float]] = None) -> dict:
        """
        Portfolio-level VaR using correlation-adjusted variance.
        """
        n = len(symbols)
        if weights is None:
            weights = [1.0 / n] * n
        weights = np.array(weights[:n])
        weights /= weights.sum()

        # Load returns
        all_returns = []
        valid_syms  = []
        for sym in symbols:
            closes = self._load_closes(sym)
            if len(closes) >= 30:
                all_returns.append(_log_returns(closes[-252:]))
                valid_syms.append(sym)

        if len(valid_syms) < 2:
            return {"error": "Need >= 2 valid symbols for portfolio VaR."}

        # Align lengths
        min_len = min(len(r) for r in all_returns)
        mat = np.column_stack([r[-min_len:] for r in all_returns])
        w   = weights[:len(valid_syms)]
        w  /= w.sum()

        # Portfolio return series
        port_ret = mat @ w
        port_var_95  = round(historical_var(port_ret, 0.95, 1), 5)
        port_var_99  = round(historical_var(port_ret, 0.99, 1), 5)
        port_cvar_95 = round(conditional_var(port_ret, 0.95, 1), 5)

        # Correlation matrix (top triangle as list)
        corr = np.corrcoef(mat.T)
        corr_dict = {}
        for i in range(len(valid_syms)):
            for j in range(i + 1, len(valid_syms)):
                corr_dict[f"{valid_syms[i]}:{valid_syms[j]}"] = round(float(corr[i, j]), 4)

        return {
            "symbols":      valid_syms,
            "weights":      [round(float(w_i), 4) for w_i in w],
            "portfolio_var_95":  port_var_95,
            "portfolio_var_99":  port_var_99,
            "portfolio_cvar_95": port_cvar_95,
            "pairwise_correlations": corr_dict,
            "n_bars": min_len,
            "timestamp": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    agent = PSXAdvancedRiskMetrics()
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["LUCK.KA", "PPL.KA", "OGDC.KA"]

    if len(symbols) == 1:
        result = agent.compute(symbols[0])
        print(json.dumps(result, indent=2))
    else:
        port_var = agent.portfolio_var(symbols)
        print("=== Portfolio VaR ===")
        print(json.dumps(port_var, indent=2))
        for sym in symbols:
            print(f"\n=== {sym} ===")
            print(json.dumps(agent.compute(sym), indent=2))
