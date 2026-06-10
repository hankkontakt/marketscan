# Spec 08 — #2: Earnings Analyst (AI-rapportmemo)

> **Repo:** marketscan (worker + migration + API + frontend). **Insats:** M.
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` först.
> **Bygger på #7 (RAG, spec 04).** Använd L1 (rerank) + L2 (grounding) från spec 12.

## Mål
När en ny rapport ingestats av RAG-pipelinen, generera ett strukturerat analysmemo:
nyckeltal vs föregående, ledningston, 3 nyckelcitat, implicit guidning, sektorjämförelse.
**Inga svenska earnings-call-transkript finns** → arbeta mot delårs-/årsrapporter som redan
ligger som chunkar i `document_chunks`.

## Återanvänd (exakta signaturer)
- LLM: `apps/api/core/llm_client.py` →
  `async llm_complete(prompt, *, task, json_schema=None, prefer="cheap", cache=True) -> dict`
  (returnerar parsad JSON-dict när `json_schema` ges, annars `{"text":...}`, eller
  `{"error":...,"text":""}`). `async llm_embed(texts) -> list[list[float]]` (768-dim).
  I worker utan event-loop: `asyncio.run(llm_complete(...))`.
- RAG: `backend_worker/rag/extract_signals.py` →
  `_find_relevant_chunks(ticker, query_embedding: list[float], top_k: int, conn) -> list[dict]`
  (pgvector cosine `ORDER BY embedding <=> %s::vector`; varje chunk-dict har `content`,
  `section`, `chunk_index`, `embedding`).
- Tabeller (migration 030): `company_documents(id, ticker, doc_type, title, published_date,
  source_url, language, raw_text, fetched_at)`; `document_chunks(id, document_id, ticker,
  section, chunk_index, content, embedding vector(768))`.
- Rerank: `apps/api/core/reranker.rerank(query, chunks, top_n=6)` (spec 12 L1; om modulen ej
  finns ännu → fallback `chunks[:6]`).

## Steg

### 1. Migration `supabase/migrations/033_earnings_memos.sql`
```sql
CREATE TABLE IF NOT EXISTS earnings_memos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  doc_id UUID REFERENCES company_documents(id) ON DELETE CASCADE,
  published_date DATE,
  memo JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, doc_id)
);
CREATE INDEX IF NOT EXISTS idx_earnings_memos_ticker ON earnings_memos (ticker, published_date DESC);
ALTER TABLE earnings_memos ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON earnings_memos TO anon, authenticated;
CREATE POLICY "earnings_memos_public_read" ON earnings_memos FOR SELECT USING (true);
COMMENT ON TABLE earnings_memos IS 'AI earnings memos. Migration 033. Diagnostic marker: migration_033_earnings_memos.';
```
Lägg `migration_033_earnings_memos` i `apps/api/core/diagnostics.py` USER_TABLES (samma mönster som befintliga markörer).

### 2. `backend_worker/rag/earnings_memo.py` (NY)
```python
from __future__ import annotations
import argparse, asyncio, json, logging, os, re, sys
from typing import Optional
import psycopg2
from apps.api.core.llm_client import llm_complete, llm_embed
from backend_worker.rag.extract_signals import _find_relevant_chunks
try:
    from apps.api.core.reranker import rerank
except Exception:
    def rerank(query, chunks, top_n=6, text_key="content"):  # fallback
        return chunks[:top_n]

logger = logging.getLogger(__name__)

MEMO_SCHEMA = {
    "type": "object",
    "properties": {
        "nyckeltal_kommentar": {"type": "string"},
        "ledningston": {"type": "string", "enum": ["positiv", "neutral", "defensiv"]},
        "tre_citat": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "implicit_guidning": {"type": "string"},
        "sektor_jamforelse": {"type": "string"},
        "sammanfattning": {"type": "string"},
        "citerade_kallor": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ledningston", "tre_citat", "sammanfattning"],
}

_QUERY = "utsikter resultat marginal guidning risk kapitalallokering"
_NUM_RE = re.compile(r"\d")
```
Funktion `generate_memo_for_ticker(ticker: str, conn) -> Optional[dict]`:
1. `SELECT id, published_date FROM company_documents WHERE ticker=%s ORDER BY published_date DESC LIMIT 1`. Ingen rad → `return None`.
2. Idempotens: `SELECT memo FROM earnings_memos WHERE ticker=%s AND doc_id=%s` → om finns, returnera den.
3. `q_emb = asyncio.run(llm_embed([_QUERY]))[0]`; `chunks = _find_relevant_chunks(ticker, q_emb, top_k=12, conn)`.
4. `chunks = rerank(_QUERY, chunks, top_n=6)`.
5. Bygg prompt:
   ```
   Du skriver ett kort analysmemo för {ticker}s senaste rapport.
   Använd ENBART informationen i KÄLLORNA nedan. Varje siffra du nämner MÅSTE följas av
   [KÄLLA i] där i är chunk-numret. Hitta INTE på tal. Svara som JSON enligt schemat.
   KÄLLOR:
   [KÄLLA {chunk_index}] {content}
   ...
   ```
6. `result = asyncio.run(llm_complete(prompt, task="earnings_memo", json_schema=MEMO_SCHEMA, prefer="quality"))`. Om `result.get("error")` → logga, `return None`.
7. **Grounding (L2):** slå ihop memo-textfälten; om en mening innehåller en siffra (`_NUM_RE`) men saknar `[KÄLLA` → `result["_grounding_warning"] = True` (skriv ändå). (Valfritt: använd `apps/api/core/grounding.require_citations` om den finns.)
8. Upsert:
   ```sql
   INSERT INTO earnings_memos (ticker, doc_id, published_date, memo)
   VALUES (%s,%s,%s,%s)
   ON CONFLICT (ticker, doc_id) DO UPDATE SET memo=EXCLUDED.memo, created_at=NOW()
   ```
   (`json.dumps(result)` för memo). `conn.commit()`. Returnera `result`.

`main()`: argparse `--ticker` (en) ELLER alla tickers med ny rapport
(`SELECT DISTINCT cd.ticker FROM company_documents cd LEFT JOIN earnings_memos em
ON em.ticker=cd.ticker AND em.doc_id=cd.id WHERE em.id IS NULL`). DSN = `os.environ["DATABASE_URL"]`.
Loopa, skriv JSON-summary till stdout, `sys.exit(1)` vid DB-fel.

### 3. API `apps/api/routers/stocks.py`
`GET /api/stocks/{ticker}/earnings-memo` → senaste raden ur `earnings_memos` för ticker
(`ORDER BY published_date DESC LIMIT 1`), returnera `memo`-JSON + `published_date`. 404 om saknas.
Pydantic-schema `EarningsMemoOut` i `apps/api/schemas/` (eller inline).

### 4. Frontend
- Hook `apps/web/hooks/useEarningsMemo.ts`:
  ```ts
  export function useEarningsMemo(ticker: string) {
    return useQuery({ queryKey: ["earnings-memo", ticker],
      queryFn: () => api(`/api/stocks/${ticker}/earnings-memo`),
      staleTime: 60*60_000, retry: 1, enabled: !!ticker });
  }
  ```
- Kort "Rapportanalys" i aktievyns AI-flik (bredvid `AnalysCommittee` / qualitative).
  Visa: ledningston-badge (positiv=grön, neutral=grå, defensiv=gul), `sammanfattning`,
  3 citat (kursiv), `implicit_guidning`, `nyckeltal_kommentar`, datum. Om `_grounding_warning`
  → liten not "AI-genererad — verifiera siffror mot rapporten".

### 5. Schemaläggning
I `.github/workflows/doc_intelligence.yml`: lägg steg efter `extract_signals`:
`python -m backend_worker.rag.earnings_memo`. Secrets `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`,
`DATABASE_URL` finns redan.

## Acceptanstest
- `python -m backend_worker.rag.earnings_memo --ticker <X>` → rad i `earnings_memos`; memo har
  ≤3 citat; varje siffra har `[KÄLLA]`; andra körningen = no-op (idempotent).
- `GET /api/stocks/<X>/earnings-memo` returnerar memot; frontend-kortet renderar; `tsc` grönt.
- Manuell spot-check: citaten finns i rapporten; inga uppdiktade tal.

## Definition of Done
- [ ] Migration 033 + diagnostics-markör.
- [ ] `earnings_memo.py` med rerank + grounding + idempotens.
- [ ] API-endpoint + hook + Rapportanalys-kort.
- [ ] Workflow-steg.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
