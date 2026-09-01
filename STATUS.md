# MarketScan 2.0 — Projektstatus

> **Senast uppdaterad:** 2026-09-01 (Aktiv produktion)  
> **Stack:** Next.js 15.5 (React 18.3, Tailwind v4) + FastAPI 0.115 (Python 3.12) + Supabase Postgres (Stockholm, Port 6543) + GitHub Actions (30 workflows)  
> **Frontend:** https://marketscan.vercel.app  
> **API:** https://marketscan-api.vercel.app  
> **Ground Truth:** se `SYSTEM_INDEX.md` och `docs/codex/`

## Statusöversikt

Hela systemets kärna är i aktiv produktion med hög testtäckning (412 godkända enhetstester) och fullständig typintegritet.

### ✅ Klart & i produktion

- **Frontend (Next.js 15.5):** Översikt, Screener (MasterRank, filter, segment-percentiler), Aktiekort (Analyskommitté, radar, nyckeltal, AI-förklaring), Portfölj (innehav, Avanza CSV-import, risk, ombalansering), Insider-Radar (FI klusterköp), Bevakningar & Smarta larm, Kalender, Jämför, Marknad, Guide, Kontrollpanel (Admin), Landing, Login/Register.
- **Backend API (153 routes):** 29 feature-routers i `apps/api/routers/` (screener, stocks, portfolio, risk, ai, smart-alerts, insider, market-intel, markets, calendar, strategy-lab, rebalancer, forensic-audit, admin m.fl.).
- **Kvant & Scoring (MasterRank):** 8 fuserade delblock (kvalitet 25%, värde 15%, momentum 15%, analytiker 15%, insider 10%, katalysator 10%, utdelning 5%, tillväxt 5%), Anti-Bubbla-grind, datatäthetsregler och segment-normalisering.
- **AI & RAG:** Analyskommitté (Adversarial Bull/Bear/Chair), portföljcoach, aktieförklaring och filtertolk drivna av DeepSeek-V3 med strikt JSON-validering, grounding och cache-skydd ("cacha aldrig fel").
- **Databas & Säkerhet:** 79 Supabase-migrationer, Row Level Security (RLS) på alla användardata, Session Pooler (port 6543), lokal JWT-validering (PyJWT), `require_admin` på admin- och diagnostik-endpoints.
- **Data Pipeline:** GitHub Actions batch-jobb för priser (yfinance/Finnhub), FI Insynsregister, FI Blankningsregister och Cision nyhetsströmmar.

### 🧭 Navigering & Dokumentation

- Huvudindex: [`SYSTEM_INDEX.md`](SYSTEM_INDEX.md)
- Living AI Codex: [`docs/codex/`](docs/codex/)
- Felsökningsguide: [`DEBUGGING.md`](DEBUGGING.md)
- Systemvaliderare: `python scripts/verify_codex.py`
- Testkörning: `python -m pytest apps/api/tests backend_worker/tests -v`
- Frontend type-check: `cd apps/web && npm run type-check`
