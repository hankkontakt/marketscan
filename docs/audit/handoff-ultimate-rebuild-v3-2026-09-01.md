# HANDOFF — MarketScan Ultimate Rebuild v3 (2026-09-01)

> **Läs först:** `SYSTEM_INDEX.md` + `docs/audit/ultimate-rebuild-v3-progress.md` (levande
> ledger — bocka av allt eftersom) + `docs/audit/ultimate-rebuild-v3-production-runbook.md`
> (produktionsvägen). Denna handoff är bryggan mellan sessionerna: vad som är gjort,
> vad som är kvar, och exakt hur man fortsätter.

## 1. Läget i ett stycke

V3-rebuilden (Ultimate Rebuild Specification v3, `C:\Users\hthur\Downloads\MarketScan_Ultimate_Rebuild_Specification_v3_2026-09-01.docx`)
är byggd genom faser 0–8-kärna + delar av 10/12, **helt lokalt verifierad** mot den lokala
Supabase-stacken. Produktion är **orörd** — cutover kräver ägarens explicita beslut
(runbooken är klar). Branch: `codex/ultimate-rebuild-v3`.

## 2. Commit-kedja (allt committat, trädet rent)

| Commit | Innehåll |
|---|---|
| `b11d021` | Foundation: 083 (manifest/RLS/atomisk publish), 084 (corporate actions + metric_catalog), Security Master-bootstrap (US-policy UNKNOWN→NO_SIGNAL), metric_contracts (debt_to_equity), karantän-logik i publication, E2E-lokalt |
| `96cdc5d` | API v3 komplett (system/current-snapshot, ticker-alias, segment-filter), 085 (vy + pris/segment), TS-typgenerering + sync-test, Screener V3 + DecisionHeaderV3 bakom flaggor |
| `28c97c3` | Phase 4: 086 (fx_rates, ECB-seed 2026-09-01), fx.py-kontrakt, market_calendar.py (11 MICs, VERIFIED/DOCUMENTED/WEEKEND_ONLY), likviditet på explicita kurser, 087 (fx i vyn) |
| `721c417` | Phase 6: shadow_vnext.py (jämförelsebevis, publicerar aldrig), driver-proveniens i bryggan, Topplistor V3, Phase 10-drivare i headern, produktions-runbook |

## 3. Fasstatus

- ✅ **0–3**: baslinje, security/migrationsgovernance, Security Master (lokal E2E), Metric
  Catalog/units/PIT-kontrakt
- ✅ **4**: FX-kontrakt + venue-kalender + likviditet på riktiga kurser — **rest:** riktiga
  volymdata (pris-historik) för graderna i drift; kalenderdriven stale-detection i pipelinen
- ✅ **5**: worker→stage→atomär publish, karantän, LAST_KNOWN_GOOD (lokal E2E + bevis)
- ✅ **6**: shadow-vNext-motorn (setup/risk med reason_codes, jämförelseartefakt)
- ✅ **7**: API v3 komplett + genererade TS-typer + drift-gate
- 🟡 **8**: Screener + Topplistor + aktie-header klara; **kvar:** daglig briefing, jämför,
  smarta larm, portfölj, radar (Phase 9-matris i runbooken §6)
- 🟡 **10**: drivare/varningar i header (från manifest); **kvar:** evidens-koppling när
  observations_v3 fylls (decision_evidence + /evidence-endpoint finns)
- 🟡 **11**: metod + shadow-artefakt; IC-backtest kräver historik (observations_v3 fylls
  först)
- ✅ **12**: runbook (förkontroller, en-i-taget-migrationer, efterkontroller, rollback,
  återställningsgränser) — **produktionsapplicering = ägarens beslut**

## 4. Verifieringsrecept (kör dessa i varje session som fortsätter)

```powershell
# Lokal stack (körs redan; Budgetapp-stacken ligger på 54321-54327, marketscan på 54331-54337)
supabase status

# Hela V3-sviten (72 tester):
$env:PYTHONPATH="C:\Users\hthur\OneDrive\Desktop\marketscan"
.venv\Scripts\python.exe -m pytest apps/api/tests/test_decision_v3_api.py apps/api/tests/test_v3_types_sync.py backend_worker/tests/test_decision_manifests.py backend_worker/tests/test_decision_publication.py backend_worker/tests/test_bootstrap_security_master.py backend_worker/tests/test_metric_contracts.py backend_worker/tests/test_fx.py backend_worker/tests/test_market_calendar.py backend_worker/tests/test_liquidity.py backend_worker/tests/test_shadow_vnext.py -q

# Typkontrakt + codex:
.venv\Scripts\python.exe scripts\generate_v3_types.py --check
.venv\Scripts\python.exe scripts\verify_codex.py

# Frontend:
cd apps/web; npx tsc --noEmit; npx vitest run lib/__tests__

# E2E-cykel (efter db-reset):
$env:DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54332/postgres"
$env:SUPABASE_URL="http://127.0.0.1:54331"
$env:SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
.venv\Scripts\python.exe -m backend_worker.bootstrap_security_master --apply
.venv\Scripts\python.exe -m backend_worker.decision_publication
.venv\Scripts\python.exe -m backend_worker.shadow_vnext
# + live-smoke: se C:\Users\hthur\AppData\Local\Temp\opencode\smoke_v3_api.py (startar uvicorn mot lokalen)
```

**Not:** full pytest-svit har 17 pre-existerande collection-errors i `.venv` (saknar
worker-heavy deps: pandas/yfinance — installeras i CI via `backend_worker/requirements.txt`).
Rör inte; kör V3-filerna ovan.

## 5. Konventioner & läxor (så här jobbar vi här)

- **Migrationsdoctrine:** append-only, idempotenta (`IF NOT EXISTS`/`ON CONFLICT`),
  `GRANT SELECT ... TO anon, authenticated` på nya publika tabeller, RLS på allt nytt.
  Appliceras ALDRIG automatiskt — fil skapas, ägaren kör (eller runbook-steg).
- **Gate-mönster:** backend-flagga `MARKETSCAN_FF_DECISION_V3_API` (feature_flags.py),
  frontend-flagga `NEXT_PUBLIC_DECISIONS_V3` (lib/v3.ts). V1 är default; V3 renderar bara
  när flaggan är true. Aldrig syntetisk fallback — 404/503/NO_SIGNAL är explicita tillstånd.
- **Karantän vs hårdstopp:** icke-ACTIVE/omappade rader → explicit karantän i
  quality_report (reason-kod); missing same-day MasterRank → hårdstopp. DB-funktionen
  `publish_decision_snapshot` är backstop (avvisar handlingsbara beslut på inaktiva listings).
- **Ingen statisk FX-karta** i beräkningsväg (059–061-buggklassen). `fx.py` → None=karantän.
- **Kontrakt:** ändra `apps/api/schemas/decision_v3.py` → kör
  `python scripts/generate_v3_types.py` → commit BÅDA. Sync-testet failar annars.
- **CSR:** genererade typer har optional-arrayer med `unknown` — hantera med `?? []` + casts.
- **Gotchas:** Pydantic nullable-fält behöver `= None` (annars required); vitest kräver
  `vi.mock("@/lib/supabase/client")` + `vi.stubGlobal("fetch", ...)`; `git grep` letar INTE
  i untracked-filer (använd ripgrep/grep-verktyget); PowerShell-encoding (edit-verktyget,
  aldrig Set-Content); `supabase db lint --local` skriver stderr-störning från node.exe —
  resultatraden är "No schema errors found".
- **CPRX-regeln:** Catalyst Pharmaceuticals = MERGED (Angelini, stängt 2026-07-15, $31,50).
  Regression-invariant: 0 CPRX-rader i `current_decisions_v3`. Kör aldrig om seed mot produktion.
- **Lokal stack:** ports 54331–54337 (config.toml har LOCAL-ONLY-kommentarer).
  Budgetapp-stacken (54321–54327) är en annan app — rör den inte.

## 6. Nästa steg i ordning (nästa session börjar här)

1. **Phase 9-ytor (störst värde):** daglig briefing, jämför, smarta larm, portfölj → läs
   V3-projektionen bakom samma flagga (mönster finns i `screener-v3/*` + `lib/v3.ts`).
   Larm/rebalancer ska läsa manifests, inte scan_results.
2. **Phase 4-rest:** riktiga volymdata i pipeline (yfinance-Volumes → `compute_turnover_20d`
   med `fx.py`-kurs) + kalenderdriven stale-detection (`market_calendar.is_trading_day` mot
   quote-datum) — kräver pipeline-körning med nätverk.
3. **Phase 10:** när observations_v3 fylls → `decision_evidence`-rader + "varför"-drawer med
   evidens (endpoint `/api/v3/decisions/stock/{id}/evidence` finns redan).
4. **Phase 11:** IC-backtest (180 d, per segment) när historik finns — metod + shadow-artefakt
   är grunden.
5. **Produktion:** FÖLJ RUNBOOKEN, applicera INGET utan ägarens uttryckliga "kör".
   Cutover = flaggor, rollback = flaggor av (30 min-gräns).

## 7. Kända unknowns (ärliga)

- US-venue per ticker (XNAS-default, UNKNOWN → NO_SIGNAL) — kräver venue-källa per MIC.
- debt_to_equity-enhet i live-data (kontraktet finns; provider-verifiering krävs före inkoppling).
- XTKS/XWAR/XTSE/XASX-kalendrar = WEEKEND_ONLY.
- `.env.example` återställd till placeholders (föregående session hade lagt riktiga
  service-keys där — rekommendation: rotera service_role-nyckeln om filen delats).

## 8. Artefakter

- Ledger: `docs/audit/ultimate-rebuild-v3-progress.md` (levande — uppdatera alltid)
- Baslinje: `docs/audit/ultimate-rebuild-v3-baseline.md`
- Runbook: `docs/audit/ultimate-rebuild-v3-production-runbook.md`
- Shadow-bevis: `docs/audit/shadow-vnext-2026-09-01.json`
- Spec: `C:\Users\hthur\Downloads\MarketScan_Ultimate_Rebuild_Specification_v3_2026-09-01.docx`