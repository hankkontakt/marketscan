"""
AI Research v2 Router (Phase 9)
Deterministic-grounded AI synthesis & narrative generation.
Strict grounding: AI cannot hallucinate or override canonical numbers/scores.
"""
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from apps.api.dependencies import get_supabase
from apps.api.routers.decisions_v2 import get_stock_decision
from apps.api.schemas.decision_v2 import StockDecisionV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/ai", tags=["ai-research-v2"])

class ThesisReportSection(BaseModel):
    title: str
    content: str
    bullet_points: List[str] = Field(default_factory=list)

class AIThesisReport(BaseModel):
    ticker: str
    company_name: str
    master_rank: float
    thesis_band: str
    setup_state: str
    risk_state: str
    data_grade: str
    generated_at: str
    model_version: str = "ai_research_v2"
    executive_summary: str
    sections: List[ThesisReportSection]
    grounded_canonical_facts: Dict[str, Any]

def _generate_grounded_thesis_narrative(decision: StockDecisionV2) -> AIThesisReport:
    """
    Deterministic rule-guided generator that anchors the AI narrative strictly to canonical scores.
    """
    mr = decision.master_rank
    setup = decision.setup
    risk = decision.risk
    dg = decision.data_grade

    pos_drivers_str = ", ".join([f"{d.label_sv} (+{d.contribution:.1f}p)" for d in decision.positive_drivers[:3]]) or "Inga starka enskilda positiva avvikelser"
    neg_drivers_str = ", ".join([f"{d.label_sv} ({d.contribution:.1f}p)" for d in decision.negative_drivers[:2]]) or "Inga akuta negativa motvindar"

    # Executive Summary
    summary = (
        f"{decision.name} ({decision.ticker}) erhåller ett MasterRank på {mr.score:.0f}/100 "
        f"vilket placerar aktien i kategorin '{mr.band.value}'. "
        f"Den tekniska prisbilden visar '{setup.ui_label_sv}' medan den övergripande riskprofilen bedöms som '{risk.state.value}' "
        f"(främst präglad av {risk.dominant_risk.replace('_', ' ').lower()}). "
        f"Datakvaliteten är klassad som Grade {dg.grade.value} med {(dg.weighted_coverage*100):.0f}% faktortäckning."
    )

    # Sections
    sections = [
        ThesisReportSection(
            title="1. Huvudtes & Investeringshorisont (3-12 mån)",
            content=(
                f"Den långsiktiga investeringstesen baseras på en systematisk utvärdering av 7 strukturella faktorer. "
                f"Aktien uppvisar starkast stöd inom: {pos_drivers_str}."
            ),
            bullet_points=[
                f"MasterRank Score: {mr.score:.0f}/100 (Topp {100 - mr.segment_percentile:.0f}% i segmentet)",
                f"Kvalitet och reliabilitet: {(dg.weighted_coverage*100):.0f}% av faktormodellen är verifierad med hög datakvalitet.",
            ]
        ),
        ThesisReportSection(
            title="2. Timing & Setup-kontext (5-60 dagar)",
            content=(
                f"Kortsiktig prisstruktur klassificeras som '{setup.ui_label_sv}'. "
                f"Detta speglar den aktuella jämvikten mellan momentum och rekyl utan att förvränga den fundamentala kvalitetstesen."
            ),
            bullet_points=[
                f"Setup-status: {setup.state.value}",
                f"Orsakskoder: {', '.join(setup.reason_codes) if setup.reason_codes else 'Normal trendstruktur'}"
            ]
        ),
        ThesisReportSection(
            title="3. Riskanalys & Känslighet",
            content=(
                f"Riskmotorn identifierar '{risk.dominant_risk.replace('_', ' ')}' som den primära osäkerhetsfaktorn. "
                f"Väsentliga motvindar i modellen: {neg_drivers_str}."
            ),
            bullet_points=[
                f"Likviditetsbetyg: Grade {risk.liquidity_grade}",
                f"Riskflaggor: {', '.join(risk.risk_flags) if risk.risk_flags else 'Inga förhöjda riskflaggor'}"
            ]
        ),
        ThesisReportSection(
            title="4. Slutsats & Handlingsplan",
            content=(
                f"För en systematisk investerare innebär profilen att {decision.ticker} "
                f"{'är en attraktiv kandidat för portföljallokering givet bekräftad trend' if mr.score >= 75 and setup.state.value in ('CONFIRMED', 'PULLBACK') else 'bör bevakas för förbättrad timing eller minskad risk innan ökad exponering'}."
            ),
            bullet_points=[
                f"Aktuellt pris: {decision.price.value:.2f} {decision.price.currency}",
                f"Övervakningsrekommendation: Kontrollera nästa rapport och utveckling i estimatrevideringar."
            ]
        )
    ]

    return AIThesisReport(
        ticker=decision.ticker,
        company_name=decision.name,
        master_rank=mr.score,
        thesis_band=mr.band.value,
        setup_state=setup.state.value,
        risk_state=risk.state.value,
        data_grade=dg.grade.value,
        generated_at=datetime.now(timezone.utc).isoformat(),
        executive_summary=summary,
        sections=sections,
        grounded_canonical_facts={
            "price": decision.price.value,
            "currency": decision.price.currency,
            "master_rank": mr.score,
            "thesis_band": mr.band.value,
            "setup_state": setup.state.value,
            "risk_state": risk.state.value,
            "liquidity_grade": risk.liquidity_grade,
            "data_grade": dg.grade.value,
            "positive_drivers": [d.model_dump() for d in decision.positive_drivers],
            "negative_drivers": [d.model_dump() for d in decision.negative_drivers]
        }
    )

@router.get("/thesis-report/{ticker}", response_model=AIThesisReport)
async def get_ai_thesis_report(ticker: str, sb=Depends(get_supabase)):
    """
    Grounded AI Thesis Report for a single stock.
    Anchored strictly to canonical server decision outputs.
    """
    stock_decision = await get_stock_decision(ticker=ticker, sb=sb)
    report = _generate_grounded_thesis_narrative(stock_decision)
    return report
