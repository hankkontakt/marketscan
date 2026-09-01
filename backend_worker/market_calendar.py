"""Venue-aware trading calendar (Ultimate Rebuild v3, Phase 4).

Trading-day truth per MIC, not per country: a quote dated on a Swedish
holiday, a US early close or a UK bank holiday is stale or suspicious.

Data quality is explicit per venue:
- ``VERIFIED``   — holidays taken from exchange/market-hour sources with URLs
                  recorded in ``sources`` (2026 verified this session).
- ``DOCUMENTED`` — well-known core holidays, no source fetched; treat as best
                  effort.
- ``WEEKEND_ONLY`` — holiday set unknown; only Sat/Sun are closed. Stale
                  detection must not over-trust these venues.

Half days are trading days (a session exists); ``is_half_day`` reports the
reduced session separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

MIC_XSTO = "XSTO"
MIC_XHEL = "XHEL"
MIC_XCSE = "XCSE"
MIC_XOSL = "XOSL"
MIC_XETR = "XETR"
MIC_XWAR = "XWAR"
MIC_XLON = "XLON"
MIC_XTKS = "XTKS"
MIC_XTSE = "XTSE"
MIC_XASX = "XASX"
MIC_XNAS = "XNAS"

QUALITY_VERIFIED = "VERIFIED"
QUALITY_DOCUMENTED = "DOCUMENTED"
QUALITY_WEEKEND_ONLY = "WEEKEND_ONLY"


def _d(year: int, month: int, day: int) -> date:
    return date(year, month, day)


# Verified 2026 holiday sets (sources in the VenueCalendar entries below).
_CLOSED_2026_XSTO = frozenset({
    _d(2026, 1, 1), _d(2026, 1, 6), _d(2026, 4, 3), _d(2026, 4, 6),
    _d(2026, 5, 1), _d(2026, 5, 14), _d(2026, 6, 19),
    _d(2026, 12, 24), _d(2026, 12, 25), _d(2026, 12, 31),
})
_HALF_2026_XSTO = frozenset({
    _d(2026, 1, 5), _d(2026, 4, 2), _d(2026, 4, 30), _d(2026, 5, 13), _d(2026, 10, 30),
})
_CLOSED_2026_XCSE = frozenset({
    _d(2026, 1, 1), _d(2026, 4, 2), _d(2026, 4, 3), _d(2026, 4, 6),
    _d(2026, 5, 14), _d(2026, 5, 15), _d(2026, 5, 25), _d(2026, 6, 5),
    _d(2026, 12, 24), _d(2026, 12, 25), _d(2026, 12, 31),
})
_CLOSED_2026_XOSL = frozenset({
    _d(2026, 1, 1), _d(2026, 4, 2), _d(2026, 4, 3), _d(2026, 4, 6),
    _d(2026, 5, 1), _d(2026, 5, 14), _d(2026, 5, 25),
    _d(2026, 12, 24), _d(2026, 12, 25), _d(2026, 12, 31),
})
_CLOSED_2026_XNAS = frozenset({
    _d(2026, 1, 1), _d(2026, 1, 19), _d(2026, 2, 16), _d(2026, 4, 3),
    _d(2026, 5, 25), _d(2026, 6, 19), _d(2026, 7, 3), _d(2026, 9, 7),
    _d(2026, 11, 26), _d(2026, 12, 25),
})
_HALF_2026_XNAS = frozenset({_d(2026, 11, 27), _d(2026, 12, 24)})
_CLOSED_2026_XLON = frozenset({
    _d(2026, 1, 1), _d(2026, 4, 3), _d(2026, 4, 6), _d(2026, 5, 4),
    _d(2026, 5, 25), _d(2026, 8, 31), _d(2026, 12, 25), _d(2026, 12, 28),
})
_HALF_2026_XLON = frozenset({_d(2026, 12, 24), _d(2026, 12, 31)})
_CLOSED_2026_XETR = frozenset({
    _d(2026, 1, 1), _d(2026, 4, 3), _d(2026, 4, 6), _d(2026, 5, 1),
    _d(2026, 5, 14), _d(2026, 5, 25), _d(2026, 10, 3),
    _d(2026, 12, 24), _d(2026, 12, 25), _d(2026, 12, 31),
})


@dataclass(frozen=True)
class VenueCalendar:
    mic: str
    timezone: str
    closed_days: frozenset[date]
    half_days: frozenset[date]
    quality: str
    sources: tuple[str, ...]


VENUE_CALENDARS: dict[str, VenueCalendar] = {
    MIC_XSTO: VenueCalendar(
        MIC_XSTO, "Europe/Stockholm", _CLOSED_2026_XSTO, _HALF_2026_XSTO,
        QUALITY_VERIFIED,
        ("https://www.nasdaq.com/european-market-activity/trading-hours", "https://markethours.io/market-holidays/sto"),
    ),
    MIC_XHEL: VenueCalendar(
        MIC_XHEL, "Europe/Helsinki", _CLOSED_2026_XSTO, _HALF_2026_XSTO,
        QUALITY_VERIFIED,
        ("https://www.nasdaq.com/european-market-activity/trading-hours",),
    ),
    MIC_XCSE: VenueCalendar(
        MIC_XCSE, "Europe/Copenhagen", _CLOSED_2026_XCSE, frozenset(),
        QUALITY_VERIFIED,
        ("https://www.nasdaq.com/european-market-activity/trading-hours",),
    ),
    MIC_XOSL: VenueCalendar(
        MIC_XOSL, "Europe/Oslo", _CLOSED_2026_XOSL, frozenset(),
        QUALITY_VERIFIED,
        ("https://www.nasdaq.com/european-market-activity/trading-hours",),
    ),
    MIC_XNAS: VenueCalendar(
        MIC_XNAS, "America/New_York", _CLOSED_2026_XNAS, _HALF_2026_XNAS,
        QUALITY_VERIFIED,
        ("https://www.nyse.com/markets/hours-calendars", "https://www.nasdaq.com/market-activity/stock-market-holiday-schedule"),
    ),
    MIC_XLON: VenueCalendar(
        MIC_XLON, "Europe/London", _CLOSED_2026_XLON, _HALF_2026_XLON,
        QUALITY_VERIFIED,
        ("https://markethours.io/market-holidays/lse", "https://www.londonstockexchange.com/equities-trading/business-days"),
    ),
    MIC_XETR: VenueCalendar(
        MIC_XETR, "Europe/Berlin", _CLOSED_2026_XETR, frozenset(),
        QUALITY_DOCUMENTED, (),
    ),
    MIC_XWAR: VenueCalendar(MIC_XWAR, "Europe/Warsaw", frozenset(), frozenset(), QUALITY_WEEKEND_ONLY, ()),
    MIC_XTKS: VenueCalendar(MIC_XTKS, "Asia/Tokyo", frozenset(), frozenset(), QUALITY_WEEKEND_ONLY, ()),
    MIC_XTSE: VenueCalendar(MIC_XTSE, "America/Toronto", frozenset(), frozenset(), QUALITY_WEEKEND_ONLY, ()),
    MIC_XASX: VenueCalendar(MIC_XASX, "Australia/Sydney", frozenset(), frozenset(), QUALITY_WEEKEND_ONLY, ()),
}


def venue_calendar(mic: str) -> VenueCalendar:
    return VENUE_CALENDARS.get(mic.upper().strip(), VENUE_CALENDARS[MIC_XNAS])


def is_trading_day(mic: str, day: date) -> bool:
    """True when a session exists on ``day`` (half days count as sessions)."""
    calendar = venue_calendar(mic)
    if day.weekday() >= 5:
        return False
    return day not in calendar.closed_days


def is_half_day(mic: str, day: date) -> bool:
    return day in venue_calendar(mic).half_days


def next_trading_day(mic: str, day: date) -> date:
    candidate = day + timedelta(days=1)
    while not is_trading_day(mic, candidate):
        candidate += timedelta(days=1)
    return candidate


def previous_trading_day(mic: str, day: date) -> date:
    candidate = day - timedelta(days=1)
    while not is_trading_day(mic, candidate):
        candidate -= timedelta(days=1)
    return candidate


def trading_days_between(mic: str, start: date, end: date) -> int:
    """Number of trading days in [start, end] inclusive."""
    total = 0
    cursor_day = start
    while cursor_day <= end:
        if is_trading_day(mic, cursor_day):
            total += 1
        cursor_day += timedelta(days=1)
    return total