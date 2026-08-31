"""
Hierarchical Analyst Credibility & Target Revision Engine.

Differentiates:
  - TIER_1_INDEPENDENT: Carnegie, ABG Sundal Collier, SEB, Handelsbanken, DNB, Kepler, Pareto, Nordea (Weight: 1.0)
  - COMMISSIONED_RESEARCH: Redeye, Analyst Group, Carlsquare, Penser, TradeVenue (Weight: 0.5)

For commissioned research:
  - Strips the structural +50% target price optimism bias.
  - Measures RELATIVE DELTA (Base Case raised or lowered) rather than absolute target.
  - Detects INITIATION_OF_COVERAGE (First time coverage for a previously dark stock).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

TIER_1_BANKS = {
    "carnegie", "abg", "abg sundal collier", "seb", "handelsbanken",
    "dnb", "dnb markets", "kepler", "kepler cheuvreux", "pareto",
    "pareto securities", "nordea", "danske bank", "swedbank"
}

COMMISSIONED_HOUSES = {
    "redeye", "analyst group", "carlsquare", "penser", "erik penser",
    "tradevenue", "västra hamnen", "kalqyl", "stockpicker"
}


@dataclass
class AnalystReportItem:
    house_name: str
    ticker: str
    target_price: Optional[float]
    prev_target_price: Optional[float]
    recommendation: Optional[str]  # 'BUY', 'HOLD', 'SELL', 'BASE_CASE'
    is_initiation: bool = False


def classify_house(house_name: str) -> tuple[str, float]:
    """Returns (house_category, credibility_weight)."""
    h_lower = house_name.lower().strip()
    if any(b in h_lower for b in TIER_1_BANKS):
        return ("TIER_1_INDEPENDENT", 1.0)
    elif any(c in h_lower for c in COMMISSIONED_HOUSES):
        return ("COMMISSIONED_RESEARCH", 0.5)
    return ("SPECIALIST_OTHER", 0.75)


def score_analyst_revisions(
    current_price: Optional[float],
    reports: list[AnalystReportItem]
) -> dict:
    """
    Computes an unbiased composite analyst momentum score.
    """
    if not reports or current_price is None or current_price <= 0:
        return {
            "analyst_surge_score": 50.0,
            "has_initiation": False,
            "revision_direction": "NEUTRAL",
            "badge": None,
            "summary": "Inga färska analysuppdateringar"
        }
        
    weighted_upsides = []
    revisions = []
    has_initiation = False
    initiator_name = None
    
    for r in reports:
        cat, weight = classify_house(r.house_name)
        
        if r.is_initiation:
            has_initiation = True
            initiator_name = r.house_name
            
        # Target price upside
        if r.target_price and r.target_price > 0:
            raw_upside = (r.target_price - current_price) / current_price
            
            # Commissioned research discount: If paid research claims +80% upside, calibrate to +40%
            adjusted_upside = raw_upside if cat == "TIER_1_INDEPENDENT" else raw_upside * 0.60
            weighted_upsides.append((adjusted_upside, weight))
            
        # Revision Delta
        if r.target_price and r.prev_target_price and r.prev_target_price > 0:
            delta_pct = (r.target_price - r.prev_target_price) / r.prev_target_price
            revisions.append((delta_pct, weight))
            
    # Calculate composite upside
    avg_upside = 0.0
    if weighted_upsides:
        tot_w = sum(w for _, w in weighted_upsides)
        avg_upside = sum(u * w for u, w in weighted_upsides) / tot_w
        
    # Calculate revision score
    rev_delta = 0.0
    if revisions:
        tot_rw = sum(w for _, w in revisions)
        rev_delta = sum(d * w for d, w in revisions) / tot_rw
        
    # Base score
    score = 50.0 + (avg_upside * 60.0) + (rev_delta * 40.0)
    if has_initiation:
        score += 15.0  # Initiation boost for previously dark stock
        
    final_score = float(max(10.0, min(99.0, score)))
    
    badge = None
    if has_initiation:
        badge = f"⭐ NYBEVAKNING INLEDS: {initiator_name}"
    elif rev_delta >= 0.15:
        badge = f"📈 RIKTKURS HÖJS: +{round(rev_delta * 100, 1)}%"
    elif avg_upside >= 0.35:
        badge = f"🎯 HÖG ANALYTIKERUPPSIDA: +{round(avg_upside * 100, 1)}%"
        
    return {
        "analyst_surge_score": round(final_score, 1),
        "has_initiation": has_initiation,
        "calibrated_upside_pct": round(avg_upside * 100.0, 1),
        "target_revision_pct": round(rev_delta * 100.0, 1) if revisions else None,
        "badge": badge,
        "summary": f"Analysrapporter: {len(reports)} st. Kalibrerad uppsida: +{round(avg_upside * 100, 1)}%"
    }
