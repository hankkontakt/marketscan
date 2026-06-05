"""Watchlist CRUD — fully RLS-protected via Supabase."""
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import WatchlistItem
from apps.api.core.enrichment import enrich_with_scan_data

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItem])
async def get_watchlist(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    wl = sb.table("watchlist").select("*").eq("user_id", user.id).execute()
    items = wl.data or []
    return enrich_with_scan_data(items, sb)


@router.post("/{ticker}", status_code=201)
async def add_to_watchlist(
    ticker: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    sb.table("watchlist").upsert({"user_id": user.id, "ticker": ticker.upper()}).execute()
    return {"ok": True}


@router.delete("/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("watchlist").delete().eq("user_id", user.id).eq("ticker", ticker.upper()).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bevakningen hittades inte")
