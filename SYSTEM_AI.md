# MarketScan 2.0 — Systemdokumentation

> **Repo:** `marketscan/` (ny repo, ej `stock-scanner-fix`)
> **Senast uppdaterad:** 2026-06-05
> **Status:** Scaffold klar, redo för Supabase-setup och npm install

---

## 0. Underhållsprotokoll (läs detta ALLTID först)

Uppdatera detta dokument LÖPANDE:
- När du ändrar ett API-anrop → uppdatera §3
- När du lägger till en komponent → uppdatera §4
- När du hittar ett bug → lägg i §6
- När du gör arkitekturbeslut → motivera i §2

---

## 1. Stack & Arkitektur

```
apps/web/           Next.js 16 (App Router) + React 19 + TypeScript strict
apps/api/           FastAPI Python 3.12 (Vercel serverless, max 500 MB)
backend_worker/     Tung pipeline — pandas/xgboost/yfinance — KÖR ALDRIG i API
supabase/           SQL migrations + seed
.github/workflows/  pipeline.yml — timezone: Europe/Stockholm
```

**Kritisk regel:** `backend_worker/` får ALDRIG importeras av `apps/api/`. Kontrollera alltid `apps/api/main.py` och alla routers mot denna regel.

**Storage:**
- **Het data** (aktuell scan, portföljer, bevaklista): Supabase Postgres `eu-north-1`
- **Kall data** (prishistorik, betygshistorik, backtest): Cloudflare R2 + DuckDB READ_ONLY
- DuckDB används ALDRIG på het väg (screener) — ~2s kallstart, acceptabelt för historik

---

## 2. Design-system

**Tema:** Mörkt first. CSS-variabler i `apps/web/app/globals.css`.

| Token | Värde | Användning |
|---|---|---|
| `--bg-base` | `#0A0B0D` | Djupaste bakgrund |
| `--bg-surface` | `#131519` | Kort, paneler |
| `--bg-elevated` | `#1B1E24` | Hover, popover |
| `--accent` | `#5B8DEF` | Primär åtgärd |
| `--up` | `#3FB68B` | Positiv förändring |
| `--down` | `#E0645C` | Negativ förändring |
| `--warn` | `#D9A441` | Varning |

**Typografi:** Geist Sans (UI) + Geist Mono tabular-nums (siffror).
**Ikoner:** Lucide ONLY — aldrig emoji.
**Komponenter:** shadcn/ui (Radix-base), Tremor (KPI/charts), Recharts (radar).

---

## 3. API-router-karta

Alla routes prefixas med `/api/`.

| Route | Metod | Auth | Beskrivning |
|---|---|---|---|
| `/scan` | GET | Valfri | Screener (Postgres, het väg) |
| `/scan/sectors` | GET | Nej | Alla sektorer |
| `/scan/meta` | GET | Nej | Datum, antal per segment |
| `/stocks/{ticker}` | GET | Nej | Aktiedata |
| `/stocks/{ticker}/price-history` | GET | Nej | R2/DuckDB — OHLCV |
| `/stocks/{ticker}/score-history` | GET | Nej | R2/DuckDB — betygstrend |
| `/stocks` | GET | Nej | Snabbsök (⌘K) |
| `/portfolio` | GET | Ja | Portfölj med innehav |
| `/portfolio/holdings` | POST | Ja | Lägg till innehav |
| `/portfolio/holdings/{id}` | DELETE | Ja | Ta bort innehav |
| `/watchlist` | GET | Ja | Bevakningar |
| `/watchlist/{ticker}` | POST/DELETE | Ja | Lägg/ta bort |
| `/alerts` | GET/POST | Ja | Prisriktkurslarm |
| `/screens` | GET/POST | Ja | Sparade screener-vyer |
| `/ai/parse-filter` | POST | Nej | NL → filter JSON |
| `/ai/committee/{ticker}` | POST | Ja | Analyskommittén |
| `/ai/portfolio-coach` | POST | Ja | AI-chat portfölj |
| `/admin/status` | GET | Admin | Pipeline-status |
| `/admin/pipeline-runs` | GET | Admin | Körningshistorik |
| `/admin/users` | GET | Admin | Användarhantering |
| `/admin/score-distribution` | GET | Admin | Score-histogram |
| `/admin/universe` | GET | Admin | Universum-täckning |
| `/health` | GET | Nej | Health check |

---

## 4. Komponent-karta

```
components/
  layout/
    NavRail.tsx         Vertikal ikonnavigering (sticky, 64px bred)
    TopBar.tsx          Global sökknapp (⌘K), temaväxlare, konto
  command/
    CommandPalette.tsx  ⌘K / Ctrl+K — sök aktier + navigera vyer
  providers/
    QueryProvider.tsx   TanStack Query + devtools
  screener/
    SegmentToggle.tsx   Multi-select chips för large/mid/small/micro
    FilterRail.tsx      Expanderbara filter (köpläge, trend, sektor, etc.)
    ResultTable.tsx     Sortierbar tabell, tangentbordsnavigering
  stock/
    VerdictHeader.tsx   Sticky header — ticker, kurs, köpläge, betyg
    AnalysCommittee.tsx Tre analytiker + ordförande syntes + konfidensmätare
  charts/
    PriceChart.tsx      TradingView Lightweight Charts (candlestick, perioder)
    FactorRadar.tsx     Recharts radar — 8 faktorbetyg
```

---

## 5. Vyer & rutter

```
/                           Landningssida (publik, SEO)
/login                      Supabase Auth-inloggning
/oversikt                   Daglig briefing, top picks, snabblänkar
/screener                   Sammanslagen screener (alla segment)
/aktie/[ticker]             Aktiekort — 5 flikar
/portfolj                   Min portfölj + AI-coach
/bevakningar                Watchlist + prisriktkurslarm
/kontrollpanel              Admin (5 sektioner)
```

Alla `/(app)/*`-rutter är skyddade av `middleware.ts` (Supabase JWT-check → redirect `/login`).

---

## 6. Kända begränsningar & TODO

| # | Vad | Prioritet |
|---|---|---|
| 1 | Installera npm-paket: `cd apps/web && npm install` | Hög |
| 2 | Supabase-projekt skapa + köra migration `001_initial_schema.sql` | Hög |
| 3 | Fylla i `.env` från `.env.example` | Hög |
| 4 | `apps/api/requirements.txt` saknas — skapa från `pyproject.toml` | Hög |
| 5 | `useCommandPalette.ts` använder enkel eventbus — ersätt med Zustand när paket är installerade | Medium |
| 6 | `PriceChart.tsx` — `cmdk` och `zustand` saknas i deps (lägg till i package.json) | Medium |
| 7 | `Rapporter`-fliken i aktiekort ej implementerad (requires pipeline integration) | Medium |
| 8 | Prisriktkurslarm-UI ej byggt i Bevakningar | Medium |
| 9 | Ljust tema — CSS-tokens finns, men temaväxlaren i TopBar behöver `"use client"` + `useTheme` | Låg |

---

## 7. Nästa steg (i ordning)

```bash
# 1. Skapa Supabase-projekt (eu-north-1)
# 2. Kopiera .env.example → .env, fyll i nycklar
# 3. Kör migration
supabase db push  # eller kör SQL manuellt i Supabase dashboard

# 4. Installera frontend-paket
cd apps/web && npm install

# 5. Starta dev-server
npm run dev
# → http://localhost:3000

# 6. Starta FastAPI lokalt
cd apps/api && pip install -e ../.. && uvicorn main:app --reload
# → http://localhost:8000

# 7. Verifiera: /api/health returnerar {"status":"ok"}
# 8. Verifiera: /api/scan returnerar seed-data
# 9. Kör npm run type-check — rätta TypeScript-fel
```

---

## 8. Verifierings-checklista

| Vad | Hur | Status |
|---|---|---|
| Supabase schema | `SELECT count(*) FROM scan_results` = 8 (seed) | ❌ Pending |
| RLS | Användare A ser ej B:s portfölj | ❌ Pending |
| API < 500 MB | Vercel build logs: inga pandas/xgboost | ❌ Pending |
| Auth middleware | Oinloggad → redirect /login | ❌ Pending |
| Screener | Kombination småbolag+midcap fungerar | ❌ Pending |
| ⌘K | Öppnar palett, söker aktier | ❌ Pending |
| Aktiekort | Alla 5 flikar renderar | ❌ Pending |
| Analyskommittén | 3 analytiker + syntes med konfidens | ❌ Pending |
| Tema | Mörkt default, växlare → ljust | ❌ Pending |
