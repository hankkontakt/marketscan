# 🧭 MarketScan System Index (Living AI Codex)

> **Maskinläsbart Nav & AI-karta för MarketScan.**  
> Denna fil och underliggande kapitel i `docs/codex/` utgör systemets **Ground Truth**. Använd detta index för att navigera och läs ENDAST det relevanta kapitlet i docs/codex/. Fulla omläsningar av stora dokument/arkiv är förbjudna.

---

## ⚡ Fast-Start Personas (Vem är du just nu?)

Välj din roll nedan och gå direkt till angivet kapitel:

| Din Roll / Uppgift | Läs Detta Först | Primär Arbetsyta |
|---|---|---|
| 📈 **Quant / Scoring Agent** (Justera ranking, vikter, faktorer) | [`01_QUANT_MASTERRANK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/01_QUANT_MASTERRANK.md) | `backend_worker/master_rank.py`, `qmj_scores.py` |
| 🔄 **Pipeline & Data Agent** (Scrapers, FI-register, datafel) | [`02_DATA_PIPELINE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/02_DATA_PIPELINE.md) | `backend_worker/pipeline/`, `db_loader.py` |
| 🤖 **AI & RAG Agent** (DeepSeek, rapportanalys, embeddings) | [`03_AI_RAG_SYNTHESIS.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/03_AI_RAG_SYNTHESIS.md) | `apps/api/core/deepseek_client.py`, `backend_worker/rag/` |
| 🔌 **API & Backend Agent** (FastAPI-endpoints, auth, routes) | [`04_API_ARCHITECTURE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/04_API_ARCHITECTURE.md) | `apps/api/routers/`, `apps/api/dependencies.py` |
| 🗄️ **Database & SQL Agent** (Postgres scheman, RLS, migrationer) | [`05_DATABASE_SCHEMA.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/05_DATABASE_SCHEMA.md) | `supabase/migrations/` |
| 🎨 **Frontend & UX Agent** (Next.js vyer, React Query, UI) | [`06_FRONTEND_STATE_UX.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/06_FRONTEND_STATE_UX.md) | `apps/web/app/(app)/`, `apps/web/components/` |
| ⚖️ **Risk & Portfolio Agent** (HRP, VaR, backtests, simulering) | [`07_PORTFOLIO_RISK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/07_PORTFOLIO_RISK.md) | `apps/api/core/risk_calc.py`, `apps/api/core/portfolio_construction.py` |

---

## 🗺️ Master Routing Table (Var hittar du vad?)

| Delsystem / Ämne | Kapitel i Codex | Viktiga Källfiler |
|---|---|---|
| **Systemöversikt & Arkitektur** | [`00_SYSTEM_BLUEPRINT.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/00_SYSTEM_BLUEPRINT.md) | `apps/api/main.py`, `apps/web/package.json` |
| **MasterRank & Anti-Bubbla-Grind** | [`01_QUANT_MASTERRANK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/01_QUANT_MASTERRANK.md) | `backend_worker/master_rank.py` |
| **QMJ-kvalitet & Piotroski F-Score** | [`01_QUANT_MASTERRANK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/01_QUANT_MASTERRANK.md) | `backend_worker/qmj_scores.py` |
| **Alpha Discovery Moduler** | [`01_QUANT_MASTERRANK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/01_QUANT_MASTERRANK.md) | `backend_worker/alpha_discovery/` |
| **FI Insyns- & Blankningsregister** | [`02_DATA_PIPELINE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/02_DATA_PIPELINE.md) | `backend_worker/fi_insider_bulk.py`, `fi_short_positions.py` |
| **Cision Nyhetsström & RSS** | [`02_DATA_PIPELINE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/02_DATA_PIPELINE.md) | `backend_worker/news_stream_cision.py` |
| **DeepSeek LLM & Prompter** | [`03_AI_RAG_SYNTHESIS.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/03_AI_RAG_SYNTHESIS.md) | `apps/api/core/deepseek_client.py` |
| **RAG & Dokumentextraktion** | [`03_AI_RAG_SYNTHESIS.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/03_AI_RAG_SYNTHESIS.md) | `backend_worker/rag/document_fetcher.py` |
| **FastAPI Routing & Middleware** | [`04_API_ARCHITECTURE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/04_API_ARCHITECTURE.md) | `apps/api/routers/`, `apps/api/main.py` |
| **Auth, JWT & Supabase Dependencies** | [`04_API_ARCHITECTURE.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/04_API_ARCHITECTURE.md) | `apps/api/dependencies.py`, `apps/api/core/security.py` |
| **Postgres Tabeller, Scheman & RLS** | [`05_DATABASE_SCHEMA.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/05_DATABASE_SCHEMA.md) | `supabase/migrations/` |
| **Next.js Vyer & Komponenter** | [`06_FRONTEND_STATE_UX.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/06_FRONTEND_STATE_UX.md) | `apps/web/app/(app)/`, `apps/web/components/` |
| **Portföljoptimering & HRP** | [`07_PORTFOLIO_RISK.md`](file:///c:/Users/hthur/OneDrive/Desktop/marketscan/docs/codex/07_PORTFOLIO_RISK.md) | `apps/api/core/portfolio_construction.py` |

---

## 🛑 Top 5 Invarianter (ALDRIG bryta)

1. **`backend_worker/` får ALDRIG importeras av `apps/api/`.** Vercel har en 500MB gräns. `pandas`, `xgboost`, `scipy` och `yfinance` är förbjudna i API-bundeln.
2. **React 18.3 — Uppgradera INTE till React 19.** Radix UI kräver React 18.
3. **`def` (synkront) för Supabase DB-anrop i FastAPI.** Använd `def` för att inte blockera FastAPIs async event-loop.
4. **Service role key (`get_supabase_admin`) ENDAST bakom `require_admin`.**
5. **InfoTooltip (`i`-bubbla) överallt bredvid finansiella mått.** Inga emojis i UI — endast Lucide-ikoner.

---

## 📜 Living Documentation Directive (Regler för AI)

1. **Ändra In-Place:** När du ändrar kod, uppdatera motsvarande tabell/beskrivning i relevant kapitel under `docs/codex/`. Ersätt gammal information.
2. **Inga Mikro-Changelogs i Boken:** Git äger historiken. Boken beskriver **endast Nuläget (Ground Truth)**.
3. **Håll Budgeten:** Max 500 rader per kapitel.
4. **Validera:** Kör `python scripts/verify_codex.py` innan du lämnar uppgiften.
