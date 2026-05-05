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

import math
from datetime import date, timedelta
from typing import Any


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
    # Placeholder: smooth wave — same *shape* for every ticker until you replace it.
    out: list[dict[str, Any]] = []
    start = date.today() - timedelta(days=90)
    for i in range(64):
        d = start + timedelta(days=i)
        t = i / 6.0
        close = 100.0 + 12.0 * math.sin(t) + 3.0 * math.cos(t * 0.7)
        out.append({"date": d.isoformat(), "close": round(close, 2)})
    return out


def get_analysis_sections(symbol: str, market: str) -> list[dict[str, Any]]:
    """
    Blocks rendered under "Analysis" on the ticker page.

    Return a list of dicts with keys: title, body (plain text or short HTML-safe string).
    Optional: metric_label, metric_value for a small stat chip in the card.

    Replace template strings with outputs from your analytics (e.g. volatility, beta).
    """
    market_label = "Australia (ASX)" if market == "asx" else "United States (NYSE / NASDAQ)"
    return [
        {
            "title": "Price action (template)",
            "body": (
                f"Symbol {symbol} on {market_label}. Replace this block in "
                "`analytics.get_analysis_sections()` with summaries from your DataFrame."
            ),
            "metric_label": "Template",
            "metric_value": "—",
        },
        {
            "title": "Momentum & trend (template)",
            "body": (
                "Add RSI, MACD, or moving-average signals here using pandas-ta or "
                "your own rolling-window logic."
            ),
            "metric_label": "Signal",
            "metric_value": "Neutral",
        },
        {
            "title": "Risk snapshot (template)",
            "body": (
                "Placeholder for volatility (e.g. annualized std of log returns), "
                "max drawdown, or beta vs a benchmark index."
            ),
            "metric_label": "Vol (template)",
            "metric_value": "—",
        },
    ]


def build_ticker_extras(symbol: str, market: str) -> dict[str, Any]:
    """Bundle extras passed to `ticker.html`. Called from `app.py`."""
    return {
        "graph_series": get_template_chart_series(symbol, market),
        "analysis_sections": get_analysis_sections(symbol, market),
    }
