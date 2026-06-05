# MarketScan 2.0 — Komplett handoff-dokument

> **Syfte:** Fullständig projektöversikt för en AI-assistent som tar vid där föregående slutade.
> Uppdaterad: 2026-06-05. Täcker allt: arkitektur, designbeslut, bugghistorik, vad som är gjort och vad som återstår.

---

## 1. Projektbeskrivning

MarketScan är en **personlig aktieanalys- och screeningplattform** byggd för hobbyinvesterare (primärt familjebruk, kan skalas till fler).

Systemet hämtar data från börsen varje dag via yfinance, betygsätter ~800 aktier (0–100) baserat på 8 faktorer, och presenterar det i ett rent webbgränssnitt. Användaren kan screena aktier, bevaka favoriter, hantera en portfölj och få AI-analys per aktie.

**Design-filosofi (användarens egna ord):**
- "Lysa-lugn" som bas — enkelt, rent, inga distraktioner
- "Avanza-handlingsbar" som touch — tydliga knappar, direkt action
- Progressiv disclosure: enkel vy först, djupdyk på begäran
- Inga AI-färger (inga lila/neon-blå gradienter, ingen "AI-hemsida-känsla")
- Lysa-stil tooltip-bubblor (`i`-ikoner) på alla värden som förklarar vad de betyder
- Nybörjarvänligt — folk som köper aktier som hobby ska förstå allt
- Framtidsidé (ej implementerad): onboarding-frågor à la Lysa (erfarenhetsnivå, riskaptit) som personaliserar hur mycket data som visas

**Gammal kodbas:** `C:\Users\hthur\OneDrive\Desktop\stock-scanner-fix` (Streamlit-prototyp, används INTE längre för UI — men pipeline-koden återanvänds)

**Ny kodbas:** `C:\Users\hthur\OneDrive\Desktop\marketscan` (detta projekt)

---

## 2. Teknisk stack (exakt)

| Lager | Val | Version |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Next.js 15.5, React 18.3 |
| Styling | Tailwind CSS v4 | |
| Komponent-primitiver | Radix UI (Dialog, Select, Tooltip etc.) | |
| Charts | Recharts (area, pie, donut) + Lightweight Charts (candlestick) | |
| Ikoner | Lucide React — INGA emojis | |
| Typsnitt | Inter (allt, inklusive siffror) med `tabular-nums` | Laddat via next/font/google |
| State/datahämtning | TanStack React Query v5 | |
| Auth-klient | @supabase/ssr + supabase-js | |
| Command palette | cmdk | |
| Toast-notiser | Sonner | |
| Backend | FastAPI + Python 3.12 | |
| Auth-validering | PyJWT HS256 (lokal, inga nätverksanrop) | |
| Databas (het) | Supabase Postgres (eu-north-1, Stockholm) | |
| Kall lagring | Cloudflare R2 + DuckDB — EJ KONFIGURERAT ÄN | |
| Pipeline | GitHub Actions — EJ KOPPLAT ÄN | |

---

## 3. Monorepo-struktur

```
marketscan/
├── apps/
│   ├── web/                              # Next.js frontend (körs på localhost:3000)
│   │   ├── app/
│   │   │   ├── (marketing)/page.tsx     # Landningssida (publik)
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx       # Inloggning
│   │   │   │   ├── register/page.tsx    # Registrering
│   │   │   │   └── reset/page.tsx       # Glömt lösenord
│   │   │   ├── (app)/                   # Skyddade sidor (kräver inloggning via middleware)
│   │   │   │   ├── layout.tsx           # App-shell: NavRail + TopBar + CommandPalette
│   │   │   │   ├── oversikt/            # Startsida (Lysa-stil)
│   │   │   │   ├── screener/            # Aktie-screener (heter "Aktier" i UI)
│   │   │   │   ├── aktie/[ticker]/      # Aktiekort med detaljer
│   │   │   │   ├── portfolj/            # Min portfölj
│   │   │   │   ├── bevakningar/         # Bevakningar + prisriktkurslarm
│   │   │   │   └── kontrollpanel/       # Admin-vy
│   │   │   ├── layout.tsx               # Root: Inter-font, tema=light, Toaster, QueryProvider
│   │   │   └── globals.css              # Alla CSS-variabler och design tokens
│   │   ├── components/
│   │   │   ├── ui/InfoTooltip.tsx       # i-bubbla med Radix Tooltip — används ÖVERALLT
│   │   │   ├── charts/
│   │   │   │   ├── PriceChart.tsx       # Lightweight Charts, candlestick + MA50/200 + volym
│   │   │   │   ├── FactorRadar.tsx      # Radar-chart för 8 faktorer (Recharts)
│   │   │   │   └── ScoreSparkline.tsx   # SVG sparkline för betygshistorik
│   │   │   ├── screener/
│   │   │   │   ├── FilterRail.tsx       # Filter: köpläge, trend, sektor, betyg, P/E, ROE, utdelning
│   │   │   │   ├── ResultTable.tsx      # Sorterbara resultat med tangentbordsnavigering
│   │   │   │   └── SegmentToggle.tsx    # Chip-väljare för large/mid/small/micro_cap
│   │   │   ├── stock/
│   │   │   │   ├── VerdictHeader.tsx    # Sticky aktie-header med kurs, betyg, Bevaka, Lägg i portfölj
│   │   │   │   └── AnalysCommittee.tsx  # 3 AI-analytiker + ordförande-syntes
│   │   │   ├── layout/
│   │   │   │   ├── NavRail.tsx          # Ikonnavigation vänster med hover-labels
│   │   │   │   └── TopBar.tsx           # Sökruta + tema-toggle + profilmeny med logout
│   │   │   └── command/
│   │   │       └── CommandPalette.tsx   # Ctrl+K sökning — aktier + snabblänkar
│   │   ├── hooks/
│   │   │   ├── useScreener.ts           # React Query: hämtar scan_results
│   │   │   ├── usePortfolio.ts          # React Query: portfölj, holdings, watchlist
│   │   │   ├── useStock.ts              # React Query: enskild aktie, prishistorik, score-historik
│   │   │   ├── useTheme.ts              # Ljust/mörkt tema med localStorage
│   │   │   └── useCommandPalette.ts     # Global open/close-state för Ctrl+K
│   │   ├── lib/
│   │   │   ├── supabase/client.ts       # Supabase browser-klient
│   │   │   ├── supabase/server.ts       # Supabase server-klient (SSR)
│   │   │   ├── api.ts                   # Typad fetch-wrapper mot FastAPI
│   │   │   ├── format.ts                # formatPrice, formatPctChange, signalLabel etc.
│   │   │   └── utils.ts                 # cn() (className-merge)
│   │   ├── types/scan.ts                # TypeScript-typer för ScanRow (speglar Supabase-schema)
│   │   ├── middleware.ts                # Auth-gate: redirectar ologgade till /login
│   │   ├── next.config.ts               # devIndicators: false (tar bort N-ikon)
│   │   ├── package.json                 # React 18.3 (INTE 19 — Radix kräver 18)
│   │   └── .env.local                   # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_API_URL
│   └── api/                             # FastAPI (körs på localhost:8000)
│       ├── main.py                      # App + CORS + router-registrering
│       ├── dependencies.py              # get_supabase() — Supabase Python-klient
│       ├── core/
│       │   ├── config.py                # Pydantic Settings (läser rot-.env)
│       │   ├── security.py              # JWT-validering: get_current_user, get_optional_user
│       │   └── duckdb_r2.py             # R2-frågor via DuckDB (ej konfigurerat ännu)
│       ├── routers/
│       │   ├── screener.py              # GET /scan, /scan/meta, /scan/sectors
│       │   ├── stocks.py                # GET /stocks/{ticker}, /price-history, /score-history
│       │   │                            # OBS: genererar mock-data när R2 saknas
│       │   ├── portfolio.py             # CRUD: portfölj, holdings, watchlist, alerts, screens
│       │   ├── ai.py                    # /ai/committee, /ai/parse-filter, /ai/portfolio-coach
│       │   └── admin.py                 # /admin/status, /admin/universe, /admin/score-distribution
│       ├── schemas/                     # Pydantic-schemas
│       └── requirements.txt             # ALDRIG pandas/xgboost här — Vercel 500MB-gräns
├── backend_worker/                       # Tung Python — körs ALDRIG av API
│   ├── db_loader.py                     # copy_expert() bulk-load till Postgres
│   └── r2_uploader.py                   # Parquet → R2 (ej implementerat fullt)
├── supabase/
│   ├── migrations/001_initial_schema.sql # Alla tabeller, index, RLS-policies
│   └── seed.sql                         # 8 test-aktier (nu ersatta av riktiga data)
├── load_data.py                          # Engångsskript: importerar parquet → Supabase
├── .env                                  # API-nycklar (läses av FastAPI från roten)
├── STATUS.md                             # Kortare statusdokument
└── HANDOFF.md                            # Detta dokument
```

---

## 4. Miljövariabler

### `C:\Users\hthur\OneDrive\Desktop\marketscan\.env` (läses av FastAPI)

```env
SUPABASE_URL=https://eukhlhowbbrccerxpisp.supabase.co       ✅ klar
SUPABASE_ANON_KEY=eyJ...                                      ✅ klar
SUPABASE_SERVICE_KEY=eyJ...                                   ✅ klar
SUPABASE_JWT_SECRET=...                                       ✅ klar
DATABASE_URL=postgresql://postgres.xxx:pw@aws-xxx:6543/...    ✅ klar (Session Pooler, IPv4)
DEEPSEEK_API_KEY=sk-d7861ea...                                ✅ Klar — AI-analys aktiv
R2_KEY_ID=                                                    ❌ SAKNAS — Cloudflare betalningsproblem
R2_SECRET=                                                    ❌ SAKNAS
R2_ENDPOINT=                                                  ❌ SAKNAS
R2_BUCKET=marketscan-data
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
```

### `C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web\.env.local` (läses av Next.js)

```env
NEXT_PUBLIC_SUPABASE_URL=https://eukhlhowbbrccerxpisp.supabase.co   ✅ klar
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...                                  ✅ klar
NEXT_PUBLIC_API_URL=http://localhost:8000                              ✅ klar
```

---

## 5. Starta lokalt

```bash
# Terminal 1 — API (kör från marketscan-roten)
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python -m uvicorn apps.api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web
npm run dev

# Öppna: http://localhost:3000
```

---

## 6. Databas — Supabase-schema

```sql
-- Publik läsning (pipeline skriver via service key)
scan_results (
  ticker TEXT PRIMARY KEY,
  name TEXT, segment TEXT, sector TEXT, country TEXT,
  score_total NUMERIC, score_value NUMERIC, score_quality NUMERIC,
  score_momentum NUMERIC, score_growth NUMERIC, score_risk NUMERIC,
  score_size NUMERIC, score_dividend NUMERIC, score_sentiment NUMERIC,
  entry_signal TEXT,      -- STARK | OK | VÄNTA | EJ_AKTUELL
  confidence_label TEXT,  -- Hög | Medel | Låg
  trend_signal TEXT,      -- Upptrend | Sidled | Nedtrend
  predicted_return NUMERIC, ml_rank INT, piotroski_f INT,
  price NUMERIC, change_pct NUMERIC, market_cap NUMERIC,
  pe_trailing NUMERIC, pe_forward NUMERIC, roe NUMERIC, roa NUMERIC,
  gross_margin NUMERIC, operating_margin NUMERIC,
  revenue_growth NUMERIC, earnings_growth NUMERIC,
  dividend_yield NUMERIC, debt_to_equity NUMERIC, beta NUMERIC,
  low_liquidity BOOLEAN, scan_date DATE
)

-- RLS: user_id = auth.uid()
profiles (id UUID PK → auth.users, display_name TEXT, created_at)
portfolios (id, user_id, name, created_at)
holdings (id, portfolio_id, ticker, shares, cost_basis, added_at)
watchlist (id, user_id, ticker, added_at)
price_alerts (id, user_id, ticker, condition TEXT, target_price NUMERIC, note TEXT, active BOOL)
saved_screens (id, user_id, name TEXT, filter_json JSONB, created_at)
pipeline_runs (id, run_type, status, tickers_ok, tickers_err, duration_s, error_msg, started_at)
```

**Viktig SQL som körts:**
```sql
GRANT SELECT ON public.scan_results TO anon;
GRANT SELECT ON public.scan_results TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scan_results TO service_role;
CREATE POLICY "scan_results_public_read" ON scan_results FOR SELECT USING (true);
GRANT SELECT ON public.pipeline_runs TO anon;
GRANT SELECT ON public.pipeline_runs TO authenticated;
```

---

## 7. Gamla repot — pipeline

**Sökväg:** `C:\Users\hthur\OneDrive\Desktop\stock-scanner-fix`

Pipeline-data finns i `reports/`:
- `scored_universe_YYYY-MM-DD.parquet` — stora + medelstora bolag (~760 rader)
- `smallcap_scored_YYYY-MM-DD.parquet` — småbolag

Senaste filer (2026-06-04 / 2026-06-02). Totalt ~820 aktier.

**För att ladda data till Supabase:**
```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python load_data.py
```

Scriptet hittar automatiskt senaste parquet-filer, mappar kolumner, deriverar `segment` från `market_cap`, och gör upsert via Supabase Python-klient i batchar om 200.

**Körkommando för gamla pipelinen:**
```bash
cd C:\Users\hthur\OneDrive\Desktop\stock-scanner-fix
python -c "from core.daily_pipeline import run_pipeline; run_pipeline('morning')"
```

---

## 8. Designsystem

### Färger (CSS-variabler i globals.css)

**Ljust tema (standard):**
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
--color-up:             #15803D  /* traditionell grön */
--color-down:           #DC2626  /* tydlig röd */
--color-warn:           #B45309  /* amber */
--color-score-high:     #15803D  /* betyg 70+ */
--color-score-mid:      #1D4ED8  /* betyg 50–69 */
--color-score-low:      #8B929F  /* betyg <50 */
```

**Mörkt tema (data-theme="dark"):**
```css
--color-bg-base: #0A0B0D, --color-accent: #5B8DEF, --color-up: #3FB68B, etc.
```

### Typsnitt
- **Inter** för allt (text OCH siffror) — exakt som Lysa
- `tabular-nums` via CSS-klass `.tabular` för priser och procent (kolumner alignar)
- Laddat via `next/font/google` i `app/layout.tsx`

### Komponenter
- `InfoTooltip` — liten `i`-knapp med Radix Tooltip, används ÖVERALLT bredvid värden
- `ScoreSparkline` — SVG polyline, 1px, färgas av riktning (upp=grön, ner=röd)
- Inga emojis — ALLTID Lucide-linjeikoner
- Avrundade hörn: `rounded-xl` (16px) för kort, `rounded-2xl` (24px) för stora paneler

---

## 9. API-endpoints

**Bas-URL lokalt:** `http://localhost:8000`

```
GET  /api/scan?segments=&score_min=&entry_signal=&trend_signal=&sector=&limit=
GET  /api/scan/meta
GET  /api/scan/sectors
GET  /api/stocks?q=&limit=           # sökning för Ctrl+K
GET  /api/stocks/{ticker}
GET  /api/stocks/{ticker}/price-history    # mock-data om R2 saknas
GET  /api/stocks/{ticker}/score-history    # mock-data om R2 saknas
GET  /api/portfolio                   # kräver JWT
POST /api/portfolio/holdings          # { ticker, shares, cost_basis? }
DEL  /api/portfolio/holdings/{id}
GET  /api/watchlist                   # kräver JWT
POST /api/watchlist/{ticker}
DEL  /api/watchlist/{ticker}
GET  /api/alerts                      # kräver JWT
POST /api/alerts                      # { ticker, condition, target_price, note? }
DEL  /api/alerts/{id}
GET  /api/screens                     # kräver JWT
POST /api/screens                     # { name, filter_json }
DEL  /api/screens/{id}
POST /api/ai/committee/{ticker}       # kräver DEEPSEEK_API_KEY i .env
POST /api/ai/parse-filter             # NL → filter-params
POST /api/ai/portfolio-coach          # kräver DEEPSEEK_API_KEY + JWT
GET  /api/admin/status                # kräver JWT
GET  /api/admin/universe
GET  /api/admin/score-distribution
GET  /api/admin/pipeline-runs
GET  /api/admin/users
```

---

## 10. Vad som är KLART ✅

### Infrastruktur
- [x] Monorepo-struktur, alla mappar och filer
- [x] Supabase projekt, alla tabeller + index + RLS
- [x] Auth-middleware (Next.js) skyddar `/app`-rutter
- [x] FastAPI med alla routers
- [x] Lokal JWT-validering (PyJWT, ingen nätverksroundtrip)
- [x] CORS konfigurerat
- [x] `load_data.py` — importerar 820 aktier från gamla parquet-filer

### Design
- [x] Ljust tema som standard (Lysa/Avanza-inspirerat, inga AI-färger)
- [x] Mörkt tema tillgängligt via knapp i topbar
- [x] Inter-font för allt (inklusive siffror), tabular-nums
- [x] CSS-variabler för alla färger — enkelt att ändra tema
- [x] App-shell: NavRail (vänster, hover-labels) + TopBar (sökruta + profil-dropdown)
- [x] NavRail visar hover-labels vid musen
- [x] Profilmeny: visar e-post, länk till inställningar, logout-knapp
- [x] Ctrl+K / ⌘K command palette med aktiesökning + snabblänkar
- [x] InfoTooltip (`i`-bubbla) på ALLA finansiella värden genomgående

### Startsida (Översikt)
- [x] Lysa-stil portföljchart med Recharts area-graf
- [x] Periodknappar 1M/3M/6M/12M med avkastning (exempeldata tills riktig data finns)
- [x] 3 starka köplägen — klickbara kort med ticker, namn, betyg, kurs
- [x] Bevakningslista med länk till aktiekort
- [x] God morgon/eftermiddag/kväll-hälsning

### Aktier (Screener)
- [x] Sammanslagen motor för alla segment i en vy
- [x] Segment-toggle (large/mid/small/micro) med preset-snabbvyer
- [x] FilterRail: köpläge, trend, sektor, betyg-min, Piotroski-min, P/E-max, ROE-min, utdelning-min, exkl. låg likviditet
- [x] Fritextsökning med AI-tolkning av naturligt språk (kräver DEEPSEEK_API_KEY)
- [x] Resultattabell med sortering på betyg/kurs/förändring/börsvärde/P/E/ROE
- [x] Tangentbordsnavigering (piltangenter + Enter)
- [x] Sparklines i tabellen
- [x] Spara/ladda anpassade vyer (kräver inloggning)

### Aktiekort
- [x] Sticky header (VerdictHeader + tabbar som EN enhet)
- [x] Header: kurs, daglig förändring, köpläge-badge, totalbetyg, trend, AI-prognos
- [x] "Bevaka"-knapp kopplar till API (lägger till/tar bort från watchlist)
- [x] "Lägg i portfölj" — inline-formulär med antal + inköpskurs → API
- [x] 5 flikar: Översikt / Faktorer / Analys / Rapporter / AI
- [x] Prishistorik-chart (Lightweight Charts, candlestick + MA50/200 + volym, tema-medveten)
- [x] Nyckeltal med InfoTooltip på varje värde (P/E, ROE, ROA, Piotroski, etc.)
- [x] Faktorbetyg-radar + staplar med InfoTooltip-förklaringar
- [x] Betygstrend-linjegraf (Recharts area, mock-data om R2 saknas)
- [x] Rapporter-fliken: tillväxt + nyckeltal från senaste rapporten
- [x] Analyskommittén (AI-fliken): 3 analytiker + ordförande, konfidensmätare, oenighets-flagga
- [x] Mock prishistorik och score-historik genereras deterministiskt baserat på ticker

### Min portfölj
- [x] Lägg till innehav-formulär direkt på sidan (ticker + antal + inköpskurs)
- [x] Innehållstabell med kurs, värde, betyg, köpläge per rad
- [x] Ta bort innehav
- [x] Allokeringsdonut (Recharts)
- [x] Riskpanel (antal innehav, koncentration)
- [x] "Fråga om din portfölj" — AI-coach med konversationshistorik (kräver DEEPSEEK_API_KEY)

### Bevakningar
- [x] Lista bevakade aktier med köpläge, betyg, kurs, förändring
- [x] Lägg till via ticker-fält
- [x] Ta bort bevakning
- [x] Prisriktkurslarm: skapa larm (över/under + riktkurs + anteckning) per aktie
- [x] Lista aktiva larm med ta-bort-knapp
- [x] InfoTooltip förklarar hur larm fungerar

### Kontrollpanel (Admin)
- [x] 5 sektioner: Status / Pipeline / Universum / Mått / Inställningar
- [x] Systemstatus: antal aktier i scan, senaste körning
- [x] Pipeline-körningshistorik
- [x] Universum: fördelning per segment/sektor/land
- [x] Mått: betygsdistribution (histogram), per köpläge
- [x] Tillgänglig för alla inloggade (ej bara admin-roll)

### Auth-sidor
- [x] Landningssida: modern Lysa-inspirerad, features, trust markers, footer
- [x] Login: fungerar, länk till registrering + glömt lösenord
- [x] Registrering: fungerar, bekräftelsemeddelande
- [x] Lösenordsåterställning: /reset

---

## 11. Vad som SAKNAS / ÅTERSTÅR ⬜

### Hög prioritet (påverkar daglig användning)

**1. ✅ DEEPSEEK_API_KEY redan satt i .env**
- Utan den: AI-fliken visar "(AI ej konfigurerad)", fritextsökning fungerar ej, portföljcoach fungerar ej
- Fix: Lägg till `DEEPSEEK_API_KEY=sk-ant-...` i `C:\Users\hthur\OneDrive\Desktop\marketscan\.env`
- Hämta från: console.deepseek.com

**2. Pipeline kopplad till ny databas**
- Just nu körs gamla pipelinen (`stock-scanner-fix`) till lokala filer
- `load_data.py` körs manuellt för att ladda data
- Behövs: ändra gamla `core/daily_pipeline.py` så att den i slutet anropar `load_scan()` från `backend_worker/db_loader.py`
- Alternativt: lägg till ett steg i GitHub Actions efter pipeline-körning
- Fil att modifiera: `C:\Users\hthur\OneDrive\Desktop\stock-scanner-fix\core\daily_pipeline.py`

**3. Cloudflare R2 (prishistorik)**
- Betalningsproblem med Cloudflare — uppskjutet
- Just nu: API genererar deterministisk mock-data för prishistorik och betygstrend
- När R2 fungerar: `backend_worker/r2_uploader.py` + konfigurera R2_KEY_ID/R2_SECRET/R2_ENDPOINT i .env

### Medium prioritet

**4. GitHub Actions — automatisk daglig körning**
- Behövs: `.github/workflows/pipeline.yml` uppdateras med nya Supabase-hemligheter
- Schemat i gamla repot körs kl 06:15, 18:30 (Europe/Stockholm) + söndag 08:00
- Kopiera workflow-fil från gamla repot, lägg till secrets i GitHub repo settings

**5. Vercel-driftsättning**
- `apps/web` driftsätts via Vercel (Next.js)
- `apps/api` driftsätts via Vercel Python serverless (`vercel.json` finns redan)
- Blockas av: behöver fungera utan localhost-beroenden, R2 bör finnas

**6. Portfölj-historik (% per period)**
- Översiktsidan visar exempeldata för 1M/3M/6M/12M (hårdkodade värden i `OversiktView.tsx`)
- Riktig data kräver att holdings + historiska priser beräknas
- Enklast: spara snapshots av portföljvärde i en ny tabell `portfolio_snapshots`

**7. Rapporter-fliken — detaljerade kvartalsrapporter**
- Visar tillväxt + nyckeltal men INTE kvartalsvis EPS vs estimat
- Kräver: hämta `stock.quarterly_earnings` från yfinance i pipeline och lagra i R2/Postgres

**8. Prisriktkurslarm — backend-logik**
- [x] Bakgrundskollen i `backend_worker/price_alert_checker.py` är byggd
- [x] Manuell trigger endpoint `GET /api/alerts/check` (admin-only) finns i portfolio-router
- [x] GitHub Actions cron workflow behöver läggas till (se sektion 18)

### Lägre prioritet

**9. Settings/Profil-sida**
- Profilmenyn länkar till kontrollpanel — ingen dedikerad settings-sida
- Behövs: `app/(app)/installningar/page.tsx` med: visningsnamn, e-post, lösenordsbyte, tema-preferens sparad i Supabase

**10. Sektoröversikt**
- "Mini-heatmap" med sektorer och genomsnittsbetyg
- Data finns redan i scan_results (sector + score_total)
- Kan byggas som en ny vy eller som widget på Översikt

**11. Ljust/mörkt tema sparas i Supabase**
- Just nu: sparas i localStorage
- Bättre: spara i `profiles.theme_preference` i Supabase → synkas mellan enheter

---

## 12. Sparade idéer (ej planerade men diskuterade)

| Idé | Från | Beskrivning |
|---|---|---|
| **Lysa-onboarding** | Användaren | Fråga nya användare om erfarenhetsnivå, riskaptit, intresseområden. Anpassa vilka värden och detaljer som visas. Nybörjare = enklare vy, avancerade = fler siffror direkt. |
| **Strategitest (backtesting)** | Plan | Testa en filteruppsättning mot historisk data (kräver R2 med historiska snapshots) |
| **Aktiejämförelse** | Plan | Jämför 2–3 aktier sida vid sida på faktorer, pris, betyg |
| **Sektoröversikt** | Plan | Heatmap-vy med alla sektorer och deras genomsnittsbetyg |
| **Mobil-PWA** | Plan | Optimera för mobil, lägg till i hemskärmen, push-notiser |
| **E-postnotiser för larm** | Plan | Skicka e-post när prisriktkurslarm utlöses (logik finns i gamla repot) |
| **Portföljcoach konversation** | Byggt | AI-coach på portföljsidan fungerar, men kräver DEEPSEEK_API_KEY |
| **Analyskommitté med cache** | Byggt | Cachas per ticker per dag (just nu i minnet, bör cachas i Supabase) |

---

## 13. Kända buggar och begränsningar

| Bugg/Begränsning | Status | Detalj |
|---|---|---|
| Prishistorik är mock | Pågående | R2 ej konfigurerat — genereras deterministiskt från aktuell kurs. Se `stocks.py:_generate_mock_candles()` |
| Betygstrend är mock | Pågående | Samma orsak. Se `stocks.py:_generate_mock_score_history()` |
| AI fungerar ej | Blockas av nyckel | AI-analys aktiv — DEEPSEEK_API_KEY redan satt |
| Portfölj-% är hårdkodat | Pågående | 1M/3M/6M/12M på startsidan är exempeldata |
| Pipeline kör ej automatiskt | Pågående | Måste köra `load_data.py` manuellt |
| Prisriktkurslarm skickar ej notis | Pågående | UI + API klart, bakgrundsjobb saknas |
| React 18.3 (inte 19) | Permanent | Radix UI kräver React 18. Uppgradera INTE till 19 |
| `apps/api/requirements.txt` | Kritisk regel | FÅR ALDRIG innehålla pandas/xgboost/yfinance — Vercel 500MB-gräns |

---

## 14. Bugghistorik (lösta problem)

För att undvika att upprepa samma misstag:

| Problem | Lösning |
|---|---|
| `@tremor/react` inkompatibel med React 19 | Nedgraderat till React 18.3, Tremor borttaget |
| `@radix-ui/react-badge` 404 | Paketet finns inte — borttaget |
| `babel-plugin-react-compiler` fel | `reactCompiler: true` borttaget från next.config.ts |
| Middleware-fel: Supabase URL saknas | `.env.local` måste ligga i `apps/web/`, inte roten |
| `.supabase.com` vs `.supabase.co` | URL i .env.local hade fel TLD |
| `permission denied for table scan_results` | GRANT SELECT till anon + authenticated |
| `permission denied` vid INSERT (service_role) | GRANT INSERT/UPDATE till service_role |
| "Database error creating new user" | Trigger-funktion fixad med ON CONFLICT DO NOTHING |
| `python - << 'EOF'` fungerar ej på Windows CMD | Skapade `load_data.py` som en riktig fil istället |
| uvicorn startades från fel mapp | Måste startas från `marketscan/`-roten |
| `nan`-värden i JSON → ValueError | `df.replace([np.inf, -np.inf], np.nan)` + `math.isnan()` per cell |
| `scored_stocks.parquet` hittades ej | Data finns i `reports/scored_universe_*.parquet` |
| Unicode-escape i Python-docstring | Backslashes i Windows-sökvägar i strängar → använde kommentar istället |
| N-ikon + flytande bild | `devIndicators: false` + CSS `nextjs-portal { display: none }` |
| VerdictHeader täckte tabbar vid scroll | VerdictHeader + tabbar i gemensam sticky-div |
| AI committee 401 | Tog bort `get_current_user` som dependency |
| Admin-endpoints krävde role=admin | Ändrat till `get_current_user` (alla inloggade) |
| Admin COUNT(*) fungerade ej | `.select("ticker", count="exact")` + `.count` |

---

## 15. Kritiska regler att ALDRIG bryta

1. **`apps/api/requirements.txt`** — får ALDRIG innehålla `pandas`, `xgboost`, `yfinance`, `scikit-learn`. Vercel 500MB-gräns.
2. **React 18.3** — uppgradera INTE till React 19. Radix UI kräver 18.
3. **`backend_worker/`** — importeras ALDRIG av `apps/api/`. Tung Python körs bara i GitHub Actions.
4. **Supabase service key** — används bara i `backend_worker/` och `load_data.py`. Exponeras ALDRIG i frontend.
5. **Inga emojis i UI** — alltid Lucide-linjeikoner.
6. **Stateless API** — inga globala variabler i FastAPI (Vercel spinnar upp/ner instanser).
7. **DuckDB READ_ONLY** — `SET max_memory='768MB'` vid varje init om R2 används.
8. **`DATABASE_URL`** — måste vara Session Pooler (port 6543), INTE Direct. GitHub Actions använder IPv4.

---

## 16. Supabase-projekt

- **Projekt-ID:** `eukhlhowbbrccerxpisp`
- **Region:** eu-north-1 (Stockholm)
- **URL:** https://eukhlhowbbrccerxpisp.supabase.co
- **Dashboard:** https://supabase.com/dashboard/project/eukhlhowbbrccerxpisp

---

## 17. Nästa steg — exakt prioritetsordning

```
1. AI-analys aktiv — DEEPSEEK_API_KEY redan satt i .env
   → Aktiverar AI-analys, fritextsökning, portföljcoach

2. Koppla pipeline automatisk daglig körning
   → Redigera stock-scanner-fix/core/daily_pipeline.py:
      Lägg till anrop till db_loader.load_scan() i slutet av run_pipeline()
   → Alternativt: skapa GitHub Actions workflow

3. Cloudflare R2 (när betalning fungerar)
   → Lägg till R2_KEY_ID/R2_SECRET/R2_ENDPOINT i .env
   → Kör backend_worker/r2_uploader.py för att ladda upp historik
   → Prishistorik och betygstrend visar då riktig data

4. Settings-sida för användaren
   → Ny fil: apps/web/app/(app)/installningar/page.tsx
   → Visa/ändra: visningsnamn, tema-preferens, lösenordsbyte

5. Portfölj-historik (% per period på startsidan)
   → Ny tabell: portfolio_snapshots (user_id, date, total_value)
   → Beräkna % i OversiktView.tsx

6. Prisriktkurslarm backend
   → Kopiera core/price_alerts.py från gamla repot
   → Skapa nytt cron-jobb som checkar larm mot aktuella priser

7. Vercel deploy
   → Konfigurera vercel.json korrekt
   → Lägg till alla .env-variabler i Vercel dashboard
   → Deploy apps/web + apps/api

8. GitHub Actions
   → Kopiera .github/workflows/pipeline.yml från gamla repot
   → Lägg till GitHub Secrets: SUPABASE_URL, SERVICE_KEY etc.
```
