"""Shared constants for markets, chart timeframes, and display."""

MARKET_DISPLAY = {
    "us": "United States · NYSE / NASDAQ",
    "asx": "Australia · ASX / ASX 200",
}

CHART_RANGES: dict[str, dict[str, str]] = {
    "1D": {"period": "1d", "interval": "5m"},
    "5D": {"period": "5d", "interval": "30m"},
    "1M": {"period": "1mo", "interval": "1d"},
    "3M": {"period": "3mo", "interval": "1d"},
    "6M": {"period": "6mo", "interval": "1d"},
    "1Y": {"period": "1y", "interval": "1d"},
    "5Y": {"period": "5y", "interval": "1wk"},
}

DEFAULT_CHART_RANGE = "3M"
