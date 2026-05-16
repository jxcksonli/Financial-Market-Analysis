"""
Finnhub news (free tier) — company and market headlines.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any

FINNHUB_BASE = "https://finnhub.io/api/v1"
NEWS_LIMIT = 20
LOOKBACK_DAYS = 30


def get_api_key() -> str | None:
    key = (os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_TOKEN") or "").strip()
    return key or None


def finnhub_symbol(symbol: str) -> str:
    """Map app symbols to Finnhub tickers (US-focused API)."""
    s = symbol.strip().upper()
    if s.endswith(".AX"):
        return s[:-3]
    return s


def _time_ago(unix_ts: int) -> str:
    if not unix_ts:
        return ""
    try:
        ts = int(unix_ts)
    except (TypeError, ValueError):
        return ""
    delta = max(0, int(time.time()) - ts)
    if delta < 60:
        return "just now"
    if delta < 3600:
        m = delta // 60
        return f"{m}m ago"
    if delta < 86400:
        h = delta // 3600
        return f"{h}h ago"
    d = delta // 86400
    if d == 1:
        return "1d ago"
    if d < 7:
        return f"{d}d ago"
    w = d // 7
    return f"{w}w ago" if w > 1 else "1w ago"


def _normalize_item(item: dict[str, Any], category: str) -> dict[str, Any]:
    ts = item.get("datetime") or 0
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = 0
    headline = (item.get("headline") or item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "").strip()
    return {
        "headline": headline,
        "source": source,
        "url": url,
        "published_at": ts,
        "time_ago": _time_ago(ts),
        "category": category,
    }


def _finnhub_get(path: str, params: dict[str, Any]) -> Any:
    key = get_api_key()
    if not key:
        raise ValueError(
            "FINNHUB_API_KEY is not set. Create a .env file in the project root "
            "(see .env.example) with your key from https://finnhub.io/register"
        )

    q = {**params, "token": key}
    url = f"{FINNHUB_BASE}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Financial-Market-Insights/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
        if e.code == 401:
            raise ValueError("Invalid Finnhub API key.") from e
        if e.code == 429:
            raise ValueError("Finnhub rate limit reached. Try again shortly.") from e
        raise ValueError(f"Finnhub request failed ({e.code}): {body or e.reason}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"Could not reach Finnhub: {e.reason}") from e


def fetch_company_news(symbol: str) -> list[dict[str, Any]]:
    sym = finnhub_symbol(symbol)
    today = date.today()
    from_d = today - timedelta(days=LOOKBACK_DAYS)
    raw = _finnhub_get(
        "/company-news",
        {"symbol": sym, "from": from_d.isoformat(), "to": today.isoformat()},
    )
    if not isinstance(raw, list):
        return []

    items: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        norm = _normalize_item(row, "company")
        if norm["headline"] and norm["url"]:
            items.append(norm)

    items.sort(key=lambda x: x["published_at"], reverse=True)
    return items[:NEWS_LIMIT]


def fetch_market_news() -> list[dict[str, Any]]:
    raw = _finnhub_get("/news", {"category": "general"})
    if not isinstance(raw, list):
        return []

    items: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        norm = _normalize_item(row, "market")
        if norm["headline"] and norm["url"]:
            items.append(norm)

    items.sort(key=lambda x: x["published_at"], reverse=True)
    return items[:NEWS_LIMIT]


def _merge_dedupe(
    company: list[dict[str, Any]], market: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for item in company + market:
        key = item.get("url") or item.get("headline")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    merged.sort(key=lambda x: x["published_at"], reverse=True)
    return merged[:NEWS_LIMIT]


def fetch_news(symbol: str, news_filter: str = "all") -> dict[str, Any]:
    """Return up to 20 news items for *symbol* and filter mode."""
    filt = (news_filter or "all").strip().lower()
    if filt not in ("all", "company", "market"):
        raise ValueError('filter must be "all", "company", or "market"')

    fh_sym = finnhub_symbol(symbol)
    company: list[dict[str, Any]] = []
    market: list[dict[str, Any]] = []

    if filt in ("all", "company"):
        company = fetch_company_news(symbol)
    if filt in ("all", "market"):
        market = fetch_market_news()

    if filt == "company":
        items = company
    elif filt == "market":
        items = market
    else:
        items = _merge_dedupe(company, market)

    return {
        "symbol": symbol,
        "finnhub_symbol": fh_sym,
        "filter": filt,
        "items": items,
    }
