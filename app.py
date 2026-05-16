"""
Small Flask app: US vs ASX quotes (yfinance) and ticker insight pages.
"""

from __future__ import annotations

import os
from datetime import timezone
from typing import Any

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, render_template, request

import analytics
import indicators

app = Flask(__name__)

MARKET_DISPLAY = {
    "us": "United States · NYSE / NASDAQ",
    "asx": "Australia · ASX / ASX 200",
}

# yfinance period / interval per UI timeframe button
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


def normalize_ticker(raw: str, market: str) -> str:
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


def _fast_get(fast, key: str):
    if fast is None:
        return None
    if isinstance(fast, dict):
        return fast.get(key)
    return getattr(fast, key, None)


def _history_rule(interval: str) -> str | None:
    interval = (interval or "").strip().lower()
    if interval in ("", "day", "daily", "d"):
        return None
    if interval in ("week", "weekly", "w"):
        return "W-FRI"
    if interval in ("month", "monthly", "m"):
        return "M"
    if interval in ("quarter", "quarterly", "q"):
        return "Q"
    if interval in ("year", "yearly", "y", "annual", "annually"):
        return "Y"
    return None


def _bars_from_hist(df: pd.DataFrame, *, intraday: bool) -> list[dict[str, Any]]:
    idx = df.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert(timezone.utc).tz_localize(None)
    bars: list[dict[str, Any]] = []
    for i, ts in enumerate(idx):
        row = df.iloc[i]
        if intraday:
            t = pd.Timestamp(ts).isoformat()
        else:
            t = pd.Timestamp(ts).strftime("%Y-%m-%d")
        bars.append(
            {
                "t": t,
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": float(row["Volume"]) if pd.notna(row["Volume"]) else 0.0,
            }
        )
    return bars


def fetch_ohlc(
    symbol: str, range_key: str = DEFAULT_CHART_RANGE
) -> tuple[dict[str, Any] | None, str | None]:
    """OHLCV bars for Plotly candlestick charts."""
    key = (range_key or DEFAULT_CHART_RANGE).strip().upper()
    cfg = CHART_RANGES.get(key)
    if not cfg:
        return None, f'range must be one of: {", ".join(CHART_RANGES)}'

    period = cfg["period"]
    interval = cfg["interval"]
    intraday = interval not in ("1d", "1wk", "1mo", "3mo")

    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, interval=interval, auto_adjust=True)
        if hist is None or hist.empty:
            return None, "No price history returned for this symbol."

        df = pd.DataFrame(hist)[["Open", "High", "Low", "Close", "Volume"]].dropna(
            how="all", subset=["Close"]
        )
        if df.empty:
            return None, "No usable OHLCV rows for this symbol."

        bars = _bars_from_hist(df, intraday=intraday)
        if not bars:
            return None, "No usable OHLCV rows for this symbol."

        ind = indicators.compute_indicators(df)

        info: dict[str, Any] = {}
        try:
            info = stock.info or {}
        except Exception:
            info = {}
        try:
            fast = stock.fast_info
        except Exception:
            fast = {}

        last = _fast_get(fast, "last_price") or _fast_get(fast, "lastPrice")
        if last is None:
            last = info.get("regularMarketPrice") or info.get("currentPrice")
        if last is None:
            last = bars[-1]["c"]

        prev_close = _fast_get(fast, "previous_close") or _fast_get(fast, "previousClose")
        if prev_close is None:
            prev_close = info.get("previousClose")
        if prev_close is None and len(bars) > 1:
            prev_close = bars[-2]["c"]

        change_pct = None
        if last is not None and prev_close not in (None, 0):
            try:
                change_pct = (float(last) - float(prev_close)) / float(prev_close) * 100.0
            except (TypeError, ValueError):
                change_pct = None

        return {
            "symbol": symbol,
            "range": key,
            "bars": bars,
            "indicators": ind,
            "intraday": intraday,
            "name": info.get("shortName") or info.get("longName") or symbol,
            "last": float(last) if last is not None else None,
            "previous_close": float(prev_close) if prev_close is not None else None,
            "change_percent": round(change_pct, 2) if change_pct is not None else None,
            "currency": info.get("currency") or _fast_get(fast, "currency"),
            "exchange": info.get("exchange") or info.get("fullExchangeName"),
        }, None
    except Exception as e:
        return None, str(e)


def fetch_history(
    symbol: str, period: str = "3mo", interval: str = "day"
) -> tuple[dict | None, str | None]:
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, auto_adjust=True)
        if hist is None or hist.empty:
            return None, "No price history returned for this symbol."
        df = pd.DataFrame(hist)[["Open", "High", "Low", "Close", "Volume"]].dropna(
            how="all", subset=["Close"]
        )
        if df.empty:
            return None, "No usable OHLCV rows for this symbol."

        rule = _history_rule(interval)
        if rule:
            # Close: last available in the bucket. Volume: total in bucket.
            df = (
                df.resample(rule)
                .agg({"Close": "last", "Volume": "sum"})
                .dropna(how="all", subset=["Close"])
            )

        idx = df.index
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert(timezone.utc).tz_localize(None)
        dates = [d.strftime("%Y-%m-%d") for d in idx]
        closes = df["Close"].astype(float).tolist()
        series = [{"date": d, "close": float(c)} for d, c in zip(dates, closes)]
        return {"series": series}, None
    except Exception as e:
        return None, str(e)


def compute_quote(
    raw: str, market: str, *, history_period: str = "3mo", history_interval: str = "day"
) -> tuple[dict[str, Any] | None, str | None]:
    """Shared quote payload for /api/quote and ticker page."""
    if market not in ("us", "asx"):
        return None, 'market must be "us" or "asx"'
    if not raw.strip():
        return None, "Enter a ticker symbol."

    symbol = normalize_ticker(raw, market)
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        try:
            fast = stock.fast_info
        except Exception:
            fast = {}
    except Exception as e:
        return None, f"Request failed: {e}"

    last = _fast_get(fast, "last_price") or _fast_get(fast, "lastPrice")
    if last is None:
        last = info.get("regularMarketPrice") or info.get("currentPrice")

    prev_close = _fast_get(fast, "previous_close") or _fast_get(fast, "previousClose")
    if prev_close is None:
        prev_close = info.get("previousClose")

    hist_payload, hist_err = fetch_history(
        symbol, period=history_period, interval=history_interval
    )
    if last is None and hist_payload and hist_payload.get("series"):
        pts = hist_payload["series"]
        last = pts[-1]["close"]
        if prev_close is None and len(pts) > 1:
            prev_close = pts[-2]["close"]

    change_pct = None
    if last is not None and prev_close not in (None, 0):
        try:
            change_pct = (float(last) - float(prev_close)) / float(prev_close) * 100.0
        except (TypeError, ValueError):
            change_pct = None

    currency = info.get("currency") or _fast_get(fast, "currency")
    name = info.get("shortName") or info.get("longName") or symbol
    exchange = info.get("exchange") or info.get("fullExchangeName")

    if hist_err and last is None:
        return None, hist_err or "Could not load symbol."

    last_f = float(last) if last is not None else None
    prev_f = float(prev_close) if prev_close is not None else None

    return {
        "symbol": symbol,
        "name": name,
        "market": market,
        "last": last_f,
        "previous_close": prev_f,
        "change_percent": round(change_pct, 2) if change_pct is not None else None,
        "currency": currency,
        "exchange": exchange,
        "history": hist_payload,
        "history_error": hist_err,
    }, None


def format_price(amount: float | None, currency: str | None) -> str | None:
    if amount is None:
        return None
    cur = currency or "USD"
    return f"{amount:,.2f} {cur}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ticker/<path:raw_ticker>")
def ticker_page(raw_ticker: str):
    market = request.args.get("market", "us").lower()
    if market not in ("us", "asx"):
        market = "us"

    chart_range = request.args.get("range", DEFAULT_CHART_RANGE).strip().upper()
    if chart_range not in CHART_RANGES:
        chart_range = DEFAULT_CHART_RANGE
    data, err = compute_quote(raw_ticker, market)
    if err or data is None:
        return render_template(
            "ticker.html",
            error=err or "Unknown error.",
            name=None,
            symbol=normalize_ticker(raw_ticker, market) if raw_ticker.strip() else "",
            chart_range=chart_range,
            chart_ranges=list(CHART_RANGES.keys()),
        )

    sym = data["symbol"]
    extras = analytics.build_ticker_extras(sym, market)
    graph_series = (data.get("history") or {}).get("series") or extras["graph_series"]

    return render_template(
        "ticker.html",
        error=None,
        name=data.get("name"),
        symbol=sym,
        market=market,
        market_display=MARKET_DISPLAY[market],
        chart_range=chart_range,
        chart_ranges=list(CHART_RANGES.keys()),
        last=data.get("last"),
        last_display=format_price(data.get("last"), data.get("currency")),
        change_percent=data.get("change_percent"),
        currency=data.get("currency"),
        exchange=data.get("exchange"),
        graph_series=graph_series,
        analysis_sections=extras["analysis_sections"],
    )


@app.get("/api/ohlc")
def ohlc():
    raw = request.args.get("ticker", "").strip()
    market = request.args.get("market", "us").lower()
    range_key = request.args.get("range", DEFAULT_CHART_RANGE).strip().upper()

    if market not in ("us", "asx"):
        return jsonify({"ok": False, "error": 'market must be "us" or "asx"'}), 400
    if not raw.strip():
        return jsonify({"ok": False, "error": "Enter a ticker symbol."}), 400

    symbol = normalize_ticker(raw, market)
    payload, err = fetch_ohlc(symbol, range_key)
    if err:
        code = 404 if "No " in err or "Invalid" in err else 502
        return jsonify({"ok": False, "error": err, "symbol": symbol}), code
    assert payload is not None
    return jsonify({"ok": True, "market": market, **payload})


@app.get("/api/quote")
def quote():
    raw = request.args.get("ticker", "").strip()
    market = request.args.get("market", "us").lower()
    interval = request.args.get("interval", "day").lower()
    data, err = compute_quote(raw, market, history_interval=interval)
    if err:
        if "Enter a ticker" in err or "market must" in err:
            code = 400
        elif str(err).startswith("Request failed"):
            code = 502
        else:
            code = 404
        return jsonify({"ok": False, "error": err}), code
    assert data is not None
    return jsonify(
        {
            "ok": True,
            **data,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
