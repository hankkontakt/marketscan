"""
tenders_tracker.py -- Offentliga Upphandlingar & Ramavtals-Tracker (B2B & Forsvar).

Analyserar offentliga ramavtal och upphandlingsvinster (TED / Doffin / TendSign)
for nordiska och europeiska IT-konsulter och forsvarsbolag (Bouvet, Knowit, Saab, MilDef).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def score_public_tenders(
    tender_volume_msek: Optional[float],
    annual_revenue_msek: Optional[float],
    has_multiyear_framework: bool = False,
    is_defense_or_critical_gov: bool = False,
) -> dict:
    """Beraknar poang och flaggor for offentliga upphandlingar och ramavtal.

    Returnerar:
      - tender_score_z: 0 till 100
      - tender_exposure_pct: float
      - flags: list[str]
    """
    res = {
        "tender_score_z": 50.0,
        "tender_exposure_pct": 0.0,
        "flags": [],
    }

    if tender_volume_msek is None or annual_revenue_msek is None or annual_revenue_msek <= 0:
        if has_multiyear_framework:
            res["tender_score_z"] = 65.0
            res["flags"].append("MULTIYEAR_FRAMEWORK_AGREEMENT")
        return res

    vol = max(0.0, float(tender_volume_msek))
    rev = float(annual_revenue_msek)
    exposure = (vol / rev) * 100.0
    res["tender_exposure_pct"] = round(exposure, 1)

    score = 50.0
    if exposure >= 40.0:
        score += 25.0
        res["flags"].append("STRONG_PUBLIC_SECTOR_MOAT")
    elif exposure >= 20.0:
        score += 15.0
        res["flags"].append("SIGNIFICANT_GOV_CONTRACTS")
    elif exposure < 5.0 and not has_multiyear_framework:
        score -= 5.0

    if has_multiyear_framework:
        score += 10.0
        res["flags"].append("MULTIYEAR_FRAMEWORK_AGREEMENT")

    if is_defense_or_critical_gov:
        score += 10.0
        res["flags"].append("CRITICAL_INFRASTRUCTURE_SUPPLIER")

    res["tender_score_z"] = round(min(100.0, max(0.0, score)), 1)
    return res
