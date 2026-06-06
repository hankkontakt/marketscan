"""
GET /scan — hot path, Postgres only (no DuckDB, no pandas).
Handles segment-toggle, all filters, NL search via AI.
"""
import csv
from fastapi import APIRouter, Depends, Query
from apps.api.dependencies import get_supabase
from apps.api.schemas.scan import ScanRow

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
    # Use count="exact" to avoid fetching all rows
    count_res = sb.table("scan_results").select("ticker", count="exact").execute()
    total = count_res.count or 0

    if total == 0:
        return {"scan_date": None, "total": 0, "by_segment": {}}

    # Only fetch scan_date from the most recent row
    date_res = sb.table("scan_results").select("scan_date").order("scan_date", desc=True).limit(1).execute()
    scan_date = date_res.data[0].get("scan_date") if date_res.data else None

    # Fetch segments to build histogram (only ~4 distinct values)
    segment_res = sb.table("scan_results").select("segment").execute()
    by_segment = {}
    for r in (segment_res.data or []):
        s = r.get("segment")
        if s:
            by_segment[s] = by_segment.get(s, 0) + 1

    return {"scan_date": scan_date, "total": total, "by_segment": by_segment}


@router.get("/export")
async def export_scan(
    segments: list[str] = Query(["large_cap", "mid_cap", "small_cap", "micro_cap"]),
    sb=Depends(get_supabase),
):
    """Export scan results as CSV."""
    from fastapi.responses import StreamingResponse
    import io

    result = sb.table("scan_results").select(
        "ticker,name,sector,segment,country,price,change_pct,score_total,"
        "score_value,score_quality,score_momentum,score_growth,score_risk,"
        "score_dividend,score_sentiment,entry_signal,trend_signal,"
        "pe_trailing,roe,piotroski_f,market_cap,dividend_yield,beta"
    ).in_("segment", segments).order("score_total", desc=True).execute()

    rows = result.data or []
    if not rows:
        return {"message": "Inga rader att exportera"}

    output = io.StringIO()
    writer = csv.writer(output)
    headers = list(rows[0].keys())
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(h, "") for h in headers])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=marketscan-export.csv"},
    )
