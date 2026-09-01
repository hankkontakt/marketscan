"""Venue-aware trading calendar tests (Phase 4) — verified 2026 dates."""
from datetime import date

from backend_worker.market_calendar import (
    is_half_day,
    is_trading_day,
    next_trading_day,
    previous_trading_day,
    trading_days_between,
    venue_calendar,
    QUALITY_VERIFIED,
    QUALITY_WEEKEND_ONLY,
    MIC_XNAS,
    MIC_XSTO,
    MIC_XLON,
)


def test_swedish_holidays_2026_are_closed():
    # Midsummer Eve 2026-06-19 (Friday) — verified closed (markethours.io + nasdaq.com)
    assert is_trading_day(MIC_XSTO, date(2026, 6, 19)) is False
    # Epiphany 2026-01-06 (Tuesday)
    assert is_trading_day(MIC_XSTO, date(2026, 1, 6)) is False
    # Ascension Day 2026-05-14 (Thursday)
    assert is_trading_day(MIC_XSTO, date(2026, 5, 14)) is False
    # Christmas Eve 2026-12-24 (Thursday)
    assert is_trading_day(MIC_XSTO, date(2026, 12, 24)) is False


def test_swedish_half_days_are_still_trading_days():
    # Epiphany Eve 2026-01-05: half day, but a session exists
    assert is_half_day(MIC_XSTO, date(2026, 1, 5)) is True
    assert is_trading_day(MIC_XSTO, date(2026, 1, 5)) is True
    # All Saints' Eve 2026-10-30
    assert is_half_day(MIC_XSTO, date(2026, 10, 30)) is True
    assert is_trading_day(MIC_XSTO, date(2026, 10, 30)) is True


def test_us_holidays_2026_are_closed():
    # Labor Day 2026-09-07 (Monday)
    assert is_trading_day(MIC_XNAS, date(2026, 9, 7)) is False
    # Independence Day observed 2026-07-03 (Friday; Jul 4 is Saturday)
    assert is_trading_day(MIC_XNAS, date(2026, 7, 3)) is False
    # Juneteenth 2026-06-19 (Friday)
    assert is_trading_day(MIC_XNAS, date(2026, 6, 19)) is False


def test_us_early_close_days_are_trading_days():
    assert is_half_day(MIC_XNAS, date(2026, 11, 27)) is True
    assert is_trading_day(MIC_XNAS, date(2026, 11, 27)) is True
    assert is_half_day(MIC_XNAS, date(2026, 12, 24)) is True


def test_london_holidays_2026_are_closed():
    # Boxing Day observed 2026-12-28 (Monday)
    assert is_trading_day(MIC_XLON, date(2026, 12, 28)) is False
    # Summer Bank Holiday 2026-08-31 (Monday)
    assert is_trading_day(MIC_XLON, date(2026, 8, 31)) is False
    # LSE does NOT close on May 1 (Labour Day) — continental exchanges do
    assert is_trading_day(MIC_XLON, date(2026, 5, 1)) is True


def test_weekends_are_always_closed():
    assert is_trading_day(MIC_XNAS, date(2026, 9, 5)) is False  # Saturday
    assert is_trading_day(MIC_XSTO, date(2026, 9, 6)) is False  # Sunday


def test_regular_monday_is_a_trading_day():
    assert is_trading_day(MIC_XNAS, date(2026, 9, 8)) is True  # Tuesday after Labor Day
    assert is_trading_day(MIC_XSTO, date(2026, 5, 4)) is True  # Monday after May 1


def test_next_and_previous_trading_day():
    # Friday 2026-09-04 -> next trading day is Monday 2026-09-07? NO — Labor Day.
    # Thursday 2026-09-03 -> next is Friday 2026-09-04.
    assert next_trading_day(MIC_XNAS, date(2026, 9, 3)) == date(2026, 9, 4)
    # Thursday 2026-09-03 -> next after that skips Labor Day weekend.
    assert next_trading_day(MIC_XNAS, date(2026, 9, 4)) == date(2026, 9, 8)
    # Monday 2026-09-07 (holiday) -> previous trading day is Friday 2026-09-04.
    assert previous_trading_day(MIC_XNAS, date(2026, 9, 7)) == date(2026, 9, 4)


def test_trading_days_between_counts_only_sessions():
    # 2026-09-03 (Thu) .. 2026-09-08 (Tue) = Thu, Fri, [Mon closed], Tue = 3
    assert trading_days_between(MIC_XNAS, date(2026, 9, 3), date(2026, 9, 8)) == 3


def test_quality_flags_are_explicit():
    assert venue_calendar(MIC_XSTO).quality == QUALITY_VERIFIED
    assert venue_calendar(MIC_XNAS).quality == QUALITY_VERIFIED
    # Unverified venues are WEEKEND_ONLY and must not be over-trusted
    assert venue_calendar("XTKS").quality == QUALITY_WEEKEND_ONLY
    assert venue_calendar("XTKS").closed_days == frozenset()


def test_unknown_mic_falls_back_to_us_calendar():
    assert venue_calendar("ZZZZ").mic == MIC_XNAS