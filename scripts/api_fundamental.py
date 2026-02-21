"""
Bridge script: runs PSXFundamentalAgent and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_fundamental.py <mode> [symbol_or_symbols]
  mode: quick | deep | screen
  symbol_or_symbols: for quick/deep one symbol (e.g. OGDC); for screen comma-separated or omit for default list.
"""
import sys
import os
import json
from datetime import datetime
from dataclasses import asdict
from typing import Any, Dict

# Ensure project root is on the path so psx_fundamental_agent can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_fundamental_agent import (
    PSXFundamentalAgent,
    FundamentalScore,
    ValuationMetrics,
    FinancialHealthMetrics,
    GrowthMetrics,
    MomentumMetrics,
    RedFlag,
)

DEFAULT_SYMBOLS = [
    "LUCK", "PSO", "HBL", "ENGRO", "MCB",
    "OGDC", "PPL", "UBL", "HUBC", "FFC",
]


def score_to_dict(score: FundamentalScore) -> Dict[str, Any]:
    """Convert FundamentalScore to JSON-serializable dict (enums as .value)."""
    red_flags_serialized = [
        {
            "flag": r.flag,
            "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
            "action": r.action.value if hasattr(r.action, "value") else str(r.action),
            "description": r.description,
        }
        for r in score.red_flags
    ]
    return {
        "symbol": score.symbol,
        "fundamental_score": score.fundamental_score,
        "recommendation": score.recommendation.value if hasattr(score.recommendation, "value") else str(score.recommendation),
        "confidence": score.confidence.value if hasattr(score.confidence, "value") else str(score.confidence),
        "valuation": asdict(score.valuation),
        "financial_health": asdict(score.financial_health),
        "growth_metrics": asdict(score.growth_metrics),
        "momentum_metrics": asdict(score.momentum_metrics),
        "red_flags": red_flags_serialized,
        "catalysts": list(score.catalysts),
        "analyst_consensus": score.analyst_consensus,
        "fair_value": score.fair_value,
        "upside_pct": score.upside_pct,
        "data_timestamp": score.data_timestamp,
        "data_quality": score.data_quality,
        "valuation_score": score.valuation_score,
        "health_score": score.health_score,
        "growth_score": score.growth_score,
        "momentum_score": score.momentum_score,
        "processing_time_ms": score.processing_time_ms,
        "analysis_mode": score.analysis_mode,
        "research_report": score.research_report,
    }


def main() -> None:
    mode = (sys.argv[1] or "quick").strip().lower()
    if mode not in ("quick", "deep", "screen"):
        print(json.dumps({"success": False, "error": f"Invalid mode: {mode}. Use quick, deep, or screen."}))
        sys.exit(1)

    symbol_arg = (sys.argv[2] or "").strip().upper().replace(".KA", "")
    if mode in ("quick", "deep") and not symbol_arg:
        print(json.dumps({"success": False, "error": "Symbol required for quick and deep mode."}))
        sys.exit(1)

    if mode == "screen":
        symbols_list = [s.strip().upper().replace(".KA", "") for s in symbol_arg.split(",") if s.strip()] if symbol_arg else DEFAULT_SYMBOLS
    else:
        symbols_list = [symbol_arg]

    # For deep mode, use an LLM client so the agent runs the full research pipeline (given prompts).
    llm_client = None
    if mode == "deep":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if api_key:
            try:
                import anthropic
                llm_client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                pass

    try:
        devnull = open(os.devnull, "w", encoding="utf-8")
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            agent = PSXFundamentalAgent(cache_ttl_hours=24, llm_client=llm_client)
            if mode == "quick":
                score = agent.quick_analysis(symbols_list[0])
                data = score_to_dict(score)
            elif mode == "deep":
                score = agent.deep_analysis(symbols_list[0])
                data = score_to_dict(score)
            else:
                results = agent.screen_universe(symbols_list)
                data = {
                    "results": {sym: score_to_dict(s) for sym, s in results.items()},
                    "symbols_analyzed": len(symbols_list),
                }
        finally:
            sys.stdout = old_stdout
            devnull.close()

        out = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
