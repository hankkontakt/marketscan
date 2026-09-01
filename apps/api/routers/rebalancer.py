"""
rebalancer.py — API Router för Lysa-Style Portfölj-Rebalansering.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_user_supabase
from apps.api.core.rebalancer_engine import generate_rebalance_plan, calculate_portfolio_allocation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio/rebalance", tags=["Rebalancer"])


class RebalancePlanRequest(BaseModel):
    target_funds_pct: float = Field(default=60.0, ge=0.0, le=100.0)
    target_stocks_pct: float = Field(default=40.0, ge=0.0, le=100.0)
    max_sector_cap_pct: float = Field(default=25.0, ge=5.0, le=100.0)
    monthly_deposit_sek: Optional[float] = Field(default=None, ge=0.0)
    custom_stock_holdings: Optional[list[dict]] = None
    custom_fund_holdings: Optional[list[dict]] = None


def _fetch_user_fund_holdings(sb, user_id: str) -> list[dict]:
    """Fetch fund holdings across user portfolios."""
    try:
        ports = sb.table("portfolios").select("id").eq("user_id", user_id).execute()
        port_ids = [p["id"] for p in (ports.data or [])]
        if port_ids:
            res_f = sb.table("fund_holdings").select("*").in_("portfolio_id", port_ids).execute()
            return res_f.data or []
    except Exception as e:
        logger.warning("Could not fetch fund_holdings: %s", e)
    return []


@router.post("/plan")
def create_rebalance_plan(
    body: RebalancePlanRequest,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Skapar en ren och handlingsbar rebalanseringsplan."""
    stock_holdings = body.custom_stock_holdings
    fund_holdings = body.custom_fund_holdings

    # Hämta från databasen om inte anroparen skickade med egna innehav
    if stock_holdings is None:
        try:
            res = sb.table("portfolio_holdings").select("*").eq("user_id", user.id).execute()
            stock_holdings = res.data or []
        except Exception as e:
            logger.warning("Could not fetch portfolio_holdings: %s", e)
            stock_holdings = []

    if fund_holdings is None:
        fund_holdings = _fetch_user_fund_holdings(sb, user.id)

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
def get_rebalance_overview(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Snabböversikt av aktuell fördelning mellan basfonder och aktier."""
    try:
        res = sb.table("portfolio_holdings").select("*").eq("user_id", user.id).execute()
        stock_holdings = res.data or []
    except Exception as e:
        logger.warning("Could not fetch portfolio_holdings: %s", e)
        stock_holdings = []

    fund_holdings = _fetch_user_fund_holdings(sb, user.id)

    alloc = calculate_portfolio_allocation(stock_holdings, fund_holdings)
    return {
        "allocation": alloc,
        "is_balanced": abs(alloc["funds_pct"] - 60.0) <= 5.0,
        "drift_pct": round(alloc["funds_pct"] - 60.0, 1),
    }
