"""
Bridge script: runs PSXTechnicalAgent and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_technical.py <mode> [symbol_or_symbols] [filter]
  mode: single | batch | mtf | screen
  symbol_or_symbols: for single/mtf one symbol (e.g. OGDC); for batch/screen comma-separated or omit for default list.
  filter: for screen only: overbought | oversold | both (default both).
"""
import sys
import os
import json
from datetime import datetime
from typing import Any, Dict

# Ensure project root is on the path so psx_technical_agent and psx_price_store can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_price_store import PSXPriceStore
from psx_technical_agent import (
    PSXTechnicalAgent,
    TechnicalSnapshot,
    TechnicalSignal,
    SignalType,
    SignalStrength,
    MultiTimeframeSnapshot,
)

try:
    from llm_client import chat_completion as llm_chat_completion
    _LLM_AVAILABLE = True
except Exception:
    llm_chat_completion = None
    _LLM_AVAILABLE = False

DEFAULT_SYMBOLS = [
    "LUCK", "PSO", "HBL", "ENGRO", "MCB",
    "OGDC", "PPL", "UBL", "HUBC", "FFC",
]


def snapshot_to_dict(snapshot: TechnicalSnapshot) -> Dict[str, Any]:
    """Convert TechnicalSnapshot to JSON-serializable dict (enums as .value)."""
    signals_serialized = [
        {
            "symbol": s.symbol,
            "date": s.date,
            "indicator": s.indicator,
            "signal_type": s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
            "strength": s.strength.value if hasattr(s.strength, "value") else str(s.strength),
            "value": s.value,
            "threshold": s.threshold,
            "description": s.description or "",
        }
        for s in snapshot.signals
    ]
    out = {
        "symbol": snapshot.symbol,
        "date": snapshot.date,
        "signals": signals_serialized,
        "overall_bias": (
            snapshot.overall_bias.value
            if hasattr(snapshot.overall_bias, "value")
            else str(snapshot.overall_bias)
        ),
        "confidence": snapshot.confidence,
        "indicator_values": snapshot.indicator_values,
        "trend_score": getattr(snapshot, "trend_score", 50),
        "mean_reversion_score": getattr(snapshot, "mean_reversion_score", 50),
        "technical_score": getattr(snapshot, "technical_score", 50),
    }
    if getattr(snapshot, "divergences", None):
        out["divergences"] = [
            d if isinstance(d, dict) else getattr(d, "__dict__", str(d))
            for d in snapshot.divergences
        ]
    if getattr(snapshot, "patterns", None):
        out["patterns"] = [
            p if isinstance(p, dict) else getattr(p, "__dict__", str(p))
            for p in snapshot.patterns
        ]
    if getattr(snapshot, "fibonacci_levels", None):
        out["fibonacci_levels"] = snapshot.fibonacci_levels
    if getattr(snapshot, "elliott_wave", None):
        out["elliott_wave"] = snapshot.elliott_wave
    # Always include AI summary/call so the frontend can show the section (or a fallback)
    out["ai_summary"] = getattr(snapshot, "ai_summary", None)
    out["ai_call"] = getattr(snapshot, "ai_call", None)
    out["ai_call_rationale"] = getattr(snapshot, "ai_call_rationale", None)
    return out


def multi_timeframe_to_dict(mtf: MultiTimeframeSnapshot) -> Dict[str, Any]:
    """Convert MultiTimeframeSnapshot to JSON-serializable dict."""
    return {
        "symbol": mtf.symbol,
        "date": mtf.date,
        "daily": snapshot_to_dict(mtf.daily),
        "weekly": snapshot_to_dict(mtf.weekly),
        "confirmation_score": mtf.confirmation_score,
        "aligned_signals": list(mtf.aligned_signals),
        "conflicting_signals": list(mtf.conflicting_signals),
    }


def main() -> None:
    mode = (sys.argv[1] or "single").strip().lower()
    if mode not in ("single", "batch", "mtf", "screen"):
        print(json.dumps({"success": False, "error": f"Invalid mode: {mode}. Use single, batch, mtf, or screen."}))
        sys.exit(1)

    symbol_arg = (sys.argv[2] or "").strip().upper().replace(".KA", "")
    if mode in ("single", "mtf") and not symbol_arg:
        print(json.dumps({"success": False, "error": "Symbol required for single and mtf mode."}))
        sys.exit(1)

    if mode in ("batch", "screen"):
        symbols_list = (
            [s.strip().upper().replace(".KA", "") for s in symbol_arg.split(",") if s.strip()]
            if symbol_arg
            else DEFAULT_SYMBOLS
        )
    else:
        symbols_list = [symbol_arg]

    screen_filter = "both"
    if mode == "screen":
        filter_arg = (sys.argv[3] or "both").strip().lower()
        if filter_arg in ("overbought", "oversold", "both"):
            screen_filter = filter_arg

    try:
        price_store = PSXPriceStore()
        devnull = open(os.devnull, "w", encoding="utf-8")
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            for sym in symbols_list:
                price_store.fetch_and_store(sym, days=250)
            if mode == "mtf":
                price_store.update_weekly_from_daily(symbols_list)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            devnull.close()

        llm_client = llm_chat_completion if _LLM_AVAILABLE else None
        agent = PSXTechnicalAgent(price_store, llm_client=llm_client)

        if mode == "single":
            snapshot = agent.analyze_symbol(symbols_list[0])
            data = snapshot_to_dict(snapshot)
        elif mode == "mtf":
            mtf = agent.analyze_multi_timeframe(symbols_list[0])
            data = multi_timeframe_to_dict(mtf)
        elif mode == "screen":
            results = agent.analyze_batch(symbols_list)
            want_overbought = screen_filter in ("overbought", "both")
            want_oversold = screen_filter in ("oversold", "both")
            filtered = {}
            for sym, snap in results.items():
                has_ob = any(s.signal_type == SignalType.OVERBOUGHT for s in snap.signals)
                has_os = any(s.signal_type == SignalType.OVERSOLD for s in snap.signals)
                if (want_overbought and has_ob) or (want_oversold and has_os):
                    filtered[sym] = snap
            data = {
                "results": {sym: snapshot_to_dict(s) for sym, s in filtered.items()},
                "symbols_analyzed": len(symbols_list),
                "symbols_matching": len(filtered),
                "filter": screen_filter,
            }
        else:
            results = agent.analyze_batch(symbols_list)
            data = {
                "results": {sym: snapshot_to_dict(s) for sym, s in results.items()},
                "symbols_analyzed": len(symbols_list),
            }

        out = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(out))
    except Exception as e:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
