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
def get_public_data(db: Client = Depends(get_supabase)):
    return db.table("scan_results").select("*").execute()

# 2. Användarisolerad data med RLS (portfölj, watchlist, larm)
def get_user_portfolio(user: User = Depends(get_current_user), db: Client = Depends(get_user_supabase)):
    return db.table("portfolios").select("*").execute()

# 3. Privilegierade admin-operationer
def run_admin_action(admin: User = Depends(require_admin), db: Client = Depends(get_supabase_admin)):
    return db.table("pipeline_runs").select("*").execute()
```

---

## 4. Fullständig Router-Katalog (153 routes över 29 routers)

Alla endpoints är registrerade i `apps/api/main.py`:

| Router-fil | Prefix / Rutter | Viktiga Endpoints | Skydd |
|---|---|---|---|
| `main.py` & `request_id.py` | `/api/health`, `/api/debug/health` | Systemhälsa och requestId-diagnostik | Publikt / `require_admin` |
| `admin.py` | `/api/admin` | `/status`, `/pipeline-runs`, `/health`, `/diagnostics/deep`, `/workflow/trigger` | `require_admin` |
| `ai.py` | `/api/ai` | `/committee/{ticker}`, `/compare`, `/parse-filter`, `/daily-coach`, `/explain/{ticker}` | `get_current_user` |
| `alerts.py` | `/api/price-alerts` | `""`, `/{alert_id}`, `/check` (manuellt tröskellarm) | `get_current_user` |
| `smart_alerts.py` | `/api/alerts`, `/api/score-history`, `/api/signal-transitions` | `GET/POST /api/alerts`, `/api/alerts/triggered`, `/api/score-history/movers` | `get_current_user` / `get_supabase` |
| `calendar.py` | `/api/calendar` | `/earnings`, `/ipo`, `/dividends`, `/economic` | `get_supabase` |
| `feedback.py` | `/api/feedback` | `""` | `get_optional_user` |
| `forensic_audit.py` | `/api/ai` | `/forensic-audit/{ticker}` | `get_current_user` |
| `insider.py` | `/api/stocks`, `/api/insider-radar` | `/{ticker}/insider`, `/api/insider-radar` | `get_supabase` |
| `macro_regime.py` | `/api/macro-regime` | `/regime` | `get_supabase` |
| `market_intel.py` | `/api/market-intel` | `/shorts/{ticker}`, `/qmj/rank`, `/master/rank`, `/master/{ticker}`, `/radar` | `get_supabase` |
| `markets.py` | `/api/markets` | `/indices`, `/sectors`, `/top-movers`, `/sector-rotation` | `get_supabase` |
| `ml_performance.py` | `/api/ml-performance` | `/status`, `/confusion`, `/drift`, `/metrics` | `require_admin` |
| `notifications.py` | `/api/notifications`| `""`, `/unread-count`, `/mark-read`, `/{id}/read` | `get_current_user` |
| `paper_trading_router.py` | `/api/paper-trading`, `/paper` | `/account`, `/positions`, `/orders`, `/trades`, `/performance` | `get_current_user` |
| `portfolio.py` | `/api/portfolio` | `""`, `/{id}`, `/construct`, `/import/avanza/preview`, `/export/avanza` | `get_current_user` |
| `profile.py` | `/api/profile` | `""`, `/preferences`, `/risk`, `/api-keys`, `/account` | `get_current_user` |
| `rebalancer.py` | `/api/portfolio/rebalance` | `/plan`, `/execute` | `get_current_user` |
| `risk.py` | `/api/portfolio` | `/analytics`, `/analytics/factor`, `/analytics/correlation`, `/optimize`, `/rebalance` | `get_current_user` |
| `saved_screens.py` | `/api/screens` | `""`, `/{screen_id}` | `get_current_user` |
| `screener.py` | `/api/scan` | `""`, `/sectors`, `/countries`, `/segments`, `/meta` | `get_supabase` |
| `smallcap.py` | `/api/smallcap` | `""`, `/sectors` (MEWS- och småbolagsscreening) | `get_supabase` |
| `snapshots.py` | `/api/snapshots` | `""`, `/capture`, `/latest` | `get_current_user` |
| `stocks.py` | `/api/stocks` | `""`, `/search`, `/{ticker}`, `/{ticker}/similar`, `/{ticker}/financials` | `get_supabase` |
| `strategy_lab.py` | `/api/strategies`, `/api/signal-analytics` | `/api/strategies`, `/api/strategies/{id}/run`, `/api/signal-analytics` | `get_current_user` |
| `tracking.py` | `/api/tracking` | `/pageview`, `/event`, `/session` | `get_optional_user` |
| `transactions.py`| `/api/transactions` | `""`, `/{transaction_id}` | `get_current_user` |
| `watchlist.py` | `/api/watchlist` | `""`, `/{ticker}` | `get_current_user` |

---

## 5. Invarianter & Felsökningsrecept

1. **`def` vs `async def`:** Alla Supabase DB-handlers MÅSTE definieras som vanliga `def` (inte `async def`). FastAPI kör då anropet i en trådpool och blockerar inte event-loopen.
2. **CORS & Global Handler:** Kastade exceptions fångas av den globala exception-handlern i `apps/api/main.py` som alltid injicerar CORS-headers.
3. **Mall för nya routes:** Använd alltid `apps/api/routers/_TEMPLATE.py` vid skapande av nya routers.
4. **Felhantering med DB-översättning:** Använd `handle_db_error()` från `apps/api/core/db.py` för att mappa Postgres-felkoder (t.ex. `42501`) till informativa HTTP-svar.
