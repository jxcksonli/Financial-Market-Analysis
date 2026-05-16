"""Shared Finnhub HTTP client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

FINNHUB_BASE = "https://finnhub.io/api/v1"


def get_api_key() -> str | None:
    key = (os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_TOKEN") or "").strip()
    return key or None


def finnhub_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".AX"):
        return s[:-3]
    return s


def finnhub_get(path: str, params: dict[str, Any]) -> Any:
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
