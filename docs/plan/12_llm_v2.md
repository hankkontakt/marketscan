# Spec 12 — LLM v2 (RAG-kvalitet, grounding, judge)

> **Repo:** marketscan. **Insats:** S–M per punkt.
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` + spec 04 (RAG) först.
> **L1 + L2 ska användas direkt av spec 08 (earnings-memo) och spec 10 (coach).**
> Allt ryms inom Gemini-gratis + lokala open-source-modeller → budgetneutralt.

## Återanvänd (exakt)
- `apps/api/core/llm_client.py`: `async llm_complete(prompt, *, task, json_schema=None,
  prefer="cheap", cache=True) -> dict`; `async llm_embed(texts) -> list[list[float]]`.
- RAG: `backend_worker/rag/extract_signals.py::_find_relevant_chunks(ticker, q_emb, top_k, conn)`
  (pgvector cosine). Chunk-dict har `content`, `section`, `chunk_index`.
- AI-committee: `apps/api/routers/ai.py` (synthesis-fält `disagreement` finns redan).

## L1 — Cross-encoder reranking (störst LLM-ROI)
**Bygg `apps/api/core/reranker.py` (NY, delas av API + workers):**
```python
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
_MODEL = None
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # liten, tål svenska tillräckligt
                                                       # alt: "BAAI/bge-reranker-base"

def _load():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import CrossEncoder
        _MODEL = CrossEncoder(_MODEL_NAME)
    return _MODEL

def rerank(query: str, chunks: list[dict], top_n: int = 6, text_key: str = "content") -> list[dict]:
    """Sortera chunkar efter cross-encoder-relevans mot query, returnera topp-n.
       Fallback: om sentence-transformers/modell ej kan laddas → chunks[:top_n]."""
    if not chunks:
        return []
    try:
        model = _load()
        pairs = [(query, c.get(text_key, "")) for c in chunks]
        scores = model.predict(pairs)
        ranked = [c for _, c in sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)]
        return ranked[:top_n]
    except Exception as e:
        logger.warning("rerank fallback (no model): %s", e)
        return chunks[:top_n]
```
- Pinna `sentence-transformers` i `backend_worker/requirements.txt` (och API-requirements om
  API:t anropar rerank). Modellen laddas lazy + cachas i process.
- **Integration:** i `extract_signals._find_relevant_chunks`-anropare och i
  `earnings_memo.generate_memo_for_ticker`: hämta `top_k=12` via pgvector → `rerank(query,
  chunks, top_n=6)` före LLM. Evidens: +15–25 % relevans; hallucination 19 %→2,1 %.

## L2 — Grounding / fine-grained verification
**Bygg `apps/api/core/grounding.py` (NY):**
```python
import re
_NUM = re.compile(r"\d")
_CIT = re.compile(r"\[KÄLLA\s+\d+\]")

def require_citations(text: str, sources: list[str]) -> dict:
    """Varje mening med en siffra MÅSTE ha en [KÄLLA i]-tagg. Returnerar
       {ok: bool, ungrounded: list[str]} (meningar med tal utan källa)."""
    ungrounded = []
    for sent in re.split(r"(?<=[.!?])\s+", text or ""):
        if _NUM.search(sent) and not _CIT.search(sent):
            ungrounded.append(sent.strip())
    return {"ok": not ungrounded, "ungrounded": ungrounded}
```
- **Användning (spec 08 + 10):** efter LLM-svar, kör `require_citations` på memo/briefing-texten.
  Om `not ok` → antingen flagga (`_grounding_warning=True`) ELLER kör en verifikationspass:
  skicka tillbaka de ogrundade meningarna med "Ta bort eller källbelägg dessa tal."
- **Prompt-mönster (återanvänd överallt):** "Använd ENDAST källorna. Varje siffra MÅSTE ha
  [KÄLLA i]. Hitta inte på tal."

## L3 — Strukturerad mall-extraktion
- Definiera **strikta** `json_schema` (med `enum`, `maxItems`, `required`) för alla
  strukturerade LLM-anrop: earnings-memo (spec 08 `MEMO_SCHEMA`), `parse-filter`,
  committee-synthesis. `llm_complete` skickar redan `response_schema` (Gemini) /
  `response_format=json_object` (DeepSeek).
- Lägg en **enkel validering + en retry:** om svaret saknar ett `required`-fält → kör om EN
  gång med tillägget "Du missade fältet X — inkludera det." Annars acceptera/flagga.

## L4 — LLM-as-judge / self-consistency (valfri, sist)
- I `ai.py` committee-synthesis: kör synthesis 2–3 ggr (eller via 2 modeller). Om verdict
  skiljer sig → sätt `disagreement=True` (fältet finns) och välj majoritet. Låg prioritet;
  bygg efter L1–L3.

## Filer
| Fil | Åtgärd |
|---|---|
| `apps/api/core/reranker.py` | L1 (NY) |
| `apps/api/core/grounding.py` | L2 (NY) |
| `backend_worker/rag/extract_signals.py`, `backend_worker/rag/earnings_memo.py` | integrera L1 + L2 |
| `apps/api/routers/ai.py` | L3 (strikta scheman + retry), L4 (judge) |
| `backend_worker/requirements.txt` (+ API-requirements) | `sentence-transformers` |

## Acceptanstest
- `rerank("utsikter marginal", chunks)` ändrar ordningen vs ren cosine; utan modell →
  fallback returnerar `chunks[:top_n]` (ingen krasch).
- `require_citations("Omsättningen ökade 12%.", [])` → `ok=False` (fångar ogrundad siffra);
  `require_citations("Omsättningen ökade 12% [KÄLLA 3].", ["3"])` → `ok=True`.
- Memo (spec 08) med reranking → mer relevanta citat (manuell jämförelse).

## Definition of Done
- [ ] `reranker.py` med lazy-load + fallback; integrerad i RAG + memo.
- [ ] `grounding.py` + validering i spec 08 & 10.
- [ ] Strikta scheman + en-retry i strukturerade anrop.
- [ ] `sentence-transformers` pinnad.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
