# MarketScan 2.0 — SYSTEM_AI.md
> Komplett teknisk referens för AI-agenter. Uppdateras vid varje kodändring.

---

## 0. Underhållsprotokoll

**Obligatoriskt för alla AI-modeller:**

| Händelse | Skriv i |
|---|---|
| Genomförd kodändring | Relevant sektion + en rad i §18 Ändringslogg |
| Bugg eller risk | §16 Kända problem |
| Förbättringsidé | §17 |
| Fixat något från §16 | Markera `DONE ✅`, radera inte |

Format ändringslogg: `YYYY-MM-DD — beskrivning (fil:rad)`. Nyaste överst.

---

## 1. Snabbreferens

### 1.1 Vanligaste uppgifter

| Uppgift | Var |
|---|---|
| Starta API lokalt | `cd marketscan && python -m uvicorn apps.api.main:app --reload --port 8000` |
| Starta frontend lokalt | `cd apps/web && npm run dev` |
| Ladda data från pipeline | `cd marketscan && python load_data.py` |
| Lägg till ny API-route | `apps/api/routers/` + registrera i `main.py` |
| Lägg till ny sida | `apps/web/app/(app)/ny-sida/page.tsx` |
| Ändra designsystem | `apps/web/app/globals.css` (CSS-variabler) |
| Ändra färger/tema | `globals.css` → `:root` (ljust) + `[data-theme="dark"]` (mörkt) |
| Lägg till ny komponent | `apps/web/components/` (välj rätt undermapp) |
| Ändra API-anrop i frontend | `apps/web/lib/api.ts` (fetch-wrapper) + `hooks/` (React Query) |
| Kör SQL-migration | Supabase Dashboard → SQL Editor → klistra in |
| Se databas-schema | `supabase/migrations/001_initial_schema.sql` |

### 1.2 Kritiska gotchas

- **backend_worker/ får ALDRIG importeras av apps/api/** — Vercel 500MB-gräns. pandas, xgboost, yfinance är förbjudna i API.
- **`.env` ligger i projektroten** — läses av FastAPI. **`apps/web/.env.local`** läses av Next.js.
- **DATABASE_URL måste vara Session Pooler** (port 6543), INTE Direct (port 5432). GitHub Actions kräver IPv4.
- **React 18.3 — uppgradera INTE till 19.** Radix UI kräver 18.
- **Supabase service key** används bara i backend_worker/ och load_data.py. Exponeras ALDRIG i frontend.
- **Inga emojis i UI** — alltid Lucide-linjeikoner.
- **Inga globala variabler i FastAPI** — Vercel spinnar upp/ner instanser (stateless).
- **InfoTooltip (`i`-bubbla)** används ÖVERALLT bredvid finansiella värden.
- **Mock-data genereras deterministiskt** — baserat på ticker (hash), så samma aktie får samma chart. R2 krävs för riktig data.

---

## 2. Systemöversikt

**Vad:** Modern webbapp för aktieanalys och screening. Next.js-frontend + FastAPI-backend + Supabase-databas. Ersätter gamla Streamlit-prototypen (`stock-scanner-fix`).

**Stack:**
| Lager | Teknik | Version |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Next.js 15.5, React 18.3 |
| Styling | Tailwind CSS v4 | |
| Komponent-primitiver | Radix UI (Dialog, Select, Tooltip, Tabs, Dropdown, Switch) | |
| Charts | Recharts (area, pie, donut, radar) + Lightweight Charts (candlestick) | |
| Ikoner | Lucide React — INGA emojis | |
| Typsnitt | Inter (allt, inklusive siffror) med `tabular-nums` | next/font/google |
| State/datahämtning | TanStack React Query v5 | |
| Auth-klient | @supabase/ssr + supabase-js | |
| Command palette | cmdk | |
| Toast-notiser | Sonner | |
| Backend | FastAPI + Python 3.12 | |
| Auth-validering | PyJWT HS256 (lokal, inga nätverksanrop) | |
| Databas (het) | Supabase Postgres (eu-north-1, Stockholm) | |
| Kall lagring | Cloudflare R2 + DuckDB — EJ KONFIGURERAT ÄN | |
| Pipeline | GitHub Actions — EJ KOPPLAT ÄN | |

### 2.1 Designbeslut

| Beslut | Varför |
|---|---|
| Next.js App Router + SSR | SEO för landningssida, snabb navigering, middleware för auth-gate |
| FastAPI serverless (Vercel) | Gratis hosting, autoskalning, ingen serverhantering |
| Supabase för all användardata | Inbyggd auth, RLS, Postgres — mindre kod än egen backend |
| TanStack Query för datahämtning | Automatisk cachning, dedup, re-fetch, optimistiska updates |
| CSS-variabler för teman | Ljust/mörkt/auto-tema utan runtime CSS-in-JS overhead |
| Inter för all typografi | Exakt som Lysa — enhetligt, professionellt, tabular-nums för siffror |
| Progressiv disclosure | Enkel vy först, djupdyk på begäran — InfoTooltips förklarar allt |
| Mock-data som fallback | R2 är ej konfigurerat — deterministisk mock så UI alltid fungerar |
| backend_worker/ isolerat | pandas/xgboost/yfinance får ej finnas i API (Vercel 500MB-gräns) |

---

## 3. Katalogstruktur

```
marketscan/
├── apps/
│   ├── web/                              # Next.js frontend (localhost:3000)
│   │   ├── app/
│   │   │   ├── (marketing)/page.tsx     # Landningssida (publik, SEO)
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx       # Inloggning
│   │   │   │   ├── register/page.tsx    # Registrering
│   │   │   │   └── reset/page.tsx       # Glömt lösenord
│   │   │   ├── (app)/                   # Skyddade sidor (kräver inloggning)
│   │   │   │   ├── layout.tsx           # App-shell: NavRail + TopBar + CommandPalette
│   │   │   │   ├── oversikt/            # Dashboard (Lysa-stil)
│   │   │   │   ├── screener/            # Aktie-screener ("Aktier" i UI)
│   │   │   │   ├── aktie/[ticker]/      # Aktiekort med detaljer (5 flikar)
│   │   │   │   ├── portfolj/            # Min portfölj
│   │   │   │   ├── bevakningar/         # Bevakningar + prisriktkurslarm
│   │   │   │   ├── kontrollpanel/       # Admin-vy
│   │   │   │   └── installningar/       # Användarinställningar
│   │   │   ├── layout.tsx               # Root: Inter-font, tema, Toaster, QueryProvider
│   │   │   └── globals.css              # ALLA CSS-variabler och design tokens
│   │   ├── components/
│   │   │   ├── ui/InfoTooltip.tsx       # "i"-bubbla med Radix Tooltip
│   │   │   ├── charts/
│   │   │   │   ├── PriceChart.tsx       # Lightweight Charts (candlestick)
│   │   │   │   ├── FactorRadar.tsx      # Recharts radar (8 faktorer)
│   │   │   │   └── ScoreSparkline.tsx   # SVG sparkline för betygstrend
│   │   │   ├── screener/
│   │   │   │   ├── FilterRail.tsx       # Expanderbara filter
│   │   │   │   ├── ResultTable.tsx      # Sorterbar tabell + tangentbordsnavigering
│   │   │   │   └── SegmentToggle.tsx    # Chip-väljare för segment
│   │   │   ├── stock/
│   │   │   │   ├── VerdictHeader.tsx    # Sticky aktie-header
│   │   │   │   └── AnalysCommittee.tsx  # 3 AI-analytiker + ordförande
│   │   │   ├── layout/
│   │   │   │   ├── NavRail.tsx          # Ikonnavigation vänster
│   │   │   │   └── TopBar.tsx           # Sök + tema + profilmeny
│   │   │   ├── command/
│   │   │   │   └── CommandPalette.tsx   # Ctrl+K sökning
│   │   │   └── providers/
│   │   │       └── QueryProvider.tsx    # TanStack Query setup
│   │   ├── hooks/
│   │   │   ├── useScreener.ts           # React Query: scan_results
│   │   │   ├── useStock.ts              # React Query: enskild aktie, historik
│   │   │   ├── usePortfolio.ts          # React Query: portfolio, watchlist, history
│   │   │   ├── useTheme.ts              # Ljust/mörkt/auto med localStorage
│   │   │   └── useCommandPalette.ts     # Event-bus för Ctrl+K open/close
│   │   ├── lib/
│   │   │   ├── api.ts                   # Typad fetch-wrapper
│   │   │   ├── format.ts               # formatPrice, signalLabel, scoreColorClass m.fl.
│   │   │   ├── utils.ts                # cn() (clsx + tailwind-merge)
│   │   │   ├── supabase/client.ts      # Browser Supabase-klient
│   │   │   └── supabase/server.ts      # SSR Supabase-klient
│   │   ├── types/scan.ts               # TypeScript-typer
│   │   ├── middleware.ts               # Auth-gate (redirect /login)
│   │   ├── next.config.ts              # devIndicators: false
│   │   └── package.json                # React 18.3 (INTE 19)
│   └── api/                             # FastAPI (localhost:8000)
│       ├── main.py                      # App + CORS + router-registrering
│       ├── dependencies.py              # get_supabase(), get_supabase_admin()
│       ├── core/
│       │   ├── config.py                # Pydantic Settings (läser .env)
│       │   ├── security.py              # JWT-validering
│       │   ├── deepseek_client.py       # DeepSeek API-anrop
│       │   └── duckdb_r2.py             # R2-frågor via DuckDB (ej konfigurerat)
│       ├── routers/
│       │   ├── screener.py              # GET /scan, /scan/meta, /scan/sectors
│       │   ├── stocks.py                # GET /stocks/{ticker}, price-history, score-history
│       │   ├── portfolio.py             # CRUD: portfölj, holdings, watchlist, alerts, screens, snapshots
│       │   ├── ai.py                    # POST /ai/parse-filter, committee, portfolio-coach
│       │   ├── admin.py                 # GET /admin/status, universe, score-distribution
│       │   └── profile.py               # PUT /api/profile
│       ├── schemas/
│       │   ├── scan.py                  # ScanRow, ScanFilters
│       │   └── portfolio.py            # HoldingIn/Out, PortfolioOut, SnapshotIn/Out m.fl.
│       └── requirements.txt            # ALDRIG pandas/xgboost — Vercel 500MB-gräns
├── backend_worker/                      # Tung Python — körs ALDRIG av API
│   ├── db_loader.py                     # copy_expert() bulk-load till Postgres
│   ├── r2_uploader.py                   # Parquet → R2 (ej konfigurerat)
│   ├── pipeline/entrypoint.py           # GitHub Actions brygga
│   ├── price_alert_checker.py           # Cron: kolla larm mot priser
│   └── portfolio_snapshot.py            # Cron: dagliga portfölj-snapshots
├── supabase/
│   ├── migrations/001_initial_schema.sql  # Alla tabeller, index, RLS-policies
│   ├── migrations/002_portfolio_snapshots.sql  # Portfolio snapshots-tabell
│   └── seed.sql                         # 8 test-aktier
├── .github/workflows/
│   └── pipeline.yml                     # CI/CD för pipeline
├── load_data.py                          # Engångsskript: importera parquet → Supabase
├── .env                                  # API-nycklar (läses av FastAPI från roten)
├── HANDOFF.md                            # Komplett handoff-dokument
├── SETUP.md                              # Uppstartsguide
├── STATUS.md                             # Projektstatus
└── SYSTEM_AI.md                          # Detta dokument
```

---

## 4. Designsystem

### 4.1 Färger (CSS-variabler i `globals.css`)

**Ljust tema (`:root`, standard — Lysa/Avanza-inspirerat):**
```css
--color-bg-base:      #F8F9FB    /* sida-bakgrund */
--color-bg-surface:   #FFFFFF    /* kort, paneler */
--color-bg-elevated:  #F1F3F7    /* hover, popover */
--color-border:       #E3E6EC
--color-border-strong:#C8CDD8
--color-text-primary:   #14181F
--color-text-secondary: #4A5567
--color-text-muted:     #8B929F
--color-accent:         #1D4ED8  /* institutionell blå — sparsamt */
--color-accent-soft:    rgba(29,78,216,0.08)
--color-accent-hover:   #1A44C2
--color-up:             #15803D  /* traditionell grön */
--color-up-soft:        rgba(21,128,61,0.08)
--color-down:           #DC2626  /* tydlig röd */
--color-down-soft:      rgba(220,38,38,0.08)
--color-warn:           #B45309
--color-warn-soft:      rgba(180,83,9,0.08)
--color-score-high:     #15803D  /* betyg 70+ */
--color-score-mid:      #1D4ED8  /* betyg 50–69 */
--color-score-low:      #8B929F  /* betyg <50 */
```

**Mörkt tema (`[data-theme="dark"]`):**
```css
--color-bg-base:      #0A0B0D
--color-bg-surface:   #131519
--color-bg-elevated:  #1B1E24
--color-border:       #23272E
--color-border-strong:#2E3340
--color-text-primary:   #EDEEF1
--color-text-secondary: #9CA3AF
--color-text-muted:     #6B7280
--color-accent:         #5B8DEF
--color-up:             #3FB68B
--color-down:           #E0645C
--color-warn:           #D9A441
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
- **Inter** för allt (text OCH siffror) — exakt som Lysa
- `tabular-nums` via `.tabular` CSS-klass för priser och procent (kolumner alignar)
- Laddat via `next/font/google` i `app/layout.tsx`

### 4.4 Komponentstil
- `InfoTooltip` — Radix Tooltip med "i"-ikon, används ÖVERALLT bredvid finansiella värden
- Avrundade hörn: `rounded-xl` (12px) för kort, `rounded-2xl` (16px) för stora paneler
- Inga emojis — ALLTID Lucide-linjeikoner
- CSS-klasser: `.score-chip-high/mid/low`, `.signal-stark/ok/vanta/ej`, `.skeleton` (loading)

---

## 5. API — Complete Route Map

Alla routes prefixas med `/api/`. FastAPI körs på `http://localhost:8000`.

### 5.1 Screener

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/scan` | GET | Nej (valfri) | Hot path, Postgres only. Filter: segments, score_min/max, sector, country, entry_signal, trend_signal, piotroski_min, pe_max, roe_min, dividend_yield_min, exclude_low_liquidity, search. Default large_cap+mid_cap, limit 200. |
| `/api/scan/sectors` | GET | Nej | Distinkta sektorer för filter-dropdown |
| `/api/scan/meta` | GET | Nej | Metadata: scan_date, total, by_segment |

### 5.2 Stocks

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/stocks/{ticker}` | GET | Nej | Enskild aktie från scan_results |
| `/api/stocks/{ticker}/price-history` | GET | Nej | OHLCV från R2/DuckDB. Fallback: deterministisk mock-data |
| `/api/stocks/{ticker}/score-history` | GET | Nej | Veckovisa betyg från R2/DuckDB. Fallback: deterministisk mock-data |
| `/api/stocks` | GET | Nej | Snabbsök ticker/name (⌘K-paletten) |

### 5.3 Portfolio

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/portfolio` | GET | JWT | Portfölj med innehav, enriched med aktuella priser |
| `/api/portfolio/holdings` | POST | JWT | Lägg till innehav `{ticker, shares, cost_basis?}` |
| `/api/portfolio/holdings/{id}` | DELETE | JWT | Ta bort innehav |
| `/api/portfolio/snapshot` | POST | JWT | Skapa daglig portfölj-snapshot (upsert user_id+date) |
| `/api/portfolio/history` | GET | JWT | Periodavkastning 1M/3M/6M/12M baserat på snapshots |

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

### 5.6 Saved Screens

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/screens` | GET | JWT | Sparade screener-vyer |
| `/api/screens` | POST | JWT | Spara vy `{name, filter_json}` |
| `/api/screens/{id}` | DELETE | JWT | Ta bort vy |

### 5.7 AI

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/ai/parse-filter` | POST | Nej | Naturligt språk → filter-JSON. Anropar DeepSeek |
| `/api/ai/committee/{ticker}` | POST | JWT | Analyskommittén: 3 parallella AI-anrop + ordförande-syntes |
| `/api/ai/portfolio-coach` | POST | JWT | AI-portföljrådgivare med konversationshistorik |

### 5.8 Admin

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/admin/status` | GET | JWT (alla) | Systemstatus: scan_rows, last_runs |
| `/api/admin/pipeline-runs` | GET | JWT (alla) | Pipeline-körningshistorik |
| `/api/admin/users` | GET | JWT (alla) | Användarprofiler |
| `/api/admin/score-distribution` | GET | JWT (alla) | Score-histogram + per signal |
| `/api/admin/universe` | GET | JWT (alla) | Täckning per sektor/segment/land |

### 5.9 Profile

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/profile` | PUT | JWT | Uppdatera display_name |
| `/api/profile` | GET | JWT | Hämta profil (e-post, display_name) |

### 5.10 Health

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/api/health` | GET | Nej | Hälsokontroll |

---

## 6. Databas — Supabase Schema

**Projekt:** `eukhlhowbbrccerxpisp` (eu-north-1, Stockholm)
**URL:** `https://eukhlhowbbrccerxpisp.supabase.co`

### 6.1 Tabeller

| Tabell | RLS | Innehåll |
|---|---|---|
| `scan_results` | Publik läsning | Aktuell scan — alla aktier med betyg, signaler, nyckeltal |
| `profiles` | Privat (egen rad) | display_name, role (user/admin) |
| `portfolios` | Privat (egen) | name, user_id |
| `holdings` | Privat (via portfolio) | ticker, shares, cost_basis |
| `watchlist` | Privat (egen) | ticker, user_id |
| `price_alerts` | Privat (egen) | ticker, condition (above/below), target_price, note, active |
| `saved_screens` | Privat (egen) | name, filter_json |
| `pipeline_runs` | Publik läsning | logg: run_type, status, tickers_ok/err, duration |
| `portfolio_snapshots` | Privat (egen) | date, total_value, total_cost (UNIQUE user_id+date) |

### 6.2 scan_results — nyckelkolumner

| Kolumn | Typ | Beskrivning |
|---|---|---|
| `ticker` | TEXT PK | Unik identifierare (t.ex. VOLV-B.ST) |
| `name` | TEXT | Bolagsnamn |
| `segment` | TEXT | large_cap / mid_cap / small_cap / micro_cap |
| `score_total` | NUMERIC(5,2) | Totalbetyg 0-100 |
| `score_value/momentum/quality/growth/risk/size/dividend/sentiment` | NUMERIC(5,2) | Faktorbetyg |
| `entry_signal` | TEXT | STARK / OK / VÄNTA / EJ_AKTUELL |
| `trend_signal` | TEXT | Upptrend / Sidled / Nedtrend |
| `price` | NUMERIC(12,4) | Aktuell kurs |
| `market_cap` | NUMERIC(20,2) | Börsvärde |

### 6.3 Viktiga SQL-policies

```sql
-- scan_results: publik läsning
GRANT SELECT ON public.scan_results TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scan_results TO service_role;

-- pipeline_runs: publik läsning
GRANT SELECT ON public.pipeline_runs TO anon, authenticated;

-- Auto-skapa profil + portfolio vid registrering (trigger on auth.users)
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

### 7.2 Sida för sida

| # | Sida | Route | Fil | Notering |
|---|---|---|---|---|
| 1 | 🏠 Landningssida | `/` | `(marketing)/page.tsx` | Hero, 3 features, CTA, footer. Publik, SEO. |
| 2 | 🔐 Login | `/login` | `(auth)/login/page.tsx` | Supabase signInWithPassword → redirect /oversikt |
| 3 | 📝 Registrering | `/register` | `(auth)/register/page.tsx` | Supabase signUp, visar bekräftelsemeddelande |
| 4 | 🔄 Glömt lösenord | `/reset` | `(auth)/reset/page.tsx` | resetPasswordForEmail |
| 5 | 📊 Översikt | `/oversikt` | `OversiktView.tsx` | Dashboard: hälsning (God morgon/eftermiddag), portföljkort med area-chart + periodknappar (1M/3M/6M/12M), starka köplägen (top 3), bevakningslista. Använder `usePortfolioHistory()` för riktig perioddata. |
| 6 | 🔍 Aktier | `/screener` | `ScreenerView.tsx` | Full screener: NL-sök, segment-toggle, FilterRail, ResultTable med tangentbordsnavigering + sparklines. Spara/ladda vyer. |
| 7 | 📈 Aktiekort | `/aktie/[ticker]` | `StockView.tsx` | 5 flikar: Översikt (pricechart + key metrics), Faktorer (radar + bars), Analys, Rapporter, AI (Analyskommittén). Sticky VerdictHeader. |
| 8 | 💼 Portfölj | `/portfolj` | `PortfoljView.tsx` | Innehavstabell, lägg till/ta bort, allokeringsdonut, riskpanel, "Fråga om din portfölj" AI-coach. |
| 9 | ⭐ Bevakningar | `/bevakningar` | `BevakninarView.tsx` | Watchlist med betyg/kurs, snabblägg till, ta bort. Prisriktkurslarm: skapa/radera (above/below + target_price + note). |
| 10 | 🛠️ Kontrollpanel | `/kontrollpanel` | `KontrollpanelView.tsx` | 5 sektioner: Status (KPI:er + pipeline-runs-tabell), Pipeline (körningshistorik), Universum (per segment/sektor/land), Mått (score-distribution histogram + per signal), Inställningar. Tillgänglig för alla inloggade. |
| 11 | ⚙️ Inställningar | `/installningar` | `InstallningarView.tsx` | 4 sektioner: Profil (visningsnamn), Tema (ljust/mörkt/auto), Lösenord (3 fält → updateUser), Konto (radera — UI only). |

### 7.3 Aktiedetaljvy — 5 flikar

| Flik | Innehåll |
|---|---|
| Översikt | PriceChart (Lightweight Charts, candlestick + MA50/MA200 + volym), Key Metrics-grid med InfoTooltips (P/E, ROE, ROA, Piotroski, Beta, Volatilitet, Direktavkastning, D/E) |
| Faktorer | FactorRadar (Recharts, 8 faktorer) + staplar med InfoTooltip-förklaringar. Betygstrend-linjegraf (Recharts area) |
| Analys | Tillväxtdata + nyckeltal från senaste rapport |
| Rapporter | Kvartalsdata (kräver pipeline-integration) |
| AI | Analyskommittén: 3 analytiker (teknisk, fundamental, sentiment) + ordförande-syntes. Kräver DEEPSEEK_API_KEY. |

---

## 8. Hooks (React Query + klientstate)

| Hook | Anrop | Syfte |
|---|---|---|
| `useScreener(filters?)` | `GET /api/scan` | Scan-data med filter. Returnerar ScanRow[]. staleTime 60s. |
| `useScanMeta()` | `GET /api/scan/meta` | Scan-date, total, by_segment |
| `useSectors()` | `GET /api/scan/sectors` | Available sectors |
| `useStock(ticker)` | `GET /api/stocks/{ticker}` | Single stock detail |
| `usePriceHistory(ticker)` | `GET /api/stocks/{ticker}/price-history` | OHLCV candles |
| `useScoreHistory(ticker)` | `GET /api/stocks/{ticker}/score-history` | Weekly scores |
| `usePortfolio()` | `GET /api/portfolio` | Portfolio with holdings |
| `useAddHolding()` | `POST /api/portfolio/holdings` | Mutation med invalidate |
| `useRemoveHolding()` | `DELETE /api/portfolio/holdings/{id}` | Mutation med invalidate |
| `useWatchlist()` | `GET /api/watchlist` | Watchlist items |
| `usePortfolioHistory(periods?)` | `GET /api/portfolio/history` | Period returns (1M/3M/6M/12M) |
| `useTheme()` | localStorage | `{ theme, resolved, setTheme, toggle }`. Sparas i "ms-theme". |
| `useCommandPalette()` | Event bus | `{ open, setOpen }` — öppnar/stänger ⌘K |

**Caching:** Alla `useQuery`-anrop har `staleTime: 60s` (default), retry: 1 gång.

---

## 9. AI-analys

### 9.1 Provider

| Provider | Modell | Användning |
|---|---|---|
| DeepSeek | deepseek-chat | All AI i API:et (parse-filter, committee, portfolio-coach) |

**Kräver:** `DEEPSEEK_API_KEY` i `.env` (projektroten). Saknas → alla AI-anrop returnerar "(AI ej konfigurerad)".

### 9.2 Funktioner

| Funktion | max_tokens | Syfte |
|---|---|---|
| `parse_nl_filter()` | 500 | Naturligt språk → filter-JSON. "Hitta undervärderade industribolag med starkt momentum" → `{sector: "Industri", entry_signal: "STARK", ...}` |
| `get_committee_analysis()` | 500 per analytiker + 500 ordförande | 3 parallella AI-anrop (teknisk, fundamental, sentiment) + ordförande syntes. Returnerar verdict + confidence + summary + disagreement-note. |
| `portfolio_coach()` | 600 | Konversationsbaserad portföljrådgivning med historik |

### 9.3 Caching

Committee-analys cachas per ticker per dag (in-memory för sessionen). NL-filter och portfolio-coach cachas inte.

### 9.4 Promptar (i `apps/api/routers/ai.py`)

- `NL_FILTER_SYSTEM` — instruktion för NL→JSON-tolkning
- `ANALYST_PROMPTS["teknisk"]` — teknisk analys (trend, momentum, RSI, MACD)
- `ANALYST_PROMPTS["fundamental"]` — fundamental analys (P/E, ROE, marginaler, skuldsättning)
- `ANALYST_PROMPTS["sentiment"]` — sentiment (sektor, marknadsregim, relativ styrka)
- `ANALYST_PROMPTS["ordforande"]` — syntes med JSON-formatkrav
- `PORTFOLIO_COACH_SYSTEM` — portföljrådgivning

---

## 10. Konfiguration

### 10.1 `.env` (projektrot, läses av FastAPI)

| Variabel | Status | Beskrivning |
|---|---|---|
| `SUPABASE_URL` | ✅ Klar | `https://eukhlhowbbrccerxpisp.supabase.co` |
| `SUPABASE_ANON_KEY` | ✅ Klar | Publik nyckel (RLS enforced) |
| `SUPABASE_SERVICE_KEY` | ✅ Klar | Admin-nyckel (bypass RLS) |
| `SUPABASE_JWT_SECRET` | ✅ Klar | För lokal JWT-validering |
| `DATABASE_URL` | ❌ Poolern ej provisionerad | Postgres — pooler-port (6543) svarar ej. Se §16. |
| `DEEPSEEK_API_KEY` | ✅ Klar | AI-analys |
| `GEMINI_API_KEY` | ✅ Klar | Fallback för AI |
| `FINNHUB_API_KEY` | ✅ Klar | Earnings data |
| `EMAIL_SENDER/PASSWORD/TO` | ✅ Klar | E-postutskick |
| `R2_KEY_ID/SECRET/ENDPOINT` | ❌ Saknas | Cloudflare R2 (prishistorik) |
| `R2_KEY_ID/SECRET/ENDPOINT` | ❌ Saknas | Cloudflare R2 (prishistorik) |
| `ENVIRONMENT` | ✅ `development` | "development" → docs tillgängliga |
| `CORS_ORIGINS` | ✅ `["http://localhost:3000"]` | |

### 10.2 `apps/web/.env.local` (läses av Next.js)

| Variabel | Status |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Klar |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Klar |
| `NEXT_PUBLIC_API_URL` | ✅ Klar (`http://localhost:8000`) |

---

## 11. Backend Workers (körs ALDRIG i API)

| Worker | Beskrivning | När |
|---|---|---|
| `db_loader.py:load_scan()` | Bulk-load scan_results via psycopg2 COPY (13s för 1200 rader) | Efter pipeline-körning |
| `db_loader.py:log_pipeline_run()` | Logga pipeline-körning till pipeline_runs-tabellen | Efter pipeline-körning |
| `r2_uploader.py` | Ladda upp Parquet-snapshots till Cloudflare R2 | När R2 är konfigurerat |
| `pipeline/entrypoint.py` | GitHub Actions entrypoint — brygga mellan old core/ och new storage | CI/CD |
| `price_alert_checker.py` | Kolla alla aktiva larm mot aktuella priser, markera triggade | Var 30:e min (vardagar) |
| `portfolio_snapshot.py` | Skapa dagliga portfölj-snapshots för alla användare | Dagligen |

---

## 12. Auth-flöde

1. **Registrering:** Supabase `signUp()` → auto-creates profile + portfolio via DB trigger
2. **Inloggning:** `signInWithPassword()` → Supabase sätter session-cookie
3. **Middleware:** Kollar Supabase session → redirect `/login` om ogiltig
4. **API-auth:** JWT-bearer token → lokal HS256-validering (ingen nätverksroundtrip)
5. **Roller:** `user` (default) eller `admin`. Admin checkas via `require_admin()` dependency.
6. **CORS:** Endast `localhost:3000` (dev) och `marketscan.vercel.app` (prod)

---

## 13. Backend_worker-beroenden (tung Python)

```txt
pandas>=2.2
numpy>=1.26
yfinance>=0.2.40
xgboost>=2.0
scikit-learn>=1.5
psycopg2-binary>=2.9
boto3>=1.35
python-dotenv>=1.0
```

**ALDRIG i `apps/api/requirements.txt`.** API:t har bara lätta beroenden: fastapi, uvicorn, pydantic, supabase, PyJWT, httpx, duckdb.

---

## 14. Miljövariabler — vad som behövs

| Variabel | Var | Status | Var hittar du den |
|---|---|---|---|
| `SUPABASE_URL` | `.env` (rot) | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | `.env` (rot) + `.env.local` | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_SERVICE_KEY` | `.env` (rot) | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_JWT_SECRET` | `.env` (rot) | ✅ Klar | Supabase → Settings → API → JWT Settings |
| `DATABASE_URL` | `.env` (rot) | ❌ Poolern ej provisionerad | Supabase Database Settings. Port 6543 svarar ej — poolern måste aktiveras. |
| `DEEPSEEK_API_KEY` | `.env` (rot) | ✅ Klar | platform.deepseek.com (lokal) |
| `GEMINI_API_KEY` | `.env` (rot) | ✅ Klar | console.gemini.google.com |
| `FINNHUB_API_KEY` | `.env` (rot) | ✅ Klar | finnhub.io |
| `EMAIL_SENDER/PASSWORD/TO` | `.env` (rot) | ✅ Klar | Gmail-lösenord
| `R2_KEY_ID/SECRET/ENDPOINT` | `.env` (rot) | ❌ Saknas | Cloudflare R2 Dashboard |
| `NEXT_PUBLIC_API_URL` | `apps/web/.env.local` | ✅ Klar | `http://localhost:8000` |

**GitHub Actions secrets som behövs:**
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `FINNHUB_API_KEY`, `R2_KEY_ID`, `R2_SECRET`, `R2_ENDPOINT`, `ANTHROPIC_API_KEY` (om Claude används i pipeline)

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
| "AI ej konfigurerad" i UI | `DEEPSEEK_API_KEY` saknas i `.env` | Lägg till nyckeln |
| Screener visar inga aktier | `load_data.py` ej kört | Kör `python load_data.py` |
| Portfolio/watchlist 401 | Användaren ej inloggad | Skapa konto på `/register` |
| Prishistorik är konstig | Mock-data (R2 ej konfigurerat) | Normalt beteende — R2 krävs för riktig data |
| `permission denied for table X` | RLS/Grants ej konfigurerade | Kör `GRANT SELECT ON X TO anon/authenticated/service_role` |
| `st: "useQuery" is not a function` | React Query version mismatch | Kolla `@tanstack/react-query` i package.json |

### 15.3 Diagnostik

```bash
# API health check
curl http://localhost:8000/api/health

# Kolla antal aktier i databasen
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY']); print(sb.table('scan_results').select('ticker', count='exact').execute().count)"

# Starta API med detaljerad loggning
python -m uvicorn apps.api.main:app --reload --port 8000 --log-level debug
```

---

## 16. Kända problem & teknisk skuld

| Problem | Allvarlighet | Fil | Notering |
|---|---|---|---|
| Prishistorik är mock-data | MEDIUM | `apps/api/routers/stocks.py` | R2 ej konfigurerat — deterministisk mock baserad på ticker-hash |
| Betygstrend är mock-data | MEDIUM | `apps/api/routers/stocks.py` | Samma orsak |
| AI-analys kräver API-nyckel | HÖG | `apps/api/core/deepseek_client.py` | `DEEPSEEK_API_KEY` saknas i `.env` |
| Portfölj-% är riktig men kräver snapshots | LÅG | `backend_worker/portfolio_snapshot.py` | Cron-jobbet måste köras för att bygga historik |
| Pipeline kör ej automatiskt | HÖG | `.github/workflows/pipeline.yml` | Måste konfigurera GitHub Secrets + DATABASE_URL |
| Prislarm skickar ej notis | MEDIUM | `backend_worker/price_alert_checker.py` | Cron-jobbet är byggt men ej aktivt i GitHub Actions |
| `DATABASE_URL` saknas i `.env` | HÖG | `.env` | Blockar pipeline-koppling + backend_worker-crons |
| React 18.3 (inte 19) | Permanent | `package.json` | Radix UI kräver React 18. Uppgradera INTE till 19 |
| API cache för AI-kommittén är in-memory | LÅG | `apps/api/routers/ai.py` | `_get_cache` returnerar alltid None — borde använda Supabase eller Redis |

---

## 17. Förbättringsidéer

| Idé | Prioritet | Filer |
|---|---|---|
| Lägg till `DEEPSEEK_API_KEY` i `.env` | HÖG | `.env` |
| Koppla pipeline: fyll i DATABASE_URL + sätt GitHub Secrets | HÖG | `.env`, `.github/workflows/pipeline.yml` |
| Cloudflare R2 — prishistorik och betygstrender | MEDIUM | `backend_worker/r2_uploader.py`, `.env` |
| Vercel-driftsättning (både web + api) | MEDIUM | `vercel.json`, Vercel Dashboard |
| Prislarm-cron: GitHub Actions workflow | MEDIUM | `backend_worker/price_alert_checker.py` |
| Portfölj-snapshot-cron: GitHub Actions workflow | MEDIUM | `backend_worker/portfolio_snapshot.py` |
| Kvartalsdata (Rapporter-fliken) | MEDIUM | Pipeline + ny tabell i Supabase |
| Sektoröversikt (heatmap) | LÅG | Ny sida eller widget på översikt |
| Ljust/mörkt sparas i Supabase per användare | LÅG | `profiles.theme_preference` |
| Push-notiser för prislarm | LÅG | `backend_worker/price_alert_checker.py` + e-post |
| Mobil-PWA | LÅG | Manifest, service worker |

---

## 18. Ändringslogg

> Nyaste överst. Format: `YYYY-MM-DD — beskrivning (fil)`.

### 2026-06-05 — Initial SYSTEM_AI.md för MarketScan 2.0
Skapad från inventering av hela codebase: alla sidor, komponenter, hooks, API-routes, databas-scheman, designsystem, backend-workers och konfiguration.
`SYSTEM_AI.md`

### 2026-06-05 — Settings-sida + profil-API
Ny `/installningar` med 4 sektioner (profil, tema, lösenord, konto). `PUT /api/profile`. NavRail-uppdatering. Auto-tema-stöd i useTheme.
`apps/web/app/(app)/installningar/`, `apps/api/routers/profile.py`, `apps/web/components/layout/NavRail.tsx`, `apps/web/hooks/useTheme.ts`

### 2026-06-05 — AI-provider bytt från Claude till DeepSeek
`_call_ai()` och `_call_ai_chat()` anropar nu `call_deepseek()`/`call_deepseek_chat()`. All Anthropic-kod borttagen.
`apps/api/core/deepseek_client.py`, `apps/api/routers/ai.py`, `apps/api/core/config.py`

### 2026-06-05 — Prisriktkurslarm backend
`price_alert_checker.py` för cron-körning. `GET /api/alerts/check` för manuell trigger. Kollar larm mot aktuella priser, markerar triggade.
`backend_worker/price_alert_checker.py`, `apps/api/routers/portfolio.py`

### 2026-06-05 — Portföljhistorik (snapshots + API + frontend)
SQL-migration för portfolio_snapshots. POST snapshot + GET history endpoints. Cron-job för dagliga snapshots. Översiktsidan visar riktig perioddata.
`supabase/migrations/002_portfolio_snapshots.sql`, `apps/api/routers/portfolio.py`, `apps/web/app/(app)/oversikt/OversiktView.tsx`, `backend_worker/portfolio_snapshot.py`
