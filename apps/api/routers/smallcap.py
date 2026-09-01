"""Smallcap scanner results."""
import logging
from fastapi import APIRouter, Depends, Query
from apps.api.dependencies import get_supabase
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/smallcap", tags=["smallcap"])


class SmallcapResultOut(BaseModel):
    ticker: str
    name: str | None = None
    segment: str | None = None
    sector: str | None = None
    score_total: float | None = None
    score_insider: float | None = None
    score_fcf: float | None = None
    score_piotroski: float | None = None
    score_growth: float | None = None
    score_balance: float | None = None
    score_valuation: float | None = None
    score_momentum: float | None = None
    score_liquidity: float | None = None
    market_cap: float | None = None
    price: float | None = None
    cash_runway_months: float | None = None
    insider_buying: bool = False
    entry_signal: str | None = None
    master_rank: float | None = None
    master_rank_pctl: float | None = None
    liquidity_grade: str | None = None
    mews_score: float | None = None
    piotroski_f: int | None = None
    dividend_yield: float | None = None


@router.get("", response_model=list[SmallcapResultOut])
def get_smallcap_results(
    score_min: float = Query(0.0, ge=0),
    sector: str | None = None,
    limit: int = Query(50, le=200),
    sb=Depends(get_supabase),
):
    """Smallcap scanner results from smallcap_results with fallback to scan_results."""
    try:
        q_sc = sb.table("smallcap_results").select("*").gte("score_total", score_min)
        if sector:
            q_sc = q_sc.eq("sector", sector)
        res_sc = q_sc.order("score_total", desc=True).limit(limit).execute()
        if res_sc.data and len(res_sc.data) > 0:
            return res_sc.data
    except Exception as e:
        logger.debug("smallcap_results query failed or empty: %s", e)

    # Fallback-väg: query scan_results för small_cap och micro_cap
    q = (
        sb.table("scan_results")
        .select("*")
        .in_("segment", ["small_cap", "micro_cap"])
        .gte("score_total", score_min)
    )
    if sector:
        q = q.eq("sector", sector)
    res = q.order("score_total", desc=True).limit(limit).execute()
    rows = res.data or []

    if rows:
        tickers = [r["ticker"] for r in rows if r.get("ticker")]
        try:
            mr_res = (
                sb.table("master_rank")
                .select("ticker, master_rank, master_rank_pctl, tier, liquidity_grade")
                .in_("ticker", tickers)
                .execute()
            )
            mr_map = {r["ticker"]: r for r in (mr_res.data or []) if r.get("ticker")}
            for r in rows:
                m = mr_map.get(r["ticker"], {})
                if m:
                    if m.get("master_rank") is not None:
                        r["master_rank"] = m.get("master_rank")
                    if m.get("master_rank_pctl") is not None:
                        r["master_rank_pctl"] = m.get("master_rank_pctl")
                    if m.get("liquidity_grade"):
                        r["liquidity_grade"] = m.get("liquidity_grade")
        except Exception as e:
            logger.debug("enrich smallcap with master_rank failed: %s", e)

    return rows


@router.get("/sectors")
def get_smallcap_sectors(sb=Depends(get_supabase)):
    """Distinct sectors in smallcap results."""
    try:
        res = sb.table("smallcap_results").select("sector").execute()
        sectors = sorted(set(r["sector"] for r in (res.data or []) if r.get("sector")))
        if sectors:
            return {"sectors": sectors}
    except Exception:
        pass

    res = sb.table("scan_results").select("sector").in_("segment", ["small_cap", "micro_cap"]).execute()
    sectors = sorted(set(r["sector"] for r in (res.data or []) if r.get("sector")))
    return {"sectors": sectors}
