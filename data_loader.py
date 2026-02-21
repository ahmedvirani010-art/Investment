"""
Data loader for HMM Regime backtesting.
Fetches OHLCV (e.g. BTC-USD hourly), prepares features, fits HMM, and returns
aligned DataFrame with State plus bull/bear state IDs.
"""

from typing import Tuple

import pandas as pd

from psx_hmm_regime import fit_and_predict, get_data, prepare_features


def load_btc_hmm(
    symbol: str = "BTC-USD",
    period: str = "730d",
    interval: str = "1h",
    n_components: int = 7,
) -> Tuple[pd.DataFrame, int, int]:
    """
    Load OHLCV data, prepare features, fit HMM, and return aligned data with regime states.

    Returns:
        df: DataFrame with Open, High, Low, Close, Volume, Returns, State (same index as bars).
        bull_state_id: HMM state id with highest mean return (Bull Run).
        bear_state_id: HMM state id with lowest mean return (Bear/Crash).
    """
    df = get_data(symbol, period=period, interval=interval)
    df = prepare_features(df)

    result = fit_and_predict(
        symbol=symbol,
        period=period,
        interval=interval,
        n_components=n_components,
    )

    if len(df) != len(result.states):
        raise ValueError(
            f"Length mismatch: data has {len(df)} rows, HMM returned {len(result.states)} states"
        )

    df = df.assign(State=result.states)
    bull_state_id = result.summary[0].state
    bear_state_id = result.summary[-1].state

    return df, bull_state_id, bear_state_id
