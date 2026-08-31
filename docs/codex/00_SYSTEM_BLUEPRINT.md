# 🏛️ Kapitel 0: System Blueprint & Helikopterperspektiv

> **Domän:** Övergripande systemarkitektur, infrastruktur, dataflöde och miljöregler.  
> **Status:** Aktiv produktion (Mark sanning).

---

## 1. Executive Summary & TL;DR

MarketScan är en modern analys- och screeningplattform för aktier (med primärt fokus på Norden och globala storbolag) som kombinerar kvantitativ faktoranalys (MasterRank), maskininlärning, finansiell dokumentintelligens (RAG) och portföljriskhantering.

```
┌─────────────────────────┐          ┌─────────────────────────┐
│        Frontend         │          │       Backend API       │
│      Next.js 15.5       │ ──HTTP─► │       FastAPI 0.115     │
│   (Vercel: marketscan)  │          │ (Vercel: marketscan-api)│
└─────────────────────────┘          └────────────┬────────────┘
                                                  │
                                                  ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│     Backend Worker      │          │    Database & Storage   │
│     GitHub Actions      │ ──SQL──► │    Supabase Postgres    │
│  (Daglig pipeline/cron) │          │  (Stockholm eu-north-1) │
└─────────────────────────┘          └─────────────────────────┘
```

---

## 2. Infrastruktur & Driftsmiljö

| Komponent | Host / Miljö | Url / Hostnamn | Konfiguration & Begränsningar |
|---|---|---|---|
| **Frontend** | Vercel Project | `https://marketscan.vercel.app` | Next.js 15.5 App Router, React 18.3, Tailwind v4. Anropar API direkt. |
| **API** | Vercel Serverless | `https://marketscan-api.vercel.app` | Python 3.12, FastAPI. Max 500MB serverless bundle (inga tunga ML-libbar). |
| **Databas** | Supabase Postgres | `eu-north-1` (Stockholm) | **Session Pooler (port 6543)** används i produktion. RLS på alla användartabeller. |
| **Worker / Batch** | GitHub Actions | 13 schemalagda workflows | Kör kvant-pipelines, scrapers, ML-träning och larm. Använder `service_role`-nyckel. |

---

## 3. End-to-End Dataflöde

1. **Ingestion:** GitHub Actions kör `backend_worker/pipeline/entrypoint.py` dagligen. Hämtar priser från yfinance/Finnhub, insynsdata från Finansinspektionen (`backend_worker/fi_insider_bulk.py`) och pressmeddelanden från Cision.
2. **Kvant & Poängsättning:** `backend_worker/master_rank.py` fuserar 8 delblock, applicerar Anti-Bubbla-grinden och beräknar MasterRank.
3. **Persistens:** `backend_worker/db_loader.py` skriver normaliserad data till Supabase-tabellen `scan_results`.
4. **API Servning:** FastAPI i `apps/api/routers/` läser från Supabase via `apps/api/dependencies.py` och levererar JSON till frontend med lokal JWT-auth.
5. **Frontend Presentation:** TanStack React Query v5 i `apps/web/` cを受ar data och renderar vyer med progressiv disclosure och `InfoTooltip`.

---

## 4. Absoluta Invarianter (Systemlagar)

1. **Separation API vs Worker:** `backend_worker/` får ALDRIG importeras av `apps/api/`. `pandas`, `xgboost`, `scipy` och `yfinance` är strikt förbjudna i API-bundeln.
2. **React 18.3 Låsning:** Uppgradera inte till React 19 eftersom Radix UI-primitiv kräver React 18.
3. **Synkrona DB-handlers i FastAPI:** Använd vanliga `def`-funktioner för FastAPI-endpoints som gör synkrona Supabase-anrop, så att trådpoolen sköter I/O och inte blockerar FastAPIs async loop.
4. **Supabase Client Scopes:**
   - `get_supabase_anon`: För publika oinloggade anrop.
   - `get_supabase_user`: För inloggade användare med RLS-isolering.
   - `get_supabase_admin`: Används ENDAST internt i endpoints skyddade av `require_admin`.
5. **Designsystem:** Inga emojis i användargränssnittet (använd Lucide React-ikoner). Alla finansiella mått ska ha en `InfoTooltip`.

---

## 5. Källkodskarta

| Område | Mapp / Fil | Ansvar |
|---|---|---|
| API Huvudingång | `apps/api/main.py` | FastAPI app, CORS, global exception handler, route-registrering |
| API Beroenden | `apps/api/dependencies.py` | Auth, token-validering, Supabase-klienter |
| API Routers | `apps/api/routers/` | Alla REST-endpoints |
| Worker Pipeline | `backend_worker/pipeline/` | Pipeline orkestrering och batch-körningar |
| Worker Kvant | `backend_worker/master_rank.py` | MasterRank beräkningsmotor |
| Databas Migrationer | `supabase/migrations/` | SQL-scheman och RLS-policies |
| Frontend Webbapp | `apps/web/` | Next.js applikation |

---

## 6. Underhålls- och Verifieringsrutin

När ändringar görs i arkitekturen ska detta dokument och berörda domänkapitel uppdateras in-place.
Kör alltid:
```bash
python scripts/verify_codex.py
```
