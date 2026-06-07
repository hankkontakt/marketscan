"""
Admin endpoints — Kontrollpanel backend.
Requires admin role.
"""
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from apps.api.core.security import get_current_user, require_admin, User
from apps.api.dependencies import get_supabase


class PipelineRunOut(BaseModel):
    id: str
    run_type: str
    status: str
    tickers_ok: int | None = None
    tickers_err: int | None = None
    duration_s: float | None = None
    error_msg: str | None = None
    started_at: str | None = None


class SystemStatusOut(BaseModel):
    scan_rows: int
    last_runs: list[PipelineRunOut]


class ScoreDistributionOut(BaseModel):
    buckets: list[dict]
    total: int
    by_signal: dict[str, int]


class UniverseStatsOut(BaseModel):
    by_sector: dict[str, int]
    by_segment: dict[str, int]
    by_country: dict[str, int]
    low_liquidity: int
    total: int


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=SystemStatusOut)
async def system_status(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Pipeline health, latest run, scan freshness."""
    _ = user  # admin access verified
    scan_count = sb.table("scan_results").select("ticker", count="exact").execute()
    last_run = (
        sb.table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(5)
        .execute()
    )
    return {
        "scan_rows": scan_count.count or 0,
        "last_runs": last_run.data or [],
    }


@router.get("/pipeline-runs", response_model=list[PipelineRunOut])
async def pipeline_runs(
    limit: int = 20,
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    res = (
        sb.table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


class UsersListOut(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    created_at: str | None = None


@router.get("/users", response_model=list[UsersListOut])
async def list_users(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    profiles = sb.table("profiles").select("*").order("created_at").execute()
    return profiles.data or []


@router.get("/score-distribution", response_model=ScoreDistributionOut)
async def score_distribution(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Score histogram for monitoring model drift."""
    res = sb.table("scan_results").select("score_total, segment, entry_signal").execute()
    rows = res.data or []
    buckets = [0] * 10
    for r in rows:
        s = r.get("score_total")
        if s is not None:
            idx = min(int(s // 10), 9)
            buckets[idx] += 1
    return {
        "buckets": [{"range": f"{i*10}-{i*10+9}", "count": c} for i, c in enumerate(buckets)],
        "total": len(rows),
        "by_signal": {
            sig: sum(1 for r in rows if r.get("entry_signal") == sig)
            for sig in ["STARK", "OK", "VÄNTA", "EJ_AKTUELL"]
        },
    }


@router.get("/universe", response_model=UniverseStatsOut)
async def universe_stats(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Coverage by sector and segment."""
    res = sb.table("scan_results").select("sector, segment, country, low_liquidity").execute()
    rows = res.data or []
    from collections import Counter
    return {
        "by_sector": dict(Counter(r.get("sector") for r in rows if r.get("sector"))),
        "by_segment": dict(Counter(r.get("segment") for r in rows)),
        "by_country": dict(Counter(r.get("country") for r in rows if r.get("country"))),
        "low_liquidity": sum(1 for r in rows if r.get("low_liquidity")),
        "total": len(rows),
    }
