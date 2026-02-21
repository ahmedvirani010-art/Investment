"""
Vectorized technical indicators for HMM Regime backtesting.
Produces per-bar series for the 8 confirmation conditions.
"""

import pandas as pd
import numpy as np


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (EMA with alpha = 1/period)."""
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def compute_rsi_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI series (0-100). Same formula as psx_technical_agent."""
    delta = df["Close"].diff()
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    avg_gains = gains.rolling(window=period, min_periods=period).mean()
    avg_losses = losses.rolling(window=period, min_periods=period).mean()
    rs = avg_gains / avg_losses.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd_series(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram. Same formula as psx_technical_agent."""
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_adx_series(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """ADX and directional indicators. Returns (adx, plus_di, minus_di)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_di = 100 * _wilder_smooth(plus_dm, period) / atr.replace(0, np.nan)
    minus_di = 100 * _wilder_smooth(minus_dm, period) / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = _wilder_smooth(dx, period)
    return adx, plus_di, minus_di


def compute_confirmation_conditions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all 8 confirmation condition series for the backtester.

    Returns DataFrame with same index as df and columns (all boolean where applicable):
      - rsi_ok: RSI < 90
      - momentum_ok: Momentum > 1% (20-bar)
      - volatility_ok: Rolling 20-bar std of returns < 6%
      - volume_ok: Volume > SMA(Volume, 20)
      - adx_ok: ADX > 25
      - price_above_ema50: Close > EMA(Close, 50)
      - price_above_ema10: Close > EMA(Close, 10)
      - macd_above_signal: MACD line > Signal line
    """
    out = pd.DataFrame(index=df.index)

    # 1. RSI < 90
    rsi = compute_rsi_series(df, period=14)
    out["rsi_ok"] = rsi < 90

    # 2. Momentum > 1% (e.g. 20-bar)
    momentum_period = 20
    momentum_pct = (df["Close"] - df["Close"].shift(momentum_period)) / df["Close"].shift(momentum_period).replace(0, np.nan)
    out["momentum_ok"] = momentum_pct > 0.01

    # 3. Volatility < 6% (20-period rolling std of returns)
    vol_period = 20
    returns = df["Close"].pct_change()
    rolling_vol = returns.rolling(vol_period, min_periods=vol_period).std()
    out["volatility_ok"] = rolling_vol < 0.06

    # 4. Volume > SMA(Volume, 20)
    vol_sma20 = df["Volume"].rolling(20, min_periods=20).mean()
    out["volume_ok"] = df["Volume"] > vol_sma20

    # 5. ADX signal: ADX > 25
    adx, plus_di, minus_di = compute_adx_series(df, period=14)
    out["adx_ok"] = adx > 25

    # 6. Price > EMA 50
    ema50 = df["Close"].ewm(span=50, adjust=False).mean()
    out["price_above_ema50"] = df["Close"] > ema50

    # 7. Price > EMA 10 (10-day moving average)
    ema10 = df["Close"].ewm(span=10, adjust=False).mean()
    out["price_above_ema10"] = df["Close"] > ema10

    # 8. MACD > Signal line
    macd_line, signal_line, _ = compute_macd_series(df)
    out["macd_above_signal"] = macd_line > signal_line

    # --- Bear confirmation conditions (for short entry) ---
    # 1. RSI > 30 (bearish bias, avoid extreme oversold)
    out["rsi_bear_ok"] = rsi > 30
    # 2. 20-bar momentum < -1%
    out["momentum_bear_ok"] = momentum_pct < -0.01
    # 3. volatility_ok same as long
    # 4. volume_ok same as long
    # 5. ADX bear signal: ADX > 25 and -DI > +DI
    out["adx_bear_ok"] = (adx > 25) & (minus_di > plus_di)
    # 6. Price < EMA 50
    out["price_below_ema50"] = df["Close"] < ema50
    # 7. Price < EMA 10
    out["price_below_ema10"] = df["Close"] < ema10
    # 8. MACD < Signal line
    out["macd_below_signal"] = macd_line < signal_line

    return out


def compute_indicator_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute raw indicator values per bar for veto agent context (point-in-time safe).
    Same index as df; use .iloc[i] for bar i only.

    Returns DataFrame with columns: rsi, macd_line, macd_signal, adx, plus_di, minus_di,
    ema10, ema50, close.
    """
    rsi = compute_rsi_series(df, period=14)
    macd_line, signal_line, _ = compute_macd_series(df)
    adx, plus_di, minus_di = compute_adx_series(df, period=14)
    ema10 = df["Close"].ewm(span=10, adjust=False).mean()
    ema50 = df["Close"].ewm(span=50, adjust=False).mean()
    out = pd.DataFrame(
        {
            "rsi": rsi,
            "macd_line": macd_line,
            "macd_signal": signal_line,
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "ema10": ema10,
            "ema50": ema50,
            "close": df["Close"],
        },
        index=df.index,
    )
    return out
