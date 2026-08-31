"""
Autonomous Alpha Fusion & Discovery Engine (Guldkorns-Motorn).

Synthesizes:
  1. FCF & Operating Leverage Inflection (Weight: 25%)
  2. Smart Money & Super-Investor Shadowing (Weight: 25%)
  3. Catalyst NLP Legal Order Stream (Weight: 20%)
  4. Hierarchical Analyst Surge & Revision (Weight: 15%)
  5. Wyckoff Stealth Accumulation (Weight: 15%)
  - Subtracts Warrant (TO) Dilution Penalty & Liquidity Penalty

Outputs:
  - alpha_score (0.0 - 100.0)
  - alpha_tier ('TIER_1_ALPHA', 'TIER_2_ALPHA', 'WATCHLIST', 'NEUTRAL')
  - badges (list of human-readable badges for UI)
  - investment_thesis (Concise 1-page structured memo)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_alpha_score(
    ticker: str,
    company_name: str,
    fcf_inflection: dict,
    smart_money: dict,
    catalyst_report: dict,
    analyst_report: dict,
    wyckoff_report: dict,
    warrant_report: dict,
    adtv_sek_20d: Optional[float] = None
) -> dict:
    """
    Computes the composite Alpha Score (Guldkorns-Score).
    """
    s_fcf = fcf_inflection.get("inflection_score", 50.0)
    s_sm = smart_money.get("smart_money_score", 50.0)
    s_cat = catalyst_report.get("catalyst_score", 50.0)
    s_an = analyst_report.get("analyst_surge_score", 50.0)
    s_wyck = wyckoff_report.get("divergence_score", 50.0)
    
    # Base weighted sum
    raw_alpha = (
        0.25 * s_fcf +
        0.25 * s_sm +
        0.20 * s_cat +
        0.15 * s_an +
        0.15 * s_wyck
    )
    
    # Penalties
    dilution_pen = warrant_report.get("dilution_penalty", 0.0)
    
    # Liquidity check (< 200k SEK daily volume makes execution difficult)
    liquidity_pen = 0.0
    is_illiquid = False
    if adtv_sek_20d is not None and adtv_sek_20d < 200_000:
        liquidity_pen = 10.0
        is_illiquid = True
        
    final_score = raw_alpha - dilution_pen - liquidity_pen
    final_score = float(max(10.0, min(99.0, final_score)))
    
    # Collect all active badges
    badges = []
    if fcf_inflection.get("badge"):
        badges.append(fcf_inflection["badge"])
    if smart_money.get("badge"):
        badges.append(smart_money["badge"])
    if catalyst_report.get("badge") and catalyst_report.get("category") != "GENERAL_PRESS_RELEASE":
        badges.append(catalyst_report["badge"])
    if analyst_report.get("badge"):
        badges.append(analyst_report["badge"])
    if wyckoff_report.get("badge"):
        badges.append(wyckoff_report["badge"])
    if warrant_report.get("overhang_flag"):
        badges.append(f"⚠️ TO-ÖVERHÄNG: {warrant_report['reason']}")
    elif not warrant_report.get("overhang_flag"):
        badges.append("🛡️ TO-REN: Inget Optionsöverhäng")
    if is_illiquid:
        badges.append("💧 LÅG LIKVIDITET (<200 tkr/dag)")
        
    # Determine Alpha Tier
    if final_score >= 78.0 and not warrant_report.get("overhang_flag"):
        tier = "TIER_1_ALPHA"
        verdict = "🔥 GULDKORN (STARK KÖPKANDIDAT)"
    elif final_score >= 68.0:
        tier = "TIER_2_ALPHA"
        verdict = "🟢 HÖG ALPHA-KANDIDAT"
    elif final_score >= 58.0:
        tier = "WATCHLIST"
        verdict = "👀 BEVAKNINGSLISTA"
    else:
        tier = "NEUTRAL"
        verdict = "⚪ NEUTRAL"
        
    # Structured 1-Page Investment Thesis
    thesis_parts = [
        f"### Investeringstes: {company_name} ({ticker})",
        f"**Alpha-Klassificering:** {verdict} (Poäng: {final_score:.1f}/100)",
        "",
        "**Nyckeldrivkrafter & Inflektioner:**",
        f"- **Kassaflöde:** {fcf_inflection.get('reason', 'Normalt')}",
        f"- **Smart Money:** {smart_money.get('reason', 'Ingen förändring')}",
        f"- **Katalysator / Nyheter:** {catalyst_report.get('summary', 'Ingen större order')}",
        f"- **Analytikerbild:** {analyst_report.get('summary', 'Neutral')}",
        f"- **Ägardynamik:** {wyckoff_report.get('reason', 'Neutral')}",
        "",
        "**Strukturell Riskprofil:**",
        f"- Teckningsoptions-risk (TO): {warrant_report.get('reason')}",
        f"- Omsättningslikviditet: {f'{adtv_sek_20d/1e3:.0f} tkr/dag' if adtv_sek_20d else 'OK'}"
    ]
    
    thesis_text = "\n".join(thesis_parts)
    
    return {
        "ticker": ticker,
        "company_name": company_name,
        "alpha_score": round(final_score, 1),
        "alpha_tier": tier,
        "verdict": verdict,
        "badges": badges,
        "is_illiquid": is_illiquid,
        "thesis_memo": thesis_text,
        "subscores": {
            "fcf_inflection": s_fcf,
            "smart_money": s_sm,
            "catalyst_nlp": s_cat,
            "analyst_surge": s_an,
            "wyckoff": s_wyck,
            "dilution_penalty": dilution_pen,
            "liquidity_penalty": liquidity_pen
        }
    }
