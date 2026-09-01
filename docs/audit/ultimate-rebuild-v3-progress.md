# Ultimate Rebuild v3 — Living Progress Ledger (2026-09-01)

> Levande dokument: bockas av allt eftersom enheter blir klara, med
> maskinverifierbart bevis per avslutad gate. Källan till sanning är kod +
> lokala verifieringsresultat; detta dokument är spåret, inte beviset.
> Baslinje: `docs/audit/ultimate-rebuild-v3-baseline.md` (branch `codex/ultimate-rebuild-v3`).

## Verifieringskontext (måste re-kollas före varje produktionssteg)

- Repo-HEAD vid skrivtillfället: `e5052dd` + WIP på branch `codex/ultimate-rebuild-v3`.
- Lokal migrationskedja: `001`–`084` (084 = ny i denna slice).
- Produktionsmigrationer: `082` var head vid audit; **inget appliceras på
  produktion från denna workspace** (planens tillägg: lokal stack är sanningskälla).
- CPRX-fakta verifierade externt (2026-09-01, två källor): Angelini Pharma
  slutförde förvärvet 2026-07-15 ($31,50/aktie kontant), Nasdaq-handeln
  avstängd 2026-07-16, Form 25-avnotering. Källa: Angelini pressrelease +
  Catalyst 8-K (stocktitan/Reuters).

## Fasstatus (planens §35-nyckel)

| Fas | Status | Bevis |
|---|---|---|
| 0 — Freeze/baseline | ✅ Baslinje | `docs/audit/ultimate-rebuild-v3-baseline.md` |
| 1 — Security & migrationsgovernance | ✅ (083 levererar RLS/definer-fix; migrationsrensa) | baslinjen + `083` |
| 2 — Security Master full-universe | ✅ Lokal E2E (9/9 listings, CPRX MERGED); 🟡 produktion kräver venue-källa + staging-ledger | 084 + bootstrap + E2E-bevis nedan |
| 3 — Metric Catalog/units/PIT | ✅ Kontrakt + seed + worker-normalisering; 🟡 provider-adaptrar och live-unit-audit kvar | 084 + `metric_contracts.py` |
| 4 — Likviditet/kalender/FX/events | ⬜ Ej påbörjad | |
| 5 — Worker-pipeline + atomär publish | ✅ Lokal E2E (stage→publish→LAST_KNOWN_GOOD); 🟡 produktionsinkoppling via env-gate | `decision_publication.py` + E2E-bevis |
| 6 — MasterRank/Setup/Risk vNext shadow | ⬜ Ej påbörjad | |
| 7 — Decision API v3 | 🟡 Grund finns + flag-gate-test; TS-klient/kontraktstester saknas | `decisions_v3.py` + tester |
| 8 — Core UI cutover | ⬜ Ej påbörjad | |
| 9–12 — Produktflytt/AI/Research/Portfölj | ⬜ Ej påbörjad | |

## Avslutade enheter (bockas av löpande)

- [x] **084-migration:** `corporate_actions` (RLS service-only, anon läser EFFECTIVE),
      `apply_effective_corporate_actions()` (SECURITY DEFINER, service_role-only),
      CPRX-seed (MERGED, known 2026-05-07, effective 2026-07-15, $31,50),
      `metric_catalog`-seed med 14 kanoniska kontrakt (debt_to_equity_ratio = ratio,
      ej procentenheter).
- [x] **bootstrap_security_master.py:** `resolve_venue` med dokumenterad US-default-policy
      (XNAS/USD, state UNKNOWN → NO_SIGNAL), corporate-action-medveten initial-state,
      skip-om-any-listing, `apply_effective_corporate_actions` efter bootstrap.
- [x] **metric_contracts.py:** `normalize_debt_to_equity` (percent→ratio, UNIT_UNKNOWN-
      karantän, plausible-bounds-flaggor, inget tyst winsorize), transform_version v1.
- [x] **decision_publication.py:** icke-ACTIVE/omappade rader = explicit karantän i
      quality_report (excluded_count + reasons), missing same-day MasterRank kvar =
      hårdstopp.
- [x] **seed.sql:** master_rank-rader för demo-universum (8 .ST + CPRX 76.85/T1/STARK
      = legacy-buggspegel) + CPRX-scanrad (local-only, körs aldrig mot produktion).
- [x] **Lokal stack:** unika portar i `supabase/config.toml` (54331/54332/54333/54334/54337 —
      Budgetapp-stacken ligger på 54321–54327; filen är lokal/untracked). `supabase start` OK.
- [x] **Lokal E2E:** reset genom 084 + seed → bootstrap → publish → alla gates gröna (nedan).

## Lokal E2E-bevis (2026-09-01, `supabase db reset --local` → manuell kedja)

- [x] `supabase db reset --local` → 84 migrationer (001–084) + seed; `supabase db lint --local` → "No schema errors found".
- [x] `bootstrap_security_master --apply` → 9 listings: 8 .ST = ACTIVE (XSTO/SEK), CPRX = MERGED (XNAS/USD, via corporate-action-medveten initial-state; 0 transitions = skapad direkt i rätt state).
- [x] `decision_publication` (env-gated) → snapshot `3dcab92b…` PUBLISHED, **8 manifests, 1 excluded**; quality_report: `excluded=1 exclusions=[{ticker: CPRX, reason: listing_not_active:MERGED}]`.
- [x] `current_decisions_v3`: 8 rader, **CPRX = 0 rader** (regression-invariant håller).
- [x] DB-backstop: manuellt staged handlingsbart manifest för MERGED-CPRX → `publish_decision_snapshot` avvisar ("Cannot publish actionable decisions for inactive listings").
- [x] anon-REST: `current_decisions_v3` läsbar (8 rader), `corporate_actions` visar endast EFFECTIVE, `scan_results` läsbar.
- [x] **LAST_KNOWN_GOOD:** publish med tom dag (2020-01-01) → `ManifestInvariantError`, pekaren oförändrad (`3dcab92b…`).

## Testbevis (senaste körning)

- [x] `pytest apps/api/tests/test_decision_v3_api.py backend_worker/tests/test_decision_manifests.py
      backend_worker/tests/test_decision_publication.py backend_worker/tests/test_bootstrap_security_master.py
      backend_worker/tests/test_metric_contracts.py -q` → **29 passed**
      (första körningen 27 passed / 2 failed = test-stub saknade script-entry; fixad och omkörd).
- Not: full svit har 17 pre-existerande collection-errors i lokal `.venv` (saknar
  worker-heavy deps: pandas/yfinance m.fl. — installeras i CI via
  `backend_worker/requirements.txt`). Ej orsakade av denna slice.

## Kända unknowns (planens §41-register)

- US-venue per ticker: legacy-data saknar venue-fält; XNAS-default är en audited
  exception policy (UNKNOWN → NO_SIGNAL) tills venue-källa per MIC finns.
- debt_to_equity i live-data: värden som 8.94/99.89/139.66 tyder på procentenheter
  (Yahoo-konvention), men provider-verifiering mot live-data krävs innan
  scoring-sökvägen ändras — kontraktet finns nu, transformen är medvetet inte
  inkopplad i master_rank.py.