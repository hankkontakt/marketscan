# PLAN — Phase 9: Produktflytt till V3 (daglig briefing, jämför, smarta larm, portfölj)

> Branch: `codex/ultimate-rebuild-v3`. Nattkörning 2026-09-01 (fortsättning). Bas: handoff + runbook §6-matris + spec §25/§26/§29/§30/§31/§35/§40.
> Grundregler: flag-gates (backend `MARKETSCAN_FF_DECISION_V3_API`, frontend `NEXT_PUBLIC_DECISIONS_V3`), aldrig syntetisk fallback (404/503/NO_SIGNAL explicita), API importerar aldrig backend_worker, inga emojis (Lucide), InfoTooltip vid mått, React 18.3.
> REVIDERAD efter reviewer-natt (2 blockerande fynd fixade): diff-lagret flyttas till worker + `decision_transitions`-tabell; FK = `decision_id`.

## Låsta designbeslut

1. **Deterministiskt delta-lager i WORKER, API läser** (spec §29 + RLS-verklighet): anon kan bara se `status='PUBLISHED'` snapshots (083:281) och publish supersedear alla tidigare (083:237-238) → API kan ALDRIG diffa två snapshots. Därför: `backend_worker/decision_transitions.py` diffar de två senaste snapshotsarna (service-roll) och skriver `decision_transitions`-tabellen (i 088, anon-readable). `/changes` + `/transitions` läser bara tabellen. "Workers compute, API reads" (spec §31).
2. **Reason codes:** `thesis:BULLISH→CONSTRUCTIVE`, `setup:READY→WATCH`, `risk:NORMAL→ELEVATED`, `data_grade:A→B`, `tradability:ACTIVE→MERGED`, `rank_delta:+4.1`. State-ändringar alltid material; rank-delta om |Δ|≥5. Aldrig LLM.
3. **Alerts:** nya regeltyper (thesis/setup/risk/data_grade/tradability_transition) läser `decision_transitions`/manifests; `triggered_alerts.decision_id`; legacy-regler orörda (V1-fallback).
4. **Portfölj:** `holdings.listing_id` (migration 088 + backfill via upper(ticker)-match, **endast exakt-1-träff annars NULL + rapport**); risk/diversification joinar `current_decisions_v3`. **Construct omställs INTE** (spec §0.3 — ingen ny score-kompression; ad-hoc-mappning defer:as, dokumenteras).
5. **Migration 088 skapas + granskas (migration-vakt-natt) + rapporteras i HANDOFF; appliceras ALDRIG mot produktion.** Lokal stack (54331-54337) är testmiljö — användarens recept tillåter db-reset lokalt.
6. **En snapshot → `/changes` returnerar tomt explicit tillstånd** (inga deltas att visa), UI visar "ingen historik ännu". (Verifierat: lokalt 1 PUBLISHED.) E2E kräver en andra publikation lokalt (ändrad seed + republish).
7. **AICompareCard exkluderas ur V3-jämför-vägen** (hämtar score_total — exit-gate).
8. **CHECK-idempotens:** Postgres saknar `ADD CONSTRAINT IF NOT EXISTS` → utöka alert_rules med DO-block som kollar `pg_constraint`.

## Tasks

### Våg 1 — DB + worker-diff (P0, fundament)
- **T2. Migration 088** — fil: `supabase/migrations/088_phase9_alerts_portfolio.sql`. (a) `decision_transitions`-tabell: `id, snapshot_from, snapshot_to, listing_id, ticker, transition_type, from_state, to_state, reason_code, rank_delta, decision_id, created_at` + RLS (service-write, anon/authenticated-read) + GRANT; (b) `alert_rules`: behåll CHECK, utöka med DO-block + pg_constraint-koll (nya typer); (c) `triggered_alerts.decision_id uuid NULL REFERENCES public.decision_manifests(decision_id)`; (d) `holdings.listing_id uuid NULL REFERENCES public.listings(id)` + index; (e) backfill: `UPDATE holdings SET listing_id = (SELECT l.id FROM listings l WHERE upper(l.ticker) = upper(holdings.ticker) AND l.state='ACTIVE' ...)` — endast exakt-1-träff, annars NULL + rapport-rad. AC: idempotent, RLS intakt, CPRX-invariant (0 rader), FK korrekt (`decision_id`). Verifiering: SQL-granskning (migration-vakt-natt) + lokal db-reset i E2E.
- **T5a. Worker-diff** — filer: `backend_worker/decision_transitions.py` (ny), `backend_worker/tests/test_decision_transitions.py` (ny). Ren funktion: hämta 2 senaste PUBLISHED snapshots (service-roll) → diff per listing → transition-rader (reason codes ovan). Körs som eget steg `python -m backend_worker.decision_transitions` (anropas efter publikation). AC: 1 snapshot → 0 rader (tomt); 2 snapshots → deterministiska deltas; rank-delta |Δ|<5 → ingen rank-rad; CPRX-rad ALDRIG (inaktiv). Verifiering: pytest ny fil + fixture med 2 snapshots.

### Våg 2 — API-kontrakt (P0)
- **T1. V3 API-kontrakt** — filer: `apps/api/routers/decisions_v3.py`, `apps/api/schemas/decision_v3.py`, `scripts/generate_v3_types.py`, `apps/web/lib/types/decision_v3.ts` (genererad), `apps/web/lib/v3.ts`, `apps/api/tests/test_decision_v3_api.py`. Nya flag-gated endpoints: `GET /changes?limit=` (läser decision_transitions → ChangeEventV3[]), `GET /transitions?limit=` (samma data, normaliserad för larm → TransitionEventV3[]), `POST /compare {tickers}` (läser current_decisions_v3, samma snapshot → CompareProjectionV3). Nya scheman (TOP_LEVEL i generatorn): `ChangeEventV3`, `ChangesProjectionV3` (bär snapshot-meta: as_of, snapshot_id, model_version), `CompareRequestV3`, `CompareProjectionV3`, `TransitionEventV3`. Klientfunktioner `v3Changes/v3Compare/v3Transitions` i v3.ts. **Ingen /snapshots-endpoint** (current-snapshot finns redan). AC: flag av → 404; flag på + 0 rader → tom lista (200); 2 snapshots → deltas; `--check` grönt. Verifiering: `generate_v3_types.py --check`, pytest API + hela V3-sviten.

### Våg 3 — Briefing + Jämför (P1, störst värde)
- **T3. Briefing V3** — filer: `apps/web/app/(app)/daglig-briefing/page.tsx`, `.../DagligBriefingView.tsx`. Ersätt MasterRank-top + score-movers med "What changed?"-sektioner från `v3Changes()` (state-transitioner + rank-movers med reason codes); snapshot-as-of-header; behåll ej score-baserade sektioner (regim/insider/sektor); **gate:a bort MasterRankStrip** (legacy-endpoint) i V3-vägen; gate i page.tsx. AC: noll entry_signal/score_total/**analyst_upside/rsi_14/score_movers** i V3-vägen; tomt tillstånd explicit; V1 orörd vid flag av.
- **T4. Jämför V3** — filer: `apps/web/app/(app)/jamfor/page.tsx`, `.../JamforView.tsx`, `apps/web/hooks/useCompare.ts`. Ny V3-gren via `v3Compare()`: samma snapshot, faktor-/riskskillnader, archetype-mått (`segment_percentile`, drivers), decision_id synlig. Prisdiagrammet behålls. AICompareCard exkluderas ur V3-vägen. AC: samma snapshot_id för alla tickers; noll legacy-fält i V3-vägen.

### Våg 4 — Larm (P1)
- **T5b. Larmmotor V3** — filer: `backend_worker/smart_alert_engine.py`, `backend_worker/tests/` (utökning). Nya regeltyper (thesis/setup/risk/data_grade/tradability_transition) utvärderas mot `decision_transitions`-rader + manifests → skriver `triggered_alerts` med `decision_id`; legacy if/elif-grenar orörda (mönster L317-340). AC: V3-regler triggar bara på verkliga transitioner; decision_id sätts; legacy-regler oförändrade.
- **T6. Larm-API + frontend** — filer: `apps/api/routers/smart_alerts.py`, `apps/web/app/(app)/bevakningar/page.tsx`, `.../BevakninarView.tsx`, `apps/web/hooks/useAlerts.ts`. `VALID_RULE_TYPES` (smart_alerts.py L28,57-61) + schemas utökas; triggered-endpoint returnerar decision_id; V3-gren: Thesis/Setup/Risk/Data-badges via `v3StockByTicker`, nya regeltyper, utlösningar länkar decision_id. AC: nya typer skapbara; noll legacy-fält i V3-vägen.

### Våg 5 — Portfölj (P1/P2)
- **T7. Portfolio-API V3-join** — filer: `apps/api/routers/portfolio.py`, `apps/api/routers/risk.py`, `apps/api/schemas/portfolio.py`. `get_portfolio`/`risk`/`diversification`: join `current_decisions_v3` via listing_id (ticker-fallback), exponera thesis/setup/risk/data_grade/decision_id per innehav; flag-gated berikning, scan_results-fallback kvar. **construct orörd** (defer:as, dokumenterad). AC: innehav visar V3-dimensioner; V1-fallback vid flag av.
- **T8a. PortfoljView V3** — filer: `apps/web/app/(app)/portfolj/page.tsx`, `.../PortfoljView.tsx`, `apps/web/hooks/usePortfolio.ts`. Totalbetyg/Köpläge → Thesis/Setup/Risk/Data-badges + decision_id-länk. AC: noll legacy-fält i V3-vägen.
- **T8b. Byggare + Risk V3** — filer: `apps/web/app/(app)/portfolj/byggare/page.tsx`, `.../PortfolioBuilderView.tsx`, `apps/web/app/(app)/portfolj/risk/page.tsx`, `.../RiskView.tsx`. Konsumerar T7-champion-data (där den finns; annars V1). AC: inga score_total/entry_signal i V3-vägen.

### Våg 6 — Exit-gate + docs (P2)
- **T9. Exit-gate-sweep + docs** — filer: `docs/audit/ultimate-rebuild-v3-production-runbook.md`, `docs/audit/ultimate-rebuild-v3-progress.md`, `docs/codex/06_FRONTEND_STATE_UX.md` + `04_API_ARCHITECTURE.md`. Uppdatera Phase 9-matrisen; dokumentera kvarvarande legacy. AC: grep-sweep över fyra ytor → noll entry_signal/score_total/analyst_upside/rsi_14 i V3-vägar.

## DEFERRED (dokumenteras, byggs ej nu)
- **Radar** — kräver Phase 4 event-inputs (nyhetskällor).
- **Digest mailer** — egen task senare.
- **Per-stock `/changes`-uppgradering** — befintlig endpoint (decisions_v3.py L121-124) får reason codes via T1-diff-hjälparen i senare task.
- **Portfolio construct V3-mappning** — kräver arketypbeslut (spec §0.3); dokumenteras som öppen fråga.

## Vågplan
Våg 1: T2 + T5a. Våg 2: T1. Våg 3: T3 + T4. Våg 4: T5b → T6. Våg 5: T7 → T8a/T8b. Våg 6: T9. Max 2-3 arbetare per våg. Commit efter varje våg. Ledger + nattrapport efter varje paket.

## Verifieringskommandon (globala)
```
.venv\Scripts\python.exe -m pytest apps/api/tests/test_decision_v3_api.py apps/api/tests/test_v3_types_sync.py backend_worker/tests/test_decision_manifests.py backend_worker/tests/test_decision_publication.py backend_worker/tests/test_bootstrap_security_master.py backend_worker/tests/test_metric_contracts.py backend_worker/tests/test_fx.py backend_worker/tests/test_market_calendar.py backend_worker/tests/test_liquidity.py backend_worker/tests/test_shadow_vnext.py backend_worker/tests/test_decision_transitions.py -q
.venv\Scripts\python.exe scripts\generate_v3_types.py --check
.venv\Scripts\python.exe scripts\verify_codex.py
cd apps/web; npx tsc --noEmit; npx vitest run lib/__tests__; npm run build
```