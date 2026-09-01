# Ultimate Rebuild v3 — Produktionsrunbook (Phase 12, hardening)

> **Läs innan något appliceras mot produktion.** Detta steg körs inte
> automatiskt: produktionsapplicering kräver ett separat, uttryckligt beslut
> (planens tillägg 2026-09-01). Den här runbooken är den enda godkända vägen.
> Källkod, migrationer och tester i repot är det replikerbara beviset; den
> lokala stacken (ports 54331–54337) är schema-sanningskällan.

## 0. Produktionsfakta (verifiera ALLTID på nytt vid utförandet)

- Supabase-projekt: `eukhlhowbbrccerxpisp.supabase.co` (eu-north-1)
- Migrationsledger i produktion: senast känd `082` (audit 2026-09-01) —
  **re-kolla** med `supabase migration list --linked` före allt annat.
- `scan_results`/`master_rank` är legacy-kompatibilitet under migreringen;
  V3 är ett parallellt, avstängt flöde tills denna runbook är genomförd.

## 1. Förkontroller (alla måste vara gröna)

1. `supabase migration list --linked` — verifiera att `083`/`084`/`085`/`086`/`087`
   INTE redan är applicerade (annars: stoppa, analysera avvikelsen).
2. Repo-HEAD innehåller commits `b11d021`, `96cdc5d`, `28c97c3` + denna slicen.
3. `git status` rent; inga secrets i working tree (`.env.example` ska ha placeholders).
4. Lokal grön svit (senast: **72 passed**):
   `python -m pytest apps/api/tests/test_decision_v3_api.py apps/api/tests/test_v3_types_sync.py backend_worker/tests/... -q`
5. `python scripts/generate_v3_types.py --check` → "match OpenAPI contract".
6. `cd apps/web && npx tsc --noEmit` ren + `npx vitest run` grön.
7. Shadow-bevis finns: `docs/audit/shadow-vnext-2026-09-01.json` (Phase 6/11-artefakt).

## 2. Applicering — EN migration i taget, i ordning, manuellt kontrollerad

Kör i Supabase Dashboard SQL Editor (eller `supabase db push --linked` per fil):

| Steg | Fil | Vad den gör | Efterkontroll |
|---|---|---|---|
| 1 | `083_decision_manifest_foundation.sql` | Security Master, observations, manifest, atomisk publish, RLS | `SELECT count(*) FROM listings;` → 0 (innan bootstrap) |
| 2 | `084_corporate_actions_metric_catalog.sql` | corporate_actions + CPRX-seed + metric_catalog | `SELECT ticker, action_type FROM corporate_actions;` → CPRX MERGED EFFECTIVE |
| 3 | `085_current_decisions_v3_price.sql` | vy utökad (pris/segment) | `SELECT * FROM current_decisions_v3 LIMIT 1;` → tom (ingen snapshot ännu) |
| 4 | `086_fx_rates.sql` | fx_rates + ECB-seed | `SELECT count(*) FROM fx_rates;` → 10 |
| 5 | `087_current_decisions_v3_fx.sql` | vy utökad (fx-kontext) | samma som 3 |

**Mellan varje steg:** kör `supabase db lint --linked` + sök efter ERROR-nivå i Security
Advisor. Avvikelse → STOPP, rapportera exakt utdata, applicera inte nästa.

## 3. Produktionsbackfill (efter steg 5, med service-credentials)

1. `DATABASE_URL=<direct> python -m backend_worker.bootstrap_security_master --apply`
   → alla legacy-tickers får listings; suffixlösa US → XNAS/UNKNOWN (NO_SIGNAL tills
   venue-verifiering); CPRX skapas direkt MERGED.
2. Verifiera: `SELECT state, count(*) FROM listings GROUP BY state;` — CPRX=MERGED,
   inga ACTIVE-rader för avnoterade bolag.
3. Kör en pipeline-omkörning (liquidity → catalyst → analyst → master_rank) så att
   `scan_date = idag` finns i master_rank.
4. **Första publikation:** `MARKETSCAN_PUBLISH_DECISIONS_V3=true` + service-credentials.
   Kontrollera loggen: "Published V3 decision snapshot … with N manifests (M excluded)".
   `N + M` = antal same-day-rader; exkluderade = icke-ACTIVE/omappade (karantän).
5. Efterkontroll (Phase 12-gates):
   - `SELECT count(*) FROM current_decisions_v3 WHERE ticker='CPRX';` → **0**
   - `SELECT excluded_count, exclusions FROM decision_snapshots ORDER BY created_at DESC LIMIT 1;`
     → exclusions innehåller CPRX med reason `listing_not_active:MERGED`
   - `SELECT current_decision_snapshot_id FROM publication_state;` → satt
   - anon-REST: `/rest/v1/current_decisions_v3` läsbar, `/rest/v1/corporate_actions` visar
     endast EFFECTIVE, `/rest/v1/pipeline_runs` tom för anon.

## 4. Cutover (flaggor — inga kodändringar i detta steg)

1. Backend: sätt `MARKETSCAN_FF_DECISION_V3_API=true` (Vercel env).
   → `/api/v3/decisions/*` svarar; `system/current-snapshot` visar pekaren.
2. Frontend: sätt `NEXT_PUBLIC_DECISIONS_V3=true` + redeploy.
   → Screener + Topplistor + aktie-Header renderar V3 (V1 kvar som fallback vid fel).
3. Verifiera i produktion: screener visar Thesis/Setup/Risk/Data/Kurs-Idag,
   CPRX syns INTE som handlingsbar, aktiesidan visar beslutsheader.
4. **Rollback (30 min-gräns):** sätt flaggorna till false → V1-surfaces åter.
   Data: inga dataändringar sker vid cutover — endast flaggor. Den publicerade
   snapshoten ligger kvar och kan alltid läsas via v3-API:t.

## 5. Återställningsgränser (vad som INTE görs)

- Migrationerna är append-only och idempotenta (`IF NOT EXISTS`/`ON CONFLICT`).
  Vid problem efter applicering: **applicera inte om**, stoppa och analysera.
- `publish_decision_snapshot` är den enda tillståndsändringen på publiceringssidan;
  fel publicering korrigeras genom att publicera en ny snapshot (LAST_KNOWN_GOOD
  bevaras automatiskt — bevisat lokalt).
- Ingen `DROP`-migration skapas för V3 — legacy `scan_results`-ytor lever kvar
  tills full produktoverflytt är validerad (Phase 9-migreringsmatrisen nedan).

## 6. Phase 9-migreringsmatris (återstående produktytor, dokumenterad status)

| Yta | V3-status | Flagga | Not |
|---|---|---|---|
| Screener | ✅ klar | `NEXT_PUBLIC_DECISIONS_V3` | 6-kolumnstabell §27.1 |
| Topplistor | ✅ klar | samma | DecisionTableV3 återanvänds |
| Aktiesida header | ✅ klar | samma | Thesis/Setup/Risk/Data + drivare |
| Daglig briefing | ✅ klar (2026-09-01) | samma | "What changed?" från `decision_transitions` (v3Changes), snapshot-as-of, ej score-baserade sektioner behållna |
| Jämför | ✅ klar (2026-09-01) | samma | v3Compare: samma snapshot, Thesis/Setup/Risk/Data + drivare, decision_id; AICompareCard exkluderad ur V3-vägen |
| Smarta larm | ✅ klar (2026-09-01) | samma | 5 nya transition-regeltyper läser `decision_transitions` + manifests, `triggered_alerts.decision_id`; legacy-regler orörda |
| Portfölj | ✅ klar (2026-09-01) | samma | Holdings + risk/rebalance visar Thesis/Setup/Risk/Data-badges (V3-join via `enrich_with_v3_decisions`); construct V3-mappning defer:ad (spec §0.3) |
| Radar | ⬜ | samma | kräver Phase 4 event-inputs (nyhets-/eventkällor) |
| Digest mailer | ⬜ | samma | egen task senare (utanför Phase 9) |

## 7. Kända brister att åtgärda i senare faser (ärligt läge)

- US-venue per ticker är UNKNOWN (XNAS-default) → NO_SIGNAL tills venue-källa.
- `debt_to_equity`-enheten i live-data är inte provider-verifierad (kontraktet
  finns i `metric_contracts.py`; transformen inkopplas efter verifiering).
- XTKS/XWAR/XTSE/XASX-kalendrar är WEEKEND_ONLY.
- Riktiga volymdata för likviditetsgrader kräver pris-historik (Phase 4 rest).
- Phase 11 IC-backtest kräver historiska observationer (metod + shadow-artefakt
  finns; dataserien byggs när observations_v3 fylls).