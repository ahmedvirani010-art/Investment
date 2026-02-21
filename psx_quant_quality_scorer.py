"""
PSX Quantitative Quality Scoring Agent
========================================
Implements three battle-tested quantitative quality frameworks:

1. PIOTROSKI F-SCORE (0–9)
   Measures financial strength across 9 binary signals:
   - Profitability (4 signals): ROA, CFO, ΔROA, Accruals
   - Leverage/Liquidity (3 signals): ΔLeverage, ΔLiquidity, Share issuance
   - Operating Efficiency (2 signals): ΔMargin, ΔTurnover
   F-score >= 7 → Strong BUY candidate; <= 2 → Potential short

2. ALTMAN Z-SCORE (bankruptcy predictor)
   Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
   Z > 2.99 → Safe zone; 1.81–2.99 → Grey zone; < 1.81 → Distress
   (Adapted Z' for non-listed or private firms also supported)

3. BENEISH M-SCORE (earnings manipulation detector)
   M < -2.22 → Low manipulation probability
   M > -2.22 → Possible earnings manipulation (red flag)

Combined Composite Quality Score → STRONG / GOOD / FAIR / WEAK / DISTRESSED

Note: Requires financial metrics in the database or provided as dict.
      Falls back to partial scores when data is incomplete.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

FinancialData = dict   # {metric_name: value}


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

class PiotroskiFScore:
    """
    Computes the Piotroski F-Score from two years of financial data.

    Required financial metrics (year 0 = current, year 1 = prior year):
      roa0, roa1        : Return on Assets (net_income / avg_total_assets)
      cfo0              : Cash Flow from Operations / total_assets
      accruals0         : (net_income - cfo) / total_assets
      leverage0, lever1 : Long-term debt / avg_total_assets
      current0, curr1   : Current ratio (current_assets / current_liabilities)
      shares0, shares1  : Diluted shares outstanding
      gross_margin0, gm1: Gross margin (gross_profit / revenue)
      asset_turnover0, at1: Revenue / avg_total_assets
    """

    SIGNALS = [
        "roa_positive",
        "cfo_positive",
        "roa_improving",
        "accrual_low",
        "leverage_decreasing",
        "liquidity_improving",
        "no_dilution",
        "margin_improving",
        "turnover_improving",
    ]

    def compute(self, d: FinancialData) -> dict:
        score  = 0
        signals = {}

        # ---- Profitability ----
        roa0  = d.get("roa0",  0.0)
        roa1  = d.get("roa1",  0.0)
        cfo0  = d.get("cfo0",  0.0)
        acc0  = d.get("accruals0", 0.0)   # (NI - CFO) / TA

        signals["roa_positive"]   = 1 if roa0 > 0 else 0
        signals["cfo_positive"]   = 1 if cfo0 > 0 else 0
        signals["roa_improving"]  = 1 if roa0 > roa1 else 0
        signals["accrual_low"]    = 1 if cfo0 > roa0 else 0   # high quality earnings

        score += sum([signals["roa_positive"], signals["cfo_positive"],
                      signals["roa_improving"], signals["accrual_low"]])

        # ---- Leverage / Liquidity ----
        lev0  = d.get("leverage0", 0.0)
        lev1  = d.get("leverage1", 0.0)
        cur0  = d.get("current0",  1.0)
        cur1  = d.get("current1",  1.0)
        sh0   = d.get("shares0",   1.0)
        sh1   = d.get("shares1",   1.0)

        signals["leverage_decreasing"]  = 1 if lev0 < lev1 else 0
        signals["liquidity_improving"]  = 1 if cur0 > cur1 else 0
        signals["no_dilution"]          = 1 if sh0 <= sh1 * 1.01 else 0  # allow 1% tolerance

        score += sum([signals["leverage_decreasing"], signals["liquidity_improving"],
                      signals["no_dilution"]])

        # ---- Operating Efficiency ----
        gm0   = d.get("gross_margin0", 0.0)
        gm1   = d.get("gross_margin1", 0.0)
        at0   = d.get("asset_turnover0", 0.0)
        at1   = d.get("asset_turnover1", 0.0)

        signals["margin_improving"]   = 1 if gm0 > gm1 else 0
        signals["turnover_improving"] = 1 if at0 > at1 else 0

        score += sum([signals["margin_improving"], signals["turnover_improving"]])

        # ---- Interpretation ----
        if score >= 7:
            rating = "STRONG BUY"
            color  = "green"
        elif score >= 5:
            rating = "GOOD"
            color  = "lightgreen"
        elif score >= 3:
            rating = "FAIR"
            color  = "yellow"
        else:
            rating = "WEAK / AVOID"
            color  = "red"

        return {
            "f_score":     score,
            "max_score":   9,
            "rating":      rating,
            "signals":     signals,
            "breakdown": {
                "profitability":         sum(signals[k] for k in ["roa_positive","cfo_positive","roa_improving","accrual_low"]),
                "leverage_liquidity":    sum(signals[k] for k in ["leverage_decreasing","liquidity_improving","no_dilution"]),
                "operating_efficiency": sum(signals[k] for k in ["margin_improving","turnover_improving"]),
            },
        }


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------

class AltmanZScore:
    """
    Original Altman Z-Score for publicly traded manufacturing firms.
    Also computes Z' (private firms) and Z'' (non-manufacturing).

    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities  (or Book Equity / TL for Z')
    X5 = Revenue / Total Assets
    """

    def compute(self, d: FinancialData) -> dict:
        ta    = d.get("total_assets",       1.0)
        wc    = d.get("working_capital",     0.0)  # current_assets - current_liabilities
        re    = d.get("retained_earnings",   0.0)
        ebit  = d.get("ebit",               0.0)
        mktcap = d.get("market_cap",        None)
        book_eq = d.get("book_equity",      None)
        tl    = max(d.get("total_liabilities", 1.0), 1.0)
        rev   = d.get("revenue",            0.0)

        x1 = wc   / ta
        x2 = re   / ta
        x3 = ebit / ta
        x5 = rev  / ta

        results = {}

        # ---- Z (public manufacturing) ----
        if mktcap is not None:
            x4_pub = mktcap / tl
            z_pub  = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4_pub + 1.0*x5
            results["z_public"] = {
                "score":  round(z_pub, 3),
                "zone":   _altman_zone(z_pub, "public"),
                "x4_used": "market_cap/total_liabilities",
            }

        # ---- Z' (private) ----
        if book_eq is not None:
            x4_priv = book_eq / tl
            z_prime = 0.717*x1 + 0.847*x2 + 3.107*x3 + 0.420*x4_priv + 0.998*x5
            results["z_prime_private"] = {
                "score":  round(z_prime, 3),
                "zone":   _altman_zone(z_prime, "private"),
                "x4_used": "book_equity/total_liabilities",
            }

        # ---- Z'' (non-manufacturing / emerging markets) ----
        if book_eq is not None:
            x4_em = book_eq / tl
            z_em  = 6.56*x1 + 3.26*x2 + 6.72*x3 + 1.05*x4_em
            results["z_double_prime_em"] = {
                "score":  round(z_em, 3),
                "zone":   _altman_zone(z_em, "em"),
            }

        # Select best available
        best_key = None
        if "z_public" in results:
            best_key = "z_public"
        elif "z_prime_private" in results:
            best_key = "z_prime_private"
        elif "z_double_prime_em" in results:
            best_key = "z_double_prime_em"

        components = {
            "x1_working_capital_ratio":  round(x1, 4),
            "x2_retained_earnings_ratio": round(x2, 4),
            "x3_ebit_ratio":             round(x3, 4),
            "x5_asset_turnover":         round(x5, 4),
        }

        return {
            "models":     results,
            "best_model": best_key,
            "best_score": results[best_key]["score"] if best_key else None,
            "best_zone":  results[best_key]["zone"]  if best_key else "DATA_MISSING",
            "components": components,
        }


def _altman_zone(z: float, variant: str) -> str:
    if variant == "public":
        if z > 2.99:   return "SAFE"
        if z > 1.81:   return "GREY"
        return "DISTRESS"
    elif variant == "private":
        if z > 2.90:   return "SAFE"
        if z > 1.23:   return "GREY"
        return "DISTRESS"
    else:  # EM / Z''
        if z > 2.60:   return "SAFE"
        if z > 1.10:   return "GREY"
        return "DISTRESS"


# ---------------------------------------------------------------------------
# Beneish M-Score
# ---------------------------------------------------------------------------

class BeneishMScore:
    """
    Beneish M-Score: detects earnings manipulation probability.

    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

    Thresholds:
      M > -2.22 → Possible manipulator (red flag)
      M < -2.22 → Unlikely manipulator
    """

    def compute(self, d: FinancialData, d_prev: Optional[FinancialData] = None) -> dict:
        """
        d      : current year financials
        d_prev : prior year financials (optional; uses 0 defaults if missing)
        """
        dp = d_prev or {}

        # ---- Compute indices ----
        # DSRI: Days Sales Receivable Index
        recv0  = d.get("receivables",  0.0)
        recv1  = dp.get("receivables", recv0 * 0.9)
        rev0   = max(d.get("revenue",   1.0), 1.0)
        rev1   = max(dp.get("revenue",  rev0 * 0.9), 1.0)
        dsri   = (recv0 / rev0) / (recv1 / rev1 + 1e-9) if recv1 else 1.0

        # GMI: Gross Margin Index (prev_gm / curr_gm; > 1 = deteriorating margins)
        gp0    = d.get("gross_profit",  0.0)
        gp1    = dp.get("gross_profit", gp0)
        gmi    = ((gp1 / rev1) / (gp0 / rev0 + 1e-9)) if gp0 > 0 else 1.0

        # AQI: Asset Quality Index
        ta0    = max(d.get("total_assets", 1.0), 1.0)
        ta1    = max(dp.get("total_assets", ta0), 1.0)
        ca0    = d.get("current_assets",  0.0)
        ca1    = dp.get("current_assets", ca0)
        ppe0   = d.get("net_ppe",         0.0)
        ppe1   = dp.get("net_ppe",        ppe0)
        aqi    = (1 - (ca0 + ppe0) / ta0) / (1 - (ca1 + ppe1) / ta1 + 1e-9)

        # SGI: Sales Growth Index (curr_rev / prev_rev)
        sgi    = rev0 / rev1

        # DEPI: Depreciation Index (prev_depr_rate / curr_depr_rate)
        dep0   = max(d.get("depreciation",  1.0), 1.0)
        dep1   = max(dp.get("depreciation", dep0), 1.0)
        depi   = (dep1 / (dep1 + ppe1 + 1e-9)) / (dep0 / (dep0 + ppe0 + 1e-9) + 1e-9)

        # SGAI: Sales, General & Admin Expense Index
        sga0   = d.get("sga_expense",  0.0)
        sga1   = dp.get("sga_expense", sga0)
        sgai   = (sga0 / rev0) / (sga1 / rev1 + 1e-9) if sga1 else 1.0

        # TATA: Total Accruals to Total Assets
        ni0    = d.get("net_income",   0.0)
        cfo0   = d.get("cfo",          0.0)
        tata   = (ni0 - cfo0) / ta0

        # LVGI: Leverage Index
        ltd0   = d.get("long_term_debt", 0.0)
        ltd1   = dp.get("long_term_debt", ltd0)
        cl0    = d.get("current_liabilities", 0.0)
        cl1    = dp.get("current_liabilities", cl0)
        lvgi   = ((ltd0 + cl0) / ta0) / ((ltd1 + cl1) / ta1 + 1e-9)

        # ---- M-Score ----
        m = (-4.84
             + 0.920 * dsri
             + 0.528 * gmi
             + 0.404 * aqi
             + 0.892 * sgi
             + 0.115 * depi
             - 0.172 * sgai
             + 4.679 * tata
             - 0.327 * lvgi)

        if m > -2.22:
            verdict   = "POSSIBLE_MANIPULATOR"
            warning   = True
            desc      = "M-Score suggests elevated probability of earnings manipulation."
        else:
            verdict   = "UNLIKELY_MANIPULATOR"
            warning   = False
            desc      = "M-Score does not indicate earnings manipulation."

        return {
            "m_score":     round(m, 4),
            "threshold":   -2.22,
            "verdict":     verdict,
            "warning":     warning,
            "description": desc,
            "indices": {
                "DSRI":  round(dsri, 4),
                "GMI":   round(gmi,  4),
                "AQI":   round(aqi,  4),
                "SGI":   round(sgi,  4),
                "DEPI":  round(depi, 4),
                "SGAI":  round(sgai, 4),
                "TATA":  round(tata, 4),
                "LVGI":  round(lvgi, 4),
            },
        }


# ---------------------------------------------------------------------------
# Composite Quality Score
# ---------------------------------------------------------------------------

class PSXQuantQualityScorer:
    """
    Aggregates Piotroski, Altman, and Beneish into a Composite Quality Score.
    """

    def __init__(self, price_db: str = "price_data/prices.db"):
        self.price_db = price_db
        self.piotroski = PiotroskiFScore()
        self.altman    = AltmanZScore()
        self.beneish   = BeneishMScore()

    def score(self, symbol: str,
              current_year: FinancialData,
              prior_year: Optional[FinancialData] = None) -> dict:
        """
        Full quality scoring for a symbol.

        Args:
            symbol       : PSX ticker
            current_year : dict of current-year financial metrics
            prior_year   : dict of prior-year financial metrics (optional)

        Returns:
            Combined quality assessment with all three models.
        """
        py = prior_year or {}

        # ---- Piotroski ----
        # Build inputs from financial data dicts
        piotroski_data = {
            "roa0":           current_year.get("roa", current_year.get("net_income", 0) / max(current_year.get("total_assets", 1), 1)),
            "roa1":           py.get("roa", py.get("net_income", 0) / max(py.get("total_assets", 1), 1)),
            "cfo0":           current_year.get("cfo", 0) / max(current_year.get("total_assets", 1), 1),
            "accruals0":      (current_year.get("net_income", 0) - current_year.get("cfo", 0)) / max(current_year.get("total_assets", 1), 1),
            "leverage0":      current_year.get("long_term_debt", 0) / max(current_year.get("total_assets", 1), 1),
            "leverage1":      py.get("long_term_debt", 0) / max(py.get("total_assets", 1), 1),
            "current0":       current_year.get("current_ratio", current_year.get("current_assets", 1) / max(current_year.get("current_liabilities", 1), 1)),
            "current1":       py.get("current_ratio", py.get("current_assets", 1) / max(py.get("current_liabilities", 1), 1)),
            "shares0":        current_year.get("shares_outstanding", 1),
            "shares1":        py.get("shares_outstanding", current_year.get("shares_outstanding", 1)),
            "gross_margin0":  current_year.get("gross_margin", current_year.get("gross_profit", 0) / max(current_year.get("revenue", 1), 1)),
            "gross_margin1":  py.get("gross_margin", py.get("gross_profit", 0) / max(py.get("revenue", 1), 1)),
            "asset_turnover0": current_year.get("revenue", 0) / max(current_year.get("total_assets", 1), 1),
            "asset_turnover1": py.get("revenue", 0) / max(py.get("total_assets", 1), 1),
        }

        f_result = self.piotroski.compute(piotroski_data)

        # ---- Altman ----
        altman_data = {
            "total_assets":      current_year.get("total_assets", 1),
            "working_capital":   current_year.get("working_capital",
                                   current_year.get("current_assets", 0) -
                                   current_year.get("current_liabilities", 0)),
            "retained_earnings": current_year.get("retained_earnings", 0),
            "ebit":              current_year.get("ebit", current_year.get("operating_income", 0)),
            "market_cap":        current_year.get("market_cap", None),
            "book_equity":       current_year.get("book_equity",
                                   current_year.get("total_equity", None)),
            "total_liabilities": current_year.get("total_liabilities",
                                   current_year.get("total_assets", 1) -
                                   current_year.get("total_equity", 0)),
            "revenue":           current_year.get("revenue", 0),
        }

        z_result = self.altman.compute(altman_data)

        # ---- Beneish ----
        beneish_current = {
            "receivables":        current_year.get("receivables", 0),
            "revenue":            current_year.get("revenue", 1),
            "gross_profit":       current_year.get("gross_profit", 0),
            "total_assets":       current_year.get("total_assets", 1),
            "current_assets":     current_year.get("current_assets", 0),
            "net_ppe":            current_year.get("net_ppe", 0),
            "depreciation":       current_year.get("depreciation", 1),
            "sga_expense":        current_year.get("sga_expense", 0),
            "net_income":         current_year.get("net_income", 0),
            "cfo":                current_year.get("cfo", 0),
            "long_term_debt":     current_year.get("long_term_debt", 0),
            "current_liabilities":current_year.get("current_liabilities", 0),
        }
        beneish_prior = {
            "receivables":        py.get("receivables", beneish_current["receivables"]),
            "revenue":            py.get("revenue", beneish_current["revenue"]),
            "gross_profit":       py.get("gross_profit", beneish_current["gross_profit"]),
            "total_assets":       py.get("total_assets", beneish_current["total_assets"]),
            "current_assets":     py.get("current_assets", beneish_current["current_assets"]),
            "net_ppe":            py.get("net_ppe", beneish_current["net_ppe"]),
            "depreciation":       py.get("depreciation", beneish_current["depreciation"]),
            "sga_expense":        py.get("sga_expense", beneish_current["sga_expense"]),
            "long_term_debt":     py.get("long_term_debt", beneish_current["long_term_debt"]),
            "current_liabilities":py.get("current_liabilities", beneish_current["current_liabilities"]),
        }

        m_result = self.beneish.compute(beneish_current, beneish_prior)

        # ---- Composite Score (0-100) ----
        # Piotroski: 0-9 → 0-30 pts
        f_pts = f_result["f_score"] / 9 * 30

        # Altman: Safe=30, Grey=15, Distress=0
        zone_pts = {"SAFE": 30, "GREY": 15, "DISTRESS": 0, "DATA_MISSING": 10}
        z_pts = zone_pts.get(z_result["best_zone"], 10)

        # Beneish: no manipulation=40, possible manipulation=-20 (penalty)
        m_pts = 40 if not m_result["warning"] else 10

        composite = f_pts + z_pts + m_pts   # max = 30+30+40 = 100
        composite = round(min(composite, 100), 1)

        if composite >= 75:
            quality_label = "STRONG"
        elif composite >= 55:
            quality_label = "GOOD"
        elif composite >= 35:
            quality_label = "FAIR"
        elif composite >= 20:
            quality_label = "WEAK"
        else:
            quality_label = "DISTRESSED"

        return {
            "symbol":           symbol,
            "composite_score":  composite,
            "quality_label":    quality_label,
            "piotroski":        f_result,
            "altman":           z_result,
            "beneish":          m_result,
            "red_flags": _collect_red_flags(f_result, z_result, m_result),
            "green_flags": _collect_green_flags(f_result, z_result, m_result),
            "timestamp":        datetime.now().isoformat(),
        }


def _collect_red_flags(f: dict, z: dict, m: dict) -> list[str]:
    flags = []
    if f["f_score"] <= 2:
        flags.append(f"Piotroski F-Score critically low ({f['f_score']}/9) – financial deterioration.")
    if z["best_zone"] == "DISTRESS":
        flags.append(f"Altman Z-Score in DISTRESS zone ({z['best_score']}) – bankruptcy risk.")
    elif z["best_zone"] == "GREY":
        flags.append(f"Altman Z-Score in GREY zone ({z['best_score']}) – monitor closely.")
    if m["warning"]:
        flags.append(f"Beneish M-Score ({m['m_score']}) suggests possible earnings manipulation.")
    # Individual signal red flags
    sig = f.get("signals", {})
    if sig.get("accrual_low") == 0:
        flags.append("Low accruals quality: CFO < net income (aggressive revenue recognition risk).")
    if sig.get("leverage_decreasing") == 0:
        flags.append("Leverage increased year-over-year (balance sheet risk).")
    return flags


def _collect_green_flags(f: dict, z: dict, m: dict) -> list[str]:
    flags = []
    if f["f_score"] >= 7:
        flags.append(f"Strong Piotroski F-Score ({f['f_score']}/9) – financial health excellent.")
    if z["best_zone"] == "SAFE":
        flags.append(f"Altman Z-Score safe zone ({z['best_score']}) – no distress risk.")
    if not m["warning"]:
        flags.append("Beneish M-Score does not indicate earnings manipulation.")
    sig = f.get("signals", {})
    if sig.get("roa_positive") and sig.get("cfo_positive"):
        flags.append("Both ROA and CFO are positive – quality profitability.")
    if sig.get("no_dilution"):
        flags.append("No share dilution – management is not diluting shareholders.")
    return flags


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    scorer = PSXQuantQualityScorer()

    # Demo with synthetic LUCK-like data
    current = {
        "revenue":            50_000_000_000,
        "gross_profit":       12_500_000_000,
        "net_income":          4_000_000_000,
        "cfo":                 5_200_000_000,
        "ebit":                5_500_000_000,
        "total_assets":       35_000_000_000,
        "total_equity":       18_000_000_000,
        "total_liabilities":  17_000_000_000,
        "current_assets":      8_000_000_000,
        "current_liabilities": 5_000_000_000,
        "long_term_debt":      6_000_000_000,
        "net_ppe":            12_000_000_000,
        "retained_earnings":  10_000_000_000,
        "receivables":         4_000_000_000,
        "depreciation":        2_000_000_000,
        "sga_expense":         1_500_000_000,
        "market_cap":         80_000_000_000,
        "shares_outstanding":   800_000_000,
        "working_capital":     3_000_000_000,
        "roa":                 0.114,
        "current_ratio":       1.60,
        "gross_margin":        0.25,
    }
    prior = {k: v * 0.88 for k, v in current.items()
             if isinstance(v, (int, float)) and k not in ("roa","current_ratio","gross_margin")}
    prior.update({"roa": 0.09, "current_ratio": 1.45, "gross_margin": 0.22})

    sym = sys.argv[1] if len(sys.argv) > 1 else "LUCK.KA"
    result = scorer.score(sym, current, prior)
    print(json.dumps(result, indent=2))
