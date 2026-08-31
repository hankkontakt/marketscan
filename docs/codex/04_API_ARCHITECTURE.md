# 🔌 Kapitel 4: API & Backend Architecture

> **Domän:** FastAPI REST-backend, serverless körning på Vercel, auth, Supabase-klienter och router-katalog.  
> **Status:** Aktiv produktion.

---

## 1. Executive Summary & TL;DR

FastAPI-backend (`apps/api/`) agerar som säker gateway mellan Next.js-klienten och Supabase Postgres. Den är designad för serverless-drift på Vercel med extremt låg latens via lokal JWT-validering (PyJWT) och trådpool-baserad databashantering.

---

## 2. Arkitektur & Middleware-stack

```
  Klientanrop (Next.js / Browser)
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                   apps/api/main.py                          │
  │  1. RequestIDMiddleware (spårar requestId i alla headers)    │
  │  2. CORSMiddleware (tillåter Vercel previews & prod origin) │
  │  3. Global Exception Handler (sätter CORS även vid 500-fel) │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 apps/api/dependencies.py                    │
  │  • get_supabase_anon   -> Publik åtkomst                    │
  │  • get_supabase_user   -> Inloggad användare med RLS        │
  │  • get_supabase_admin  -> Service role (kräver require_admin)│
  │  • get_current_user    -> Lokal PyJWT HS256 validering      │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                   apps/api/routers/                         │
  │  30 dedikerade feature-routers (screener, portfolio, ai...) │
  └─────────────────────────────────────────────────────────────┘
```

---

## 3. De Tre Supabase-Klienterna (Injektionsmönster)

Alla endpoints måste välja rätt klient via FastAPI `Depends`:

```python
# 1. Publik data (scan_results, marknadsöversikter)
def get_public_data(db: Client = Depends(get_supabase_anon)):
    return db.table("scan_results").select("*").execute()

# 2. Användarisolerad data med RLS (portfölj, watchlist, larm)
def get_user_portfolio(user_id: str = Depends(get_current_user), db: Client = Depends(get_supabase_user)):
    return db.table("portfolios").select("*").execute()

# 3. Privilegierade admin-operationer
def run_admin_action(admin: dict = Depends(require_admin), db: Client = Depends(get_supabase_admin)):
    return db.table("pipeline_runs").select("*").execute()
```

---

## 4. Fullständig Router-Katalog

Alla endpoints är registrerade i `apps/api/main.py`:

| Router-fil | Prefix / Område | Viktiga Endpoints | Skydd |
|---|---|---|---|
| `admin.py` | `/api/admin` | `/health`, `/diagnostics/deep`, `/workflow/trigger` | `require_admin` |
| `ai.py` | `/api/ai` | `/committee`, `/compare`, `/parse-filter` | `get_current_user` |
| `alerts.py` | `/api/alerts` | `/`, `/{id}` (legacy prislarm) | `get_current_user` |
| `smart_alerts.py` | `/api/smart-alerts` | `/rules`, `/events`, `/digest` | `get_current_user` |
| `calendar.py` | `/api/calendar` | `/events`, `/earnings` | `get_optional_user` |
| `feedback.py` | `/api/feedback` | `/submit` | `get_optional_user` |
| `insider.py` | `/api/insider` | `/trades`, `/clusters`, `/radar` | `get_optional_user` |
| `macro_regime.py` | `/api/macro-regime` | `/current`, `/history` | `get_supabase_anon` |
| `market_intel.py` | `/api/market-intel` | `/news`, `/sentiment`, `/movers` | `get_supabase_anon` |
| `markets.py` | `/api/markets` | `/indices`, `/commodities`, `/crypto` | `get_supabase_anon` |
| `ml_performance.py` | `/api/ml-performance` | `/metrics`, `/drift`, `/confusion` | `require_admin` |
| `notifications.py` | `/api/notifications`| `/list`, `/mark-read` | `get_current_user` |
| `paper_trading_router.py` | `/api/paper-trading`| `/accounts`, `/orders`, `/positions`| `get_current_user` |
| `portfolio.py` | `/api/portfolio` | `/`, `/import/avanza/preview`, `/construct` | `get_current_user` |
| `profile.py` | `/api/profile` | `/me`, `/settings`, `/preferences` | `get_current_user` |
| `risk.py` | `/api/risk` | `/analyze`, `/var`, `/stress-test` | `get_current_user` |
| `saved_screens.py` | `/api/saved-screens` | `/`, `/{id}` | `get_current_user` |
| `screener.py` | `/api/scan` | `/`, `/countries`, `/segments` | `get_supabase_anon` |
| `smallcap.py` | `/api/smallcap` | `/mews`, `/discovery` | `get_supabase_anon` |
| `snapshots.py` | `/api/snapshots` | `/history`, `/capture` | `get_current_user` |
| `stocks.py` | `/api/stocks` | `/{ticker}`, `/{ticker}/similar`, `/{ticker}/financials` | `get_supabase_anon` |
| `strategy_lab.py` | `/api/strategy-lab` | `/strategies`, `/backtest`, `/barbell-optimize` | `get_current_user` |
| `tracking.py` | `/api/tracking` | `/click`, `/event` | `get_optional_user` |
| `transactions.py`| `/api/transactions` | `/`, `/{id}` | `get_current_user` |
| `watchlist.py` | `/api/watchlist` | `/`, `/{ticker}` | `get_current_user` |

---

## 5. Invarianter & Felsökningsrecept

1. **`def` vs `async def`:** Alla Supabase DB-handlers MÅSTE definieras som vanliga `def` (inte `async def`). FastAPI kör då anropet i en trådpool och blockerar inte event-loopen.
2. **CORS & Global Handler:** Kastade exceptions fångas av den globala exception-handlern i `apps/api/main.py` som alltid injicerar CORS-headers.
3. **Mall för nya routes:** Använd alltid `apps/api/routers/_TEMPLATE.py` vid skapande av nya routers.
4. **Felhantering med DB-översättning:** Använd `handle_db_error()` från `apps/api/core/db.py` för att mappa Postgres-felkoder (t.ex. `42501`) till informativa HTTP-svar.
