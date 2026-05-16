"""
Claude-powered watchlist sentiment from Finnhub headlines (30-minute cache).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

import finnhub_news
from finnhub_client import finnhub_symbol

CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CACHE_TTL_SEC = 30 * 60
INTER_TICKER_DELAY_SEC = 0.35

WATCHLIST: list[dict[str, str]] = [
    {"label": "NDQ", "ticker": "NDQ", "market": "asx"},
    {"label": "VAS", "ticker": "VAS", "market": "asx"},
    {"label": "VGS", "ticker": "VGS", "market": "asx"},
    {"label": "NVTS", "ticker": "NVTS", "market": "us"},
    {"label": "ETHA", "ticker": "ETHA", "market": "us"},
]

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(label: str, ticker: str, market: str) -> str:
    return f"{label}:{ticker}:{market}".upper()


def _normalize_ticker(raw: str, market: str) -> str:
    t = raw.strip().upper()
    if not t:
        return t
    if market == "asx":
        if not t.endswith(".AX"):
            t = f"{t}.AX"
    else:
        if t.endswith(".AX"):
            t = t[:-3]
    return t


def get_anthropic_api_key() -> str | None:
    key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    return key or None


def _headlines_for_ticker(ticker: str, market: str, *, limit: int = 5) -> list[str]:
    """Last N company headlines (falls back to mixed feed)."""
    symbol = _normalize_ticker(ticker, market)
    try:
        payload = finnhub_news.fetch_news(symbol, "company")
        items = payload.get("items") or []
    except (ValueError, Exception):
        items = []

    if len(items) < limit:
        try:
            payload = finnhub_news.fetch_news(symbol, "all")
            seen = {i.get("headline") for i in items}
            for row in payload.get("items") or []:
                h = (row.get("headline") or "").strip()
                if h and h not in seen:
                    items.append(row)
                    seen.add(h)
                if len(items) >= limit:
                    break
        except (ValueError, Exception):
            pass

    out: list[str] = []
    for row in items[:limit]:
        h = (row.get("headline") or "").strip()
        if h:
            out.append(h)
    return out


def _system_prompt(ticker: str) -> str:
    return (
        f"You are a financial analyst. Given these news headlines for ticker {ticker}, "
        "return a JSON object with: "
        "{ sentiment: 'bullish' | 'neutral' | 'bearish', "
        "score: number between -1.0 and 1.0, "
        "reason: string under 20 words, "
        "key_risk: string under 15 words }"
    )


def _parse_json_response(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Claude response was not a JSON object.")
    return data


def _normalize_sentiment(data: dict[str, Any]) -> dict[str, Any]:
    sentiment = str(data.get("sentiment") or "neutral").strip().lower()
    if sentiment not in ("bullish", "neutral", "bearish"):
        sentiment = "neutral"

    try:
        score = float(data.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(-1.0, min(1.0, score))

    reason = str(data.get("reason") or "").strip()[:120]
    key_risk = str(data.get("key_risk") or "").strip()[:80]

    if not reason:
        reason = "Insufficient signal from headlines."
    if not key_risk:
        key_risk = "Headline sample may be incomplete."

    return {
        "sentiment": sentiment,
        "score": round(score, 3),
        "reason": reason,
        "key_risk": key_risk,
    }


def _call_claude(ticker: str, headlines: list[str]) -> dict[str, Any]:
    key = get_anthropic_api_key()
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file "
            "(see .env.example)."
        )

    user_body = (
        "Headlines:\n"
        + "\n".join(f"- {h}" for h in headlines)
        if headlines
        else "No recent headlines were available for this ticker."
    )

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 256,
        "system": _system_prompt(ticker),
        "messages": [{"role": "user", "content": user_body}],
    }

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode()[:300]
        except Exception:
            pass
        if e.code == 401:
            raise ValueError("Invalid Anthropic API key.") from e
        if e.code == 429:
            raise ValueError("Anthropic rate limit reached. Try again shortly.") from e
        raise ValueError(f"Claude API error ({e.code}): {err_body or e.reason}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"Could not reach Claude API: {e.reason}") from e

    blocks = body.get("content") or []
    text_parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text") or ""))
    if not text_parts:
        raise ValueError("Empty response from Claude API.")
    return _normalize_sentiment(_parse_json_response("\n".join(text_parts)))


def analyze_ticker_sentiment(
    label: str,
    ticker: str,
    market: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    ck = _cache_key(label, ticker, market)
    now = time.time()

    if not force_refresh and ck in _CACHE:
        expires, cached = _CACHE[ck]
        if now < expires:
            row = dict(cached)
            row["from_cache"] = True
            row["cached_until"] = int(expires)
            return row

    headlines = _headlines_for_ticker(ticker, market, limit=5)
    sym = _normalize_ticker(ticker, market)
    fh_ticker = finnhub_symbol(sym)

    if not headlines:
        result = _normalize_sentiment(
            {
                "sentiment": "neutral",
                "score": 0.0,
                "reason": "No recent headlines available.",
                "key_risk": "Thin or missing news flow.",
            }
        )
    else:
        result = _call_claude(fh_ticker or ticker.upper(), headlines)

    row: dict[str, Any] = {
        "label": label,
        "ticker": ticker.upper(),
        "market": market,
        "finnhub_symbol": fh_ticker,
        "headline_count": len(headlines),
        "from_cache": False,
        "cached_until": int(now + CACHE_TTL_SEC),
        **result,
    }
    _CACHE[ck] = (now + CACHE_TTL_SEC, row)
    return row


def get_watchlist_sentiment(*, force_refresh: bool = False) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for i, entry in enumerate(WATCHLIST):
        if force_refresh and i > 0:
            time.sleep(INTER_TICKER_DELAY_SEC)
        items.append(
            analyze_ticker_sentiment(
                entry["label"],
                entry["ticker"],
                entry["market"],
                force_refresh=force_refresh,
            )
        )

    cached_until = max((r.get("cached_until") or 0) for r in items) if items else 0
    return {
        "items": items,
        "cached_until": cached_until,
        "cache_ttl_sec": CACHE_TTL_SEC,
        "model": CLAUDE_MODEL,
    }
