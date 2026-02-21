"""
HMM Regime backtester: 8-condition voting, 48h cooldown, 1.25x leverage.
Optional AI veto agent: when enabled, proposed actions are submitted to an LLM for PROCEED/VETO.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from backtest_indicators import compute_confirmation_conditions, compute_indicator_values
from backtest_veto_agent import ask_veto
from data_loader import load_btc_hmm

# Defaults (can be overridden via run_backtest for optimization)
DEFAULT_COOLDOWN_HOURS = 48
DEFAULT_LEVERAGE = 1.25
STARTING_CAPITAL = 10_000.0
DEFAULT_MIN_CONFIRMATIONS = 6
CONDITION_COLUMNS = [
    "rsi_ok",
    "momentum_ok",
    "volatility_ok",
    "volume_ok",
    "adx_ok",
    "price_above_ema50",
    "price_above_ema10",
    "macd_above_signal",
]
CONDITION_COLUMNS_BEAR = [
    "rsi_bear_ok",
    "momentum_bear_ok",
    "volatility_ok",
    "volume_ok",
    "adx_bear_ok",
    "price_below_ema50",
    "price_below_ema10",
    "macd_below_signal",
]


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    return_pct: float
    leveraged_return_pct: float
    side: str  # "long" | "short"


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[float]
    timestamps: List[str]
    current_signal: str  # "Long" | "Cash" | "Short"
    current_regime: str  # "Bull" | "Bear"
    bull_state_id: int
    bear_state_id: int
    total_return_pct: float
    buy_hold_return_pct: float
    alpha_pct: float
    win_rate: float
    max_drawdown_pct: float
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    states: List[int]
    vetoes_issued: int = 0
    veto_events: List[Dict[str, Any]] = field(default_factory=list)


def _build_veto_payload(
    t: pd.Timestamp,
    action: str,
    regime: str,
    votes: int,
    votes_bear: int,
    conditions: pd.DataFrame,
    conditions_bull_columns: List[str],
    conditions_bear_columns: List[str],
    i: int,
    indicator_values_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Build point-in-time payload for the veto agent (data only as of bar i)."""
    row = conditions.iloc[i]
    conditions_bull = {c: bool(row[c]) for c in conditions_bull_columns if c in row.index}
    conditions_bear = {c: bool(row[c]) for c in conditions_bear_columns if c in row.index}
    payload: Dict[str, Any] = {
        "as_of_timestamp": t.isoformat() if hasattr(t, "isoformat") else str(t),
        "action": action,
        "regime": regime,
        "votes": votes,
        "votes_bear": votes_bear,
        "conditions_bull": conditions_bull,
        "conditions_bear": conditions_bear,
    }
    if indicator_values_df is not None and i < len(indicator_values_df):
        iv = indicator_values_df.iloc[i]
        payload["indicator_values"] = {k: (float(iv[k]) if pd.notna(iv[k]) else None) for k in indicator_values_df.columns}
    return payload


def run_backtest(
    symbol: str = "BTC-USD",
    period: str = "730d",
    interval: str = "1h",
    n_components: int = 7,
    cooldown_hours: Optional[float] = None,
    leverage: Optional[float] = None,
    min_confirmations: Optional[int] = None,
    allow_short: bool = False,
    min_bear_confirmations: Optional[int] = None,
    df: Optional[pd.DataFrame] = None,
    bull_state_id: Optional[int] = None,
    bear_state_id: Optional[int] = None,
    use_agent_veto: bool = False,
    llm_client: Optional[Any] = None,
) -> BacktestResult:
    """
    Load data (or use provided df), compute indicators, run simulation, return result.

    Optional strategy params: cooldown_hours, leverage, min_confirmations, allow_short, min_bear_confirmations.
    When allow_short is True, min_bear_confirmations defaults to min_confirmations if None.
    When df and bull_state_id/bear_state_id are provided (e.g. for walk-forward), skip load_btc_hmm.
    When use_agent_veto is True and llm_client is provided, proposed entries/exits are sent to the
    veto agent; if the agent returns VETO, the action is skipped (point-in-time data only).
    """
    _cooldown_hours = cooldown_hours if cooldown_hours is not None else DEFAULT_COOLDOWN_HOURS
    _leverage = leverage if leverage is not None else DEFAULT_LEVERAGE
    _min_confirmations = min_confirmations if min_confirmations is not None else DEFAULT_MIN_CONFIRMATIONS
    _min_bear = min_bear_confirmations if min_bear_confirmations is not None else _min_confirmations

    if df is not None and bull_state_id is not None and bear_state_id is not None:
        pass
    else:
        df, bull_state_id, bear_state_id = load_btc_hmm(
            symbol=symbol,
            period=period,
            interval=interval,
            n_components=n_components,
        )

    conditions = compute_confirmation_conditions(df)
    # Align: conditions may have NaNs at the start; only consider bars where all conditions are valid
    confirmations = conditions[CONDITION_COLUMNS].fillna(False).astype(bool)
    vote_sum = confirmations.sum(axis=1)
    confirmations_bear = conditions[CONDITION_COLUMNS_BEAR].fillna(False).astype(bool)
    vote_sum_bear = confirmations_bear.sum(axis=1)

    indicator_values_df: Optional[pd.DataFrame] = None
    if use_agent_veto and llm_client is not None:
        indicator_values_df = compute_indicator_values(df)

    timestamps = df.index
    n = len(df)
    if n == 0:
        raise ValueError("No data after HMM preparation")

    equity = STARTING_CAPITAL
    equity_curve = [equity]
    position = 0  # 0 = flat, 1 = long, -1 = short
    entry_price: Optional[float] = None
    entry_time: Optional[pd.Timestamp] = None
    last_exit_time: Optional[pd.Timestamp] = None
    trades: List[Trade] = []
    vetoes_issued = 0
    veto_events: List[Dict[str, Any]] = []

    cooldown_seconds = _cooldown_hours * 3600

    for i in range(1, n):
        t = timestamps[i]
        state = int(df["State"].iloc[i])
        close = float(df["Close"].iloc[i])
        votes = int(vote_sum.iloc[i])
        votes_bear = int(vote_sum_bear.iloc[i])
        is_bull = state == bull_state_id
        is_bear = state == bear_state_id

        # Exit long: regime flip to bear -> close immediately
        if position == 1 and is_bear:
            if use_agent_veto and llm_client is not None:
                payload = _build_veto_payload(
                    t, "EXIT_LONG", "Bear", votes, votes_bear,
                    conditions, CONDITION_COLUMNS, CONDITION_COLUMNS_BEAR, i, indicator_values_df,
                )
                result, reason = ask_veto(payload, llm_client)
                if result == "VETO":
                    vetoes_issued += 1
                    veto_events.append({"timestamp": str(t), "action": "EXIT_LONG", "result": "VETO", "reason": reason})
                    equity_curve.append(equity)
                    continue
            exit_price = close
            raw_return = (exit_price - entry_price) / entry_price
            leveraged_return = raw_return * _leverage
            equity *= 1 + leveraged_return
            trades.append(
                Trade(
                    entry_time=entry_time.isoformat(),
                    exit_time=t.isoformat() if hasattr(t, "isoformat") else str(t),
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_pct=raw_return * 100,
                    leveraged_return_pct=leveraged_return * 100,
                    side="long",
                )
            )
            position = 0
            last_exit_time = t
            entry_price = None
            entry_time = None
            equity_curve.append(equity)
            continue

        # Exit short: regime flip to bull -> close short
        if position == -1 and is_bull:
            if use_agent_veto and llm_client is not None:
                payload = _build_veto_payload(
                    t, "EXIT_SHORT", "Bull", votes, votes_bear,
                    conditions, CONDITION_COLUMNS, CONDITION_COLUMNS_BEAR, i, indicator_values_df,
                )
                result, reason = ask_veto(payload, llm_client)
                if result == "VETO":
                    vetoes_issued += 1
                    veto_events.append({"timestamp": str(t), "action": "EXIT_SHORT", "result": "VETO", "reason": reason})
                    equity_curve.append(equity)
                    continue
            exit_price = close
            raw_return = (entry_price - exit_price) / entry_price  # short profit when price down
            leveraged_return = raw_return * _leverage
            equity *= 1 + leveraged_return
            trades.append(
                Trade(
                    entry_time=entry_time.isoformat(),
                    exit_time=t.isoformat() if hasattr(t, "isoformat") else str(t),
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_pct=raw_return * 100,
                    leveraged_return_pct=leveraged_return * 100,
                    side="short",
                )
            )
            position = 0
            last_exit_time = t
            entry_price = None
            entry_time = None
            equity_curve.append(equity)
            continue

        # Entry long: bull regime + min_confirmations/8 conditions + not in position + cooldown
        if position == 0 and is_bull and votes >= _min_confirmations:
            if last_exit_time is not None:
                delta = (t - last_exit_time).total_seconds()
                if delta < cooldown_seconds:
                    equity_curve.append(equity)
                    continue
            if use_agent_veto and llm_client is not None:
                payload = _build_veto_payload(
                    t, "ENTER_LONG", "Bull", votes, votes_bear,
                    conditions, CONDITION_COLUMNS, CONDITION_COLUMNS_BEAR, i, indicator_values_df,
                )
                result, reason = ask_veto(payload, llm_client)
                if result == "VETO":
                    vetoes_issued += 1
                    veto_events.append({"timestamp": str(t), "action": "ENTER_LONG", "result": "VETO", "reason": reason})
                    equity_curve.append(equity)
                    continue
            position = 1
            entry_price = close
            entry_time = t

        # Entry short: bear regime + bear confirmations + allow_short + cooldown
        if allow_short and position == 0 and is_bear and votes_bear >= _min_bear:
            if last_exit_time is not None:
                delta = (t - last_exit_time).total_seconds()
                if delta < cooldown_seconds:
                    equity_curve.append(equity)
                    continue
            if use_agent_veto and llm_client is not None:
                payload = _build_veto_payload(
                    t, "ENTER_SHORT", "Bear", votes, votes_bear,
                    conditions, CONDITION_COLUMNS, CONDITION_COLUMNS_BEAR, i, indicator_values_df,
                )
                result, reason = ask_veto(payload, llm_client)
                if result == "VETO":
                    vetoes_issued += 1
                    veto_events.append({"timestamp": str(t), "action": "ENTER_SHORT", "result": "VETO", "reason": reason})
                    equity_curve.append(equity)
                    continue
            position = -1
            entry_price = close
            entry_time = t

        equity_curve.append(equity)

    # If still in long at end, mark-to-market (close at last close)
    if position == 1 and entry_price is not None and entry_time is not None:
        exit_price = float(df["Close"].iloc[-1])
        raw_return = (exit_price - entry_price) / entry_price
        leveraged_return = raw_return * _leverage
        equity *= 1 + leveraged_return
        trades.append(
            Trade(
                entry_time=entry_time.isoformat(),
                exit_time=timestamps[-1].isoformat() if hasattr(timestamps[-1], "isoformat") else str(timestamps[-1]),
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=raw_return * 100,
                leveraged_return_pct=leveraged_return * 100,
                side="long",
            )
        )
        equity_curve[-1] = equity  # keep same length as timestamps

    # If still in short at end, mark-to-market
    if position == -1 and entry_price is not None and entry_time is not None:
        exit_price = float(df["Close"].iloc[-1])
        raw_return = (entry_price - exit_price) / entry_price
        leveraged_return = raw_return * _leverage
        equity *= 1 + leveraged_return
        trades.append(
            Trade(
                entry_time=entry_time.isoformat(),
                exit_time=timestamps[-1].isoformat() if hasattr(timestamps[-1], "isoformat") else str(timestamps[-1]),
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=raw_return * 100,
                leveraged_return_pct=leveraged_return * 100,
                side="short",
            )
        )
        equity_curve[-1] = equity

    # Metrics
    total_return_pct = (equity / STARTING_CAPITAL - 1) * 100
    first_close = float(df["Close"].iloc[0])
    last_close = float(df["Close"].iloc[-1])
    buy_hold_return_pct = (last_close / first_close - 1) * 100
    alpha_pct = total_return_pct - buy_hold_return_pct

    wins = sum(1 for tr in trades if tr.leveraged_return_pct > 0)
    win_rate = (wins / len(trades) * 100) if trades else 0.0

    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = max_dd

    last_state = int(df["State"].iloc[-1])
    current_regime = "Bull" if last_state == bull_state_id else "Bear"
    if position == 1:
        current_signal = "Long"
    elif position == -1:
        current_signal = "Short"
    else:
        current_signal = "Cash"

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        timestamps=[t.isoformat() if hasattr(t, "isoformat") else str(t) for t in timestamps],
        current_signal=current_signal,
        current_regime=current_regime,
        bull_state_id=bull_state_id,
        bear_state_id=bear_state_id,
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        alpha_pct=alpha_pct,
        win_rate=win_rate,
        max_drawdown_pct=max_drawdown_pct,
        open=df["Open"].tolist(),
        high=df["High"].tolist(),
        low=df["Low"].tolist(),
        close=df["Close"].tolist(),
        states=df["State"].astype(int).tolist(),
        vetoes_issued=vetoes_issued,
        veto_events=veto_events,
    )
