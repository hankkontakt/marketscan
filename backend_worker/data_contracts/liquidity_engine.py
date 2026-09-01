"""
Liquidity Engine (Phase 2 - P0)
Calculates real listing-level Average Daily Volume (ADV), zero-volume penalty, and LiquidityGrade (A-F).
Eliminates the 'liquidity_grade NULL for 100% of rows' issue.
"""
from typing import Optional, List, Dict
import numpy as np
from pydantic import BaseModel, Field

class LiquiditySnapshot(BaseModel):
    listing_id: Optional[str] = None
    ticker: str
    currency: str = "USD"
    median_adv_shares_20d: float
    median_adv_usd_20d: float
    zero_volume_days_20d: int = 0
    estimated_spread_bps: float = 10.0
    liquidity_grade: str  # 'A', 'B', 'C', 'D', 'E', 'F'
    is_tradable_for_retail: bool = True
    is_tradable_for_institutions: bool = True

def compute_liquidity_grade(
    daily_volumes: List[float],
    daily_prices: List[float],
    fx_to_usd: float = 1.0,
    currency: str = "USD"
) -> LiquiditySnapshot:
    """
    Calculate deterministic liquidity metrics from recent daily volume and price history.
    """
    if not daily_volumes or not daily_prices or len(daily_volumes) == 0:
        return LiquiditySnapshot(
            ticker="",
            currency=currency,
            median_adv_shares_20d=0.0,
            median_adv_usd_20d=0.0,
            zero_volume_days_20d=20,
            estimated_spread_bps=200.0,
            liquidity_grade="F",
            is_tradable_for_retail=False,
            is_tradable_for_institutions=False
        )

    # 20d window
    vols = np.array(daily_volumes[-20:], dtype=float)
    prices = np.array(daily_prices[-20:], dtype=float)

    zero_vols = int(np.sum(vols <= 0))
    daily_turnover_local = vols * prices
    daily_turnover_usd = daily_turnover_local * fx_to_usd

    med_shares = float(np.nanmedian(vols)) if len(vols) > 0 else 0.0
    med_turnover_usd = float(np.nanmedian(daily_turnover_usd)) if len(daily_turnover_usd) > 0 else 0.0

    # Determine grade
    # Grade A: ADV >= $10M
    # Grade B: $2M <= ADV < $10M
    # Grade C: $500k <= ADV < $2M
    # Grade D: $100k <= ADV < $500k
    # Grade E: $20k <= ADV < $100k
    # Grade F: < $20k or > 3 zero-volume days
    if zero_vols >= 4 or med_turnover_usd < 20_000:
        grade = "F"
        est_spread = 250.0
        inst_ok = False
        retail_ok = False
    elif zero_vols >= 2 or med_turnover_usd < 100_000:
        grade = "E"
        est_spread = 120.0
        inst_ok = False
        retail_ok = True
    elif med_turnover_usd < 500_000:
        grade = "D"
        est_spread = 60.0
        inst_ok = False
        retail_ok = True
    elif med_turnover_usd < 2_000_000:
        grade = "C"
        est_spread = 30.0
        inst_ok = True
        retail_ok = True
    elif med_turnover_usd < 10_000_000:
        grade = "B"
        est_spread = 15.0
        inst_ok = True
        retail_ok = True
    else:
        grade = "A"
        est_spread = 5.0
        inst_ok = True
        retail_ok = True

    return LiquiditySnapshot(
        ticker="",
        currency=currency,
        median_adv_shares_20d=med_shares,
        median_adv_usd_20d=med_turnover_usd,
        zero_volume_days_20d=zero_vols,
        estimated_spread_bps=est_spread,
        liquidity_grade=grade,
        is_tradable_for_retail=retail_ok,
        is_tradable_for_institutions=inst_ok
    )
