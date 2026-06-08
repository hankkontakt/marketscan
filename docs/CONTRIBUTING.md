# MarketScan — Utvecklings- & felsökningsguide

> Den här filen finns för att en framtida ändring (eller en AI) ska komma rätt
> direkt. Den kodifierar mönster som lärdes den hårda vägen. Läs `SYSTEM_AI.md`
> för den fullständiga systemkartan; läs den här för **hur man bygger och
> felsöker utan att trampa i samma minor igen**.

---

## 1. Felsök FÖRST — innan du gissar

Tre verktyg svarar på "varför funkar det inte" på sekunder istället för en lång
session:

| Verktyg | Vad det visar | Hur |
|---|---|---|
| **Djupdiagnostik** | env-vars, per-tabell authenticated-åtkomst (fångar 42501-grant-fel), migrations-status | `GET /api/admin/diagnostics/deep` (admin) |
| **Smoke-test** | hela API-ytan: vad 500:ar (krasch) vs är skyddat (401) | `python scripts/smoke_test.py [base_url]` |
| **Global felhanterare** | gör alla serverfel läsbara MED CORS i frontend | automatisk (`apps/api/main.py`) |

**Regel:** ser du ett fel i UI:t som inte är självförklarande — kör smoke-testet
mot `https://marketscan-api.vercel.app` och öppna djupdiagnostiken. Gissa inte.

### Vanliga felkoder och vad de betyder
| Symptom | Trolig orsak | Åtgärd |
|---|---|---|
| `permission denied for table X` / kod `42501` | saknad GRANT till rollen | kör `023_grant_table_privileges.sql` |
| "Nätverksfel" i frontend | servern svarade utan CORS (ohanterat fel) ELLER fel origin | global handler fixar CORS; kolla att `API_BASE` är absolut |
| `relation "X" does not exist` / `42P01` | migration ej körd | kör migrationen; se diagnostiken |
| 422 från ett endpoint | request-body matchar inte schemat | jämför frontend-payload mot Pydantic-modellen |
| Endpoint 500:ar bara med giltig token | handler-logiken (DB) felar, ej auth | felmeddelandet visar nu typen; kolla loggar |

---

## 2. Arkitektur i ett andetag

```
Browser ──absolut fetch (CORS)──> marketscan-api.vercel.app   (FastAPI, apps/api/)
   │                                       │
   └ web-…-hankkontakts.vercel.app         └ Supabase (Postgres + Auth + RLS)
     (Next.js, apps/web/)                    pipeline skriver via service_role
```

- **Två separata Vercel-projekt**, olika domäner. Frontend anropar API:t
  **direkt** på dess egen domän (`apps/web/lib/api.ts` → `API_BASE`). Ingen
  proxy (proxa inte same-origin — den vägen går genom Deployment Protection).
- **Tre Supabase-klient-nivåer** (`apps/api/dependencies.py`):
  `get_supabase` (anon, publik läsning) · `get_user_supabase` (anon + JWT → RLS
  per användare) · `get_supabase_admin` (service_role, kringgår RLS — endast
  bakom `require_admin`).

---

## 3. Bygga en ny endpoint / router

Kopiera **`apps/api/routers/_TEMPLATE.py`** — den har alla konventioner inbyggda.
Registrera den i `apps/api/main.py` med `app.include_router(<feature>.router)`.

### Reglerna (och varför)
1. **`def`, inte `async def`**, när kroppen bara gör synkrona Supabase-anrop.
   FastAPI kör `def`-handlers i en threadpool; ett synkront anrop i `async def`
   blockerar event-loopen. Använd `async def` **endast** om du `await`:ar något.
2. **Användardata** → `Depends(get_current_user)` + `Depends(get_user_supabase)`.
   JWT:n vidarebefordras till PostgREST så RLS isolerar per användare.
3. **service_role** (`get_supabase_admin`) **endast** bakom `require_admin`.
4. **Wrappa DB-anrop** med `apps/api/core/db.py`-helpers (`db.run`, `db.rows`,
   `db.one_or_404`). De översätter råa DB-fel till läsbara HTTPExceptions med
   rätt statuskod — aldrig en CORS-lös 500.
5. **Sätt alltid `response_model`** så kontraktet är explicit och validerat.

### Ny tabell → ny migration (obligatoriskt mönster)
```sql
CREATE TABLE IF NOT EXISTS my_table ( ... user_id UUID REFERENCES auth.users(id) ... );
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "my_table_own" ON my_table FOR ALL
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON my_table TO authenticated;  -- 023 sätter default, men var explicit
```
> **Publik läs-tabell** (som `scan_results`/`smallcap_results`): `FOR SELECT
> USING (true)` + `GRANT SELECT ... TO anon`. **Backend-only tabell** (som
> `client_errors`): RLS på, ingen policy → endast service_role kommer åt.

Migrationer körs **manuellt** i Supabase SQL Editor (de auto-appliceras inte).
Efter att en ny tabell lagts till: lägg in den i `apps/api/core/diagnostics.py`
(`USER_TABLES`/`MIGRATION_MARKERS`) så diagnostiken täcker den.

---

## 4. Frontend-konventioner (`apps/web/`)

- All API-åtkomst går genom **`lib/api.ts`** (`api<T>(path, init)`). Lägg inte
  råa `fetch("/api/...")` någon annanstans — då tappar du JWT, timeout och
  felhantering.
- `API_BASE` använder `||` (inte `??`) med absolut default → anropar API-domänen
  direkt. Sätt aldrig en tom `NEXT_PUBLIC_API_URL`.
- Nya datahämtningar: lägg en hook i `hooks/` (TanStack Query) — inte fetch i
  komponenten.

---

## 5. Säkerhetschecklista (kör vid varje ny feature)
- [ ] Användar-endpoints har `get_current_user`; admin-endpoints har `require_admin`.
- [ ] Ingen `get_supabase_admin` utan `require_admin`.
- [ ] Ny tabell: RLS på + policy + GRANT (se §3).
- [ ] Inga secrets med `NEXT_PUBLIC_`-prefix (de hamnar i klient-bundeln).
- [ ] Dyra externa anrop (LLM) bakom auth och/eller rate-limit.
- [ ] Användarinput till PostgREST-filter saneras (`safe_search`).
- [ ] `python scripts/smoke_test.py` grön före deploy.

---

## 6. Verifiera lokalt innan commit
```bash
python -m py_compile apps/api/**/*.py            # syntax
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"  # import
python scripts/smoke_test.py http://localhost:8000   # API-yta (kräver lokal server)
cd apps/web && npx tsc --noEmit                  # frontend-typer
```
