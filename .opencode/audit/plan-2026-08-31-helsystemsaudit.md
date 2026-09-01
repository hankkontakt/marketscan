# MarketScan — Hel-systemsaudit & Fixplan (2026-08-31)

**Goal:** Eliminera alla verifierade fel/nedbrytningar i MarketScan (API, web, Supabase/migrationer, CI, backend_worker, verktyg, Codex-drift) i 4 vågor, med bevakade repo-invarianter, och lämna systemet grönt på GATE-API, GATE-WEB, GATE-CODEX och GATE-BW.

**Scope/boundaries (vad som INTE görs):**
- Ingen ny funktionalitet, inget stilbyte, inga UI-omdesigner (endast invariants- och standardbrott).
- Inga DB-mutationer utförs av build-agent mot produktions-DB. Migrationer 077/078 skrivs, men **applicering i Supabase är en manuell åtgärd av användaren** — och en nödvändig gate mellan Våg 0 och Våg 1.
- Ingen Vercel-deploy/CI-körning automatiskt. Deploy görs endast när användaren begär det.
- Inga refaktorer bortom de som krävs av fynden (t.ex. ingen ERC-pure-python-port nu; se V3-5 som frivillig/efterföljande).

**Assumptions (nummererade; varje riskabelt antagande märkt):**
1. `portfolio_holdings`-tabellen finns INTE i `supabase/migrations/` (grep 0 träffar, verifierad) — men dess existens i **live-DB** är `not verified`. Build-agenten måste kolla `\d portfolio_holdings` (eller `information_schema.tables`) i live-Supabase FÖRE V1-4: finns den → adaptera (0), finns inte → skapa i 077 (planens primärväg).
2. Migration 077 är ännu inte applicerad i prod (senaste är 076 per filnamn; appliceringsstatus `not verified`).
3. Vilken Postgres-roll som kör migrationer manuellt påverkar om `ALTER DEFAULT PRIVILEGES` i 077 träffar framtida tabeller — `not verified`; planen ändrar därför 023:s default-privileges till SELECT-only MEN lägger även en Codex-regel (05_DATABASE_SCHEMA.md) om att varje ny tabellmigration måste `ENABLE ROW LEVEL SECURITY`.
4. `profile.py:105` (delete_account med sb_admin) — admin-status `not verified`; koden gör inga `require_admin`-kontroller i rutten. Behandlas som invariantbrott (V1-4).
5. `strategy_backtester.yml` kör köade backtests från `strategy_runs`-tabellen (antagande baserat på att workflown finns och kör `backend_worker.strategy_backtester`); kökvitto `not verified` — build-agenten verifierar i V0-2.
6. Exakta CLI-argument för `python -m backend_worker.fundamentals_fetcher` (rapporterad main-lack, `__main__`-block rad 297-320) — `not verified`; byggagenten läser rad 295-320 före V3-2.
7. Tester i `backend_worker/tests` (29 testfiler, verifierad via glob) kör grönt på Python 3.12 efter V3-2-byte; cpython-pycache visar 3.13 — `not verified`, verifieras i V3-2.

**Dependencies (task-ordning):**
- Våg 0 → (MIGRATION 077 APPLICERAD I PROD — manuell gate) → Våg 1 → Våg 2 → Våg 3.
- Intra-våg: V0-3 (migration 077) och dess prod-applicering FÖRE V0-1:s request_id-deploy (client_errors-anon) och FÖRE alla user-JWT-byten i V1-1/V1-4. V1-8 (doc-drift) FÖRE V2-4 (skärpning av verify_codex). V3-1 (index 078) före V1-3:s admin-verifiering vid risk.
- Codex-synk-in-place: varje task som rör kod uppdaterar berörd `docs/codex/*.md` i samma commit (Ground Truth-regeln).

**Downstream consumers (måste fungera efter ändringarna):**
- Web: `lib/api.ts` + hooks `useAICompare`/`useDailyCoach` etc. mot ändrade ai-endpoints; `VerdictHeader.tsx`/`useStock.ts` mot `price-history`; `KalenderView` mot `/calendar/earnings|dividends`; `PortfolioBuilderView.tsx` mot `/portfolio/construct` (501-fallback); `ScreenerView`/`ResultTable` mot screener-svar (tier/signal — oförändrade värden efter port); `useCompare`-typer.
- API-klienter: `scripts/smoke_test.py` (utökas V2-4), admin-diagnostics (`/api/admin/diagnostics/deep`), `request_id.py`-konsumenten `/api/debug/client-error` (web `lib/tracking.ts`).
- CI/backend: `orchestrator.yml`-mönster (pipeline.yml härmar), `digest_mailer.py` via `email/sender.py` (RESEND_FROM), `strategy_runs`-kötning via `strategy_backtester.yml`.
- DB/schema: `023`-grants, `036/037` (tracking anon), `022` (fund_holdings policy existerar `022:21-27`), `018:44-48` (watchlist policy existerar), `003` (ai_cache — får RLS+GRANT i 077), `035` (feedback-adminpolicy korrigeras).
- Docs/verktyg: `verify_codex.py` (skärps V2-4), `04_API_ARCHITECTURE.md` m.fl. (V1-8).

**Risks/fallback:**
1. **Live-DB-drift vs migrations** (portfolio_holdings-existens, company_profiles.isin från 029, vilka GRANTs som faktiskt applicerats) — ingen gate täcker detta. Beslut: build-agenten gör en read-only checklista mot live-Supabase FÖRE V0-3/V1-4 och skriver utfallet i tasken; vid osäkerhet behålls service_role-läsning i rebalancer tills 077 applicerats (dokumenterad intermittent).
2. **Deploy-race migration↔Vercel** — manuell SQL krävs; "077 applicerad i prod"-kvitto = explicit gate mellan våg 0 och våg 1 (byggagenten stoppar våg 1 tills kvitto).
3. **Tyst funktionsförlust efter numpy/scipy-borttagning** (construct/barbell/stress_test → 501 eller guarded fallback): GATE-API fångar import-krash, inte 501-regressioner → V2-4 lägger smoke-grupp för 501-patient + web-fallback i PortfolioBuilderView.
4. **Spam-vektor** (client_errors anon-INSERT): CHECK-längdgränser + trim i request_id.py + rate-limit behålls.
5. **022/018-policys** får inte tas bort: fund_holdings policy `022:21-27` (via portfolio-ägande) och watchlist `018:44-48` bekräftade.

**Consultations (faktiskt utförda):**
- `explore` ×4: apps/api (30 routers + 18 core), supabase+migrations/CI (76 migrationer + 30 workflows), backend_worker+scripts+docs-drift, apps/web (omstart).
- `explore` verifieringsreviews ×3: API-rapport (23/23 CONFIRMED, 1 ADJUSTED, +5 nya), DB/CI-rapport (16 fynd: 13 CONFIRMED, 2 ADJUSTED, 2 REJECTED, +5 nya), backend+docs-rapport (16 fynd: 14 CONFIRMED, 2 ADJUSTED, 1 REJECTED, +5 nya).
- `advisor` ×2: arkitektur-/riskbeslut (PROCEED med revisioner) och hela planutkastet (REVISE — 5 korrigeringar, alla inkorporerade).
- `planer` ×1: konsolidering till 22 atomiska tasks (vågor/ägarskap/verifiering).

---

## FYNDINVENTARIUM (alla verifierade fel, med fix-ankarpunkt)

### P0 — blockerare (måste bort före allt annat)

| # | Fynd (\<fil\>:line, verify-status) | Fix i task |
|---|---|---|
| 1 | `apps/api/routers/tracking.py:26` + `apps/api/core/request_id.py:57-62` — service_role-klient på HELT publik endpoint (track_events, capture_client_error). CONFIRMED ×2 | V0-1 |
| 2 | backend_worker-import i apps/api: `rebalancer.py:13`, `forensic_audit.py:15`, `screener.py:88-90` (hot-loop), `strategy_lab.py:256` (bg-task). CONFIRMED ×4 | V0-2 |
| 3 | `apps/api/core/portfolio_construction.py:14-15` numpy/scipy top-level, importerad via `strategy_lab.py:21` → app-start-krasch på Vercel (ingen av dem i `apps/api/requirements.txt`). CONFIRMED. Plus `strategy_lab.py:21`-modulimporten i sig = krasch om numpy bort (advisor#2-P0). | V0-2 |
| 4 | RLS-hål: `company_profiles` (026) + `alpha_candidates` (076) utan RLS; `023:57-58` ALTER DEFAULT PRIVILEGES ger authenticated full CRUD; `company_profiles.yml:57-70` skapar STALE duplikattabell (utan isin från 029) utan RLS. CONFIRMED | V0-3 |
| 5 | `.github/workflows/pipeline.yml:33,45,61,87-89` — trasig: `PYTHONPATH marketscan:stock-scanner`, `-m marketscan.backend_worker...` (ModuleNotFoundError) och saknar stock-scanner-krav. `score_tracker.yml:23-25` saknar `schedule` i if. CONFIRMED | V0-4 |
| 6 | `apps/web/app/(auth)/auth/callback/route.ts:14` — `setAll() {}` tom → session-sättning uteblir; `:20` skickar hela URL:en som auth_code (`node_modules/@supabase/auth-js:1523`). CONFIRMED | V0-5 |

### P1 — invarianter + datakorrekthet

| # | Fynd | Fix |
|---|---|---|
| 7 | service_role utan require_admin: `ai.py:151,306,400,614,650,681`; `portfolio.py:81`; `watchlist.py:26`; `paper_trading_router.py:14,63,151`; `profile.py:105`; `rebalancer.py:32,68`; `forensic_audit.py:48`. CONFIRMED | V1-1/V1-4/V0-2 |
| 8 | async def med synkrona Supabase-anrop: `stocks.py:103,187,394,495`; `snapshots.py:12,73`; `rebalancer.py:29,66`; `calendar.py:96,163`; `insider.py:41`; `admin.py:408`; `request_id.py:57`; `core/ai_cache.py:10,52`. CONFIRMED | V1-1..V1-4 |
| 9 | Sync httpx i async: `ai.py:748,764`; `core/llm_client.py:296` (sync providers). CONFIRMED | V1-1 |
| 10 | Lazy tunga importer (ej i requirements): `portfolio.py:728` numpy; `core/prices.py:118` pandas; `stocks.py:457` yfinance; `markets.py:176` yfinance; `ml_performance.py:114` scipy. CONFIRMED | V1-2 |
| 11 | Trasiga DB-anrop: `rebalancer.py:41,72` (portfolio_holdings saknas); `rebalancer.py:48,74` (fund_holdings har ingen `user_id` → alltid tom); `admin.py:584` (ai_cache delete `.neq("id",…)` → 500). CONFIRMED | V1-3/V1-4 |
| 12 | Oautentiserade: `portfolio.py:401` import_preview; `strategy_lab.py:503,528`; `ai.py:498` GET /journal/{ticker}. CONFIRMED | V1-1/V1-4 |
| 13 | Frontend P1: `KalenderView.tsx:119-120` tidszonsbugg (toISOString); `StockView.tsx:641,648,665` mojibake. CONFIRMED | V1-7 |
| 14 | Backend data: `master_rank.py:791` piotroski_f-None TypeError (SELECT 564-569 utan IS NOT NULL); `run_alpha_discovery.py:76-117,229` fabrikat skrivs till alpha_candidates; `insider_cluster.py:116,298` f-string-SQL; `qmj_scores.py:824` excluded-räkning fel, `:754` hårdkodad april; `news_stream_cision.py:139` set-trim; `master_rank.py:920` warning_flags död. CONFIRMED (1 ADJUSTED: insider_cluster 132/312 ej interpolering) | V1-5 |
| 15 | `core.daily_pipeline` finns EJ men importeras: `entrypoint.py:144,284,291`; `ml_trainer.py:113`; `sector_rotation.py:17`; `entrypoint.py:293-302` död fallback. `requirements.txt:15` kommentar → icke-existerande news_fetcher.py. CONFIRMED | V1-6 |
| 16 | Doc-drift 7 kapitel: `04:69-95` router-katalog inaktuell; `02:75,78-80,94` funktioner/load_data.py finns ej; `01:30,32` tier-trösklar (kod: TIER_T2=65.0/TIER_T3=50.0, min_blocks 3/4 — master_rank.py:44-45,446); `06:41-42`; `07:83-85,98`; `03:71,83-84` (validate_grounding finns ej). CONFIRMED | V1-8 |
| 17 | CI: `digest.yml:41` EMAIL_FROM vs `email/sender.py:16` RESEND_FROM; `orchestrator.yml:222` portfolio_snapshot-modul finns ej; `orchestrator.yml:118-121` psql ON_ERROR_STOP=0+grep sväljer fel (revision: behåll 0 i bootstrap + post-verify); `insider_trades.yml:58-61` duplicerad index (049:16-17). CONFIRMED | V0-4 |
| 18 | `035_user_feedback.sql:25-28` admin-policy läser JWT `app_metadata.role`; rollen bor i `profiles.role` (security.py:127-158, profiles.role 001:74). CONFIRMED | V0-3 |
| 19 | `verify_codex.py:40` PATH_REGEX matchar ej parenteser; `:130-149` route-drift WARN-only (exit 0); `:56-59` linjebudget-WARN fäller gate (exit 1). CONFIRMED | V2-4 |
| 20 | `smoke_test.py:38-72` saknar ~13 endpoint-grupper; `:80` hårdkodad fel Origin. CONFIRMED (=heltäckande lista erhölls) | V2-4 |

### P2 (urval, komplett lista i task-texterna)

| Fynd (fil:line, status) | Fix |
|---|---|
| `paper_trading_router.py:61` body:dict → pydantic (float-krasch); `profile.py:192` upsert+.eq no-op; `llm_client.py:350` delad list-referens; `llm_client.py:87,102` /tmp-budget; `ml_performance.py:95` /app-pad; `duckdb_r2.py:21-30` secrets i SQL; `main.py:49,70` CORS-regex ×2 hårdkodad; `markets.py:159-208` död _fetch_indices_yfinance + duplicerad _YAHOO_INDEX_SYMBOLS; `stocks.py:822-837` syntetisk mock-benchmark; `admin.py` m.fl. except-pass + läckande felmeddelanden (lista i V3-5). Alla CONFIRMED | V1-2/V1-3/V2-1/V3-5 |
| Web P2 (alla CONFIRMED): emojis `PortfoljView.tsx:188`, `AiPrestandaView.tsx:158`, `StrategiLabView.tsx:420`, `lib/themes.ts:19-84`+`ThemeCard.tsx:175`; fragment-utan-key `InsiderRadarView.tsx:344-355`, `SignalAnalyticsView.tsx:296-307`; tysta catches `ScreenerView.tsx:106-107`, `JamforView.tsx:220`; any `useCompare.ts:64,78-80`; kollision `useStock.ts:26` vs `useAlerts.ts:66`; fetch-i-useEffect `JamforView.tsx:54-88,207-222`, `CommandPalette.tsx:68-85`, `KalenderView.tsx:137-178`; dead state `PortfoljView.tsx:52,86,89`; död kod `useAlerts.ts`, `useCompare.ts (useStockDetail)`; `labels.ts:17-18`; `StrategiLabView.tsx:140` SVAG; `StockView.tsx:299`+`ScreenerView.tsx:35` full-listor; `ImportModal.tsx:449` reload | V2-2/V2-3 |
| Migrations-P3: saknade index `paper_trades.portfolio_id` (006), `portfolio_optimizations.user_id` (009), `pipeline_runs.started_at` (001:126-136), `user_ticker_requests.added_to_universe` (017) | V3-1 |
| CI-P3: python 3.11×6 (digest:30, risk_analysis:34, score_tracker:36, signal_analytics:24, smart_alerts:32, strategy_backtester:29); cron-kollisioner bekräftade: company_profiles:16==pipeline:17, signal_analytics:9==ml_retrain:16, alpha_discovery:11==doc_intelligence:11 (REJECTED: master_rank:16 vs watchlist_alerts:11 = bara fredagar; qmj_regime:12 vs earnings_surprise:12 = bara när 8:e är måndag); `master_rank.yml:57-62` placeholder | V3-2 |

### P3 (se V3-3/V3-4/V3-5: web-prestanda/typer, delade libs, error-hygiene-svep)
`ResultTable.tsx:38-42,151,315`; `useTheme.ts:24`; `package.json:34,54`; `PriceChart.tsx:114`; `OversiktView.tsx:105`; `VerdictHeader.tsx:29-34` vs `useStock.ts:17-24`; `MewsStrip.tsx:69`; `MangdubblareView.tsx:19`; `FilterRail.tsx:35-39`; `StockView.tsx:57-58`; admin-JWT-dekod ×5; hårdkodade Tailwind-färger ×9-filer; ZBar ×2; null-dash-inkonsistens; `MultiFactorRadar.tsx:74`; `RebalanceView.tsx:120`; `admin.py:358` psycopg2-guard; `reranker.py:29` guard (bekräftas intakt). Alla CONFIRMED (P3).

---

## Genomförande

**Gates (återanvänds i varje task):**
- **GATE-API:** `PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"` + `python scripts/smoke_test.py` (smoke lokalt mot dev-API)
- **GATE-WEB:** `cd apps/web && npx tsc --noEmit && npx eslint . && npx vitest run`
- **GATE-CODEX:** `python scripts/verify_codex.py`
- **GATE-BW:** `python -m pytest backend_worker/tests -q`

---

### Task V0-1: Ta bort service_role från publika endpoints (tracking + client-errors)

**Files:** Modify `apps/api/routers/tracking.py`, `apps/api/core/request_id.py`.
**Proof (verifyed):** `tracking.py:26` `sb: Client = Depends(get_supabase_admin)` (docstring "fully public"); `request_id.py:57-62` async def `capture_client_error` → `get_supabase_admin()`; `request_id.py:95` läcker `f"Error: {e}"`; RLS: `036:14-26` + `037:9-11` (tracking_events anon INSERT ✓); `018:128-140` (client_errors RLS utan policy, deny-by-default; rad 140-kommentar bekräftar).
**Interfaces:** Consumes: anropas från `lib/tracking.ts`-client (`/api/tracking/events`), `/api/debug/client-error`. Produces: inga nya symboler.
**Ändring:**
- [ ] `tracking.py`: `get_supabase_admin` → `get_supabase()` (anon). Rate-limit/validatorer oförändrade.
- [ ] `request_id.py`: `capture_client_error` sync `def`; service_role → anon-klient; **ny** policy för `client_errors` anon INSERT skapas i 077 (V0-3) med CHECK-längdgränser (≤4 000 tecken på meddelande) — här läggs trim + längd-guard i Python.
- [ ] Sanera `:95` läcka → logga internt, svara neutralt.
**Acceptance criteria:** `rg -n "get_supabase_admin" apps/api/routers/tracking.py apps/api/core/request_id.py` → 0 träffar; endpoint svarar 200 utan token efter 077; ingen intern-feltext till klient.
**Verification:** GATE-API; `curl -X POST` mot `/api/debug/client-error` (lokal dev) → 200. *Not run.*

### Task V0-2: Bryt alla backend_worker-imports + numpy/scipy i API-bundeln

**Files:** Modify `apps/api/routers/rebalancer.py`, `apps/api/routers/forensic_audit.py`, `apps/api/routers/screener.py`, `apps/api/routers/strategy_lab.py`, `apps/api/core/portfolio_construction.py`; Create `apps/api/core/rebalancer_engine.py`, `apps/api/core/master_rank_utils.py`.
**Proof:** `rebalancer.py:13`, `forensic_audit.py:15`, `screener.py:88-90`, `strategy_lab.py:21,256`; `portfolio_construction.py:14-15`; advisor#1: `strategy_backtester.py:26-28` (numpy+psycopg2 top-level → INTE portbar); `master_rank.py:35` numpy top-level → kopiera funktioner, importera ej modul; `rebalancer_engine.py:12-15` ren Python; `strategy_lab.py:249-262` befintlig DB-flag-fallback.
**Interfaces:** Consumes: `strategy_lab.py` (modul-import), `background_tasks`-registrering. Produces: `apps/api/core/rebalancer_engine.py` (`generate_rebalance_plan`, `calculate_portfolio_allocation` — portade), `apps/api/core/master_rank_utils.py` (`tier_of`, `signal_from_tier` + tier-konstanter 44-45).
**Ändring:**
- [ ] Porta rena funktioner (rebalancer_engine, tier_of/signal_from_tier) genom KOPIERING (inkl. konstanter), ingen modul-import.
- [ ] `rebalancer.py:13`-importen byts mot lokal core-modul; `async def`→`def` (:29,:66); tabellanropen korrigeras (V1-4 äger RLS/user-JWT-bytet — gör samtidigt: `portfolio_holdings` enligt planens primärväg, `fund_holdings` via `portfolio_id`-uppslag).
- [ ] `forensic_audit.py:15`: behåll LLM-steget i API via `deepseek_client`; PDF-parsning (pypdf, guarded `forensic_pdf_audit.py:46`) flyttas/fallback → tjänstefel 503 med tydligt budskap om inte tillgängligt; `sb_admin`→user-klient (:48).
- [ ] `screener.py:88-90`: importen flyttas ur loopen till toppen mot `master_rank_utils`; värden identiska (verifiera mot original via enhetstest jämför 3 case).
- [ ] `strategy_lab.py:21`: `portfolio_construction`-importen → lazy/guarded (try/except ImportError med logg) så app-start klarar sig utan numpy/scipy.
- [ ] `strategy_lab.py:256`: ta bort in-process `_run_backtest`-importen; köet kvar (`strategy_runs`-insert), körning sker via `strategy_backtester.yml` CI (verifiera i assumption 5).
- [ ] `portfolio_construction.py:14-15`: numpy/scipy → import innanför funktioner med tydlig fallback; endpoints `/api/portfolio/construct`, `strategy_lab`-barbell/stress-test: returnerar 501 med tydligt meddelande om deps saknas (feature-flag `ENABLE_HEAVY_OPT`); `portfolio.py:728` import numpy → try-guard.
- [ ] `apps/api/requirements.txt`: ingen ny dependency läggs till.
**Acceptance criteria:** `rg -n "backend_worker" apps/api` → 0 träffar; `rg -n "import numpy|import pandas|import scipy|import yfinance" apps/api` → endast guarded/lazy (med ImportError-handling); GATE-API passerar i miljö UTAN numpy/scipy.
**Verification:** GATE-API (körs utan numpy/scipy installerade); API-importtest `PYTHONPATH=. python -c "from apps.api.main import app"`. *Not run.*

### Task V0-3: RLS-migration 077 + CI-schema-reparation (company_profiles)

**Files:** Create `supabase/migrations/077_rls_security_hardening.sql`; Modify `supabase/migrations/023_grant_table_privileges.sql`, `supabase/migrations/035_user_feedback.sql`, `.github/workflows/company_profiles.yml`, `docs/codex/05_DATABASE_SCHEMA.md`.
**Proof:** `023:28,45,50,57-58` (default-privileges full CRUD; REVOKE-loop täcker endast scan_results/ai_cache/pipeline_runs), `026:13-30` ("No RLS needed"), `076:4-28` (ingen RLS), `022:21-27` (fund_holdings policy finns ✓), `018:44-48` (watchlist policy finns ✓), `003:1-7` (ai_cache: cache_key PK, ingen id), `018:137-140` (client_errors), `035:25-28` vs `security.py:127-158`.
**Interfaces:** Consumes: alla framtida user-JWT-byten (V1-1, V1-4) kräver dessa policys/GRANTs. Produces: tabell `portfolio_holdings` (om ej live), RLS-policys, GRANTs.
**Ändring (077 innehåll):**
- [ ] `ALTER TABLE company_profiles ENABLE ROW LEVEL SECURITY;` + policy: `SELECT USING (true)` för anon+authenticated (publik läsning, motsvarande scan_results), skrivning via service_role (bypass).
- [ ] Dito `alpha_candidates`.
- [ ] `client_errors`: `CREATE POLICY client_errors_anon_insert ON client_errors FOR INSERT TO anon WITH CHECK (char_length(message::text) <= 4000);` + `GRANT INSERT ON client_errors TO anon;` (023:32 gav anon endast SELECT — GRANT krävs).
- [ ] `ai_cache`: `ALTER TABLE ai_cache ENABLE ROW LEVEL SECURITY;` + policies SELECT/INSERT/DELETE FOR authenticated (delad global cache — alla ser alla) + `GRANT SELECT, INSERT, DELETE ON ai_cache TO authenticated;` (023:50 REVOKE:ade I/U/D — GRANT krävs för att user-JWT-cache ska fungera, annars 42501).
- [ ] `portfolio_holdings` (primärväg): `CREATE TABLE IF NOT EXISTS portfolio_holdings(...)` — portfolio_id (FK portfolios), user_id, isin, name, shares, cost_basis, current_price, purchase_date, added_at, updated_at; `ENABLE ROW LEVEL SECURITY`; policy `FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id)` + SELECT/UPDATE/DELETE `USING (auth.uid() = user_id)`; GRANT SELECT/INSERT/UPDATE/DELETE TO authenticated. (`not verified` live-existens — om tabellen redan finns, hoppa skapande och ALTER/RLS/policy endast.)
- [ ] `023:57-58`: `ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES TO authenticated` (SELECT-only för framtida tabeller) — med kommentar om att ändringen gäller framtida tabeller från samma roll.
- [ ] `035:25-28`: policy → `EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')`.
- [ ] `company_profiles.yml`: radera `CREATE TABLE IF NOT EXISTS company_profiles` + duplicerade index (`:57-70,71-74`); behåll fetch-steget; kommentar → "schema i migration 026 (isa-fält via 029)".
- [ ] Codex 05: lägg regel "varje ny tabellmigration MÅSTE ENABLE ROW LEVEL SECURITY + minst en policy" (möter 023:s systemsutrymme).
**Acceptance criteria:** 077 idempotent (IF NOT EXISTS/DROP IF EXISTS); `company_profiles`/`alpha_candidates`/`ai_cache` `relrowsecurity = t`; `rg -n "CREATE TABLE" .github/workflows/` → 0; feedback-adminpolicy matchar `security.py`-modellen.
**Verification (post-apply, manuell):** `SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('company_profiles','alpha_candidates','ai_cache')` → alla t; `SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_name IN ('client_errors','ai_cache')` → anon INSERT / authenticated I+D. *Not run — kräver live-DB.*

### Task V0-4: Reparera CI-workflows (pipeline + övriga)

**Files:** Modify `.github/workflows/pipeline.yml`, `.github/workflows/score_tracker.yml`, `.github/workflows/digest.yml`, `.github/workflows/orchestrator.yml`, `.github/workflows/insider_trades.yml`.
**Proof:** `pipeline.yml:33,45,61,87-89`; `entrypoint.py:276` (absolut import `from backend_worker.db_loader`), `entrypoint.py:401` (choices); `orchestrator.yml:46,85-90,118-121,159,222`; `score_tracker.yml:12-13,23-25`; `risk_analysis.yml:20-23` (korrekt mönster); `digest.yml:41` vs `backend_worker/email/sender.py:16`; `insider_trades.yml:58-61` vs `049:16-17`.
**Interfaces:** Consumes: `backend_worker.pipeline.entrypoint` (mönster), `email/sender.py` (RESEND_FROM), `fundamentals`-deps. Produces: inga.
**Ändring:**
- [ ] `pipeline.yml`: checkout till repo-root (standard), `PYTHONPATH: ".:stock-scanner"` (orchestrator-mönstret), `python -m backend_worker.pipeline.entrypoint` (+ mode-argument per `:401`-choices: `morning/evening/weekly/manual/smallcap/targeted` — uppdatera hand-off-beskrivningen av `:21` så den matchar kod), installera BÅDA requirements (`backend_worker/requirements.txt` + stock-scanner-requirements — exakt ref från `orchestrator.yml:85-90`), cron `:17` flyttas (krockar `company_profiles.yml:16` `0 7 * * 0`).
- [ ] `score_tracker.yml`: lägg `github.event_name == 'schedule'` i jobbets if.
- [ ] `digest.yml`: `EMAIL_FROM` → `RESEND_FROM`.
- [ ] `orchestrator.yml:222`: ta bort `python -m backend_worker.portfolio_snapshot`-steget (modul saknas); `:118-121`: behåll `ON_ERROR_STOP=0` i bootstrap (migrations idempotens `not verified` — advisor#1-revision) men lägg efterkörnings-verify: `psql -f` + `\dt`-närvaro-check + tydlig `::error`-logg, och `continue-on-error` tas bort för verify-steget.
- [ ] `insider_trades.yml:58-61`: radera duplicerat UNIQUE INDEX (049 äger det).
**Acceptance criteria:** alla workflow-YAML validerar; inga referenser till icke-existerande moduler; score_tracker-cron faktiskt träffar jobbet; ingen `CREATE TABLE`/index-dupe i workflows.
**Verification:** YAML-parse `python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"` → ok; `rg -n "marketscan\.backend_worker|EMAIL_FROM|portfolio_snapshot" .github/workflows/` → 0. *Not run.*

### Task V0-5: Fixa auth-callback (setAll + code-parameter)

**Files:** Modify `apps/web/app/(auth)/auth/callback/route.ts`.
**Proof:** `route.ts:14` `setAll() {},`; `:20` `exchangeCodeForSession(request.url)`; @supabase/ssr-mönster (advisor#1: cookiesToSet → `NextResponse.redirect(...).cookies.set(...)`; ingen `cookies()` från next/headers krävs; `node_modules/@supabase/auth-js:1523` sänder auth_code verbatim → byt till `request.nextUrl.searchParams.get('code')`).
**Interfaces:** Consumes: Supabase-klient (anon key), redirect-flöde till `/oversikt` eller `/login`. Produces: inga nya symboler.
**Ändring:**
- [ ] Samla `cookiesToSet`-loop → applicera på den `NextResponse` som skapas (`response.cookies.set(name, value, options)`), exakt per @supabase/ssr-dokumentation.
- [ ] `exchangeCodeForSession(await request.nextUrl.searchParams.get("code") ?? "")` med 400-fallback om code saknas.
- [ ] Svara med `no-store`/no-cache-headers enligt mönster.
**Acceptance criteria:** E-postbekräftelse/OAuth-callback fullbordar inloggning; session-cookien satt; `/oversikt` nås inloggad; `npx tsc --noEmit` rent.
**Verification:** GATE-WEB + manuellt login-flöde mot dev-Supabase. *Not run.*

> **GATE mellan våg 0 och våg 1:** 077 applicerad i prod (kvitto från `pg_class`-/`role_table_grants`-koll ovan). Våg 1 startar INTE förrän kvittot finns.

---

### Task V1-1: ai.py + llm_client.py — service_role, async, sync-httpx, journal-auth

**Files:** Modify `apps/api/routers/ai.py`, `apps/api/core/llm_client.py`.
**Proof:** `ai.py:151,306,400,614,650,681` (sb_admin utan require_admin), `:498` (journal utan auth — ADJUSTED: GET ej POST), `:737,748,754,764` (sync providers i async), `llm_client.py:113,135` (sync httpx), `:244,296` (loop sync result), `:350` (delad lista), `:87,102` (/tmp-budget), `ai_cache.py:10,52` (sync från async-anrop).
**Interfaces:** Consumes: web-hooks `useAICompare`, `useDailyCoach`, `useExplainStock` etc. mot samma paths. Produces: inga sökvägsändringar.
**Ändring:**
- [ ] `sb_admin`→`get_user_supabase` på :151,:306,:400,:614,:650,:681 (efter 077).
- [ ] `async def`→`def` där kroppen är helt synkron (:71,:147,:306,:355,:397,:609,:645,:677).
- [ ] Sync providers (`_call_gemini_complete`/`_call_deepseek_complete`): anrop via `asyncio.to_thread` i `llm_complete` (:296) och i `_call_ai`/`_call_ai_chat` (:748,:764).
- [ ] `GET /journal/{ticker}` (:498): lägg `get_current_user`.
- [ ] `llm_embed` (:350): `[[0.0] * 768 for _ in range(len(texts))]`.
- [ ] `ai_cache.py`: vid aflänkning från async-endpoints → `asyncio.to_thread`, eller gör async-cache med `run_in_executor`; `/tmp`-budgetfil — flytta budget till in-minne/lås-matchning (P2, acceptera ephemeral med dokumentationsnotis om serverless).
**Acceptance criteria:** `rg -n "get_supabase_admin" apps/api/routers/ai.py` → 0; journal kräver auth; inga sync-Supabase/HTTP-anrop i async-kontext; GATE-API.
**Verification:** GATE-API; `rg -n "await httpx|\.execute\(\)" apps/api/routers/ai.py` → endast async-klienter. *Not run.*

### Task V1-2: stocks/markets/ml_performance/prices — async→def, guarded lazy imports, mock-borttag

**Files:** Modify `apps/api/routers/stocks.py`, `apps/api/routers/markets.py`, `apps/api/routers/ml_performance.py`, `apps/api/core/prices.py`.
**Proof:** `stocks.py:103,187,394,495` (async+sync execute), `:457` yfinance, `:822-837` mock-benchmark (`is_synthetic`), `:1036` läckande feltext; `markets.py:159-208` död kod + `_YAHOO_INDEX_SYMBOLS`-duplikat `:205-208` (divergera från dödkod-listan: yahoo-listan saknar ^AXJO/^BSESN/SSEC), `:176` yfinance; `ml_performance.py:114` scipy (`:110` finns manuell fallback — behåll), `:95` `/app/stock-scanner-fix`; `core/prices.py:118` pandas.
**Interfaces:** Consumes: web `useStock`, `VerdictHeader`, jämför-vy, market-intel-kort. Produces: inga.
**Ändring:**
- [ ] `async def`→`def` på de fyra stocks-handlers (+ ev. andra I fynden).
- [ ] Alla tunga lazy-imports → `try/except ImportError` med tydlig logg + fallback (yfinance: 502 "data-källa otillgänglig"; pandas: manuell fallback där görbart).
- [ ] Radera `_fetch_indices_yfinance` + duplicerad `_YAHOO_INDEX_SYMBOLS`; behåll en källa.
- [ ] Radera `_generate_mock_benchmark_candles`/`is_synthetic`-produktionsfallback → 404/tydligt fel.
- [ ] `ml_performance.py:95` → `os.environ.get("SCANNER_PATH", "/tmp/stock-scanner-ext")` scoped och dokumenterad (Vercel-safe default).
- [ ] Sanera läckande feltext (stocks.py:1036, market_intel.py-serien + fler enligt V3-5-listan).
**Acceptance criteria:** GATE-API; `rg -n "_fetch_indices_yfinance|_generate_mock_benchmark|is_synthetic" apps/api` → 0; inga oskyddade tunga imports.
**Verification:** GATE-API. *Not run.*

### Task V1-3: snapshots/calendar/insider/admin/ai_cache — async→def, admin-bug, error-hygiene

**Files:** Modify `apps/api/routers/snapshots.py`, `apps/api/routers/calendar.py`, `apps/api/routers/insider.py`, `apps/api/routers/admin.py`, `apps/api/core/ai_cache.py`.
**Proof:** `snapshots.py:12,73`; `calendar.py:96,163` (sync kropp; men `:20,:140,:210` AsyncClient — BEHÅLL async där); `insider.py:41`; `admin.py:408` (sync execute :428), `:584` (`.neq("id",...)` mot ai_cache utan id → 500; korrekt mönster `ai_cache.py:82` `.neq("cache_key","")`), `:351-352` except pass, `:262,296,530,587,723-725` läckor, `:358` psycopg2 guarded; `ai_cache.py:10,52`.
**Interfaces:** Consumes: admin-UI (`/api/admin/*`), kalender-vy, insider-radar. Produces: inga.
**Ändring:**
- [ ] async→def för de synkron-kroppiga handlers (listas ovan); om `httpx.AsyncClient` används behålls async.
- [ ] `admin.py:584`: `delete().neq("cache_key", "")`-mönster.
- [ ] Error-hygiene: `except Exception: pass` → `logger.exception`/`logger.warning`; felmeddelanden → generiska, detaljer i logg.
- [ ] `ai_cache.py`-anropare fixas i V1-1/V0-2 (to_thread).
**Acceptance criteria:** GATE-API; `rg -n "except Exception" apps/api/routers/admin.py` → inga tysta; clear-cache-admin 200.
**Verification:** GATE-API; manuell `POST /api/admin/cache/clear` (lokal dev). *Not run.*

### Task V1-4: portfolio/strategy_lab/watchlist/paper_trading/profile/rebalancer — auth + user-JWT + pydantic

**Files:** Modify `apps/api/routers/portfolio.py`, `apps/api/routers/strategy_lab.py`, `apps/api/routers/watchlist.py`, `apps/api/routers/paper_trading_router.py`, `apps/api/routers/profile.py`, `apps/api/routers/rebalancer.py`; (077 äger ev. tabellskapandet).
**Proof:** `portfolio.py:401` (import_preview utan auth), `:81` (sb_admin), `:489,553` läckor, `:728` numpy-guard; `strategy_lab.py:503,528` (utan auth), `:21` (redan V0-2); `watchlist.py:26`; `paper_trading_router.py:14,63,151`, `:61` body:dict (float-krasch), `:74` (scan_results.price NULL förlitelse); `profile.py:105`, `:69` läcka, `:192` upsert+.eq no-op; `rebalancer.py:29,32,41,48,66,68,74` (async, sb_admin, portfolio_holdings, fund_holdings-user_id-restriktion).
**Interfaces:** Consumes: web-portfolio-vy, watchlist-toggle (3 ställen), paper-trading-vy, rebalance-vy, profil. Produces: (077) `portfolio_holdings`.
**Ändring:**
- [ ] `get_current_user` på `import_preview`, `optimize_barbell_portfolio`, `run_portfolio_stress_test`.
- [ ] `sb_admin`→`get_user_supabase` på alla listade (policys i 077/022/018 bekräftade).
- [ ] `rebalancer.py`: async→def; `portfolio_holdings`-läsning via ny tabell (V1-4 antar 077-applicerad; fallback: om live-schema saknas → dokumenterad logg + tom lista); `fund_holdings`-läsning via `user→portfolios.id→fund_holdings.portfolio_id`.
- [ ] `paper_trading_router.py`: pydantic-modell (shares: float ≥0, ticker: str pattern); `:74` → fetch pris från kolumn med fallback (t.ex. `last_price`) + guard.
- [ ] `profile.py:192`: ta bort no-op `.eq`.
- [ ] `portfolio.py:728`: numpy-guard (V0-2).
- [ ] Error-hygiene: portfolio.py:489,553; profile.py:69.
**Acceptance criteria:** `rg -n "get_supabase_admin" apps/api/routers/{portfolio,strategy_lab,watchlist,paper_trading_router,profile,rebalancer}.py` → 0 (endast admin.py, alerts.py:49, forensic_audit, ml_performance per plan); import_preview kräver auth; rebalance-planen läser korrekt data; paper-trade validerar med 422 på ogiltig input.
**Verification:** GATE-API; smoke (401 för import_preview utan token, 422 för paper-trade med "abc"-shares). *Not run.*

### Task V1-5: backend_worker dataintegritet

**Files:** Modify `backend_worker/master_rank.py`, `backend_worker/run_alpha_discovery.py`, `backend_worker/insider_cluster.py`, `backend_worker/qmj_scores.py`, `backend_worker/news_stream_cision.py`.
**Proof:** `master_rank.py:564-569,791` (+`44-45,446` i V0-2-porten), `:920`; `run_alpha_discovery.py:76-117,229`; `insider_cluster.py:116,298` (ADJUSTED: 132,312 ej interpolering); `qmj_scores.py:754,824`; `news_stream_cision.py:139`.
**Interfaces:** Consumes: `alpha_candidates`, `master_rank`, `scan_results`. Produces: inga sökvägsändringar.
**Ändring:**
- [ ] `master_rank.py`: None-guard på `piotroski_f` (och övriga möjliga None i ekvationen) + `IS NOT NULL`-filter i SELECT; `warning_flags` skrivs med faktiska flags (dokumenterad form) eller kolumnen tas bort från upsert.
- [ ] `run_alpha_discovery.py`: fabrikat (price 50.0, sharesOutstanding 50M, fejkad pressrelease/rating/HoldingChange/wyckoff) → ERSÄTT med riktiga datakällor; där data saknas → hoppa item + logga; skriv ALDRIG syntetiska poster till `alpha_candidates`.
- [ ] `insider_cluster.py`: parameterisera f-string-SQL (offsets), t.ex. `(SELECT $1::date)`.
- [ ] `qmj_scores.py:824`: korrekt formel (excluderade = `len(rows) - sum(alpha_rank is not None)`); `:754`: datumdriven flagga (april = regel i dokumenterad konstant/config).
- [ ] `news_stream_cision.py:139`: sortera hashar (tidsstämpel-spår) innan trim.
**Acceptance criteria:** GATE-BW; enhetstest för None-piotroski-fall; `rg` visar inga syntetiska `AnalystReportItem`-fabrikat i alpha-datan; inga f-string-SQL med datum i insider_cluster.
**Verification:** GATE-BW + respektive modul-smoke (t.ex. `python -m backend_worker.qmj_scores --help`). *Not run.*

### Task V1-6: entrypoint/ml_trainer/sector_rotation — core.daily_pipeline-importen + fallback-varv

**Files:** Modify `backend_worker/pipeline/entrypoint.py`, `backend_worker/ml_trainer.py`, `backend_worker/sector_rotation.py`, `backend_worker/requirements.txt`.
**Proof:** `entrypoint.py:144,284,291` (import av icke-existerande `core.daily_pipeline` — det ligger i stock-scanner), `:293-302` (fallback död; `parquet_files[0]` fångas men degraderar), `:401`; `ml_trainer.py:113`; `sector_rotation.py:17`; `requirements.txt:15`.
**Interfaces:** Consumes: `$PYTHONPATH`-beroende på stock-scanner. Produces: inga.
**Ändring:**
- [ ] `core.daily_pipeline`-importer → villkorade (`try/except ImportError` med dokumenterad logg + `SKIPPED: requires stock-scanner`) ELLER styrs av env `INCLUDE_EXTERNAL_PIPELINE=1`; inga tysta krascher.
- [ ] `entrypoint.py:293-302`: förenkla — använd `fallback or parquet_files[0]` med guard → tydligt fel (inte död kod).
- [ ] requirements-kommentar rättas (news_fetcher.py existerar ej → avlägsna/dokumentera stock-scanner-owned deps).
**Acceptance criteria:** `python -m backend_worker.pipeline.entrypoint --mode morning` UTAN stock-scanner ger tydligt skip/begränsat fel, inte ModuleNotFoundError; GATE-BW.
**Verification:** GATE-BW; `python -m backend_worker.pipeline.entrypoint --help`. *Not run.*

### Task V1-7: Frontend P1 — Kalender-tidszon + StockView-mojibake (+ P2-items i samma filer)

**Files:** Modify `apps/web/app/(app)/kalender/KalenderView.tsx`, `apps/web/app/(app)/aktie/[ticker]/StockView.tsx`.
**Proof:** `KalenderView.tsx:119-120`; `StockView.tsx:641,648,665` (mojibake: `FaktorÃ¶versikt`→Faktoröversikt, `DÃ¶lj detaljer`→Dölj detaljer, `â€"`→—), `:57-58` (useExperience ×2), `:299` (hela QMJ-listan per aktiesida); `KalenderView.tsx:137-178` (fetch-i-useEffect).
**Interfaces:** Consumes: `/calendar/earnings|dividends`, `/market-intel/qmj/rank`, `useExperience`. Produces: inga.
**Ändring:**
- [ ] KalenderView: bygg `YYYY-MM-DD` i lokal tz (date-fns `format`) istället för `toISOString().slice(0,10)`.
- [ ] StockView: rätta mojibake-tecken; `useExperience` 1×; `:299`-hela-listan-optimering (engångsmemo/query-param) — eller lämna som känd optimering med notering om den kräver ny endpoint (endpoint-lösning = utanför scope).
- [ ] KalenderView: fetch-i-useEffect → react-query-hook (med befintlig API-klient).
**Acceptance criteria:** GATE-WEB; `rg -n "Ã|â€" apps/web` → 0; månadsvy korrekt i UTC+1/+2; inga duplicate `useExperience`.
**Verification:** GATE-WEB. *Not run.*

### Task V1-8: Doc-drift — 7 codex-kapitel (Ground Truth-synk)

**Files:** Modify `docs/codex/04_API_ARCHITECTURE.md`, `docs/codex/02_DATA_PIPELINE.md`, `docs/codex/01_QUANT_MASTERRANK.md`, `docs/codex/06_FRONTEND_STATE_UX.md`, `docs/codex/07_PORTFOLIO_RISK.md`, `docs/codex/03_AI_RAG_SYNTHESIS.md` (+ `05_DATABASE_SCHEMA.md` — RLS-regel från V0-3).
**Proof:** `04:69-95` (alla avvikelser verifierade — alerts/smart_alerts/macro_regime/market_intel/ml_performance/paper_trading/risk/saved_screens/smallcap/snapshots/profile/calendar), `02:75,78-80,94`, `01:30,32` (kod vinner: TIER_T2=65.0/TIER_T3=50.0, min_blocks 3/4), `06:41-42`, `07:83-85,98`, `03:71,83-84`.
**Interfaces:** Consumes: `verify_codex.py` (skärps V2-4). Produces: inga kodändringar.
**Ändring:** Skriv om berörda kapitel mot FAKTISKA prefixes/paths/funktioner/trösklar (kod vinner över bok). V3-5-codex-regel: varje ny tabellmigration RLS.
**Acceptance criteria:** GATE-CODEX; `rg -n "run_morning|load_data\.py|validate_grounding|/api/smart-alerts|/api/insider/radar" docs/codex/` → 0; alla kapitel ≤500 rader.
**Verification:** GATE-CODEX. *Not run.*

---

### Task V2-1: duckdb-secrets + CORS-dedup

**Files:** Modify `apps/api/core/duckdb_r2.py`, `apps/api/main.py`.
**Proof:** `duckdb_r2.py:21-30`; `main.py:49,70`.
**Ändring:** (1) R2-hemligheter → inte i SQL-sträng (parameterisera/normalisera; säkerställ att de aldrig loggas). (2) CORS-regex: en konstant i settings och återanvänd i både felhanterings- och CORSMiddleware (ingen manuell dupe-synk).
**AC:** GATE-API; `rg -n "hankkontakts" apps/api/main.py` → 1.
**Verification:** GATE-API. *Not run.*

### Task V2-2: Web P2 — emojis → Lucide + UI-konsistens

**Files:** Modify `apps/web/app/(app)/portfolj/PortfoljView.tsx`, `apps/web/app/(app)/ai-prestanda/AiPrestandaView.tsx`, `apps/web/app/(app)/strategi-lab/StrategiLabView.tsx`, `apps/web/lib/themes.ts`, `apps/web/components/screener/ThemeCard.tsx`, `apps/web/components/charts/MultiFactorRadar.tsx`, `apps/web/components/portfolio/RebalanceView.tsx`.
**Proof (alla CONFIRMED):** `PortfoljView.tsx:188` (⚖️), `AiPrestandaView.tsx:158` (✅/⚠️), `StrategiLabView.tsx:420` (⚠), `themes.ts:19-84`, `ThemeCard.tsx:175`, `MultiFactorRadar.tsx:74`, `RebalanceView.tsx:120` (✓), `StrategiLabView.tsx:140` (SVAG), `:215` (native confirm), `PortfoljView.tsx:52,86,89` (dead state).
**Ändring:** emojis → Lucide; SVAG-option → korrekt värde (verifiera giltiga signalvärden i API); native confirm → bekräftelse-UI; dead state bort; `?`-tooltip → InfoTooltip.
**AC:** GATE-WEB; `rg -n "⚖|✅|⚠|✓|❌|" apps/web` → 0 (undantag dokumenterade).
**Verification:** GATE-WEB. *Not run.*

### Task V2-3: Web P2 — korrekthet + fetch-hygien

**Files:** Modify `apps/web/app/(app)/insider-radar/InsiderRadarView.tsx`, `apps/web/app/(app)/signal-analytics/SignalAnalyticsView.tsx`, `apps/web/app/(app)/screener/ScreenerView.tsx`, `apps/web/app/(app)/jamfor/JamforView.tsx`, `apps/web/components/command/CommandPalette.tsx`, `apps/web/hooks/useCompare.ts`, `apps/web/hooks/useAlerts.ts`, `apps/web/hooks/useStock.ts`, `apps/web/lib/labels.ts`, `apps/web/components/portfolio/ImportModal.tsx`, `apps/web/components/portfolio/PortfolioBuilderView.tsx`.
**Proof:** se fyndtabell P2 + advisor#2 (PortfolioBuilderView 501-fallback).
**Ändring:** fragment-keys; tysta catches → användar-feedback; `any`→typer (`useCompare`); ta bort död kod (`useAlerts.ts useScoreHistory+useSignalTransitions`, `useCompare.useStockDetail`); behåll EN `useScoreHistory` (useStock-versionen; lägg heterogen cache-key + rätt endpoint); flytta fetch-i-useEffect till react-query (JamforView, CommandPalette); `labels.ts` + `ScanParams`-typ (`preset_used`); ImportModal → query-invalidering; PortfolioBuilderView: hantera 501 från `/construct`/barbell/stress-test graceful med info-UI.
**AC:** GATE-WEB; inga `any` i hooks; inga fetch-i-useEffect kvar i de tre vyerna.
**Verification:** GATE-WEB. *Not run.*

### Task V2-4: Verktygsgates — verify_codex.py + smoke_test.py (post-V1-8)

**Files:** Modify `scripts/verify_codex.py`, `scripts/smoke_test.py`.
**Proof:** `verify_codex.py:40,56-59,130-149`; `smoke_test.py:38-72,80`; våg-deliverables.
**Ändring:**
- [ ] `PATH_REGEX` → parenteser + mellanslag (utöka teckenklassen).
- [ ] Route-drift: samtliga listade routes i 04-kapitlet → hård check (exit 1) efter V1-8 (annars WARN/exit 0).
- [ ] Linjebudget: allvar → WARN utan exit-fällning (separat flagga `--strict-warnings`).
- [ ] `smoke_test.py`: lägg +13 endpoint-grupper (market-intel ×9, ml-performance ×5, ai ×9, paper ×3, portfolio/risk|construct|rebalance/*|diversification|holdings|reset|snapshot|history|import/preview|import/avanza/preview|funds/{id}, strategies, strategy-lab, signal-analytics, calendar/dividends|economic, insider-radar, insider/clusters, stocks/{ticker}/insider, ai/forensic-audit/{ticker}, feedback, price-alerts/check, admin ×13, debug ×N, markets/regime, stocks/compare|benchmark/omxs30|{ticker}/…, smallcap/sectors, profile/risk|account, transactions/twr) + 501-grupp för `/construct`, barbell, stress-test (förväntad 501 utan deps).
- [ ] `:80` — härled Origin från `--base-url` (eller env `EXPECTED_ORIGIN`) istället för hardcodad URL.
**AC:** `verify_codex.py` ger korrekt exit per allvar; smoke_test passerar mot lokal dev-API; tsc/vitest oförändrat grönt.
**Verification:** `python scripts/verify_codex.py; echo exitcode`; `python scripts/smoke_test.py http://localhost:8000`. *Not run.*

---

### Task V3-1: Migration 078 — saknade index

**Files:** Create `supabase/migrations/078_missing_indexes.sql`.
**Proof:** `006:13-22` paper_trades; `009:1-10` portfolio_optimizations; `001:126-136` pipeline_runs (admin.py:547 ordnar på started_at); `017:3-12` user_ticker_requests (admin.py:609-611 + entrypoint.py:201).
**Ändring:** `CREATE INDEX IF NOT EXISTS` på respektive kolumn.
**AC:** idempotent; `EXPLAIN` på admin.py:547-querien använder index.
**Verification:** SQL-körning i Supabase (manuell) + `EXPLAIN` i psql. *Not run.*

### Task V3-2: CI P3 — python 3.12 + cron-kollisioner + master_rank-placeholder

**Files:** Modify `.github/workflows/digest.yml`, `.github/workflows/risk_analysis.yml`, `.github/workflows/signal_analytics.yml`, `.github/workflows/smart_alerts.yml`, `.github/workflows/strategy_backtester.yml`, `.github/workflows/master_rank.yml`, `.github/workflows/ml_retrain.yml`, `.github/workflows/alpha_discovery.yml`, `.github/workflows/doc_intelligence.yml`.
**Proof:** `digest.yml:30`, `risk_analysis.yml:34`, `score_tracker.yml:36` (V0-4), `signal_analytics.yml:24`, `smart_alerts.yml:32`, `strategy_backtester.yml:29` (3.11); cron-paren `signal_analytics:9`==`ml_retrain:16`, `alpha_discovery:11`==`doc_intelligence:11`; `master_rank.yml:57-62` placeholder.
**Ändring:** 3.11→3.12; flytta en i varje krockpar (spread ≥10 min); `master_rank.yml`-placeholder → `python -m backend_worker.fundamentals_fetcher` (exakta args: läs `fundamentals_fetcher.py:295-320` — `not verified`); efter byte: verifiera GATE-BW på 3.12.
**AC:** `rg -n "3\.11" .github/workflows/` → 0; inga identiska crons; master_rank kör riktig fetcher.
**Verification:** YAML-parse + cron-grep. *Not run.*

### Task V3-3: Web P3 — prestanda/typer

**Files:** Modify `apps/web/components/screener/ResultTable.tsx`, `apps/web/hooks/useTheme.ts`, `apps/web/package.json`, `apps/web/components/charts/PriceChart.tsx`, `apps/web/app/(app)/oversikt/OversiktView.tsx`, `apps/web/components/widgets/MewsStrip.tsx`, `apps/web/app/(app)/mangdubblare/MangdubblareView.tsx`, `apps/web/components/screener/FilterRail.tsx`.
**Ändring:** useMemo-sortering; ref-focus via useCallback; ↓/↑ → Lucide; localStorage-try/catch; next/eslint-config-align; PriceChart-deps; PERIOD_LABELS-dela; MewsStrip-enkel-cast; Mangdubblare-matematik; FilterRail `mews_flag`+`search` i hasActive.
**AC:** GATE-WEB; `npx eslint .` rent.
**Verification:** GATE-WEB. *Not run.*

### Task V3-4: Web-förbättringar — delade libs/hooks + färgvariabler

**Files:** Create `apps/web/lib/adminJwt.ts`, `apps/web/hooks/useWatchlistToggle.ts`; Modify `apps/web/components/layout/TopBar.tsx`, `apps/web/components/layout/NavRail.tsx`, `apps/web/app/(app)/kontrollpanel/KontrollpanelView.tsx`, `apps/web/app/(app)/admin/feedback/AdminFeedbackView.tsx`, `apps/web/components/stock/VerdictHeader.tsx`, `apps/web/components/stock/VerdictCard.tsx`, `apps/web/app/(app)/bevakningar/BevakninarView.tsx`, `apps/web/app/(app)/topplistor/TopplistorView.tsx`, `apps/web/app/(app)/kvalitetslista/KvalitetslistaView.tsx`, `apps/web/app/(app)/radar/RadarView.tsx`, `apps/web/app/(app)/mangdubblare/MangdubblareView.tsx`.
**Ändring:** Admin-JWT-dekod → `adminJwt.ts`; bevaka/avbevaka → `useWatchlistToggle`; hardkodade Tailwind-färger → `var(--color-up/down/warn)` (~10 filer, lista kommer från D3/P3-receipts); ZBar → delad komponent; null-dash → enhetlig "—".
**AC:** GATE-WEB; `rg -n "emerald-|red-400|amber-"` i listade filer → 0; en JWT-dekod-funktion.
**Verification:** GATE-WEB. *Not run.*

### Task V3-5: P3-rester — error-hygiene-svep + guards

**Files:** Modify (vid behov) `apps/api/routers/admin.py`, `apps/api/routers/portfolio.py`, `apps/api/routers/profile.py`, `apps/api/routers/stocks.py`, `apps/api/routers/market_intel.py`, `apps/api/routers/rebalancer.py`, `apps/api/routers/paper_trading_router.py`, `apps/api/routers/forensic_audit.py`, `apps/api/core/request_id.py`, `apps/api/core/llm_client.py`; Verify `apps/api/core/reranker.py:29`, `apps/api/routers/admin.py:358`.
**Ändring:**
- [ ] `rg -n "except Exception" apps/api` → inga tysta pass kvar (logga istället) — i ägarfiler löses i V0-V2, här svepet + rester.
- [ ] Läckande felmeddelanden → generiska svar + detaljer i logg (admin.py:262,296,530,587,723-725; portfolio.py:489,553; profile.py:69; stocks.py:1036; market_intel.py:115,150,174,294,327,367,410,449,487,655; request_id.py:95).
- [ ] `paper_trading_router.py:74`: guard mot `scan_results.price = NULL` (portfolio.py:44-47-dokumentation).
- [ ] Guards intakta: reranker.py:29 (sentence_transformers), admin.py:358 (psycopg2).
**AC:** Grep-svep tomt; GATE-API.
**Verification:** `rg -n "except Exception:\s*(pass)?" apps/api` + GATE-API. *Not run.*

---

## Verifiering och godkännande

- Build-agenten kör gates i varje task-avslut och rapporterar FAKTISK utdata (kommandon + resultat). Inga påståenden utan körning.
- Migrationer 077/078 appliceras manuellt; mellan våg 0 och 1 krävs "077 i prod"-kvitto.
- Codex-validering `python scripts/verify_codex.py` körs efter varje våg.
- Deploy/push endast på användarens uttryckliga begäran.
