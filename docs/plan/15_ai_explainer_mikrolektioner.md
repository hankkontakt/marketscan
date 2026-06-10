# Spec 15 — M3 AI-förklarare + Mikrolektioner

> **Skrivet: 2026-06-10. Beräknad insats: M (5–7h).**
> **Skrivet för:** DeepSeek v4-flash. **Läs HELA spec 14 + spec 13** innan du rör kod.
> **Bygger på:** `apps/api/routers/ai.py`, `llm_client.py`, `ai_cache.py`,
> `_build_stock_context()`, `VerdictCard`, `FeedbackWidget`.

---

## 0. Vad och varför

En nybörjare ser omdömeskortet (spec 14) och tänker "okej... men varför?".
AI-förklararen svarar på det — i enkelt språk, grundat i bolagets faktiska
siffror. **AI:n förklarar, råder aldrig.** Den är en pedagog, inte en rådgivare.

**Två lägen:**
1. **"Förklara enkelt"** — en knapptryckning → cachat AI-svar. Visas som ett
   expanderbart kort under omdömeskortet.
2. **"Fråga mer"** — en uppföljningsinput där användaren kan ställa en specifik
   fråga om bolaget. Sparar kontexten (tidigare förklaring + fråga).

**Allt cachas** per `(ticker, nivå, dag)`. Gemini free tier först → DeepSeek fallback.
Kostnad: ~0 kr vid normal användning.

---

## 1. Delsteg A — API: explain-endpoint

**Fil:** `apps/api/routers/ai.py` — lägg till:

```python
# ── AI Explainer (M3) ─────────────────────────────────────────────

AI_EXPLAIN_SYSTEM = """Du är en pedagogisk finansiell förklarare för en svensk
aktieanalys-app. Din målgrupp är nybörjare som aldrig handlat aktier förut.

REGLER (följ strikt):
1. Använd ENBART informationen du får i datan nedan. HITTA INTE PÅ tal.
2. Översätt ALLA finanstermer till vad de betyder i praktiken.
   - Säg ALDRIG "P/E 15" — säg "aktien kostar 15 gånger årsvinsten, vilket är..."
   - Säg ALDRIG "ROE 18%" — säg "för varje 100-lapp bolaget har ger det 18 kr i vinst"
3. Förklara som om du pratar med en 12-åring. Korta meningar. Vardagsspråk.
4. Var ärlig om osäkerheter. Säg "det här vet vi inte" om data saknas.
5. Ge ALDRIG köpråd. Säg ALDRIG "du bör köpa/sälja".
6. Avsluta med en ödmjuk påminnelse om att ingen kan förutse börsen.

FORMAT: max 250 ord. Vanlig text, inte punktlista. Inga rubriker."""

EXPLAIN_FOLLOWUP_SYSTEM = """Du är en pedagogisk finansiell förklarare.
Du har tidigare förklarat en aktie för en nybörjare (se kontext nedan).
Nu har användaren en följdfråga om aktien.

REGLER (samma som förra förklaringen):
1. Använd ENDAST datan du redan har. Hitta inte på.
2. Översätt finanstermer till vardagsspråk.
3. Korta meningar, enkelt språk.
4. Ge ALDRIG köpråd.
5. Om användaren frågar något du inte har data för, säg ärligt "det kan jag inte svara på".

FORMAT: max 200 ord. Konversationston."""

class ExplainRequest(BaseModel):
    stock_data: dict

class ExplainResponse(BaseModel):
    ticker: str
    explanation: str
    level: str
    cached_date: str

class FollowupRequest(BaseModel):
    stock_data: dict
    previous_explanation: str
    question: str

class FollowupResponse(BaseModel):
    ticker: str
    answer: str
    cached_date: str


@router.post("/explain/{ticker}", response_model=ExplainResponse)
@limiter.limit("30/minute")  # P-7: rate-limit, AI kostar
async def explain_stock(
    request: Request,
    ticker: str,
    body: ExplainRequest,
    user: User = Depends(get_current_user),
    sb_admin = Depends(get_supabase_admin),
):
    """AI-förklarare: förklara en aktie för en nybörjare."""
    level = "beginner"  # Alltid nybörjarnivå för denna endpoint
    cache_key = f"explain:{ticker}:{level}:{date.today().isoformat()}"

    cached = get_cached(cache_key, sb_admin)
    if cached:
        return cached

    context = _build_stock_context(ticker, body.stock_data)

    prompt = f"""Här är data om aktien {ticker}:

{context}

Förklara den här aktien för mig. Vad betyder siffrorna i praktiken? 
Är det här ett bolag som är billigt eller dyrt? Lönsamt eller inte? 
Växer det? Finns det några varningssignaler?"""

    result = await _call_ai(AI_EXPLAIN_SYSTEM, prompt, max_tokens=500)

    response = {
        "ticker": ticker,
        "explanation": result,
        "level": level,
        "cached_date": date.today().isoformat(),
    }

    set_cache(cache_key, response, sb_admin)
    return response


@router.post("/explain/{ticker}/followup", response_model=FollowupResponse)
@limiter.limit("20/minute")
async def explain_followup(
    request: Request,
    ticker: str,
    body: FollowupRequest,
    user: User = Depends(get_current_user),
    sb_admin = Depends(get_supabase_admin),
):
    """Följdfråga efter en förklaring."""
    context = _build_stock_context(ticker, body.stock_data)

    prompt = f"""TIDIGARE FÖRKLARING OM {ticker}:
{body.previous_explanation}

ANVÄNDARENS FÖLJDFRÅGA:
{body.question}

DATA OM AKTIEN (samma som tidigare):
{context}"""

    answer = await _call_ai(EXPLAIN_FOLLOWUP_SYSTEM, prompt, max_tokens=400)

    return {
        "ticker": ticker,
        "answer": answer,
        "cached_date": date.today().isoformat(),
    }
```

---

## 2. Delsteg B — API: micro-lesson endpoint

```python
# ── Mikrolektioner (M3) ───────────────────────────────────────────

MICRO_LESSON_SYSTEM = """Du är en pedagogisk finansiell utbildare.
Förklara ett ekonomiskt begrepp på max 3 meningar, på svenska.
Använd enkelt vardagsspråk. Som om du förklarar för en 12-åring.
Ge ETT konkret exempel. Inga siffror om det inte behövs."""

MICRO_LESSONS = {
    "pe_trailing": "Vad är P/E (pris/vinst)?",
    "roe": "Vad är ROE (avkastning på eget kapital)?",
    "beta": "Vad är Beta (svängighet)?",
    "dividend_yield": "Vad är direktavkastning/utdelning?",
    "debt_to_equity": "Vad är skuldsättning?",
    "market_cap": "Vad är börsvärde?",
    "gross_margin": "Vad är bruttomarginal?",
    "piotroski_f": "Vad är Piotroski F-Score?",
    "score_total": "Vad är Totalbetyget?",
}

class MicroLessonRequest(BaseModel):
    topic: str

class MicroLessonResponse(BaseModel):
    topic: str
    question: str
    explanation: str
    cached_date: str


@router.post("/micro-lesson", response_model=MicroLessonResponse)
@limiter.limit("60/minute")
async def micro_lesson(
    request: Request,
    body: MicroLessonRequest,
    user: User = Depends(get_current_user),
    sb_admin = Depends(get_supabase_admin),
):
    """Förklara ett finansiellt begrepp enkelt."""
    topic = body.topic
    question = MICRO_LESSONS.get(topic, f"Vad är {topic}?")
    cache_key = f"micro_lesson:{topic}:{date.today().isoformat()}"

    cached = get_cached(cache_key, sb_admin)
    if cached:
        return cached

    prompt = f"Förklara: {question}"
    explanation = await _call_ai(MICRO_LESSON_SYSTEM, prompt, max_tokens=200)

    response = {
        "topic": topic,
        "question": question,
        "explanation": explanation,
        "cached_date": date.today().isoformat(),
    }

    set_cache(cache_key, response, sb_admin)
    return response
```

---

## 3. Delsteg C — ExplainSection-komponent

**Fil:** `apps/web/components/stock/ExplainSection.tsx` (NY)

```tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Sparkles, Send } from "lucide-react";
import { api } from "@/lib/api";
import { trackEvent, EVENT } from "@/lib/tracking";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { cn } from "@/lib/utils";
import type { ScanRow } from "@/types/scan";

/**
 * ExplainSection — AI-förklarare för en aktie.
 * 
 * Två faser:
 * 1. "Förklara enkelt" — hämtar/visar första förklaringen
 * 2. "Fråga mer" — följdfrågor
 */
export function ExplainSection({ ticker, stock }: { ticker: string; stock: ScanRow }) {
  const [showFollowup, setShowFollowup] = useState(false);
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<Array<{ q: string; a: string }>>([]);

  // Hämta förklaring (cachad)
  const { data: explanation, isLoading } = useQuery({
    queryKey: ["explain", ticker],
    queryFn: () =>
      api<{ explanation: string }>(`/api/ai/explain/${ticker}`, {
        method: "POST",
        body: JSON.stringify({ stock_data: stock }),
      }),
    staleTime: 8 * 60 * 60_000, // 8h cache
  });

  // Följdfråga mutation
  const followupMutation = useMutation({
    mutationFn: (q: string) =>
      api<{ answer: string }>(`/api/ai/explain/${ticker}/followup`, {
        method: "POST",
        body: JSON.stringify({
          stock_data: stock,
          previous_explanation: explanation?.explanation || "",
          question: q,
        }),
      }),
    onSuccess: (data, q) => {
      setChatHistory((prev) => [...prev, { q, a: data.answer }]);
      setQuestion("");
      trackEvent(EVENT.EXPLAIN_FOLLOWUP, { ticker });
    },
  });

  function handleAsk() {
    if (!question.trim()) return;
    followupMutation.mutate(question.trim());
  }

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles size={18} className="text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Förstå {ticker}
        </h3>
      </div>

      {/* Förklaring */}
      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-[var(--color-bg-elevated)] rounded w-full" />
          <div className="h-3 bg-[var(--color-bg-elevated)] rounded w-3/4" />
          <div className="h-3 bg-[var(--color-bg-elevated)] rounded w-5/6" />
        </div>
      ) : explanation ? (
        <div className="space-y-3">
          <p className="text-sm leading-relaxed text-[var(--color-text-secondary)]">
            {explanation.explanation}
          </p>
          <p className="text-[10px] text-[var(--color-text-muted)]">
            AI-genererad — inte finansiell rådgivning.
          </p>
          <FeedbackWidget component="explain_text" context={`explain:${ticker}`} />
        </div>
      ) : null}

      {/* Chat history */}
      {chatHistory.map((chat, i) => (
        <div key={i} className="space-y-2 pt-3 border-t border-[var(--color-border-subtle)]">
          <p className="text-xs font-medium text-[var(--color-accent)]">
            Du frågade: {chat.q}
          </p>
          <p className="text-sm leading-relaxed text-[var(--color-text-secondary)]">
            {chat.a}
          </p>
        </div>
      ))}

      {/* Följdfråga */}
      {!showFollowup ? (
        <button
          onClick={() => {
            setShowFollowup(true);
            trackEvent(EVENT.EXPLAIN_CLICK, { ticker });
          }}
          className="text-xs text-[var(--color-accent)] hover:underline"
        >
          Fråga mer om {ticker}...
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder={`Vad mer vill du veta om ${ticker}?`}
            className="flex-1 text-sm px-3 py-2 rounded-xl border border-[var(--color-border)]
                       bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)]
                       focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]
                       placeholder:text-[var(--color-text-muted)]"
          />
          <button
            onClick={handleAsk}
            disabled={followupMutation.isPending || !question.trim()}
            className="p-2 rounded-xl bg-[var(--color-accent)] text-white
                       disabled:opacity-40 transition-opacity"
          >
            <Send size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 4. Delsteg D — MicroLesson-komponent

**Fil:** `apps/web/components/ui/MicroLesson.tsx` (NY)

```tsx
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { HelpCircle } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * MicroLesson — klickbart "(?)" som öppnar en AI-förklaring
 * av ett finansiellt begrepp. Komplement till InfoTooltip.
 * 
 * Usage: <span>P/E <MicroLesson topic="pe_trailing" /></span>
 */
export function MicroLesson({ topic, label }: { topic: string; label?: string }) {
  const [open, setOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["micro-lesson", topic],
    queryFn: () =>
      api<{ explanation: string }>("/api/ai/micro-lesson", {
        method: "POST",
        body: JSON.stringify({ topic }),
      }),
    staleTime: 24 * 60 * 60_000, // 24h — lärdomar ändras inte
    enabled: open,               // Hämta bara när öppnad
  });

  return (
    <span className="inline-flex items-center">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full
                   text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)]
                   transition-colors cursor-help"
        aria-label={label || `Vad är ${topic}?`}
      >
        <HelpCircle size={12} />
      </button>
      {open && (
        <span
          className={cn(
            "absolute z-50 mt-6 ml-1 w-56 p-3 rounded-xl shadow-lg text-xs leading-relaxed",
            "bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)]",
            "text-[var(--color-text-secondary)]",
          )}
        >
          {isLoading ? (
            <span className="text-[var(--color-text-muted)]">Hämtar förklaring...</span>
          ) : data ? (
            data.explanation
          ) : (
            <span className="text-[var(--color-text-muted)]">Kunde inte hämta förklaring.</span>
          )}
          <button
            onClick={() => setOpen(false)}
            className="block mt-1 text-[10px] text-[var(--color-accent)] hover:underline"
          >
            Stäng
          </button>
        </span>
      )}
    </span>
  );
}
```

---

## 5. Delsteg E — Integration

### I VerdictCard (spec 14):

Under omdömet, lägg direkt:
```tsx
<ExplainSection ticker={stock.ticker} stock={stock} />
```

### I sifferkorten (NumberCard i VerdictCard):

Lägg `MicroLesson` bredvid varje label:
```tsx
<span className="flex items-center gap-1">
  <span className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wide">
    P/E
  </span>
  <MicroLesson topic="pe_trailing" />
</span>
```

### I OverviewTab (för intermediate/experter):

Lägg `MicroLesson` bredvid nyckeltalen i den vanliga tabellen.

---

## 6. Filer som rörs

| Fil | Åtgärd |
|---|---|
| `apps/api/routers/ai.py` | Lägg: `/explain/{ticker}`, `/explain/{ticker}/followup`, `/micro-lesson` |
| `apps/web/components/stock/ExplainSection.tsx` | NY — förklaringskort + följdfråge-chat |
| `apps/web/components/ui/MicroLesson.tsx` | NY — "(?)" inline-lektion |
| `apps/web/components/stock/VerdictCard.tsx` | Lägg ExplainSection + MicroLesson bredvid nyckeltal |
| `apps/web/app/(app)/aktie/[ticker]/StockView.tsx` | Se spec 14 |

---

## 7. Acceptanstest

- [ ] `POST /api/ai/explain/ERIC-B` returnerar en svensk förklaring (cachad dag 2)
- [ ] `POST /api/ai/explain/ERIC-B/followup` svarar på en följdfråga
- [ ] `POST /api/ai/micro-lesson { topic: "roe" }` returnerar en 3-menings förklaring
- [ ] ExplainSection visar "Fråga mer..." och tar emot input
- [ ] Följdfrågor sparas i chatHistory (client-side, försvinner vid reload)
- [ ] MicroLesson öppnar popup med förklaring
- [ ] Alla svar innehåller "inte finansiell rådgivning" / disclaimer
- [ ] FeedbackWidget under varje AI-svar
- [ ] Rate-limit headers finns (30/min explain, 60/min micro-lesson)
- [ ] `cd apps/web && npx tsc --noEmit` — 0 fel
- [ ] `docs/SYSTEM_AI.md` uppdaterad
