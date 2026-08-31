"""
forensic_audit.py — API Router för 1-Klicks Forensisk Delårs-Audit.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_supabase_admin
from apps.api.core.ai_cache import get_cached, set_cache
from backend_worker.forensic_pdf_audit import run_forensic_audit

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


@router.post("/forensic-audit/{ticker}", response_model=ForensicAuditResponse)
async def get_forensic_audit(
    ticker: str,
    body: ForensicAuditRequest,
    user: User = Depends(get_current_user),
    sb_admin=Depends(get_supabase_admin),
):
    """Kör 1-klicks forensisk audit på delårsrapporten med DeepSeek V4 Pro."""
    t = ticker.upper().strip()
    today = date.today().isoformat()
    cache_key = f"forensic_audit:{t}:{body.period_label}:{today}"

    cached = get_cached(cache_key, sb_admin)
    if cached:
        return cached

    # Om report_text inte skickades med, hämta bolagets senaste kända profil / fakta
    text_to_audit = body.report_text
    if not text_to_audit or len(text_to_audit.strip()) < 50:
        # Fallback till strukturerad snapshot om ingen rå PDF skickats
        try:
            res = sb_admin.table("company_profiles").select("*").eq("ticker", t).execute()
            if res.data:
                prof = res.data[0]
                text_to_audit = (
                    f"Bolagsfakta för {prof.get('name', t)} ({t}):\n"
                    f"Beskrivning: {prof.get('description', '')}\n"
                    f"Sektor: {prof.get('sector', '')}\n"
                    f"Omsättning TTM: {prof.get('revenue_ttm', 'Okänd')} MSEK\n"
                    f"EBIT TTM: {prof.get('ebit_ttm', 'Okänd')} MSEK\n"
                )
        except Exception:
            pass

    if not text_to_audit:
        text_to_audit = f"Finansiell granskning av {body.company_name or t} ({t})."

    audit_result = run_forensic_audit(
        report_text=text_to_audit,
        ticker=t,
        company_name=body.company_name or t,
    )

    if not audit_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=audit_result.get("error", "Forensisk audit kunde inte slutföras")
        )

    parsed = audit_result.get("audit", {})
    response_data = {
        "ticker": t,
        "company_name": parsed.get("company_name", body.company_name or t),
        "traffic_light": parsed.get("traffic_light", "GUL"),
        "audit_score": parsed.get("audit_score", 70),
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

    set_cache(cache_key, response_data, sb_admin)
    return response_data
