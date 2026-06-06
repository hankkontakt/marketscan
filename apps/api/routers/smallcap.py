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


@router.get("", response_model=list[SmallcapResultOut])
async def get_smallcap_results(
    score_min: float = Query(0.0, ge=0),
    sector: str | None = None,
    limit: int = Query(50, le=200),
    sb=Depends(get_supabase),
):
    """Smallcap scanner results with filters."""
    q = sb.table("smallcap_results").select("*").gte("score_total", score_min)
    if sector:
        q = q.eq("sector", sector)
    res = q.order("score_total", desc=True).limit(limit).execute()
    return res.data or []


@router.get("/sectors")
async def get_smallcap_sectors(sb=Depends(get_supabase)):
    """Distinct sectors in smallcap results."""
    res = sb.table("smallcap_results").select("sector").execute()
    sectors = sorted(set(r["sector"] for r in (res.data or []) if r.get("sector")))
    return {"sectors": sectors}
