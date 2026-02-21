"""
Multivariate multi-asset backtester: one position at a time, best asset by score.
Asset-agnostic: works with any list of aligned assets.
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from backtest_indicators import compute_confirmation_conditions
from multivariate_loader import AlignedAsset

COOLDOWN_BARS = 2
LEVERAGE = 1.25
STARTING_CAPITAL = 10_000.0
MIN_CONFIRMATIONS = 6
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


@dataclass
class MultivariateTrade:
    asset: str  # symbol
    label: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    return_pct: float
    leveraged_return_pct: float


@dataclass
class MultivariateBacktestResult:
    trades: List[MultivariateTrade]
    equity_curve: List[float]
    timestamps: List[str]
    current_signal: str  # "Cash" | "Long"
    current_asset: Optional[str]  # symbol when Long, else None
    current_asset_label: Optional[str]
    assets: List[dict]  # [{"symbol", "label"}, ...]
    total_return_pct: float
    buy_hold_return_pct: float
    alpha_pct: float
    win_rate: float
    max_drawdown_pct: float


def _score(is_bull: bool, votes: int) -> int:
    """Higher is better. Bull + 8 votes beats bear + 8."""
    return (10 if is_bull else 0) + votes


def run_multivariate_backtest(
    aligned_assets: List[AlignedAsset],
    cooldown_bars: int = COOLDOWN_BARS,
    min_confirmations: int = MIN_CONFIRMATIONS,
    leverage: float = LEVERAGE,
) -> MultivariateBacktestResult:
    """
    Run backtest: at each bar score all assets, hold at most one long; rotate or enter when best asset meets entry.
    """
    if not aligned_assets:
        raise ValueError("aligned_assets is empty")
    n_bars = len(aligned_assets[0].df)
    for a in aligned_assets:
        if len(a.df) != n_bars:
            raise ValueError(f"Asset {a.symbol} has {len(a.df)} bars, expected {n_bars}")
    timestamps = aligned_assets[0].df.index
    symbol_to_asset = {a.symbol: a for a in aligned_assets}
    symbol_to_label = {a.symbol: a.label for a in aligned_assets}

    # Precompute conditions and vote sum per asset
    conditions_per_asset: dict[str, pd.Series] = {}
    for a in aligned_assets:
        cond = compute_confirmation_conditions(a.df)
        confirmations = cond[CONDITION_COLUMNS].fillna(False).astype(bool)
        conditions_per_asset[a.symbol] = confirmations.sum(axis=1)

    equity = STARTING_CAPITAL
    equity_curve = [equity]
    position: Optional[str] = None  # symbol when long
    entry_price: Optional[float] = None
    entry_time: Optional[pd.Timestamp] = None
    entry_bar: Optional[int] = None
    last_exit_bar: Optional[int] = None
    trades: List[MultivariateTrade] = []

    def _get_state_votes_score(i: int, sym: str) -> tuple[int, int, bool, bool, int]:
        a = symbol_to_asset[sym]
        state = int(a.df["State"].iloc[i])
        votes = int(conditions_per_asset[sym].iloc[i])
        is_bull = state == a.bull_state_id
        is_bear = state == a.bear_state_id
        score = _score(is_bull, votes)
        return state, votes, is_bull, is_bear, score

    def _rank_assets(i: int) -> List[tuple[str, int, bool, int]]:
        # (symbol, score, is_bull, votes) sorted by score desc, then symbol asc
        rows = []
        for a in aligned_assets:
            _, votes, is_bull, _, score = _get_state_votes_score(i, a.symbol)
            rows.append((a.symbol, score, is_bull, votes))
        rows.sort(key=lambda x: (-x[1], x[0]))
        return rows

    for i in range(1, n_bars):
        t = timestamps[i]
        ranked = _rank_assets(i)
        best_symbol = ranked[0][0]
        best_score = ranked[0][1]
        best_bull = ranked[0][2]
        best_votes = ranked[0][3]

        if position is not None:
            a = symbol_to_asset[position]
            _, votes_a, is_bull_a, is_bear_a, score_a = _get_state_votes_score(i, position)
            close_a = float(a.df["Close"].iloc[i])

            # Exit if our asset turned bear (equity updates only on trade close)
            if is_bear_a:
                exit_price = close_a
                raw_return = (exit_price - entry_price) / entry_price if entry_price else 0.0
                leveraged_return = raw_return * leverage
                equity *= 1 + leveraged_return
                trades.append(
                    MultivariateTrade(
                        asset=position,
                        label=symbol_to_label[position],
                        entry_time=entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
                        exit_time=t.isoformat() if hasattr(t, "isoformat") else str(t),
                        entry_price=entry_price,
                        exit_price=exit_price,
                        return_pct=raw_return * 100,
                        leveraged_return_pct=leveraged_return * 100,
                    )
                )
                position = None
                entry_price = None
                entry_time = None
                entry_bar = None
                last_exit_bar = i
                equity_curve.append(equity)
                continue

            # Rotation: another asset has higher score and meets entry
            for sym, score, is_bull, votes in ranked:
                if sym == position:
                    continue
                if score > score_a and is_bull and votes >= min_confirmations:
                    # Rotate: close A (update equity), enter sym
                    exit_price = close_a
                    raw_return = (exit_price - entry_price) / entry_price if entry_price else 0.0
                    leveraged_return = raw_return * leverage
                    equity *= 1 + leveraged_return
                    trades.append(
                        MultivariateTrade(
                            asset=position,
                            label=symbol_to_label[position],
                            entry_time=entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
                            exit_time=t.isoformat() if hasattr(t, "isoformat") else str(t),
                            entry_price=entry_price,
                            exit_price=exit_price,
                            return_pct=raw_return * 100,
                            leveraged_return_pct=leveraged_return * 100,
                        )
                    )
                    position = sym
                    entry_price = float(symbol_to_asset[sym].df["Close"].iloc[i])
                    entry_time = t
                    entry_bar = i
                    break
            equity_curve.append(equity)
            continue

        # Cash: check cooldown then entry
        if last_exit_bar is not None and (i - last_exit_bar) <= cooldown_bars:
            equity_curve.append(equity)
            continue
        if best_bull and best_votes >= min_confirmations:
            position = best_symbol
            entry_price = float(symbol_to_asset[best_symbol].df["Close"].iloc[i])
            entry_time = t
            entry_bar = i
        equity_curve.append(equity)

    # Mark-to-market if still in position
    if position is not None and entry_price is not None and entry_time is not None:
        a = symbol_to_asset[position]
        exit_price = float(a.df["Close"].iloc[-1])
        raw_return = (exit_price - entry_price) / entry_price
        leveraged_return = raw_return * leverage
        equity *= 1 + leveraged_return
        trades.append(
            MultivariateTrade(
                asset=position,
                label=symbol_to_label[position],
                entry_time=entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
                exit_time=timestamps[-1].isoformat() if hasattr(timestamps[-1], "isoformat") else str(timestamps[-1]),
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=raw_return * 100,
                leveraged_return_pct=leveraged_return * 100,
            )
        )
        equity_curve[-1] = equity

    # Metrics
    total_return_pct = (equity / STARTING_CAPITAL - 1) * 100
    buy_hold_returns = []
    for a in aligned_assets:
        first_close = float(a.df["Close"].iloc[0])
        last_close = float(a.df["Close"].iloc[-1])
        buy_hold_returns.append((last_close / first_close - 1) * 100)
    buy_hold_return_pct = sum(buy_hold_returns) / len(buy_hold_returns) if buy_hold_returns else 0.0
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

    return MultivariateBacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        timestamps=[t.isoformat() if hasattr(t, "isoformat") else str(t) for t in timestamps],
        current_signal="Long" if position else "Cash",
        current_asset=position,
        current_asset_label=symbol_to_label.get(position) if position else None,
        assets=[{"symbol": a.symbol, "label": a.label} for a in aligned_assets],
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        alpha_pct=alpha_pct,
        win_rate=win_rate,
        max_drawdown_pct=max_dd,
    )
