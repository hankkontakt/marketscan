# PLAN.md — Alpha-datalager för MarketScan (familj/vänner, 0 kr)

> Skapat 2026-08-28 efter 3 forsknings- och verifieringsrundor
> (`.opencode/audit/alpha-*`) + granskningspass (v2: korrigeringar från rev).
> Beslut: evidensbaserad signalstack med gratis, officiella källor och mätbar
> forward-utfallshistorik. Inga "alpha"-claims i UI.

## STATUS 2026-08-28 (implementering + produktion klart)

| Task | Status | Bevis |
|---|---|---|
| A1 universe_mapping.py + 040 + universe_mapping.yml | ✅ Live-testad (112 emittenter, HTML-paginering, rate-limit-respekt) |
| A2 fi_short_positions.py + 041 + shorts.yml | ✅ Live-testad (338 rader, LEI→ISIN-anrikning 24/25, ny-disclosure-logik) |
| A3 signal_analytics + factor_metrics + 042 | ✅ Implementerad (90/180/365 d, Rank-IC, decil-spread netto 2 %/round-trip) |
| B1 qmj_scores.py + 043 + qmj.yml + tester | ✅ 14/14 tester gröna; live: NANEXA (data_quality ok, alla metriker) |
| B2 insider_cluster säljkluster + 044 | ✅ Implementerad (säljkluster → warning-flagga, uppsättningsregler) |
| C1 market_intel-router (5 endpoints) | ✅ 151 route-import OK; `def` (repo-konvention), RLS-public read |
| C2 UI: badges + kvalitetslista + nav | ✅ tsc OK; textregler respekterade (ingen "alpha"-text i UI) |
| Gates | ✅ py_compile alla, import alla, 14/14 unittest, tsc, smoke (prod 200 OK) |
| Migrationer 040-044 | ✅ `supabase db push` → **applicerade på produktion**, migration list remote=local |
| Production run 1 (2026-08-28) | ✅ shorts 338 rader, universum 29+29, QMJ **44 rader skrivna, 0 fel** |
| Deploy | ✅ Vercel auto-deploy: API 200 på /api/market-intel/*, web /kvalitetslista 200 |
| Prod-verifiering (deployad API) | ✅ qmj/rank = 42+ nordiska rader; shorts/DYNVO.ST = 9,72 % |

**Buggar hittade & fixade i produktionsfasen (alla bevisade):**
1. `fy_age_fit` spans negativa (fallande kolumner) → sortering.
2. `latest`-kolumn = äldsta (fallande) → fy_last.
3. Enhetsfel mcap/ratio (absoluta enheter).
4. Baslinje-semantik shorts (222→0 falska new_discoveries) via worker_state.
5. marknadssök rate-limits: retry+backoff (annars 29 emittenter per natt).
6. TIMESTAMPTZ datetime vs date (delisting-detektor).
7. `psycopg2 %`-kollision: LIKE-mönster som parametrar.
8. **np.float64 i composite → SQL-text "np.float64(...)" → 'schema np'** (reproducerad mot postgres:16, fixad med float-cast + savepoints).
9. Read-fel aborterade transaktion → rollback-hygiene.

**Kvar (du gör): INGENTING akut** — signal_analytics weekly fyller factor_metrics
(90/180/365 dagar) allt eftersom score_history ackumuleras; universum-registret
växer 29-100+ per natt; QMJ täcker +120 tickers per vecka.

## UPPDATERING 2026-08-28 (andra halvan — nyhetskedjan live)

- **Nyhetskedjan i produktion**: news.yml — Nasdaq-officiella (regelbäringar) +
  GNews-temasweep (188 events, 44 ticker-matchade) + DeepSeek-klassificerare
  (59 klassade, thinking OFF, JSON-mode). Kostnad: ~$0,001/körning.
- **UNIVERSE 156 emittenter** (från 29) + Finnhub/yfinance ISIN-mappning (28 med
  ticker idag; växer) + delisting 554 kontroller.
- **QMJ med strata**: 114 rader skrivna, 0 fel — BOOZT.ST 75,9 topp-5-listade
  (småbolag nu på riktigt), rank_mode within_stratum/global.
- **Token-experiment (2026-08-28)**: mer tokens = INTE bättre.
  A_minimal 5/8 (1291t) · B_few-shot 6/8 (2030t) ← VALD · C_kontext 4/8 (1519t —
  bias!) · D_thinking 4/8 (3134t, 2.4× latens). Slutsats: few-shot-design > mer
  tokens; thinking AV; bolagskontext AV (färgar fel — t.ex. "emission→positiv").
- **Testgrind**: 26/26 unittest (stratum, norm/match, as-of, momentum, short-filter),
  py_compile alla, prod-receipts bekräftade.
- **Migrationer**: 045 (news_events) + 046 (stratum/rank_mode) applicerade.

## Beslutlogg (v1 → v2)

| # | Korrigering | Orsak (bevisad/observerad) |
|---|---|---|
| 1 | Migrationsnummer **040+**: `040_universe_registry`, `041_short_positions`, `042_factor_metrics`, `043_qmj_scores` (+ kolumn-tillägg i 029 för säljkluster, se B2) | 037–039 redan tagna (037_tracking_grants, 038_disable_signup_trigger, 039_robust_handle_new_user) |
| 2 | Egna workflow-filer: `universe.yml`, `shorts.yml`, `qmj.yml` + A3 utökar sin befintliga analytik-jobb. **`pipeline.yml` rörs INTE.** | Fil-ägarprincip; tre waves i samma fil = merge-strider. Se §Regler. |
| 3 | Neutral-z-regler: alla saknade metrics → z=50 (NEVER 0); grupp n<20 → hela-universet-rank; insider-data saknas → z=50 | Falska signaler: ett NVG-elutrymme höjde inte "0"-poäng måste sätta genomsnitt, inte noll |
| 4 | Säljkluster: `backend_worker/insider_cluster.py` (NUVERKANDE skrivare, BUY-only) utökas → säljkluster beräknas (unique_sellers_30d, total_sell_amount_30d) + migration tilläggskolumn; SEMANTIK: säljkluster = `warning_flag` (visa + människlig granskning), ändrar INTE alpha_rank; köpkluster → insider_z = 50 + 2σ·clip(cluster_score) | Lund 2015: säljkluster mest informativa — men säljare kan vara ombalansering/skatt; övertro = falsk exkludering |
| 5 | Freshness-guards: short-snapshot äldre än 7 d → använd senast kända + varningsflagga; **0-rader-fetch → rensa INTE exklusioner** (last-known-good) | Sidformat ändras → tyst dataförlust |
| 6 | As-of-regel förstärkt: `fy_end` tas ur statements-kolumnerna (årtal INTE antaget); kolumnerna måste vara ~1 år (±40 d) isär → annars data_quality='suspect', z=50 | Kvartalsdata kan smyga in i "annual"-tabellen; icke-kalender-år (t.ex. butiksbolag apr–mars) |
| 7 | Momentum-spec bevisad: ADJUSTED close; 12-1 med 21 dagars skip; vol-skalas av 3-mån-do-vol; kräver ≥252 sessioner annars z=50; |30-dagars-avkastning|>60 % → data_quality-flagga (rights/delisting-bedrag) | Rättsutspädningar + nya listningar förstör enkla momentumtal |
| 8 | Raw-statement-cache: R2-parquet (befintligt mönster; pipelinen HAR parquet-arkiv) — fetch max 1×/7d per ticker; budget 120 tickers/natt (sleep 1,5–2 s; try/except; resumable) | yfinance 2400 calls/vecka i ett svep = rate-limit-nedfrysning |
| 9 | Alla nya tabeller: RLS-enable + GRANT anon/authenticated + index (scan_date, ticker, lei) | Repo-mönster (023/029) |
| 10 | C2-textregler: tillåtna ord (källa, evidensbaserad, mätt hittills, ej garanti); förbjudna (alpha, kommer att öka, slå börsen) | Ärlighet |
| 11 | **Inga commits i stock-scanner-repot** — qmj/workers lever i marketscan/backend_worker; stock-scanner-import sker read-only via befintlig sys.path-hack | Separat git-repo |

---

## Scope

1. Universums-registret (sant levande nordiskt universum; FI-emittentlista =
   sanning, Yahoo-ticker = derivat) + delisting-detektor.
2. Blankningssäkerhetsgrind (FI HTML-scrape, verifierad väg) + ny-disclosure-varning.
3. QMJ-kvalitetskomposit (evidens: 4 nordiska studier + AQR) + momentum (12-1,
   vol-skalad) + värde (EV/EBITDA, FCF-yield, sektorneutral om n≥15) + payout,
   med punkt-i-tid-hänsyn; **årlig ledviktning** (april) och hårda filter.
4. Insider-säljkluster-varning (utökar befintlig buy-only-worker).
5. Mätning: horisonter 90/180/365 + factor_metrics (Rank-IC, decil-spread,
   netto 100 bps/sida) — forward-validering, inte historisk backtest.

## UTANFÖR scope (medvetet)

- Bolagsverket: verifierad blockad för automation (TLS-alert via PS 5.1, curl-schannel
  och python; webb = connection reset; ingen proxy). Eventuell OAuth-registrering
  testas separat i webbläsare — icke-blockerande eftersom yfinance-raw räcker.
- ESAP: fas-1-insamling startade 2026-07-10, publik 2027-07-10 (domän ej i DNS idag).
  Återbesök juli 2027 (årsrapporter+shorts, senare även MAR-insider).
- PEAD, Börsdata (59 €), ML-ranker, historiska alpha-claims.
- Ändringar i `core/scoring.calc_quality_score` — befintliga tester får ej försvagas.

---

## Uppgifter och filägande

### Fas A — våg 1 (A1+A2+A3 parallellt; inga delade filer)

**A1. Universums-registret** — `backend_worker/universe_mapping.py` (NY) +
`040_universe_registry.sql` (NY) + `.github/workflows/universe.yml` (NY).
- Daglig; källor: marknadssök-emittentlista (mönster från `fi_insider_bulk.py`)
  → orgnr/LEI/ISIN/namn; ISIN→Yahoo-ticker (befintlig mappning i
  `insider_fetcher.py`/`company_profiles` + manuell seed för kända gap);
  yfinance-presence-probe (cachad 7 d).
- Tabell: `universe_registry(isin PK, ticker, orgnr, lei, name, market,
  status['listed'|'verify'|'delisted'|'no_price_data'], listed_date,
  delisted_date, source, updated_at)` + RLS/GRANT/index.
- Delisting: FI-lista ≠ Yahoo → 'verify'; 404 → 'delisted' efter 2 v av
  'verify'; NO-Yahoo-data överhuvudtaget (NGM-fall) → 'no_price_data'
  (ALDRI 'delisted').
- ACCEPTANS: alla `smallcap_results`-tickers har rad; ZinZino fångas 'delisted';
  ≥1 nyintroducerad fångas; migration i journal.

**A2. Blankningworker** — `backend_worker/fi_short_positions.py` (NY) +
`041_short_positions.sql` (NY) + `.github/workflows/shorts.yml` (NY).
- Källa: FI net-short HTML-tabell (verifierad 2026-08-28; Excel = JS-renderad,
  fallback HTML). Daglig snapshot.
- `short_positions(scan_date, lei, ticker, issuer_name, total_short_pct,
  latest_position_date, holders_json, is_new_discovery, delta_pp)` + index.
- Events: första förekomst >0,5 % eller Δ≥+0,5 pp inom 90 d.
- Freshness-logg till `worker_state`; 0-rader → ALERT + förra kända värdet
  kvarstår (last-known-good).
- ACCEPTANS: körning → ≥100 rader; ≥90 % LEI→ticker-join; event-tabell;
  manuellt fel-fall (0-rader) testat.

**A3. Mätning utökad** — `backend_worker/signal_analytics.py` (utöka) +
`042_factor_metrics.sql` (NY) + befintlig analytics-workflow-rad.
- Horisonter läggs till: 90/180/365; `factor_metrics(factor, horizon_days, n,
  rank_ic, decile_spread_net, win_rate, computed_at)`; netto = 100 bps/sida.
- ACCEPTANS: körbar; ≥1 rad per faktor; migr. i journal.

### Fas B — våg 2 (B1 + B2 parallellt; olika filer)

**B1. QMJ-komposit** — `backend_worker/qmj_scores.py` (NY), `043_qmj_scores.sql`
(NY), `.github/workflows/qmj.yml` (NY), `tests/test_qmj_scores.py` (NY).
- Källa: yfinance RÅ-bokslut (`financials`, `quarterly_*`, `balance_sheet`)
  via R2-parquet-cache (8); ALDRIG `.info`-derivativ (Tokmanni-fällan).
- As-of: fy_end från kolumnindex; ≥3 årliga kolumner, avstånd 365±40 d;
  published_safe = fy_end + 5 mån; `as_of_date` lagras; suspect → z=50.
- Metrik: ROE, ROA(EBIT/TA), GMAR, CFOA, accruals, leverage(DE, ND/EBITDA),
  räntetäckning, ROE-vol, beta/IVOL, netto-utgivning; rank-z inom
  [50–300, 300–1500, 1500–5000 Mkr] (grupp n<20 → universum-rank).
- Komposit: quality 40 / momentum 25 (12-1 vol-skalad enligt 7) /
  insider_z 15 (köpkluster: 50 + 2σ·clip(cluster_score); saknas → 50;
  säljkluster → warning_flag ENDAST) / value 10 / payout 10.
- Hårda filter: short ≥8 % (senast kända, freshness 7 d) eller
  new_discovery<90 d → `alpha_rank=NULL` + `exclusion_reason`; likviditet
  (omsättning <1 Mkr/d → rank ej NULL men `liquidity_warning`).
- `qmj_scores(ticker, scan_date, as_of_date, rebalance_flag, quality_z,
  momentum_z, value_z, payout_z, insider_z, alpha_rank, exclusion_reason,
  warning_flags, data_quality, metrics_json)` + RLS/index.
- Veckovis fredag-natt; rebalance_flag=sant ENDAST april + vid
  delisting/nydisclosure-systemfel.
- Tester: as-of-regel; all-absent-neutralitet; grupp<20-fallback;
  delisted-exkludering; yfinance-404; split-justerad momentum (syntetisk);
  short-filter-tom; freshness-guard; icke-årlig-kolumn-validering.

**B2. Säljkluster-utökning** — `backend_worker/insider_cluster.py` (utöka;
  befintlig BUY-only-skribent) + migrations-tillägg `ALTER TABLE
  insider_cluster_signals ADD COLUMN unique_sellers_30d, total_sell_amount_30d`.
- Semantik (4): säljkluster = warning_flag + UI-varning; ingen rank-ändring.
- ACCEPTANS: befintliga köpkluster-rader oförändrade (snapshot-test);
  säljkluster beräknas; alla existerande tester gröna.

### Fas C — våg 3 (C1+C2 parallellt; beroende på A2+A3+B1+B2)

**C1. API** — `apps/api/routers/market_intel.py` (NY): `GET
  /api/market-intel/shorts/{ticker}`, `/qmj/rank`, `/clusters/{ticker}`,
  `/factor-metrics` (read-only, RLS-respekterande).
**C2. UI** — `apps/web/app/aktie/[ticker]/page.tsx` (flagbadges:
  blankning/illikvid/säljkluster/exclude + kostnadsrad "~1 %/sida,
  rebalansera högst årligen"), ny sida `apps/web/app/kvalitetslista/page.tsx`
  (top-30 + motivering + länk till factor-metrics). Textregler enligt (10).
  Läs befintliga komponenter först, följ designen.

---

## Beroendegraf

```
A1 ─► A2 (join) ─► B1 (filter) ─► C1 ─► C2
A1 ─► B2 (ticker-mapp) ─► C1
A3 (oberoende, våg 1)
```

## Verifieringskommandon (per våg — KÖR ALLTID)

```bash
# A
python -m backend_worker.universe_mapping --dry-run
python -m backend_worker.fi_short_positions --dry-run
python -m backend_worker.signal_analytics --weeks 4
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
python scripts/smoke_test.py && python scripts/verify-migrationer.cjs
# B
python -m pytest tests/test_qmj_scores.py -q
python -m pytest backend_worker/tests -q          # befintliga får inte gå sönder
python scripts/verify-migrationer.cjs
# C
cd apps/web && npx tsc --noEmit && cd ../..
python scripts/smoke_test.py
```

## Regler

- En fil = en ägare per våg; `pipeline.yml` rörs aldrig; nya yml-filer per worker.
- Inga väckelser av gamla tester; lägg till, ta inte bort.
- Skriv inte i stock-scanner-repot (read-only-import).
- Alla nya tabeller: RLS + GRANT + index; migrationer körs manuellt
  (repo-mönster) — följ `scripts/verify-migrationer.cjs`-flödet.
- Varje task-rapport: exakt rapportkontrakt (Task Report / Verification
  Receipts / Grep Sweep / Downstream Context / Blockers).
