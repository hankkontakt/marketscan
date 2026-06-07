# DEBUGGING.md — MarketScan felsöknings-runbook

> Syfte: Gör det snabbt för Claude/DeepSeek (eller en människa) att hitta och åtgärda
> buggar utan att gissa. Läs detta FÖRST vid felrapportering.

---

## 1. Snabbdiagnos

Kör alltid först:

```bash
python scripts/doctor.py        # kontrollerar alla env-nycklar + DB
curl /api/debug/health          # admin-skyddad, djupare koll
curl /api/admin/health          # hälsokoll i adminpanelen
```

---

## 2. Symptom → orsak → fil

| Symptom | Trolig orsak | Kolla först |
|---------|-------------|-------------|
| "Failed to fetch" / alla anrop misslyckas | CORS — Vercel preview-URL inte i allow-list | `apps/api/core/config.py:28` CORS_ORIGINS |
| "Ogiltigt ticker-format: SSAB A.ST" | Regex avvisar mellanslag (B1) | `apps/api/routers/stocks.py:21` `_TICKER_RE` |
| Kalendern visar tomt / "Failed to fetch" | Finnhub API-nyckel saknas, eller CORS | `calendar.py` alla endpoints returnerar `{"events":[]}` vid fel |
| Jämför-sidan tom för ej-universum | Finnhub-fallback i compare_missing saknas (B2) | `stocks.py:428-457` — Finnhub-fallback finns redan |
| Price-history visar mock (is_synthetic=true) | R2 inte konfigurerad eller Finnhub-problem | `duckdb_r2.py`, `settings.R2_KEY_ID` |
| Admin-sidan 403 | Användaren har inte admin-roll i profiles | `profiles.role` i Supabase, `security.py:60` require_admin |
| Pipeline-trigger i admin ger 503 | GH_DISPATCH_TOKEN saknas | `GH_DISPATCH_TOKEN` i miljövariabler |
| Sökning returnerar inget | `safe_search` sanerade bort allt, eller tabellen tom | `search_utils.safe_search`, `scan_results`-rader |
| Portfölj visar "Ingen portfölj hittad" | Användaren har ingen portfolio-rad (skapas vid registrering) | `profiles`-tabell, signup-trigger |
| Innehav visas utan pris/sector | Aktien är inte i scan_results (utanför universum) | `scan_results` för den tickern |
| Notifikationer kommer inte | `notifications`-tabell RLS eller endpoint | `notifications.py`, RLS-policies |
| Diversifiering visar 0/inget | Portföljen tom eller priser saknas | `portfolio.py` diversification-endpoint |
| Liknande aktier tomt | Aktien inte i universum (score-vektorer saknas) | `stocks.py` similar-endpoint, kräver scan_results |
| AI-jämförelse misslyckas | DeepSeek-nyckel saknas eller rate limit | `settings.DEEPSEEK_API_KEY`, `deepseek_client.py` |
| Kalenderdag-klick öppnas inte | date-fns locale eller format-fel | `KalenderView.tsx` formatDay + dialog |

---

## 3. Kända millar & fallgropar

### API
- **Alla Finnhub-anrop MÅSTE använda `params=`** — f-string-URL med mellanslag förstör request.
  OK: `client.get(url, params={"symbol": t})`
  FEL: `client.get(f"...?symbol={t}")`
- **validate_ticker** tar `.upper().strip()` — mellanslag OK (regex tillåter `\s`).
- **Ticker-normalisering** måste ske FÖRE insert i watchlist/portfolio.
- **Inga modulglobaler** i FastAPI (Vercel serverless). `duckdb_r2.py` har `_con` — fixa vid R2-arbete.

### Frontend
- **Alla tooltips använder `InfoTooltip`** från `components/ui/` — skapa aldrig ny.
- **Charts:** återanvänd `components/charts/` — dubblera inte.
- **Lucide-ikoner** `strokeWidth={1.5}` — inga emojis.
- **TanStack Query** för datafetching, inte `useEffect`+`setState` förutom enklast möjliga.

### Databas
- **RLS på ALLA nya tabeller** — glöm inte DELETE-policy.
- **Roll läses från `profiles`** — aldrig från JWT (`user_metadata`).
- **`(select auth.uid())`** i RLS-policy (cachas), inte bara `auth.uid()`.

---

## 4. Verktyg

```bash
# Backend
uvicorn apps.api.main:app --reload     # starta API lokalt
python scripts/doctor.py                # diagnoseskript
python scripts/seed_demo.py             # fyll demo-data

# Frontend
cd apps/web && npm run dev              # Next.js dev-server
npx tsc --noEmit                        # type-check (gör alltid före commit)

# Pipeline
python -m backend_worker.pipeline.entrypoint --mode morning  # lokal pipeline
```

---

## 5. Lägga till ny debugging

1. **Ny symptom→orsak:** lägg till i tabellen i §2
2. **Ny endpoint:** admin-skyddad under `debug_router` i `request_id.py` eller `admin.py`
3. **Ny diagnos:** lägg check i `doctor.py` och/eller `/api/debug/health`
4. **Ny RLS-policy:** verifiera SELECT/INSERT/UPDATE/DELETE — glöm inte DELETE
