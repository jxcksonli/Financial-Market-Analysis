"""Shared Anthropic Claude API helper."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def get_anthropic_api_key() -> str | None:
    key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    return key or None


def claude_complete(
    *,
    system: str,
    user: str,
    max_tokens: int = 1024,
    timeout: int = 90,
) -> str:
    key = get_anthropic_api_key()
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file "
            "(see .env.example)."
        )

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("Empty response from Claude API.")
    return text
