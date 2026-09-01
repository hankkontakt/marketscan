"""
forensic_audit.py — API Router för 1-Klicks Forensisk Delårs-Audit.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_user_supabase
from apps.api.core.ai_cache import get_cached, set_cache
from apps.api.core.deepseek_client import call_deepseek

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["Forensic Audit"])


class ForensicAuditRequest(BaseModel):
    company_name: Optional[str] = ""
    report_text: Optional[str] = None
    period_label: Optional[str] = "LTM"


class ForensicAuditResponse(BaseModel):
    ticker: str
    company_name: str
    traffic_light: str
    audit_score: int
    dilution_emission_risk: str
    cash_runway_months: Optional[float] = None
    capitalized_rd_pct_of_ebit: Optional[float] = None
    real_ebit_adjusted_msek: Optional[float] = None
    covenant_and_debt_risks: list[str] = []
    accounting_red_flags: list[str] = []
    positive_qualities: list[str] = []
    verdict_summary_sv: str
    cached_date: str


SYSTEM_PROMPT = (
    "Du är en forensisk chefsrevisor och finansanalytiker specialiserad på nordiska börsbolag. "
    "Ditt uppdrag är att skydda investerare från dolda minor, aggressiv redovisning och förestående emissioner.\n"
    "Svara ENBART i strikt JSON-format."
)


@router.post("/forensic-audit/{ticker}", response_model=ForensicAuditResponse)
async def get_forensic_audit(
    ticker: str,
    body: ForensicAuditRequest,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Kör 1-klicks forensisk audit på delårsrapporten med DeepSeek V4 Pro."""
    t = ticker.upper().strip()
    today = date.today().isoformat()
    cache_key = f"forensic_audit:{t}:{body.period_label}:{today}"

    cached = get_cached(cache_key, sb)
    if cached:
        return cached

    # Om report_text inte skickades med, hämta bolagets senaste kända profil / fakta
    text_to_audit = body.report_text
    if not text_to_audit or len(text_to_audit.strip()) < 50:
        try:
            res = sb.table("company_profiles").select("*").eq("ticker", t).execute()
            if res.data:
                prof = res.data[0]
                text_to_audit = (
                    f"Bolagsfakta för {prof.get('name', t)} ({t}):\n"
                    f"Beskrivning: {prof.get('description', '')}\n"
                    f"Sektor: {prof.get('sector', '')}\n"
                    f"Omsättning TTM: {prof.get('revenue_ttm', 'Okänd')} MSEK\n"
                    f"EBIT TTM: {prof.get('ebit_ttm', 'Okänd')} MSEK\n"
                )
        except Exception as e:
            logger.warning("Could not fetch company profile for forensic audit: %s", e)

    if not text_to_audit:
        text_to_audit = f"Finansiell granskning av {body.company_name or t} ({t})."

    company_name = body.company_name or t
    user_prompt = f"""Granska följande utdrag ur delårsrapporten/årsredovisningen för {company_name} ({t}).

Svara STRICT i följande JSON-format utan markdown-block:
{{
  "ticker": "{t}",
  "company_name": "{company_name}",
  "traffic_light": "GRÖN",
  "audit_score": 75,
  "dilution_emission_risk": "LÅG",
  "cash_runway_months": null,
  "capitalized_rd_pct_of_ebit": null,
  "real_ebit_adjusted_msek": null,
  "covenant_and_debt_risks": [],
  "accounting_red_flags": [],
  "positive_qualities": [],
  "verdict_summary_sv": "Sammanfattning på 3-4 meningar."
}}

RAPPORTTEXT:
{text_to_audit[:15000]}
"""
    try:
        raw_resp = await call_deepseek(SYSTEM_PROMPT, user_prompt, max_tokens=1000, temperature=0.2)
        clean_json = raw_resp.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        parsed = json.loads(clean_json)
    except Exception as e:
        logger.warning("Forensic audit LLM call or JSON parse failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forensisk audit-tjänsten är för närvarande inte tillgänglig.",
        )

    response_data = {
        "ticker": t,
        "company_name": parsed.get("company_name", company_name),
        "traffic_light": parsed.get("traffic_light", "GUL"),
        "audit_score": int(parsed.get("audit_score", 70)),
        "dilution_emission_risk": parsed.get("dilution_emission_risk", "MEDEL"),
        "cash_runway_months": parsed.get("cash_runway_months"),
        "capitalized_rd_pct_of_ebit": parsed.get("capitalized_rd_pct_of_ebit"),
        "real_ebit_adjusted_msek": parsed.get("real_ebit_adjusted_msek"),
        "covenant_and_debt_risks": parsed.get("covenant_and_debt_risks", []),
        "accounting_red_flags": parsed.get("accounting_red_flags", []),
        "positive_qualities": parsed.get("positive_qualities", []),
        "verdict_summary_sv": parsed.get("verdict_summary_sv", "Analys slutförd."),
        "cached_date": today,
    }

    try:
        set_cache(cache_key, response_data, sb)
    except Exception as e:
        logger.warning("Failed to cache forensic audit: %s", e)

    return response_data
