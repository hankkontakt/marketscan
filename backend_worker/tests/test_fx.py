"""FX normalization contract tests (Phase 4)."""
from datetime import date

import pytest

from backend_worker.fx import FxRate, rate_to_sek


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self._sql = None

    def execute(self, sql, params=None):
        self._sql = (sql, params)

    def fetchone(self):
        return self._rows


def test_sek_is_identity_rate_without_database():
    cursor = FakeCursor([])
    result = rate_to_sek("SEK", date(2026, 9, 1), cursor)
    assert result == FxRate(rate=1.0, rate_date=date(2026, 9, 1), source="identity")
    assert cursor._sql is None  # no DB hit


def test_exact_date_rate_is_resolved():
    cursor = FakeCursor({"rate": 9.58973, "rate_date": date(2026, 9, 1), "source": "ecb-eurofxref-2026-09-01"})
    result = rate_to_sek("USD", date(2026, 9, 1), cursor)
    assert result.rate == pytest.approx(9.58973)
    assert result.source == "ecb-eurofxref-2026-09-01"


def test_nearest_prior_rate_is_documented_fallback():
    cursor = FakeCursor({"rate": 9.4, "rate_date": date(2026, 8, 28), "source": "ecb-eurofxref-2026-08-28"})
    result = rate_to_sek("USD", date(2026, 9, 1), cursor)
    assert result.rate == pytest.approx(9.4)
    assert result.rate_date == date(2026, 8, 28)


def test_missing_rate_returns_none_not_a_guess():
    cursor = FakeCursor(None)
    assert rate_to_sek("USD", date(2026, 9, 1), cursor) is None


def test_unknown_currency_returns_none():
    cursor = FakeCursor(None)
    assert rate_to_sek("XXX", date(2026, 9, 1), cursor) is None
    assert rate_to_sek("", date(2026, 9, 1), cursor) is None


def test_query_uses_exact_and_prior_lookup():
    cursor = FakeCursor(None)
    rate_to_sek("USD", date(2026, 9, 1), cursor)
    sql, params = cursor._sql
    assert "rate_date <= %s" in sql
    assert params == ("USD", date(2026, 9, 1))