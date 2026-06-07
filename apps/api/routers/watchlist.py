"""Watchlist CRUD — fully RLS-protected via Supabase."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_user_supabase as get_supabase, get_supabase_admin
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import WatchlistItem
from apps.api.core.enrichment import enrich_with_scan_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItem])
async def get_watchlist(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    wl = sb.table("watchlist").select("*").eq("user_id", user.id).execute()
    items = wl.data or []
    return enrich_with_scan_data(items, sb)


@router.post("/{ticker}", status_code=201)
async def add_to_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
    sb_admin=Depends(get_supabase_admin),
):
    t = ticker.upper()
    sb.table("watchlist").upsert({"user_id": user.id, "ticker": t}).execute()

    # If ticker not in universe, queue it for the next pipeline run.
    # Uses admin client because regular users lack the UPDATE policy on
    # user_ticker_requests (needed for upsert on conflict).
    try:
        exists = (
            sb.table("scan_results")
            .select("ticker")
            .eq("ticker", t)
            .limit(1)
            .execute()
        )
        if not exists.data:
            sb_admin.table("user_ticker_requests").upsert(
                {
                    "ticker": t,
                    "user_id": user.id,
                    "source": "watchlist",
                    "added_to_universe": False,
                },
                on_conflict="ticker",
            ).execute()
            logger.info("Queued out-of-universe ticker %s (watchlist) for next pipeline run", t)
    except Exception as e:
        # Non-fatal — watchlist entry is still saved
        logger.debug("Could not queue ticker request for %s: %s", t, e)

    return {"ok": True}


@router.delete("/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("watchlist").delete().eq("user_id", user.id).eq("ticker", ticker.upper()).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bevakningen hittades inte")
