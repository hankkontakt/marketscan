"""
Portfolio Construction & Optimizer v2 (Phase 11)
Translates MasterRank v2 alphas, RiskState, SetupState timing, and liquidity capacity into target portfolio weights.
"""
from typing import Dict, List, Any, Optional
import numpy as np
from pydantic import BaseModel, Field

class PortfolioCandidate(BaseModel):
    ticker: str
    master_rank: float
    setup_state: str = "NEUTRAL"
    risk_state: str = "MEDIUM"
    data_grade: str = "B"
    sector: Optional[str] = "General"
    current_weight: float = 0.0
    median_adv_usd_20d: float = 1_000_000.0

class TargetWeightResult(BaseModel):
    ticker: str
    target_weight: float
    current_weight: float
    delta_weight: float
    action: str  # 'BUY', 'SELL', 'HOLD', 'TRIM'
    reason: str

class PortfolioOptimizationResult(BaseModel):
    target_weights: List[TargetWeightResult]
    total_allocated: float
    cash_weight: float
    turnover: float
    warnings: List[str] = Field(default_factory=list)

def optimize_portfolio_v2(
    candidates: List[PortfolioCandidate],
    max_position_weight: float = 0.10,
    max_sector_weight: float = 0.25,
    portfolio_aum_usd: float = 100_000.0,
    target_positions_count: int = 15
) -> PortfolioOptimizationResult:
    warnings = []
    eligible = []

    # 1. Filter candidates by DataGrade and Risk
    for c in candidates:
        if c.data_grade in ("E", "F"):
            warnings.append(f"Excluded {c.ticker}: Low DataGrade ({c.data_grade})")
            continue
        if c.risk_state == "VERY_HIGH":
            warnings.append(f"Excluded {c.ticker}: VERY_HIGH risk state")
            continue
        if c.setup_state == "DAMAGED" and c.current_weight == 0.0:
            warnings.append(f"Deferred {c.ticker}: DAMAGED setup state (waiting for stabilization)")
            continue
        eligible.append(c)

    if not eligible:
        return PortfolioOptimizationResult(
            target_weights=[],
            total_allocated=0.0,
            cash_weight=1.0,
            turnover=0.0,
            warnings=["No eligible candidates met investability criteria"]
        )

    # 2. Score alpha and timing adjustment
    scores = []
    for c in eligible:
        alpha = max(0.0, c.master_rank - 50.0)
        # Timing multiplier
        timing_mult = 1.0
        if c.setup_state in ("CONFIRMED", "PULLBACK"):
            timing_mult = 1.15
        elif c.setup_state == "EXTENDED":
            timing_mult = 0.70
        elif c.setup_state == "EVENT_RISK":
            timing_mult = 0.80

        scores.append(alpha * timing_mult)

    # Top N selection
    top_indices = np.argsort(scores)[::-1][:target_positions_count]
    selected = [eligible[i] for i in top_indices if scores[i] > 0]

    if not selected:
        return PortfolioOptimizationResult(
            target_weights=[],
            total_allocated=0.0,
            cash_weight=1.0,
            turnover=0.0,
            warnings=["No candidates had positive alpha"]
        )

    # 3. Compute base raw weights proportional to score
    sel_scores = np.array([scores[eligible.index(c)] for c in selected])
    total_score = np.sum(sel_scores)
    raw_weights = sel_scores / total_score if total_score > 0 else np.ones(len(selected)) / len(selected)

    # 4. Apply position and sector constraints
    weights = np.minimum(raw_weights, max_position_weight)

    # Liquidity capacity constraint: position_usd <= 2% of 20d ADV
    for i, c in enumerate(selected):
        max_liq_usd = c.median_adv_usd_20d * 0.02
        max_liq_weight = max_liq_usd / max(portfolio_aum_usd, 1.0)
        weights[i] = min(weights[i], max_liq_weight)

    # Renormalize if total exceeds 1.0
    if np.sum(weights) > 1.0:
        weights = weights / np.sum(weights)

    total_allocated = float(np.sum(weights))
    cash_weight = max(0.0, 1.0 - total_allocated)

    results = []
    turnover = 0.0

    for c, w in zip(selected, weights):
        target_w = round(float(w), 4)
        delta_w = round(target_w - c.current_weight, 4)
        turnover += abs(delta_w) / 2.0

        if delta_w > 0.01:
            action = "BUY"
            reason = f"Positive alpha ({c.master_rank:.0f}) and valid {c.setup_state} setup"
        elif delta_w < -0.01:
            action = "TRIM"
            reason = "Rebalance position closer to target"
        else:
            action = "HOLD"
            reason = "Position within target tolerance"

        results.append(TargetWeightResult(
            ticker=c.ticker,
            target_weight=target_w,
            current_weight=c.current_weight,
            delta_weight=delta_w,
            action=action,
            reason=reason
        ))

    return PortfolioOptimizationResult(
        target_weights=results,
        total_allocated=round(total_allocated, 4),
        cash_weight=round(cash_weight, 4),
        turnover=round(turnover, 4),
        warnings=warnings
    )
