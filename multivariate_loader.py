"""
Load and align N assets by date for the multivariate backtester.
Uses the same HMM pipeline (psx_hmm_regime) for every symbol so adding new assets requires no code change.
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

from psx_hmm_regime import fit_and_predict, get_data, prepare_features


@dataclass
class AlignedAsset:
    symbol: str
    label: str
    df: pd.DataFrame  # aligned to common index; has Open, High, Low, Close, Volume, Returns, State
    bull_state_id: int
    bear_state_id: int


def load_and_align_assets(
    assets: List[dict],
    period: str = "730d",
    interval: str = "1d",
    n_components: int = 7,
) -> List[AlignedAsset]:
    """
    Load OHLCV + HMM states for each asset, then align all to the inner join of dates.

    assets: list of {"symbol": str, "label": str}
    Returns list of AlignedAsset with aligned DataFrames (same index for all).
    """
    if not assets:
        raise ValueError("assets list is empty")

    raw_list: List[AlignedAsset] = []
    for entry in assets:
        symbol = entry["symbol"]
        label = entry.get("label", symbol)
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
                f"Length mismatch for {symbol}: data {len(df)} rows, HMM {len(result.states)} states"
            )
        df = df.assign(State=result.states)
        bull_state_id = result.summary[0].state
        bear_state_id = result.summary[-1].state
        raw_list.append(
            AlignedAsset(
                symbol=symbol,
                label=label,
                df=df,
                bull_state_id=bull_state_id,
                bear_state_id=bear_state_id,
            )
        )

    # Align: inner join on date index
    common_index = raw_list[0].df.index
    for a in raw_list[1:]:
        common_index = common_index.intersection(a.df.index)
    if len(common_index) == 0:
        raise ValueError("No common dates across assets after inner join")

    aligned: List[AlignedAsset] = []
    for a in raw_list:
        df_aligned = a.df.loc[common_index].copy()
        aligned.append(
            AlignedAsset(
                symbol=a.symbol,
                label=a.label,
                df=df_aligned,
                bull_state_id=a.bull_state_id,
                bear_state_id=a.bear_state_id,
            )
        )
    return aligned
