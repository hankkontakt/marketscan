# 🤖 Kapitel 3: AI, LLM & RAG Synthesis Engine

> **Domän:** LLM-arkitektur (DeepSeek/Claude), svensk finansiell dokumentintelligens, RAG, Re-ranking och Grounding.  
> **Status:** Aktiv produktion.

---

## 1. Executive Summary & TL;DR

AI-motorn i MarketScan syntetiserar kvantitativ data och ostrukturerad text (årsredovisningar, kvartalsrapporter, pressmeddelanden) för att ge förklarande sammanfattningar, analyskommitté-bedömningar och djupgående bolagsrapporter. Motorn drivs primärt av DeepSeek-V3 med strikta grounding- och cachingmekanismer.

---

## 2. Arkitektur & RAG-flöde

```
  ┌─────────────────────────┐          ┌─────────────────────────┐
  │ PDF / Delårsrapporter   │          │ Cision Nyhetsflöde      │
  └────────────┬────────────┘          └────────────┬────────────┘
               │                                    │
               ▼                                    ▼
  ┌──────────────────────────────────────────────────────────────┐
  │              backend_worker/rag/document_fetcher.py          │
  │  • PDF-parsing (pdfplumber) & HTML extraktion                │
  │  • Semantisk chunking (500–1000 tokens med överlapp)         │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                 apps/api/core/reranker.py                    │
  │  • Kors-enkoder (CrossEncoder) re-ranking av relevanta stycken│
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │               apps/api/core/deepseek_client.py               │
  │  • Prompt-injicering med kvantitativa siffror + textchunks    │
  │  • Strikt JSON Schema-validering                             │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                apps/api/core/grounding.py                    │
  │  • Verifierar att LLM-svaret stöds av källtexten (Citations)  │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                 apps/api/core/ai_cache.py                    │
  │  • Cachning i Supabase (`ai_cache`) för kostnadskontroll     │
  └──────────────────────────────────────────────────────────────┘
```

---

## 3. Kärnkomponenter & Modeller

| Komponent | Modul / Fil | Syfte |
|---|---|---|
| **DeepSeek Klient** | `apps/api/core/deepseek_client.py` | Primär LLM-klient med OpenAI-kompatibelt gränssnitt; `_resolve_endpoint` routar nyckeltyp ('sk-or-…' → OpenRouter, 'sk-…' → api.deepseek.com); `return_meta=True` returnerar `(text, finish_reason)` så avklippta svar ('length') kan detekteras |
| **LLM Router & Fallback** | `apps/api/core/llm_client.py` | Fallback-orkestrering (`prefer="cheap"`/`"quality"`) och token-budget; nycklar läses från `settings` vid anropstid och återanvänder `_resolve_endpoint` — samma routing-källa som committee/explain-vägen; synkrona httpx-anrop körs i `asyncio.to_thread` |
| **Re-ranker** | `apps/api/core/reranker.py` | Väljer ut de mest relevanta textstyckena för given fråga |
| **Grounding Validator** | `apps/api/core/grounding.py` | Kräver källhänvisningar och förhindrar hallucinationer |
| **AI Caching** | `apps/api/core/ai_cache.py` | Hash-baserad caching i tabellen `ai_cache` |
| **Rapportanalys** | `backend_worker/ai_report_analyzer.py` | Automatisk extraktion av VD-ord, risker och framtidsutsikter |

---

## 4. AI-Funktioner i API & Frontend

1. **Analyskommittén (`POST /api/ai/committee/{ticker}`):** 2-stegs Adversarial Protokoll: Stage 1 kör parallellt Bull Investor (tillväxt, vallgrav), Short-Seller Bear (skulder, marginalpress, forensik), Teknisk, Fundamental och Sentiment. Stage 2 kör Ordföranden som syntetiserar debatten, väger bevisen och fördelar sannolikheter (`bull_pct`, `base_pct`, `bear_pct`).
2. **Aktiejämförelse (`POST /api/ai/compare`):** Djupgående semantisk jämförelse mellan två bolags affärsmodeller och vallgravar.
3. **Smart Filter-tolk (`POST /api/ai/parse-filter`):** Översätter naturligt språk (t.ex. "lönsamma verkstadsbolag med låg skuld och bra utdelning") till strukturerade SQL/API-filter.
4. **Mikrolektioner & Begreppsförklarare (`POST /api/ai/micro-lesson`):** Genererar pedagogiska förklaringar anpassade för nybörjare.
5. **Portföljcoach & Daglig Briefing (`POST /api/ai/daily-coach` & `POST /api/ai/portfolio-coach`):** Servern beräknar ALLA fakta ur innehaven (grounding); LLM:en (`llm_complete`, `prefer="quality"`, `max_tokens=700`, omförsök vid truncation → 1500) formulerar en briefing. Cachas per användare/dag/portföljläge — ENDAST lyckade och fullständiga svar.
6. **AI-förklaring (`POST /api/ai/explain/{ticker}` + `/followup`):** Pedagogisk förklaring för nybörjare, `max_tokens=1200` (omförsök vid avklippning → 2500), `finish_reason`-styrd truncation-flagga till frontend, cache-nyckel `explain:v2:…` (gamla avklippta poster ogiltigförklaras).
7. **AI Journal (`GET /api/ai/journal/{ticker}`):** Hämtar strukturerad analyshistorik och anteckningar för en specifik aktie.

---

## 5. Källkodskarta & Kodankare

| Område | Fil | Funktioner |
|---|---|---|
| AI API Router | `apps/api/routers/ai.py` | `/api/ai/committee/{ticker}`, `/api/ai/compare`, `/api/ai/parse-filter`, `/api/ai/portfolio-coach`, `/api/ai/daily-coach`, `/api/ai/journal/{ticker}`, `/api/ai/explain/{ticker}`, `/api/ai/explain/{ticker}/followup`, `/api/ai/micro-lesson` |
| LLM-routing-test | `apps/api/tests/test_llm_client_routing.py` | Routing-paritet, settings-nycklar, finish-normalisering, cache-policy ("fel cachas aldrig") |
| RAG Fetcher | `backend_worker/rag/document_fetcher.py` | `fetch_company_filings()`, `extract_pdf_text()` |
| Grounding Check | `apps/api/core/grounding.py` | `require_citations()`, `validate_grounding()` |
| AI Cache Helper | `apps/api/core/ai_cache.py` | `get_cached()`, `set_cache()` |

---

## 6. Säkerhets- och Kostnadsregler

1. **Autentiseringskrav:** Alla publika LLM-endpoints kräver inloggad användare (`get_current_user`) för att förhindra DoS och oönskad API-kostnad.
2. **Strikta JSON-kontrakt:** Inga fria textströmmar utan validering via Pydantic. Om modellen returnerar ogiltig JSON körs en automatisk retry med felmeddelandet injicerat.
3. **Cachningspolicy:** Analyser för samma kvartalsrapport cachas i 7 dagar om inte användaren begär tvingad uppdatering.
4. **CACHA ALDRIG FEL (regression 2026-08-31 & ROND 13):** Felaktiga, avklippta eller ogrundade LLM-svar får ALDRIG fastna i `ai_cache` — `daily-coach` returnerar tom briefing vid fel och kör omförsök vid truncation; `committee` och `compare` cachar enbart verifierade synteser.
5. **Token-policy:** explain/followup kör 1200 tokens med omförsök vid 2500; daily-coach 700 med omförsök vid 1500; committee-analytiker 2500. Prompt-kontrakt: explain tillåter markdown (renderas av `MarkdownLite`), daily-coach förbjuder markdown; disclaimers läggs alltid av gränssnittet, aldrig av modellen (undviker dubbletter).
