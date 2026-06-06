"""Portfolio & holdings CRUD — fully RLS-protected via Supabase."""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.dependencies import get_supabase
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import HoldingIn, HoldingOut, PortfolioOut
from apps.api.core.enrichment import enrich_with_scan_data

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ─── Portfolio ──────────────────────────────────────────────────────────────

@router.get("", response_model=PortfolioOut)
async def get_portfolio(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    port = (
        sb.table("portfolios").select("*").eq("user_id", user.id)
        .order("created_at").limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio = port.data[0]

    holdings_res = (
        sb.table("holdings").select("*")
        .eq("portfolio_id", portfolio["id"]).execute()
    )
    holdings = holdings_res.data or []

    enrich_with_scan_data(holdings, sb)

    portfolio["holdings"] = holdings
    return portfolio


@router.post("/holdings", response_model=HoldingOut, status_code=201)
async def add_holding(
    body: HoldingIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    port = (
        sb.table("portfolios").select("id").eq("user_id", user.id)
        .limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    res = sb.table("holdings").insert({
        "portfolio_id": portfolio_id,
        "ticker": body.ticker.upper(),
        "shares": body.shares,
        "cost_basis": body.cost_basis,
    }).execute()
    return res.data[0]


@router.delete("/holdings/{holding_id}", status_code=204)
async def remove_holding(
    holding_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    res = sb.table("holdings").delete().eq("id", holding_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Innehavet hittades inte")


# ─── Portfolio risk ────────────────────────────────────────────────────────────


class SectorAllocation(BaseModel):
    sector: str
    value: float
    pct: float


class PortfolioRiskOut(BaseModel):
    tickers: list[str]
    sector_allocation: list[SectorAllocation]
    concentration_pct: float
    total_value: float
    count: int
    score_avg: float | None = None


@router.get("/risk", response_model=PortfolioRiskOut)
async def get_portfolio_risk(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    """Portfolio risk metrics: sector allocation, concentration, avg score."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return PortfolioRiskOut(tickers=[], sector_allocation=[], concentration_pct=0, total_value=0, count=0, score_avg=None)

    holdings = sb.table("holdings").select("*").eq("portfolio_id", port.data[0]["id"]).execute()
    items = holdings.data or []
    if not items:
        return PortfolioRiskOut(tickers=[], sector_allocation=[], concentration_pct=0, total_value=0, count=0, score_avg=None)

    tickers = [h["ticker"] for h in items]
    scan = sb.table("scan_results").select("ticker,price,sector,score_total").in_("ticker", tickers).execute()
    scan_map = {r["ticker"]: r for r in (scan.data or [])}

    total_value = 0.0
    sector_values: dict[str, float] = Counter()
    scores = []
    for h in items:
        info = scan_map.get(h["ticker"])
        price = info.get("price") if info else h.get("cost_basis")
        if price is None:
            continue
        val = float(price) * float(h["shares"])
        total_value += val
        sector = (info or {}).get("sector") or "Övrigt"
        sector_values[sector] += val
        score = (info or {}).get("score_total")
        if score is not None:
            scores.append(float(score))

    allocation = [
        SectorAllocation(sector=s, value=round(v, 2), pct=round(v / total_value * 100, 1))
        for s, v in sector_values.most_common()
    ]

    concentration_pct = round((sector_values.most_common(1)[0][1] / total_value * 100), 1) if sector_values else 0
    score_avg = round(sum(scores) / len(scores), 1) if scores else None

    return PortfolioRiskOut(
        tickers=tickers,
        sector_allocation=allocation,
        concentration_pct=concentration_pct,
        total_value=round(total_value, 2),
        count=len(items),
        score_avg=score_avg,
    )
