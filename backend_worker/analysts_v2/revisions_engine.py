"""
Analyst Revisions Engine v2 (Phase 4)
Calculates 30d EPS/target revisions, revision breadth, and single-penalty dispersion reliability.
"""
from typing import Optional, Dict, Any
from datetime import date
import numpy as np
from pydantic import BaseModel, Field

class AnalystRevisionOutput(BaseModel):
    listing_id: Optional[str] = None
    snapshot_date: date
    target_mean: Optional[float] = None
    target_revision_30d: Optional[float] = None
    eps_revision_30d: Optional[float] = None
    revision_breadth: float = 0.0  # (up - down) / max(total, 1)
    analyst_count: int = 0
    dispersion_ratio: float = 0.0  # std_dev / mean
    reliability: float = 0.0

def compute_analyst_revisions(
    current_target: Optional[float],
    target_30d_ago: Optional[float],
    current_eps_fy1: Optional[float],
    eps_fy1_30d_ago: Optional[float],
    up_revisions: int = 0,
    down_revisions: int = 0,
    target_std_dev: Optional[float] = None,
    analyst_count: int = 0,
    today: Optional[date] = None
) -> AnalystRevisionOutput:
    today_dt = today or date.today()

    target_rev = None
    if current_target is not None and target_30d_ago is not None and target_30d_ago > 0:
        target_rev = round((current_target / target_30d_ago) - 1.0, 4)

    eps_rev = None
    if current_eps_fy1 is not None and eps_fy1_30d_ago is not None and abs(eps_fy1_30d_ago) > 0.001:
        eps_rev = round((current_eps_fy1 / eps_fy1_30d_ago) - 1.0, 4)

    total_revs = up_revisions + down_revisions
    breadth = (up_revisions - down_revisions) / max(total_revs, 1) if total_revs > 0 else 0.0

    disp_ratio = 0.0
    if target_std_dev is not None and current_target is not None and current_target > 0:
        disp_ratio = round(target_std_dev / current_target, 4)

    # Single-penalty dispersion reliability calculation
    # Base reliability from analyst count
    if analyst_count == 0:
        rel = 0.0
    elif analyst_count <= 2:
        rel = 0.40
    elif analyst_count <= 5:
        rel = 0.65
    elif analyst_count <= 12:
        rel = 0.85
    else:
        rel = 0.95

    # Single penalty for high dispersion (target disagreement)
    if disp_ratio > 0.30:
        rel *= 0.75
    elif disp_ratio > 0.18:
        rel *= 0.90

    return AnalystRevisionOutput(
        snapshot_date=today_dt,
        target_mean=current_target,
        target_revision_30d=target_rev,
        eps_revision_30d=eps_rev,
        revision_breadth=round(breadth, 4),
        analyst_count=analyst_count,
        dispersion_ratio=disp_ratio,
        reliability=round(rel, 3)
    )
