"""
AI endpoints: NL screener parser, stock analysis, Analyskommittén, portfolio coach.
All responses are cached per ticker/day to minimize token spend.
"""
import asyncio
import json
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from apps.api.core.ai_cache import get_cached, set_cache
from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_supabase, get_supabase_admin
from apps.api.core.rate_limiter import limiter

logger = logging.getLogger(__name__)

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
async def parse_nl_filter(
    request: Request,
    body: NLFilterRequest,
    user: User = Depends(get_current_user),
):
    """Parse natural language query into screener filter params.
    Rate limited: 10 req/min (DeepSeek costs money).
    """
    # P1-3: Apply rate limit when slowapi is available
    if limiter is not None:
        try:
            await limiter._check_request_limit(request, "10/minute")
        except Exception:
            pass  # Fail open — slowapi checks via middleware, this is belt-and-suspenders

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
    sb_admin=Depends(get_supabase_admin),
    user: User = Depends(get_current_user),
):
    """
    Analyskommittén: 3 analysts + chair synthesis.
    Cached per ticker per day (stored in Supabase).
    L4: Kör synthesis 2 ggr för self-consistency.
    """
    import asyncio

    cache_key = f"committee:{ticker}:{date.today().isoformat()}"
    # Read from anon client (public read), write via admin (P2-5: ensures cache writes succeed)
    cached = get_cached(cache_key, sb_admin)
    if cached:
        return cached

    context = _build_stock_context(ticker, body.stock_data)

    # P2-4: return_exceptions=True so a single analyst timeout doesn't crash the whole committee
    results = await asyncio.gather(
        _call_ai(ANALYST_PROMPTS["teknisk"], context),
        _call_ai(ANALYST_PROMPTS["fundamental"], context),
        _call_ai(ANALYST_PROMPTS["sentiment"], context),
        return_exceptions=True,
    )

    # Degrade gracefully: use fallback text for any analyst that failed
    _FALLBACK = "Analysen kunde inte hämtas."
    tech_analysis = results[0] if not isinstance(results[0], Exception) else _FALLBACK
    fund_analysis = results[1] if not isinstance(results[1], Exception) else _FALLBACK
    sent_analysis = results[2] if not isinstance(results[2], Exception) else _FALLBACK

    # Chair synthesis — only if at least one analyst succeeded
    if all(r == _FALLBACK for r in [tech_analysis, fund_analysis, sent_analysis]):
        raise HTTPException(status_code=503, detail="Analyskommittén är tillfälligt otillgänglig")

    chair_input = f"""
Aktie: {ticker}

TEKNISK ANALYTIKER:
{tech_analysis}

FUNDAMENTAL ANALYTIKER:
{fund_analysis}

SENTIMENTANALYTIKER:
{sent_analysis}
"""
    # L4 — Self-consistency: kör synthesis 2 ggr för att detektera oenighet
    syn_results = await asyncio.gather(
        _call_ai(ANALYST_PROMPTS["ordforande"], chair_input, max_tokens=500),
        _call_ai(ANALYST_PROMPTS["ordforande"], chair_input, max_tokens=500),
        return_exceptions=True,
    )

    syntheses = []
    for sr in syn_results:
        if isinstance(sr, Exception):
            continue
        try:
            clean = sr.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            syntheses.append(json.loads(clean))
        except (json.JSONDecodeError, AttributeError):
            pass

    if not syntheses:
        # Fallback om båda misslyckades
        if isinstance(syn_results[0], str):
            try:
                clean = syn_results[0].strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                syntheses = [json.loads(clean)]
            except (json.JSONDecodeError, AttributeError):
                pass
        if not syntheses:
            syntheses = [{"verdict": "AVVAKTA", "confidence": 50, "summary": syn_results[0] if isinstance(syn_results[0], str) else "Analys ej tillgänglig", "disagreement": False}]

    # Kontrollera oenighet mellan synteserna (L4)
    disagreement = False
    disagreement_note = None
    if len(syntheses) >= 2:
        verdicts = [s.get("verdict", "") for s in syntheses]
        if verdicts[0] != verdicts[1]:
            disagreement = True
            disagreement_note = f"Oenighet mellan syntesomgångar: '{verdicts[0]}' vs '{verdicts[1]}'"

    # Använd första syntesen som huvudsaklig
    synthesis = syntheses[0]
    synthesis["disagreement"] = disagreement or synthesis.get("disagreement", False)
    if disagreement and not synthesis.get("disagreement_note"):
        synthesis["disagreement_note"] = disagreement_note

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

    # P2-5: Use admin client for cache writes so grant/RLS issues don't silently skip caching
    set_cache(cache_key, response, sb_admin)

    # Save to AI journal for transparency
    try:
        sb_admin.table("ai_journal").insert({
            "ticker": ticker,
            "verdict": synthesis.get("verdict", "AVVAKTA"),
            "confidence": synthesis.get("confidence"),
            "summary": synthesis.get("summary"),
            "score_at_time": body.stock_data.get("score_total"),
            "price_at_time": body.stock_data.get("price"),
        }).execute()
    except Exception as e:
        logger.warning("Failed to save AI journal entry for %s: %s", ticker, e)

    return response


# ─── AI Compare ──────────────────────────────────────────────────────────────


AI_COMPARE_SYSTEM = """Du är en analytiker som jämför 2-5 aktier.
Analysera skillnader i: värdering, kvalitet, momentum, tillväxt, risk, sentiment.
För varje aktie, nämn dess styrka och svaghet.

Returnera JSON:
{
  "recommendation": "ticker för den mest attraktiva aktien just nu",
  "reasoning": "kort motivering varför (max 200 ord på svenska)",
  "strengths": { "TICKER": "styrka" },
  "weaknesses": { "TICKER": "svaghet" },
  "summary": "en mening som sammanfattar jämförelsen"
}
Inga generella disclaimers. Var konkret och datadriven."""


class AICompareRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=5)
    stock_datas: list[dict]


class AICompareResponse(BaseModel):
    ticker: str
    recommendation: str
    reasoning: str
    strengths: dict[str, str]
    weaknesses: dict[str, str]
    summary: str
    cached_date: str


@router.post("/compare")
async def ai_compare(body: AICompareRequest, sb=Depends(get_supabase), sb_admin=Depends(get_supabase_admin), user: User = Depends(get_current_user)):
    """AI that compares 2-5 stocks and recommends the most attractive one."""
    import asyncio

    key = f"compare:{'-'.join(sorted(body.tickers))}:{date.today().isoformat()}"
    cached = get_cached(key, sb_admin)
    if cached:
        return cached

    context_lines = []
    for td in body.stock_datas:
        t = td.get("ticker", "")
        context_lines.append(_build_stock_context(t, td))

    context = "\n\n---\n\n".join(context_lines) or "Ingen data tillgänglig."

    try:
        raw = await _call_ai(AI_COMPARE_SYSTEM, context, max_tokens=800)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(clean)
    except Exception as e:
        logger.warning("AI compare failed: %s", e)
        result = {
            "recommendation": body.tickers[0],
            "reasoning": "Kunde inte genomföra jämförelsen just nu. Försök igen senare.",
            "strengths": {t: "" for t in body.tickers},
            "weaknesses": {t: "" for t in body.tickers},
            "summary": "AI-jämförelse ej tillgänglig.",
        }

    response = {
        "ticker": "-".join(sorted(body.tickers)),
        **result,
        "cached_date": date.today().isoformat(),
    }

    set_cache(key, response, sb_admin)
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


# ─── Daglig proaktiv coach (Spec 10) ──────────────────────────────────────────

DAILY_COACH_SYSTEM = """Du är en kvantitativ portföljrådgivare. Svara på svenska, max 250 ord.
ANVÄND ENDAST siffrorna du får i JSON — hitta inte på egna tal.
Peka på övervikter och risker (t.ex. om en enskild position eller sektor är för stor, eller
om portföljvolatiliteten ligger över målvolatiliteten) och ge tre konkreta, handlingsbara
förslag. Föreslå ALDRIG att lägga order automatiskt. Avsluta INTE med en disclaimer.
Skriv i ren, lättläst svenska. Använd INTE markdown, asterisker (*), fetstil-markeringar
eller rubriker — bara vanliga meningar och vid behov korta punkter med bindestreck."""

_COACH_DISCLAIMER = "Detta är inte finansiell rådgivning. Inga affärer läggs automatiskt."


class DailyCoachRequest(BaseModel):
    holdings: list[dict] = Field(default_factory=list)  # [{ticker, shares, price, sector?}]
    risk_profile: dict | None = None                     # {profile, max_position_pct, target_volatility}
    volatility_ann: float | None = None
    regime_label: str | None = None


class DailyCoachResponse(BaseModel):
    briefing: str
    facts: dict
    date: str
    disclaimer: str
    empty: bool = False


@router.post("/daily-coach", response_model=DailyCoachResponse)
async def daily_coach(
    body: DailyCoachRequest,
    user: User = Depends(get_current_user),
    sb_admin=Depends(get_supabase_admin),
):
    """Proaktiv daglig coach-briefing. Servern beräknar ALLA fakta ur innehaven
    (grounding); LLM:en får bara de beräknade talen. Cachas per användare/dag/portföljläge."""
    import hashlib

    today = date.today().isoformat()
    holdings = [h for h in body.holdings
                if h.get("shares") and h.get("price") and h.get("ticker")]
    if not holdings:
        return {"briefing": "", "facts": {}, "date": today,
                "disclaimer": _COACH_DISCLAIMER, "empty": True}

    # ── Beräkna fakta (i Python, ej LLM) ─────────────────────────────────────
    values = {h["ticker"]: float(h["shares"]) * float(h["price"]) for h in holdings}
    total = sum(values.values()) or 1.0
    weights = {t: v / total for t, v in values.items()}
    largest_t = max(weights, key=weights.get)
    largest_pct = weights[largest_t]
    top3 = sum(sorted(weights.values(), reverse=True)[:3])

    sector_w: dict[str, float] = {}
    for h in holdings:
        s = h.get("sector")
        if s:
            sector_w[s] = sector_w.get(s, 0.0) + weights[h["ticker"]]
    largest_sector = max(sector_w, key=sector_w.get) if sector_w else None

    rp = body.risk_profile or {}
    max_pos = rp.get("max_position_pct")
    target_vol = rp.get("target_volatility")
    vol = body.volatility_ann

    facts = {
        "antal_innehav": len(holdings),
        "totalt_varde_kr": round(total),
        "storsta_position": {"ticker": largest_t, "vikt_pct": round(largest_pct * 100, 1)},
        "topp3_koncentration_pct": round(top3 * 100, 1),
        "storsta_sektor": ({"sektor": largest_sector, "vikt_pct": round(sector_w[largest_sector] * 100, 1)}
                           if largest_sector else None),
        "max_positionsgrans_pct": round(max_pos * 100, 1) if max_pos else None,
        "over_positionsgrans": bool(max_pos is not None and largest_pct > max_pos),
        "portfoljvolatilitet_pct": round(vol * 100, 1) if vol is not None else None,
        "malvolatilitet_pct": round(target_vol * 100, 1) if target_vol is not None else None,
        "over_malvolatilitet": bool(target_vol is not None and vol is not None and vol > target_vol),
        "riskprofil": rp.get("profile"),
        "marknadsregim": body.regime_label,
    }

    # ── Cache per användare/dag/portföljläge ─────────────────────────────────
    state_hash = hashlib.md5(
        json.dumps({k: round(v) for k, v in sorted(values.items())}).encode()
    ).hexdigest()[:8]
    cache_key = f"daily_coach:{user.id}:{today}:{state_hash}"
    cached = get_cached(cache_key, sb_admin)
    if cached:
        return cached

    try:
        from apps.api.core.llm_client import llm_complete
        prompt = (DAILY_COACH_SYSTEM + "\n\nPORTFÖLJDATA (JSON):\n"
                  + json.dumps(facts, ensure_ascii=False))
        # prefer="cheap" → Gemini free tier först, DeepSeek bara som fallback.
        # cache=False här eftersom vi redan cachar svaret via set_cache nedan.
        result = await llm_complete(prompt, task="daily_coach", prefer="cheap", cache=False)
        briefing = (result or {}).get("text", "").strip()
        if not briefing:
            briefing = "Kunde inte generera en coach-briefing just nu. Försök igen senare."
    except Exception as e:
        logger.warning("daily-coach LLM failed: %s", e)
        briefing = "Kunde inte generera en coach-briefing just nu. Försök igen senare."

    resp = {"briefing": briefing, "facts": facts, "date": today,
            "disclaimer": _COACH_DISCLAIMER, "empty": False}
    set_cache(cache_key, resp, sb_admin)
    return resp


# ─── AI Journal ─────────────────────────────────────────────────────────────


class AIJournalEntryOut(BaseModel):
    id: str
    ticker: str
    verdict: str
    confidence: int | None = None
    summary: str | None = None
    score_at_time: float | None = None
    price_at_time: float | None = None
    created_at: str


class AIJournalOut(BaseModel):
    ticker: str
    entries: list[AIJournalEntryOut]


@router.get("/journal/{ticker}", response_model=AIJournalOut)
def get_ai_journal(ticker: str, sb=Depends(get_supabase)):
    """Get AI analysis history for a ticker (transparency log)."""
    t = ticker.upper().strip()
    res = (
        sb.table("ai_journal")
        .select("*")
        .eq("ticker", t)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )

    entries = []
    for item in res.data or []:
        entries.append(AIJournalEntryOut(
            id=item["id"],
            ticker=item["ticker"],
            verdict=item["verdict"],
            confidence=item.get("confidence"),
            summary=item.get("summary"),
            score_at_time=float(item["score_at_time"]) if item.get("score_at_time") else None,
            price_at_time=float(item["price_at_time"]) if item.get("price_at_time") else None,
            created_at=item.get("created_at", ""),
        ))

    return AIJournalOut(ticker=ticker, entries=entries)


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


async def _call_ai(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    """Call AI provider — currently DeepSeek."""
    from apps.api.core.deepseek_client import call_deepseek

    return await call_deepseek(system_prompt, user_message, max_tokens=max_tokens, temperature=0.3)


async def _call_ai_chat(system_prompt: str, context: str, messages: list[dict]) -> str:
    """Call AI provider with chat history — currently DeepSeek."""
    from apps.api.core.deepseek_client import call_deepseek_chat

    return await call_deepseek_chat(system_prompt, context, messages, max_tokens=600)
