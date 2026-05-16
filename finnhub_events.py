"""Finnhub earnings calendar."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from finnhub_client import finnhub_get, finnhub_symbol


def _num(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fmt_eps(val: float | None) -> str | None:
    if val is None:
        return None
    return f"{val:.2f}"


def fetch_earnings_calendar(
    from_d: date, to_d: date, symbol: str | None = None
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "from": from_d.isoformat(),
        "to": to_d.isoformat(),
    }
    if symbol:
        params["symbol"] = finnhub_symbol(symbol)

    raw = finnhub_get("/calendar/earnings", params)
    rows = raw.get("earningsCalendar") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []

    today = date.today()
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = (row.get("symbol") or "").strip().upper()
        d_str = (row.get("date") or "").strip()
        if not sym or not d_str:
            continue
        try:
            ev = date.fromisoformat(d_str[:10])
        except ValueError:
            continue

        eps_est = _num(row.get("epsEstimate") or row.get("epsEstimated"))
        eps_prev = _num(
            row.get("epsPrevious")
            or row.get("epsPrev")
            or row.get("epsActual")
        )
        days = (ev - today).days

        out.append(
            {
                "symbol": sym,
                "date": ev.isoformat(),
                "eps_estimate": _fmt_eps(eps_est),
                "eps_previous": _fmt_eps(eps_prev),
                "days_until": days,
                "soon": 0 <= days <= 7,
                "past": days < 0,
                "hour": row.get("hour") or "",
            }
        )

    out.sort(key=lambda x: (x["date"], x["symbol"]))
    return out


def upcoming_earnings_for_symbols(
    symbols: list[str], *, horizon_days: int = 90
) -> list[dict[str, Any]]:
    today = date.today()
    end = today + timedelta(days=horizon_days)
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []

    for sym in symbols:
        fh = finnhub_symbol(sym)
        if not fh:
            continue
        try:
            rows = fetch_earnings_calendar(today, end, fh)
        except ValueError:
            raise
        except Exception:
            continue
        for row in rows:
            key = (row["symbol"], row["date"])
            if key in seen:
                continue
            seen.add(key)
            if not row["past"]:
                merged.append(row)

    merged.sort(key=lambda x: (x["date"], x["symbol"]))
    return merged


def historical_earnings_for_symbol(
    symbol: str, from_d: date, to_d: date
) -> list[dict[str, Any]]:
    rows = fetch_earnings_calendar(from_d, to_d, symbol)
    return [r for r in rows if r["past"] or r["days_until"] <= 0]
