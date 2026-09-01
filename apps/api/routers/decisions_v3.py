"""V3 decision endpoints: projections only, never request-time quant work."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.core.feature_flags import is_feature_enabled
from apps.api.dependencies import get_supabase
from apps.api.schemas.decision_v3 import DecisionProjectionV3, ScreenerProjectionV3

router = APIRouter(prefix="/v3/decisions", tags=["decisions-v3"])


def _require_v3_flag() -> None:
    if not is_feature_enabled("decision_v3_api"):
        raise HTTPException(status_code=404, detail="Decision API v3 is disabled")


def _current_rows(db, *, listing_id: Optional[str] = None, limit: int = 100):
    if db is None:
        raise HTTPException(status_code=503, detail="Decision snapshot store is unavailable")
    query = db.table("current_decisions_v3").select("*")
    if listing_id:
        query = query.eq("listing_id", listing_id)
    result = query.order("master_rank_score", desc=True).limit(limit).execute()
    return result.data or []


@router.get("/screener", response_model=ScreenerProjectionV3, dependencies=[Depends(_require_v3_flag)])
def screener(
    thesis_band: str | None = Query(None),
    setup_state: str | None = Query(None),
    risk_state: str | None = Query(None),
    data_grade: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_supabase),
):
    rows = _current_rows(db, limit=limit)
    filters = {
        "thesis_band": thesis_band,
        "setup_state": setup_state,
        "risk_state": risk_state,
        "data_grade": data_grade,
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
def stock(listing_id: str, db=Depends(get_supabase)):
    rows = _current_rows(db, listing_id=listing_id, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="No published decision for listing")
    return rows[0]


@router.get("/stock/{listing_id}/history", dependencies=[Depends(_require_v3_flag)])
def history(listing_id: str, db=Depends(get_supabase)):
    if db is None:
        raise HTTPException(status_code=503, detail="Decision snapshot store is unavailable")
    result = db.table("decision_manifests").select("*").eq("listing_id", listing_id).order("decision_time", desc=True).execute()
    return {"listing_id": listing_id, "rows": result.data or []}


@router.get("/stock/{listing_id}/evidence", dependencies=[Depends(_require_v3_flag)])
def evidence(listing_id: str, db=Depends(get_supabase)):
    decision = stock(listing_id, db)
    result = db.table("decision_evidence").select("*").eq("decision_id", decision["decision_id"]).execute()
    return {"decision_id": decision["decision_id"], "rows": result.data or []}


@router.get("/stock/{listing_id}/changes", dependencies=[Depends(_require_v3_flag)])
def changes(listing_id: str, db=Depends(get_supabase)):
    rows = history(listing_id, db)["rows"]
    return {"listing_id": listing_id, "current": rows[0] if rows else None, "previous": rows[1] if len(rows) > 1 else None}
