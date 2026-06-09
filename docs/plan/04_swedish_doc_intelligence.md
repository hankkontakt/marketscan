# Spec 04 — #7 + #12: Svensk dokumentintelligens (RAG + Q-rapport-NLP)

> **Repo:** `marketscan`. Greenfield (inget finns idag).
> **Mål:** Bygg ett system som läser svenska års-/delårsrapporter, extraherar
> framåtblickande signaler (utsikter, ton, riskförändringar) och ger ett
> `qualitative_score` (0–100) per bolag som matar AI-kommittén. Billigast möjligt.
> **#7 (RAG över årsredovisningar) och #12 (NLP på delårsrapporter) är HÄR SAMMANSLAGNA**
> till ett dokument-pipeline — samma ingestion, chunking, embeddings, extraktion.
> **Läs först:** master §2, §3, §4 (kostnad!), §6. Läs `apps/api/core/deepseek_client.py`,
> `apps/api/core/config.py`, `apps/api/routers/ai.py`, migration `003_ai_cache.sql`,
> `core/ai_analysis.py` (stock-scanner-fix, för committee-kontext).

> ⚠️ **Detta är ett massivt projekt. Bygg i ordning A→F. Stanna och fråga användaren
> om något steg kräver betald tjänst utöver Gemini free tier + DeepSeek v4-flash.**

---

## 0. Kostnadsstrategi (avgör hela arkitekturen)

| Komponent | Val | Kostnad |
|---|---|---|
| Embeddings | **Gemini `gemini-embedding` free tier** (10M tok/min gratis) | 0 kr |
| Vektorlagring | **pgvector i befintliga Supabase** | 0 kr |
| Extraktion (struktur) | **Gemini Flash-Lite free** (1000 req/dygn) → DeepSeek v4-flash fallback | ~0–80 kr/mån |
| Syntes (kvalitativ text) | DeepSeek v4-flash, hård cache i `ai_cache` | inkluderat |
| Dokumentkälla | MFN.se publika feeds / bolagens IR-sidor | 0 kr |

**Princip:** Allt cachas (`ai_cache` + embeddings lagras permanent). Ett dokument
embeddas/extraheras EN gång. Re-körning är gratis (cache-hit). Budgettak per dygn.

---

## A. LLM-abstraktionslager (delas med #19 — bygg FÖRST)

**Fil:** `apps/api/core/llm_client.py` (ny)

Ett enhetligt interface som väljer billigaste tillgängliga modell med fallback:
```python
"""
llm_client.py — Enhetligt LLM-interface med kostnadsoptimerad routing.

Ordning: Gemini free tier → DeepSeek v4-flash (betald) → fel.
Allt cachas via ai_cache (cache_key = sha256 av prompt+model+task).
Budgettak: max N DeepSeek-anrop/dygn (env LLM_DAILY_PAID_CAP, default 500).
"""
from __future__ import annotations

async def llm_complete(
    prompt: str,
    *, task: str,                 # "extract" | "synthesize" | "embed"
    json_schema: dict | None = None,  # om satt: tvinga strukturerad JSON-output
    prefer: str = "cheap",        # "cheap" (Gemini först) | "quality" (DeepSeek)
    cache: bool = True,
) -> dict: ...

async def llm_embed(texts: list[str]) -> list[list[float]]:
    """Gemini gemini-embedding (free). Returnerar vektorer (dim 768 el. modellens dim)."""
```
- Gemini: använd `GEMINI_API_KEY` (env, finns). REST: `generativelanguage.googleapis.com`.
- DeepSeek: återanvänd `deepseek_client.py`.
- Vid 429 från Gemini (kvot slut) → fallback DeepSeek (för `complete`) eller vänta/kö
  (för `embed`, eftersom embed-kvoten är enorm — 10M tok/min — bör sällan slå i).
- Räkna paid-anrop i en enkel dygnsräknare (tabell `llm_budget` eller Redis-lös: en rad
  i en `worker_state`-tabell). Vid tak nått → returnera cache-only / hoppa över.

**Acceptanstest A:** `llm_embed(["test svenska text"])` ger en vektor; `llm_complete` med
`json_schema` ger giltig JSON; cache-hit andra gången (ingen nät-anrop).

---

## B. pgvector + dokumentschema

**Migration:** `marketscan/supabase/migrations/0NN_doc_intelligence.sql`
```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Råa dokument (en rad per rapport)
CREATE TABLE IF NOT EXISTS company_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  doc_type TEXT NOT NULL,        -- 'annual_report' | 'interim_report' | 'press_release'
  title TEXT,
  published_date DATE,
  source_url TEXT,
  language TEXT DEFAULT 'sv',
  raw_text TEXT,                 -- extraherad text (PDF→text)
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, doc_type, published_date, source_url)
);

-- Chunkar + embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES company_documents(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  section TEXT,                  -- 'outlook' | 'ceo_letter' | 'risk' | 'financials' | 'other'
  chunk_index INTEGER,
  content TEXT NOT NULL,
  embedding vector(768),         -- matcha Gemini-embeddings dim
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON document_chunks (ticker);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
  ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Extraherade kvalitativa signaler (en rad per bolag, senaste rapport)
CREATE TABLE IF NOT EXISTS qualitative_signals (
  ticker TEXT PRIMARY KEY,
  qualitative_score FLOAT,       -- 0-100
  outlook_direction TEXT,        -- 'positive'|'neutral'|'negative'
  hedging_density FLOAT,         -- andel osäkerhetsspråk (0-1)
  capital_intent TEXT,           -- 'investing'|'returning'|'cutting'
  tone_change FLOAT,             -- vs föregående rapport (-1..+1)
  summary TEXT,                  -- kort svensk sammanfattning (DeepSeek)
  based_on_doc_id UUID,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE company_documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE qualitative_signals   ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON qualitative_signals TO anon, authenticated;
CREATE POLICY "qual_public_read" ON qualitative_signals FOR SELECT USING (true);
-- company_documents/document_chunks: ingen publik läsning (rå upphovsrättsskyddad text)
```
> Verifiera Gemini-embeddings faktiska dimension och sätt `vector(N)` därefter. Om
> ivfflat kräver data innan index → skapa index efter första inläsningen (skriv i Deploy).

---

## C. Dokumentingestion

**Fil:** `marketscan/backend_worker/rag/document_fetcher.py` (ny)

### C1. Källor (gratis)
- **MFN.se** (Modular Finance News): publika sidor/feeds per bolag med pressmeddelanden +
  rapporter för alla nordiska noterade bolag. Undersök publik feed-URL (t.ex. per-bolag
  RSS/JSON). Om ingen ren publik feed finns → fallback C2.
- **Bolagens IR-sidor / Nasdaq Nordic IR-portal**: standardiserade PDF-länkar.
> Verifiera MFN:s publika åtkomst vid implementation. Om bara betald Dataflow-API finns →
> `# TODO(fråga)` och använd IR-sidor. Stanna inte hela projektet på detta.

### C2. PDF→text
`pypdf` eller `pdfplumber` (open source). Extrahera text + identifiera sektioner via
rubrik-heuristik (svenska: "Utsikter", "Framtidsutsikter", "VD har ordet", "Risker",
"Väsentliga risker"). Lagra `raw_text` + sektionstaggar.

### C3. Chunking + embeddings
- Dela per sektion, ~500–800 tokens/chunk, 15% overlap.
- `llm_embed()` (Gemini free) → spara i `document_chunks.embedding`.
- Idempotent: hoppa dokument som redan finns (`company_documents` UNIQUE).

**Robusthet:** logga antal dokument/chunkar per körning; 0 nya under en
rapportperiod = misstänkt → varna.

---

## D. Strukturerad extraktion (RAG-frågor)

**Fil:** `marketscan/backend_worker/rag/extract_signals.py` (ny)

För varje bolag med ny rapport, kör 5 strukturerade queries mot dess chunkar (hämta topp-k
relevanta chunkar via cosine-likhet i pgvector, mata till `llm_complete(task="extract",
json_schema=...)`):

1. **Intäktsutsikter:** riktning (positive/neutral/negative) + citat.
2. **Marginal-/lönsamhetsguidning:** expanderande/stabil/krympande.
3. **Ledningens ton/konfidens:** hedging-densitet (räkna "kan", "kanske", "under
   förutsättning", "beror på") + övergripande ton.
4. **Riskförändring:** nya/borttagna riskfaktorer vs föregående rapport.
5. **Kapitalallokering:** investerar / återför (utdelning/återköp) / drar ner.

Aggregera → `qualitative_score` (0–100) med transparent viktning (t.ex. utsikter 35%,
marginal 20%, ton 20%, risk 15%, kapital 10%). Spara i `qualitative_signals`.
DeepSeek skriver en kort svensk `summary` (cachas).

**Kostnadskontroll:** kör bara för bolag med NY rapport sedan förra körningen. Cache per
(ticker, doc_id). Gemini Flash-Lite först; DeepSeek bara om Gemini-kvot slut eller
JSON-validering misslyckas 2 ggr.

---

## E. Integration i AI-kommittén

`core/ai_analysis.py` (stock-scanner-fix) / `apps/api/routers/ai.py` kör idag en
3-analytiker-kommitté. Mata in `qualitative_signals` som KÄLLA till den fundamentala/
sentiment-analytikern istället för att LLM:en gissar — ersätt "shallow" prompt med faktiska
extraherade signaler + citat. Detta höjer kvaliteten OCH sänker kostnaden (mindre
fritext-generering).

- API: `GET /api/stocks/{ticker}/qualitative` → `qualitative_signals`-raden + summary.
- Frontend: nytt kort i aktievyns AI-flik "Rapportanalys" som visar utsikter/ton/risk
  med citat ur rapporten + tooltip.

---

## F. Schemaläggning

**Fil:** `.github/workflows/doc_intelligence.yml` (ny). Daglig (eller 2×/dygn under
rapportsäsong):
1. `python -m backend_worker.rag.document_fetcher --days 3`
2. `python -m backend_worker.rag.extract_signals`
Registrera i admin `_WORKFLOW_INPUTS` + panel. Secret: `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`.

---

## Filer som rörs
| Fil | Åtgärd |
|---|---|
| `apps/api/core/llm_client.py` | NY — LLM-routing (delas med #19) |
| `supabase/migrations/0NN_doc_intelligence.sql` | NY — pgvector + 3 tabeller |
| `backend_worker/rag/document_fetcher.py` | NY — ingestion + embeddings |
| `backend_worker/rag/extract_signals.py` | NY — strukturerad extraktion |
| `apps/api/routers/ai.py` | Mata committee med qualitative_signals |
| `apps/api/routers/stocks.py` | `GET /api/stocks/{t}/qualitative` |
| `apps/web/components/stock/…` | "Rapportanalys"-kort |
| `.github/workflows/doc_intelligence.yml` | NY |
| `apps/api/routers/admin.py` | Registrera workflow |
| `requirements.txt` (marketscan) | `pypdf`/`pdfplumber`, `google-generativeai` |

## Definition of Done
- [ ] LLM-lager med Gemini→DeepSeek-fallback + cache + dygnsbudget; test A grönt.
- [ ] pgvector aktivt; dokument + chunkar + embeddings lagras idempotent.
- [ ] 5 strukturerade signaler extraheras → `qualitative_score` per bolag.
- [ ] AI-kommittén använder faktiska rapport-signaler (inte gissningar).
- [ ] Frontend visar Rapportanalys med citat.
- [ ] Kostnad mäts/loggas; Gemini-free täcker normal volym; DeepSeek bara fallback.
- [ ] Upphovsrätt: rå rapporttext är EJ publikt läsbar (RLS); endast korta citat/summary visas.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
