"""V3 decision endpoints: projections only, never request-time quant work."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.core.feature_flags import is_feature_enabled
from apps.api.dependencies import get_supabase
from apps.api.schemas.decision_v3 import (
    CurrentSnapshotV3,
    DecisionProjectionV3,
    ScreenerProjectionV3,
)

router = APIRouter(prefix="/v3/decisions", tags=["decisions-v3"])


def _require_v3_flag() -> None:
    if not is_feature_enabled("decision_v3_api"):
        raise HTTPException(status_code=404, detail="Decision API v3 is disabled")


def _db_or_503(db):
    if db is None:
        raise HTTPException(status_code=503, detail="Decision snapshot store is unavailable")
    return db


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def _current_rows(db, *, listing_id: Optional[str] = None, ticker: Optional[str] = None, limit: int = 100):
    db = _db_or_503(db)
    query = db.table("current_decisions_v3").select("*")
    if listing_id:
        query = query.eq("listing_id", listing_id)
    if ticker:
        query = query.eq("ticker", ticker.upper().strip())
    result = query.order("master_rank_score", desc=True).limit(limit).execute()
    return result.data or []


@router.get("/screener", response_model=ScreenerProjectionV3, dependencies=[Depends(_require_v3_flag)])
def screener(
    thesis_band: str | None = Query(None),
    setup_state: str | None = Query(None),
    risk_state: str | None = Query(None),
    data_grade: str | None = Query(None),
    segment: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_supabase),
):
    rows = _current_rows(db, limit=limit)
    filters = {
        "thesis_band": thesis_band,
        "setup_state": setup_state,
        "risk_state": risk_state,
        "data_grade": data_grade,
        "segment": segment,
    }
    rows = [row for row in rows if all(value is None or row.get(key) == value for key, value in filters.items())]
    if not rows:
        raise HTTPException(status_code=404, detail="No published decision snapshot matches the request")
    return ScreenerProjectionV3(
        snapshot_id=rows[0]["decision_snapshot_id"],
        as_of=rows[0]["published_at"],
        total_count=len(rows),
        rows=rows,
    )


@router.get("/stock/{listing_id}", response_model=DecisionProjectionV3, dependencies=[Depends(_require_v3_flag)])
def stock(listing_id: str, ticker: str | None = Query(None), db=Depends(get_supabase)):
    """Current decision by canonical listing_id, or by legacy ticker alias.

    The listing_id path segment may also be a legacy ticker (e.g. ``CPRX``)
    when the UI has not yet resolved a listing: the projection is still read
    from the same published snapshot, never computed or synthesized.
    """
    db = _db_or_503(db)
    if ticker:
        rows = _current_rows(db, ticker=ticker, limit=1)
    elif _is_uuid(listing_id):
        rows = _current_rows(db, listing_id=listing_id, limit=1)
    else:
        rows = _current_rows(db, ticker=listing_id, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="No published decision for listing")
    return rows[0]


@router.get("/stock/{listing_id}/history", dependencies=[Depends(_require_v3_flag)])
def history(listing_id: str, db=Depends(get_supabase)):
    db = _db_or_503(db)
    listing = stock(listing_id, db=db)
    result = (
        db.table("decision_manifests")
        .select("*")
        .eq("listing_id", listing["listing_id"])
        .order("decision_time", desc=True)
        .execute()
    )
    return {"listing_id": listing["listing_id"], "rows": result.data or []}


@router.get("/stock/{listing_id}/evidence", dependencies=[Depends(_require_v3_flag)])
def evidence(listing_id: str, db=Depends(get_supabase)):
    db = _db_or_503(db)
    decision = stock(listing_id, db)
    result = db.table("decision_evidence").select("*").eq("decision_id", decision["decision_id"]).execute()
    return {"decision_id": decision["decision_id"], "rows": result.data or []}


@router.get("/stock/{listing_id}/changes", dependencies=[Depends(_require_v3_flag)])
def changes(listing_id: str, db=Depends(get_supabase)):
    rows = history(listing_id, db)["rows"]
    return {"listing_id": listing_id, "current": rows[0] if rows else None, "previous": rows[1] if len(rows) > 1 else None}


@router.get("/system/current-snapshot", response_model=CurrentSnapshotV3, dependencies=[Depends(_require_v3_flag)])
def current_snapshot(db=Depends(get_supabase)):
    """Health/observability projection: exactly one published pointer or null."""
    db = _db_or_503(db)
    pointer = db.table("publication_state").select("current_decision_snapshot_id, updated_at").limit(1).execute()
    snapshot_id = (pointer.data or [{}])[0].get("current_decision_snapshot_id")
    if not snapshot_id:
        return CurrentSnapshotV3(manifest_count=0, actionable_count=0, excluded_count=0)
    snapshots = (
        db.table("decision_snapshots")
        .select("decision_snapshot_id, published_at, master_model_version, code_sha, quality_report")
        .eq("decision_snapshot_id", snapshot_id)
        .execute()
    )
    snapshot = (snapshots.data or [{}])[0]
    manifests = (
        db.table("decision_manifests")
        .select("is_actionable")
        .eq("decision_snapshot_id", snapshot_id)
        .execute()
    )
    manifest_rows = manifests.data or []
    report = snapshot.get("quality_report") or {}
    return CurrentSnapshotV3(
        current_snapshot_id=snapshot_id,
        published_at=snapshot.get("published_at"),
        master_model_version=snapshot.get("master_model_version"),
        code_sha=snapshot.get("code_sha"),
        manifest_count=len(manifest_rows),
        actionable_count=sum(1 for row in manifest_rows if row.get("is_actionable")),
        excluded_count=report.get("excluded_count", 0),
        quality_report=report,
    )