# MarketScan 2.0 — Projektstatus

> Senast uppdaterad: 2026-06-05  
> Stack: Next.js 15 + FastAPI + Supabase + GitHub Actions

---

## Vad är MarketScan?

En personlig aktieanalys- och screeningplattform byggd för hobbyinvesterare.  
Systemet hämtar data från börsen varje dag, beräknar betyg (0–100) för ~1 200 aktier baserat på 8 faktorer (värde, kvalitet, momentum m.fl.) och presenterar det i ett rent webbgränssnitt.

**Design-filosofi:** Lysa-lugn (enkel, ren) + Avanza-handlingsbar (tydliga åtgärder) + Bloomberg-täthet på begäran (djupdyk när man vill).

---

## Arkitektur

```
Next.js 15 (Vercel)          →   FastAPI (Vercel serverless)   →   Supabase Postgres
apps/web/                         apps/api/                         "het" data: scan + användare

GitHub Actions (daglig pipeline)  →   backend_worker/           →   Supabase + (Cloudflare R2)
Kör kl 07:30, 17:30, söndag          Tung Python: pandas/ML         "kall" data: prishistorik
```

**Kritisk regel:** `backend_worker/` (pandas, xgboost, yfinance) får ALDRIG importeras av `apps/api/`. API:et är en lättviktig brygga — måste hålla sig under Vercels 500 MB-gräns.

---

## Status per fas

### ✅ Fas 0 — Fundament
- [x] Monorepo-struktur (`apps/web`, `apps/api`, `backend_worker`, `supabase/`)
- [x] Supabase-projekt skapat (eu-north-1, Stockholm)
- [x] SQL-migrations: alla tabeller, index, RLS-policies
- [x] Seed-data: 8 testaktier
- [x] Rot-`.env` konfigurerad med Supabase-nycklar
- [x] `apps/web/.env.local` konfigurerad

### ✅ Fas 1 — Pipeline-grund
- [x] `backend_worker/db_loader.py` — bulk-laddar data via `copy_expert()`
- [x] `load_data.py` — engångsskript för att importera gamla parquet-filer
- [ ] GitHub Actions pipeline-fil kopplad till ny databas *(krävs för automatisk daglig uppdatering)*
- [ ] Cloudflare R2 — prishistorik och betygssnapshots *(betalningsproblem, uppskjutet)*

### ✅ Fas 2 — API
- [x] FastAPI med alla routers: screener, stocks, portfolio, watchlist, ai, admin
- [x] Pydantic-schemas
- [x] JWT-validering (lokal, ingen nätverksroundtrip)
- [x] Supabase RLS respekteras — service key för pipeline, anon/JWT för användare
- [x] CORS konfigurerad för `localhost:3000`

### ✅ Fas 3 — Designsystem + app-shell
- [x] Mörkt + ljust tema (ljust som standard, som Lysa/Avanza)
- [x] CSS-variabler för alla färger — finansiella, institutionella (ej AI-blålila)
- [x] Typsnitt: Inter för allt (inkl. siffror) med `tabular-nums` — exakt som Lysa
- [x] App-shell: NavRail (vänster), TopBar (toppen)
- [x] Kommandopalett (⌘K / Ctrl+K) för snabbsökning
- [x] Fungerande profilmeny (dropdown med e-post, inställningar, logga ut)
- [x] Auth-middleware — skyddar alla `/app`-rutter
- [x] Registrering (`/register`) och lösenordsåterställning (`/reset`)
- [x] Next.js dev-indikatorer borttagna

### ✅ Fas 4 — Kärnvyer (delvis)

#### Översikt (Hemvy)
- [x] Lysa-inspirerad portföljchart med area-graf
- [x] Periodknappar 1M / 3M / 6M / 12M med avkastning
- [x] 3 starka köplägen — klickbara till aktiesidan
- [x] Bevakningslista på startsidan
- [x] Exempeldata visas om ingen portfölj lagts till

#### Aktier (Screener)
- [x] Sammanslagen motor — stora, medelstora, småbolag, mikrobolag i en vy
- [x] Segment-toggle (multi-select)
- [x] FilterRail med betyg, sektor, köpläge, trend, P/E, ROE m.fl.
- [x] Resultattabell med sortering och tangentbordsnavigering
- [x] Sparklines i tabellen
- [x] Fritextsökning med AI-tolkning av naturligt språk
- [x] Spara/ladda anpassade vyer (kräver inloggning)

#### Aktiekort (Detaljsida)
- [x] Sticky header med kurs, köpläge, totalbetyg, trend, AI-prognos
- [x] Flikar: Översikt / Faktorer / Analys / Rapporter / AI
- [x] Prishistorik-chart (Lightweight Charts, candlestick + volym + MA50/MA200)
- [x] Nyckeltal-panel med `i`-tooltips som förklarar varje värde
- [x] Faktorbetyg-radar och staplar med förklaringar
- [x] Analyskommittén (3 AI-analytiker + ordförande) — kräver `ANTHROPIC_API_KEY`
- [x] Mock-prisdata när R2 inte är konfigurerat
- [ ] Rapporter-fliken — visar platshållare, behöver kvartalsdata från pipeline

#### Min portfölj
- [x] Innehav-tabell med kurs, värde, betyg, köpläge
- [x] Allokeringsdonut (Recharts)
- [x] Riskpanel (antal innehav, koncentration)
- [x] "Fråga om din portfölj" — AI-coach med konversationshistorik
- [ ] Lägg till innehav-formulär direkt på sidan *(läggs till via aktiekortets knapp)*

#### Bevakningar
- [x] Lista med betyg, köpläge, kurs, förändring per bevakad aktie
- [x] Snabblägg-till via ticker-fält
- [x] Ta bort bevakning
- [x] Bevaka-knapp — sparar/tar bort från watchlist via API
- [x] Lägg i portfölj — inline-formulär med antal + inköpskurs
- [x] Score history mock-data — betygstrend visas som linjegraf
- [x] NavRail hover-labels
- [x] Segment + filter sammanslagda i en ruta
- [x] Prisriktkurslarm — backend-checker i `backend_worker/price_alert_checker.py`
- [x] Manuell trigger `GET /api/alerts/check` (admin-only)
- [ ] Prisriktkurslarm — e-postnotiser när larm utlöses *(framtida fas)*

### ⬜ Fas 5 — Admin + driftsättning
- [ ] Kontrollpanel — systemstatus, pipeline-trigger, universe-hantering
- [ ] Vercel-driftsättning
- [ ] GitHub Actions — koppla befintlig pipeline till ny Supabase-databas
- [ ] Domänkonfiguration

---

## Kända problem / begränsningar just nu

| Problem | Orsak | Lösning |
|---|---|---|
| Prishistorik är mock-data | Cloudflare R2 ej konfigurerat (betalningsproblem) | Lös R2-konto eller använd alternativ lagring |
| Betygstrend-chart är tom | Kräver historiska R2-snapshots | Byggs när pipeline är kopplad |
| AI-analys kräver API-nyckel | `ANTHROPIC_API_KEY` ej satt i `.env` | Lägg till nyckeln, se Setup nedan |
| Portfolio/watchlist 401 | Kräver inloggat konto | Skapa konto på `/register` |
| Rapporter-fliken är platshållare | Kvartalsdata ej implementerat i pipeline | Framtida fas |
| Bara 8 testaktier | `load_data.py` ej körd | Kör skriptet, se Setup nedan |
| Pipeline kör inte automatiskt | GitHub Actions ej kopplat till ny DB | Uppdatera `pipeline.yml` med nya hemligheter |

---

## Setup — köra lokalt

### 1. Förkrav
- Python 3.11+
- Node.js 20+
- Konton: Supabase (klart), Cloudflare R2 (uppskjutet)

### 2. Starta API
```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python -m uvicorn apps.api.main:app --reload --port 8000
```

### 3. Starta frontend (nytt CMD-fönster)
```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web
npm run dev
```

Öppna: `http://localhost:3000`

### 4. Ladda riktig aktiedata (engång)
```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python load_data.py
```

### 5. Skapa användarkonto
Gå till `http://localhost:3000/register`

### 6. Aktivera AI-analys
Lägg till i `.env` (rot-mappen):
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Miljövariabler — vad som behövs

**Fil:** `C:\Users\hthur\OneDrive\Desktop\marketscan\.env`

| Variabel | Status | Var hittar du den |
|---|---|---|
| `SUPABASE_URL` | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_SERVICE_KEY` | ✅ Klar | Supabase → Settings → API |
| `SUPABASE_JWT_SECRET` | ✅ Klar | Supabase → Settings → API |
| `DATABASE_URL` | ❌ Poolern ej provisionerad | Supabase → Settings → Database → Session Pooler. Port 6543 svarar ej. |
| `DEEPSEEK_API_KEY` | ✅ Klar | platform.deepseek.com |
| `GEMINI_API_KEY` | ✅ Klar | console.gemini.google.com |
| `FINNHUB_API_KEY` | ✅ Klar | finnhub.io |
| `EMAIL_SENDER` | ✅ Klar | Gmail |
| `EMAIL_PASSWORD` | ✅ Klar | App-lösenord |
| `EMAIL_TO` | ✅ Klar | h.thurner@hotmail.se |
| `R2_KEY_ID` | ❌ Saknas | Cloudflare R2 (uppskjutet) |
| `R2_SECRET` | ❌ Saknas | Cloudflare R2 (uppskjutet) |
| `R2_ENDPOINT` | ❌ Saknas | Cloudflare R2 (uppskjutet) |

**Fil:** `C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web\.env.local`

| Variabel | Status |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Klar |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Klar |
| `NEXT_PUBLIC_API_URL` | ✅ Klar (`http://localhost:8000`) |

---

## Nästa prioriterade steg

### Hög prioritet
1. **Skapa användarkonto** → `localhost:3000/register`
2. **Kör SQL-migration** för portfolio_snapshots (se HANDOFF.md)
3. **DATABASE_URL** → pooler-port (6543) svarar ej. Kontrollera i Supabase Dashboard → Database → Connection Pooling att poolern är aktiverad.
4. **Ladda riktig data** → `python load_data.py` (om ny data behövs)
5. **AI-analys aktiverad** ✅ `DEEPSEEK_API_KEY` är satt — fungerar direkt + prisriktkurslarm

### Medium prioritet
5. **Cloudflare R2** → riktig prishistorik och betygstrender (när betalning fungerar)
6. **Rapporter-fliken** → kvartalsdata via yfinance i pipeline
7. **E-postnotiser vid larm** → skicka notis när `price_alert_checker.py` triggar ett larm

### Lägre prioritet
8. **Vercel-driftsättning** → när appen känns klar lokalt
9. **Kontrollpanel** → admin-sidan för systemövervakning
10. **Ljust/mörkt per användare** → spara inställning i Supabase-profil

---

## Sparade idéer (ej planerade ännu)

| Idé | Beskrivning |
|---|---|
| **Lysa-onboarding** | Fråga nya användare om erfarenhetsnivå och anpassa vilka värden/förklaringar som visas. Nybörjare får enklare vy, avancerade får fler siffror direkt. |
| **Sektoröversikt** | Mini-heatmap med alla sektorer och deras genomsnittsbetyg |
| **Strategitest** | Backtesta en filteruppsättning mot historisk data (kräver R2) |
| **Aktiejämförelse** | Jämför 2–3 aktier sida vid sida |
| **Mobil-PWA** | Optimera för mobil, lägg till i hemskärmen |
| **E-postnotiser** | Skicka e-post när ett prisriktkurslarm utlöses |

---

## Datamodell (Supabase)

| Tabell | Innehåll | RLS |
|---|---|---|
| `scan_results` | Aktuell scan — alla aktier med betyg och nyckeltal | Publik läsning |
| `profiles` | Användarens visningsnamn | Privat (egen rad) |
| `portfolios` | Portföljnamn per användare | Privat |
| `holdings` | Innehav: ticker, antal, inköpskurs | Privat |
| `watchlist` | Bevakade tickers | Privat |
| `price_alerts` | Prisriktkurslarm | Privat |
| `saved_screens` | Sparade filteruppsättningar | Privat |
| `pipeline_runs` | Logg för varje pipeline-körning | Publik läsning |

---

## Filstruktur (viktigaste filer)

```
marketscan/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/(app)/          # Skyddade sidor (kräver login)
│   │   │   ├── oversikt/       # Startsida (Lysa-stil)
│   │   │   ├── screener/       # Aktie-screener
│   │   │   ├── aktie/[ticker]/ # Aktiekort med prishistorik + AI
│   │   │   ├── portfolj/       # Min portfölj
│   │   │   └── bevakningar/    # Bevakningslista
│   │   ├── components/
│   │   │   ├── ui/InfoTooltip  # i-bubbla förklarar alla värden
│   │   │   ├── charts/         # PriceChart, FactorRadar, ScoreSparkline
│   │   │   ├── screener/       # FilterRail, ResultTable, SegmentToggle
│   │   │   └── stock/          # VerdictHeader, AnalysCommittee
│   │   └── app/globals.css     # Alla CSS-variabler och färger
│   └── api/                    # FastAPI (lättviktig, ej pandas)
│       └── routers/            # screener, stocks, portfolio, watchlist, ai, admin
├── backend_worker/             # Tung Python (kör ALDRIG i API)
│   └── db_loader.py            # Laddar data till Supabase
├── supabase/migrations/        # SQL-schema
├── load_data.py                # Engångsskript: importera gamla parquet-filer
├── .env                        # API-nycklar (läses av FastAPI)
└── STATUS.md                   # Den här filen
```
