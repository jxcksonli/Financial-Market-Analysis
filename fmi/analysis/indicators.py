"""
Technical indicators from OHLCV DataFrames (pure pandas).
"""

from __future__ import annotations

import math

import pandas as pd


def _tolist(series: pd.Series | None) -> list[float | None]:
    if series is None:
        return []
    out: list[float | None] = []
    for v in series:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out.append(None)
        else:
            out.append(float(v))
    return out


def _sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger(close: pd.Series, length: int = 20, std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = _sma(close, length)
    dev = close.rolling(window=length, min_periods=length).std()
    upper = mid + std * dev
    lower = mid - std * dev
    return lower, mid, upper


def compute_indicators(df: pd.DataFrame) -> dict[str, list[float | None]]:
    """Return indicator series aligned 1:1 with ``df`` rows."""
    empty: dict[str, list[float | None]] = {
        "sma50": [],
        "sma200": [],
        "bb_lower": [],
        "bb_mid": [],
        "bb_upper": [],
        "rsi": [],
        "macd": [],
        "macd_signal": [],
        "macd_hist": [],
    }
    if df is None or df.empty:
        return empty

    close = df["Close"]
    bb_lower, bb_mid, bb_upper = _bollinger(close, length=20, std=2.0)
    macd_line, macd_signal, macd_hist = _macd(close, fast=12, slow=26, signal=9)

    return {
        "sma50": _tolist(_sma(close, 50)),
        "sma200": _tolist(_sma(close, 200)),
        "bb_lower": _tolist(bb_lower),
        "bb_mid": _tolist(bb_mid),
        "bb_upper": _tolist(bb_upper),
        "rsi": _tolist(_rsi(close, 14)),
        "macd": _tolist(macd_line),
        "macd_signal": _tolist(macd_signal),
        "macd_hist": _tolist(macd_hist),
    }
