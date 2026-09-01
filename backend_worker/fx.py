"""FX normalization contract (Ultimate Rebuild v3, Phase 4).

Every currency conversion must resolve to a dated, sourced rate from
``public.fx_rates`` (base = SEK). There is no silent approximation: an
unknown currency or a missing rate returns ``None`` and the caller must
treat the observation as quarantined, never guess.

Lookup rule: exact ``rate_date`` first; otherwise the most recent prior
rate (documented nearest-prior fallback — rates are valid until the next
publish). ``SEK`` is the identity rate without a database hit.
"""
from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

SOURCE_IDENTITY = "identity"


@dataclass(frozen=True)
class FxRate:
    rate: float
    rate_date: date
    source: str


def rate_to_sek(currency: str, as_of: date, cursor: Any) -> FxRate | None:
    """Resolve SEK-per-unit rate for ``currency`` as of ``as_of``.

    Returns ``None`` when the currency is unknown or no rate exists on or
    before ``as_of`` — the observation must be quarantined, not converted.
    """
    normalized = (currency or "").upper().strip()
    if not normalized:
        return None
    if normalized == "SEK":
        return FxRate(rate=1.0, rate_date=as_of, source=SOURCE_IDENTITY)
    cursor.execute(
        """
        SELECT rate, rate_date, source
        FROM public.fx_rates
        WHERE base_currency = 'SEK' AND quote_currency = %s AND rate_date <= %s
        ORDER BY rate_date DESC
        LIMIT 1
        """,
        (normalized, as_of),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return FxRate(rate=float(row["rate"]), rate_date=row["rate_date"], source=row["source"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a dated SEK FX rate from fx_rates")
    parser.add_argument("--currency", required=True, help="quote currency, e.g. USD")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="rate date (YYYY-MM-DD)")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    import psycopg2
    from psycopg2.extras import RealDictCursor
    with psycopg2.connect(database_url) as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            result = rate_to_sek(args.currency, date.fromisoformat(args.as_of), cursor)
    if result is None:
        print(f"No dated rate for {args.currency} as of {args.as_of} — quarantined")
        raise SystemExit(1)
    print(f"{args.currency} -> SEK {result.rate:.6f} (rate_date {result.rate_date}, source {result.source})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()