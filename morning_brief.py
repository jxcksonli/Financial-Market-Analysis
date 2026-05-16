"""
Morning Brief: watchlist moves, headlines, events → Claude summary.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

import yfinance as yf
import macro_calendar
from claude_client import CLAUDE_MODEL, claude_complete
from finnhub_client import finnhub_symbol
from finnhub_events import fetch_earnings_calendar
from sentiment_service import WATCHLIST, _headlines_for_ticker, _normalize_ticker

MORNING_BRIEF_SYSTEM = """You are my personal trading assistant. Generate a concise morning brief for today
in this format:
- MARKET MOOD: one sentence on overall sentiment
- WATCHLIST MOVES: for each ticker, one line: price change, why (if news), watch for
- TODAY'S EVENTS: any earnings or macro events to be aware of
- FOCUS: which 1-2 tickers deserve the most attention today and why
Keep the whole brief under 250 words. Be direct, no filler."""


def _overnight_change_pct(symbol: str) -> dict[str, Any]:
    """Last session vs prior close from daily bars."""
    out: dict[str, Any] = {
        "change_percent": None,
        "last_close": None,
        "prev_close": None,
        "as_of": None,
    }
    try:
        hist = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=True)
        if hist is None or hist.empty or len(hist) < 2:
            return out
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return out
        prev = float(closes.iloc[-2])
        last = float(closes.iloc[-1])
        out["last_close"] = round(last, 4)
        out["prev_close"] = round(prev, 4)
        out["as_of"] = str(closes.index[-1].date())
        if prev != 0:
            out["change_percent"] = round((last - prev) / prev * 100.0, 2)
    except Exception:
        pass
    return out


def _watchlist_snapshot() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in WATCHLIST:
        label = entry["label"]
        market = entry["market"]
        sym = _normalize_ticker(entry["ticker"], market)
        move = _overnight_change_pct(sym)
        headlines = _headlines_for_ticker(entry["ticker"], market, limit=3)
        rows.append(
            {
                "label": label,
                "symbol": sym,
                "finnhub_symbol": finnhub_symbol(sym),
                "market": market,
                "change_percent": move["change_percent"],
                "last_close": move["last_close"],
                "prev_close": move["prev_close"],
                "price_as_of": move["as_of"],
                "headlines": headlines,
            }
        )
    return rows


def _events_today_tomorrow() -> dict[str, Any]:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    macro = [
        m
        for m in macro_calendar.macro_events_between(today, tomorrow)
        if m.get("days_until") in (0, 1)
    ]

    earnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in WATCHLIST:
        fh = finnhub_symbol(_normalize_ticker(entry["ticker"], entry["market"]))
        try:
            rows = fetch_earnings_calendar(today, tomorrow, fh)
        except (ValueError, Exception):
            continue
        for row in rows:
            if row.get("days_until") not in (0, 1):
                continue
            key = (row.get("symbol"), row.get("date"))
            if key in seen:
                continue
            seen.add(key)
            earnings.append(row)

    earnings.sort(key=lambda x: (x.get("date"), x.get("symbol")))
    return {
        "today": today.isoformat(),
        "tomorrow": tomorrow.isoformat(),
        "macro": macro,
        "earnings": earnings,
    }


def _build_user_payload() -> dict[str, Any]:
    today = date.today()
    return {
        "brief_date": today.isoformat(),
        "weekday": today.strftime("%A"),
        "watchlist": _watchlist_snapshot(),
        "events": _events_today_tomorrow(),
    }


def generate_morning_brief() -> dict[str, Any]:
    payload = _build_user_payload()
    user_message = (
        "Use the following JSON data to write today's morning brief.\n\n"
        + json.dumps(payload, indent=2)
    )
    brief_text = claude_complete(
        system=MORNING_BRIEF_SYSTEM,
        user=user_message,
        max_tokens=600,
        timeout=90,
    )
    now = datetime.now(timezone.utc).astimezone()
    return {
        "brief": brief_text,
        "date": payload["brief_date"],
        "generated_at": now.isoformat(timespec="seconds"),
        "model": CLAUDE_MODEL,
        "context": payload,
    }
