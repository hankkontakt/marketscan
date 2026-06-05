"""
GET /stocks/{ticker} — detailed stock view.
Hot data from Postgres, cold (price history, score history) from R2/DuckDB.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.duckdb_r2 import query_score_history, query_price_history

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}")
async def get_stock(ticker: str, sb=Depends(get_supabase)):
    """Current scan data for a single ticker."""
    result = (
        sb.table("scan_results")
        .select("*")
        .eq("ticker", ticker.upper())
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")
    return result.data


@router.get("/{ticker}/price-history")
async def get_price_history(ticker: str):
    """OHLCV data from R2 for TradingView Lightweight Charts."""
    try:
        data = query_price_history(ticker.upper())
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"Historikdata ej tillgänglig: {exc}")
    return {"ticker": ticker, "candles": data}


@router.get("/{ticker}/score-history")
async def get_score_history(ticker: str, limit: int = 52):
    """Weekly score snapshots from R2 for Betygstrend chart."""
    try:
        data = query_score_history(ticker.upper(), limit=limit)
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"Betygstrend ej tillgänglig: {exc}")
    return {"ticker": ticker, "history": data}


@router.get("")
async def search_stocks(q: str, limit: int = 10, sb=Depends(get_supabase)):
    """Quick search by ticker or name — used by ⌘K palette."""
    result = (
        sb.table("scan_results")
        .select("ticker, name, segment, score_total, entry_signal, price, change_pct")
        .or_(f"ticker.ilike.%{q}%,name.ilike.%{q}%")
        .order("score_total", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
