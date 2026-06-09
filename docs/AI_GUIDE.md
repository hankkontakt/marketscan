# MarketScan — AI-operatörsmanual

> **Du som läser detta är en AI som ska arbeta i MarketScan.** Den här filen är
> din enda obligatoriska startpunkt. Den lär dig *hur du ska tänka*, hur hela
> systemet hänger ihop, exakt vilka verktyg som finns och hur du använder dem,
> samt vilka misstag som redan gjorts så att du slipper göra om dem.
>
> `SYSTEM_AI.md` är referens-uppslagsverket (varje fil/funktion). Den här filen
> är *operativ doktrin*. Läs den här FÖRST, slå upp detaljer i `SYSTEM_AI.md`.
>
> Senast reviderad: 2026-06-09.

---

## 0. Prime directives — så här tänker du

1. **Felsök, gissa inte.** Det finns tre verktyg som svarar på "varför funkar
   det inte" på sekunder (se §3). Använd dem *innan* du teoretiserar. En enda
   bugg i det här projektet tog en gång ~500 meddelanden att hitta för att ingen
   körde diagnostiken först. Gör inte om det.
2. **Anta ingenting — verifiera mot verkligheten.** Proba live-API:t med `curl`,
   kör smoke-testet, läs den faktiska koden. "Borde fungera" är inte data.
3. **Felet du ser är sällan rotorsaken.** "Nätverksfel" var egentligen en saknad
   databasrättighet tre lager ner. Följ kedjan till botten.
4. **Bevara säkerhet och datakorrekthet över allt annat.** RLS, GRANTs och
   auth-dependencies är inte valfria. Se §8.
5. **Lämna systemet lättare att felsöka än du hittade det.** Varje fix bör också
   göra nästa likadana fel lättare att hitta (bättre felmeddelande, diagnostik,
   test).
6. **Håll dokumentationen levande.** Ändrar du arkitektur eller hittar en bugg —
   uppdatera `SYSTEM_AI.md` (changelog överst) och, om mönstret är nytt, den här
   filen och `CONTRIBUTING.md`.

---

## 1. Vad MarketScan är (60 sekunder)

En svensk aktieanalys-plattform: en daglig pipeline scorar aktier (teknisk +
fundamental + sentiment), och en webbapp låter användare screena, bygga
portfölj, få AI-analys, sätta alarm och backtesta strategier.

**Stack:**
- **Frontend:** Next.js 14 (App Router, TypeScript) — `apps/web/`
- **API:** FastAPI (Python) — `apps/api/`
- **Pipeline/jobb:** Python på GitHub Actions — `backend_worker/`
- **Databas/Auth:** Supabase (Postgres + Auth + RLS)
- **Lagring:** Cloudflare R2 (parquet-filer)
- **AI:** DeepSeek (LLM)
- **Hosting:** två separata Vercel-projekt (frontend + API)

---

## 2. Arkitektur — request-flödet

```
┌─────────────┐  absolut fetch (CORS)   ┌────────────────────────┐
│  Webbläsare │ ──────────────────────► │ marketscan-api.vercel  │  FastAPI
│ (Next.js)   │  Authorization: Bearer  │ apps/api/main.py        │  apps/api/
│ web-…vercel │   <Supabase JWT>        └───────────┬────────────┘
└─────────────┘                                     │ supabase-py (PostgREST)
       ▲                                            ▼
       │ inloggning (direkt)              ┌────────────────────────┐
       └────────────────────────────────►│ Supabase                │
                                          │ Postgres + Auth + RLS   │
                                          └───────────▲────────────┘
                                                      │ service_role (skriver)
                                          ┌───────────┴────────────┐
                                          │ GitHub Actions pipeline │  backend_worker/
                                          │ → R2 (parquet) → DB     │
                                          └────────────────────────┘
```

**Tre saker en ny AI nästan alltid missförstår:**

1. **Två Vercel-projekt, olika domäner.** Frontend (`web-…-hankkontakts-projects
   .vercel.app`) och API (`marketscan-api.vercel.app`) är separata deploys.
   Frontend anropar API:t **direkt på dess domän** (absolut URL i
   `apps/web/lib/api.ts`). Proxa INTE via same-origin — den vägen går genom
   Vercel Deployment Protection och ger "Nätverksfel".

2. **Tre Supabase-klientnivåer** (`apps/api/dependencies.py`) — välj rätt:
   | Klient | Nyckel | RLS | Använd för |
   |---|---|---|---|
   | `get_supabase` | anon | ✅ gäller | publik läsning (screener, marknad) |
   | `get_user_supabase` | anon + **JWT** | ✅ per användare | **all användardata** |
   | `get_supabase_admin` | service_role | ❌ kringgås | **endast** bakom `require_admin` / cron |

3. **GRANT ≠ RLS.** Postgres har två lager: table-GRANT (grov grind: får rollen
   röra tabellen alls?) och RLS (fin filtrering: vilka rader?). **Båda** måste
   stämma. Saknad GRANT = fel `42501`, osynligt för all kod ovanför databasen.
   Migration `023` sätter GRANTs för alla tabeller.

---

## 3. Felsökningsdoktrinen — DINA tre verktyg

Detta är det viktigaste avsnittet. Använd dessa **före** all gissning.

### 3.1 Djupdiagnostik — `GET /api/admin/diagnostics/deep` (admin)
Ett anrop returnerar `{ok, summary, issues[], env, tables, migrations}`. Den
probar varje användartabell med **authenticated-kontext** (admin-JWT) — alltså
exakt den väg en riktig användare går — så en saknad GRANT dyker upp som ett
konkret `issue` med åtgärd ("kör migration 023"). `service_role`-checks kan
aldrig se det (de kringgår grants). Källkod: `apps/api/core/diagnostics.py`.
I UI:t: Kontrollpanel → fliken **Diagnostik**.

### 3.2 Smoke-test — `python scripts/smoke_test.py [base_url]`
Probar hela API-ytan och hävdar rätt sak per klass: publik→200,
auth/admin-utan-token→401/403. Allt som 500:ar (krasch) eller 404:ar
(routing-bugg) FAIL:ar. Stdlib-only, kör mot live eller `http://localhost:8000`.
Sätt `SMOKE_JWT=<token>` för att även testa inloggade läsningar (→ 200).
Exit-kod ≠ 0 vid fel → använd i CI / före deploy.

### 3.3 Global felhanterare — automatisk (`apps/api/main.py`)
Varje ohanterat undantag returneras nu som JSON-500 **med CORS-headers** (plus
full traceback i loggen). Det betyder: ett serverfel visas som ett *läsbart*
meddelande i frontend, aldrig som ett kryptiskt CORS-löst "Nätverksfel". När du
ser `"Internt serverfel (XxxError)"` i UI:t → kolla API-loggarna för
tracebacken; felet ÄR fångat, inte gömt.

### 3.4 Felkods-uppslagstabell
| Symptom / kod | Betyder | Åtgärd |
|---|---|---|
| `42501` / `permission denied for table X` | saknad GRANT för rollen | kör `supabase/migrations/023_grant_table_privileges.sql` |
| `42P01` / `relation X does not exist` | migration ej körd | kör migrationen; kolla diagnostiken |
| `42703` / `column X does not exist` | schema/kod osynkat | en migration saknas eller koden är fel |
| `23505` | duplikatnyckel | upsert eller hantera konflikt |
| "Nätverksfel" i frontend | CORS-löst svar (ohanterat fel) ELLER fel `API_BASE` | global handler fixar CORS; verifiera absolut API-URL |
| 422 från endpoint | request-body ≠ Pydantic-schema | jämför frontend-payload mot modellen |
| endpoint 500:ar bara MED giltig token | handler-logiken (DB), inte auth | felet visar nu typen; kolla loggar |
| `ModuleNotFoundError: No module named 'apps'` | Vercel-runtime saknar paket-init | säkerställ `apps/__init__.py` finns |

---

## 4. Fil-för-fil-karta

### `apps/api/` — FastAPI
| Fil | Roll |
|---|---|
| `main.py` | App-skapande, middleware, **global exception handler**, router-registrering |
| `dependencies.py` | De tre Supabase-klienterna (anon / user / admin) |
| `core/security.py` | `get_current_user`, `require_admin`, JWT-verifiering (läser `app_metadata.role`) |
| `core/db.py` | **DB-helpers** (`run`/`rows`/`one_or_404`) — översätter DB-fel till läsbara HTTPExceptions |
| `core/diagnostics.py` | Djupdiagnostik-logiken |
| `core/config.py` | `settings` — alla env-vars + `CORS_ORIGINS` |
| `core/rate_limiter.py` | slowapi-limiter |
| `core/request_id.py` | Request-ID-middleware + `/api/debug/*` (client-error, health) |
| `core/search_utils.py` | `safe_search` — sanerar PostgREST-filter |
| `core/ai_cache.py` | AI-svarscache (per ticker/dag) |
| `core/avanza_import.py` | CSV-parsning för Avanza-import |
| `core/enrichment.py` | Berikar innehav med scan-data |
| `routers/*.py` | 28 routers (en per domän). **`_TEMPLATE.py` = mall för nya.** |

### `apps/web/` — Next.js
| Sökväg | Roll |
|---|---|
| `lib/api.ts` | **Enda** API-klienten (`api<T>()`) — JWT, timeout, fel→`ApiError`. `API_BASE` absolut. |
| `lib/supabase/` | Supabase browser/server-klient (auth) |
| `middleware.ts` | Auth-skydd: redirectar oinloggade från privata routes |
| `hooks/` | TanStack Query-hooks (datahämtning) |
| `components/` | UI, inkl. `admin/AdminSections.tsx` (Kontrollpanel) |
| `app/(app)/*` | Inloggade sidor (oversikt, screener, portfolj, kontrollpanel, …) |
| `app/(auth)/*` | login, register, reset |
| `app/sw.ts` | Service worker (Serwist). `apiRoute` (NetworkOnly) FÖRST i `runtimeCaching`. |

### `backend_worker/` — pipeline & jobb (körs på GitHub Actions, ej Vercel)
| Fil | Roll |
|---|---|
| `pipeline/entrypoint.py` | Pipeline-ingång (mode: manual/daily/smallcap…) |
| `db_loader.py` | Laddar scoring-resultat → `scan_results` (via service_role/psycopg2) |
| `r2_uploader.py` / `duckdb_r2.py` | Parquet till/från R2 |
| `smallcap_scanner.py`, `risk_analyzer.py`, `score_tracker.py`, `smart_alert_engine.py`, `strategy_backtester.py`, `signal_analytics.py`, `sector_rotation.py`, `universe_discovery.py`, `ml_trainer.py` | Analys-/jobb-moduler |

### `supabase/migrations/` — körs MANUELLT i Supabase SQL Editor
001 schema · 005 smallcap · 012 profil · 014 transaktioner · 018 RLS-härdning ·
019 risk · 020 smart alerts · 021 strategy lab · 022 fund_holdings ·
**023 GRANTs (kritisk)**.

### `scripts/` — verktyg
`smoke_test.py` (API-yta) · `fix_async_handlers.py` (async→def AST-transformer).

---

## 5. Konventionerna (reglerna) — och varför

Bryt inte dessa. De flesta finns för att en specifik bugg en gång tog timmar.

1. **`def`, inte `async def`**, om handlern bara gör synkrona Supabase-anrop.
   FastAPI kör `def` i threadpool; synkront anrop i `async def` blockerar
   event-loopen. Använd `async def` ENDAST om du `await`:ar (httpx, gather).
   *(89 handlers konverterades 2026-06-09; gör inte om felet i nya.)*
2. **Användardata** → `Depends(get_current_user)` + `Depends(get_user_supabase)`.
3. **`get_supabase_admin` ENDAST bakom `require_admin`.** Service_role kringgår
   RLS — oautentiserad användning = full dataexponering.
4. **Wrappa DB-anrop med `apps.api.core.db`-helpers** så fel blir läsbara.
5. **Sätt alltid `response_model`.**
6. **Dyra externa anrop (LLM) bakom auth** (och helst rate-limit).
7. **Ny tabell** → RLS på + policy + GRANT (se §6.2).
8. **Frontend:** all API-åtkomst via `lib/api.ts`. Inga råa `fetch("/api/...")`.
   `API_BASE` med `||` (inte `??`) och absolut default.

---

## 6. Vanliga uppgifter — steg för steg

### 6.1 Lägg till en ny API-endpoint
1. Kopiera `apps/api/routers/_TEMPLATE.py` → `apps/api/routers/<feature>.py`.
2. Justera `prefix`/`tags`, schemas, och handlers (följ mallen exakt).
3. Registrera i `apps/api/main.py`: `app.include_router(<feature>.router)`.
4. Verifiera: `PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"`.
5. Lägg till en probe i `scripts/smoke_test.py` och kör det.

### 6.2 Lägg till en ny tabell
```sql
CREATE TABLE IF NOT EXISTS my_table ( id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id), ... );
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "my_table_own" ON my_table FOR ALL
  USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON my_table TO authenticated;
```
- **Publik läs-tabell:** `FOR SELECT USING (true)` + `GRANT SELECT … TO anon`.
- **Backend-only:** RLS på, ingen policy → endast service_role kommer åt.
- Lägg in tabellen i `apps/api/core/diagnostics.py` (`USER_TABLES`/`MIGRATION_MARKERS`).
- Migrationen körs **manuellt** i Supabase SQL Editor. Säg till användaren.

### 6.3 Lägg till en frontend-sida/data
1. Backend-endpoint klart (6.1).
2. Lägg en hook i `apps/web/hooks/` (TanStack Query, anropar `api<T>()`).
3. Bygg sidan i `apps/web/app/(app)/<route>/`.
4. `cd apps/web && npx tsc --noEmit` ska vara grön.

### 6.4 Felsöka "det funkar inte"
1. Kör `python scripts/smoke_test.py` → ser du 500/404 nånstans?
2. Öppna Kontrollpanel → **Diagnostik** (eller `GET /api/admin/diagnostics/deep`).
   Läs `issues[]`.
3. Reproducera mot live med `curl` (skicka rätt `Origin`-header).
4. Är det `42501` → migration 023. `42P01` → migration saknas. 422 → schema.
5. Ohanterat fel? Frontend visar nu `"Internt serverfel (Typ)"` → läs loggen.

### 6.5 Trigga pipelinen
Admin → Pipeline-fliken (kräver `GH_DISPATCH_TOKEN` i Vercel). Eller manuellt
via GitHub Actions-workflowen. Pipeline skriver `scan_results` via service_role.

---

## 7. Buggmönster-katalog (lär dig känna igen dessa)

Varje rad är en verklig bugg som hittats. Känn igen mönstret omedelbart.

| Mönster | Symptom | Rotorsak | Skydd nu |
|---|---|---|---|
| **Saknad GRANT** | "Nätverksfel" / 500 / tom lista | `42501`, RLS på men ingen table-grant | migration 023 + diagnostik probar authenticated-kontext |
| **CORS-löst fel** | "Nätverksfel" maskerar riktiga felet | middleware-ordning: ohanterat fel förbi CORS | global exception handler sätter CORS |
| **async + sync SDK** | oförutsägbar latens/timeout | `async def` + synkront Supabase blockerar loopen | 89 konverterade till `def`; regel §5.1 |
| **`?? ""` på env** | anrop går till fel origin | tom sträng faller inte igenom `??` | `API_BASE` använder `||` + absolut default |
| **Oautentiserad LLM** | kostnads-/DoS-risk | dyra endpoints utan auth | `get_current_user` på AI-endpoints |
| **Dödkod m. korrupt encoding** | `SyntaxError` vid import | mojibake-fil, oimporterad | `prompts.py` borttagen |
| **Ohanterad DB-rad** | endast med giltig token: 500 | `.execute()` utan try/except | `db.run()`-helpers + global handler |

---

## 8. Säkerhetsmodell (verifiera vid varje ändring)
- **GRANT + RLS i tandem.** Användartabeller: RLS `FOR ALL` med `USING` +
  `WITH CHECK` på `(select auth.uid()) = user_id`. GRANT till `authenticated`.
- **service_role aldrig i frontend** och aldrig utan `require_admin` i API.
- **Inga secrets med `NEXT_PUBLIC_`-prefix** (de bakas in i klient-bundeln).
- **Admin/debug-endpoints** kräver `require_admin`. (`/api/debug/client-error`
  är medvetet öppen men rate-limitad.)
- **Användarinput → PostgREST** saneras med `safe_search`.
- **CORS** tillåter endast `*-hankkontakts-projects.vercel.app` + explicit lista.
- Checklista före deploy finns i `CONTRIBUTING.md §5`.

---

## 9. Verifiera innan du commitar
```bash
PYTHONPATH=. python -c "from apps.api.main import app; print('routes', len(app.routes))"  # API importerar
python scripts/smoke_test.py                          # API-ytan (live) grön
cd apps/web && npx tsc --noEmit                        # frontend-typer
```
Commit-meddelanden: förklara **rotorsak** och **varför**, inte bara vad. Avsluta
med `Co-Authored-By:`-raden. Committa per logisk enhet. Pusha bara när bett om
det — men i det här projektet auto-deployar Vercel på push till `master`.

---

## 10. Dokumentindex (vad varje fil är till för)
| Fil | Innehåll |
|---|---|
| **`docs/AI_GUIDE.md`** | **Den här filen — operativ doktrin. Börja här.** |
| `docs/SYSTEM_AI.md` | Referens: varje fil/funktion/dataflöde + changelog |
| `docs/CONTRIBUTING.md` | Utvecklings-/felsökningsguide, konventioner, checklista |
| `docs/PIPELINE_SETUP.md` | Pipeline-/GitHub Actions-uppsättning |
| `DEBUGGING.md` | Äldre felsöknings-runbook (komplement) |
| `HANDOFF.md` / `STATUS.md` / `SETUP.md` | Historik/status/lokal setup |

> Om något i den här filen motsäger verkligheten: **verkligheten vinner** —
> verifiera mot koden/live, fixa, och uppdatera den här filen.
