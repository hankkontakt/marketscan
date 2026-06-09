# MarketScan — Komplett systemdokumentation (AI-underhåll)

> 🧭 **NY AI? Läs `docs/AI_GUIDE.md` FÖRST** — den är den operativa manualen (hur
> du ska tänka, alla verktyg, buggmönster, vanliga uppgifter). Den här filen
> (`SYSTEM_AI.md`) är referens-uppslagsverket: varje fil, funktion och dataflöde.
>
> **Underhållsprotokoll**: Uppdatera denna fil varje gång du ändrar kod, hittar en bugg,
> eller upptäcker en förbättringsmöjlighet — även om det inte hör ihop med uppgiften du
> arbetar med just nu. Lägg till under rätt sektion nedan.

---

## 0. Underhållsprotokoll (senaste ändringar)

| Datum | Fas | Ändring | Fil |
|---|---|---|---|
| 2026-06-09 | mega | **Systemhärdning + DX-megaprojekt.** (1) Audit: 89 `async def`-handlers som bara gjorde synkrona Supabase-anrop → konverterade till `def` (ingen event-loop-blockering) via AST-transformer. (2) Säkerhet: 3 oautentiserade dyra LLM-endpoints (`/ai/parse-filter`, `/ai/committee`, `/ai/compare`) → kräver nu auth (kostnads-/DoS-skydd). (3) Verktyg: `GET /api/admin/diagnostics/deep` (env+grants+migrations på ett anrop), `scripts/smoke_test.py` (hela API-ytan), `scripts/fix_async_handlers.py`. (4) DX: `apps/api/core/db.py` (översätter DB-fel till läsbara HTTPExceptions), `routers/_TEMPLATE.py`, `docs/CONTRIBUTING.md`. (5) Admin-UI: ny "Diagnostik"-flik. (6) Smoke-test hittade `/api/smallcap` 500 = `42501` på `smallcap_results` för anon → fixas av migration 023. | många |
| 2026-06-08 | fix | **🔴 DEN VERKLIGA ROTORSAKEN bakom import-felet: saknade table-GRANTs (Postgres 42501).** Efter CORS-fixen visade sig det riktiga felet: `permission denied for table portfolios (42501)`. Tabeller skapade via SQL-migrationer fick aldrig table-privilegier till `authenticated`/`anon` — RLS var på men GRANT-lagret UNDER RLS saknades, så `get_user_supabase` (authenticated-rollen) nekas på portfolios/holdings/transactions/watchlist/alerts m.fl. Ny migration `023_grant_table_privileges.sql`: `GRANT SELECT,INSERT,UPDATE,DELETE` till authenticated på alla tabeller (RLS är per-rad-grinden), `SELECT` till anon, samt `REVOKE` skrivrätt på de 3 RLS-lösa tabellerna (scan_results, ai_cache, pipeline_runs) + `ALTER DEFAULT PRIVILEGES` för framtida tabeller. **MÅSTE köras manuellt i Supabase SQL Editor.** | `supabase/migrations/023_grant_table_privileges.sql` |
| 2026-06-08 | fix | **🔴 RIKTIG ROTORSAK till import "Nätverksfel": CORS-lösa 500-svar.** Starlette `add_middleware()` PREPENDAR → sist tillagd = ytterst. `RequestIDMiddleware` (rad 52, sist) ligger UTANFÖR `CORSMiddleware`. Ett *ohanterat* undantag i en route bubblar förbi CORS → Starlettes `ServerErrorMiddleware` returnerar 500 **utan CORS-headers** → browsern blockerar → `fetch()` kastar → "Nätverksfel" (maskerar det riktiga felet). Därför passerade alla mina probes: no-auth/bogus-token avvisas i `get_current_user` (dependency) FÖRE handlern → träffar inre `ExceptionMiddleware` → får CORS. En giltig token kör hela `import_confirm`, där portfölj-queryn på första raden saknade try/except. Fix: (1) global `@app.exception_handler(Exception)` som loggar tracebacken och returnerar JSON-500 MED CORS-headers (echo av tillåten Origin) — systemiskt skydd för ALLA routes; (2) wrap portfölj-query i `import_confirm` → HTTPException(502) med riktigt felmeddelande. **Lärdom: lägg ALDRIG en middleware efter CORS som inte själv hanterar fel; eller använd alltid en global exception-handler som sätter CORS-headers.** | `apps/api/main.py`, `apps/api/routers/portfolio.py` |
| 2026-06-08 | fix | **🔴 ARKITEKTURÄNDRING — import "Nätverksfel" löst.** `API_BASE = NEXT_PUBLIC_API_URL ?? ""` gav tom sträng (Vercel injicerar `NEXT_PUBLIC_API_URL=""`, och `??` fångar inte tom sträng) → browsern POST:ade till **samma origin** → web-deploymentens Vercel Deployment Protection redirectade till SSO → `fetch()` kastade TypeError → "Nätverksfel". Fix: `API_BASE = NEXT_PUBLIC_API_URL \|\| "https://marketscan-api.vercel.app"` (`\|\|` fångar även tom sträng) → browsern anropar API-domänen DIREKT (CORS verifierat live: OPTIONS+POST → 200/401 med rätt headers). **Tog även bort `rewrites()`-proxyn** (fas0 nedan) — den proxade genom den skyddade deploymenten. | `apps/web/lib/api.ts`, `apps/web/next.config.ts` |
| 2026-06-08 | fix | yfinance fallback för globala index: byt `fast_info.get()` → `Ticker.history(period="2d")` — fast_info stödjer inte `.get()` i nyare yfinance-versioner och fungerar inte för index utanför börsstängning | `apps/api/routers/markets.py` |
| 2026-06-08 | feat | Nytt screener-filter: **land** — `/api/scan/countries` endpoint, `country` i `ScanParams`, `useCountries()` hook, FilterRail-dropdown i utvikat läge | `screener.py`, `api.ts`, `useScreener.ts`, `FilterRail.tsx` |
| 2026-06-08 | fix | Admin "Mått"-histogram: färgkodade staplar (röd/gul/blå/grön per betygsnivå), räknarvärde ovanför varje stapel, ta bort `minHeight` på tomma staplar, byt signaltabell mot horisontell stapelchart | `AdminSections.tsx` |
| 2026-06-08 | feat | Admin "Inställningar" komplett: actionable setup-guider för GH_DISPATCH_TOKEN, R2 Storage, Supabase service role, admin-SQL, databas-migrationer, universum-expansion | `AdminSections.tsx` |
| 2026-06-08 | fix | Service worker: `apiRoute` (NetworkOnly) placerad FÖRST i `runtimeCaching` — `defaultCache` från `@serwist/next` hade en NetworkFirst+10s-regel för `/api/*` GET som tog prioritet | `apps/web/app/sw.ts` |
| 2026-06-08 | fix | Admin `security.py`: rollkälla justerad till `app_metadata.role` (JWT) + `asyncio.to_thread` runt Supabase-anrop | `apps/api/core/security.py` |
| 2026-06-08 | fix | Oversikt "Dagens marknad": tom up/down-lista visar nu "Ingen prisdata för idag — kör pipeline" istf blank | `apps/web/app/(app)/oversikt/OversiktView.tsx` |
| 2026-06-08 | fas0 | Skapa tom `apps/__init__.py` — `from apps.api.main import app` kräver att `apps` är ett Python-paket | `apps/__init__.py` |
| 2026-06-08 | fas0 | Fix path-bugg i Vercel-shim: `dirname(abspath(__file__))` gav `<repo>/api`, inte `<repo>` | `api/main.py` |
| 2026-06-08 | fas0 | Lägg till Next.js `rewrites()` proxy `/api/*` → `marketscan-api.vercel.app` | `apps/web/next.config.ts` |
| 2026-06-08 | fas1 | Ny migration: RLS-härdning alla user-tabeller + `client_errors`-tabell | `supabase/migrations/018_rls_hardening.sql` |
| 2026-06-08 | fas1 | Lägg till `@limiter.limit("10/minute")` på `/api/debug/client-error` | `apps/api/core/request_id.py` |
| 2026-06-08 | fas1 | Strama CORS-regex från `.*hankkontakts.*` till `web-[a-z0-9-]+-hankkontakts-projects` | `apps/api/main.py` |
| 2026-06-08 | fas2 | FX-normalisering av `market_cap` (SEK→USD) före segment-klassificering | `backend_worker/db_loader.py` |
| 2026-06-08 | fas2 | UTF-8-härdning: `client_encoding="UTF8"` + `encoding="utf-8"` till `to_csv()` | `backend_worker/db_loader.py` |
| 2026-06-08 | fas3 | DEPRECATED-header på `hrp_optimizer.py`, `portfolio_snapshot.py`, `load_data.py` | alla tre filer |
| 2026-06-08 | mega1 | **Risk Analytics**: `risk_analyzer.py`, migration 019, API-router `risk.py`, `RiskView.tsx`, hooks | se nedan |
| 2026-06-08 | mega2 | **Smart Alerts**: `score_tracker.py`, `smart_alert_engine.py`, `digest_mailer.py`, migration 020, router `smart_alerts.py`, hooks | se nedan |
| 2026-06-08 | mega3 | **Strategy Lab**: `strategy_backtester.py`, `signal_analytics.py`, migration 021, router `strategy_lab.py`, `StrategiLabView.tsx`, `SignalAnalyticsView.tsx`, hooks | se nedan |
| 2026-06-08 | infra | 6 nya GH Actions workflows: score_tracker, risk_analysis, smart_alerts, digest, signal_analytics, strategy_backtester | `.github/workflows/` |
| 2026-06-08 | infra | NavRail: lade till Strategi Lab (FlaskConical) + Signalanalys (Activity) | `NavRail.tsx` |
| 2026-06-08 | infra | PortfoljView: lade till länk-kort till djupgående riskanalys | `PortfoljView.tsx` |
| 2026-06-08 | infra | Nya TS-typer: RiskMetrics, FactorExposure, CorrelationMatrix, OptimizeResult, RebalanceResult, AlertRule, TriggeredAlert, Strategy, StrategyRun, SignalAnalytics | `types/portfolio.ts`, `types/alerts.ts`, `types/strategy.ts` |
| 2026-06-08 | fix | Next.js 15: `params: Promise<{id}>` + `await params` i `/strategi-lab/[id]/page.tsx` | `strategi-lab/[id]/page.tsx` |
| 2026-06-08 | fix | Kalender 401: byt `get_current_user` → `get_optional_user` i `/calendar`-endpoints | `apps/api/routers/calendar.py` |
| 2026-06-08 | fix | Admin JWT: `payload.role` är alltid `"authenticated"` — custom roller ligger i `payload.app_metadata.role` | `kontrollpanel/page.tsx`, `NavRail.tsx` |
| 2026-06-08 | fix | SQL för att sätta admin-roll: `UPDATE auth.users SET raw_app_meta_data = raw_app_meta_data \|\| '{"role":"admin"}' WHERE id = '<uid>'` | (Supabase SQL-editor) |
| 2026-06-08 | feat | Compare-vy: yfinance-fallback för aktier utanför universumet via `_yfinance_fundamentals()` | `apps/api/routers/stocks.py` |
| 2026-06-08 | feat | Globala index: yfinance-fallback (`^OMX ^GSPC ^IXIC ^DJI ^FTSE ^GDAXI ^STOXX50E ^N225 ^HSI`) när FINNHUB_API_KEY saknas | `apps/api/routers/markets.py` |
| 2026-06-08 | feat | MultiFactorRadar: stapel/radar-toggle (`BarView` / `RadarView`) med Recharts RadarChart | `apps/web/components/charts/MultiFactorRadar.tsx` |
| 2026-06-08 | feat | Strategy Lab: HowItWorksBox-komponent med collapsible förklarare på klarspråk | `apps/web/app/(app)/strategi-lab/StrategiLabView.tsx` |
| 2026-06-08 | feat | Avanza-import: omskriven `ImportModal.tsx` med tvåfilsuppladdning (positioner + inkopskurs) | `apps/web/components/portfolio/ImportModal.tsx` |
| 2026-06-08 | feat | Avanza-import: `parse_positioner_csv`, `parse_inkopskurser_csv`, `kortnamn_to_ticker`, `get_buy_date` | `apps/api/core/avanza_import.py` |
| 2026-06-08 | feat | Avanza-import: ny endpoint `POST /api/portfolio/import/avanza/preview` — parsar båda CSV-filerna server-side | `apps/api/routers/portfolio.py` |
| 2026-06-08 | feat | Avanza-import: `/import/confirm` skapar nu `buy`-transaktion med köpdatum när `purchase_date` är känt | `apps/api/routers/portfolio.py` |
| 2026-06-08 | fix | Admin-sektioner (Status/Hälsa/Universum/Mått) visade ingenting vid API-fel — nu visas `ErrorBlock` med retry-knapp | `apps/web/components/admin/AdminSections.tsx` |
| 2026-06-08 | fix | Marknadsöversikt: "Finnhub API-nyckel krävs"-meddelande ersatt med generisk feltext + retry-knapp | `apps/web/app/(app)/marknad/MarknadView.tsx` |
| 2026-06-08 | fix | Strategi Lab subtitle: teknisk text → klarspråk ("Testa hur en aktieväljarstrategi hade presterat historiskt") | `StrategiLabView.tsx` |
| 2026-06-08 | fix | Signalanalys: all intern terminologi bortplockat (score_tracker.py, signal_transitions, entry_signal); kolumnnamn och beskrivningar på klarspråk | `SignalAnalyticsView.tsx` |

---

## 1. Systemöversikt

### Arkitektur

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions  (stock-scanner + marketscan repo)        │
│  PYTHONPATH="marketscan:stock-scanner"                    │
│  backend_worker/pipeline/entrypoint.py --mode morning     │
│      ↓                                                    │
│  _fast_pipeline()                                         │
│    1. Läs parquet (stock-scanner/reports/)                │
│    2. Uppdatera priser via yfinance (~10 sek)             │
│    3. Spara ny parquet                                    │
│    4. COPY → Supabase (psycopg2 bulk, ~2 sek)            │
│    5. Ladda upp snapshot till R2 (valfritt)               │
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Vercel: marketscan-api.vercel.app       │
│  FastAPI (Python serverless)             │
│  apps/api/main.py (full app)             │
│  api/main.py (Vercel shim → apps/api)   │
│  vercel.json: maxDuration=60            │
└─────────────────────────────────────────┘
         ↑ direkt cross-origin fetch (CORS)
┌─────────────────────────────────────────┐
│  Vercel: web-…-hankkontakts-…vercel.app │
│  Next.js 14 (App Router)                │
│  apps/web/                              │
│  API_BASE = NEXT_PUBLIC_API_URL         │
│    || "https://marketscan-api…"         │
│  (ingen proxy — direkt till API-domän)  │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Supabase (Postgres + Auth + RLS)       │
│  scan_results  — ingen RLS (publik läs) │
│  profiles/portfolios/etc — RLS aktivt   │
└─────────────────────────────────────────┘
```

### Repo-struktur

| Katalog | Innehåll |
|---|---|
| `apps/api/` | FastAPI-app, routers, core |
| `apps/web/` | Next.js 14 frontend |
| `backend_worker/` | Pipeline-stöd: db_loader, r2_uploader, ml_trainer m.fl. |
| `backend_worker/pipeline/` | GitHub Actions entrypoint |
| `supabase/migrations/` | SQL-migrationer 001–018 |
| `api/` | Vercel-shim som re-exportar FastAPI-appen |
| `docs/` | Denna fil + PIPELINE_SETUP.md |

---

## 2. Deploy-arkitektur (Vercel)

### Två separata projekt

| Projekt | URL | Konfiguration |
|---|---|---|
| `marketscan-api` | `https://marketscan-api.vercel.app` | `vercel.json`: `functions: {"apps/api/main.py": {maxDuration: 60}}` |
| `web` | `https://web-…-hankkontakts-projects.vercel.app` | Next.js |

### Hur frontend når API:t

1. `apps/web/lib/api.ts`: `API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://marketscan-api.vercel.app"`
2. Browsern anropar **API-domänen direkt** (cross-origin). CORS i `apps/api/main.py` tillåter web-domänen via `allow_origin_regex`.
3. **Ingen `rewrites()`-proxy.** Den togs bort 2026-06-08.

> **🔴 OBS — läs detta innan du rör API-routingen:**
> - Använd `||`, **aldrig** `??`. Vercel injicerar `NEXT_PUBLIC_API_URL=""` (tom sträng) i web-projektet, och `?? ""` behåller den tomma strängen → `API_BASE=""` → browsern POST:ar till **samma origin**.
> - Web-deploymenten har **Vercel Deployment Protection** (SSO-redirect). En same-origin `/api/*`-POST redirectas då cross-origin → `fetch()` kastar TypeError → **"Nätverksfel"**. Detta var roten till import-buggen.
> - **Proxa INTE** `/api/*` same-origin via `rewrites()` — det routar genom den skyddade deploymenten och återinför buggen.
> - Default-värdet `https://marketscan-api.vercel.app` är hårdkodat så fixen håller även om Vercel-env-varen saknas/är tom. Sätt gärna `NEXT_PUBLIC_API_URL` korrekt ändå, men koden är robust utan den.

### Vercel-shim (`api/main.py`)

```python
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # <repo>
sys.path.insert(0, _repo_root)
from apps.api.main import app
```

`apps/__init__.py` **måste existera** (tomt) för att `from apps.api.main import app` ska fungera.

---

## 3. Pipeline (GitHub Actions)

### Entrypoint

```
backend_worker/pipeline/entrypoint.py  run(mode)
```

**Fast path** (morning / evening / manual):
1. Ladda senaste `scored_universe_*.parquet` från `stock-scanner/reports/`
2. Uppdatera priser med `core.data_fetcher.fetch_prices_only()` (~10 sek)
3. Hoppa över ML-predictions (yfinance per ticker → hänger i timmar utan cache)
4. Spara uppdaterad parquet
5. `db_loader.load_scan()` → Supabase via `COPY`
6. `r2_uploader.upload_score_snapshot()` (om R2-nycklar finns)

**Full path** (weekly / smallcap):
- Kör `core.daily_pipeline.run_pipeline(mode)` med SIGALRM-timeout (75 min)
- Fallback: läs senaste sparad parquet om timeout

### Kända gotchas

| Problem | Lösning |
|---|---|
| `run_pipeline('morning')` hänger (nyheter/AI/SMTP) | Fast path kringgår `run_pipeline()` helt |
| ML-predictions hänger (yfinance cache saknas) | Hoppa över i fast path |
| `invalid input syntax for type integer: "12.8"` | `ml_rank`/`piotroski_f` castas till `Int64` i `_prepare_df` |
| `ValueError: Invalid endpoint: ` (boto3) | `_r2_configured()` guard returnerar tidigt om R2-variabler saknas |
| Nästan alla bolag klassas som `large_cap` | SEK-värden normaliseras till USD via `_FX_TO_USD`-map (fas2-fix) |

---

## 4. FastAPI-app (`apps/api/`)

### Middleware-ordning (utifrån in)

1. `GZipMiddleware` (minimum_size=1000)
2. `CORSMiddleware`
   - `allow_origins` = från `settings.CORS_ORIGINS`
   - `allow_origin_regex` = `r"https://web-[a-z0-9-]+-hankkontakts-projects\.vercel\.app"`
3. `SecurityHeadersMiddleware` (via `add_security_headers`)
4. `SlowAPIMiddleware` (rate limiting)
5. `RequestIDMiddleware` (X-Request-ID, logging)

### Routers

| Router | Prefix | Auth |
|---|---|---|
| `screener` | `/api` | publik (scan_results utan RLS) |
| `stocks` | `/api` | publik |
| `portfolio` | — | kräver JWT |
| `ai` | `/api` | kräver JWT, rate-limitad |
| `admin` | `/api` | `require_admin` |
| `calendar` | `/api` | publik |
| `debug` | `/api/debug` | `/health` kräver admin; `/client-error` publik, rate-limitad |

### Konfiguration (`apps/api/core/config.py`)

Läser från `.env` och miljövariabler via pydantic-settings. Alla API-nycklar deklareras här.

### Säkerhetsregler

- `GH_CHECKOUT_TOKEN` — aldrig i frontend/bundeln, bara backend-secret
- `service_role`-nyckel — bara i `backend_worker`/admin-endpoints
- Logga aldrig tokens, lösenord eller PII
- `/api/debug/*` — MÅSTE vara admin-skyddat (läcker systeminformation)
- `/api/debug/client-error` — rate-limitad 10/min/IP via slowapi

---

## 5. Databas (Supabase)

### Migreringsöversikt

| Migration | Innehåll |
|---|---|
| 001 | Grundschema: scan_results, profiles, portfolios, holdings, watchlist, price_alerts, saved_screens, pipeline_runs |
| 002 | portfolio_snapshots |
| 003 | ai_cache |
| 004 | ml_predictions |
| 005 | smallcap_results |
| 006 | paper_trading (paper_portfolios, paper_trades, paper_positions) |
| 007 | backtest_results |
| 008 | sector_rotation |
| 009 | portfolio_optimizations |
| 010 | universe_candidates |
| 011 | options_data |
| 012 | notification_preferences (+ uppdaterad handle_new_user trigger) |
| 013 | notifications |
| 014 | transactions |
| 015 | insider_trades |
| 016 | ai_journal |
| 017 | user_ticker_requests |
| **018** | **RLS-härdning: FOR ALL WITH CHECK på alla user-tabeller; client_errors-tabell** |

### RLS-principer

- `scan_results` — **ingen RLS** (publik läsning, service_role skriver)
- Alla user-tabeller — `FOR ALL USING ((select auth.uid()) = user_id) WITH CHECK (...)`
- Cached `(select auth.uid())` föredras över `auth.uid()` direkt (performance)
- `notifications` — INSERT reserverat för service_role (backend); users: SELECT/UPDATE/DELETE
- `client_errors` — ingen policy = bara service_role kan läsa/skriva

### scan_results COPY-laddning

```python
# db_loader.load_scan()
buf = io.StringIO()
prepared.to_csv(buf, index=False, header=False, na_rep="", encoding="utf-8")
buf.seek(0)
with psycopg2.connect(dsn, client_encoding="UTF8") as con:
    cur.execute("TRUNCATE scan_results;")
    cur.copy_expert("COPY scan_results (...) FROM STDIN WITH (FORMAT csv, NULL '')", buf)
```

### Segment-klassificering

`market_cap` normaliseras till USD med statisk FX-map innan tröskeltestning:

```python
_FX_TO_USD = {"SEK": 0.093, "EUR": 1.08, "USD": 1.0, ...}  # uppdatera periodiskt
SEGMENT_THRESHOLDS = {"large_cap": 10B, "mid_cap": 2B, "small_cap": 300M}  # USD
```

---

## 6. Frontend (`apps/web/`)

### API-klient

`apps/web/lib/api.ts`:
- `API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://marketscan-api.vercel.app"` (direkt till API-domänen, `||` inte `??` — se §2 "Hur frontend når API:t")
- Lägger till Supabase JWT automatiskt om session finns
- 55s `AbortController`-timeout → `ApiError(408, ...)`; nätverks-TypeError → `ApiError(0, "Nätverksfel ...")`
- Kastar `ApiError` (med HTTP-statuskod) vid fel

### PWA

Serwist (`@serwist/next`) konfigurerat i `next.config.ts`. Service worker: `app/sw.ts` → `public/sw.js`. Inaktiverat i `development`.

---

## 7. Kända förbättringsmöjligheter (backlog)

| ID | Beskrivning | Prioritet |
|---|---|---|
| B1 | ML-predictions i fast pipeline: behöver lokal OHLCV-cache för att aktiveras | Låg |
| B2 | FX-rater i `_FX_TO_USD` är statiska — uppdatera kvartalsvis eller hämta dynamiskt | Låg |
| B3 | `portfolio_snapshot.py` som GH Actions cron-jobb — aktivera om snapshotfunktionen behöver bakgrundskörning | Medel |
| B4 | `price_alert_checker.py` — planerad notificationkälla (Fas 6) | Medel |
| B5 | Shared rate-limit counter för Vercel (nuvar per-instans) — Upstash Redis | Låg |
| B6 | Supabase Connection Pooling (port 6543) för production scalability | Medel |

---

## 8. Felsökningsguide

| Symptom | Rotorsak | Lösning |
|---|---|---|
| `500 FUNCTION_INVOCATION_FAILED` på API | Import-tids-krasch | Kontrollera `apps/__init__.py` finns, `api/main.py` har rätt `dirname(dirname(...))` |
| "Failed to fetch" i frontend | `NEXT_PUBLIC_API_URL` satt fel eller proxy saknas | Sätt tom sträng + verifiera `rewrites()` i `next.config.ts` |
| Tom aktielista trots pipeline-data | API returnerar 500 | Testa `curl https://marketscan-api.vercel.app/api/scan?limit=2` |
| Pipeline hänger efter XGBoost-varning | `run_pipeline()` anropar nyheter/AI/SMTP | Fast path kringgår — kör `manual`/`morning`/`evening` |
| `invalid input syntax for type integer` | `ml_rank` är float i parquet | Redan fixat i `_prepare_df` (round + Int64) |
| Nästan allt `large_cap` | SEK-värden jämfördes mot USD-trösklar | Fixat: `_to_usd()` normaliserar med FX-map |
| Mojibake i `entry_signal` | Fel encoding vid COPY | Fixat: `client_encoding="UTF8"` + `encoding="utf-8"` |
| `ModuleNotFoundError: No module named 'core'` | `PYTHONPATH` saknar stock-scanner | GH Actions workflow: `PYTHONPATH: "marketscan:stock-scanner"` |
| Backtest-resultat saknas trots klar run | `strategy_daily_equity` är tom | Kontrollera att `score_history` har data — backtests kräver historisk snapshotdata |
| Signalanalys visar inga rader | `signal_transitions` är tom | Vänta tills score_tracker körts och signaler faktiskt ändrats |
| Risk analytics visar bara beta/vol | Saknar nattlig cache | Kör `risk_analyzer.py` via GH Actions eller vänta till nästa natt |

---

## 9. Mega-projekt (implementerade 2026-06-08)

### 9.1 Risk Analytics

**Syfte:** Djupgående portföljriskanalys med nattlig beräkning.

**Flöde:**
```
GitHub Actions: risk_analysis.yml (nightly efter score_tracker)
  → backend_worker/risk_analyzer.py
    → hämtar prishistorik via yfinance (1 år)
    → beräknar Sharpe, Sortino, Calmar, VaR, CVaR, beta, max_drawdown, HRP/minvar
    → upsert → portfolio_risk_cache (per user_id)
    → upsert → portfolio_factor_exposure (weighted avg scores vs benchmark)
```

**API-endpoints (apps/api/routers/risk.py):**
- `GET /api/portfolio/analytics` — full riskrapport (cache + realtidsfallback)
- `GET /api/portfolio/analytics/factor` — faktorexponering vs benchmark
- `GET /api/portfolio/analytics/correlation` — korrelationsmatris
- `GET /api/portfolio/optimize` — HRP + minvar + equal weights
- `GET /api/portfolio/rebalance` — driftanalys + köp/sälj-förslag
- `POST/GET /api/portfolio/rebalance/targets` — CRUD för målallokeringar

**DB-tabeller:** `portfolio_risk_cache`, `portfolio_factor_exposure`, `rebalancing_targets`

**Frontend:** `/portfolj/risk` → `RiskView.tsx` (MetricTiles, CorrelationHeatmap, FactorRadar, OptimizeView, RebalanceDriftView)

---

### 9.2 Smart Alerts

**Syfte:** Compound larmsystem med 6 regeltyper + veckodigest.

**Flöde:**
```
score_tracker.yml (nightly after pipeline):
  → backend_worker/score_tracker.py
    → snapshot scan_results → score_history
    → jämför med förra snapshot → signal_transitions

smart_alerts.yml (nightly):
  → backend_worker/smart_alert_engine.py
    → laddar alla aktiva alert_rules
    → utvärderar 6 typer: price_cross, score_change, signal_change,
      screen_match, insider_cluster, volatility_spike
    → batch-insert notifications + triggered_alerts

digest.yml (varje måndag 09:30):
  → backend_worker/digest_mailer.py
    → bygger HTML via email/layout.py + components.py
    → skickar via Resend API
    → loggar i digest_log
```

**API-endpoints (apps/api/routers/smart_alerts.py):**
- `GET/POST/PUT/DELETE /api/alerts` — CRUD för compound larmregler
- `GET /api/alerts/triggered` — historik senaste 30 dagar
- `GET /api/score-history/{ticker}` — betygstidslinje per aktie
- `GET /api/score-history/movers` — störst betygskändringar N dagar
- `GET /api/signal-transitions/{ticker}` — transitionshistorik per aktie

**DB-tabeller:** `score_history`, `signal_transitions`, `alert_rules`, `triggered_alerts`, `digest_log`

---

### 9.3 Strategy Lab

**Syfte:** Backtestar screener-strategier mot historiska betygssnapshots.

**Flöde:**
```
Frontend: POST /api/strategies/{id}/run
  → skapar strategy_runs med status=pending
  → försöker köra in-process i bakgrundstask (om DATABASE_URL satt)

strategy_backtester.yml (nightly, --run-pending):
  → backend_worker/strategy_backtester.py
    → hämtar alla pending strategy_runs
    → för varje run: laddar score_history, simulerar portfölj,
      räknar om vid rebalanceringsdatum, applicerar courtage
    → skriver equity-kurva till strategy_daily_equity
    → uppdaterar strategy_runs med alla metrics

signal_analytics.yml (varje söndag):
  → backend_worker/signal_analytics.py
    → grupperar signal_transitions per (field, from, to)
    → beräknar hålltid, framåtavkastning, win rate, sektorbrytning
    → upsert → signal_persistence_cache
```

**API-endpoints (apps/api/routers/strategy_lab.py):**
- `GET/POST/PUT/DELETE /api/strategies` — CRUD + publik delning
- `POST /api/strategies/{id}/run` — kö-ar backtest (202 Accepted)
- `GET /api/strategies/{id}/results` — metrics + equity-kurva
- `GET /api/strategies/compare?run_ids=…` — jämför upp till 5 runs
- `GET /api/signal-analytics` — alla transition-statistik
- `GET /api/signal-analytics/{field}/{from}/{to}` — detaljvy + exempel

**DB-tabeller:** `strategies`, `strategy_runs`, `strategy_daily_equity`, `signal_persistence_cache`

**Frontend:** `/strategi-lab` (lista + skapa), `/strategi-lab/[id]` (equity-kurva + metrics), `/signal-analytics` (tabellvy med drill-down)

---

### 9.4 Deployment-checklista för mega-projekten

1. **Kör DB-migrationer i Supabase SQL-editor** (i ordning):
   - `019_risk_analytics.sql`
   - `020_smart_alerts.sql`
   - `021_strategy_lab.sql`

2. **Redeploya `marketscan-api`** (ny routerregistrering i `main.py`)

3. **Redeploya `web`** (ny NavRail-länkar, nya sidor)

4. **Sätt GitHub Secrets** om de saknas:
   - `DATABASE_URL` — direktanslutning PostgreSQL (psycopg2)
   - `RESEND_API_KEY` — för digest-mailer
   - `EMAIL_FROM` — avsändaradress (t.ex. `digest@marketscan.se`)
   - `APP_URL` — frontend-URL för CTA-knappar i email

5. **Triggra score_tracker manuellt** första gången för att fylla `score_history`

6. **Notera:** strategy backtests kräver ≥7 dagars `score_history` för meningsfull data
