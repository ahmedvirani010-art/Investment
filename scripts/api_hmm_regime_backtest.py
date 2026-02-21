"""
Bridge script: runs HMM Regime backtest and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_hmm_regime_backtest.py [symbol] [--period 730d] [--interval 1h] [--n-components 7]
  Optional (for optimized params): --cooldown-hours 48 --leverage 1.25 --min-confirmations 6
  Optional short trades: --allow-short [--min-bear-confirmations N]
  Optional AI veto: --use-agent-veto (requires ANTHROPIC_API_KEY in env)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="BTC-USD", help="e.g. BTC-USD")
    parser.add_argument("--period", default="730d")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--n-components", type=int, default=7)
    parser.add_argument("--cooldown-hours", type=float, default=None)
    parser.add_argument("--leverage", type=float, default=None)
    parser.add_argument("--min-confirmations", type=int, default=None)
    parser.add_argument("--allow-short", action="store_true", help="Include short trades in bear regime")
    parser.add_argument("--min-bear-confirmations", type=int, default=None)
    parser.add_argument("--use-agent-veto", action="store_true", help="Use LLM veto agent (requires ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    llm_client = None
    if args.use_agent_veto:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                llm_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass  # run without veto if anthropic not installed
        # if no key or import failed, llm_client stays None and backtest runs without veto

    result = run_backtest(
        symbol=args.symbol,
        period=args.period,
        interval=args.interval,
        n_components=args.n_components,
        cooldown_hours=args.cooldown_hours,
        leverage=args.leverage,
        min_confirmations=args.min_confirmations,
        allow_short=args.allow_short,
        min_bear_confirmations=args.min_bear_confirmations,
        use_agent_veto=args.use_agent_veto,
        llm_client=llm_client,
    )

    trades_payload = [
        {
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "return_pct": t.return_pct,
            "leveraged_return_pct": t.leveraged_return_pct,
            "side": t.side,
        }
        for t in result.trades
    ]

    out = {
        "current_signal": result.current_signal,
        "current_regime": result.current_regime,
        "bull_state_id": result.bull_state_id,
        "bear_state_id": result.bear_state_id,
        "timestamps": result.timestamps,
        "open": result.open,
        "high": result.high,
        "low": result.low,
        "close": result.close,
        "states": result.states,
        "equity_curve": result.equity_curve,
        "trades": trades_payload,
        "total_return_pct": result.total_return_pct,
        "buy_hold_return_pct": result.buy_hold_return_pct,
        "alpha_pct": result.alpha_pct,
        "win_rate": result.win_rate,
        "max_drawdown_pct": result.max_drawdown_pct,
        "vetoes_issued": getattr(result, "vetoes_issued", 0),
        "veto_events": getattr(result, "veto_events", []),
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
