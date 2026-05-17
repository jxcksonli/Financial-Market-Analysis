"""HTTP routes and JSON API endpoints."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from fmi.analysis.analytics import get_analysis_sections
from fmi.config import CHART_RANGES, DEFAULT_CHART_RANGE, MARKET_DISPLAY
from fmi.integrations.finnhub import fetch_news
from fmi.quotes import (
    compute_quote,
    fetch_ohlc,
    format_price,
    normalize_ticker,
)
import fmi.services.events as events_service


def register_routes(app: Flask) -> None:
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
      data, err = compute_quote(raw_ticker, market, include_history=False)
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
      analysis_sections = get_analysis_sections(sym, market)

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
          analysis_sections=analysis_sections,
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

  @app.get("/api/news")
  def news():
      raw = request.args.get("ticker", "").strip()
      market = request.args.get("market", "us").lower()
      news_filter = request.args.get("filter", "all").lower()

      if market not in ("us", "asx"):
          return jsonify({"ok": False, "error": 'market must be "us" or "asx"'}), 400
      if not raw.strip():
          return jsonify({"ok": False, "error": "Enter a ticker symbol."}), 400

      symbol = normalize_ticker(raw, market)
      try:
          payload = fetch_news(symbol, news_filter)
      except ValueError as e:
          msg = str(e)
          if "FINNHUB_API_KEY" in msg or "Invalid Finnhub" in msg:
              code = 503
          elif "rate limit" in msg.lower():
              code = 429
          else:
              code = 502
          return jsonify({"ok": False, "error": msg, "symbol": symbol}), code

      return jsonify({"ok": True, "market": market, **payload})

  @app.get("/api/events")
  def events():
      raw = request.args.get("ticker", "").strip()
      market = request.args.get("market", "us").lower()
      range_key = request.args.get("range", DEFAULT_CHART_RANGE).strip().upper()
      if range_key not in CHART_RANGES:
          range_key = DEFAULT_CHART_RANGE

      if market not in ("us", "asx"):
          return jsonify({"ok": False, "error": 'market must be "us" or "asx"'}), 400
      if not raw.strip():
          return jsonify({"ok": False, "error": "Enter a ticker symbol."}), 400

      symbol = normalize_ticker(raw, market)
      try:
          payload = events_service.fetch_events_panel(symbol)
      except ValueError as e:
          msg = str(e)
          if "FINNHUB_API_KEY" in msg or "Invalid Finnhub" in msg:
              code = 503
          elif "rate limit" in msg.lower():
              code = 429
          else:
              code = 502
          return jsonify({"ok": False, "error": msg, "symbol": symbol}), code

      return jsonify({"ok": True, "market": market, "range": range_key, **payload})

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
      return jsonify({"ok": True, **data})
