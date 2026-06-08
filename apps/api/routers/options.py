"""Options data — chain, Greeks, flow analysis (from backend_worker pipeline)."""
import logging
from fastapi import APIRouter, Depends
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/options", tags=["options"])


@router.get("/{ticker}")
def get_options_chain(ticker: str, sb=Depends(get_supabase)):
    """Latest options chain data for a ticker."""
    res = sb.table("options_data").select("*").eq("ticker", ticker.upper()).order("expiration").execute()
    return {"ticker": ticker.upper(), "options": res.data or [], "count": len(res.data or [])}
