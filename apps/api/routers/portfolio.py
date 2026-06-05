"""
Portfolio & watchlist CRUD — fully RLS-protected via Supabase.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import (
    HoldingIn, HoldingOut, PortfolioOut,
    WatchlistItem, PriceAlertIn, PriceAlertOut,
    SavedScreenIn, SavedScreenOut,
)

router = APIRouter(tags=["portfolio"])


# ─── Portfolio ──────────────────────────────────────────────────────────────

@router.get("/portfolio", response_model=PortfolioOut)
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

    # Enrich with current prices from scan_results
    tickers = [h["ticker"] for h in holdings]
    if tickers:
        scan_res = (
            sb.table("scan_results")
            .select("ticker, name, price, change_pct, score_total, entry_signal")
            .in_("ticker", tickers).execute()
        )
        scan_map = {r["ticker"]: r for r in (scan_res.data or [])}
        for h in holdings:
            meta = scan_map.get(h["ticker"], {})
            h.update({k: meta.get(k) for k in ["name", "price", "change_pct", "score_total", "entry_signal"]})

    portfolio["holdings"] = holdings
    return portfolio


@router.post("/portfolio/holdings", response_model=HoldingOut, status_code=201)
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


@router.delete("/portfolio/holdings/{holding_id}", status_code=204)
async def remove_holding(
    holding_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    sb.table("holdings").delete().eq("id", holding_id).execute()


# ─── Watchlist ───────────────────────────────────────────────────────────────

@router.get("/watchlist", response_model=list[WatchlistItem])
async def get_watchlist(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    wl = sb.table("watchlist").select("*").eq("user_id", user.id).execute()
    items = wl.data or []
    tickers = [i["ticker"] for i in items]
    if tickers:
        scan_res = (
            sb.table("scan_results")
            .select("ticker, name, price, change_pct, score_total, entry_signal")
            .in_("ticker", tickers).execute()
        )
        scan_map = {r["ticker"]: r for r in (scan_res.data or [])}
        for item in items:
            meta = scan_map.get(item["ticker"], {})
            item.update({k: meta.get(k) for k in ["name", "price", "change_pct", "score_total", "entry_signal"]})
    return items


@router.post("/watchlist/{ticker}", status_code=201)
async def add_to_watchlist(
    ticker: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    sb.table("watchlist").upsert({"user_id": user.id, "ticker": ticker.upper()}).execute()
    return {"ok": True}


@router.delete("/watchlist/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    sb.table("watchlist").delete().eq("user_id", user.id).eq("ticker", ticker.upper()).execute()


# ─── Price alerts ─────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[PriceAlertOut])
async def get_alerts(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    res = sb.table("price_alerts").select("*").eq("user_id", user.id).eq("active", True).execute()
    return res.data or []


@router.post("/alerts", response_model=PriceAlertOut, status_code=201)
async def create_alert(
    body: PriceAlertIn, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("price_alerts").insert({
        "user_id": user.id,
        "ticker": body.ticker.upper(),
        "condition": body.condition,
        "target_price": body.target_price,
        "note": body.note,
    }).execute()
    return res.data[0]


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    sb.table("price_alerts").delete().eq("id", alert_id).execute()


# ─── Saved screens ────────────────────────────────────────────────────────────

@router.get("/screens", response_model=list[SavedScreenOut])
async def get_saved_screens(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    res = sb.table("saved_screens").select("*").eq("user_id", user.id).order("created_at").execute()
    return res.data or []


@router.post("/screens", response_model=SavedScreenOut, status_code=201)
async def save_screen(
    body: SavedScreenIn, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("saved_screens").insert({
        "user_id": user.id, "name": body.name, "filter_json": body.filter_json
    }).execute()
    return res.data[0]


@router.delete("/screens/{screen_id}", status_code=204)
async def delete_screen(
    screen_id: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    sb.table("saved_screens").delete().eq("id", screen_id).execute()
