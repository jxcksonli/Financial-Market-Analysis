"""Bundle earnings, macro calendar, and chart event markers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fmi.data import macro_calendar
from fmi.integrations.finnhub.client import finnhub_symbol
from fmi.integrations.finnhub.events import (
    fetch_earnings_calendar,
    upcoming_earnings_for_symbols,
)

EARNINGS_WATCHLIST = ("NVTS", "ETHA")

# Approximate calendar span per chart range (days back from today)
RANGE_HISTORY_DAYS: dict[str, int] = {
    "1D": 3,
    "5D": 10,
    "1M": 35,
    "3M": 100,
    "6M": 200,
    "1Y": 380,
    "5Y": 1900,
}


def earnings_symbol_set(chart_symbol: str) -> list[str]:
    symbols: list[str] = list(EARNINGS_WATCHLIST)
    fh = finnhub_symbol(chart_symbol)
    if fh and fh not in symbols:
        symbols.append(fh)
    return symbols


def _bar_dates(bars: list[dict[str, Any]]) -> list[str]:
    return [str(b.get("t") or "") for b in bars if b.get("t")]


def _date_only(ts: str) -> str:
    return (ts or "")[:10]


def align_marker_x(event_date: str, bar_times: list[str], intraday: bool) -> str | None:
    """Pick a bar x value that Plotly can use for a vertical line."""
    d = event_date[:10]
    if not d:
        return None

    if intraday:
        for t in bar_times:
            if _date_only(t) == d:
                return t
        return None

    if d in bar_times:
        return d
    for t in bar_times:
        if _date_only(t) == d:
            return t
    return None


def build_chart_markers(
    chart_symbol: str,
    range_key: str,
    bars: list[dict[str, Any]],
    *,
    intraday: bool,
) -> list[dict[str, Any]]:
    if not bars:
        return []

    today = date.today()
    days_back = RANGE_HISTORY_DAYS.get(range_key.upper(), 100)
    from_d = today - timedelta(days=days_back)
    to_d = today

    bar_times = _bar_dates(bars)
    markers: list[dict[str, Any]] = []
    seen_x: set[str] = set()

    def add_marker(iso: str, kind: str, label: str) -> None:
        x = align_marker_x(iso, bar_times, intraday)
        if not x or x in seen_x:
            return
        seen_x.add(x)
        markers.append(
            {
                "date": iso[:10],
                "x": x,
                "type": kind,
                "label": label,
            }
        )

    try:
        earn_rows = fetch_earnings_calendar(
            from_d, to_d, finnhub_symbol(chart_symbol)
        )
        for row in earn_rows:
            if row["date"][:10] > today.isoformat():
                continue
            add_marker(row["date"], "earnings", f"{row['symbol']} earnings")
    except (ValueError, Exception):
        pass

    for macro in macro_calendar.macro_events_between(from_d, to_d):
        if macro["date"] > today.isoformat():
            continue
        add_marker(macro["date"], "macro", macro["title"])

    markers.sort(key=lambda m: m["date"])
    return markers


def fetch_events_panel(chart_symbol: str) -> dict[str, Any]:
    """Earnings + macro lists only (no chart marker rebuild)."""
    symbols = earnings_symbol_set(chart_symbol)
    earnings: list[dict[str, Any]] = []
    try:
        earnings = upcoming_earnings_for_symbols(symbols)
    except ValueError:
        raise

    macro = macro_calendar.upcoming_macro()
    return {
        "chart_symbol": chart_symbol,
        "finnhub_symbol": finnhub_symbol(chart_symbol),
        "earnings_watchlist": list(EARNINGS_WATCHLIST),
        "earnings": earnings,
        "macro": macro,
    }


def fetch_events_payload(
    chart_symbol: str,
    range_key: str,
    bars: list[dict[str, Any]] | None = None,
    *,
    intraday: bool = False,
) -> dict[str, Any]:
    payload = fetch_events_panel(chart_symbol)
    chart_markers: list[dict[str, Any]] = []
    if bars:
        chart_markers = build_chart_markers(
            chart_symbol, range_key, bars, intraday=intraday
        )
    payload["chart_markers"] = chart_markers
    return payload
