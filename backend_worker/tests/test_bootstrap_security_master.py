"""Security Master bootstrap policy tests — venue resolution and initial state."""
from datetime import datetime, timezone

import pytest

from backend_worker.bootstrap_security_master import (
    _effective_action_state,
    ensure_listing,
    listing_identity,
    resolve_venue,
)
from backend_worker.decision_manifests import ManifestInvariantError


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [("VOLV-B.ST", ("XSTO", "SEK")), ("SAP.DE", ("XETR", "EUR")), ("7203.T", ("XTKS", "JPY"))],
)
def test_listing_identity_uses_verified_exchange_suffixes(ticker, expected):
    assert listing_identity(ticker) == expected


def test_listing_identity_rejects_unknown_exchange():
    with pytest.raises(ManifestInvariantError, match="No verified MIC"):
        listing_identity("CPRX")


def test_resolve_venue_verifies_suffix_tickers():
    venue = resolve_venue("VOLV-B.ST")
    assert (venue.mic, venue.currency, venue.verified) == ("XSTO", "SEK", True)


def test_resolve_venue_applies_us_default_policy_for_suffixless_tickers():
    # Audited exception policy: suffix-less legacy tickers are US-listed under
    # a default MIC; identity exists but tradability stays UNKNOWN (NO_SIGNAL).
    venue = resolve_venue("CPRX")
    assert (venue.mic, venue.currency, venue.verified) == ("XNAS", "USD", False)


class ScriptedCursor:
    """Minimal cursor double: matches SQL by substring, records inserts."""

    def __init__(self, script):
        self._script = script  # list of (substring, result_row_or_None)
        self.inserts = []

    def execute(self, sql, params=None):
        for substring, result in self._script:
            if substring in sql:
                self._last = result
                break
        else:
            raise AssertionError(f"unexpected SQL: {sql}")
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql:
            self.inserts.append((sql, params))

    def fetchone(self):
        return self._last


def test_effective_action_state_returns_merged_for_cprx():
    cursor = ScriptedCursor([
        ("FROM public.corporate_actions", {"action_type": "MERGED", "effective_at": datetime(2026, 7, 15, tzinfo=timezone.utc)}),
    ])
    state = _effective_action_state(cursor, "CPRX", "XNAS")
    assert state == ("MERGED", None)


def test_ensure_listing_skips_existing_listing():
    cursor = ScriptedCursor([("FROM public.listings", {"listing_id": "existing"})])
    assert ensure_listing(cursor, {"ticker": "VOLV-B.ST", "name": "Volvo AB", "country": "SE"}) is False


def test_ensure_listing_creates_merged_listing_when_corporate_action_is_effective():
    cursor = ScriptedCursor([
        ("FROM public.listings", None),
        ("FROM public.corporate_actions", {"action_type": "MERGED", "effective_at": datetime(2026, 7, 15, tzinfo=timezone.utc)}),
        ("FROM public.issuers", None),
        ("INSERT INTO public.issuers", {"issuer_id": "issuer-1"}),
        ("FROM public.securities", None),
        ("INSERT INTO public.securities", {"security_id": "security-1"}),
        ("INSERT INTO public.listings", None),
    ])
    created = ensure_listing(cursor, {"ticker": "CPRX", "name": "Catalyst Pharmaceuticals, Inc.", "country": "US"})
    assert created is True
    listing_sql, params = cursor.inserts[-1]
    assert "INSERT INTO public.listings" in listing_sql
    assert params[4] == "MERGED"


def test_ensure_listing_creates_unknown_listing_for_us_default_policy():
    cursor = ScriptedCursor([
        ("FROM public.listings", None),
        ("FROM public.corporate_actions", None),
        ("FROM public.issuers", None),
        ("INSERT INTO public.issuers", {"issuer_id": "issuer-2"}),
        ("FROM public.securities", None),
        ("INSERT INTO public.securities", {"security_id": "security-2"}),
        ("INSERT INTO public.listings", None),
    ])
    created = ensure_listing(cursor, {"ticker": "MSFT", "name": "Microsoft Corporation", "country": "US"})
    assert created is True
    _, params = cursor.inserts[-1]
    assert (params[1], params[3], params[4]) == ("XNAS", "USD", "UNKNOWN")