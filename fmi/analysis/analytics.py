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

# Simple category taxonomy (extensible)
# Keep it intentionally small and “human-guessable”.
CATEGORY_RULES: dict[str, dict[str, list[str]]] = {
    "Utilities": {
        "keywords": ["utility", "utilities", "power grid", "electricity", "gas", "water", "renewable", "solar", "wind"],
        "domains": [],
    },
    "Tech": {
        "keywords": ["ai", "chip", "semiconductor", "software", "cloud", "cyber", "iphone", "android", "microsoft", "apple"],
        "domains": [],
    },
    "Finance": {
        "keywords": ["bank", "banks", "interest rate", "rates", "fed", "rba", "inflation", "loan", "credit", "mortgage"],
        "domains": [],
    },
    "Energy": {
        "keywords": ["oil", "gas", "opec", "crude", "lng", "pipeline", "energy"],
        "domains": [],
    },
    "Politics": {
        "keywords": ["donald trump", "biden", "election", "tariff", "sanction", "white house", "congress", "parliament"],
        "domains": [],
    },
}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def classify_ticker_category(info: dict[str, Any]) -> str:
    sector = _norm(str(info.get("sector") or ""))
    industry = _norm(str(info.get("industry") or ""))
    s = f"{sector} {industry}"
    if "utility" in s:
        return "Utilities"
    if "financial" in s or "bank" in s or "insurance" in s:
        return "Finance"
    if "technology" in s or "software" in s or "semiconductor" in s:
        return "Tech"
    if "energy" in s or "oil" in s or "gas" in s:
        return "Energy"
    return "Other"


def classify_news_category(title: str, domain: str | None = None) -> str:
    text = f"{_norm(title)} {_norm(domain or '')}"
    if not text.strip():
        return "Other"
    for cat, rules in CATEGORY_RULES.items():
        for kw in rules.get("keywords", []):
            if _norm(kw) and _norm(kw) in text:
                return cat
        for d in rules.get("domains", []):
            if _norm(d) and _norm(d) in _norm(domain or ""):
                return cat
    return "Other"


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


def _gdelt_articles(
    query: str,
    *,
    startdatetime: str,
    enddatetime: str,
    max_records: int = 8,
) -> list[dict[str, str]]:
    """
    Pull a small list of matching articles (title + url) from GDELT ArtList mode.
    """
    q = (query or "").strip()
    if not q:
        return []

    cache_key = ("artlist", f"{startdatetime}|{enddatetime}|{max_records}|{q}")
    now = time.time()
    cached = _GDELT_CACHE.get(cache_key)
    if cached and now - cached[0] < 30 * 60:
        # Stored as {"articles": [...]} for cache compatibility.
        cached_articles = cached[1].get("articles")
        if isinstance(cached_articles, list):
            return [a for a in cached_articles if isinstance(a, dict)]  # type: ignore[return-value]

    params = {
        "query": q,
        "mode": "ArtList",
        "format": "json",
        "startdatetime": startdatetime,
        "enddatetime": enddatetime,
        "maxrecords": str(max_records),
        "sort": "datedesc",
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FinancialMarketInsights/1.0 (gdelt news; no-auth; educational)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        obj = json.loads(raw)
    except Exception:
        return []

    if not isinstance(obj, dict):
        return []

    arts = obj.get("articles")
    if not isinstance(arts, list):
        return []

    out: list[dict[str, str]] = []
    for a in arts:
        if not isinstance(a, dict):
            continue
        title = a.get("title") or a.get("name") or ""
        url = a.get("url") or ""
        if not isinstance(title, str) or not isinstance(url, str):
            continue
        title = title.strip()
        url = url.strip()
        if not title or not url:
            continue
        seendate = a.get("seendate") or a.get("date") or ""
        domain = a.get("domain") or ""
        meta = " · ".join([x for x in [domain, seendate] if isinstance(x, str) and x.strip()])
        cat = classify_news_category(title, domain if isinstance(domain, str) else None)
        out.append(
            {
                "title": title,
                "url": url,
                "meta": meta,
                "domain": domain if isinstance(domain, str) else "",
                "category": cat,
            }
        )

    _GDELT_CACHE[cache_key] = (now, {"articles": out})
    return out


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

    ticker_cat = classify_ticker_category(info)

    # Big move detection (last ~60 sessions) + attach headlines around that date.
    # Note: GDELT DOC API only searches the last ~3 months; this intentionally stays recent.
    daily_rets = close.pct_change().dropna()
    last_n = daily_rets.tail(60)
    if last_n.empty:
        moves_body = "No recent daily returns available to detect large moves."
        moves_links: list[dict[str, str]] = []
        moves_metric = "—"
    else:
        dip_date = last_n.idxmin()
        dip_ret = float(last_n.min()) * 100.0
        gain_date = last_n.idxmax()
        gain_ret = float(last_n.max()) * 100.0

        def _dt_range(d) -> tuple[str, str]:
            # Search a 48h window around the move date.
            # GDELT expects YYYYMMDDHHMMSS.
            day = pd.Timestamp(d).to_pydatetime()
            start = pd.Timestamp(day.date()) - pd.Timedelta(days=1)
            end = pd.Timestamp(day.date()) + pd.Timedelta(days=1, hours=23, minutes=59, seconds=59)
            return start.strftime("%Y%m%d%H%M%S"), end.strftime("%Y%m%d%H%M%S")

        dip_start, dip_end = _dt_range(dip_date)
        gain_start, gain_end = _dt_range(gain_date)

        dip_links = _gdelt_articles(
            gdelt_query, startdatetime=dip_start, enddatetime=dip_end, max_records=6
        )
        gain_links = _gdelt_articles(
            gdelt_query, startdatetime=gain_start, enddatetime=gain_end, max_records=6
        )

        def _best_cause(links: list[dict[str, Any]]) -> dict[str, Any] | None:
            if not links:
                return None
            for l in links:
                if l.get("category") == ticker_cat and ticker_cat != "Other":
                    return l
            # Prefer politics if it explicitly mentions it (user example: Trump, actions, etc.)
            for l in links:
                if l.get("category") == "Politics":
                    return l
            return links[0]

        dip_cause = _best_cause(dip_links)
        gain_cause = _best_cause(gain_links)

        moves_body = (
            f"Largest dip (recent): {pd.Timestamp(dip_date).date().isoformat()} ({dip_ret:+.2f}%). "
            f"Largest gain (recent): {pd.Timestamp(gain_date).date().isoformat()} ({gain_ret:+.2f}%)."
        )
        moves_links = (
            [
                {
                    "title": f"Dip coverage ({l.get('category','Other')}): {l['title']}",
                    "url": l["url"],
                    "meta": l.get("meta", ""),
                }
                for l in dip_links[:3]
            ]
            + [
                {
                    "title": f"Gain coverage ({l.get('category','Other')}): {l['title']}",
                    "url": l["url"],
                    "meta": l.get("meta", ""),
                }
                for l in gain_links[:3]
            ]
        )
        moves_metric = f"{max(abs(dip_ret), abs(gain_ret)):.2f}%"

        dip_label = None
        dip_url = None
        if dip_cause:
            dip_label = f"Caused by: {dip_cause.get('title','').strip()}"
            dip_url = dip_cause.get("url")

        gain_label = None
        gain_url = None
        if gain_cause:
            gain_label = f"Caused by: {gain_cause.get('title','').strip()}"
            gain_url = gain_cause.get("url")

        # Expose marker data via a hidden analysis block entry (used by the chart JS).
        # This keeps the wiring minimal without adding new routes.
        marker_block = {
            "title": "Chart markers",
            "body": "",
            "hidden": True,
            "markers": [
                {
                    "date": pd.Timestamp(dip_date).date().isoformat(),
                    "kind": "dip",
                    "label": dip_label,
                    "url": dip_url,
                    "category": ticker_cat,
                },
                {
                    "date": pd.Timestamp(gain_date).date().isoformat(),
                    "kind": "gain",
                    "label": gain_label,
                    "url": gain_url,
                    "category": ticker_cat,
                },
            ],
        }

    blocks = [
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
        {
            "title": "Big moves ↔ news",
            "body": moves_body,
            "links": moves_links,
            "metric_label": "Max move",
            "metric_value": moves_metric,
        },
    ]
    if "marker_block" in locals():
        blocks.append(marker_block)
    return [b for b in blocks if b]


def build_ticker_extras(symbol: str, market: str) -> dict[str, Any]:
    """Bundle extras passed to `ticker.html`. Called from `app.py`."""
    return {
        "graph_series": get_template_chart_series(symbol, market),
        "analysis_sections": get_analysis_sections(symbol, market),
    }
