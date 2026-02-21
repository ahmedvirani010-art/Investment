"""
PSX Advanced Analysis Orchestrator
=====================================
Integrates ALL advanced agents into a unified, comprehensive analysis pipeline:

  1. Market Regime Detection    (psx_regime_detector.py)
  2. GARCH Volatility Modeling  (psx_garch_volatility.py)
  3. Advanced Risk Metrics      (psx_advanced_risk_metrics.py)
  4. Portfolio Optimization     (psx_portfolio_optimizer.py)
  5. Quantitative Quality Score (psx_quant_quality_scorer.py)
  6. Cointegration & Pairs      (psx_cointegration_pairs.py)
  7. Macro Factor Model         (psx_macro_factor_model.py)
  8. Advanced Backtesting       (psx_backtesting_framework.py)

  … plus existing agents:
  - Technical indicators (psx_technical_agent.py)
  - Fundamental scoring  (psx_fundamental_agent.py)
  - Anomaly detection    (psx_anomaly_agent.py)
  - News correlation     (psx_news_anomaly_correlator.py)

Output:
  - Per-stock advanced analysis report
  - Market-wide regime summary
  - Portfolio optimization recommendations
  - Top pairs trading opportunities
  - Macro risk attribution
  - Backtesting comparison
  - Comprehensive JSON report saved to advanced_analysis_<timestamp>.json

Usage:
  python run_advanced_analysis.py [symbol1 symbol2 ...]
  python run_advanced_analysis.py  # uses default PSX liquid stocks
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from typing import Optional

# ---- Advanced agent imports ----
try:
    from psx_regime_detector       import PSXRegimeDetector
    HAS_REGIME = True
except ImportError:
    HAS_REGIME = False

try:
    from psx_garch_volatility      import PSXGARCHVolatilityAgent
    HAS_GARCH = True
except ImportError:
    HAS_GARCH = False

try:
    from psx_advanced_risk_metrics import PSXAdvancedRiskMetrics
    HAS_RISK = True
except ImportError:
    HAS_RISK = False

try:
    from psx_portfolio_optimizer   import PSXPortfolioOptimizer
    HAS_MPT = True
except ImportError:
    HAS_MPT = False

try:
    from psx_cointegration_pairs   import PSXCointegrationScanner
    HAS_PAIRS = True
except ImportError:
    HAS_PAIRS = False

try:
    from psx_macro_factor_model    import PSXMacroFactorModel
    HAS_MACRO = True
except ImportError:
    HAS_MACRO = False

try:
    from psx_backtesting_framework import (
        PSXStrategyComparator, PSXBacktester,
        MomentumBreakoutStrategy, RSIMeanReversionStrategy, DualMAStrategy
    )
    HAS_BACKTEST = True
except ImportError:
    HAS_BACKTEST = False

try:
    from psx_quant_quality_scorer  import PSXQuantQualityScorer
    HAS_QUALITY = True
except ImportError:
    HAS_QUALITY = False

# ---- Existing agent imports (optional) ----
try:
    from psx_technical_agent import PSXTechnicalAgent
    HAS_TECHNICAL = True
except ImportError:
    HAS_TECHNICAL = False

try:
    from psx_fundamental_agent import PSXFundamentalAgent
    HAS_FUNDAMENTAL = True
except ImportError:
    HAS_FUNDAMENTAL = False

try:
    from psx_anomaly_agent import PSXAnomalyAgent
    HAS_ANOMALY = True
except ImportError:
    HAS_ANOMALY = False


# ---------------------------------------------------------------------------
# Default PSX universe
# ---------------------------------------------------------------------------

DEFAULT_SYMBOLS = [
    "LUCK.KA",  "PPL.KA",  "OGDC.KA", "HBL.KA",  "MCB.KA",
    "UBL.KA",   "ENGRO.KA","DGKC.KA", "PSO.KA",  "POL.KA",
    "MLCF.KA",  "ABL.KA",  "CHCC.KA", "FAUJI.KA","MARI.KA",
]

PRICE_DB = "price_data/prices.db"
MACRO_DB = "price_data/macro.db"


# ---------------------------------------------------------------------------
# Section runner (safe wrapper)
# ---------------------------------------------------------------------------

def _run_safe(section_name: str, fn):
    """Run fn(), return result or error dict on exception."""
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc), "traceback": traceback.format_exc()[-500:]}


# ---------------------------------------------------------------------------
# Per-stock analysis
# ---------------------------------------------------------------------------

def analyse_stock(symbol: str, portfolio_value: float = 5_000_000) -> dict:
    """Run all advanced analyses for a single symbol."""
    print(f"  Analysing {symbol}...")

    result: dict = {"symbol": symbol, "timestamp": datetime.now().isoformat()}

    # 1. Market Regime
    if HAS_REGIME:
        result["regime"] = _run_safe("regime", lambda: PSXRegimeDetector(PRICE_DB).detect(symbol))

    # 2. GARCH Volatility
    if HAS_GARCH:
        result["volatility"] = _run_safe("garch", lambda: PSXGARCHVolatilityAgent(PRICE_DB).analyse(symbol))

    # 3. Advanced Risk Metrics
    if HAS_RISK:
        result["risk_metrics"] = _run_safe("risk", lambda: PSXAdvancedRiskMetrics(PRICE_DB).compute(
            symbol, portfolio_value=portfolio_value))

    # 4. Macro Factor Model
    if HAS_MACRO:
        result["macro_factors"] = _run_safe("macro", lambda: PSXMacroFactorModel(PRICE_DB, MACRO_DB).fit(symbol))

    # 5. Backtesting (quick single-strategy run)
    if HAS_BACKTEST:
        def _bt():
            bt = PSXBacktester(PRICE_DB)
            strat = DualMAStrategy()
            return bt.walk_forward(symbol, strat, {"fast_period": 20, "slow_period": 50},
                                   initial_capital=1_000_000, n_splits=3)
        result["backtest_dualma"] = _run_safe("backtest", _bt)

    # 6. Existing technical analysis (if available)
    if HAS_TECHNICAL:
        def _tech():
            agent = PSXTechnicalAgent(PRICE_DB)
            return agent.analyse(symbol) if hasattr(agent, "analyse") else {"skipped": True}
        result["technical"] = _run_safe("technical", _tech)

    return result


# ---------------------------------------------------------------------------
# Market-wide analysis
# ---------------------------------------------------------------------------

def market_wide_analysis(symbols: list[str],
                          portfolio_value: float = 5_000_000) -> dict:
    """Run cross-stock analyses: regime summary, portfolio opt, pairs."""
    print("\n[Market-Wide Analysis]")
    result: dict = {"timestamp": datetime.now().isoformat()}

    # 1. Market Regime Summary
    if HAS_REGIME:
        print("  Regime detection...")
        result["market_regime"] = _run_safe("market_regime",
            lambda: PSXRegimeDetector(PRICE_DB).market_regime_summary(symbols))

    # 2. Portfolio Optimization
    if HAS_MPT:
        print("  Portfolio optimization...")
        def _mpt():
            opt = PSXPortfolioOptimizer(PRICE_DB)
            r = opt.optimize(symbols, min_weight=0.0, max_weight=0.35)
            # Remove verbose efficient frontier for summary
            r.pop("efficient_frontier", None)
            return r
        result["portfolio_optimization"] = _run_safe("mpt", _mpt)

    # 3. Portfolio VaR
    if HAS_RISK:
        print("  Portfolio VaR...")
        result["portfolio_var"] = _run_safe("port_var",
            lambda: PSXAdvancedRiskMetrics(PRICE_DB).portfolio_var(symbols))

    # 4. Pairs Trading
    if HAS_PAIRS:
        print("  Scanning for cointegrated pairs...")
        def _pairs():
            scanner = PSXCointegrationScanner(PRICE_DB)
            pairs   = scanner.find_pairs(symbols, min_corr=0.50)
            # Remove raw residuals from output (too verbose)
            for p in pairs:
                p.pop("residuals", None)
                if "cointegration" in p:
                    p["cointegration"].pop("residuals", None)
            return {"n_pairs_found": len(pairs),
                    "top_pairs": pairs[:5],
                    "active_signals": [p for p in pairs
                                       if p.get("spread", {}).get("signal") not in
                                       ("HOLD", "EXIT_NEUTRAL")][:5]}
        result["pairs_trading"] = _run_safe("pairs", _pairs)

    # 5. Strategy comparison across top stocks
    if HAS_BACKTEST:
        print("  Strategy comparison...")
        def _strat_comp():
            comp = PSXStrategyComparator(PRICE_DB)
            top3 = symbols[:3]
            return {sym: comp.compare(sym) for sym in top3}
        result["strategy_comparison"] = _run_safe("strat_comp", _strat_comp)

    return result


# ---------------------------------------------------------------------------
# Synthesis: generate final investment scorecard
# ---------------------------------------------------------------------------

def _build_scorecard(symbol: str, stock_result: dict) -> dict:
    """
    Synthesise all advanced analyses into a concise investment scorecard.
    Score: 0-100 composite (higher = more attractive).
    """
    score  = 50.0   # neutral baseline
    flags  = []
    green  = []

    # ---- Regime bias ----
    regime_info = stock_result.get("regime", {})
    regime = regime_info.get("regime", "UNKNOWN")
    if regime == "BULL":
        score += 10; green.append("Bull regime: momentum favours longs.")
    elif regime == "BEAR":
        score -= 10; flags.append("Bear regime: higher caution required.")
    elif regime == "HIGH_VOLATILITY":
        score -= 5;  flags.append("High-volatility regime: reduce position size.")
    elif regime == "SIDEWAYS":
        score += 2;  green.append("Sideways regime: mean-reversion strategies preferred.")

    # ---- GARCH volatility ----
    vol_info = stock_result.get("volatility", {})
    vol_regime_label = vol_info.get("vol_regime", {}).get("label", "NORMAL")
    if vol_regime_label == "EXTREME":
        score -= 15; flags.append("Extreme vol: extremely high price uncertainty.")
    elif vol_regime_label == "HIGH":
        score -= 8;  flags.append("High vol: wider stops needed, reduce size.")
    elif vol_regime_label == "LOW":
        score += 8;  green.append("Low vol: compressed risk, potential breakout setup.")

    # ---- Advanced risk ----
    risk_info = stock_result.get("risk_metrics", {})
    risk_score = risk_info.get("risk_score", {})
    risk_label = risk_score.get("label", "MODERATE")
    if risk_label == "VERY HIGH":
        score -= 12; flags.append("Very-high composite risk score.")
    elif risk_label == "HIGH":
        score -= 6
    elif risk_label == "LOW":
        score += 8;  green.append("Low composite risk score.")

    ret_metrics = risk_info.get("return_metrics", {})
    sharpe = ret_metrics.get("sharpe_ratio", 0)
    if sharpe > 1.5:
        score += 10; green.append(f"Excellent Sharpe ratio ({sharpe:.2f}).")
    elif sharpe > 0.5:
        score += 5;  green.append(f"Positive Sharpe ({sharpe:.2f}).")
    elif sharpe < 0:
        score -= 8;  flags.append(f"Negative Sharpe ({sharpe:.2f}) – destroying risk-adj. value.")

    # ---- Macro factor ----
    macro_info = stock_result.get("macro_factors", {})
    alpha_ann  = macro_info.get("alpha", {}).get("annualised", 0)
    if alpha_ann > 0.05:
        score += 8;  green.append(f"Positive alpha ({alpha_ann*100:.1f}% pa) – skilled management or mispricing.")
    elif alpha_ann < -0.05:
        score -= 8;  flags.append(f"Negative alpha ({alpha_ann*100:.1f}% pa) – structurally underperforming.")

    # ---- Backtest ----
    bt_info = stock_result.get("backtest_dualma", {})
    oos_sharpe = bt_info.get("aggregate_oos", {}).get("avg_oos_sharpe_ratio", 0)
    overfit    = bt_info.get("overfit_warning", False)
    if oos_sharpe > 1.0 and not overfit:
        score += 8;  green.append(f"DualMA walk-forward OOS Sharpe {oos_sharpe:.2f} – strategy validated.")
    elif overfit:
        flags.append("Strategy shows overfitting in walk-forward test.")

    # Clamp
    score = max(0, min(100, round(score, 1)))
    if score >= 70:
        verdict = "STRONG BUY / OVERWEIGHT"
    elif score >= 55:
        verdict = "BUY / SLIGHT OVERWEIGHT"
    elif score >= 45:
        verdict = "HOLD / NEUTRAL"
    elif score >= 30:
        verdict = "UNDERWEIGHT / AVOID"
    else:
        verdict = "SELL / STRONG AVOID"

    return {
        "symbol":     symbol,
        "score":      score,
        "verdict":    verdict,
        "regime":     regime,
        "vol_regime": vol_regime_label,
        "sharpe":     round(sharpe, 4),
        "alpha_ann":  round(alpha_ann, 4),
        "green_flags": green,
        "red_flags":  flags,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_advanced_analysis(symbols: Optional[list[str]] = None,
                           portfolio_value: float = 5_000_000,
                           save_report: bool = True) -> dict:
    """
    Full advanced analysis pipeline.

    Args:
        symbols:         List of PSX tickers. Uses DEFAULT_SYMBOLS if None.
        portfolio_value: Total portfolio value in PKR for sizing calculations.
        save_report:     Write JSON report to disk.

    Returns:
        Comprehensive results dict.
    """
    symbols = symbols or DEFAULT_SYMBOLS
    print(f"\n{'='*70}")
    print(f"PSX ADVANCED ANALYSIS PIPELINE")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")

    # ---- Seed macro data if empty ----
    if HAS_MACRO:
        from psx_macro_factor_model import MacroDataStore
        macro_store = MacroDataStore(MACRO_DB)
        if not macro_store.available_series():
            print("Seeding synthetic macro data (first-run setup)...")
            macro_store.seed_synthetic()

    # ---- Per-stock analysis ----
    print("[Per-Stock Advanced Analysis]")
    stock_results = {}
    for sym in symbols:
        stock_results[sym] = analyse_stock(sym, portfolio_value)

    # ---- Market-wide analysis ----
    market_results = market_wide_analysis(symbols, portfolio_value)

    # ---- Investment scorecards ----
    print("\n[Generating Investment Scorecards]")
    scorecards = [_build_scorecard(sym, stock_results[sym]) for sym in symbols]
    scorecards.sort(key=lambda x: x["score"], reverse=True)

    # ---- Compile full report ----
    report = {
        "metadata": {
            "generated_at":  datetime.now().isoformat(),
            "n_symbols":     len(symbols),
            "symbols":       symbols,
            "portfolio_value_pkr": portfolio_value,
            "agents_loaded": {
                "regime_detector":      HAS_REGIME,
                "garch_volatility":     HAS_GARCH,
                "advanced_risk":        HAS_RISK,
                "portfolio_optimizer":  HAS_MPT,
                "quant_quality":        HAS_QUALITY,
                "cointegration_pairs":  HAS_PAIRS,
                "macro_factor_model":   HAS_MACRO,
                "backtesting":          HAS_BACKTEST,
                "technical_agent":      HAS_TECHNICAL,
                "fundamental_agent":    HAS_FUNDAMENTAL,
                "anomaly_agent":        HAS_ANOMALY,
            },
        },
        "scorecards":     scorecards,
        "stock_analysis": stock_results,
        "market_analysis": market_results,
    }

    # ---- Save report ----
    if save_report:
        os.makedirs("reports", exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/advanced_analysis_{ts}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved → {filename}")

    # ---- Print summary ----
    print(f"\n{'='*70}")
    print("INVESTMENT SCORECARD SUMMARY (Advanced Analysis)")
    print(f"{'='*70}")
    print(f"{'Symbol':<12} {'Score':>6} {'Verdict':<28} {'Regime':<14} {'Vol':<12} {'Sharpe':>8}")
    print("-" * 80)
    for sc in scorecards:
        print(f"{sc['symbol']:<12} {sc['score']:>6.0f} {sc['verdict']:<28} "
              f"{sc['regime']:<14} {sc['vol_regime']:<12} {sc['sharpe']:>8.3f}")

    # ---- Market regime summary ----
    mr = market_results.get("market_regime", {})
    if mr and not mr.get("error"):
        print(f"\nMarket Regime: {mr.get('market_regime', 'N/A')} "
              f"(confidence: {mr.get('confidence', 0):.1%})")
        breakdown = mr.get("regime_breakdown", {})
        if breakdown:
            print("  " + " | ".join(f"{k}: {v:.0%}" for k, v in breakdown.items()))

    # ---- Portfolio optimization ----
    mpt = market_results.get("portfolio_optimization", {})
    if mpt and not mpt.get("error"):
        rec  = mpt.get("recommendation", {})
        port = mpt.get("portfolios", {})
        best_key = rec.get("recommended_portfolio", "maximum_sharpe")
        best_port = port.get(best_key, {})
        print(f"\nRecommended Portfolio: {best_key.upper()}")
        print(f"  Return: {best_port.get('return', 0)*100:.1f}%  "
              f"Vol: {best_port.get('vol', 0)*100:.1f}%  "
              f"Sharpe: {best_port.get('sharpe', 0):.2f}")
        weights = best_port.get("weights", {})
        if weights:
            top_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]
            print("  Top weights: " + ", ".join(f"{s}: {w:.1%}" for s, w in top_w))

    # ---- Top pairs ----
    pairs_info = market_results.get("pairs_trading", {})
    active     = pairs_info.get("active_signals", [])
    if active:
        print(f"\nActive Pairs Trading Signals ({len(active)}):")
        for p in active[:3]:
            sp = p.get("spread", {})
            print(f"  {p['pair']:<20} Signal: {sp.get('signal','N/A'):<18} "
                  f"Z={sp.get('z_score', 0):+.2f}  Grade={p.get('pair_quality',{}).get('grade','?')}")

    print(f"\n{'='*70}")
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    symbols = sys.argv[1:] if len(sys.argv) > 1 else None
    report  = run_advanced_analysis(symbols, portfolio_value=5_000_000)
