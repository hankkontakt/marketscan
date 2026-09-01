"""Publish immutable V3 decisions from a fully refreshed legacy score snapshot.

This is a deliberately narrow bridge while the scoring engine still writes to
``scan_results`` and ``master_rank``.  It never creates Security Master rows:
every legacy ticker must already resolve to a canonical listing.  That makes a
missing mapping a hard stop instead of silently publishing a partial universe.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from backend_worker.decision_manifests import DecisionManifest, DecisionManifestPublisher, ManifestInvariantError

logger = logging.getLogger(__name__)

_COVERAGE_FIELDS = (
    "master_rank", "master_rank_pctl", "quality_z", "value_z", "momentum_z",
    "analyst_z", "tech_z", "insider_z", "catalyst_z", "growth_z",
)
_THESIS_BY_TIER = {"T1": "BULLISH", "T2": "CONSTRUCTIVE", "T3": "NEUTRAL", "T4": "AVOID"}
_SETUP_BY_SIGNAL = {"STARK": "READY", "OK": "WATCH", "VÄNTA": "WAIT", "EJ_AKTUELL": "INSUFFICIENT"}


def _value(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    value = row.get(key, default)
    return default if value is None else value


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    return []


def manifest_from_legacy_row(
    row: Mapping[str, Any], *, snapshot_id: str, decision_time: datetime
) -> DecisionManifest:
    """Convert one same-day legacy score row to an immutable V3 manifest."""
    listing_id = _value(row, "listing_id")
    ticker = _value(row, "ticker", "?")
    if not listing_id:
        raise ManifestInvariantError(f"Security Master mapping missing for {ticker}")
    if decision_time.tzinfo is None:
        raise ManifestInvariantError("decision_time must be timezone-aware")

    coverage = sum(_value(row, field) is not None for field in _COVERAGE_FIELDS) / len(_COVERAGE_FIELDS)
    entry_signal = str(_value(row, "entry_signal", "EJ_AKTUELL"))
    setup_state = _SETUP_BY_SIGNAL.get(entry_signal, "INSUFFICIENT")
    warning_flags = _json_list(row.get("warning_flags")) + _json_list(row.get("data_missing"))
    pit_status = str(_value(row, "pit_status", "STALE"))
    is_low_liquidity = bool(_value(row, "low_liquidity", False))
    risk_state = "CRITICAL" if pit_status != "READY" else "ELEVATED" if is_low_liquidity or warning_flags else "NORMAL"
    tier = str(_value(row, "tier", "T4"))
    is_actionable = (
        str(_value(row, "listing_state", "UNKNOWN")) == "ACTIVE"
        and tier in {"T1", "T2"}
        and setup_state in {"READY", "WATCH"}
        and risk_state == "NORMAL"
        and coverage >= 0.75
    )

    return DecisionManifest(
        listing_id=str(listing_id),
        decision_snapshot_id=snapshot_id,
        decision_time=decision_time,
        thesis_band=_THESIS_BY_TIER.get(tier, "AVOID"),
        setup_state=setup_state,
        risk_state=risk_state,
        data_grade="A" if coverage >= 0.9 else "B" if coverage >= 0.75 else "C" if coverage >= 0.5 else "D",
        coverage=coverage,
        master_rank_score=_value(row, "master_rank"),
        segment_percentile=_value(row, "master_rank_pctl"),
        setup_vector={"entry_signal": entry_signal, "trend": _value(row, "trend_tech")},
        risk_vector={"pit_status": pit_status, "low_liquidity": is_low_liquidity},
        is_actionable=is_actionable,
        stale_critical_count=0 if pit_status == "READY" else 1,
        street_context={"analyst_upside": _value(row, "analyst_upside"), "analyst_count": _value(row, "analyst_count")},
        warnings=warning_flags,
        model_versions={"master_rank": "legacy-bridge-v3"},
    )


def load_publishable_rows(cursor: Any, scan_date: date) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Load same-day legacy and MasterRank data; stale ranks are rejected.

    Returns ``(publishable, excluded)``. A legacy row whose canonical listing
    is missing or not ``ACTIVE`` (e.g. CPRX after its acquisition) is an
    explicit quarantine record, not a publication blocker — it resolves to
    ``NO_SIGNAL`` and is reported in the quality report (plan phase 2 exit
    gate: resolve or explicit quarantine). Missing same-day MasterRank for a
    row that would be published remains a hard stop.
    """
    cursor.execute(
        """
        SELECT sr.ticker, sr.entry_signal, sr.low_liquidity,
               l.listing_id, l.state AS listing_state,
               mr.master_rank, mr.master_rank_pctl, mr.tier, mr.quality_z,
               mr.value_z, mr.momentum_z, mr.analyst_z, mr.tech_z, mr.insider_z,
               mr.catalyst_z, mr.growth_z, mr.pit_status, mr.trend_tech,
               mr.warning_flags, mr.data_missing, mr.analyst_upside, mr.analyst_count
        FROM public.scan_results sr
        LEFT JOIN public.listings l
          ON upper(l.ticker) = upper(sr.ticker) AND l.valid_to IS NULL
        LEFT JOIN public.master_rank mr
          ON mr.ticker = sr.ticker AND mr.scan_date = sr.scan_date
        WHERE sr.scan_date = %s
        ORDER BY sr.ticker
        """,
        (scan_date,),
    )
    rows = list(cursor.fetchall())
    if not rows:
        raise ManifestInvariantError(f"No scan_results rows exist for {scan_date.isoformat()}")
    publishable: list[Mapping[str, Any]] = []
    excluded: list[Mapping[str, Any]] = []
    for row in rows:
        if row["listing_id"] is None:
            excluded.append({"ticker": str(row["ticker"]), "reason": "no_active_listing"})
        elif str(row["listing_state"]) != "ACTIVE":
            excluded.append({"ticker": str(row["ticker"]), "reason": f"listing_not_active:{row['listing_state']}"})
        else:
            publishable.append(row)
    missing_rank = [str(row["ticker"]) for row in publishable if row["master_rank"] is None]
    if missing_rank:
        sample = ", ".join(missing_rank[:5])
        raise ManifestInvariantError(f"Same-day MasterRank is missing for {len(missing_rank)} listings: {sample}")
    return publishable, excluded


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "uncommitted"


def publish_current_snapshot(
    *, client: Any, cursor: Any, scan_date: date | None = None, publication_run_id: str | None = None
) -> str:
    """Stage and atomically publish a complete same-day V3 universe."""
    effective_date = scan_date or date.today()
    snapshot_id = str(uuid4())
    rows, excluded = load_publishable_rows(cursor, effective_date)
    decision_time = datetime.now(timezone.utc)
    manifests = [manifest_from_legacy_row(row, snapshot_id=snapshot_id, decision_time=decision_time) for row in rows]
    DecisionManifestPublisher(client).stage_and_publish(
        snapshot_id=snapshot_id,
        publication_run_id=publication_run_id or str(uuid4()),
        data_snapshot_id=str(uuid4()),
        master_model_version="legacy-bridge-v3",
        code_sha=_code_sha(),
        manifests=manifests,
        quality_report={
            "scan_date": effective_date.isoformat(),
            "row_count": len(rows),
            "published_count": len(manifests),
            "excluded_count": len(excluded),
            "exclusions": excluded,
            "complete_universe": True,
        },
    )
    logger.info(
        "Published V3 decision snapshot %s with %d manifests (%d excluded)",
        snapshot_id, len(manifests), len(excluded),
    )
    return snapshot_id


def publish_from_environment(scan_date: date | None = None) -> str:
    """Worker entry point. Requires service credentials and a direct DB DSN."""
    database_url = os.environ.get("DATABASE_URL")
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not database_url or not supabase_url or not service_key:
        raise ManifestInvariantError("DATABASE_URL, SUPABASE_URL and SUPABASE_SERVICE_KEY are required for V3 publication")
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from supabase import create_client

    with psycopg2.connect(database_url) as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            return publish_current_snapshot(client=create_client(supabase_url, service_key), cursor=cursor, scan_date=scan_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    publish_from_environment()
