"""Portfolio & holdings CRUD — fully RLS-protected via Supabase."""
from fastapi import APIRouter, Depends, HTTPException, status
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
