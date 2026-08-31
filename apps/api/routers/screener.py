"""
GET /scan — hot path, Postgres only (no DuckDB, no pandas).
Handles segment-toggle, all filters, NL search via AI.
"""
import csv
import logging

from fastapi import APIRouter, Depends, Query
from apps.api.dependencies import get_supabase
from apps.api.schemas.scan import ScanRow
from apps.api.core.search_utils import safe_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["screener"])

# All segments in the universe. The app's focus is the full market (small/micro
# included), so the /scan DEFAULT is "no segment filter" — every segment is
# returned unless the client explicitly passes ?segments=...
_ALL_SEGMENTS = ["large_cap", "mid_cap", "small_cap", "micro_cap"]


def _apply_common_filters(q, segments, sector, country, entry_signal, trend_signal,
                          piotroski_min, pe_max, roe_min, dividend_yield_min,
                          exclude_low_liquidity, mews_flag, search):
    # Default = ALL segments (small/micro included — the app's focus). Only
    # filter when the client explicitly passes ?segments=...
    if segments is not None:
        q = q.in_("segment", segments)

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
    if mews_flag is not None and mews_flag:
        q = q.eq("mews_flag", True).gt("mews_score", 0)
    if search:
        # P0-4: sanitize before interpolating into PostgREST filter
        safe_term = safe_search(search)
        if safe_term:
            q = q.or_(f"ticker.ilike.%{safe_term}%,name.ilike.%{safe_term}%")
    return q


def _enrich_with_master_rank(sb, rows: list[dict]) -> list[dict]:
    """Merge master_rank table data into scan_results rows.

    Ensures ALL views (not just sort_by=master_rank) show rank, tier,
    z-scores, and trend data — critical for small/micro caps whose
    scan_results entry_signal is stale.
    """
    if not rows:
        return rows
    tickers = list({r["ticker"] for r in rows})
    try:
        mr_res = (
            sb.table("master_rank")
            .select("ticker, master_rank, tier, quality_z, value_z, momentum_z, "
                    "analyst_z, analyst_upside, analyst_count, trend_tech, currency")
            .in_("ticker", tickers)
            .not_.is_("master_rank", "null")
            .execute()
        )
        mr_by_ticker: dict[str, dict] = {}
        for r in (mr_res.data or []):
            t = r["ticker"]
            # Keep highest master_rank per ticker (dedup if multiple scan_dates)
            if t not in mr_by_ticker or (r.get("master_rank") or 0) > (mr_by_ticker[t].get("master_rank") or 0):
                mr_by_ticker[t] = r
    except Exception as e:
        logger.warning("master_rank enrichment failed (non-fatal): %s", e)
        return rows

    for row in rows:
        m = mr_by_ticker.get(row["ticker"], {})
        from backend_worker.master_rank import tier_of, signal_from_tier
        seg = row.get("segment")

        if m:
            row["master_rank"] = m.get("master_rank")
            # Always re-evaluate tier and signal with live segment-aware thresholds
            if row["master_rank"] is not None:
                row["tier"] = tier_of(row["master_rank"], False, m.get("pit_status", "READY"), segment=seg)
                row["entry_signal"] = signal_from_tier(row["tier"])
            else:
                row["tier"] = m.get("tier")
                row["entry_signal"] = signal_from_tier(row["tier"])
            row["quality_z"] = m.get("quality_z") or row.get("quality_z") or row.get("score_quality")
            row["value_z"] = m.get("value_z") or row.get("value_z") or row.get("score_value")
            row["momentum_z"] = m.get("momentum_z") or row.get("momentum_z") or row.get("score_momentum")
            row["analyst_z"] = m.get("analyst_z")
            row["analyst_upside"] = m.get("analyst_upside")
            row["analyst_count"] = m.get("analyst_count")
            row["trend_tech"] = m.get("trend_tech") or row.get("trend_signal")
            if m.get("currency"):
                row["currency"] = m.get("currency")
        else:
            # Fallback for tickers not yet in master_rank table (e.g. newly scanned small/micro caps):
            # Derive rank, tier & entry_signal from score_total and segment-aware thresholds
            score = row.get("score_total")
            if score is not None:
                row["master_rank"] = round(float(score), 1)
                row["tier"] = tier_of(float(score), False, "READY", segment=seg)
                row["entry_signal"] = signal_from_tier(row["tier"])
            row["quality_z"] = row.get("quality_z") or row.get("score_quality")
            row["value_z"] = row.get("value_z") or row.get("score_value")
            row["momentum_z"] = row.get("momentum_z") or row.get("score_momentum")
            row["trend_tech"] = row.get("trend_tech") or row.get("trend_signal")
    return rows


@router.get("", response_model=list[ScanRow])
def get_scan(
    segments: list[str] | None = Query(default=None),
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
    mews_flag: bool | None = None,
    sort_by: str = Query(default="score_total", pattern="^(score_total|mews_score|master_rank)$"),
    limit: int = Query(default=500, ge=1, le=500),
    sb=Depends(get_supabase),
):
    db_sort = "mews_score" if sort_by == "mews_score" else "score_total"
    q = (
        sb.table("scan_results")
        .select("*")
        .gte("score_total", score_min)
        .lte("score_total", score_max)
        .order(db_sort, desc=True)
        .limit(limit)
    )
    q = _apply_common_filters(q, segments, sector, country, entry_signal, trend_signal,
                              piotroski_min, pe_max, roe_min, dividend_yield_min,
                              exclude_low_liquidity, mews_flag, search)
    result = q.execute()
    rows = result.data or []

    # Enrich with master_rank data (authoritative rank, segment-aware tier & signals)
    rows = _enrich_with_master_rank(sb, rows)

    if sort_by == "master_rank":
        rows.sort(key=lambda r: float(r.get("master_rank") or r.get("score_total") or 0.0), reverse=True)

    return rows


@router.get("/sectors", response_model=list[str])
def get_sectors(sb=Depends(get_supabase)):
    """Distinct sectors in current scan — for filter dropdown."""
    result = (
        sb.table("scan_results")
        .select("sector")
        .not_.is_("sector", "null")
        .execute()
    )
    sectors = sorted({row["sector"] for row in result.data if row.get("sector")})
    return sectors


@router.get("/countries", response_model=list[str])
def get_countries(sb=Depends(get_supabase)):
    """Distinct countries in current scan — for filter dropdown."""
    result = (
        sb.table("scan_results")
        .select("country")
        .not_.is_("country", "null")
        .execute()
    )
    countries = sorted({row["country"] for row in result.data if row.get("country")})
    return countries


@router.get("/meta")
def get_scan_meta(sb=Depends(get_supabase)):
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
def export_scan(
    segments: list[str] = Query(default=list(_ALL_SEGMENTS)),
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
