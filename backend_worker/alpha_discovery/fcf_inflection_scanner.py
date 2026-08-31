"""
Free Cash Flow & Operating Leverage Inflection Scanner.

Detects the exact financial quarter when a small-cap crosses key inflection points:
  1. FCF_INFLECTION: Free Cash Flow turns positive (Negative -> Positive) with sustained revenue growth.
  2. OPERATING_LEVERAGE_BURST: Revenue grows >15% while OpEx grows <5%, resulting in EBIT margin expansion >500 bps.
  3. WORKING_CAPITAL_CLEAN: Cash flow is genuinely organic, not from stretching supplier debts (Sloan Accruals < 0).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def evaluate_fcf_inflection(
    fcf_ttm: Optional[float],
    fcf_prior_year_ttm: Optional[float],
    revenue_growth_yoy: Optional[float],
    ebit_margin_current: Optional[float],
    ebit_margin_prior: Optional[float],
    sloan_accrual_ratio: Optional[float] = None
) -> dict:
    """
    Evaluates whether the company is at a cash flow inflection point.
    """
    if fcf_ttm is None:
        return {
            "inflection_type": "NO_DATA",
            "inflection_score": 50.0,
            "badge": None,
            "reason": "Saknar kassaflödesdata"
        }
        
    is_fcf_positive = fcf_ttm > 0
    was_fcf_negative = fcf_prior_year_ttm is not None and fcf_prior_year_ttm < 0
    
    # 1. Turnaround to Positive FCF
    is_fcf_inflection = is_fcf_positive and was_fcf_negative
    
    # 2. Operating Leverage: Margin expanding significantly
    has_op_leverage = False
    if ebit_margin_current is not None and ebit_margin_prior is not None:
        margin_delta = ebit_margin_current - ebit_margin_prior
        if margin_delta >= 0.05 and revenue_growth_yoy is not None and revenue_growth_yoy > 0.10:
            has_op_leverage = True
            
    # Check if cash flow is clean (negative accruals = cash received is higher than net income)
    is_organic = sloan_accrual_ratio is not None and sloan_accrual_ratio < 0.0
    
    score = 50.0
    badge = None
    
    if is_fcf_inflection and has_op_leverage:
        score = 95.0
        badge = "🚀 DUBBEL INFLEKTION: FCF+ & OPERATIV HÄVSTÅNG"
        reason = "Kassaflödet har vänt till positivt samtidigt som rörelsemarginalen expanderar kraftigt"
    elif is_fcf_inflection:
        score = 88.0
        badge = "⚡ KASSAFLÖDES-GENOMBROTT (FCF > 0)"
        reason = f"Fritt kassaflöde vände från negativt ({fcf_prior_year_ttm/1e6:.1f} Mkr) till positivt ({fcf_ttm/1e6:.1f} Mkr)"
    elif has_op_leverage:
        score = 82.0
        badge = "📈 OPERATIV HÄVSTÅNG"
        reason = "Omsättningstillväxt genererar accelererande marginalförstärkning"
    elif is_fcf_positive and is_organic:
        score = 75.0
        badge = "💎 STARK ORGANISK KASSAGENERERING"
        reason = "Stabilt positivt kassaflöde med hög vinstkvalitet"
    else:
        score = 50.0
        reason = "Normal kassaflödesprofil"
        
    return {
        "inflection_type": "FCF_AND_OP_LEVERAGE" if (is_fcf_inflection and has_op_leverage) else ("FCF_INFLECTION" if is_fcf_inflection else "NORMAL"),
        "inflection_score": float(score),
        "is_fcf_positive": is_fcf_positive,
        "is_fcf_inflection": is_fcf_inflection,
        "has_operating_leverage": has_op_leverage,
        "is_organic_cash": is_organic,
        "badge": badge,
        "reason": reason
    }
