# MARKETSCAN — MASTERRANK R15: DRIFTÅTERSTÄLLNING & STREET-PARITET · ANTIGRAVITY-HANDOFF

> **Vem:** Google Antigravity (eller annan coding-agent). **Vad:** kör hela programmet nedan i task-ordning 1→8.
> **Var:** Windows. Workspace-root: `C:\Users\hthur\OneDrive\Desktop\marketscan`. Alla sökvägar relativa roten om inget annat sägs.
> **Föregångare:** R14-planen (SEGMENTINTEGRITET & SEGMENTDIFFERENTIERING) är **IMPLEMENTERAD** (commits 9469c5b..7c4f1ee) och arkiverad i `.opencode/audit/plan-r14-masterrank.md`. Bygg vidare på den koden — återinför inte R14-ändringar.
> **Utfärdad:** 2026-09-01 av plan-agent (opencode/GLM-5.3) efter live-verifiering av R14-resultatet, kodgranskning och 2 analytiker-research-rapporter. Godkänd av ägaren.

---

## REGELVERK (gäller alla tasks — bryt aldrig)

**Regel 0 — Code wins over book:** Om radnummer förskjutits, filer flyttats eller en gate fejar: verifiera själv, anpassa, dokumentera avvikelsen i slutrapporten. Planen är ett recept, inte en religiös text. "Koden vinner över boken vinner över gamla dokument." Radnumren i §1 hänvisar till post-R14-koden — verifiera dem själv först.

**Regel 1 — Kör aldrig en gate du inte kört:** Rapportera FAKTISK kommandoutdata (kommando + resultat) i slutrapporten. "NEVER claim a check you did not run." Svep alltid nya/ändrade symboler med grep (call sites + display sites) och uppdatera varje träff — inget funnet ska sägas explicit.

**Regel 2 — Windows-encoding (kritisk):** PowerShell 5.1 `Set-Content`/`Get-Content`/`Out-File` dubbelkorrumperar svenska tecken (å/ä/ö → `â€"`). Skriv/editera ALLTID UTF-8-filer via edit-verktyget eller .NET: `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`. Misstänkt korruption: `git grep -l "Ã¤\|â€\|Ã¶" -- <sökväg>`.

**Regel 3 — Git:** Conventional commits (feat/fix/chore/docs + scope), EN commit per avslutad task. Ingen push utan uttrycklig tillåtelse. Committa aldrig `.env`, secrets, tokens eller PII.

**Regel 4 — Projektlagar (från CLAUDE.md, absoluta):**
1. `backend_worker/` får ALDRIG importeras av `apps/api/`. `pandas`, `xgboost`, `scipy`, `yfinance` är förbjudna i API-bundeln (Vercel 500MB-tak).
2. Synkrona Supabase-handlers i FastAPI = vanliga `def` (ALDRIG `async def` — annars blockeras event-loopen).
3. Migrationer körs MANUELLT i Supabase Dashboard SQL Editor — skapa filen i `supabase/migrations/`, kör den INTE själv. Nya kolumner kräver explicit `GRANT SELECT ON ... TO anon, authenticated;` (mönster: `supabase/migrations/023_grant_table_privileges.sql`).
4. Inga emojis i UI — linjeikoner från `lucide-react`. Alla finansiella värden renderas med `<InfoTooltip>`.
5. React 18.3-låsning (uppgradera ej till 19 — Radix UI bryts). Next.js 15: route-params är async promises.
6. Codex-dokument (`docs/codex/`) uppdateras IN-PLACE när kod ändras (Task 8 sköter detta).
7. `service_role`-klienten (`get_supabase_admin`) endast bakom `require_admin`.
8. `DATABASE_URL` i produktion = Supabase Session Pooler (port 6543).

**Regel 5 — STOP-villkor:** En gate misslyckas → stoppa, rapportera exakt utdata, vänta på mänskligt beslut. Fynden i §1 reproduceras inte vid omverifiering → dokumentera avvikelsen innan du fortsätter. Radera aldrig data — arkivera. **Migrationer (Task 1) måste appliceras av MÄNNISKAN i Supabase SQL Editor innan Task 5 (pipeline-omkörning)** — rapportera exakt vilka filer som ska köras och vänta på bekräftelse.

---

## 0. BAKGRUND & MÅL

R14 implementerade segmentdifferentiering (vikter v2, junk-gate, segment×sektor-normalisering, likviditetsgrader, äkta earnings/analytiker-data). Live-verifiering 2026-09-01 visar att **koden är deployad men datadriften hänger efter** — hemsidan visar just nu blandad föråldrad data med inkonsistenta signaler — och att **rankningen har dokumenterade avvikelser mot analytikerkonsensus** (value-trap-bias hos storbolag, felaktig fundamentaldata hos småbolag).

**Mål:**
1. **P0 — Drift:** få `/api/scan` att visa korrekt MasterRank, tier och deterministiska Köpläge-signaler; få Pctl-kolumnen populerad; få en fullständig pipeline-omkörning med stale-detektion.
2. **P1 — Street-paritet:** korrigera rankningen mot dokumenterade analytikerfynd (cykeltopp, engångsvinster, value traps, QARP-relief, felaktig revenue-data).
3. **P2 — Polish:** tech-hämtning för XETRA, change_pct, äkta MEWS-komponenter, validering + codex.

**Scope/boundaries — detta görs INTE:** ny datakälla (Börsdata/Millistream), realtids-nyhetsreaktivitet (LeMaitre-guidance-fallet — framtida task, se §5), patentklipp-databas (Task 3c är proxy), UI-ombyggen (Pctl-kolumnen finns redan i ScreenerView), ML-omträning.

---

## 1. VERIFIERADE FYND (live + kod, 2026-09-01) — varje task löser minst ett fynd

### Driftfel (varför hemsidan visar fel just nu)

| # | Fynd | Bevis | Lösas i |
|---|---|---|---|
| **R1** | **`master_rank_pctl` persisteras aldrig:** `compute_table` beräknar percentilen (`backend_worker/master_rank.py:676-692`) men `upsert_master` INSERT saknar kolumnen — och ingen migration skapar `master_rank_pctl` i `master_rank`-tabellen. Pctl-kolumnen i UI visar "—" för alla aktier, för alltid, även efter omkörning. | Grep: `master_rank_pctl` förekommer ENDAST i compute_table + tester — ingen upsert-/migrationsreferens. Live: Pctl "—" i alla rader. | T1+T3 |
| **R2** | **Screener-enrichment failar tyst och drar ner hela vyn:** enrichment SELECTar `master_rank_pctl` från DB (`apps/api/routers/screener.py:73`) → kolumnen finns inte → PostgREST-exception → `except` fångar och returnerar o-enrichade rader (`:85-87`) → fallback-sökvägen (`:112-124`) körs ALDRIG. Bevis: `/api/scan?segments=small_cap` visar `master_rank: null, tier: null` för AOF.DE **trots att master_rank-raden finns (51.96, verifierad via `/api/market-intel/master/AOF.DE`)**. Detta förklarar Köpläge-inkonsistensen: Harvia 56 → "Ej aktuellt" medan ATOSS 52 → "Avvakta" — signalerna kommer från legacy `scan_results.entry_signal`, inte från tier. | Live + kod ovan. | T2 |
| **R3** | **master_rank-tabellen i blandat tillstånd:** MU-raden är exakt identisk med pre-R14 (71.2828571428571; catalyst_z 15.5555 konstant; fel etikett `:earnings`; analyst_z null) medan AOF.DE har en ny-kod-rad (analyst_z 43.5 med 8 analytiker — men rsi_14/momentum_z null). Pipeline-omkörningen var ofullständig/avbruten. `liquidity_grade`/`turnover_20d_median` null överallt (migration 081 troligen ej applicerad — manuellt steg). | Live-jämförelse pre/post R14-fetch; `/api/market-intel/master/rank` + `/AOF.DE`. | T1+T5 |

### Datafel (research-bevisade)

| # | Fynd | Bevis | Lösas i |
|---|---|---|---|
| **D1** | **ATOSS revenue_growth −4 % är FEL:** H1 2026 faktiskt **+12 %** (cloud +26 %, EBIT-marginal 35 %). −4 % matchar endast maintenance-intäkter → growth_z 42 är orättvist låg. | `.opencode/audit/analyst-check-smallcaps-2026-09-01.md` (primärkällor). | T4 |
| **D2** | **Bolagsbeskrivningar fel:** Text S.A. (TXT.WA) = LiveChat/ChatBot/HelpDesk kundtjänst-SaaS (INTE e-learning/e-kiosk/SuperMemo); 7148.T = Financial Products Group — lease-/fastighets-/flygfond (INTE money transfer). | Samma rapport. | T4 |

### Street-paritetsgap (rankning vs analytikerkonsensus, sep 2026)

| # | Fynd | Bevis | Lösas i |
|---|---|---|---|
| **S1** | **Storbolag — systematiskt value-trap-bias.** Street-ordning: **MU ≈ TSMC ≈ MSFT > PETR4 > 2914 > BMY > Olympus**. Vår ordning: MU > PETR4 > BMY > 2914 > MSFT > TSMC > Olympus. Specifikt: **BMY #3 med ~0 % konsensus-upside** (PT $62.8–66.2 vs pris $66.58; Eliquis/Opdivo-LOE 2028; MS bear $40) — vår growth_z 78 bygger på earnings_growth +137 % (engång) medan intäkter faller −3 %. **MU #1 håller men är cykeltopp:** ROE 67 %/85 % bruttomarginal är toppvärden; Citi/UBS förväntar minnespristopp 2027. **Olympus:** value_z 92 = value trap (Hold, −4 % till +37 % upside). MSFT/TSMC underviktade pga value/payout-block. | `.opencode/audit/analyst-check-largecaps-2026-09-01.md` (dubbel-/trippelkällor). | T3 |
| **S2** | **Småbolag — toppen stämmer, två avvikelser.** Harvia #1 = Street Strong Buy (+12.6 %) ✓; ATOSS #2 = Buy +25.9 %, noll sells ✓ (men se D1). **LeMaitre #3 för hög** — Street Hold efter guidance-neddragning 4 aug (6H/3B). Text #4/FPG #6 = value traps (P/E 9–10, fallande intäkter, accrual-flaggor) — vår placering OK men av slump (tunna data), inte design. Puilo #7 ✓ (+1.1 % upside). | `.opencode/audit/analyst-check-smallcaps-2026-09-01.md`. | T3 (+T4 för D1) |

---

## 2. RESEARCH-UNDERLAG (läs vid behov — innehåller alla källor med URL)

1. `.opencode/audit/analyst-check-largecaps-2026-09-01.md` — konsensus, targets, bull/bear, cykeltiming för MU/PETR4/BMY/2914/MSFT/TSMC/Olympus.
2. `.opencode/audit/analyst-check-smallcaps-2026-09-01.md` — samma för Harvia/ATOSS/LeMaitre/Text/MSAB/FPG/Puilo + datafel D1/D2.
3. `.opencode/audit/smallcap-factor-scoring-2026-09-01.md` + `.opencode/audit/small-cap-ranking-nordic-2026-09-01.md` — R14:s underlag (institutionell praxis, nordiska trösklar).

Alla finns på disk (untracked). R14-planen: `.opencode/audit/plan-r14-masterrank.md`.

---

## 3. TASKS (kör i ordning: T1 → T2 → T3 → T4 → [MÄNNISKAN applicerar migrationer] → T5 → [T6 ∥ T7] → T8)

### TASK 1 — DB-schema: pctl-kolumn + migrationsstatus (P0, löser R1-del)

**Files:** Create `supabase/migrations/082_master_rank_pctl.sql` (verifiera nästa lediga nummer först: `Get-ChildItem supabase\migrations | Sort-Object Name | Select-Object -Last 3`).

**Evidence:** R1. R14 skapade 080/081 men appliceringsstatus i produktion är okänd — R3 tyder på att 081 EJ är applicerad.

**Interfaces:** Consumes: `master_rank`-tabell (R14-schema). Produces: kolumn `master_rank_pctl numeric` i `master_rank`; rapport över migrationsstatus.

**Acceptance criteria:**
1. `082_master_rank_pctl.sql` skapad med: `ALTER TABLE master_rank ADD COLUMN IF NOT EXISTS master_rank_pctl numeric;` + `GRANT SELECT ON master_rank TO anon, authenticated;` (Regel 4.3-mönster).
2. Rapport till människan listar exakt vilka migrationer som ska appliceras manuellt: 082 + (om saknade) 080/081 — med SQL-filernas fullständiga sökvägar.

**Verification** (`not run`): filen existerar; rapporten innehåller status.

- [ ] Skapa migrationsfil
- [ ] Verifiera/dokumentera appliceringsstatus för 080/081/082 (kolla om `liquidity_grade`/`turnover_20d_median`/`master_rank_pctl` finns i respektive tabeller — via `information_schema.columns` om DB-åtkomst finns, annars via live-API-svar)
- [ ] STOP: rapportera till människan vilka migrationer som ska köras manuellt — vänta på bekräftelse innan Task 5

### TASK 2 — Enrichment-robusthet i screener (P0, löser R2)

**Files:** Modify `apps/api/routers/screener.py`.

**Evidence:** R2. `_enrich_with_master_rank` (`screener.py:60-125`): SELECT med `master_rank_pctl` (`:73`) → exception → tyst return (`:85-87`) → fallback (`:112-124`) körs aldrig.

**Interfaces:**
- Consumes: `master_rank`-tabellen; `tier_of`/`signal_from_tier` från `apps/api/core/master_rank_utils.py`.
- Produces: kolumnmedveten enrichment — full SELECT → vid fel retry utan `master_rank_pctl` → ERROR-logg (med antal berörda tickers); fallback-sökvägen exekveras ALLTID för rader utan master_rank-rad, även efter partiell query-failure.

**Acceptance criteria:**
1. Enrichment failar ALDRIG tyst: vid kolumnfel loggas ERROR och retry utan den kolumnen lyckas.
2. Rader utan master_rank-rad får fallback-rank/tier/signal från `score_total` (befintlig logik `:112-124`) — alltid.
3. Efter Task 1 + omkörning: `/api/scan?segments=small_cap` visar AOF.DE `master_rank ≈ 51.96`, `tier T3`, `entry_signal "VÄNTA"` (deterministiskt från tier); Harvia 56 → T2 → "Bra läge" — signal konsistent med rank för ALLA rader.
4. `def` inte `async def` (Regel 4.2).

**Verification** (`not run`): `PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"` → tal > 0; live-curl small_cap + kontroll att signalen är monoton med rank.

- [ ] Implementera kolumnmedveten retry + ERROR-loggning
- [ ] Säkerställ att fallback alltid körs (flytta ur except-sökvägen)
- [ ] Verifiera signal-monotonicitet mot live efter omkörning

### TASK 3 — MasterRank-motorn: pctl-persistens + Street-paritetskorrigeringar (P0+P1, löser R1-del + S1 + S2-del)

**Files:** Modify `backend_worker/master_rank.py` · Test `backend_worker/tests/test_master_rank.py`.

**Evidence:** R1 (upsert saknar pctl), S1 (BMY growth_z 78 från earnings +137 % medan intäkt −3 %; MU cykeltopp ROE 67 %; Olympus value_z 92 value trap), S2 (LeMaitre fallen angel). Befintlig kod: `upsert_master` INSERT-kolumnlista; `fuse()`-guardarna (Quality-Momentum Guard etc.); `build_sector_z_maps`-mekanismen för sektorpercentiler; QARP-synergin.

**Interfaces:**
- Consumes: `scan_results.revenue_growth`/`earnings_growth`/`roe_raw`, sektor-maps, `weights.json` v2 (oförändrat).
- Produces: `master_rank_pctl` persisteras; nya flaggor i `data_missing`: `cycle_peak`, `earnings_spike_watch`, `value_trap_watch`, `qarp_relief`.

**Deländringar (a–f):**
- **a) pctl-persistens (R1):** lägg till `master_rank_pctl` i `upsert_master` INSERT + ON CONFLICT UPDATE (kolumnen finns efter Task 1).
- **b) Cykeljustering (S1/MU):** i `fuse` eller `master_rank_run`: om quality_z bygger på ROE/marginal > sektorns p90 (använd `build_sector_z_maps`-mekanismen på roe_raw/gross_margin) ELLER (pe_forward < 10 OCH roe_raw > 0.50) → dämpa quality_z mot sektor-p90-nivå + flagg `cycle_peak`. Klassiskt cyklikt "billigt" (låg P/E vid topp-ROE) ska INTE ge value-bonus. Dokumentera MU-fallet i kommentar.
- **c) Intäktsförfall (S1/BMY):** om `revenue_growth < 0` och `earnings_growth > 0.5` → `growth_z = min(growth_z, 45.0)` + flagg `earnings_spike_watch` (engångsvinster/skatteeffekter lurar inte längre growth-blocket).
- **d) Value-trap-guard (S1/Olympus, S2/Text+FPG):** om `value_z ≥ 85` och `revenue_growth < 0` → `value_z = min(value_z, 65.0)` + flagg `value_trap_watch`. (Quality-Momentum Guard fångar inte detta — value är ju högt.)
- **e) QARP-relief (S2/ATOSS):** utöka befintlig QARP-synergi: om `quality_z ≥ 85` och `roe_raw ≥ 0.40` och PEG ≤ 3 → value-straffet dämpas i synergin (använd `max(value_z, 50.0)` som vz_f) + flagg `qarp_relief`. Säkerställ att `roe_raw` bärs in i values-dict från scan_results.
- **f) Enhetstester per deländring** med profiler från fynden: BMY-liknande (rev −3 %, earnings +137 %) → growth_z ≤ 45; Text-liknande (value 92, rev < 0) → value_z ≤ 65; ATOSS-liknande (quality 89, roe 66 %) → `qarp_relief`; MU-liknande (ROE sektor-p90+) → `cycle_peak`; pctl i upsert-verifierad.

**Acceptance criteria:**
1. Alla tester gröna inkl. nya (f).
2. `python -m backend_worker.master_rank --dry-run` OK.
3. Efter omkörning (Task 5): BMY rank < MSFT/TSMC; ATOSS rank stiger; Olympus/Text/FPG får `value_trap_watch`.

**Verification** (`not run`): `python -m pytest backend_worker/tests/test_master_rank.py -q` → 0 fail; `--dry-run` → OK.

- [ ] a–f implementerade + tester
- [ ] Grep-svep: `cycle_peak`, `earnings_spike_watch`, `value_trap_watch`, `qarp_relief` — call sites + tester uppdaterade

### TASK 4 — Fundamentaldata-korrigeringar (P1, löser D1+D2)

**Files:** Modify `backend_worker/company_info_fetcher.py` · Modify `backend_worker/universe_mapping.py` (eller den fil som håller bolagsbeskrivningar — hitta via `git grep -i "e-learning\|money transfer\|description" backend_worker`).

**Evidence:** D1 (ATOSS −4 % vs faktiska +12 % — mappningen verkar plocka maintenance-segmentet), D2 (Text/FPG-beskrivningar).

**Interfaces:** Consumes: yfinance-fundamentaldata. Produces: korrekt `revenue_growth` (totalintäkter) + korrekta `name`/beskrivningsfält i scan_results.

**Acceptance criteria:**
1. AOF.DE `revenue_growth > 0` (≈ +12 %) efter omkörning — verifiera mot yfinance rådata att totalintäkter används.
2. Text S.A.-beskrivning = kundtjänst-SaaS (LiveChat/ChatBot); 7148.T = Financial Products Group.
3. Sampling: 20 slumpmässiga tickers — ≤1 felaktig beskrivning.

**Verification** (`not run`): efter omkörning: live `scan?search=ATOSS` → revenue_growth > 0.

- [ ] Diagnos + fix av revenue-mappningen
- [ ] Rätta beskrivningar + sampling-svep

### TASK 5 — Pipeline-omkörning & stale-gate (P0; EFTER att MÄNNISKAN applicerat migrationerna från Task 1)

**Files:** Modify `scripts/ranking_sanity_gate.py`.

**Evidence:** R3 (blandad stale-data upptäcktes först manuellt — ingen gate fångade det).

**Interfaces:** Consumes: master_rank/scan_results-tabeller. Produces: nya gate-påståenden + körningsrecept.

**Ny gate-logik:**
1. **Stale-gate:** `max(scan_date)` i master_rank ≤ 3 dagar gammal (hade fångat R3 direkt).
2. **Pctl-täckning:** andelen rader med master_rank non-null som har `master_rank_pctl` non-null ≥ 95 %.
3. Verifiera att R14:s catalyst-varians-gate finns och passerar nu.

**Körningsrecept (i ordning, efter migrationsbekräftelse):** `liquidity` → `catalyst_fetcher` → `analyst_fetcher` → `master_rank`. Verifiera därefter: MU-rad ÄNDRAS (catalyst varierar, analyst_z fylld), liquidity_grade populerad, Harvia-signal konsistent.

**Acceptance criteria:** gates gröna; MU-rad ändrad vs 71.2828571428571; inga "Ej aktuellt"-signaler på rader med rank ≥ segment-T2-tröskel.

**Verification** (`not run`): `python scripts/ranking_sanity_gate.py` → grönt; live master/rank visar förändrad MU-rad.

- [ ] Implementera gate 1–2 + verifiera 3
- [ ] Kör pipeline-kedjan + verifiera mot live
- [ ] STOP om gates fortfarande röda → rapportera exakt utdata

### TASK 6 — Tech-hämtning XETRA + change_pct (P2)

**Files:** Modify `backend_worker/technical_snapshot.py` · Modify `backend_worker/db_loader.py`.

**Evidence:** R3 (AOF.DE rsi_14/momentum_z null — tech-hämtning failar för .DE-suffix); live: `change_pct` null i alla rader ("Idag"-kolumnen tom).

**Interfaces:** Consumes: yfinance prisserier. Produces: tech-data för .DE-tickers; `change_pct` populerad från senaste prisserien i `_prepare_df`.

**Acceptance criteria:**
1. AOF.DE `rsi_14` non-null efter omkörning.
2. `change_pct` non-null för ≥90 % av rader.

**Verification** (`not run`): live scan → change_pct fylld; master/AOF.DE → rsi non-null.

- [ ] Diagnos + fix .DE-hämtning (suffix-hantering i fetch_price_history)
- [ ] change_pct-populering + test

### TASK 7 — MEWS-komponenter äkta (P2)

**Files:** Modify (diagnosen bestämmer filen — hitta producenten via `git grep -n "mews_operating_leverage" backend_worker`; trolig kandidat `backend_worker/qmj_scores.py`).

**Evidence:** Live: `mews_operating_leverage`/`mews_revenue_accel`/`mews_clean_accruals` = 50.0419 konstant i ALLA rader (aldrig beräknade) — MEWS-scoren bygger bara på 3 av 6 komponenter.

**Interfaces:** Produces: äkta komponentvärden (varians > 0) ELLER dokumenterad borttagning ur medelvärdet.

**Acceptance criteria:** komponentvarians > 0 efter omkörning ELLER dokumenterat beslut med motivering i codex.

- [ ] Diagnos + fix/dokumenterad borttagning

### TASK 8 — Validering & dokumentation (P2)

**Files:** Modify `backend_worker/backtest_runner.py` · Modify `docs/codex/01_QUANT_MASTERRANK.md`.

**Evidence:** Docs kap 1 §7-receptet (backtest vid viktändring); nya guardarna i Task 3 behöver dokumenteras; Street-pariteten ska valideras.

**Innehåll:**
1. Backtest: per-segment IC (180 d) före/efter Task 3-guardarna; dokumentera BMY/MU/ATOSS/Text-fallens rank-förändring konkret.
2. Codex kap 1 in-place: `cycle_peak`, `earnings_spike_watch`, `value_trap_watch`, `qarp_relief`, pctl-persistens, enrichment-robusthet.
3. **Street-paritetscheck:** kör `python -m backend_worker.master_rank --print` och jämför storbolagstoppen mot research-rapportens Street-ordning (MU ≈ TSMC ≈ MSFT > PETR4 > 2914 > BMY > Olympus); dokumentera residuala avvikelser som designval vs fel.

**Acceptance criteria:** `python scripts/verify_codex.py` grönt; backtestrapport skriven; paritetsdokument med residualanalys.

- [ ] Backtest + fall-dokumentation
- [ ] Codex uppdaterat + verify_codex grönt
- [ ] Street-paritetscheck dokumenterad

---

## 4. GLOBALA SLUTGATES (kör ALLA efter Task 8 — rapportera FAKTISK utdata)

```powershell
python scripts/verify_codex.py
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
python scripts/smoke_test.py
PYTHONPATH=. python -m pytest apps/api/tests backend_worker/tests -q
cd apps/web; npx tsc --noEmit
python scripts/ranking_sanity_gate.py
python -m backend_worker.master_rank --dry-run
```

**Live-före/efter-referens (efter Task 5:s omkörning):**
- `/api/scan?segments=small_cap&sort_by=master_rank&limit=5` → AOF.DE master_rank ≈ 51.96 + tier + signal konsistent med rank (före: null/null/legacy-signal)
- Pctl-kolumnen visar värden (före: "—" överallt)
- `/api/market-intel/master/rank` → MU-rad ÄNDRAD (före: exakt 71.2828571428571, catalyst 15.5555 konstant), analyst_z fylld för MU/MSFT
- BMY rank < MSFT/TSMC (före: BMY #3)
- `scan?search=ATOSS` → revenue_growth > 0 (före: −4 %)
- `scan?search=SAP` → fortfarande large_cap (regressionstest av R14)

**Commit-plan (conventional, en per task):**
- `chore(db): master_rank_pctl migration + status report`
- `fix(api): column-aware master_rank enrichment with deterministic fallback`
- `feat(worker): street-parity guards (cycle peak, earnings spike, value trap, qarp relief) + pctl persistence`
- `fix(worker): fundamentals revenue mapping + company descriptions`
- `chore(scripts): stale-data gates + pipeline rerun verification`
- `fix(worker): xetra tech fetch + change_pct population`
- `feat(worker): real MEWS components`
- `docs(codex): R15 rank guards + street-parity validation`

---

## 5. UTANFÖR SCOPE — framtida tasks (namngivna med evidens)

1. **Nyhetsreaktivitet:** guidance-neddragningar (LeMaitre 4 aug) ska slå igenom i momentum inom dagar — kräver nyhetsflödes-koppling till momentum-block (Cision finns redan i pipelinen).
2. **Patentklipp-databas:** Task 3c är en proxy (revenue-fall + vinstspike); äkta LOE-data kräver ny källa.
3. **Börsdata/Millistream** för First North-fundamentalia (yfinance opålitlig där).
4. **January/momentum-säsongshantering** i rebalancing (research-rapport 2).

---

## 6. CHECKLISTA (gå igenom i slutet)

- [ ] T1: migrationsfil skapad; migrationsstatus rapporterad; MÄNNISKAN bekräftat applicering innan T5
- [ ] T2: enrichment failar aldrig tyst; AOF.DE visar 51.96 + konsistent signal; Harvia "Bra läge"
- [ ] T3: alla guard-tester gröna; pctl persisteras; BMY < MSFT/TSMC efter omkörning
- [ ] T4: ATOSS revenue > 0; beskrivningar korrekta; sampling ≤1 fel/20
- [ ] T5: stale-gate + pctl-täckning gröna; MU-rad ändrad
- [ ] T6: AOF.DE rsi non-null; change_pct ≥90 %
- [ ] T7: MEWS-varians > 0 eller dokumenterat beslut
- [ ] T8: verify_codex grönt; backtest + Street-paritetsdokument skrivna
- [ ] Alla globala slutgates körda med FAKTISK utdata i slutrapporten
- [ ] Grep-svep av alla nya/ändrade symboler genomfört
- [ ] Inga secrets/PII i committat material

**Slutrapport:** skriv `.opencode/audit/r15-implementation-report.md` med: per task — vad som gjordes, faktisk gate-utdata, avvikelser från planen (Regel 0), kvarvarande punkter från §5.
