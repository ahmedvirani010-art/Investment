"""
Backtest veto agent: given point-in-time technical data and a proposed action,
calls an LLM to return PROCEED or VETO. Used by the HMM regime backtester as a veto vote.
"""

from typing import Any, Optional, Tuple

VETO_SYSTEM = """You are a veto agent for a backtest. You receive only point-in-time data (no future information) and a proposed trading action.
Your job is to respond with exactly one of: PROCEED or VETO.
- PROCEED: allow the action (enter or exit) as suggested by the strategy.
- VETO: block the action based on the technical/regime context (e.g. conflicting signals, risk, or weak confirmation).

You may add one short reason on the next line after PROCEED or VETO. Do not give trading advice; only decide whether to allow or block this single action."""


def _format_payload(payload: dict[str, Any]) -> str:
    """Format the point-in-time payload as readable text for the LLM."""
    lines = [
        f"Timestamp (as of): {payload.get('as_of_timestamp', '')}",
        f"Proposed action: {payload.get('action', '')}",
        f"Regime: {payload.get('regime', '')}",
        f"Bull votes (conditions met): {payload.get('votes', 0)} / 8",
        f"Bear votes (conditions met): {payload.get('votes_bear', 0)} / 8",
        "",
        "Bull conditions (true/false):",
    ]
    for name, val in payload.get("conditions_bull", {}).items():
        lines.append(f"  {name}: {val}")
    lines.append("")
    lines.append("Bear conditions (true/false):")
    for name, val in payload.get("conditions_bear", {}).items():
        lines.append(f"  {name}: {val}")
    if payload.get("indicator_values"):
        lines.append("")
        lines.append("Indicator values at this bar:")
        for k, v in payload["indicator_values"].items():
            if isinstance(v, float) and (v != v or abs(v) > 1e10):  # NaN or inf
                lines.append(f"  {k}: N/A")
            else:
                lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def ask_veto(
    payload: dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Tuple[str, str]:
    """
    Ask the veto agent whether to allow the proposed action.

    Args:
        payload: Point-in-time dict with as_of_timestamp, action, regime, votes,
                 votes_bear, conditions_bull, conditions_bear, optional indicator_values.
        llm_client: Anthropic client (e.g. anthropic.Anthropic()). If None, returns PROCEED.

    Returns:
        ("PROCEED", reason) or ("VETO", reason). reason may be empty.
    """
    if llm_client is None:
        return "PROCEED", ""

    user_text = _format_payload(payload)
    try:
        response = llm_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=VETO_SYSTEM,
            messages=[{"role": "user", "content": user_text}],
        )
        text = response.content[0].text.strip().upper()
    except Exception:
        return "PROCEED", ""

    # Parse first line for PROCEED or VETO
    first_line = text.split("\n")[0].strip() if text else ""
    if "VETO" in first_line:
        result = "VETO"
    else:
        result = "PROCEED"
    reason = "\n".join(text.split("\n")[1:]).strip() if "\n" in text else ""
    return result, reason
