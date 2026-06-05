"""
GET /scan — hot path, Postgres only (no DuckDB, no pandas).
Handles segment-toggle, all filters, NL search via AI.
"""
from fastapi import APIRouter, Depends, Query
from apps.api.dependencies import get_supabase
from apps.api.schemas.scan import ScanRow, ScanFilters

router = APIRouter(prefix="/scan", tags=["screener"])


@router.get("", response_model=list[ScanRow])
async def get_scan(
    segments: list[str] = Query(default=["large_cap", "mid_cap"]),
    score_min: float = Query(default=0, ge=0, le=100),
    score_max: float = Query(default=100, ge=0, le=100),
    sector: str | None = None,
    country: str | None = None,
    entry_signal: str | None = None,
    trend_signal: str | None = None,
    piotroski_min: int | None = Query(default=None, ge=0, le=9),
    pe_max: float | None = None,
    roe_min: float | None = None,
    dividend_yield_min: float | None = None,
    exclude_low_liquidity: bool = False,
    search: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    sb=Depends(get_supabase),
):
    q = (
        sb.table("scan_results")
        .select("*")
        .in_("segment", segments)
        .gte("score_total", score_min)
        .lte("score_total", score_max)
        .order("score_total", desc=True)
        .limit(limit)
    )

    if sector:
        q = q.eq("sector", sector)
    if country:
        q = q.eq("country", country)
    if entry_signal:
        q = q.eq("entry_signal", entry_signal)
    if trend_signal:
        q = q.eq("trend_signal", trend_signal)
    if piotroski_min is not None:
        q = q.gte("piotroski_f", piotroski_min)
    if pe_max is not None:
        q = q.lte("pe_trailing", pe_max).gt("pe_trailing", 0)
    if roe_min is not None:
        q = q.gte("roe", roe_min)
    if dividend_yield_min is not None:
        q = q.gte("dividend_yield", dividend_yield_min)
    if exclude_low_liquidity:
        q = q.eq("low_liquidity", False)
    if search:
        # Supabase ilike on ticker or name
        q = q.or_(f"ticker.ilike.%{search}%,name.ilike.%{search}%")

    result = q.execute()
    return result.data


@router.get("/sectors", response_model=list[str])
async def get_sectors(sb=Depends(get_supabase)):
    """Distinct sectors in current scan — for filter dropdown."""
    result = (
        sb.table("scan_results")
        .select("sector")
        .not_.is_("sector", "null")
        .execute()
    )
    sectors = sorted({row["sector"] for row in result.data if row.get("sector")})
    return sectors


@router.get("/meta")
async def get_scan_meta(sb=Depends(get_supabase)):
    """Scan metadata: date, counts per segment."""
    result = sb.table("scan_results").select("segment, scan_date").execute()
    rows = result.data
    if not rows:
        return {"scan_date": None, "total": 0, "by_segment": {}}

    from collections import Counter
    counts = Counter(r["segment"] for r in rows)
    scan_date = rows[0].get("scan_date") if rows else None
    return {"scan_date": scan_date, "total": len(rows), "by_segment": dict(counts)}
