"""
Phase 1 Verification Tests: Security Master v2
- CPRX acquired fixture hard tradability gate
- Dual-listing multi-venue mapping to same issuer
- Ticker resolution and temporal mapping
- UNKNOWN state NO_SIGNAL handling
- 100% active universe resolution
"""
import pytest
from backend_worker.security_master.models import SecurityState, CorporateActionType, CorporateAction
from backend_worker.security_master.resolver import SecurityMasterResolver
from backend_worker.security_master.backfill import build_benchmark_security_master

def test_cprx_acquired_regression_gate():
    resolver = build_benchmark_security_master()
    is_tradable, state, expl = resolver.enforce_tradability_gate("CPRX")
    assert is_tradable is False
    assert state in (SecurityState.MERGED, SecurityState.DELISTED)
    assert "quarantined" in expl.lower() or "inactive" in expl.lower()

def test_active_stock_tradability_gate():
    resolver = build_benchmark_security_master()
    is_tradable, state, expl = resolver.enforce_tradability_gate("2330.TW")
    assert is_tradable is True
    assert state == SecurityState.ACTIVE

    is_tradable_halo, state_halo, _ = resolver.enforce_tradability_gate("HALO")
    assert is_tradable_halo is True
    assert state_halo == SecurityState.ACTIVE

def test_unknown_ticker_gate():
    resolver = build_benchmark_security_master()
    is_tradable, state, expl = resolver.enforce_tradability_gate("NON_EXISTENT_TICKER_XYZ")
    assert is_tradable is False
    assert state == SecurityState.UNKNOWN
    assert "NO_SIGNAL" in expl

def test_dual_listing_hierarchy():
    resolver = SecurityMasterResolver()
    issuer = resolver.register_issuer(legal_name="Taiwan Semiconductor Manufacturing Co", country="TW")
    security = resolver.register_security(issuer_id=issuer.issuer_id, isin="US8740391003")

    listing_tw = resolver.register_listing(
        security_id=security.security_id,
        mic="XTAI",
        ticker="2330.TW",
        currency="TWD",
        is_primary=True
    )
    listing_adr = resolver.register_listing(
        security_id=security.security_id,
        mic="XNYS",
        ticker="TSM",
        currency="USD",
        is_primary=False
    )

    # Separate listings, same underlying security and issuer
    assert listing_tw.listing_id != listing_adr.listing_id
    assert listing_tw.security_id == listing_adr.security_id == security.security_id
    assert resolver.resolve_listing_by_ticker("2330.TW").currency == "TWD"
    assert resolver.resolve_listing_by_ticker("TSM").currency == "USD"

def test_benchmark_cohort_all_resolved():
    resolver = build_benchmark_security_master()
    active_count = 0
    inactive_count = 0
    for ticker in ["2330.TW", "6861.T", "AOF.DE", "HALO", "PLTR", "APP", "GOOGL", "ASML.AS",
                   "BIOG-B.ST", "MSAB-B.ST", "TXT.WA", "PUUILO.HE", "HARVIA.HE", "NCAB.ST",
                   "ASAN", "BOUV.OL", "OEM-B.ST", "DIOS.ST", "AVGO", "CPRX", "SBB-B.ST"]:
        tradable, state, _ = resolver.enforce_tradability_gate(ticker)
        if ticker == "CPRX":
            assert tradable is False
            inactive_count += 1
        else:
            assert tradable is True
            assert state == SecurityState.ACTIVE
            active_count += 1

    assert active_count == 20
    assert inactive_count == 1
