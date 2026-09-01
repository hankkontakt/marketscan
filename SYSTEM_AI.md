# MarketScan 2.0 — SYSTEM_AI.md (Aktiv Ground Truth)

> **Aktiv sammanfattning för AI-agenter.**
> **HANDOFF-arkiv:** se docs/archive/ (*current state = git*).
> **Primär dokumentation:** Använd alltid SYSTEM_INDEX.md och relevanta kapitel i docs/codex/.

---

## 1. Kritiska regler — ALDRIG bryta

1. **ackend_worker/ får ALDRIG importeras av pps/api/.** Vercel 500MB-gräns. pandas, xgboost, yfinance är förbjudna i API.
2. **React 18.3 — uppgradera INTE till 19.** Radix UI kräver 18.
3. **def (inte sync def)** för synkrona Supabase DB-handlers i FastAPI för att inte blockera event-loopen.
4. **Supabase service key** (get_supabase_admin) används BARA bakom 
equire_admin i API samt i ackend_worker/. Exponeras ALDRIG i frontend.
5. **Inga emojis i UI** — alltid Lucide-linjeikoner.
6. **DATABASE_URL måste vara Session Pooler** (port 6543), INTE Direct (port 5432).
7. **InfoTooltip (i-bubbla)** används överallt bredvid finansiella värden.
8. **Stateless FastAPI** — inga globala variabler med föränderligt tillstånd.

---

## 2. Snabbreferens för kommandon

| Uppgift | Kommando |
|---|---|
| Starta API lokalt | python -m uvicorn apps.api.main:app --reload --port 8000 |
| Starta frontend lokalt | cd apps/web && npm run dev |
| Validera Codex | python scripts/verify_codex.py |
| Smoke test | python scripts/smoke_test.py |
| Bygg frontend (type-check) | cd apps/web && npx tsc --noEmit |
| Köra enhetstester | PYTHONPATH=. pytest apps/api/tests backend_worker/tests -v |

---

## 3. Arkitekturöversikt

- **Frontend (pps/web):** Next.js 15.5, React 18.3, Tailwind v4, Radix UI, TanStack Query v5.
- **Backend (pps/api):** FastAPI, PyJWT (HS256 lokal), Supabase-klienter (dependencies.py).
- **Worker (ackend_worker):** yfinance, pandas, XGBoost, beräkning av MasterRank, RAG-extraktion.
- **Databas:** Supabase Postgres med RLS-policies per tabell (supabase/migrations/).

---

## 4. Pekare till Living AI Codex

| Ämne | Codex-kapitel |
|---|---|
| Systemöversikt & Blueprint | docs/codex/00_SYSTEM_BLUEPRINT.md |
| MasterRank & QMJ Scoring | docs/codex/01_QUANT_MASTERRANK.md |
| Datapipeline & FI Register | docs/codex/02_DATA_PIPELINE.md |
| AI Syntes & DeepSeek | docs/codex/03_AI_RAG_SYNTHESIS.md |
| API Arkitektur & Routes | docs/codex/04_API_ARCHITECTURE.md |
| Databasschema & RLS | docs/codex/05_DATABASE_SCHEMA.md |
| Frontend State & Komponenter | docs/codex/06_FRONTEND_STATE_UX.md |
| Portfölj & Risk (HRP) | docs/codex/07_PORTFOLIO_RISK.md |

För fullständig historik och äldre planer, se docs/archive/system-ai-2026-09-01.md.
