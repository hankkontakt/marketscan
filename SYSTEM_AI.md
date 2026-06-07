# MarketScan 2.0 — SYSTEM_AI.md

> **Fullständig teknisk referens för AI-agenter.** Skriven för att en ny AI-modell utan tidigare kontext ska kunna förstå hela systemet, göra ändringar och felsöka på egen hand.
>
> **Senast uppdaterad:** 2026-06-07
>
> **Läs ALLTID HANDOFF.md först** — den har användarens design-filosofi och projektets historia.

---

## 0. Underhållsprotokoll

**Obligatoriskt för alla AI-modeller som gör kodändringar:**

| Händelse | Skriv i |
|---|---|
| Genomförd kodändring | Relevant sektion + en rad i §19 Ändringslogg |
| Bugg eller risk | §17 Kända problem |
| Förbättringsidé | §18 Förbättringsidéer |
| Fixat något från §17 | Markera `DONE ✅`, radera inte raden |

Format ändringslogg: `YYYY-MM-DD — beskrivning (fil:rad)`. Nyaste överst.

---

## 1. Snabbreferens

### 1.1 Vanligaste uppgifter

| Uppgift | Kommando |
|---|---|
| Starta API lokalt | `cd marketscan && python -m uvicorn apps.api.main:app --reload --port 8000` |
| Starta frontend lokalt | `cd apps/web && npm run dev` |
| Ladda data från pipeline | `cd marketscan && python load_data.py` |
| Lägg till ny API-route | `apps/api/routers/` + registrera i `main.py` |
| Lägg till ny sida | `apps/web/app/(app)/ny-sida/page.tsx` + View-fil |
| Ändra designsystem | `apps/web/app/globals.css` (CSS-variabler) |
| Bygg frontend (type-check) | `cd apps/web && npx tsc --noEmit` |
| Se alla API-routes | Starta API, öppna `http://localhost:8000/docs` |
| Kör SQL-migration | Supabase Dashboard → SQL Editor → klistra in |

### 1.2 Kritiska regler — ALDRIG bryta

1. **`backend_worker/` får ALDRIG importeras av `apps/api/`.** Vercel 500MB-gräns. pandas, xgboost, yfinance är förbjudna i API.
2. **React 18.3 — uppgradera INTE till 19.** Radix UI kräver 18.
3. **Supabase service key** används bara i backend_worker/ och load_data.py. Exponeras ALDRIG i frontend.
4. **Inga emojis i UI** — alltid Lucide-linjeikoner.
5. **Inga globala variabler i FastAPI** — Vercel spinnar upp/ner instanser (stateless).
6. **InfoTooltip (`i`-bubbla)** används ÖVERALLT bredvid finansiella värden.
7. **DATABASE_URL måste vara Session Pooler** (port 6543), INTE Direct (port 5432).
8. **Två separata Vercel-projekt** — frontend och API deployas oberoende. Se §16.

---

## 2. Systemöversikt

**Vad:** Modern webbapp för aktieanalys och screening. Next.js-frontend + FastAPI-backend + Supabase-databas. Ersätter gamla Streamlit-prototypen (`stock-scanner-fix`).

**Målgrupp:** Hobbyinvesterare. "Lysa-lugn" design + "Avanza-handlingsbar" touch. Svensk UI. Progressiv disclosure (enkelt först, detaljer på begäran).

**Arkitektur (viktig!):**

```
Frontend (Vercel project: marketscan)       API (Vercel project: marketscan-api)
https://marketscan.vercel.app                https://marketscan-api.vercel.app
         │                                            │
         │  fetch til API (NEXT_PUBLIC_API_URL)        │
         └─────────────────────────────────────────────┘
                                                       │
                                                       ▼
                                              Supabase Postgres
                                         (eu-north-1, Stockholm)

GitHub Actions (backend_worker/)
    └── Daglig pipeline: yfinance → pandas → XGBoost → Supabase
    └── Cron-jobb: prislarm, portfölj-snapshots
```

### 2.1 Stack — exakta versioner

| Lager | Teknik | Version |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Next.js 15.5, React 18.3 |
| Styling | Tailwind CSS v4 | |
| Komponent-primitiver | Radix UI (Dialog, Select, Tooltip, Tabs, Dropdown, Switch) | |
| Charts | Recharts (area, pie, donut, radar) + Lightweight Charts (candlestick) | |
| Ikoner | Lucide React | |
| Typsnitt | Inter (allt) + Geist Mono (monospace för priser) | next/font/google |
| State/datahämtning | TanStack React Query v5 | |
| Auth-klient | @supabase/ssr + supabase-js | |
| Command palette | cmdk | |
| Toast-notiser | Sonner | |
| Backend | FastAPI + Python 3.12 | |
| Auth-validering | PyJWT HS256 (lokal, inga nätverksanrop) | |
| Databas (het) | Supabase Postgres (eu-north-1, Stockholm) | |
| Kall lagring | Cloudflare R2 + DuckDB — EJ KONFIGURERAT (betalningsproblem) | |
| Pipeline | GitHub Actions — workflow-filer finns, EJ KOPPLADE TILL NY DB | |

### 2.2 Designbeslut

| Beslut | Varför |
|---|---|
| Next.js App Router + SSR | SEO för landningssida, middleware för auth-gate |
| FastAPI serverless (Vercel) | Gratis hosting, autoskalning |
| Supabase för all användardata | Inbyggd auth, RLS, Postgres |
| TanStack Query | Automatisk cachning, dedup, re-fetch |
| CSS-variabler för teman | Ljust/mörkt/auto-tema utan runtime CSS-in-JS |
| Inter för all typografi | Exakt som Lysa — enhetligt, professionellt |
| Progressiv disclosure | Enkel vy först, djupdyk på begäran |
| Mock-data som fallback | R2 ej konfigurerat — deterministisk mock så UI fungerar alltid |
| backend_worker/ isolerat | pandas/xgboost/yfinance får ej finnas i API (Vercel 500MB-gräns) |

---

## 3. Katalogstruktur (komplett)

```
marketscan/
├── apps/
│   ├── web/                                     # Next.js frontend (localhost:3000)
│   │   ├── app/
│   │   │   ├── (marketing)/page.tsx            # Landningssida (publik, SEO)
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx              # Inloggning
│   │   │   │   ├── register/page.tsx           # Registrering
│   │   │   │   └── reset/page.tsx              # Glömt lösenord
│   │   │   ├── (app)/                          # Skyddade sidor (kräver inloggning)
│   │   │   │   ├── layout.tsx                  # App-shell: NavRail + TopBar + CommandPalette
│   │   │   │   ├── oversikt/                   # Dashboard (Lysa-stil)
│   │   │   │   ├── screener/                   # Aktie-screener ("Aktier" i UI)
│   │   │   │   ├── aktie/[ticker]/             # Aktiekort (5 flikar)
│   │   │   │   ├── portfolj/                   # Min portfölj
│   │   │   │   ├── bevakningar/                # Bevakningar + prisriktkurslarm
│   │   │   │   ├── kalender/                   # Kalender (rapporter, IPO, ekonomi)
│   │   │   │   ├── jamfor/                     # Aktiejämförelse
│   │   │   │   ├── marknad/                    # Marknadsöversikt
│   │   │   │   ├── guide/                      # Utbildningssida
│   │   │   │   ├── kontrollpanel/              # Admin-vy
│   │   │   │   └── installningar/              # Användarinställningar
│   │   │   ├── layout.tsx                      # Root: Inter-font, tema, Toaster, QueryProvider
│   │   │   └── globals.css                     # ALLA CSS-variabler och design tokens
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── InfoTooltip.tsx             # "i"-bubbla med Radix Tooltip
│   │   │   │   └── MetricCard.tsx              # Återanvändbar metrik-komponent
│   │   │   ├── charts/
│   │   │   │   ├── PriceChart.tsx              # Lightweight Charts (candlestick + MA50/200 + volym)
│   │   │   │   ├── FactorRadar.tsx             # Recharts radar (8 faktorer)
│   │   │   │   └── ScoreSparkline.tsx          # SVG sparkline för betygstrend
│   │   │   ├── screener/
│   │   │   │   ├── FilterRail.tsx              # Expanderbara filter med InfoTooltips
│   │   │   │   ├── ResultTable.tsx             # Sorterbar tabell + tangentbordsnavigering
│   │   │   │   └── SegmentToggle.tsx           # Chip-väljare för segment
│   │   │   ├── stock/
│   │   │   │   ├── VerdictHeader.tsx           # Sticky aktie-header (namn stort, ticker litet)
│   │   │   │   └── AnalysCommittee.tsx         # 3 AI-analytiker + ordförande
│   │   │   ├── layout/
│   │   │   │   ├── NavRail.tsx                 # Ikonnavigation vänster med hover-labels
│   │   │   │   └── TopBar.tsx                  # Sök + tema + profilmeny
│   │   │   ├── command/
│   │   │   │   └── CommandPalette.tsx          # Ctrl+K sökning
│   │   │   ├── admin/
│   │   │   │   └── AdminSections.tsx           # Admin-panelens sektioner
│   │   │   └── providers/
│   │   │       └── QueryProvider.tsx           # TanStack Query setup
│   │   ├── hooks/
│   │   │   ├── useScreener.ts                  # React Query: scan_results + meta + sectors
│   │   │   ├── useStock.ts                     # React Query: enskild aktie, historik, nyheter, earnings
│   │   │   ├── usePortfolio.ts                 # React Query: portfolio, watchlist, alerts, history
│   │   │   ├── useMarkets.tsx                  # React Query: sectors, indices, market overview
│   │   │   ├── useTheme.ts                     # Ljust/mörkt/auto med localStorage
│   │   │   └── useCommandPalette.ts            # Event-bus för Ctrl+K open/close (Zustand)
│   │   ├── lib/
│   │   │   ├── api.ts                          # Typad fetch-wrapper mot FastAPI
│   │   │   ├── format.ts                       # formatPrice, signalLabel, scoreColorClass m.fl.
│   │   │   ├── labels.ts                       # Shared konstanter: FACTOR_LABELS, PERIOD_LABELS m.fl.
│   │   │   ├── utils.ts                        # cn() (clsx + tailwind-merge)
│   │   │   └── supabase/
│   │   │       ├── client.ts                   # Browser Supabase-klient
│   │   │       └── server.ts                   # SSR Supabase-klient
│   │   ├── types/scan.ts                       # TypeScript-typer (ScanRow)
│   │   ├── middleware.ts                       # Auth-gate (redirect /login)
│   │   ├── next.config.ts                      # devIndicators: false
│   │   └── package.json                        # React 18.3 (INTE 19)
│   └── api/                                    # FastAPI (localhost:8000)
│       ├── main.py                             # App + CORS + router-registrering + GZip + rate limiting
│       ├── dependencies.py                     # get_supabase(), get_supabase_admin()
│       ├── core/
│       │   ├── config.py                       # Pydantic Settings (läser .env)
│       │   ├── security.py                     # JWT-validering + require_admin
│       │   ├── ai_cache.py                     # Supabase-baserad AI-cache (24h TTL)
│       │   ├── deepseek_client.py              # DeepSeek API-anrop
│       │   ├── rate_limiter.py                 # slowapi (optional import — graceful degradation)
│       │   ├── security_headers.py             # CSP, HSTS, X-Frame-Options
│       │   └── duckdb_r2.py                    # R2-frågor via DuckDB (ej konfigurerat)
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── screener.py                     # GET /scan, /scan/meta, /scan/sectors
│       │   ├── stocks.py                       # GET /stocks/{ticker}, price-history, score-history, news, earnings, compare, insider, piotroski
│       │   ├── portfolio.py                    # CRUD: portfölj, holdings, watchlist, alerts, screens, snapshots, risk
│       │   ├── ai.py                           # POST /ai/parse-filter, committee, portfolio-coach
│       │   ├── admin.py                        # GET /admin/status, universe, score-distribution, pipeline-runs, users
│       │   ├── profile.py                      # PUT /api/profile, GET /api/profile
│       │   ├── markets.py                      # GET /markets/sectors, /markets/indices
│       │   ├── calendar.py                     # GET /calendar/earnings, ipo, economic
│       │   ├── snapshots.py                    # GET /snapshots (portfolio snapshot history)
│       │   ├── prediction.py                   # GET /predictions, /predictions/{ticker}
│       │   ├── smallcap.py                     # GET /smallcap, /smallcap/sectors
│       │   ├── options.py                      # GET /options/{ticker}
│       │   ├── backtests.py                    # GET /backtests, /backtests/{strategy}
│       │   ├── sector_rotation_router.py       # GET /sector-rotation
│       │   ├── paper_trading_router.py         # GET /paper/portfolio, POST /paper/trade, POST /paper/reset
│       │   └── saved_screens.py                # CRUD sparade screener-vyer
│       ├── schemas/
│       │   ├── scan.py                         # ScanRow, ScanFilters
│       │   └── portfolio.py                    # HoldingIn/Out, PortfolioOut, SnapshotIn/Out
│       └── requirements.txt                    # ALDRIG pandas/xgboost
├── backend_worker/                             # Tung Python — körs ALDRIG av API
│   ├── db_loader.py                            # copy_expert() bulk-load till Postgres
│   ├── r2_uploader.py                          # Parquet → R2 (ej konfigurerat)
│   ├── ml_trainer.py                           # XGBoost träning
│   ├── smallcap_scanner.py                     # Småbolagsscanner
│   ├── sector_rotation.py                      # Sektorrotation
│   ├── hrp_optimizer.py                        # Hierarchical Risk Parity
│   ├── universe_discovery.py                   # Universum-upptäckt
│   ├── paper_trading.py                        # Pappershandelsmotor
│   ├── backtest_runner.py                      # Backtesting
│   ├── options_scanner.py                      # Optionsdata
│   ├── pipeline/entrypoint.py                  # GitHub Actions brygga
│   ├── price_alert_checker.py                  # Cron: kolla larm mot priser
│   ├── portfolio_snapshot.py                   # Cron: dagliga portfölj-snapshots
│   └── requirements.txt                        # pandas, xgboost, yfinance, scikit-learn
├── supabase/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql              # Alla tabeller, index, RLS-policies
│   │   ├── 002_portfolio_snapshots.sql         # Portfolio snapshots-tabell
│   │   ├── 003_ai_cache.sql                    # AI-cache-tabell
│   │   ├── 004_ml_predictions.sql              # ML-prediktionsresultat
│   │   ├── 005_smallcap_scan.sql               # Småbolagsresultat
│   │   ├── 006_paper_trading.sql               # Pappershandel (3 tabeller)
│   │   ├── 007_ml_backtests.sql                # Backtestresultat
│   │   ├── 008_sector_rotation.sql             # Sektorrotation
│   │   ├── 009_portfolio_optimizer.sql         # Portföljoptimeringar
│   │   ├── 010_universe_discovery.sql          # Universumkandidater
│   │   └── 011_options_data.sql               # Optionsdata
│   └── seed.sql                                # 8 test-aktier
├── .github/workflows/
│   ├── pipeline.yml                            # Daglig pipeline
│   ├── pr-ci.yml                               # CI för PR: type-check, lint, test
│   ├── ml_train.yml                            # ML-träning
│   ├── smallcap_scan.yml                       # Småbolagsscan
│   ├── sector_rotation.yml                     # Sektorrotation
│   ├── backtest_runner.yml                     # Backtest
│   ├── universe_discovery.yml                  # Universum-upptäckt
│   ├── options_scan.yml                        # Optionsscan
│   └── check-pooler.yml                        # Databas-pooler-check
├── load_data.py                                # Engångsskript: importera parquet → Supabase
├── .env                                        # API-nycklar (läses av FastAPI från roten)
├── .env.example                                # Mall för .env
├── vercel.json                                 # Vercel-functions config + rewrites
├── requirements.txt                            # Rot-nivå requirements för Vercel Python build
├── HANDOFF.md                                  # Användarens design-filosofi + projektets hela historia
├── SETUP.md                                    # Uppstartsguide
├── STATUS.md                                   # Kort projektstatus
└── SYSTEM_AI.md                                # Detta dokument
```

---

## 4. Designsystem

### 4.1 Färger (CSS-variabler i `globals.css`)

**Ljust tema (`:root`, standard — Lysa/Avanza-inspirerat):**
```css
--color-bg-base:        #F8F9FB      /* sida-bakgrund */
--color-bg-surface:     #FFFFFF      /* kort, paneler */
--color-bg-elevated:    #F1F3F7      /* hover, popover */
--color-bg-overlay:     rgba(0,0,0,0.3)
--color-border:         #E3E6EC
--color-border-strong:  #C8CDD8
--color-text-primary:   #14181F
--color-text-secondary: #4A5567
--color-text-muted:     #8B929F
--color-accent:         #1D4ED8      /* institutionell blå */
--color-accent-soft:    rgba(29,78,216,0.08)
--color-accent-hover:   #1A44C2
--color-up:             #15803D      /* traditionell grön */
--color-up-soft:        rgba(21,128,61,0.08)
--color-down:           #DC2626      /* tydlig röd */
--color-down-soft:      rgba(220,38,38,0.08)
--color-warn:           #B45309
--color-warn-soft:      rgba(180,83,9,0.08)
--color-score-high:     #15803D      /* betyg 70+ */
--color-score-mid:      #1D4ED8      /* betyg 50–69 */
--color-score-low:      #8B929F      /* betyg <50 */
```

**Mörkt tema (`[data-theme="dark"]`):**
```css
--color-bg-base:        #0A0B0D
--color-bg-surface:     #131519
--color-bg-elevated:    #1B1E24
--color-accent:         #5B8DEF
--color-up:             #3FB68B
--color-down:           #E0645C
--color-score-high:     #3FB68B
--color-score-mid:      #5B8DEF
--color-score-low:      #6B7280
```

### 4.2 Layout

| Variabel | Värde | Användning |
|---|---|---|
| `--nav-width` | 64px | NavRail vänsterkolumn |
| `--topbar-height` | 56px | TopBar höjd |

CSS-grid: `grid-template-columns: var(--nav-width) 1fr; grid-template-rows: var(--topbar-height) 1fr`

### 4.3 Typsnitt

- **Inter** för all text inklusive siffror (Lysa-style)
- **Geist Mono** för monospace (priser, tickers, tabell-siffror) via `font-mono` klassen
- `tabular-nums` via `.tabular` CSS-klass för priser och procent (kolumner alignar)
- Laddat via `next/font/google` i `app/layout.tsx`
- `line-height: 1.6` body, `1.3` headings, `letter-spacing: -0.01em` headings

### 4.4 Komponentstil

- `InfoTooltip` — Radix Tooltip med "i"-ikon, används ÖVERALLT bredvid finansiella värden
- `MetricCard` — återanvändbar komponent för nyckeltal med label, value, tooltip, change
- Avrundade hörn: `rounded-xl` (12px) för kort, `rounded-2xl` (16px) för stora paneler
- Inga emojis — ALLTID Lucide-linjeikoner (strokeWidth={1.5})
- CSS-klasser: `.score-chip-high/mid/low`, `.signal-stark/ok/vanta/ej`, `.skeleton` (loading)

---

## 5. API — Complete Route Map

Alla routes prefixas med `/api/`. FastAPI körs på `http://localhost:8000` (dev) eller `https://marketscan-api.vercel.app` (prod).

**Totalt: ~60+ routes.**

### 5.1 Screener

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/scan` | GET | Nej | Hot path, Postgres only. Filter: segments[], score_min, score_max, sector, country, entry_signal, trend_signal, piotroski_min, pe_max, roe_min, dividend_yield_min, exclude_low_liquidity, search. Default large_cap+mid_cap, limit 200. |
| `/api/scan/sectors` | GET | Nej | Distinkta sektorer för filter-dropdown |
| `/api/scan/meta` | GET | Nej | Metadata: scan_date, total, by_segment |

### 5.2 Stocks

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/stocks?q=&limit=` | GET | Nej | Snabbsök ticker/name (⌘K-paletten) |
| `/api/stocks/{ticker}` | GET | Nej | Enskild aktie från scan_results |
| `/api/stocks/{ticker}/price-history` | GET | Nej | OHLCV. Först Finnhub API, sedan R2/DuckDB, sist mock-data. |
| `/api/stocks/{ticker}/score-history` | GET | Nej | Veckovisa betyg från R2/DuckDB. Fallback: mock-data |
| `/api/stocks/{ticker}/news` | GET | Nej | Företagsnyheter via Finnhub API |
| `/api/stocks/{ticker}/earnings` | GET | Nej | Kvartalsrapporter via Finnhub API |
| `/api/stocks/{ticker}/insider-trades` | GET | Nej | Insynshandel via Finnhub API |
| `/api/stocks/{ticker}/piotroski` | GET | Nej | Piotroski F-Score detaljer (alla 9 kriterier) |
| `/api/stocks/compare` | POST | Nej | Jämför 2–5 aktier (tickers[], metrics) |

### 5.3 Portfolio

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/portfolio` | GET | JWT | Portfölj med innehav, enriched med aktuella priser |
| `/api/portfolio/holdings` | POST | JWT | Lägg till innehav `{ticker, shares, cost_basis?}` |
| `/api/portfolio/holdings/{id}` | DELETE | JWT | Ta bort innehav |
| `/api/portfolio/snapshot` | POST | JWT | Skapa daglig portfölj-snapshot (upsert user_id+date) |
| `/api/portfolio/history` | GET | JWT | Periodavkastning 1M/3M/6M/12M baserat på snapshots |
| `/api/portfolio/risk` | GET | JWT | Risk: sektorallokering, koncentration, snittbetyg |

### 5.4 Watchlist

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/watchlist` | GET | JWT | Bevakningslista enriched med priser/betyg |
| `/api/watchlist/{ticker}` | POST | JWT | Lägg till bevakning |
| `/api/watchlist/{ticker}` | DELETE | JWT | Ta bort bevakning |

### 5.5 Alerts

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/alerts` | GET | JWT | Aktiva prisriktkurslarm |
| `/api/alerts` | POST | JWT | Skapa larm `{ticker, condition (above/below), target_price, note?}` |
| `/api/alerts/{id}` | DELETE | JWT | Ta bort larm |
| `/api/alerts/check` | GET | Admin | Manuell larmcheck: jämför mot aktuella priser |

### 5.6 AI

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/ai/parse-filter` | POST | Nej | Naturligt språk → filter-JSON. Anropar DeepSeek |
| `/api/ai/committee/{ticker}` | POST | JWT | Analyskommittén: 3 parallella AI-anrop + ordförande-syntes |
| `/api/ai/portfolio-coach` | POST | JWT | AI-portföljrådgivare med konversationshistorik |

### 5.7 Markets

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/markets/sectors` | GET | Nej | Sektoröversikt med genomsnittsbetyg, antal, trender |
| `/api/markets/indices` | GET | Nej | Globala index via Finnhub |

### 5.8 Calendar

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/calendar/earnings` | GET | Nej | Kommande rapporter via Finnhub |
| `/api/calendar/ipo` | GET | Nej | Kommande börsnoteringar via Finnhub |
| `/api/calendar/economic` | GET | Nej | Ekonomisk kalender via Finnhub |

### 5.9 Admin

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/admin/status` | GET | Admin | Pipeline-status, antal tickers, senaste körning |
| `/api/admin/pipeline-runs` | GET | Admin | Pipeline-körningshistorik |
| `/api/admin/users` | GET | Admin | Användarprofiler |
| `/api/admin/score-distribution` | GET | Admin | Score-histogram + per signal |
| `/api/admin/universe` | GET | Admin | Täckning per sektor/segment/land |

### 5.10 Profile

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/profile` | GET | JWT | Hämta profil (e-post, display_name) |
| `/api/profile` | PUT | JWT | Uppdatera display_name |
| `/api/profile/account` | DELETE | JWT | Radera konto (auth user + all data) |

### 5.11 Prediction

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/predictions` | GET | Nej | Lista ML-prediktioner, sorterade på predicted_return |
| `/api/predictions/{ticker}` | GET | Nej | ML-prediktion för en specifik ticker |

### 5.12 Smallcap

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/smallcap` | GET | Nej | Småbolagsresultat, filterbar på score_min, sector |
| `/api/smallcap/sectors` | GET | Nej | Distinkta sektorer i smallcap |

### 5.13 Options

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/options/{ticker}` | GET | Nej | Optionskedja för ticker |

### 5.14 Backtests

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/backtests` | GET | Nej | Lista backtestresultat |
| `/api/backtests/{strategy}` | GET | Nej | Detaljer för specifik strategi |

### 5.15 Sector Rotation

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/sector-rotation` | GET | Nej | Momentum-baserad sektorrotation |

### 5.16 Paper Trading

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/paper/portfolio` | GET | JWT | Pappersportfölj med live-priser |
| `/api/paper/trade` | POST | JWT | Gör affär (buy/sell) |
| `/api/paper/reset` | POST | JWT | Återställ pappersportfölj |

### 5.17 Snapshot History

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/snapshots` | GET | JWT | Användarens portfölj-snapshot-historik |

### 5.18 Saved Screens

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/screens` | GET | JWT | Sparade screener-vyer |
| `/api/screens` | POST | JWT | Spara vy `{name, filter_json}` |
| `/api/screens/{id}` | DELETE | JWT | Ta bort vy |

### 5.19 Health

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/health` | GET | Nej | Hälsokontroll (`{"status":"ok","version":"2.0.0"}`) |

---

## 6. Databas — Supabase Schema

**Projekt-ID:** `eukhlhowbbrccerxpisp`
**Region:** eu-north-1 (Stockholm)
**URL:** `https://eukhlhowbbrccerxpisp.supabase.co`
**Dashboard:** https://supabase.com/dashboard/project/eukhlhowbbrccerxpisp

### 6.1 Tabeller

| Tabell | RLS | Innehåll |
|---|---|---|
| `scan_results` | Publik läsning | Aktuell scan — ~800 aktier med betyg, signaler, nyckeltal |
| `profiles` | Privat (egen rad) | display_name, role (user/admin) |
| `portfolios` | Privat (egen) | name, user_id |
| `holdings` | Privat (via portfolio) | ticker, shares, cost_basis |
| `watchlist` | Privat (egen) | ticker, user_id |
| `price_alerts` | Privat (egen) | ticker, condition (above/below), target_price, note, active |
| `saved_screens` | Privat (egen) | name, filter_json |
| `pipeline_runs` | Publik läsning | logg: run_type, status, tickers_ok/err, duration |
| `portfolio_snapshots` | Privat (egen) | date, total_value, total_cost (UNIQUE user_id+date) |
| `ai_cache` | Service role | cache_key, response_data, created_at (24h TTL) |
| `ml_predictions` | Publik läsning | ML 30-dagars prisprognoser |
| `smallcap_results` | Publik läsning | Småbolagsscanner-resultat |
| `paper_portfolios` | Privat (egen) | Pappershandelsportfölj |
| `paper_trades` | Privat (egen) | Pappershandelstransaktioner |
| `paper_positions` | Privat (egen) | Pappershandelspositioner |
| `backtest_results` | Publik läsning | Backtest-resultat per strategi |
| `sector_rotation` | Publik läsning | Sektormomentumdata |
| `portfolio_optimizations` | Privat (egen) | HRP-optimeringsresultat |
| `universe_candidates` | Publik läsning | Kandidater för universumutökning |
| `options_data` | Publik läsning | Optionskedjedata |

### 6.2 scan_results — nyckelkolumner

| Kolumn | Typ | Beskrivning |
|---|---|---|
| `ticker` | TEXT PK | Unik identifierare (t.ex. VOLV-B.ST, 005930.KS) |
| `name` | TEXT | Bolagsnamn |
| `segment` | TEXT | large_cap / mid_cap / small_cap / micro_cap |
| `sector` | TEXT | T.ex. Technology, Healthcare, Industri |
| `score_total` | NUMERIC(5,2) | Totalbetyg 0-100 |
| `score_value/momentum/quality/growth/risk/size/dividend/sentiment` | NUMERIC(5,2) | Faktorbetyg (8 st) |
| `entry_signal` | TEXT | STARK / OK / VÄNTA / EJ_AKTUELL |
| `confidence_label` | TEXT | Hög / Medel / Låg (ML-prognosens förtroende) |
| `trend_signal` | TEXT | Upptrend / Sidled / Nedtrend |
| `price` | NUMERIC(12,4) | Aktuell kurs |
| `market_cap` | NUMERIC(20,2) | Börsvärde |
| `predicted_return` | NUMERIC(8,4) | ML 30-dagars prognos |
| `pe_trailing`, `pe_forward` | NUMERIC(10,2) | P/E-tal |
| `roe`, `roa` | NUMERIC(5,4) | Lönsamhet |
| `piotroski_f` | INTEGER 0-9 | Finansiell styrka |
| `dividend_yield` | NUMERIC(8,4) | Direktavkastning |
| `beta` | NUMERIC(6,4) | Riskmått |
| `low_liquidity` | BOOLEAN | Låg likviditetsflagga |
| `scan_date` | DATE | Senaste scan-datum |

### 6.3 Viktiga SQL-policies (redan körda)

```sql
-- scan_results: publik läsning
GRANT SELECT ON public.scan_results TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scan_results TO service_role;

-- pipeline_runs: publik läsning
GRANT SELECT ON public.pipeline_runs TO anon, authenticated;

-- Auto-skapa profil + portfolio vid registrering
CREATE OR REPLACE FUNCTION handle_new_user() RETURNS trigger AS $$
BEGIN
  INSERT INTO profiles (id, display_name) VALUES (NEW.id, NEW.email);
  INSERT INTO portfolios (user_id, name) VALUES (NEW.id, 'Min portfölj');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 7. Sidor (Next.js App Router)

### 7.1 Sökvägsskydd

Alla `/(app)/*`-rutter skyddas av `middleware.ts` (Supabase JWT-check → redirect `/login`). Publika routes: `/`, `/login`, `/register`, `/reset`, alla `/api/*`.

### 7.2 Sida för sida — alla 13 sidor

| # | Sida | Route | Fil | Notering |
|---|---|---|---|---|
| 1 | 🏠 Landningssida | `/` | `(marketing)/page.tsx` | Hero, 3 features, CTA, footer. Publik, SEO. |
| 2 | 🔐 Login | `/login` | `(auth)/login/page.tsx` | Supabase signInWithPassword → redirect /oversikt |
| 3 | 📝 Registrering | `/register` | `(auth)/register/page.tsx` | Supabase signUp, visar bekräftelsemeddelande |
| 4 | 🔄 Glömt lösenord | `/reset` | `(auth)/reset/page.tsx` | resetPasswordForEmail → redirect /update-password |
| 5 | 📊 Översikt | `/oversikt` | `OversiktView.tsx` | Dashboard: hälsning (God morgon/eftermiddag/kväll), portföljkort med area-chart + periodknappar (1M/3M/6M/12M), top picks, bevakningslista |
| 6 | 🔍 Aktier | `/screener` | `ScreenerView.tsx` | Full screener: NL-sök, segment-toggle, FilterRail, ResultTable med sortering + sparklines |
| 7 | 📈 Aktiekort | `/aktie/[ticker]` | `StockView.tsx` | 5 flikar: Översikt / Faktorer / Analys / Rapporter / AI. Sticky VerdictHeader. |
| 8 | 💼 Portfölj | `/portfolj` | `PortfoljView.tsx` | Innehavstabell, allokeringsdonut, riskpanel, "Fråga om din portfölj" AI-coach |
| 9 | ⭐ Bevakningar | `/bevakningar` | `BevakninarView.tsx` | Watchlist + prisriktkurslarm (skapa/radera above/below) |
| 10 | 📅 Kalender | `/kalender` | `KalenderView.tsx` | 4 tabbar: Rapporter, Börsnoteringar, Ekonomi, Utdelningar |
| 11 | ↔️ Jämför | `/jamfor` | `JamforView.tsx` | Jämför 2 aktier sida vid sida med multi-select |
| 12 | 🌍 Marknad | `/marknad` | `MarknadView.tsx` | Sektoröversikt + global marknadsdata |
| 13 | 📖 Guide | `/guide` | `GuideView.tsx` | Utbildning: poängsystem, faktorer, Piotroski, signaler |
| 14 | 🛠️ Kontrollpanel | `/kontrollpanel` | `KontrollpanelView.tsx` | 5 admin-sektioner (endast admin-roll) |
| 15 | ⚙️ Inställningar | `/installningar` | `InstallningarView.tsx` | Profil, tema, lösenord, konto (radera) |

### 7.3 Aktiedetaljvy — 5 flikar i detalj

| Flik | Innehåll | Viktigt |
|---|---|---|
| Översikt | PriceChart (Lightweight Charts candlestick + MA50/MA200 + volym), Key Metrics-grid med InfoTooltips (P/E, ROE, ROA, Piotroski, Beta, Volatilitet, Direktavkastning, D/E, Börsvärde) | Prishistorik hämtas från Finnhub API (live) med fallback till mock |
| Faktorer | FactorRadar (Recharts, 8 faktorer) + staplar med InfoTooltip-förklaringar | Progressiv disclosure: "Detaljer"-knapp |
| Analys | ScoreHistoryChart (Recharts area), Piotroski F-Score detaljer (alla 9 kriterier med green/red icons) | Kräver R2 för riktig score-historik |
| Rapporter | Earnings-tabell (kvartal, EPS estimat vs utfall, överraskning), Tillväxtdata, Nyheter med sentiment-badges, Nyckeltal från senaste rapport | News och earnings från Finnhub |
| AI | Analyskommittén: 3 analytiker + ordförande-syntes. Laddas automatiskt (inget dubbelklick). | Varje analyst card: short verdict synligt, detaljer collapsed. Kräver DEEPSEEK_API_KEY. |

---

## 8. Hooks (React Query + klientstate)

| Hook | Anrop | Används i |
|---|---|---|
| `useScreener(filters?)` | `GET /api/scan` | ScreenerView, OversiktView (top picks) |
| `useScanMeta()` | `GET /api/scan/meta` | ScreenerView |
| `useSectors()` | `GET /api/scan/sectors` | FilterRail |
| `useStock(ticker)` | `GET /api/stocks/{ticker}` | StockView |
| `usePriceHistory(ticker)` | `GET /api/stocks/{ticker}/price-history` | StockView (Översikt-fliken) |
| `useScoreHistory(ticker)` | `GET /api/stocks/{ticker}/score-history` | StockView (Analys-fliken) |
| `useStockNews(ticker)` | `GET /api/stocks/{ticker}/news` | StockView (Rapporter-fliken) |
| `useStockEarnings(ticker)` | `GET /api/stocks/{ticker}/earnings` | StockView (Rapporter-fliken) |
| `usePiotroski(ticker)` | `GET /api/stocks/{ticker}/piotroski` | StockView (Analys-fliken) |
| `usePortfolio()` | `GET /api/portfolio` | PortfoljView, VerdictHeader |
| `usePortfolioHistory()` | `GET /api/portfolio/history` | OversiktView |
| `useWatchlist()` | `GET /api/watchlist` | BevakninarView, OversiktView, VerdictHeader |
| `useMarkets()` | `GET /api/markets/sectors` | MarknadView |
| `useTheme()` | localStorage | TopBar, hela appen |

**Caching:** Alla `useQuery`-anrop har `staleTime` specificerat per hook (60s-30min). React Query hanterar dedup och automatisk re-fetch.

---

## 9. AI-analys

### 9.1 Provider

| Provider | Modell | Användning |
|---|---|---|
| DeepSeek | `deepseek-chat` | All AI i API:et |

**Kräver:** `DEEPSEEK_API_KEY` i `.env` (projektroten). Är redan satt. Saknas → alla AI-anrop returnerar "(AI ej konfigurerad)".

### 9.2 Funktioner

| Funktion | max_tokens | Vad den gör |
|---|---|---|
| `parse_nl_filter()` | 500 | Naturligt språk → JSON-filter. Ex: "Hitta undervärderade industribolag" → `{sector: "Industri", entry_signal: "STARK"}` |
| `get_committee_analysis()` | 500×3 + 500 | 3 parallella AI-anrop (teknisk, fundamental, sentiment) + ordförande syntes. Returnerar verdict, confidence, summary, disagreement |
| `portfolio_coach()` | 600 | Konversationsbaserad portföljrådgivning med historik |

### 9.3 Caching

Committee-analys cachas i Supabase-tabellen `ai_cache` per ticker per dag (24h TTL). NL-filter och portfolio-coach cachas inte.

### 9.4 Promptar (i `apps/api/routers/ai.py`)

- `NL_FILTER_SYSTEM` — instruktion för NL→JSON-tolkning
- `ANALYST_PROMPTS["teknisk"]` — teknisk analys (trend, momentum, RSI, MACD, MA50/200)
- `ANALYST_PROMPTS["fundamental"]` — fundamental analys (P/E, ROE, marginaler, skuldsättning)
- `ANALYST_PROMPTS["sentiment"]` — sentiment (sektor, marknadsregim, relativ styrka)
- `ANALYST_PROMPTS["ordforande"]` — syntes med JSON-formatkrav
- `PORTFOLIO_COACH_SYSTEM` — portföljrådgivning

---

## 10. Konfiguration

### 10.1 `.env` (projektrot, läses av FastAPI)

| Variabel | Status | Värde/Anmärkning |
|---|---|---|
| `SUPABASE_URL` | ✅ Klar | `https://eukhlhowbbrccerxpisp.supabase.co` |
| `SUPABASE_ANON_KEY` | ✅ Klar | Publik nyckel (RLS enforced) |
| `SUPABASE_SERVICE_KEY` | ✅ Klar | Admin-nyckel (bypass RLS) |
| `SUPABASE_JWT_SECRET` | ✅ Klar | För lokal JWT-validering (HS256) |
| `DEEPSEEK_API_KEY` | ✅ Klar | AI-analys aktiv |
| `FINNHUB_API_KEY` | ✅ Klar | Nyheter, earnings, prishistorik, insider, kalender |
| `R2_KEY_ID`/`SECRET`/`ENDPOINT` | ❌ Saknas | Cloudflare R2 — betalningsproblem, uppskjutet |
| `ENVIRONMENT` | ✅ `development` | |
| `CORS_ORIGINS` | ✅ Klar | `["http://localhost:3000", "https://marketscan.vercel.app"]` |

### 10.2 `apps/web/.env.local` (läses av Next.js)

| Variabel | Status | Värde |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Klar | `https://eukhlhowbbrccerxpisp.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Klar | anon-nyckeln |
| `NEXT_PUBLIC_API_URL` | ✅ Klar (dev) | `http://localhost:8000` |

### 10.3 Vercel Environment Variables (två projekt)

**Frontend (marketscan):**
- `NEXT_PUBLIC_SUPABASE_URL` — samma som ovan
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — samma som ovan
- `NEXT_PUBLIC_API_URL` = `https://marketscan-api.vercel.app`

**API (marketscan-api):**
Alla från `.env` (rot) → Supabase-nycklar, DEEPSEEK_API_KEY, FINNHUB_API_KEY

---

## 11. Backend Workers (körs ALDRIG i API)

| Worker | Beskrivning | Status |
|---|---|---|
| `db_loader.py` | Bulk-load scan_results via psycopg2 COPY (13s för 1200 rader) | ✅ Byggd |
| `r2_uploader.py` | Ladda upp Parquet-snapshots till Cloudflare R2 | ⬜ Byggd, väntar på R2 |
| `ml_trainer.py` | XGBoost-träning för 30-dagars prisprognos | ✅ Byggd |
| `smallcap_scanner.py` | Småbolagsscanner-pipeline | ✅ Byggd |
| `sector_rotation.py` | Momentum-baserad sektorrotation | ✅ Byggd |
| `hrp_optimizer.py` | Hierarchical Risk Parity-portföljoptimerare | ✅ Byggd |
| `universe_discovery.py` | Hitta nya aktier automatiskt | ✅ Byggd |
| `paper_trading.py` | Pappershandelsmotor med P&L | ✅ Byggd |
| `backtest_runner.py` | Walk-forward backtesting | ✅ Byggd |
| `options_scanner.py` | Optionskedjor och Greeks | ✅ Byggd |
| `price_alert_checker.py` | Kolla alla aktiva larm mot aktuella priser | ✅ Byggd |
| `portfolio_snapshot.py` | Skapa dagliga portfölj-snapshots | ✅ Byggd |
| `pipeline/entrypoint.py` | GitHub Actions entrypoint-brygga | ✅ Byggd |

**Kritik: Alla dessa är BYGGDA men INTE kopplade till aktiv pipeline.** De kräver:
1. GitHub Secrets konfigurerade
2. DATABASE_URL fungerande (pooler-port 6543)
3. R2 konfigurerat (för vissa)

---

## 12. Auth-flöde

1. **Registrering:** Supabase `signUp()` → auto-creates profile + portfolio via DB trigger
2. **Inloggning:** `signInWithPassword()` → Supabase sätter session
3. **Middleware:** Kollar Supabase session (server-side) → redirect `/login` om ogiltig
4. **API-auth:** JWT-bearer token (från Supabase session) → lokal HS256-validering i `core/security.py`. Ingen nätverksroundtrip.
5. **Roller:** `user` (default) eller `admin`. Admin checkas via `require_admin()` dependency.
6. **CORS:** `localhost:3000` (dev) + `marketscan.vercel.app` (prod)

---

## 13. Viktiga arkitekturmönster

### Data flow — prishistorik (viktig!)

1. Försök Finnhub API (med `X-Finnhub-Token` header)
2. Fallback till R2/DuckDB (Parquet-filer i Cloudflare R2)
3. Fallback till deterministisk mock-data (seeded by ticker hash)

### AI-kommitté

1. Anrop POST `/api/ai/committee/{ticker}` med `{ticker, stock_data}`
2. 3 parallella DeepSeek-anrop (teknisk, fundamental, sentiment)
3. Ordförande syntes → JSON `{verdict, confidence, summary, disagreement}`
4. Cachas i Supabase `ai_cache` för 24h per ticker

### Screener

- Heter "Aktier" i UI:n (användarens preferens)
- Endast `scan_results`-tabellen (inga joins)
- Default: large_cap + mid_cap, limit 200, sorted by score_total DESC
- Sökning fungerar på både ticker och name (via `.ilike.%q%`)
- Naturligt språk-sök via AI om `DEEPSEEK_API_KEY` finns

---

## 14. Vercel-deployment (kritisk!)

### Två separata projekt

**VIKTIGT:** Frontend och API är två helt separata Vercel-projekt. De deployas OBEROENDE av varandra.

| Projekt | Domän | GitHub repo | Build |
|---|---|---|---|
| **marketscan** (frontend) | `https://marketscan.vercel.app` | hankkontakt/marketscan | `cd apps/web && npm run build` |
| **marketscan-api** (API) | `https://marketscan-api.vercel.app` | hankkontakt/marketscan | Python serverless (auto-detected) |

**När git push görs:**
- `.vercel/project.json` pekar på `marketscan-api` → API-projektet deployas automatiskt
- Frontend-projektet deployas **INTE automatiskt** — måste göras manuellt från Vercel Dashboard

**För att deploya frontend:**
1. Gå till https://vercel.com/hankkontakt-projects/marketscan
2. Deployments → Deploy → senaste commit från master

### API Base URL

Frontend anropar API via `NEXT_PUBLIC_API_URL`:
- **Dev:** `http://localhost:8000` (i `.env.local`)
- **Prod:** `https://marketscan-api.vercel.app` (i Vercel env vars för frontend-projektet)

Koden i `apps/web/lib/api.ts` använder `NEXT_PUBLIC_API_URL || "http://localhost:8000"`.

---

## 15. Felsökning

### 15.1 Starta lokalt

```bash
# Terminal 1 — API (kör från marketscan-roten)
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python -m uvicorn apps.api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web
npm run dev

# Öppna: http://localhost:3000
```

### 15.2 Vanliga fel

| Symptom | Rotsak | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'apps'` | Python startad från fel mapp | Kör från `marketscan/`-roten |
| API svarar 401 på alla anrop | Supabase JWT secret saknas/är fel | Kontrollera `SUPABASE_JWT_SECRET` i `.env` |
| "AI ej konfigurerad" i UI | `DEEPSEEK_API_KEY` saknas | Finns i .env — kolla att Vercel har den |
| Screener visar inga aktier | `load_data.py` ej kört | Kör `python load_data.py` |
| Portfolio/watchlist 401 | Användaren ej inloggad | Skapa konto på `/register` |
| Prishistorik är konstig | Mock-data (R2 ej konfigurerat) | Normalt — Finnhub används först, sen mock |
| Aktie hittades inte | API_BASE fel (pekade på gammal domän) | Kontrollera NEXT_PUBLIC_API_URL |
| "DEPLOYMENT_NOT_FOUND" | Vercel deployar just nu | Vänta 1-2 minuter |
| TypeScript-fel vid build | npm paket saknas | `cd apps/web && npm ci` |
| slowapi import error | Kräver `pip install slowapi` | API fungerar ändå (optional import) |

### 15.3 Diagnostik

```bash
# API health check
curl https://marketscan-api.vercel.app/api/health

# Sök efter aktie
curl https://marketscan-api.vercel.app/api/stocks?q=tesla&limit=3

# Enskild aktie
curl https://marketscan-api.vercel.app/api/stocks/EXEL

# Kolla antal aktier i databasen
curl -s "https://eukhlhowbbrccerxpisp.supabase.co/rest/v1/scan_results?select=ticker&limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY" | jq length

# Starta API med detaljerad loggning
python -m uvicorn apps.api.main:app --reload --port 8000 --log-level debug
```

---

## 16. Miljövariabler — fullständig lista

| Variabel | Var i kod | Var i Vercel | Status |
|---|---|---|---|
| `SUPABASE_URL` | `core/config.py` | API-projektet | ✅ |
| `SUPABASE_ANON_KEY` | `core/config.py` | Båda projekten | ✅ |
| `SUPABASE_SERVICE_KEY` | `core/config.py` | API-projektet | ✅ |
| `SUPABASE_JWT_SECRET` | `core/config.py` | API-projektet | ✅ |
| `DEEPSEEK_API_KEY` | `core/config.py` | API-projektet | ✅ |
| `FINNHUB_API_KEY` | `core/config.py` | API-projektet | ✅ |
| `R2_KEY_ID`/`SECRET`/`ENDPOINT` | `core/config.py` | Saknas | ❌ |
| `NEXT_PUBLIC_API_URL` | `lib/api.ts` | Frontend-projektet | ✅ (https://marketscan-api.vercel.app) |
| `NEXT_PUBLIC_SUPABASE_URL` | `lib/api.ts` | Frontend-projektet | ✅ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `lib/api.ts` | Frontend-projektet | ✅ |

---

## 17. Kända problem & teknisk skuld (2026-06-07)

| # | Problem | Allvar | Fil | Detalj |
|---|---|---|---|---|
| 1 | **"Aktie hittades inte" när man klickar från vissa vyer** | HÖG | `lib/api.ts` | Om NEXT_PUBLIC_API_URL pekar på fel domän (gammal deployment) returnerar API 404. Lösning: redeploya frontend-projektet i Vercel efter API-ändringar. |
| 2 | **Prishistorik kan vara mock** | MEDIUM | `stocks.py:169-224` | Tre nivåer: Finnhub → R2 → mock. Finnhub fungerar för de flesta tickers. Vissa ticker-format (t.ex. med `.ST`) kan misslyckas och falla till mock. `is_synthetic: true` signaleras nu till frontend. |
| 3 | **AI-analys tar ~10-15s** | MEDIUM | `ai.py:132-191` | Tre parallella DeepSeek-anrop (numera med return_exceptions=True). Inget timeouthantering i frontend — användaren ser skeleton hela tiden. |
| 4 | **R2 ej konfigurerat** | MEDIUM | `duckdb_r2.py` | Cloudflare betalningsproblem. Score-historik och price-historik från Parquet fungerar inte. |
| 5 | **Pipeline kör ej automatiskt** | HÖG | `.github/workflows/` | Workflow-filer finns men GitHub Secrets ej konfigurerade. Data laddas just nu manuellt via `load_data.py`. |
| 6 | **DATABASE_URL pooler-port fungerar ej** | HÖG | `.env` | Port 6543 svarar inte. Blockar pipeline-koppling och backend_worker-crons. |
| 7 | **Admin-panelen** | MEDIUM | `security.py` | DONE ✅ `require_admin` läser nu `profiles.role` (inte JWT-claim). Admin-länk döljs i NavRail för icke-admin. |
| 8 | **React 18.3 (inte 19)** | Permanent | `package.json` | Radix UI kräver React 18. Uppgradera INTE till 19. |
| 9 | **Ingen timeout på AI-anrop i frontend** | LÅG | `AnalysCommittee.tsx` | Om DeepSeek svarar långsamt visas skeleton tills timeout. |
| 10 | **Frontend deployas inte automatiskt** | MEDIUM | `.vercel/project.json` | Endast API-projektet deployas via git push. Frontend måste deployas manuellt. |
| 11 | **IDOR i delete-endpoints** | KRITISK | `portfolio.py, alerts.py, saved_screens.py` | DONE ✅ Alla delete-endpoints kräver nu ägarkoll (user_id + id). |
| 12 | **Supabase-token nådde aldrig Postgres/RLS** | KRITISK | `dependencies.py` | DONE ✅ `get_user_supabase()` skapad — forward:ar JWT till PostgREST. Alla user-routers uppdaterade. |
| 13 | **Paper trading GET/POST använde olika klienter** | HÖG | `paper_trading_router.py` | DONE ✅ Båda använder nu get_supabase_admin (user_id-scoping appliceras i queries). |
| 14 | **Missing await på DuckDB-anrop** | HÖG | `stocks.py:210,232` | DONE ✅ Båda anrop korrekt awaitade nu. Mock-fallback nås korrekt. |
| 15 | **db_loader normaliserade inte confidence/trend** | HÖG | `db_loader.py:46-74` | DONE ✅ confidence_map och trend_map tillagda — matchar CHECK-constraints. |
| 16 | **Rate limiting var en no-op** | MEDIUM | `rate_limiter.py, requirements.txt` | DONE ✅ SlowAPIMiddleware wired, slowapi tillagd i requirements.txt. |
| 17 | **PostgREST filter-injektion via sökterm** | MEDIUM | `screener.py:61, stocks.py:253` | DONE ✅ `safe_search()` i `core/search_utils.py` — sanerar innan interpolation. |

---

## 18. Förbättringsidéer

| # | Idé | Prioritet | Filer |
|---|---|---|---|
| 1 | **Koppla GitHub Actions pipeline** | HÖG | `.github/workflows/pipeline.yml`, GitHub Secrets |
| 2 | **Konfigurera DATABASE_URL pooler** | HÖG | Supabase Dashboard → Database → Connection Pooling |
| 3 | **Sätt upp R2 när Cloudflare-betalning fungerar** | MEDIUM | `r2_uploader.py`, R2 env vars |
| 4 | **Deploya frontend automatiskt via git push** | MEDIUM | Koppla samma repo till frontend-Vercel-projektet |
| 5 | **E-postnotiser vid prislarm** | MEDIUM | `price_alert_checker.py` + e-postintegration |
| 6 | **Pappershandels-P&L i UI** | MEDIUM | `paper_trading_router.py` + frontend |
| 7 | **Backtest-resultat i UI** | MEDIUM | `backtest_runner.py` + frontend |
| 8 | **Sektoröversikt heatmap** | LÅG | Ny widget på översikt eller marknadssidan |
| 9 | **Tema sparas i Supabase per användare** | LÅG | `profiles.theme_preference` |
| 10 | **Mobil-PWA** | LÅG | Manifest finns, service worker saknas |
| 11 | **Admin-panel: kräv admin-roll** | LÅG | `admin.py`: byt till `require_admin` |
| 12 | **Timeout/retry på AI-anrop i frontend** | LÅG | `AnalysCommittee.tsx` |

---

## 19. Ändringslogg

> Nyaste överst. Format: `YYYY-MM-DD — beskrivning (fil)`.

### 2026-06-07 — Fas 6: Funktionell expansion (stor)

**Arkitektur-grund:**
- Ny `lib/features.ts` — feature flag-konstant för att gömma datalösa vyer.
- SQL migrations 012 (profile_extensions), 013 (notifications), 014 (transactions), 015 (insider_trades), 016 (ai_journal).

**6B — Erfarenhetsläge + onboarding:**
- `components/providers/ExperienceProvider.tsx`: Ny React-kontext `useExperience()` + `<ExpertOnly>`-helper.
- `components/onboarding/OnboardingModal.tsx`: 3-stegs onboarding (välkommen → erfarenhetsnivå → klart).
- `app/(app)/layout.tsx`: Wrappar app i ExperienceProvider + OnboardingModal.
- `routers/profile.py`: Utökade fält `experience_level`, `onboarding_completed`, `theme`, `email_opt_in`. **Kritisk bugfix:** använder nu `get_user_supabase()` (ej anon) så RLS fungerar.
- `components/settings/ExperienceSection.tsx`: Växel Nybörjare/Erfaren.
- `components/settings/ProfileSection.tsx`: E-postopt-in toggle.
- `components/settings/ThemeSection.tsx`: Synkar tema till Supabase-profil.

**6C — Notiser (in-app + e-post):**
- `routers/notifications.py`: GET /notifications, /notifications/unread, POST /notifications/{id}/read, /notifications/read-all.
- `components/notifications/NotificationCenter.tsx`: Klock-ikon + panel i TopBar med oläst-räknare.
- `components/layout/TopBar.tsx`: La till NotificationBell + scan_date-badge.
- `backend_worker/email/layout.py`: Ren HTML-mail-wrapper (ingen emoji, Lysa-stil).
- `backend_worker/email/components.py`: Återanvändbara mallar (price_alert, earnings_reminder, score_change, daily_digest).
- `backend_worker/email/sender.py`: Resend-integration med send() och send_notification().
- `backend_worker/price_alert_checker.py`: Uppdaterad — skapar nu in-app-notis + skickar e-post vid larm.
- `hooks/useNotifications.ts`: React Query-hooks för notiser.

**6D — Transaktionslogg + TWR:**
- `routers/transactions.py`: CRUD transaktioner + TWR-beräkning endpoint. RLS-skyddad.
- `routers/stocks.py`: La till OMXS30 benchmark-endpoint.
- `app/(app)/portfolj/PortfoljView.tsx`: TWR-sektion + transaktionslogg-tabell.
- `hooks/usePortfolio.ts`: Nya hooks useTransactions, useAddTransaction, useDeleteTransaction, useTWR.

**3A/3B — Makroregim + Insiderdata:**
- `routers/macro_regime.py`: Marknadsregimdetektion från scan-data (tjur/björn/osäker).
- `routers/insider.py`: Insiderdata från FI-databas + Finnhub-fallback.

**4A/4B — Earnings + AI-journal:**
- `routers/ai.py`: AI-journal sparas vid varje kommittékörning. GET /ai/journal/{ticker} endpoint.

**6F — Dagens marknad + UX:**
- `routers/markets.py`: GET /markets/top-movers — dagens vinnare/förlorare + betygsvinnare.
- `app/(app)/oversikt/OversiktView.tsx`: "Dagens marknad"-widget + betygsvinnare.
- `components/command/CommandPalette.tsx`: La till åtgärder (växla tema, logga ut, inställningar).
- `TopBar.tsx`: "Senast uppdaterad"-badge från scan_date.

**6E — PWA:**
- La till @serwist/next + @serwist/sw som dependencies.
- `next.config.ts`: Serwist-konfiguration (SW avstängd i dev).
- `app/sw.ts`: Service worker med network-first för finansiella endpoints.
- `app/offline/page.tsx`: Ren offline-sida.
- `public/manifest.json`: Uppdaterad med korrekta färger.

**Säkerhetsfixar (från code review):**
- `profile.py`: Använder nu `get_user_supabase()` (med JWT) istället för `get_supabase()` (anon) — alla profil-operationer fungerar nu med RLS.
- `OnboardingModal.tsx`: useState → useEffect för att visa modalen efter profilladdning.
- `PortfoljView.tsx`: La till `useDeleteTransaction` i import.
- `markets.py`: Top-movers använder nu PostgREST LIMIT istället för full tabellscan. `get_global_indices` har nu 5-minuters in-memory cache för att minska Finnhub-förbrukning.
- `OversiktView.tsx`: Division-by-zero-skydd för portföljvärde.
- `macro_regime.py`: Använder aggregate COUNT-frågor istället för att hämta alla rader.
- `insider.py`: role-fältet från Finnhub (`position`) mappas nu korrekt i insider-trades.
- `transactions.py`: TWR-beräkning använder nu date-normaliserad transaction grouping. Snapshots begränsade till 100 för prestanda.
- `stocks.py`: `_generate_mock_candles` använder stabil byte-sum-seed (inte Pythons randomiserade `hash()`).
- `stocks.py`: `/compare` returnerar nu validerade (stora) ticker-namn istället för rå input.
- `backend_worker/price_alert_checker.py`: Använder nu `from backend_worker.email.sender import send_notification` (robust import) istället för `sys.path`-manipulation.
- `backend_worker/email/components.py`: All användardata HTML-escaped (`_escape_html`) för att förhindra self-XSS i e-post. `daily_digest_email` parameterdokumentation förtydligad (`old_score` vs `new_score`).
- `ai.py`: La till `import logging` + `logger` — saknades sedan Fas 6 och orsakade 500 på AI-slutpunkten.

**Fas 7 — Universum-expansion + Jämför-sida:**
- `supabase/migrations/017_user_tickers.sql`: Ny tabell `user_ticker_requests` för användarskapade ticker-önskemål. RLS-skyddad.
- `routers/stocks.py`: Ny `GET /stocks/search`-endpoint som först söker i `scan_results`, faller tillbaka till Finnhub för aktier utanför universum. Returnerar `in_universe: bool` så frontend kan visa rätt meddelande.
- `routers/portfolio.py`: `POST /holdings` skapar nu automatiskt `user_ticker_request` om tickern inte finns i `scan_results`.
- `routers/watchlist.py`: `POST /watchlist/{ticker}` skapar nu automatiskt `user_ticker_request` om tickern inte finns i `scan_results`.
- `schemas/portfolio.py`: La till `name`-fält i `HoldingIn` för att kunna bifoga namn från Finnhub.
- `routers/ai.py`: Ny `POST /ai/compare`-endpoint — AI jämför 2-5 aktier och rekommenderar den mest attraktiva. Cachas per dag.
- `routers/ai.py`: Fixad `_call_ai`-signatur att acceptera `max_tokens` som kwarg.
- `routers/stocks.py`: Bytte etikett "Dir.avk" → "Utdelning" i jämför-endpointen.
- `lib/format.ts`: La till `signalShortLabel()`, `signalBadgeClass()` för snyggare badge-visning av signaler. `signalLabel()` fixad för "EJ_AKTUELL".
- `components/command/CommandPalette.tsx`: Sökning använder nu `/api/stocks/search` (med universum-status). Visar "Ny"-badge för aktier utanför universum.
- `hooks/useCompare.ts`: Ny hook-fil — `useCompare()`, `useStockSearch()`, `useAICompare()`, `useStockDetail()`.
- `app/(app)/jamfor/JamforView.tsx`: Helt ny jämför-sida:
  - Faktorradar-grid per aktie (visuell profiljämförelse)
  - Grupperade metrikkort (Betyg, Fundamentala nyckeltal, Signal) — kollapsbara
  - Prisutvecklingsgraf (normaliserad till bas=0%)
  - AI-jämförelsekort med rekommendation, styrkor/svagheter
  - Stöd för icke-universum-aktier i sökningen

**Fas 1 — Säkerhet (P0):**
- `dependencies.py`: Lade till `get_user_supabase()` som forwardar JWT till PostgREST → `auth.uid()` fungerar i RLS-policies.
- `core/security.py`: `require_admin` läser nu `profiles.role` via service-klient (inte JWT-claim). Tog bort tom `AdminUser`-subklass.
- `portfolio.py, alerts.py, saved_screens.py, watchlist.py, snapshots.py`: Alla user-routers använder nu `get_user_supabase`. Delete-endpoints får ägar-villkor (`eq("user_id", user.id)` eller portfolio-id-koll).
- `core/search_utils.py`: Ny fil med `safe_search()` — sanerar söktermer innan PostgREST ilike-interpolation.
- `screener.py, stocks.py`: Sökning saniteras via `safe_search()`.

**Fas 2 — Trasiga flöden (P1):**
- `stocks.py`: Lade till `await` på `query_price_history(t)` och `query_score_history(t)` — 500-fel fixat.
- `db_loader.py`: `_prepare_df` normaliserar nu `confidence_label` (HÖG→Hög etc.) och `trend_signal` (UPPTREND→Upptrend, VARNING→None).
- `rate_limiter.py`: Lade till `SlowAPIMiddleware` — rate limiting faktiskt aktiv nu.
- `apps/api/requirements.txt`: Lade till `slowapi>=0.1.9`.
- `stocks.py`: `/piotroski` selectar nu bara befintliga kolumner — 400/500-fel undvikt.
- `stocks.py`: `EarningsItem` fick `quarter`/`year`/`surprise_pct` fält; Finnhub-mappning explicit.
- `paper_trading_router.py`: GET använder nu `get_supabase_admin` (samma som POST) — köp visas korrekt.

**Fas 3 — Kvalitet (P2):**
- `ai.py`: `asyncio.gather` med `return_exceptions=True` — enskild analytiker-timeout kraschar inte kommittén. Admin-klient för cache-skrivning (P2-5).
- `markets.py`: Globala index hämtas parallellt via asyncio.gather + gemensam httpx-klient.
- `globals.css`: `--font-mono` → `var(--font-sans)` — inga siffror faller till systemets monospace. Stale kommentarer uppdaterade.
- `JamforView.tsx`: `<>` → `<React.Fragment key={metric.label}>`, `--color-bg` → `--color-bg-surface`.
- `MarknadView.tsx, useMarkets.tsx`: Lokala `scoreColorClass`/`scoreColor`-dubbletter borttagna. Importerar från `lib/format`.
- `stocks.py`: Döda variabler `current_signal` och `one_year_ago` borttagna.

**Fas 4 — Städning (P3):**
- `middleware.ts`: Handunderhållen ruttlista → prefix-baserad logik (`!isPublic`).
- `apps/api/requirements.txt`: `slowapi>=0.1.9` tillagd.
- `core/search_utils.py`: Ny delad utility för sök-sanitering.

**Fas 5 — UX (U-):**
- `ResultTable.tsx`: InfoTooltip på kolumnrubriker (Totalbetyg, Köpläge, Trend, Börsvärde, P/E, ROE). Importerar InfoTooltip.
- `FilterRail.tsx`: SCREENER_PRESETS chips (Värde, Tillväxt, Hög kvalitet, Momentum, Översåld) ovanför filter.
- `StockView.tsx`: "AI summary" → "Sammanfattning"-kommentar (P2-9 hederlig namngivning). is_synthetic-etikett vid prisgrafen.
- `useStock.ts`: `is_synthetic` i returtypen för `usePriceHistory` och `useScoreHistory`.

### 2026-06-07 — Fullständig SYSTEM_AI.md-omskrivning
Komplett uppdaterad systemdokumentation för MarketScan 2.0. Inkluderar alla nya routes (calendar, prediction, options, backtests, sector_rotation, paper_trading), Vercel-deployment med två projekt, GitHub Actions workflows, migrations 004-011, backend_worker-filer, kända buggar med "Aktie hittades inte"-felet och API_BASE-konfiguration.
`SYSTEM_AI.md`

### 2026-06-07 — Finnhub prishistorik + AI loading fix
- Price-history: försök Finnhub först → R2 → mock
- AnalysCommittee: loading skeleton återställd (tappades när launched-state togs bort)
- API_BASE: återställd till NEXT_PUBLIC_API_URL (två separata Vercel-projekt)
- Tillförlitlighet: dölj "Låg" (visas bara för Hög/Medel med förklaring)
`apps/api/routers/stocks.py:169-224`, `apps/web/components/stock/AnalysCommittee.tsx:37-48`, `apps/web/lib/api.ts:8-13`, `apps/web/components/stock/VerdictHeader.tsx:207-210`

### 2026-06-07 — Ticker/name swap + AI text formatting
- Ticker och namn bytte plats över alla vyer: **namn stort, ticker litet** (förut var det tvärtom)
- Fixade VerdictHeader och PortfoljView som missades i första omgången
- AnalystCard: short verdict (första **fetstilta** texten) alltid synlig, detaljerad analysis collapsed med "Visa detaljerad analys"-knapp
`apps/web/components/stock/VerdictHeader.tsx:82-87`, `apps/web/components/stock/AnalysCommittee.tsx:141-176`, `apps/web/app/(app)/portfolj/PortfoljView.tsx:201-202`

### 2026-06-07 — Analyskommittén: inget dubbelklick
- Tog bort "launched"-staten (enabled: launched) — analys startar direkt när AI-fliken öppnas
- Tog bort yttre "Visa analys"-knappen i StockView AITab
`apps/web/components/stock/AnalysCommittee.tsx`, `apps/web/app/(app)/aktie/[ticker]/StockView.tsx:609-641`

### 2026-06-07 — Finnhub API-nyckel + security hardening
- Finnhub token flyttad från URL query string till header (X-Finnhub-Token)
- Slowapi rate limiting med optional import (fallback graceful när ej installerad)
- Security headers middleware (CSP, HSTS, X-Frame-Options)
- Admin endpoints: alla 5 kräver nu `require_admin` (var `get_current_user`)
- `.gitignore` skyddar nu nästlade `.env.*`-filer
- `response_model` på alla endpoints (Pydantic-schemas)
- Deduplicerade prompts i ai.py (210 rader duplicate borttagna)
`apps/api/routers/stocks.py`, `apps/api/core/rate_limiter.py`, `apps/api/core/security_headers.py`, `apps/api/routers/admin.py`, `apps/api/routers/ai.py`

### 2026-06-06 — Fas 8+: Backend Workers (9 tunga features)
- Skapat alla backend_worker-filer: ml_trainer, smallcap_scanner, sector_rotation, hrp_optimizer, universe_discovery, paper_trading, backtest_runner, options_scanner
- 8 SQL-migrationer (004-011) för motsvarande tabeller
- 6 GitHub Actions workflow-filer
- 7 API-routers: calendar, prediction, options, backtests, sector_rotation, paper_trading, smallcap
`backend_worker/`, `supabase/migrations/004-011`, `.github/workflows/`, `apps/api/routers/`

### 2026-06-05 — MarketScan 2.0 initial
Komplett plattform byggd och deployad: Next.js-frontend, FastAPI-API, Supabase-databas, alla kärnvyer, designsystem.
