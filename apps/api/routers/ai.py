"""
AI endpoints: NL screener parser, stock analysis, Analyskommittén, portfolio coach.
All responses are cached per ticker/day to minimize token spend.
"""
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from apps.api.core.ai_cache import get_cached, set_cache
from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_supabase
from pydantic import Field

router = APIRouter(prefix="/ai", tags=["ai"])

# ─── Schemas ──────────────────────────────────────────────────────────────────

class NLFilterRequest(BaseModel):
    query: str


class CommitteeRequest(BaseModel):
    ticker: str
    stock_data: dict


class PortfolioCoachRequest(BaseModel):
    question: str
    portfolio_context: dict
    history: list[dict] = []


class CommitteeResponse(BaseModel):
    ticker: str
    committee: list[dict]
    synthesis: str


class PortfolioCoachResponse(BaseModel):
    response: str


class EarningsResponseOut(BaseModel):
    ticker: str
    earnings: list[dict]


# ─── NL filter parser ─────────────────────────────────────────────────────────

NL_FILTER_SYSTEM = """Du är en aktiescreener-assistent. Tolka användarens naturliga
fråga och returnera ENDAST ett JSON-objekt med filtervärden ur listan:
{
  "segments": ["large_cap"|"mid_cap"|"small_cap"|"micro_cap"],
  "sector": "Industri"|"Teknik"|"Finans"|"Hälsovård"|"Energi"|"Fastighet"|"Konsument"|null,
  "entry_signal": "STARK"|"OK"|"VÄNTA"|"EJ_AKTUELL"|null,
  "trend_signal": "Upptrend"|"Sidled"|"Nedtrend"|null,
  "score_min": 0-100|null,
  "piotroski_min": 0-9|null,
  "pe_max": tal|null,
  "roe_min": 0-1 som decimal|null,
  "dividend_yield_min": 0-1 som decimal|null,
  "exclude_low_liquidity": true|false
}
Returnera bara JSON. Inga förklaringar. Utelämna nycklar utan värde."""


@router.post("/parse-filter")
async def parse_nl_filter(body: NLFilterRequest):
    """Parse natural language query into screener filter params."""
    result = await _call_ai(NL_FILTER_SYSTEM, body.query)
    try:
        # Strip markdown fences if present
        clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {}


# ─── Analyskommittén → output schema ──────────────────────────────

class CommitteeMember(BaseModel):
    name: str
    analysis: str


class CommitteeSynthesis(BaseModel):
    verdict: str
    confidence: int
    summary: str
    disagreement: bool
    disagreement_note: str | None = None


class CommitteeOutput(BaseModel):
    ticker: str
    analysts: dict[str, CommitteeMember]
    synthesis: CommitteeSynthesis
    cached_date: str

ANALYST_PROMPTS = {
    "teknisk": """Du är Teknisk Analytiker i en investeringskommitté.
Analysera ENBART teknisk data: trend, momentum, RSI, MACD, MA50/200, volym, volatilitet.
Ge ett tydligt omdöme (KÖPLÄGE STARKT/BRA/AVVAKTA/EJ AKTUELLT) med motivering (max 120 ord).
Slutsatsen ska vara handlingsbar. Inga generella disclaimers.""",

    "fundamental": """Du är Fundamental Analytiker i en investeringskommitté.
Analysera ENBART fundamental data: värdering (P/E, P/B), lönsamhet (ROE, marginaler),
tillväxt (intäkter, vinst), finansiell styrka (Piotroski, skuldsättning, likviditet).
Ge ett tydligt omdöme (KÖPLÄGE STARKT/BRA/AVVAKTA/EJ AKTUELLT) med motivering (max 120 ord).
Var konkret om vad som är attraktivt eller oroande.""",

    "sentiment": """Du är Sentimentanalytiker i en investeringskommitté.
Analysera ENBART mjuka faktorer: sektortrender, marknadsregim, relativ styrka mot index,
nyhetssentiment, säsongsmönster.
Ge ett tydligt omdöme (KÖPLÄGE STARKT/BRA/AVVAKTA/EJ AKTUELLT) med motivering (max 120 ord).
Var specifik om vad som driver sentimentet just nu.""",

    "ordforande": """Du är Ordförande i Analyskommittén och ska göra ett slutgiltigt syntesomdöme.
Du får tre analytikers omdömen. Väg dem mot varandra.
Returnera JSON:
{
  "verdict": "STARK"|"BRA"|"AVVAKTA"|"EJ_AKTUELLT",
  "confidence": 0-100,
  "summary": "max 150 ord på svenska",
  "disagreement": true|false,
  "disagreement_note": "om oenighet: förklara kort vad analytikerna är oeniga om"|null
}
Inga generella disclaimers. Var konkret.""",
}


@router.post("/committee/{ticker}", response_model=CommitteeOutput)
async def get_committee_analysis(
    ticker: str,
    body: CommitteeRequest,
    sb=Depends(get_supabase),
):
    """
    Analyskommittén: 3 analysts + chair synthesis.
    Cached per ticker per day (stored in Supabase).
    """
    import asyncio

    cache_key = f"committee:{ticker}:{date.today().isoformat()}"
    cached = get_cached(cache_key, sb)
    if cached:
        return cached

    context = _build_stock_context(ticker, body.stock_data)

    # Run 3 analysts in parallel
    results = await asyncio.gather(
        _call_ai(ANALYST_PROMPTS["teknisk"], context),
        _call_ai(ANALYST_PROMPTS["fundamental"], context),
        _call_ai(ANALYST_PROMPTS["sentiment"], context),
    )
    tech_analysis, fund_analysis, sent_analysis = results

    # Chair synthesis
    chair_input = f"""
Aktie: {ticker}

TEKNISK ANALYTIKER:
{tech_analysis}

FUNDAMENTAL ANALYTIKER:
{fund_analysis}

SENTIMENTANALYTIKER:
{sent_analysis}
"""
    chair_raw = await _call_ai(ANALYST_PROMPTS["ordforande"], chair_input)
    try:
        clean = chair_raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        synthesis = json.loads(clean)
    except json.JSONDecodeError:
        synthesis = {"verdict": "AVVAKTA", "confidence": 50, "summary": chair_raw, "disagreement": False}

    response = {
        "ticker": ticker,
        "analysts": {
            "teknisk": {"name": "Teknisk analytiker", "analysis": tech_analysis},
            "fundamental": {"name": "Fundamental analytiker", "analysis": fund_analysis},
            "sentiment": {"name": "Sentimentanalytiker", "analysis": sent_analysis},
        },
        "synthesis": synthesis,
        "cached_date": date.today().isoformat(),
    }

    set_cache(cache_key, response, sb)
    return response


# ─── Portfolio coach ─────────────────────────────────────────────────────────

PORTFOLIO_COACH_SYSTEM = """Du är en erfaren portföljrådgivare med kvantitativ bakgrund.
Du hjälper en privatinvesterare att förstå och förbättra sin portfölj.
Svara på svenska. Max 300 ord per svar om inget annat anges.
Använd datan du får — fabricera inga siffror. Var konkret och handlingsbar.
Om du saknar data för att svara, säg det tydligt."""


@router.post("/portfolio-coach", response_model=PortfolioCoachResponse)
async def portfolio_coach(
    body: PortfolioCoachRequest,
    user: User = Depends(get_current_user),
):
    context = f"""
PORTFÖLJDATA:
{json.dumps(body.portfolio_context, ensure_ascii=False, indent=2)}
"""
    messages = body.history + [{"role": "user", "content": body.question}]
    response = await _call_ai_chat(PORTFOLIO_COACH_SYSTEM, context, messages)
    return {"response": response}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_stock_context(ticker: str, data: dict) -> str:
    lines = [f"AKTIE: {ticker} — {data.get('name', '')}"]
    field_labels = {
        "score_total": "Totalbetyg", "entry_signal": "Köpläge", "trend_signal": "Trend",
        "price": "Kurs (SEK)", "change_pct": "Förändring idag",
        "pe_trailing": "P/E (TTM)", "roe": "ROE", "piotroski_f": "Piotroski F",
        "market_cap": "Börsvärde", "beta": "Beta", "vol_20d": "Volatilitet 20d",
        "dividend_yield": "Direktavkastning", "debt_to_equity": "Skuldsättning (D/E)",
        "revenue_growth": "Intäktstillväxt", "earnings_growth": "Vinsttillväxt",
        "gross_margin": "Bruttomarginal", "operating_margin": "Rörelsemarginal",
        "predicted_return": "AI-prognos 30d", "confidence_label": "Tillförlitlighet",
        "sector": "Sektor", "segment": "Segment",
    }
    for key, label in field_labels.items():
        val = data.get(key)
        if val is not None:
            if isinstance(val, float) and key.endswith(("_pct", "growth", "margin", "yield", "roe", "roa")):
                lines.append(f"{label}: {val*100:.1f}%")
            else:
                lines.append(f"{label}: {val}")
    return "\n".join(lines)


async def _call_ai(system_prompt: str, user_message: str) -> str:
    """Call AI provider — currently DeepSeek."""
    from apps.api.core.deepseek_client import call_deepseek

    return await call_deepseek(system_prompt, user_message, max_tokens=500, temperature=0.3)


async def _call_ai_chat(system_prompt: str, context: str, messages: list[dict]) -> str:
    """Call AI provider with chat history — currently DeepSeek."""
    from apps.api.core.deepseek_client import call_deepseek_chat

    return await call_deepseek_chat(system_prompt, context, messages, max_tokens=600)
