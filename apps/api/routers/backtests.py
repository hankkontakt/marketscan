"""Backtesting results from strategy validation pipeline."""
import logging
from fastapi import APIRouter, Depends
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("")
def get_backtest_results(sb=Depends(get_supabase)):
    """All backtest results ordered by recency."""
    res = sb.table("backtest_results").select("*").order("created_at", desc=True).execute()
    return res.data or []


@router.get("/{strategy}")
def get_strategy_backtest(strategy: str, sb=Depends(get_supabase)):
    """Backtest results for a specific strategy."""
    res = sb.table("backtest_results").select("*").eq("strategy_name", strategy).limit(1).execute()
    return res.data[0] if res.data else None
