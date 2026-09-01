"""
Backfill / Seed Security Master from Benchmark Cohort & Scan Results (Phase 1)
"""
import json
from pathlib import Path
from backend_worker.security_master.models import SecurityState, CorporateActionType, CorporateAction
from backend_worker.security_master.resolver import SecurityMasterResolver
from datetime import date

def build_benchmark_security_master() -> SecurityMasterResolver:
    """Instantiate a SecurityMasterResolver seeded with the 21 benchmark cohort securities."""
    resolver = SecurityMasterResolver()
    fixture_path = Path("data/fixtures/benchmark_cohort_v1.json")
    if not fixture_path.exists():
        return resolver

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    for item in data.get("cohort", []):
        ticker = item["ticker"]
        name = item["name"]
        expected_state_str = item.get("expected_state", "ACTIVE")
        state = SecurityState(expected_state_str)

        # Derive country/currency from ticker suffix
        mic = "XNYS"
        curr = "USD"
        country = "US"
        if ticker.endswith(".ST"):
            mic = "XSTO"
            curr = "SEK"
            country = "SE"
        elif ticker.endswith(".HE"):
            mic = "XHEL"
            curr = "EUR"
            country = "FI"
        elif ticker.endswith(".OL"):
            mic = "XOSL"
            curr = "NOK"
            country = "NO"
        elif ticker.endswith(".DE"):
            mic = "XETR"
            curr = "EUR"
            country = "DE"
        elif ticker.endswith(".AS"):
            mic = "XAMS"
            curr = "EUR"
            country = "NL"
        elif ticker.endswith(".WA"):
            mic = "XWAR"
            curr = "PLN"
            country = "PL"
        elif ticker.endswith(".T"):
            mic = "XTKS"
            curr = "JPY"
            country = "JP"
        elif ticker.endswith(".TW"):
            mic = "XTAI"
            curr = "TWD"
            country = "TW"

        issuer = resolver.register_issuer(legal_name=name, country=country)
        security = resolver.register_security(issuer_id=issuer.issuer_id)
        listing = resolver.register_listing(
            security_id=security.security_id,
            mic=mic,
            ticker=ticker,
            currency=curr,
            state=state
        )

        # Record CPRX acquisition regression case
        if ticker == "CPRX":
            corp_action = CorporateAction(
                security_id=security.security_id,
                listing_id=listing.listing_id,
                action_type=CorporateActionType.MERGER_ACQUISITION,
                effective_date=date(2026, 1, 15),
                deal_terms={"type": "cash_acquisition", "status": "completed"},
                source="SEC Form 8-K"
            )
            resolver.record_corporate_action(corp_action)

    return resolver
