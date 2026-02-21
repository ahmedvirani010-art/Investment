"""
PSX Macro Factor Model
========================
Implements a Pakistan-specific multi-factor model for equity returns.

FACTORS (PSX-contextualized):
  1. Market Beta (KSE-100 excess return)
  2. SBP Policy Rate sensitivity
  3. PKR/USD Exchange Rate sensitivity
  4. Crude Oil price sensitivity (Brent)
  5. Size factor (SMB – Small Minus Big)
  6. Value factor (HML – High Minus Low book-to-price)
  7. Momentum factor (12-1 month momentum)
  8. Inflation sensitivity (CPI)

The model:
  r_i = α_i + β_Market·r_Market + β_Rate·ΔRate + β_FX·ΔFX
        + β_Oil·ΔOil + β_Size·SMB + β_Value·HML + β_Mom·MOM + ε_i

Returns:
  - Factor betas (sensitivities)
  - Alpha (manager skill / mispricing)
  - Factor decomposition of returns
  - Stress-test scenarios for each factor
  - Macro signal interpretation

Data sources:
  - KSE-100 index (from price DB as ^KSE100 or proxy)
  - SBP rate, PKR/USD, Brent: stored in macro_data table or fetched inline
  - SMB, HML, MOM: constructed from PSX universe (computed internally)

Note: External macro data (rates, FX) can be injected via the MacroData store.
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
TRADING_DAYS   = 252
RISK_FREE_RATE = 0.22   # SBP policy rate proxy (annual)


# ---------------------------------------------------------------------------
# OLS regression helpers
# ---------------------------------------------------------------------------

def _ols_regression(y: np.ndarray, X: np.ndarray) -> dict:
    """
    OLS: y = X·β + ε
    Returns betas, t-stats, R², adjusted R², residuals.
    """
    n, k = X.shape
    try:
        XtX_inv = np.linalg.pinv(X.T @ X)
        beta    = XtX_inv @ X.T @ y
    except np.linalg.LinAlgError:
        return {}

    y_hat   = X @ beta
    resid   = y - y_hat
    ss_res  = float(resid @ resid)
    ss_tot  = float(np.sum((y - np.mean(y)) ** 2))
    r2      = 1 - ss_res / (ss_tot + 1e-12)
    adj_r2  = 1 - (1 - r2) * (n - 1) / (n - k - 1)

    sigma2  = ss_res / (n - k)
    se      = np.sqrt(np.diag(XtX_inv) * sigma2)
    t_stats = beta / (se + 1e-12)

    return {
        "beta":    beta,
        "se":      se,
        "t_stats": t_stats,
        "r2":      r2,
        "adj_r2":  adj_r2,
        "residuals": resid,
        "n":       n,
    }


# ---------------------------------------------------------------------------
# Macro data store
# ---------------------------------------------------------------------------

class MacroDataStore:
    """
    Stores/retrieves macro time-series:
      - sbp_rate: SBP policy rate (daily, carry-forward)
      - pkr_usd:  PKR/USD exchange rate
      - brent:    Brent crude oil (USD/bbl)
      - cpi:      Pakistan CPI inflation (monthly, interpolated daily)
      - kse100:   KSE-100 index level

    Uses SQLite for persistence. Data can be injected manually
    or pulled from the price database.
    """

    TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS macro_data (
        date        TEXT NOT NULL,
        series      TEXT NOT NULL,
        value       REAL NOT NULL,
        source      TEXT,
        PRIMARY KEY (date, series)
    )
    """

    def __init__(self, db_path: str = "price_data/macro.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(self.TABLE_DDL)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def insert(self, date: str, series: str, value: float, source: str = "manual"):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO macro_data (date, series, value, source)
                VALUES (?, ?, ?, ?)
            """, (date, series, value, source))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def bulk_insert(self, records: list[dict]):
        """records = [{"date": ..., "series": ..., "value": ...}]"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.executemany("""
                INSERT OR REPLACE INTO macro_data (date, series, value, source)
                VALUES (:date, :series, :value, 'bulk')
            """, records)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def load_series(self, series: str, start: str = None,
                    end: str = None) -> dict[str, float]:
        """Returns {date: value} dict."""
        try:
            conn = sqlite3.connect(self.db_path)
            q = "SELECT date, value FROM macro_data WHERE series = ?"
            params: list = [series]
            if start:
                q += " AND date >= ?"; params.append(start)
            if end:
                q += " AND date <= ?"; params.append(end)
            q += " ORDER BY date ASC"
            rows = conn.execute(q, params).fetchall()
            conn.close()
            return {r[0]: r[1] for r in rows}
        except Exception:
            return {}

    def available_series(self) -> list[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT DISTINCT series FROM macro_data").fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def seed_synthetic(self):
        """
        Seed synthetic (illustrative) Pakistani macro data for testing.
        Generates 2 years of daily data.
        """
        base = datetime(2023, 1, 1)
        records = []
        sbp_rate = 22.0
        pkr_usd  = 280.0
        brent    = 85.0
        cpi      = 27.0
        kse100   = 50_000.0

        for i in range(500):
            dt = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # Simulate gradual changes
            sbp_rate  += np.random.normal(0, 0.05)
            sbp_rate   = max(5, min(30, sbp_rate))
            pkr_usd   *= (1 + np.random.normal(-0.0002, 0.003))
            brent     *= (1 + np.random.normal(0.0, 0.015))
            brent      = max(40, min(120, brent))
            cpi       += np.random.normal(-0.01, 0.05)
            cpi        = max(5, min(40, cpi))
            kse100    *= (1 + np.random.normal(0.0003, 0.010))

            for series, val in [("sbp_rate", sbp_rate), ("pkr_usd", pkr_usd),
                                  ("brent", brent), ("cpi", cpi), ("kse100", kse100)]:
                records.append({"date": dt, "series": series, "value": round(val, 4)})

        self.bulk_insert(records)


# ---------------------------------------------------------------------------
# Factor construction
# ---------------------------------------------------------------------------

def _series_to_returns(values: dict[str, float]) -> tuple[list[str], np.ndarray]:
    """Convert level series dict → daily log-returns."""
    dates  = sorted(values.keys())
    levels = np.array([values[d] for d in dates], dtype=float)
    if len(levels) < 2:
        return [], np.array([])
    rets = np.log(levels[1:] / levels[:-1])
    return dates[1:], rets


def _pct_change(values: dict[str, float]) -> tuple[list[str], np.ndarray]:
    """Percent change in basis points for rate series."""
    dates  = sorted(values.keys())
    levels = np.array([values[d] for d in dates], dtype=float)
    if len(levels) < 2:
        return [], np.array([])
    changes = np.diff(levels)   # raw BPS change for rate-type series
    return dates[1:], changes


def _align_multi(*series_tuples) -> tuple[list[str], list[np.ndarray]]:
    """Align multiple (dates, values) tuples to common dates."""
    if not series_tuples:
        return [], []

    date_sets = [set(t[0]) for t in series_tuples]
    common    = date_sets[0]
    for ds in date_sets[1:]:
        common &= ds
    common = sorted(common)

    aligned = []
    for dates, vals in series_tuples:
        idx = {d: i for i, d in enumerate(dates)}
        aligned.append(np.array([vals[idx[d]] for d in common]))

    return common, aligned


# ---------------------------------------------------------------------------
# PSX Macro Factor Model
# ---------------------------------------------------------------------------

class PSXMacroFactorModel:
    """
    Fits a PSX-specific multi-factor model for a stock.

    Factors:
      1. Market excess return (KSE-100 minus risk-free)
      2. ΔSBP rate (basis points change)
      3. ΔPKR/USD (log return of exchange rate)
      4. ΔBrent (log return of crude oil)
      5. ΔCPI (annualised CPI change)

    Optional Fama-French style factors:
      6. SMB (size premium)
      7. HML (value premium)
      8. MOM (momentum premium)
    """

    MIN_BARS = 60

    def __init__(self,
                 price_db:  str = "price_data/prices.db",
                 macro_db:  str = "price_data/macro.db"):
        self.price_db  = price_db
        self.macro_db  = macro_db
        self.macro     = MacroDataStore(macro_db)

    def _load_stock(self, symbol: str) -> tuple[list[str], np.ndarray]:
        """Load stock log-returns from price DB."""
        cutoff = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(self.price_db)
            rows = conn.execute("""
                SELECT date, close FROM daily_prices
                WHERE  symbol = ? AND date >= ?
                ORDER  BY date ASC
            """, (symbol, cutoff)).fetchall()
            conn.close()
        except Exception:
            return [], np.array([])

        if len(rows) < 2:
            return [], np.array([])

        dates  = [r[0] for r in rows]
        closes = np.array([r[1] for r in rows], dtype=float)
        rets   = np.log(closes[1:] / closes[:-1])
        return dates[1:], rets

    def _load_factor_data(self) -> dict[str, tuple[list, np.ndarray]]:
        """Load macro factor series from the macro DB."""
        factors = {}

        # Market (KSE-100)
        kse = self.macro.load_series("kse100")
        if kse:
            d, r = _series_to_returns(kse)
            factors["market"] = (d, r)

        # SBP rate (level changes in percentage points)
        sbp = self.macro.load_series("sbp_rate")
        if sbp:
            d, r = _pct_change(sbp)
            factors["sbp_rate"] = (d, r)

        # PKR/USD
        fx = self.macro.load_series("pkr_usd")
        if fx:
            d, r = _series_to_returns(fx)
            factors["pkr_usd"] = (d, r)

        # Brent crude
        brent = self.macro.load_series("brent")
        if brent:
            d, r = _series_to_returns(brent)
            factors["brent"] = (d, r)

        # CPI
        cpi = self.macro.load_series("cpi")
        if cpi:
            d, r = _pct_change(cpi)
            factors["cpi"] = (d, r)

        return factors

    def fit(self, symbol: str) -> dict:
        """
        Fit the macro factor model for a single symbol.
        Returns betas, alpha, R², factor decomposition, and stress tests.
        """
        stock_dates, stock_rets = self._load_stock(symbol)
        if len(stock_rets) < self.MIN_BARS:
            return {"symbol": symbol, "error": "Insufficient stock data."}

        factor_data = self._load_factor_data()
        if not factor_data:
            return {"symbol": symbol,
                    "error": "No macro data available. Seed data with MacroDataStore.seed_synthetic()."}

        # ---- Align all series to common dates ----
        factor_names  = []
        factor_tuples = [(stock_dates, stock_rets)]
        for name, (d, r) in factor_data.items():
            factor_names.append(name)
            factor_tuples.append((d, r))

        common_dates, aligned = _align_multi(*factor_tuples)
        if len(common_dates) < self.MIN_BARS:
            return {"symbol": symbol,
                    "error": f"Only {len(common_dates)} common dates after alignment. Need {self.MIN_BARS}."}

        stock_r = aligned[0]
        factor_rs = aligned[1:]

        # ---- Build design matrix ----
        rf_daily = RISK_FREE_RATE / TRADING_DAYS
        X_cols   = [np.ones(len(stock_r))]   # intercept (alpha)
        col_names = ["intercept"]

        for i, name in enumerate(factor_names):
            f_r = factor_rs[i]
            if name == "market":
                X_cols.append(f_r - rf_daily)   # excess market return
                col_names.append("market_excess")
            else:
                X_cols.append(f_r)
                col_names.append(name)

        X = np.column_stack(X_cols)

        # ---- OLS ----
        ols = _ols_regression(stock_r, X)
        if not ols:
            return {"symbol": symbol, "error": "OLS regression failed."}

        beta   = ols["beta"]
        t_stat = ols["t_stats"]
        se     = ols["se"]

        # ---- Factor betas ----
        betas_dict = {}
        for i, name in enumerate(col_names):
            betas_dict[name] = {
                "beta":   round(float(beta[i]),   6),
                "t_stat": round(float(t_stat[i]), 4),
                "se":     round(float(se[i]),      6),
                "significant_5pct": abs(float(t_stat[i])) > 1.96,
            }

        # Annualised alpha
        alpha_daily = float(beta[0])
        alpha_ann   = alpha_daily * TRADING_DAYS

        # ---- Factor contributions to mean return ----
        mean_factors = [float(np.mean(f)) for f in factor_rs]
        factor_contrib = {}
        for i, name in enumerate(factor_names):
            col_idx = col_names.index("market_excess" if name == "market" else name)
            contrib = float(beta[col_idx]) * mean_factors[i] * TRADING_DAYS
            factor_contrib[name] = round(contrib, 6)

        # ---- Stress tests ----
        stress_scenarios = _stress_tests(betas_dict)

        # ---- Residual / idiosyncratic vol ----
        resid     = ols["residuals"]
        idio_vol  = float(np.std(resid, ddof=1)) * math.sqrt(TRADING_DAYS)
        sys_vol   = math.sqrt(max(
            float(np.var(stock_r, ddof=1)) - float(np.var(resid, ddof=1)), 0
        )) * math.sqrt(TRADING_DAYS)
        total_vol = float(np.std(stock_r, ddof=1)) * math.sqrt(TRADING_DAYS)

        return {
            "symbol": symbol,
            "model": {
                "factors":   col_names[1:],
                "n_obs":     ols["n"],
                "r2":        round(ols["r2"],     4),
                "adj_r2":    round(ols["adj_r2"], 4),
            },
            "alpha": {
                "daily":      round(alpha_daily, 8),
                "annualised": round(alpha_ann,   4),
                "t_stat":     betas_dict["intercept"]["t_stat"],
                "significant": betas_dict["intercept"]["significant_5pct"],
            },
            "betas":                {k: v for k, v in betas_dict.items() if k != "intercept"},
            "factor_contributions": factor_contrib,
            "volatility_decomposition": {
                "total_ann":         round(total_vol,  4),
                "systematic_ann":    round(sys_vol,    4),
                "idiosyncratic_ann": round(idio_vol,   4),
                "pct_systematic":    round(sys_vol / (total_vol + 1e-9), 4),
            },
            "stress_tests":    stress_scenarios,
            "macro_interpretation": _interpret_betas(betas_dict),
            "timestamp": datetime.now().isoformat(),
        }

    def fit_multiple(self, symbols: list[str]) -> dict[str, dict]:
        return {sym: self.fit(sym) for sym in symbols}

    def factor_attribution(self, symbols: list[str],
                            weights: Optional[list[float]] = None) -> dict:
        """
        Portfolio-level factor attribution.
        Weighted average of individual stock betas.
        """
        n = len(symbols)
        if weights is None:
            weights = [1.0 / n] * n

        results = {sym: self.fit(sym) for sym in symbols}
        portfolio_betas: dict[str, float] = {}

        for sym, w in zip(symbols, weights):
            r = results[sym]
            if "betas" not in r:
                continue
            for factor, info in r["betas"].items():
                portfolio_betas[factor] = portfolio_betas.get(factor, 0) + w * info["beta"]

        return {
            "portfolio_betas": {k: round(v, 4) for k, v in portfolio_betas.items()},
            "individual":      results,
            "stress_tests":    _stress_tests(
                {"intercept": {"beta": 0, "t_stat": 0, "se": 0, "significant_5pct": False},
                 **{k: {"beta": v, "t_stat": 0, "se": 0, "significant_5pct": True}
                    for k, v in portfolio_betas.items()}}),
            "timestamp": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Stress test scenarios
# ---------------------------------------------------------------------------

def _stress_tests(betas: dict) -> list[dict]:
    """
    Compute stock return impact under PSX-specific macro stress scenarios.
    Returns list of {scenario, factor_shocks, estimated_impact_pct}.
    """
    SCENARIOS = [
        {
            "name":  "SBP Rate Hike +300bps",
            "shocks": {"sbp_rate": +0.03, "market_excess": -0.08, "pkr_usd": 0.0},
            "desc":  "Central bank surprises with 300bps emergency rate hike.",
        },
        {
            "name":  "PKR Devaluation 15%",
            "shocks": {"pkr_usd": +0.15, "sbp_rate": +0.01, "market_excess": -0.12},
            "desc":  "PKR depreciates sharply – imported inflation, SBP tightens.",
        },
        {
            "name":  "Crude Oil Surge +40%",
            "shocks": {"brent": +0.40, "cpi": +0.02, "sbp_rate": +0.005},
            "desc":  "Oil spike drives inflation; SBP raises rates moderately.",
        },
        {
            "name":  "Crude Oil Crash -30%",
            "shocks": {"brent": -0.30, "sbp_rate": -0.01, "market_excess": +0.05},
            "desc":  "Oil collapse – energy sector stress, lower import bill.",
        },
        {
            "name":  "IMF Programme Suspension",
            "shocks": {"pkr_usd": +0.25, "market_excess": -0.20, "sbp_rate": +0.02},
            "desc":  "IMF suspends Pakistan programme – capital flight, PKR rout.",
        },
        {
            "name":  "Bull Market (+20% KSE-100)",
            "shocks": {"market_excess": +0.20, "sbp_rate": -0.005, "pkr_usd": -0.02},
            "desc":  "Positive macro surprise – broad-based rally.",
        },
        {
            "name":  "Bear Market (-20% KSE-100)",
            "shocks": {"market_excess": -0.20, "sbp_rate": +0.01, "pkr_usd": +0.05},
            "desc":  "Risk-off selloff – equity market correction.",
        },
    ]

    results = []
    for scenario in SCENARIOS:
        impact = 0.0
        factor_impacts = {}
        for factor, shock in scenario["shocks"].items():
            beta_info = betas.get(factor) or betas.get(
                "market_excess" if factor == "market" else factor)
            if beta_info is None:
                continue
            beta_val = float(beta_info["beta"])
            contrib  = beta_val * shock
            impact  += contrib
            factor_impacts[factor] = round(contrib * 100, 2)  # as % return

        results.append({
            "scenario":       scenario["name"],
            "description":    scenario["desc"],
            "factor_impacts_pct": factor_impacts,
            "total_impact_pct":   round(impact * 100, 2),
            "impact_label":   _impact_label(impact),
        })

    return results


def _impact_label(impact: float) -> str:
    if impact > 0.10:  return "STRONGLY_POSITIVE"
    if impact > 0.03:  return "POSITIVE"
    if impact > -0.03: return "NEUTRAL"
    if impact > -0.10: return "NEGATIVE"
    return "STRONGLY_NEGATIVE"


# ---------------------------------------------------------------------------
# Beta interpretation
# ---------------------------------------------------------------------------

def _interpret_betas(betas: dict) -> list[str]:
    interp = []

    mkt = betas.get("market_excess")
    if mkt:
        b = mkt["beta"]
        if b > 1.3:
            interp.append(f"High market beta ({b:.2f}): amplified market moves – aggressive growth stock.")
        elif b > 0.8:
            interp.append(f"Normal market beta ({b:.2f}): moves roughly in line with KSE-100.")
        else:
            interp.append(f"Low market beta ({b:.2f}): defensive stock, less correlated to market.")

    sbp = betas.get("sbp_rate")
    if sbp:
        b = sbp["beta"]
        if b < -10:
            interp.append(f"Rate-sensitive (β={b:.1f}): stock falls when SBP raises rates (interest-rate risk).")
        elif b > 10:
            interp.append(f"Rate beneficiary (β={b:.1f}): stock benefits from rate hikes (e.g. banks).")

    fx = betas.get("pkr_usd")
    if fx:
        b = fx["beta"]
        if b > 0.3:
            interp.append(f"PKR depreciation beneficiary (β={b:.2f}): earns in USD or has FX asset exposure.")
        elif b < -0.3:
            interp.append(f"PKR depreciation hurt (β={b:.2f}): high import costs or USD debt burden.")

    oil = betas.get("brent")
    if oil:
        b = oil["beta"]
        if b > 0.3:
            interp.append(f"Oil-linked upside (β={b:.2f}): revenues tied to energy prices.")
        elif b < -0.3:
            interp.append(f"Oil cost exposure (β={b:.2f}): margins squeezed by higher oil prices.")

    return interp


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    model = PSXMacroFactorModel()

    # Check if macro data exists; seed synthetic if empty
    if not model.macro.available_series():
        print("Seeding synthetic macro data for demonstration...")
        model.macro.seed_synthetic()

    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["LUCK.KA", "PPL.KA", "OGDC.KA"]

    for sym in symbols:
        print(f"\n{'='*60}")
        result = model.fit(sym)
        print(json.dumps({k: v for k, v in result.items() if k != "stress_tests"}, indent=2))
        print(f"\n--- Stress Tests for {sym} ---")
        for st in result.get("stress_tests", []):
            print(f"  {st['scenario']}: {st['total_impact_pct']:+.1f}%  [{st['impact_label']}]")
