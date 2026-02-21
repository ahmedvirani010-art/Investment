"""
Integrated HMM regime + spread analysis for the 7 assets:
Bitcoin, Gold, Crude Oil, Silver, NASDAQ, NIKKEI, S&P 500.

Step 1: Run HMM for each asset; persist to price_data/hmm_regimes.db.
Step 2: Run spread/cointegration on selected pairs; persist to price_data/spread_analysis.db.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from psx_hmm_regime import fit_and_predict, regime_sync, result_to_dict
from psx_spread_analyzer import spread_analysis_pair

# Default 7 assets: symbol -> label
DEFAULT_ASSETS: Dict[str, str] = {
    "BTC-USD": "Bitcoin",
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "SI=F": "Silver",
    "^IXIC": "NASDAQ",
    "^N225": "NIKKEI",
    "^GSPC": "S&P 500",
}

# Pairs to run spread analysis on (from the 7 assets)
DEFAULT_PAIRS: List[tuple] = [
    ("GC=F", "SI=F"),
    ("^IXIC", "^GSPC"),
    ("BTC-USD", "GC=F"),
]

PRICE_DATA_DIR = "price_data"
HMM_DB = os.path.join(PRICE_DATA_DIR, "hmm_regimes.db")
SPREAD_DB = os.path.join(PRICE_DATA_DIR, "spread_analysis.db")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def init_hmm_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_models (
                model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trained_at TEXT NOT NULL,
                n_components INTEGER NOT NULL,
                aic REAL,
                bic REAL,
                transition_matrix_json TEXT,
                feature_names TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                as_of_date TEXT NOT NULL,
                state INTEGER NOT NULL,
                mean_return REAL,
                volatility REAL,
                days_in_current_regime INTEGER,
                confidence REAL,
                model_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES regime_models(model_id)
            )
        """)
        try:
            conn.execute("ALTER TABLE regime_snapshots ADD COLUMN confidence REAL")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.commit()


def init_spread_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cointegration_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id TEXT NOT NULL,
                asset1 TEXT NOT NULL,
                asset2 TEXT NOT NULL,
                test_type TEXT NOT NULL,
                p_value REAL,
                half_life_days REAL,
                hedge_ratio_type TEXT,
                hedge_ratio_static REAL,
                cointegrated INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spread_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id TEXT NOT NULL,
                signal_date TEXT NOT NULL,
                zscore REAL NOT NULL,
                signal_type TEXT NOT NULL,
                regime_state INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def write_hmm_result(conn: sqlite3.Connection, result: Any, model_id: int) -> None:
    """Write one HMM result to regime_snapshots; regime_models already written by caller."""
    as_of = result.timestamps[-1] if result.timestamps else datetime.now(timezone.utc).isoformat()
    summary = result.summary
    last_state = result.last_state
    mean_ret = next((s.mean_return for s in summary if s.state == last_state), None)
    vol = next((s.volatility for s in summary if s.state == last_state), None)
    days = result.days_in_current_regime or 0
    confidence = getattr(result, "last_confidence", None)
    conn.execute(
        """INSERT INTO regime_snapshots (symbol, as_of_date, state, mean_return, volatility, days_in_current_regime, confidence, model_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (result.symbol, as_of, last_state, mean_ret, vol, days, confidence, model_id),
    )


def run_hmm_step(assets: Dict[str, str], period: str, interval: str) -> List[Any]:
    """Run HMM for each asset; persist to hmm_regimes.db. Returns list of HMMRegimeResult."""
    ensure_dir(PRICE_DATA_DIR)
    init_hmm_db(HMM_DB)
    results: List[Any] = []
    trained_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(HMM_DB) as conn:
        for symbol, label in assets.items():
            try:
                result = fit_and_predict(
                    symbol=symbol,
                    period=period,
                    interval=interval,
                    n_components=7,
                )
                results.append(result)
                transmat_json = json.dumps(result.transition_matrix) if result.transition_matrix else None
                conn.execute(
                    """INSERT INTO regime_models (symbol, trained_at, n_components, aic, bic, transition_matrix_json, feature_names)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol,
                        trained_at,
                        result.n_components,
                        result.aic,
                        result.bic,
                        transmat_json,
                        "LOG_RETURNS,REALIZED_VOL_20D,RSI_NORM,VOLUME_RATIO_20D,MOMENTUM_20D",
                    ),
                )
                model_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                write_hmm_result(conn, result, model_id)
                print(f"  HMM {symbol} ({label}): state={result.last_state}, days_in_regime={result.days_in_current_regime}")
            except Exception as e:
                print(f"  HMM {symbol} failed: {e}", file=sys.stderr)
        conn.commit()
    return results


def run_spread_step(
    pairs: List[tuple],
    period: str,
    hmm_results: Optional[List[Any]] = None,
) -> List[Any]:
    """Run spread analysis for each pair; persist to spread_analysis.db."""
    ensure_dir(PRICE_DATA_DIR)
    init_spread_db(SPREAD_DB)
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance required for spread step", file=sys.stderr)
        return []
    results: List[Any] = []
    with sqlite3.connect(SPREAD_DB) as conn:
        for s1, s2 in pairs:
            try:
                p1 = yf.download(s1, period=period, interval="1d", progress=False, threads=False)["Close"]
                p2 = yf.download(s2, period=period, interval="1d", progress=False, threads=False)["Close"]
                if isinstance(p1, pd.DataFrame):
                    p1 = p1.iloc[:, 0]
                if isinstance(p2, pd.DataFrame):
                    p2 = p2.iloc[:, 0]
                result = spread_analysis_pair(p1, p2, s1, s2, use_kalman=True)
                results.append(result)
                c = result.coint_result
                conn.execute(
                    """INSERT INTO cointegration_tests (pair_id, asset1, asset2, test_type, p_value, half_life_days, hedge_ratio_type, hedge_ratio_static, cointegrated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.pair_id,
                        result.asset1,
                        result.asset2,
                        c.test_type,
                        c.p_value,
                        result.half_life_days,
                        c.hedge_ratio_type,
                        c.hedge_ratio,
                        1 if c.cointegrated else 0,
                    ),
                )
                for sig in result.signals[:200]:
                    conn.execute(
                        """INSERT INTO spread_signals (pair_id, signal_date, zscore, signal_type, regime_state)
                           VALUES (?, ?, ?, ?, ?)""",
                        (result.pair_id, sig.date, sig.zscore, sig.signal_type, sig.regime_state),
                    )
                print(f"  Spread {s1}/{s2}: cointegrated={result.coint_result.cointegrated}, p={c.p_value:.4f}, half_life={result.half_life_days}")
            except Exception as e:
                print(f"  Spread {s1}/{s2} failed: {e}", file=sys.stderr)
        conn.commit()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Integrated HMM + spread analysis for 7 assets")
    parser.add_argument(
        "--assets",
        default=",".join(DEFAULT_ASSETS.keys()),
        help="Comma-separated symbols (default: BTC-USD,GC=F,CL=F,SI=F,^IXIC,^N225,^GSPC)",
    )
    parser.add_argument("--period", default="730d", help="yfinance period")
    parser.add_argument("--interval", default="1d", help="yfinance interval")
    parser.add_argument("--no-spread", action="store_true", help="Skip spread step")
    args = parser.parse_args()

    assets_list = [s.strip() for s in args.assets.split(",") if s.strip()]
    assets = {s: DEFAULT_ASSETS.get(s, s) for s in assets_list}
    if not assets:
        assets = DEFAULT_ASSETS

    print("Step 1: HMM regime detection")
    hmm_results = run_hmm_step(assets, args.period, args.interval)
    if hmm_results:
        sync = regime_sync(hmm_results)
        print(f"  Regime sync: aligned={sync['aligned']}, last_states={sync['last_states']}")

    if not args.no_spread:
        print("Step 2: Spread / cointegration")
        pairs = DEFAULT_PAIRS
        run_spread_step(pairs, args.period, hmm_results if hmm_results else None)

    print(f"Done. DBs: {HMM_DB}, {SPREAD_DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
