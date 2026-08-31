"""
rebalancer.py — API Router för Lysa-Style Portfölj-Rebalansering.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_supabase_admin
from backend_worker.rebalancer_engine import generate_rebalance_plan, calculate_portfolio_allocation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio/rebalance", tags=["Rebalancer"])


class RebalancePlanRequest(BaseModel):
    target_funds_pct: float = Field(default=60.0, ge=0.0, le=100.0)
    target_stocks_pct: float = Field(default=40.0, ge=0.0, le=100.0)
    max_sector_cap_pct: float = Field(default=25.0, ge=5.0, le=100.0)
    monthly_deposit_sek: Optional[float] = Field(default=None, ge=0.0)
    custom_stock_holdings: Optional[list[dict]] = None
    custom_fund_holdings: Optional[list[dict]] = None


@router.post("/plan")
async def create_rebalance_plan(
    body: RebalancePlanRequest,
    user: User = Depends(get_current_user),
    sb_admin=Depends(get_supabase_admin),
):
    """Skapar en ren och handlingsbar rebalanseringsplan."""
    stock_holdings = body.custom_stock_holdings
    fund_holdings = body.custom_fund_holdings

    # Hämta från databasen om inte anroparen skickade med egna innehav
    if stock_holdings is None:
        try:
            res = sb_admin.table("portfolio_holdings").select("*").eq("user_id", user.id).execute()
            stock_holdings = res.data or []
        except Exception:
            stock_holdings = []

    if fund_holdings is None:
        try:
            res_f = sb_admin.table("fund_holdings").select("*").eq("user_id", user.id).execute()
            fund_holdings = res_f.data or []
        except Exception:
            fund_holdings = []

    plan = generate_rebalance_plan(
        stock_holdings=stock_holdings,
        fund_holdings=fund_holdings,
        target_funds_pct=body.target_funds_pct,
        target_stocks_pct=body.target_stocks_pct,
        max_sector_cap_pct=body.max_sector_cap_pct,
        monthly_deposit_sek=body.monthly_deposit_sek,
    )

    return plan


@router.get("/overview")
async def get_rebalance_overview(
    user: User = Depends(get_current_user),
    sb_admin=Depends(get_supabase_admin),
):
    """Snabböversikt av aktuell fördelning mellan basfonder och aktier."""
    try:
        res = sb_admin.table("portfolio_holdings").select("*").eq("user_id", user.id).execute()
        stock_holdings = res.data or []
        res_f = sb_admin.table("fund_holdings").select("*").eq("user_id", user.id).execute()
        fund_holdings = res_f.data or []
    except Exception:
        stock_holdings = []
        fund_holdings = []

    alloc = calculate_portfolio_allocation(stock_holdings, fund_holdings)
    return {
        "allocation": alloc,
        "is_balanced": abs(alloc["funds_pct"] - 60.0) <= 5.0,
        "drift_pct": round(alloc["funds_pct"] - 60.0, 1),
    }
