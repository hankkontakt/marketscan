"""Controlled bootstrap of Security Master rows from the legacy ticker universe.

The legacy source has no ISIN/FIGI and no per-ticker venue field, so identity
resolution follows an explicit, documented policy:

- Verified exchange suffixes (``.ST``/``.DE``/...) map to a single MIC+currency
  and produce ``ACTIVE`` listings.
- Suffix-less tickers are treated as US-listed under the audited default policy
  (XNAS, USD) but with tradability state ``UNKNOWN``: they resolve to a
  canonical ``listing_id`` yet publish ``NO_SIGNAL`` until per-venue
  verification lands (plan section 6: UNKNOWN => NO_SIGNAL).
- Effective corporate actions override the initial state (e.g. CPRX is MERGED
  after the Angelini Pharma acquisition closed 2026-07-15).

The tool is safe to rerun: an existing listing (active or closed) for a
(MIC, ticker) pair is never duplicated.
"""
from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend_worker.decision_manifests import ManifestInvariantError

logger = logging.getLogger(__name__)

_EXCHANGE_BY_SUFFIX = {
    ".ST": ("XSTO", "SEK"), ".HE": ("XHEL", "EUR"), ".CO": ("XCSE", "DKK"),
    ".OL": ("XOSL", "NOK"), ".DE": ("XETR", "EUR"), ".WA": ("XWAR", "PLN"),
    ".T": ("XTKS", "JPY"), ".L": ("XLON", "GBP"), ".TO": ("XTSE", "CAD"),
    ".AX": ("XASX", "AUD"),
}

# Audited default policy for suffix-less (US) tickers. The legacy universe has
# no per-ticker venue field; a default MIC is assigned for identity only and
# the listing is published UNKNOWN until a venue source contract exists.
_US_DEFAULT_MIC = "XNAS"
_US_DEFAULT_CURRENCY = "USD"

# Corporate action types that map directly onto a listing tradability state.
_STATE_ACTION_TYPES = {
    "ACQUISITION_PENDING", "MERGED", "DELISTING_PENDING", "DELISTED",
    "HALTED", "SUSPENDED", "BANKRUPT",
}


@dataclass(frozen=True)
class VenueIdentity:
    mic: str
    currency: str
    verified: bool


def listing_identity(ticker: str) -> tuple[str, str]:
    """Return only a known exchange identity; unknown suffixes are a hard stop."""
    upper_ticker = ticker.upper().strip()
    for suffix, identity in sorted(_EXCHANGE_BY_SUFFIX.items(), key=lambda item: len(item[0]), reverse=True):
        if upper_ticker.endswith(suffix):
            return identity
    raise ManifestInvariantError(f"No verified MIC/currency mapping exists for ticker {ticker}")


def resolve_venue(ticker: str) -> VenueIdentity:
    """Resolve a legacy ticker to a venue identity under the audited policy."""
    try:
        mic, currency = listing_identity(ticker)
        return VenueIdentity(mic, currency, verified=True)
    except ManifestInvariantError:
        return VenueIdentity(_US_DEFAULT_MIC, _US_DEFAULT_CURRENCY, verified=False)


def _country(value: Any) -> str | None:
    country = str(value or "").upper().strip()
    return country if len(country) == 2 and country.isalpha() else None


def _effective_action_state(cursor: Any, ticker: str, mic: str) -> tuple[str, str | None] | None:
    """Return (state, valid_to) for the most recent EFFECTIVE corporate action."""
    cursor.execute(
        """
        SELECT action_type, effective_at
        FROM public.corporate_actions
        WHERE mic = %s AND upper(ticker) = upper(%s)
          AND status = 'EFFECTIVE'
          AND (effective_at IS NULL OR effective_at <= now())
        ORDER BY effective_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (mic, ticker),
    )
    row = cursor.fetchone()
    if row is None or row["action_type"] not in _STATE_ACTION_TYPES:
        return None
    return (row["action_type"], None)


def ensure_listing(cursor: Any, row: Mapping[str, Any]) -> bool:
    """Create issuer/security/listing only when no canonical listing exists.

    The initial tradability state follows the audited policy: ACTIVE for
    verified venues, UNKNOWN for the US default, or the state implied by the
    most recent effective corporate action.
    """
    ticker = str(row["ticker"]).upper().strip()
    legal_name = str(row.get("name") or "").strip()
    if not legal_name:
        raise ManifestInvariantError(f"Missing legal name for {ticker}")
    venue = resolve_venue(ticker)
    cursor.execute(
        "SELECT 1 FROM public.listings WHERE mic = %s AND upper(ticker) = %s LIMIT 1",
        (venue.mic, ticker),
    )
    if cursor.fetchone():
        return False
    action_state = _effective_action_state(cursor, ticker, venue.mic)
    state = action_state[0] if action_state else ("ACTIVE" if venue.verified else "UNKNOWN")
    domicile_country = _country(row.get("country"))
    cursor.execute(
        """
        SELECT issuer_id FROM public.issuers
        WHERE lower(legal_name) = lower(%s) AND domicile_country IS NOT DISTINCT FROM %s
        ORDER BY created_at LIMIT 1
        """,
        (legal_name, domicile_country),
    )
    existing_issuer = cursor.fetchone()
    if existing_issuer:
        issuer_id = existing_issuer["issuer_id"]
    else:
        cursor.execute(
            "INSERT INTO public.issuers (legal_name, domicile_country) VALUES (%s, %s) RETURNING issuer_id",
            (legal_name, domicile_country),
        )
        issuer_id = cursor.fetchone()["issuer_id"]
    cursor.execute(
        "SELECT security_id FROM public.securities WHERE issuer_id = %s AND share_class = 'COMMON' ORDER BY created_at LIMIT 1",
        (issuer_id,),
    )
    existing_security = cursor.fetchone()
    if existing_security:
        security_id = existing_security["security_id"]
    else:
        cursor.execute(
            "INSERT INTO public.securities (issuer_id, share_class) VALUES (%s, 'COMMON') RETURNING security_id",
            (issuer_id,),
        )
        security_id = cursor.fetchone()["security_id"]
    cursor.execute(
        """
        INSERT INTO public.listings (security_id, mic, ticker, currency, state)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (security_id, venue.mic, ticker, venue.currency, state),
    )
    return True


def apply_effective_corporate_actions(cursor: Any) -> list[tuple[str, str, str, str]]:
    """Flip already-bootstrapped listings according to effective actions."""
    cursor.execute("SELECT * FROM public.apply_effective_corporate_actions()")
    return [tuple(row.values()) for row in cursor.fetchall()]


def bootstrap_from_legacy(cursor: Any) -> tuple[int, int]:
    cursor.execute("SELECT ticker, name, country FROM public.scan_results ORDER BY ticker")
    rows = list(cursor.fetchall())
    if not rows:
        raise ManifestInvariantError("scan_results is empty; Security Master bootstrap has no source universe")
    created = sum(ensure_listing(cursor, row) for row in rows)
    return created, len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap canonical Security Master listings from scan_results")
    parser.add_argument("--apply", action="store_true", help="Persist rows; without this flag the command only validates the source universe")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ManifestInvariantError("DATABASE_URL is required")
    import psycopg2
    from psycopg2.extras import RealDictCursor
    with psycopg2.connect(database_url) as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            if not args.apply:
                cursor.execute("SELECT ticker FROM public.scan_results ORDER BY ticker")
                rows = list(cursor.fetchall())
                for row in rows:
                    resolve_venue(str(row["ticker"]))
                logger.info("Validated %d legacy tickers; rerun with --apply to create Security Master rows", len(rows))
                return
            created, total = bootstrap_from_legacy(cursor)
            transitions = apply_effective_corporate_actions(cursor)
            logger.info(
                "Security Master bootstrap complete: %d created, %d source tickers, %d corporate-action transitions",
                created, total, len(transitions),
            )
            for transition in transitions:
                logger.info("  %s/%s: %s -> %s", transition[0], transition[1], transition[2], transition[3])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()