from datetime import datetime, timezone

import pytest

from backend_worker.decision_manifests import ManifestInvariantError
from backend_worker.decision_publication import load_publishable_rows, manifest_from_legacy_row


class ScriptedCursor:
    """Minimal cursor double for load_publishable_rows."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows


def scripted_row(**overrides):
    values = {
        "ticker": "MSFT", "entry_signal": "STARK", "low_liquidity": False,
        "listing_id": "c17f8634-8152-4b3d-bc5e-827d1863813d", "listing_state": "ACTIVE",
        "master_rank": 82.0, "master_rank_pctl": 95.0, "tier": "T1",
        "quality_z": 80.0, "value_z": 55.0, "momentum_z": 70.0,
        "analyst_z": 60.0, "tech_z": 70.0, "insider_z": 50.0,
        "catalyst_z": 50.0, "growth_z": 65.0, "pit_status": "READY",
        "trend_tech": "Upptrend", "warning_flags": [], "data_missing": [],
        "analyst_upside": 0.12, "analyst_count": 8,
    }
    values.update(overrides)
    return values


def row(**overrides):
    values = {
        "ticker": "MSFT",
        "listing_id": "c17f8634-8152-4b3d-bc5e-827d1863813d",
        "listing_state": "ACTIVE",
        "entry_signal": "STARK",
        "low_liquidity": False,
        "master_rank": 82.0,
        "master_rank_pctl": 95.0,
        "tier": "T1",
        "quality_z": 80.0,
        "value_z": 55.0,
        "momentum_z": 70.0,
        "analyst_z": 60.0,
        "tech_z": 70.0,
        "insider_z": 50.0,
        "catalyst_z": 50.0,
        "growth_z": 65.0,
        "pit_status": "READY",
        "warning_flags": [],
        "data_missing": [],
    }
    values.update(overrides)
    return values


def test_complete_active_t1_row_becomes_actionable_manifest():
    manifest = manifest_from_legacy_row(
        row(), snapshot_id="f17f8634-8152-4b3d-bc5e-827d1863813d",
        decision_time=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert manifest.is_actionable is True
    assert manifest.thesis_band == "BULLISH"
    assert manifest.data_grade == "A"


def test_stale_or_incomplete_rows_are_never_actionable():
    manifest = manifest_from_legacy_row(
        row(pit_status="STALE", entry_signal="STARK"), snapshot_id="f17f8634-8152-4b3d-bc5e-827d1863813d",
        decision_time=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert manifest.risk_state == "CRITICAL"
    assert manifest.is_actionable is False


def test_missing_security_master_mapping_stops_publication():
    with pytest.raises(ManifestInvariantError, match="Security Master mapping"):
        manifest_from_legacy_row(
            row(listing_id=None), snapshot_id="f17f8634-8152-4b3d-bc5e-827d1863813d",
            decision_time=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )


def test_inactive_listings_are_excluded_as_quarantine_not_blockers():
    rows = [
        scripted_row(ticker="MSFT", listing_state="ACTIVE"),
        scripted_row(ticker="CPRX", listing_state="MERGED", master_rank=None),
        scripted_row(ticker="UNMAPPED", listing_id=None, master_rank=None),
    ]
    publishable, excluded = load_publishable_rows(ScriptedCursor(rows), datetime(2026, 9, 1).date())
    assert [r["ticker"] for r in publishable] == ["MSFT"]
    assert {r["ticker"]: r["reason"] for r in excluded} == {
        "CPRX": "listing_not_active:MERGED",
        "UNMAPPED": "no_active_listing",
    }


def test_drivers_are_derived_from_block_scores():
    manifest = manifest_from_legacy_row(
        row(quality_z=80.0, value_z=30.0, momentum_z=70.0, analyst_z=60.0,
            tech_z=20.0, insider_z=50.0, catalyst_z=50.0, growth_z=65.0),
        snapshot_id="f17f8634-8152-4b3d-bc5e-827d1863813d",
        decision_time=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert [d["label_sv"] for d in manifest.positive_drivers] == ["Kvalitet", "Momentum", "Tillväxt"]
    assert [d["label_sv"] for d in manifest.negative_drivers] == ["Värde", "Teknik"]
    assert manifest.positive_drivers[0]["factor_name"] == "quality_z"


def test_missing_same_day_rank_for_publishable_row_is_a_hard_stop():
    rows = [
        scripted_row(ticker="MSFT", master_rank=None),
        scripted_row(ticker="CPRX", listing_state="MERGED", master_rank=None),
    ]
    with pytest.raises(ManifestInvariantError, match="Same-day MasterRank is missing for 1"):
        load_publishable_rows(ScriptedCursor(rows), datetime(2026, 9, 1).date())


def test_empty_scan_day_is_a_hard_stop():
    with pytest.raises(ManifestInvariantError, match="No scan_results rows"):
        load_publishable_rows(ScriptedCursor([]), datetime(2026, 9, 1).date())
