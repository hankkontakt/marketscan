"""
forensic_shield.py — Central Forensisk Skyddsmotor (Bad Apple & Hidden Trap Shield).

Kombinerar kvantitativa kassaflödesfundamenta med kvalitativ AI-forensik:
  1. Sloan Accrual Anomaly (Bokförd vinst utan kassaflöde)
  2. Cash Runway & Emissionsrisk (< 6 månaders likviditet)
  3. Aktieutspädningstakt (> 10 % nya aktier YoY)
  4. Bruttomarginalerosion (> 3 procentenheters fall YoY)
  5. AI-identifierade dolda skulder, covenants och revisionsanmärkningar

Deterministisk och 100% testbar utan nätverksberoenden.
"""
from __future__ import annotations

import math
from typing import Optional


# Tröskelvärden för forensiska larm
SLOAN_ACCRUAL_THRESHOLD = 0.10      # >10% av tillgångarna är redovisade accruals
CRITICAL_RUNWAY_MONTHS = 6.0        # <6 månaders kassa kvar
DILUTION_THRESHOLD_PCT = 10.0       # >10% fler aktier YoY
MARGIN_EROSION_THRESHOLD_PCT = -3.0 # >3% fall i bruttomarginal
HIGH_FCF_YIELD_THRESHOLD = 0.08     # >8% kassaflödesavkastning (super-compounder)


def audit_company_forensics(
    fundamentals: Optional[dict] = None,
    ai_forensics: Optional[dict] = None,
    ticker: str = "",
    sector: Optional[str] = None
) -> dict:
    """Genomför en fullständig forensisk revision och beräknar hälsopoäng samt maxtak.

    Returnerar:
      - forensic_health_score: 0 till 100
      - forensic_flags: list[str]
      - tier_cap: "T1" | "T2" | "T3" | "DISQUALIFIED"
      - rank_penalty: float (avdrag som ska appliceras i MasterRank)
      - rank_bonus: float (bonus för extraordinärt kassaflöde)
      - is_distressed: bool
    """
    fund = fundamentals or {}
    ai = ai_forensics or {}
    
    flags = list(fund.get("forensic_flags", []))
    ai_flags = list(ai.get("forensic_red_flags", [])) + list(ai.get("covenant_or_debt_warnings", []))
    
    score = 80.0  # Basvärde: neutral till god forensisk hälsa
    rank_penalty = 0.0
    rank_bonus = 0.0
    tier_cap = "T1"
    is_distressed = False

    # 1. Sloan Accrual Anomaly
    sloan = fund.get("sloan_accrual_ratio")
    if sloan is not None:
        if sloan > SLOAN_ACCRUAL_THRESHOLD:
            if "ACCRUAL_WARNING" not in flags:
                flags.append("ACCRUAL_WARNING")
            score -= 20.0
            rank_penalty += 8.0
        elif sloan < -0.05:
            # Mycket stark kassaflödeskonvertering (kassaflödet är högre än bokförd vinst)
            score += 10.0
            rank_bonus += 2.0

    # 2. Cash Runway & Emissionsfälla (Akut likviditetsbrist)
    runway = fund.get("cash_runway_months")
    if runway is not None:
        if runway < CRITICAL_RUNWAY_MONTHS:
            if "DILUTION_EMISSION_RISK" not in flags:
                flags.append("DILUTION_EMISSION_RISK")
            score -= 40.0
            rank_penalty += 15.0
            tier_cap = "T3"  # Kan aldrig nå T1 eller T2
            is_distressed = True
        elif runway < 12.0:
            if "TIGHT_LIQUIDITY" not in flags:
                flags.append("TIGHT_LIQUIDITY")
            score -= 15.0
            rank_penalty += 5.0

    # 3. Historisk Utspädningstakt (Tryckpress för nya aktier)
    dilution = fund.get("dilution_rate_pct")
    if dilution is not None and dilution > DILUTION_THRESHOLD_PCT:
        if "SHARE_DILUTION_WARNING" not in flags:
            flags.append("SHARE_DILUTION_WARNING")
        score -= 20.0
        rank_penalty += min(15.0, (dilution - DILUTION_THRESHOLD_PCT) * 0.5 + 5.0)
        if dilution > 30.0:
            tier_cap = "T3"

    # 4. Bruttomarginalerosion (Prispress / tappad konkurrenskraft)
    margin_trend = fund.get("gross_margin_trend_pct")
    if margin_trend is not None and margin_trend < MARGIN_EROSION_THRESHOLD_PCT:
        if "MARGIN_EROSION" not in flags:
            flags.append("MARGIN_EROSION")
        score -= 15.0
        rank_penalty += 5.0

    # 5. Fritt Kassaflöde Belöning (FCF Yield)
    fcf_y = fund.get("fcf_yield")
    if fcf_y is not None:
        if fcf_y >= HIGH_FCF_YIELD_THRESHOLD:
            if "HIGH_FCF_YIELD" not in flags:
                flags.append("HIGH_FCF_YIELD")
            score += 15.0
            rank_bonus += 4.0
        elif fcf_y < -0.15:
            # Extremt negativt kassaflöde (>15% av börsvärdet bränns per år)
            if "EXTREME_CASH_BURN" not in flags:
                flags.append("EXTREME_CASH_BURN")
            score -= 25.0
            rank_penalty += 10.0

    # 6. AI-Kvalitativa Varningar
    ai_risk = ai.get("dilution_emission_risk_level")
    if ai_risk == "MYCKET_HÖG":
        if "AI_HIGH_DILUTION_RISK" not in flags:
            flags.append("AI_HIGH_DILUTION_RISK")
        score -= 30.0
        rank_penalty += 12.0
        tier_cap = "T3"
        is_distressed = True

    if ai.get("real_ebit_without_capitalization_msek") is not None and ai.get("ebit_reported_msek") is not None:
        rep = ai.get("ebit_reported_msek")
        real = ai.get("real_ebit_without_capitalization_msek")
        if rep > 0 and real < 0:
            # Bolaget visar bokförd vinst men är i själva verket olönsamt utan aktiverad FoU!
            if "CAPITALIZED_EXPENSE_WARNING" not in flags:
                flags.append("CAPITALIZED_EXPENSE_WARNING")
            score -= 25.0
            rank_penalty += 10.0
            tier_cap = "T3"

    score = max(0.0, min(100.0, score))

    if score < 30.0:
        tier_cap = "DISQUALIFIED"
        is_distressed = True

    return {
        "ticker": ticker,
        "forensic_health_score": round(score, 1),
        "forensic_flags": flags,
        "ai_flags": ai_flags,
        "tier_cap": tier_cap,
        "rank_penalty": round(rank_penalty, 2),
        "rank_bonus": round(rank_bonus, 2),
        "is_distressed": is_distressed
    }
