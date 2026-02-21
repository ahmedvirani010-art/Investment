"""
PSX Market Regime Detection Agent
==================================
Uses Hidden Markov Models (HMM) and statistical methods to identify market regimes:
  - Trending Bull  : sustained uptrend with high momentum
  - Trending Bear  : sustained downtrend with negative momentum
  - Sideways/Range : low-directional, mean-reverting market
  - High-Volatility: volatile uncertain phase (often transitions)

Regime detection feeds into the orchestrator to bias signal generation:
  - Bull regime  → weight momentum/breakout signals higher
  - Bear regime  → weight mean-reversion/defensive signals higher
  - Sideways     → favour range-bound strategies
  - High-Vol     → reduce position sizes, increase caution flags
"""

from __future__ import annotations

import sqlite3
import json
import math
from datetime import datetime, timedelta
from typing import Optional
import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ---------------------------------------------------------------------------
# Regime constants
# ---------------------------------------------------------------------------
REGIME_BULL       = "BULL"
REGIME_BEAR       = "BEAR"
REGIME_SIDEWAYS   = "SIDEWAYS"
REGIME_HIGH_VOL   = "HIGH_VOLATILITY"
REGIME_UNKNOWN    = "UNKNOWN"

ALL_REGIMES = [REGIME_BULL, REGIME_BEAR, REGIME_SIDEWAYS, REGIME_HIGH_VOL]


# ---------------------------------------------------------------------------
# Pure-Python statistical helpers (no scipy/sklearn dependency required)
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _rolling_mean(values: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out.append(_mean(values[start : i + 1]))
    return out


def _rolling_std(values: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out.append(_std(values[start : i + 1]))
    return out


def _log_returns(closes: list[float]) -> list[float]:
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
        else:
            returns.append(0.0)
    return returns


def _annualised_volatility(log_returns: list[float], window: int = 20) -> list[float]:
    """Rolling annualised volatility (252 trading days)."""
    rolling_s = _rolling_std(log_returns, window)
    return [s * math.sqrt(252) for s in rolling_s]


def _adx_simple(highs: list[float], lows: list[float], closes: list[float],
                 period: int = 14) -> list[float]:
    """Simplified ADX (Average Directional Index) – returns list same length as closes."""
    n = len(closes)
    adx = [0.0] * n
    if n < period + 1:
        return adx

    # True range
    tr_list = [0.0]
    for i in range(1, n):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)

    # +DM / -DM
    pdm = [0.0]
    ndm = [0.0]
    for i in range(1, n):
        up   = highs[i]  - highs[i - 1]
        down = lows[i - 1] - lows[i]
        pdm.append(up   if up > down and up > 0   else 0.0)
        ndm.append(down if down > up and down > 0 else 0.0)

    # Wilder smoothing
    def wilder_smooth(data: list[float], p: int) -> list[float]:
        sm = [0.0] * n
        sm[p] = sum(data[1 : p + 1])
        for i in range(p + 1, n):
            sm[i] = sm[i - 1] - sm[i - 1] / p + data[i]
        return sm

    atr14 = wilder_smooth(tr_list, period)
    pdi14 = wilder_smooth(pdm, period)
    ndi14 = wilder_smooth(ndm, period)

    # DI lines and DX
    dx_list = [0.0] * n
    for i in range(period, n):
        if atr14[i] == 0:
            continue
        pdi = 100 * pdi14[i] / atr14[i]
        ndi = 100 * ndi14[i] / atr14[i]
        denom = pdi + ndi
        if denom == 0:
            continue
        dx_list[i] = 100 * abs(pdi - ndi) / denom

    # Smooth DX → ADX
    adx[2 * period - 1] = _mean(dx_list[period : 2 * period])
    for i in range(2 * period, n):
        adx[i] = (adx[i - 1] * (period - 1) + dx_list[i]) / period

    return adx


# ---------------------------------------------------------------------------
# HMM-lite: Gaussian emission HMM with Baum-Welch (simplified 4-state)
# ---------------------------------------------------------------------------

class GaussianHMM:
    """
    Lightweight 4-state Gaussian HMM implemented without external ML libraries.
    States correspond to: Bull, Bear, Sideways, High-Vol.
    Features: [30d_return, realised_vol, adx_norm, trend_strength]
    """

    N_STATES  = 4
    N_ITER    = 30   # Baum-Welch iterations
    EPS       = 1e-9

    def __init__(self):
        # Initial state probabilities
        self.pi = np.array([0.40, 0.20, 0.30, 0.10])
        # Transition matrix (rows = from, cols = to)
        self.A = np.array([
            [0.85, 0.05, 0.08, 0.02],  # Bull → {Bull,Bear,Side,HV}
            [0.05, 0.80, 0.10, 0.05],  # Bear → ...
            [0.10, 0.10, 0.75, 0.05],  # Sideways → ...
            [0.15, 0.20, 0.35, 0.30],  # HighVol → ...
        ])
        # Gaussian emission: mean[state, feature], std[state, feature]
        # Features: [return30d, vol, adx_norm, trend_str]
        self.mu = np.array([
            [ 0.15,  0.18,  0.70,  0.60],   # Bull
            [-0.12,  0.22,  0.60, -0.55],   # Bear
            [ 0.01,  0.12,  0.25,  0.05],   # Sideways
            [-0.03,  0.40,  0.45,  0.10],   # High-Vol
        ])
        self.sigma = np.array([
            [0.10, 0.08, 0.20, 0.25],
            [0.10, 0.08, 0.20, 0.25],
            [0.06, 0.06, 0.15, 0.20],
            [0.12, 0.15, 0.20, 0.30],
        ])
        self.fitted = False

    # ---- emission probability ----
    def _emit(self, obs: np.ndarray) -> np.ndarray:
        """Return emission probabilities for all states given one observation."""
        probs = np.ones(self.N_STATES)
        for s in range(self.N_STATES):
            for f in range(obs.shape[0]):
                diff = obs[f] - self.mu[s, f]
                sig  = max(self.sigma[s, f], self.EPS)
                probs[s] *= (1 / (sig * math.sqrt(2 * math.pi))) * math.exp(-0.5 * (diff / sig) ** 2)
        return probs + self.EPS

    def fit(self, X: np.ndarray):
        """Baum-Welch EM algorithm."""
        T = X.shape[0]

        for _ in range(self.N_ITER):
            # ---- Forward pass ----
            alpha = np.zeros((T, self.N_STATES))
            alpha[0] = self.pi * self._emit(X[0])
            alpha[0] /= alpha[0].sum() + self.EPS

            scales = np.zeros(T)
            scales[0] = alpha[0].sum()

            for t in range(1, T):
                emit = self._emit(X[t])
                alpha[t] = (alpha[t - 1] @ self.A) * emit
                scales[t] = alpha[t].sum() + self.EPS
                alpha[t] /= scales[t]

            # ---- Backward pass ----
            beta = np.zeros((T, self.N_STATES))
            beta[-1] = 1.0
            for t in range(T - 2, -1, -1):
                emit_next = self._emit(X[t + 1])
                beta[t] = (self.A * emit_next[np.newaxis, :] * beta[t + 1][np.newaxis, :]).sum(axis=1)
                beta[t] = np.clip(beta[t], 0, 1e10)
                b_sum = beta[t].sum()
                if b_sum > self.EPS:
                    beta[t] /= b_sum

            # ---- Gamma & Xi ----
            gamma = alpha * beta
            gamma_sum = gamma.sum(axis=1, keepdims=True)
            gamma /= np.where(gamma_sum > self.EPS, gamma_sum, self.EPS)

            # ---- Update parameters ----
            self.pi = gamma[0] + self.EPS
            self.pi /= self.pi.sum()

            # Transition
            for i in range(self.N_STATES):
                for j in range(self.N_STATES):
                    num = sum(alpha[t, i] * self.A[i, j] * self._emit(X[t + 1])[j] * beta[t + 1, j]
                              for t in range(T - 1))
                    den = gamma[:-1, i].sum()
                    self.A[i, j] = (num + self.EPS) / (den + self.EPS)
                row_sum = self.A[i].sum()
                self.A[i] /= row_sum + self.EPS

            # Emission
            for s in range(self.N_STATES):
                g_s = gamma[:, s]
                g_sum = g_s.sum() + self.EPS
                for f in range(X.shape[1]):
                    self.mu[s, f]    = (g_s * X[:, f]).sum() / g_sum
                    diff2            = g_s * (X[:, f] - self.mu[s, f]) ** 2
                    self.sigma[s, f] = math.sqrt(diff2.sum() / g_sum + self.EPS)

        self.fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Viterbi decoding – returns array of state indices."""
        T = X.shape[0]
        viterbi  = np.zeros((T, self.N_STATES))
        backptr  = np.zeros((T, self.N_STATES), dtype=int)

        viterbi[0] = np.log(self.pi + self.EPS) + np.log(self._emit(X[0]) + self.EPS)

        log_A = np.log(self.A + self.EPS)
        for t in range(1, T):
            log_emit = np.log(self._emit(X[t]) + self.EPS)
            for j in range(self.N_STATES):
                scores = viterbi[t - 1] + log_A[:, j]
                backptr[t, j] = scores.argmax()
                viterbi[t, j] = scores.max() + log_emit[j]

        # Backtrack
        states = np.zeros(T, dtype=int)
        states[-1] = viterbi[-1].argmax()
        for t in range(T - 2, -1, -1):
            states[t] = backptr[t + 1, states[t + 1]]
        return states

    def state_probabilities(self, X: np.ndarray) -> np.ndarray:
        """Forward algorithm – returns smoothed state probs (T × N_STATES)."""
        T = X.shape[0]
        alpha = np.zeros((T, self.N_STATES))
        alpha[0] = self.pi * self._emit(X[0])
        alpha[0] /= alpha[0].sum() + self.EPS

        for t in range(1, T):
            emit = self._emit(X[t])
            alpha[t] = (alpha[t - 1] @ self.A) * emit
            s = alpha[t].sum()
            alpha[t] /= s + self.EPS
        return alpha


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _build_features(closes: list[float], highs: list[float],
                    lows: list[float]) -> Optional[np.ndarray]:
    """
    Build normalised feature matrix (T × 4) for HMM.
    Returns None if insufficient data.
    """
    n = len(closes)
    if n < 60:
        return None

    log_ret = _log_returns(closes)
    vol20   = _annualised_volatility(log_ret, 20)
    adx14   = _adx_simple(highs, lows, closes, 14)

    # 30-day rolling return (annualised)
    ret30 = [0.0] + log_ret
    roll30 = []
    for i in range(n):
        start = max(0, i - 29)
        chunk = ret30[start : i + 1]
        roll30.append(sum(chunk) * (252 / max(len(chunk), 1)))

    # Trend strength: slope of 20d linear regression normalised by vol
    trend_str = []
    for i in range(n):
        start = max(0, i - 19)
        window_c = closes[start : i + 1]
        m = len(window_c)
        if m < 2:
            trend_str.append(0.0)
            continue
        xs = list(range(m))
        xm = _mean(xs)
        ym = _mean(window_c)
        num = sum((xs[k] - xm) * (window_c[k] - ym) for k in range(m))
        den = sum((xs[k] - xm) ** 2 for k in range(m))
        slope = (num / den) if den != 0 else 0.0
        # normalise slope by price level
        norm_slope = slope / (ym + 1e-9) * 252
        trend_str.append(norm_slope)

    # Stack and clip to [-2, 2]
    X = np.column_stack([
        np.clip(roll30,    -2, 2),
        np.clip(vol20,      0, 2),
        np.clip([a / 100 for a in adx14], 0, 1),
        np.clip(trend_str, -2, 2),
    ])
    return X


# ---------------------------------------------------------------------------
# Regime label mapping (HMM state → regime name)
# Based on which mu[state] best matches regime characteristics
# ---------------------------------------------------------------------------

_STATE_TO_REGIME_DEFAULT = {
    0: REGIME_BULL,
    1: REGIME_BEAR,
    2: REGIME_SIDEWAYS,
    3: REGIME_HIGH_VOL,
}


def _assign_state_labels(mu: np.ndarray) -> dict[int, str]:
    """
    Dynamically assign regime labels to HMM states based on learned means.
    Uses return (feature 0) and vol (feature 1) as primary classifiers.
    """
    assignment: dict[int, str] = {}
    available = list(ALL_REGIMES)

    # Sort states by return (feature 0)
    state_ret = [(s, mu[s, 0]) for s in range(4)]
    state_ret.sort(key=lambda x: x[1])

    # Lowest return → Bear
    bear_state  = state_ret[0][0]
    assignment[bear_state] = REGIME_BEAR
    available.remove(REGIME_BEAR)

    # Highest return → Bull
    bull_state  = state_ret[-1][0]
    assignment[bull_state] = REGIME_BULL
    available.remove(REGIME_BULL)

    # Among remaining two, highest vol → High-Vol
    remaining = [s for s in range(4) if s not in assignment]
    remaining.sort(key=lambda s: mu[s, 1], reverse=True)
    assignment[remaining[0]] = REGIME_HIGH_VOL
    assignment[remaining[1]] = REGIME_SIDEWAYS

    return assignment


# ---------------------------------------------------------------------------
# Main Regime Detector class
# ---------------------------------------------------------------------------

class PSXRegimeDetector:
    """
    Identifies the current market regime for a PSX stock using HMM.
    Falls back to rule-based heuristics when data is insufficient.
    """

    MIN_BARS   = 60   # minimum required bars
    LOOKBACK   = 252  # bars used for HMM fitting

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db

    # ---- data loading ----

    def _load_prices(self, symbol: str, days: int = 400) -> tuple[list, list, list, list]:
        """Returns (dates, closes, highs, lows) for symbol."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(self.price_db)
            cur  = conn.cursor()
            cur.execute("""
                SELECT date, close, high, low
                FROM   daily_prices
                WHERE  symbol = ?
                  AND  date   >= ?
                ORDER  BY date ASC
            """, (symbol, cutoff))
            rows = cur.fetchall()
            conn.close()
        except Exception:
            return [], [], [], []

        if not rows:
            return [], [], [], []

        dates, closes, highs, lows = zip(*rows)
        return list(dates), list(closes), list(highs), list(lows)

    # ---- rule-based fallback ----

    def _rule_based_regime(self, closes: list[float],
                           highs: list[float], lows: list[float]) -> dict:
        """Heuristic regime classification when HMM cannot be fitted."""
        n = len(closes)
        log_ret = _log_returns(closes)

        # Volatility (last 20 bars)
        recent_vol = _std(log_ret[-20:]) * math.sqrt(252) if len(log_ret) >= 20 else 0.0

        # 30-day return
        ret_30 = (closes[-1] / closes[-31] - 1) if n >= 31 else (closes[-1] / closes[0] - 1)

        # 50-day vs 200-day SMA direction
        sma50  = _mean(closes[-50:])  if n >= 50  else _mean(closes)
        sma200 = _mean(closes[-200:]) if n >= 200 else _mean(closes)
        above_trend = closes[-1] > sma200

        if recent_vol > 0.40:
            regime = REGIME_HIGH_VOL
            confidence = min(0.85, recent_vol / 0.50)
        elif ret_30 > 0.05 and above_trend and closes[-1] > sma50:
            regime = REGIME_BULL
            confidence = min(0.80, ret_30 / 0.20 * 0.80)
        elif ret_30 < -0.05 and not above_trend and closes[-1] < sma50:
            regime = REGIME_BEAR
            confidence = min(0.80, abs(ret_30) / 0.20 * 0.80)
        else:
            regime = REGIME_SIDEWAYS
            confidence = 0.60

        return {
            "regime": regime,
            "confidence": round(confidence, 3),
            "method": "rule_based",
            "metrics": {
                "ret_30d":      round(ret_30,      4),
                "vol_20d_ann":  round(recent_vol,  4),
                "above_sma200": above_trend,
            },
        }

    # ---- HMM-based detection ----

    def _hmm_regime(self, closes: list[float], highs: list[float],
                    lows: list[float]) -> dict:
        """Fit HMM on recent data and return current regime."""
        X = _build_features(closes, highs, lows)
        if X is None:
            return self._rule_based_regime(closes, highs, lows)

        # Use last LOOKBACK bars for fitting
        X_fit = X[-self.LOOKBACK:]

        hmm = GaussianHMM()
        try:
            hmm.fit(X_fit)
        except Exception:
            return self._rule_based_regime(closes, highs, lows)

        state_map  = _assign_state_labels(hmm.mu)
        states     = hmm.predict(X_fit)
        probs      = hmm.state_probabilities(X_fit)

        current_state = int(states[-1])
        current_regime = state_map.get(current_state, REGIME_UNKNOWN)
        current_probs  = probs[-1]

        # Map raw state probs → regime probs
        regime_probs = {r: 0.0 for r in ALL_REGIMES}
        for s, r in state_map.items():
            regime_probs[r] = float(current_probs[s])

        # 5-bar regime consistency
        recent_states  = [state_map.get(int(s), REGIME_UNKNOWN) for s in states[-5:]]
        consistency    = recent_states.count(current_regime) / len(recent_states)
        confidence     = regime_probs[current_regime] * consistency

        # Regime duration (bars since last change)
        duration = 1
        for i in range(len(states) - 2, -1, -1):
            if state_map.get(int(states[i])) == current_regime:
                duration += 1
            else:
                break

        return {
            "regime":       current_regime,
            "confidence":   round(confidence, 3),
            "method":       "hmm",
            "regime_probs": {k: round(v, 4) for k, v in regime_probs.items()},
            "duration_bars": duration,
            "consistency_5d": round(consistency, 3),
            "metrics": {
                "ret_30d_ann":    round(float(X_fit[-1, 0]), 4),
                "vol_20d_ann":    round(float(X_fit[-1, 1]), 4),
                "adx_norm":       round(float(X_fit[-1, 2]), 4),
                "trend_strength": round(float(X_fit[-1, 3]), 4),
            },
        }

    # ---- public API ----

    def detect(self, symbol: str) -> dict:
        """
        Main entry point. Returns a regime dict for the given symbol.

        Returns:
            {
              "symbol":       str,
              "regime":       "BULL" | "BEAR" | "SIDEWAYS" | "HIGH_VOLATILITY",
              "confidence":   float [0-1],
              "method":       "hmm" | "rule_based",
              "regime_probs": {regime: prob, ...},   # HMM only
              "duration_bars": int,                  # HMM only
              "metrics":      {...},
              "signal_bias":  {...},
              "timestamp":    str
            }
        """
        dates, closes, highs, lows = self._load_prices(symbol)

        if len(closes) < self.MIN_BARS:
            return {
                "symbol":    symbol,
                "regime":    REGIME_UNKNOWN,
                "confidence": 0.0,
                "error":     f"Insufficient data: {len(closes)} bars (need {self.MIN_BARS})",
                "timestamp": datetime.now().isoformat(),
            }

        result = (self._hmm_regime(closes, highs, lows)
                  if len(closes) >= self.MIN_BARS
                  else self._rule_based_regime(closes, highs, lows))

        regime = result["regime"]

        # Signal bias recommendations for this regime
        signal_bias = _REGIME_SIGNAL_BIAS.get(regime, {})

        result.update({
            "symbol":      symbol,
            "signal_bias": signal_bias,
            "timestamp":   datetime.now().isoformat(),
        })
        return result

    def detect_multiple(self, symbols: list[str]) -> dict[str, dict]:
        """Detect regime for a list of symbols."""
        return {sym: self.detect(sym) for sym in symbols}

    def market_regime_summary(self, symbols: list[str]) -> dict:
        """
        Aggregate individual regimes → overall market regime.
        Majority-vote with weighted confidence.
        """
        results = self.detect_multiple(symbols)
        regime_votes: dict[str, float] = {r: 0.0 for r in ALL_REGIMES}

        for sym, r in results.items():
            if r.get("regime") in ALL_REGIMES:
                regime_votes[r["regime"]] += r.get("confidence", 0.5)

        total = sum(regime_votes.values()) + 1e-9
        regime_pcts = {k: round(v / total, 3) for k, v in regime_votes.items()}

        dominant = max(regime_votes, key=regime_votes.get)
        market_confidence = regime_pcts[dominant]

        return {
            "market_regime":     dominant,
            "confidence":        market_confidence,
            "regime_breakdown":  regime_pcts,
            "n_stocks":          len(symbols),
            "individual_results": results,
            "signal_bias":       _REGIME_SIGNAL_BIAS.get(dominant, {}),
            "timestamp":         datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Signal bias per regime (used by orchestrator to weight agent signals)
# ---------------------------------------------------------------------------

_REGIME_SIGNAL_BIAS = {
    REGIME_BULL: {
        "momentum_weight":     1.40,   # amplify momentum/breakout signals
        "mean_reversion_weight": 0.70,
        "position_size_mult":  1.10,   # slightly larger positions
        "preferred_signals":   ["BREAKOUT", "MOMENTUM", "TREND_FOLLOWING"],
        "avoid_signals":       ["OVERSOLD_REVERSAL"],
        "risk_level":          "moderate",
    },
    REGIME_BEAR: {
        "momentum_weight":     0.60,
        "mean_reversion_weight": 1.20,
        "position_size_mult":  0.70,   # reduce exposure
        "preferred_signals":   ["OVERSOLD_REVERSAL", "DEFENSIVE", "SHORT"],
        "avoid_signals":       ["BREAKOUT", "AGGRESSIVE_BUY"],
        "risk_level":          "defensive",
    },
    REGIME_SIDEWAYS: {
        "momentum_weight":     0.80,
        "mean_reversion_weight": 1.50,
        "position_size_mult":  0.90,
        "preferred_signals":   ["RANGE_BOUND", "MEAN_REVERSION", "SUPPORT_BOUNCE"],
        "avoid_signals":       ["TREND_FOLLOWING"],
        "risk_level":          "selective",
    },
    REGIME_HIGH_VOL: {
        "momentum_weight":     0.50,
        "mean_reversion_weight": 0.50,
        "position_size_mult":  0.50,   # halve position sizes
        "preferred_signals":   ["WAIT", "TIGHT_STOP"],
        "avoid_signals":       ["BREAKOUT", "AGGRESSIVE_BUY", "TREND_FOLLOWING"],
        "risk_level":          "high_caution",
    },
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    detector = PSXRegimeDetector()

    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["LUCK.KA", "PPL.KA", "OGDC.KA"]

    if len(symbols) == 1:
        result = detector.detect(symbols[0])
        print(json.dumps(result, indent=2))
    else:
        summary = detector.market_regime_summary(symbols)
        print(json.dumps(summary, indent=2))
