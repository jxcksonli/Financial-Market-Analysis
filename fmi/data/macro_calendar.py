"""
US macro event calendar (hardcoded 2025–2026 schedules).

Sources: Federal Reserve FOMC calendar, BLS CPI release schedule, BLS NFP (first Friday).
"""

from __future__ import annotations

from datetime import date
from typing import Any

# FOMC statement / decision day (second day of meeting when applicable)
FOMC_DATES: list[tuple[str, str]] = [
    ("2025-01-29", "FOMC decision"),
    ("2025-03-19", "FOMC decision"),
    ("2025-05-07", "FOMC decision"),
    ("2025-06-18", "FOMC decision"),
    ("2025-07-30", "FOMC decision"),
    ("2025-09-17", "FOMC decision"),
    ("2025-10-29", "FOMC decision"),
    ("2025-12-10", "FOMC decision"),
    ("2026-01-28", "FOMC decision"),
    ("2026-03-18", "FOMC decision"),
    ("2026-04-29", "FOMC decision"),
    ("2026-06-17", "FOMC decision"),
    ("2026-07-29", "FOMC decision"),
    ("2026-09-16", "FOMC decision"),
    ("2026-11-04", "FOMC decision"),
    ("2026-12-16", "FOMC decision"),
]

CPI_DATES: list[tuple[str, str]] = [
    ("2025-01-15", "US CPI release"),
    ("2025-02-12", "US CPI release"),
    ("2025-03-12", "US CPI release"),
    ("2025-04-10", "US CPI release"),
    ("2025-05-13", "US CPI release"),
    ("2025-06-11", "US CPI release"),
    ("2025-07-15", "US CPI release"),
    ("2025-08-12", "US CPI release"),
    ("2025-09-11", "US CPI release"),
    ("2025-10-15", "US CPI release"),
    ("2025-11-13", "US CPI release"),
    ("2025-12-10", "US CPI release"),
    ("2026-01-14", "US CPI release"),
    ("2026-02-11", "US CPI release"),
    ("2026-03-11", "US CPI release"),
    ("2026-04-14", "US CPI release"),
    ("2026-05-12", "US CPI release"),
    ("2026-06-10", "US CPI release"),
    ("2026-07-14", "US CPI release"),
    ("2026-08-12", "US CPI release"),
    ("2026-09-10", "US CPI release"),
    ("2026-10-14", "US CPI release"),
    ("2026-11-12", "US CPI release"),
    ("2026-12-10", "US CPI release"),
]

NFP_DATES: list[tuple[str, str]] = [
    ("2025-01-10", "US NFP (jobs report)"),
    ("2025-02-07", "US NFP (jobs report)"),
    ("2025-03-07", "US NFP (jobs report)"),
    ("2025-04-04", "US NFP (jobs report)"),
    ("2025-05-02", "US NFP (jobs report)"),
    ("2025-06-06", "US NFP (jobs report)"),
    ("2025-07-03", "US NFP (jobs report)"),
    ("2025-08-01", "US NFP (jobs report)"),
    ("2025-09-05", "US NFP (jobs report)"),
    ("2025-10-03", "US NFP (jobs report)"),
    ("2025-11-07", "US NFP (jobs report)"),
    ("2025-12-05", "US NFP (jobs report)"),
    ("2026-01-09", "US NFP (jobs report)"),
    ("2026-02-06", "US NFP (jobs report)"),
    ("2026-03-06", "US NFP (jobs report)"),
    ("2026-04-03", "US NFP (jobs report)"),
    ("2026-05-01", "US NFP (jobs report)"),
    ("2026-06-05", "US NFP (jobs report)"),
    ("2026-07-02", "US NFP (jobs report)"),
    ("2026-08-07", "US NFP (jobs report)"),
    ("2026-09-04", "US NFP (jobs report)"),
    ("2026-10-02", "US NFP (jobs report)"),
    ("2026-11-06", "US NFP (jobs report)"),
    ("2026-12-04", "US NFP (jobs report)"),
]

_MACRO_RAW: list[tuple[str, str, str]] = (
    [("fed", d, t) for d, t in FOMC_DATES]
    + [("cpi", d, t) for d, t in CPI_DATES]
    + [("nfp", d, t) for d, t in NFP_DATES]
)


def _days_until(event: date, today: date) -> int:
    return (event - today).days


def _macro_row(kind: str, iso: str, title: str, today: date) -> dict[str, Any]:
    ev = date.fromisoformat(iso)
    days = _days_until(ev, today)
    return {
        "kind": kind,
        "date": iso,
        "title": title,
        "days_until": days,
        "soon": 0 <= days <= 7,
        "past": days < 0,
    }


def macro_events_between(from_d: date, to_d: date) -> list[dict[str, Any]]:
    today = date.today()
    out: list[dict[str, Any]] = []
    for kind, iso, title in _MACRO_RAW:
        ev = date.fromisoformat(iso)
        if from_d <= ev <= to_d:
            out.append(_macro_row(kind, iso, title, today))
    out.sort(key=lambda x: x["date"])
    return out


def upcoming_macro(*, horizon_days: int = 120) -> list[dict[str, Any]]:
    today = date.today()
    end = today.fromordinal(today.toordinal() + horizon_days)
    rows = macro_events_between(today, end)
    return [r for r in rows if not r["past"]]
