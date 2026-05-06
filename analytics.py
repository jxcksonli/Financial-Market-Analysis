"""
Data analytics for Financial Market Insights.

Put your pandas / yfinance (and any other) analysis here. Functions below are wired
into the ticker page — replace the template bodies with real computations.

Suggested workflow:
  - Fetch OHLCV with yfinance or your own loaders into a pandas DataFrame.
  - Compute indicators, returns, volatility, etc.
  - Return JSON-serializable dicts / lists for `graph_series` and `analysis_sections`.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from typing import Any

import pandas as pd
import yfinance as yf

_GDELT_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "—"
    try:
        if math.isnan(float(x)):
            return "—"
    except Exception:
        return "—"
    return f"{x:+.2f}%"


def _fmt_money(x: float | None) -> str:
    if x is None:
        return "—"
    try:
        if math.isnan(float(x)):
            return "—"
    except Exception:
        return "—"
    return f"{float(x):,.2f}"


def _fmt_market_cap(x: float | None) -> str:
    if x is None:
        return "—"
    try:
        n = float(x)
    except Exception:
        return "—"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:,.2f}{unit}"
    return f"{n:,.0f}"


def _load_price_df(symbol: str, period: str = "6mo") -> pd.DataFrame:
    df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    df = pd.DataFrame(df)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df = df[keep].dropna(how="all")
    if "Close" in df.columns:
        df = df.dropna(subset=["Close"])
    return df


def _gdelt_fetch(query: str, *, timespan: str, mode: str) -> dict[str, Any] | None:
    """
    Best-effort fetch from GDELT DOC API (free, no key).
    Returns parsed JSON or None if throttled/unavailable.
    """
    q = (query or "").strip()
    if not q:
        return None

    cache_key = (mode, f"{timespan}|{q}")
    now = time.time()
    cached = _GDELT_CACHE.get(cache_key)
    if cached and now - cached[0] < 30 * 60:
        return cached[1]

    params = {
        "query": q,
        "mode": mode,
        "format": "json",
        "timespan": timespan,
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FinancialMarketInsights/1.0 (gdelt sentiment; no-auth; educational)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        obj = json.loads(raw)
    except Exception:
        return None

    if isinstance(obj, dict):
        _GDELT_CACHE[cache_key] = (now, obj)
        return obj
    return None


def _gdelt_avg_tone(query: str, *, timespan: str = "7d") -> float | None:
    """
    Uses GDELT's built-in tone scoring via TimelineTone.
    Returns average tone over returned timesteps (not volume-weighted).
    """
    obj = _gdelt_fetch(query, timespan=timespan, mode="timelineTone")
    if not obj:
        return None
    tl = obj.get("timeline")
    if not isinstance(tl, list) or not tl:
        return None

    tones: list[float] = []
    for row in tl:
        if not isinstance(row, dict):
            continue
        t = row.get("tone")
        if t is None:
            t = row.get("value")
        try:
            tones.append(float(t))
        except Exception:
            continue

    if not tones:
        return None
    return sum(tones) / float(len(tones))


def get_template_chart_series(symbol: str, market: str) -> list[dict[str, Any]]:
    """
    Series used in the **template chart** on the ticker page.

    Replace this with real data, for example:
        df = yf.Ticker(symbol).history(period="6mo")
        return [
            {"date": ix.strftime("%Y-%m-%d"), "close": float(row["Close"])}
            for ix, row in df.iterrows()
        ]
    """
    df = _load_price_df(symbol, period="6mo")
    if df.empty or "Close" not in df.columns:
        return []
    idx = df.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    return [
        {"date": d.strftime("%Y-%m-%d"), "close": float(c)}
        for d, c in zip(idx, df["Close"].astype(float).tolist())
    ]


def get_analysis_sections(symbol: str, market: str) -> list[dict[str, Any]]:
    """
    Blocks rendered under "Analysis" on the ticker page.

    Return a list of dicts with keys: title, body (plain text or short HTML-safe string).
    Optional: metric_label, metric_value for a small stat chip in the card.

    Replace template strings with outputs from your analytics (e.g. volatility, beta).
    """
    df = _load_price_df(symbol, period="6mo")
    info: dict[str, Any] = {}
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info = {}

    if df.empty or "Close" not in df.columns:
        return [
            {
                "title": "Price action",
                "body": "Not enough price history to compute metrics for this symbol right now.",
                "metric_label": "Status",
                "metric_value": "No data",
            }
        ]

    close = df["Close"].astype(float)
    last = float(close.iloc[-1])

    def _ret(lookback_days: int) -> float | None:
        if len(close) <= lookback_days:
            return None
        prev = float(close.iloc[-(lookback_days + 1)])
        if prev == 0:
            return None
        return (last / prev - 1.0) * 100.0

    r_5 = _ret(5)
    r_21 = _ret(21)
    r_63 = _ret(63)

    returns = close.pct_change().dropna()
    lookback = min(60, int(returns.shape[0]))
    recent = returns.tail(lookback) if lookback > 0 else returns
    daily_mu = float(recent.mean()) if not recent.empty else 0.0
    daily_sigma = float(recent.std(ddof=1)) if recent.shape[0] > 1 else 0.0

    horizon_days = 20
    exp_move = daily_sigma * math.sqrt(horizon_days) * 100.0
    drift = daily_mu * horizon_days * 100.0

    trajectory_line = (
        f"Based on several mathematical calculations, the trajectory of {symbol} is ± {exp_move:.2f}%"
    )

    trend_signal = "Neutral"
    if r_21 is not None:
        if r_21 > 2.0:
            trend_signal = "Bullish"
        elif r_21 < -2.0:
            trend_signal = "Bearish"

    pe = info.get("trailingPE") or info.get("forwardPE")
    mcap = info.get("marketCap")
    div_yield = info.get("dividendYield")
    sector = info.get("sector") or info.get("industry")

    fundamentals_bits: list[str] = []
    fundamentals_bits.append(f"Market cap: {_fmt_market_cap(mcap)}")
    if pe is not None:
        try:
            fundamentals_bits.append(f"P/E: {float(pe):.2f}")
        except Exception:
            pass
    if div_yield is not None:
        try:
            fundamentals_bits.append(f"Dividend yield: {float(div_yield) * 100.0:.2f}%")
        except Exception:
            pass
    if sector:
        fundamentals_bits.append(f"Sector: {sector}")

    price_action_body = (
        f"Last close: {_fmt_money(last)}. "
        f"5D: {_fmt_pct(r_5)} · 1M: {_fmt_pct(r_21)} · 3M: {_fmt_pct(r_63)}"
    )

    quant_body = (
        f"{trajectory_line}. "
        f"Expected drift (mean return): {_fmt_pct(drift)} over ~{horizon_days} trading days. "
        f"Volatility estimate: {daily_sigma * 100.0:.2f}% daily (lookback {lookback} sessions)."
    )

    fundamentals_body = " · ".join(fundamentals_bits) if fundamentals_bits else "No fundamentals available."

    # Free news sentiment via GDELT (best-effort).
    # Using both the ticker and (if available) the company short name to reduce ambiguity.
    company = info.get("shortName") or info.get("longName")
    q_parts = [f"\"{symbol}\""]
    if company and isinstance(company, str):
        company = company.strip()
        if company:
            q_parts.append(f"\"{company}\"")
    gdelt_query = " OR ".join(q_parts)
    avg_tone = _gdelt_avg_tone(gdelt_query, timespan="7d")
    if avg_tone is None:
        sentiment_body = "News sentiment (GDELT): unavailable right now (rate-limited or no matching coverage)."
        sentiment_metric = "—"
    else:
        if avg_tone > 1.0:
            label = "Positive"
        elif avg_tone < -1.0:
            label = "Negative"
        else:
            label = "Neutral"
        sentiment_body = (
            f"News sentiment (GDELT, 7d): {label}. "
            f"Average tone: {avg_tone:+.2f} (higher = more positive)."
        )
        sentiment_metric = f"{avg_tone:+.2f}"

    return [
        {
            "title": "Price action",
            "body": price_action_body,
            "metric_label": "1M",
            "metric_value": _fmt_pct(r_21),
        },
        {
            "title": "Quantitative trajectory",
            "body": quant_body,
            "metric_label": "± Move",
            "metric_value": f"{exp_move:.2f}%",
        },
        {
            "title": "Fundamentals snapshot",
            "body": fundamentals_body,
            "metric_label": "Trend",
            "metric_value": trend_signal,
        },
        {
            "title": "News sentiment (free)",
            "body": sentiment_body,
            "metric_label": "Tone (7d)",
            "metric_value": sentiment_metric,
        },
    ]


def build_ticker_extras(symbol: str, market: str) -> dict[str, Any]:
    """Bundle extras passed to `ticker.html`. Called from `app.py`."""
    return {
        "graph_series": get_template_chart_series(symbol, market),
        "analysis_sections": get_analysis_sections(symbol, market),
    }
