"""
Asset configuration for the multivariate multi-asset trading system.
Single source of truth: add or remove assets here; no core logic changes needed.
"""

from typing import List, TypedDict


class AssetEntry(TypedDict):
    symbol: str
    label: str


# Single source of truth for all assets in the multivariate HMM regime analysis.
# Add or remove entries here; no changes needed in multivariate_loader or backtester.
DEFAULT_ASSETS: List[AssetEntry] = [
    {"symbol": "BTC-USD", "label": "BTC"},
    {"symbol": "GC=F", "label": "GOLD"},
    {"symbol": "SI=F", "label": "SILVER"},
    {"symbol": "CL=F", "label": "CRUDE"},
    {"symbol": "^IXIC", "label": "NASDAQ"},
    {"symbol": "^N225", "label": "NIKKEI"},
]


def get_assets(override_symbols: str | None = None) -> List[AssetEntry]:
    """
    Return the list of assets to use. If override_symbols is provided (e.g. "BTC-USD,GC=F"),
    return entries for those symbols using symbol as label when not in DEFAULT_ASSETS.
    """
    if not override_symbols or not override_symbols.strip():
        return list(DEFAULT_ASSETS)
    symbols = [s.strip() for s in override_symbols.split(",") if s.strip()]
    by_symbol = {a["symbol"]: a for a in DEFAULT_ASSETS}
    out = []
    for sym in symbols:
        if sym in by_symbol:
            out.append(by_symbol[sym])
        else:
            out.append({"symbol": sym, "label": sym})
    return out
