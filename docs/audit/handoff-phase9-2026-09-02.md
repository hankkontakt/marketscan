# HANDOFF — MarketScan Phase 9 nattkörning (2026-09-01 → 09-02)

> **Läs först:** `SYSTEM_INDEX.md` + `docs/audit/ultimate-rebuild-v3-progress.md` (levande ledger) +
> `docs/audit/ultimate-rebuild-v3-production-runbook.md` (produktionsvägen, §6-matrisen uppdaterad).
> Denna handoff brygger natten till morgonen: Phase 9 (produktflytt) är klar och lokalt verifierad.

## 1. Läget i ett stycke

**Phase 9 är KLAR** — alla fyra ytor (daglig briefing, jämför, smarta larm, portfölj) har V3-varianter
bakom samma flagga (`NEXT_PUBLIC_DECISIONS_V3`), API-kontraktet utökat (changes/transitions/compare),
worker-diff-lager + migration 088 byggda. **Helt lokalt verifierad inkl. E2E med två snapshots.**
Produktion orörd. Branch `codex/ultimate-rebuild-v3`, trädet rent.

## 2. Commit-kedja (9 commits denna natt)

| Commit | Innehåll |
|---|---|
| `d6726e0` | Foundation: 088-migration (decision_transitions, alert-typer, holdings.listing_id) + decision_transitions.py-diff-lager + 14 tester |
| `c026e70` | PLAN.md Phase 9-plan (8 tasks, 6 vågor, efter reviewer-NEEDS_REVISION-fix) |
| `7752823` | Nattrapport + ledger slice 5 |
| `82fc603` | API v3: /changes, /transitions, /compare + 5 schemas + genererade TS-typer + klient + 8 tester |
| `670c4a4` | Daglig briefing V3 (What changed?) + Jämför V3 (same-snapshot) |
| `f92f5d0` | Larmmotor V3 (5 transition-regeltyper) + smart_alerts VALID_RULE_TYPES + Bevakningar V3 |
| `c4f45ef` | Portfolio API V3-join (enrich_with_v3_decisions, HoldingOut +10 fält, 13 tester) |
| `e6b48af` | Portfolj V3 + RiskView/RebalanceView V3-badges |
| `a90e762` | **E2E-fix:** `ANY(%s::uuid[])` (uuid/text-mismatch hittad i live-körning) |
| `a1d3167` | Exit-gate-sweep + docs (runbook-matris, ledger slice 6, codex 04/05/06) |

## 3. Fasstatus (uppdaterad)

- ✅ **8**: Screener, Topplistor, aktie-header, **daglig briefing, jämför** — klara
- ✅ **9**: **smarta larm (manifests-baserade transition-regler), portfölj (V3-badges)** — klara.
  **Kvar:** Radar (kräver Phase 4 event-inputs), Digest mailer (egen task)
- ✅ **10/11**: oförändrat (evidens-koppling + IC-backtest kräver observations_v3-historik)
- 🟡 **Exit-gate §40.10**: V3-vägarna har noll entry_signal/score_total (grep-verifierat);
  V1-vägarna kvar som fallback (dokumenterat)

## 4. E2E-bevis (lokal stack, 2026-09-01 natt)

- `supabase db reset --local` → 001–088 rent, lint "No schema errors found".
- bootstrap → 9 listings (8 ACTIVE + CPRX MERGED). Publikation #1 → 8 manifests, 1 excluded (CPRX).
- master_rank-mutation (VOLV-B.ST 84→70, SAND.ST 77→88, NIBE-B.ST 62→66) → publikation #2.
- `decision_transitions` → **exakt 2 rader**: SAND.ST `rank_delta:+11.0`, VOLV-B.ST `rank_delta:-14.0`,
  decision_id satta; NIBE-B.ST (Δ+4 < tröskel) och CPRX korrekt frånvarande.
- API-smoke (TestClient mot lokal): /changes 200 (2 rader, rätt snapshot_id), /transitions 200,
  /compare 200 (samma snapshot, CPRX tyst exkluderad), /compare-only-CPRX **404**, current-snapshot 8 manifests.

## 5. Verifieringsrecept (oförändrat + nya filer)

```powershell
$env:PYTHONPATH="C:\Users\hthur\OneDrive\Desktop\marketscan"
.venv\Scripts\python.exe -m pytest apps/api/tests/test_decision_v3_api.py apps/api/tests/test_v3_types_sync.py apps/api/tests/test_v3_portfolio_enrichment.py backend_worker/tests/test_decision_manifests.py backend_worker/tests/test_decision_publication.py backend_worker/tests/test_bootstrap_security_master.py backend_worker/tests/test_metric_contracts.py backend_worker/tests/test_fx.py backend_worker/tests/test_market_calendar.py backend_worker/tests/test_liquidity.py backend_worker/tests/test_shadow_vnext.py backend_worker/tests/test_decision_transitions.py backend_worker/tests/test_smart_alert_transitions.py -q
# → 114 passed
.venv\Scripts\python.exe scripts\generate_v3_types.py --check   # OK
.venv\Scripts\python.exe scripts\verify_codex.py                # 100%
cd apps/web; npx tsc --noEmit; npx vitest run lib/__tests__; npm run build  # ren / 25 passed / OK
# E2E-cykel (efter db-reset): bootstrap → publish ×2 (mellan: mutera master_rank) → decision_transitions
# → /changes via API-smoke (C:\Users\hthur\AppData\Local\Temp\opencode\smoke_phase9.py)
```

## 6. Konventioner & nya läxor

- **Diff-lagret ligger i workern + `decision_transitions`-tabellen** — API diffar ALDRIG snapshots
  (RLS: anon ser bara PUBLISHED; publish supersedear gamla). "Workers compute, API reads" (spec §31).
- **`decision_transitions` körs som eget steg** (`python -m backend_worker.decision_transitions`)
  efter publikation. Idempotent (ON CONFLICT DO NOTHING).
- **Larmregler:** nya transition-typer kräver inga conditions (ren transition + valfri ticker).
  Motorn läser `decision_transitions` (7 dagar), skriver `triggered_alerts.decision_id`.
- **V3-fönstret:** 1 snapshot → /changes 200 med tom lista ("Inga förändringar…" i UI). E2E kräver 2.
- **Pre-existing (rör INTE):** `test_alert_routes.py` ×3 + `test_phase03_security.py` ×1 failar —
  Starlette lazy-integrerar routers som `_IncludedRouter` (app.routes-inspektion ser inga paths;
  TestClient-requests fungerar). pandas saknas i .venv → collection-error i test_segment_classification.
- **Byggartefakter:** `apps/web/public/sw.js` + `tsconfig.tsbuildinfo` ändras av build — återställ alltid.

## 7. Nästa steg i ordning

1. **Radar** (Phase 9-rest): kräver Phase 4 event-inputs (nyhetskällor) — planera när källorna finns.
2. **Digest mailer:** egen task mot `decision_transitions` + decision-länkar (runbook §30-matrisraden).
3. **Phase 4-rest:** riktiga volymdata + kalenderdriven stale-detection (kräver pipeline med nätverk).
4. **Phase 10:** observations_v3 → decision_evidence-rader + "varför"-drawer (endpoint finns).
5. **Phase 11:** IC-backtest när historik finns.
6. **Produktion:** FÖLJ RUNBOOKEN (§2-4). Applicera INGET utan ägarens "kör". 088 väntar (APPROVED av
   migration-vakt-natt; lokal E2E bevisad). Cutover = flaggor; rollback = flaggor av (30 min).

## 8. Kända unknowns (uppdaterade)

- Holdings-backfill: tickers utan unik ACTIVE-träff får NULL listing_id (NOTICE vid migrering) — UI visar "—".
- /compare tappar tyst tickers utan publicerat beslut (UI visar notis). Blandade snapshots → 409.
- Rebalance/optimize-endpoints bär ännu inte V3-fälten (vyerna är additivt redo, visar "—").
- Portfolio construct V3-mappning defer:ad (spec §0.3 — kräver arketypbeslut, dokumenterad öppen fråga).

## 9. Artefakter

- Ledger: `docs/audit/ultimate-rebuild-v3-progress.md` (slice 5+6)
- Nattrapport: `docs/audit/NATTRAPPORT_2026-09-01.md` (uppdateras efter varje paket)
- Runbook: `docs/audit/ultimate-rebuild-v3-production-runbook.md` (§6-matrisen uppdaterad)
- Spec: `C:\Users\hthur\Downloads\MarketScan_Ultimate_Rebuild_Specification_v3_2026-09-01.docx`
  (+ extraherad text `C:\Users\hthur\AppData\Local\Temp\opencode\v3-spec.txt`)