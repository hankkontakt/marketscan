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

## UPPDATERING 2026-08-28 (rond 3 — radarn live, 4 punkter)

1. **Radar-sidan LIVE** — `/api/market-intel/radar` (verifierad i prod: DANSKE.CO 6
   nyheter/48h, ONCO "bridge financing" → negative 0,7, MYCR "order" → positive 0,9,
   CRAYN.OL stratum=new_small ungdata) + UI `/radar` (200, Aktiva/Topprank, tema-filter,
   ärlighetsrad; tsc OK). Radarn samlar: kvalitet/momentum/insider-z + blankning +
   insiderkluster + nyheter 48h + varningar per bolag.
2. **Few-shot-prompten INBYGGD** (vinnaren i token-experimentet: 3 exempel, thinking OFF).
3. **Tema-filter** i radarns API + UI-dropdown (ipo/order/vinstvarning/ledning/
   regulatorik/sector-ai/sector-forsvar).
4. **Finnhub exchange-täckning: verifierad = INGEN på free tier** (SE/FI/DK/NO/IS → 0
   symboler, även US-kontrollen: tillagd kandidatlista; /stock/exchange ger icke-JSON).
   Täckningsvägen kvar: FI-registret (156) + profile2?isin= (gratis, verifierad.
   Modulen finnhub_universe.py kvar för framtida betald tier.

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

---

# ROND 4 — sex förbättringar (research-baserad, 2026-08-28)

> Research utförd av evidensflottan: `docs/.opencode/audit/qmj-regim-norden-2026-08-28.md`
> + `docs/.opencode/audit/insider-reconciliation-2026-08-28.md`.
> **Tre researchbeslut:** (1) AQR QMJ Monthly har separata landskolumner
> SE/DK/FI/NO (gratis, verifierad xlsx); (2) Nasdaqs insider-tabell är
> AVPLATTFORMAD → FI insynsregister är sanningskälla — "reconciliation" blir
> FI-primär + Finnhub-korskälla + kvalitetsgrind; (3) yfinance earnings_dates
> ger EPS-konsensus/utfall/överraskning + PIT-timestamp verifierat live 3/3.

| Task | Innehåll | Fil(er) | Ägare våg |
|---|---|---|---|
| F1 | QMJ-regim: `factor_regime.py` (AQR xlsx → nordisk komposit → R12 → OOS-percentil ≥240 mån → Stark/Normal/Svag/otillräcklig) + migration 048 + `qmj_regime.yml` (mån 8:e 04:10) | ny | W1.1 |
| F2 | Insider-integritet: CSV-export primär (LEI/Status/Trading venue), fix datumfilter (Publiceringsdatum.From/To + button=export), **fix upsert-nyckel** (COALESCE(isin,ticker),name,datum,typ + volym-aggregering; Revised→UPDATE, History→skip) + `insider_reconcile.py` (FI↔Finnhub, coverage-first) + migration 049 | bef + ny | W1.2 |
| F3 | IC per signal i radarn: RadarResponse får `signal_ics` (senaste per faktor ur factor_metrics 90d) — **INGEN retention-ändring** (score_tracker 730d är ensam ägare av städning) | market_intel | W2.1 |
| F4 | Sektorrelativt värde: `qmj_scores.py` beräknar `sector_value_z` (inom-sektor n≥15, annars NULL) + `value_mode`; **kompositen behåller global value_z** (jämförbarhet över tid) + migration 050 | qmj_scores | W1.3 |
| F5 | SHA-pinning ×27 workflows (checkout 11bd7190, setup-python 8d9ed9ac, setup-node 49933ea5, **gitleaks v3.0.0 = e0c47f4f** — v2-linjen dör 2026-09-16) + `permissions: contents: read` på resten + dependabot.yml (github-actions) | .github/workflows | W2.2 |
| F6 | TS-SUE: `earnings_surprise.py` (yfinance earnings_dates → SUE z, std ≤8 kvartal, kräv ≥4, PIT-guard future) + **PIT-snapshot** (veckovis est. för kommande kvartal → estimate_source snapshot/retro) + migration 051 + `earnings_surprise.yml` (mån 04:10) | ny | W1.4 |

## Kontrakt-korrigeringar från reviewer (alla lockade)

- **F1-kolumner (live-verifierade):** header-rad ≈19 med 'DATE' i kol A; **31 kolumner** (24 ISO-koder + Global/Global Ex USA/Europe/North America/Pacific + 'None'); **nordiska serier startar 07/31/1995**; första-värde-row hittas dynamiskt per kolumn (NaN före). Sanity = NAMNGIVNA kolumner finns + ≥3 nordiska icke-NaN → WARNING inte crash. Kräv n≥240 (≈370 obs finns). Ingen French-fallback (metodmix); fallback = 'last known good + staleness' i worker_state.
- **F2:** FI CSV-export = primärkälla. Upsert: aggregera (COALESCE(isin,ticker), name, trade_date, type) → SUM(shares, amount); ON CONFLICT DO UPDATE (Revised-rad ersätter originalet); Status='History' → skip. 0-rader = varning + exit 0 (endpointPING separat). Finnhub: mät ticker-täckning först; flagga finnhub_only ENDAST vid påvisad täckning; rapportera coverage 0/N ärligt.
- **F4:** sektorpercentil kräver n≥15 i sektorn (repo-regeln n<20→universumrank), annars sector_value_z=NULL. value_mode ∈ sector|global. Komposit (10 %-vikt) = GLOBAL value_z oförändrad (IC-jämförbarhet); sector_value_z exponeras separat.
- **F6:** yfinance har INGET analytikerantal → ärlig varningstext ("konsensus kan bygga på få analytiker"). PIT-framåt = veckovis snapshot (captured_at < announce_at → använd snapshot-estimatet, estimate_source='snapshot'; annars 'retro' + flagga).
- **F7 (radar-union):** SUE **anrikar befintliga items** (LEFT JOIN) — earnings-only-tickers är INTE i all_tickers-unionen (skulle ge 5-6 None-fält + blåsa upp total).
- **F8 (cron):** qmj_regime 04:10 mån 8:e; earnings_surprise 04:10 måndag + FETCH_SLEEP 1,2-2 s + disk-cache (inget i 03-04-trängseln).

## API-kontrakt (fastställt före våg 2 — worker skriver mot detta)

- `RadarItemOut` ← lägg till: `sector: str|None`, `sector_value_z: float|None`,
  `value_mode: str|None`, `earnings_sue: float|None`, `earnings_announced: str|None`
  (ISO-datum = announced_on; PK i earnings_surprises är (ticker, announced_on)).
- `RadarResponse` ← lägg till: `signal_ics: list[FactorMetricOut]` (senaste per
  faktor, ≤5), `qmj_regime: RegimeOut|None`.
- Ny endpoint: `GET /api/market-intel/qmj-regime` → `RegimeOut` =
  `{computed_date, data_through, premium_12m, percentile, n_obs, regime,
  countries:list[str], europe_12m, global_12m}`. regime ∈ stark|normal|svag.
- SUE i radarn: senaste publicerade (announce_at < now), `earnings_quarter`
  = quarter_end ISO.

## Regim-regler (evidens: AQR-pappret + Asness et al. 2017)

- Nordisk komposit = medel av SE/DK/FI/NO-månads-QMJ (kräv ≥3 giltiga).
- R12 = 12-mån rullande; percentil OOS-expanderande; n≥240 → annars "otillräcklig".
- Buckets: pct ≥0,80 stark; ≤0,20 svag; annars normal. UI-etikett:
  "QMJ-premiens historiska kontext" + disclaimer (ingen prognos; USD; long-short).

## SUE-regler

- surprise% från Yahoo; SUE_t = surprise_t / std(surprises t-8..t-1); kräv ≥4
  tidigare, std>0; clip till ±3. Annonsering framåt i tiden → skip (PIT-guard).
- UI-etikett: "kvartalsöverraskning" — aldrig prediktion; n visas i ärlighetsrad.

## Verifiering per våg

- W1: py_compile alla ändrade/nya, `python -m pytest backend_worker/tests -q`
  (nya testfiler: test_factor_regime, test_sector_value, test_earnings_surprise,
  test_insider_reconcile — pure functions, ingen DB).
- Migrationsvakt-granskning 048–051 → applikation via `supabase db push`.
- W2: `npx tsc --noEmit` (web), py_compile API, `PYTHONPATH=. python -c
  "from apps.api.main import app; print(len(app.routes))"`.
- W3 (produktion): trigger qmj_regime.yml + earnings_surprise.yml +
  fi_insider.yml (reconcile-steg) → curl /market-intel/radar + /qmj-regime;
  ui-analys 1 spawn (radar-sidan).

## ROND 4 — SLUTSTATUS (2026-08-28, efter produktionstest)

| Punkt | Status | Produktionsbevis |
|---|---|---|
| F1 QMJ-regim | ✅ KLAR | qmj_regime.yml run ok: `premium_12m=0.003802, pct=0.3352, n_obs=361, regime=normal`; API 200 med hela kontraktet (curl-live) |
| F2 Insider-integritet | ✅ KLAR | FI CSV-export fixad (`path: csv`, datumfilter-PING-verifierad); map_rate 95 % (291/306 nyckelbara via SEED→company_profiles→universe_registry→cache); aggregate/Revised/History-semantik; reconcile run ok: `FI 195 / Finnhub 44 / both 0 / mismatch 0 / coverage 32/526 / suspicious 0` (ärligt: Finnhub-täckning 6 %) |
| F3 IC i radarn | ✅ KLAR | signal_ics-fält live (just nu `[]` = ärligt: factor_metrics tom efter Supabase-återskapandet; fylls av signal_analytics söndag) |
| F4 Sektorrelativt värde | ⚠️ KODKLAR, DATA-LÅST | `sector_value_z`/`value_mode` i qmj-scan + API + UI; MEN: sektor-backfill kräver yf.Lookup — **Yahoo blockerar GH-runnern** (query1-finance 'possibly delisted'-fel, bevisat "backfilled_names: 1"). Fylls via lokal körning / IP Yahoo godkänner; force-loop hoppar färska missar (7 d). Ärligt: radarn visar inget sektorvärde förrän data finns |
| F5 SHA-pinning | ✅ KLAR | 28 workflows 100 % pin: checkout 11bd7190 (v4.2.2), setup-python 8d9ed9ac (v5.5.0), setup-node 49933ea5 (v4.4.0), gitleaks e0c47f4f (v3.0.0; v2-dör 2026-09-16); permissions read-only ×28; dependabot github-actions LEVER (PR checkout 4.2.2→7.0.1 redan öppnad) |
| F6 TS-SUE | ⚠️ KODKLAR, DELVIS DATA-LÅST | earnings_surprise.py + PIT-snapshot + tester 13/13; 2 första GH-runs cancände på 30-min-timeout → fixad (60 min + 20 s härd tidsgräns/daemon-tråd, empiriskt verifierad); GH-throttling från Yahoo gör steget långsamt — lokal 3-ticker-dry-run 9,77 s ✓. Fylls successivt veckovis / lokalt |

**Rondens buggfynd (alla utöver planen):**
1. `gh run rerun` kör GAMAL SHA → dispatch som normalt (läxa för all framtid).
2. `insider_cluster.py` date-vs-str TypeError (rade 125/275) — fixad.
3. Constraint-krock: insider_trades.yml + insider_fetcher återskapade `insider_trades_dedup_key` (uppväckte tyst dataförlust) — nu `_ensure_reconcile_key` idempotent ×3 ställen.
4. SUE-job-timeout 30 min → 60 + 20 s-hårdgräns.
5. dependabot-PR-CI röd på FÖREXISTERANDE skuld (ai_cache BLE001, web-lint, npm test) — ej orsaken av rondens ändringar.
6. ui-analys: radarsidan auth-skyddad (redirect /login) — visuell QA kräver användarens konto; data-lagret verifierat 200.

**Kvarstående / medvetna beslut:** sektor + SUE-data beroende av Yahoo-IP-tolerans (GH-runnern blockerad): koden är PIT-riktig och testad; data fylls när körningar träffar en IP som godkänns (lokal körning ger kvitto; GH-backfill förbättras om Yahoo regleras).

---

# ROND 5 — RANKING-INTEGRITET (2026-08-29, utredning + plan)

> Fråga: "Hur kan EG (Everest Group) vara 'Mångdubblar-kandidat' (mews 72.2, f-score
> 4/9, negativa marginaler, nyheter '3 Reasons to Sell EG')?" → hela top-5 +
> mitten/botten-5 utredda mot ground truth. Utredningskvitto:
> `.opencode/audit/ground_truth_top5.md`, `.opencode/audit/ground_truth_bottom5.md`.

## A. FAKTA — topp 5 vs verklighet (ground truth, 2+ källor)

| Rank | Ticker | Systemet | Verkligt | Dom |
|---|---|---|---|---|
| 1 | VOLV-B.ST | P/E n/a, alla fundamenta NULL, kval=88, cap 580e9 SEK | P/E 19,8 (fwd 14,1), ROE 21 %, yield 3,8 % | Legitim — MEN raden har NULL-data; kvalitetspoäng ej förankrad |
| 2 | DIVISLAB.NS | P/E 42,67, D/E −24,76, f-score 4, mom 97 | P/E ~84, nettokassa, ROE 16 % | Övervärderad (pris ovanför riktkurs), skräpdata ger "billig" |
| 3 | SAND.ST | alla fundamenta NULL, kval=80, heltalsscores | P/E 26, ROE 18 %, +24 % org Q2 | Legitim kvalitet — men rådata NULL |
| 4 | ALFA.ST | alla fundamenta NULL, kval=78 | P/E 29, ROE 19 %, order +35 % | Legitim — men dyr (upside +2 %) |
| 5 | APP | P/E 0,39 (!), ROA 0,4, D/E 27,94 | P/E ~24, ROA 46 % (0,4 ≈ rätt), D/E 1,11 | P/E och D/E är skräp → "billigaste" av alla; momentum brutet (−50 % från topp) |

**Mönster:** 3 av 5 topprader (VOLV/SAND/ALFA) har NULL-fundamentals + heltals-scores
som liknar batch från annan källa/pipeline (smallcap/nordic) — CSV:erna (420 rader,
0 .ST-rader) innehåller INTE dessa radvärden. Rankingen bygger delvis på
proveniens-inkonsistens, inte på verkliga nyckeltal. APP/DIVISLAB vinner pga
korrupta värden (P/E 0,39; D/E −24,76 → risk-score straffas inte).

## B. FAKTA — mitten/botten 5 vs verklighet (systemets fel, inte aktiernas)

| Ticker | Systemet | Verkligt | Dom |
|---|---|---|---|
| SEB-A.ST | pe −0,26, roa −0,02, gm −0,42, **f-score 0** | P/E 13,5, ROE 14–16 %, CET1 17,2 %, yield 5 % | Grovt felrankad |
| FFH.TO | pe −17,51, de −1,65 | P/E 8, P/B 1,02, ROE 16,5 %, +21 % upside, återköp | Grovt felrankad (mews 68,9 — strax under flaggan) |
| BLK | pe 7,28, gm −0,03, **f-score 4** | P/E 27,8, GM 47 %, AUM $15,3T rekord | Grovt felrankad |
| UMG.AS | pe 64,54, de 90,81 | P/E 82–84 (distorderat), fwd 18–20, de 0,73, +32–47 % upside | Delvis fel — de 90,81 är skräp |
| BURE.ST | de −50,01, roa −0,14, gm −0,42 | Investmentbolag: P/B 0,95, NAV-rabatt 5–6 %, NAV +28 % H1 | Fel måttstock (P/E/ROA/gm meningslöst för inv.bolag) |

**Mönster:** banker/försäkring/investmentbolag får konsekvent absurda `.info`-värden
(negativ gm, negativ D/E, negativ CR, negativ P/E) → straffas i kvalitet/risk/f-score
→ systematisk felrankning av HELA financials-sektorn, både uppåt (mews!) och nedåt.

## C. ROTORSAKER (verifierade, fil:rad)

| # | Bugg | Bevis | Effekt |
|---|---|---|---|
| R1 | **price=NULL för 418/426 rader** — `current_price` produceras (data_fetcher.py:739/775) men `price`-kolumnen i SCAN_COLUMNS (db_loader.py:20) får ALDRIG den; mock-fallback hårdkodar 100.0 (stocks.py:432-438) | portfolio.py:44 kommentar "currently NULL for every ticker" | **Priskurvan på aktiesidan är FABRICERAD** (mock-candles slutar på 100.00 kr) |
| R2 | **dividend_yield ×100 i UI** — lagrat ÄR procent (2.19 = 2.19 %; CSV:306 bevis: 8/370,11) men VerdictCard.tsx:98 ×100 och StockView.tsx:418 `formatPct` (×100) | skärm: 219.00 % | Felaktig direktavkastning på alla sidor |
| R3 | **MAX_DIVIDEND_YIELD = 0.15 (fraktion) mot data i %** — clip(upper=0.15) klipper ALLT över 0,15 % (scoring.py:34,678) | score_dividend = 67,74 för ~alla rader | Dividend-faktorn död (konstant) |
| R4 | **pe_trailing = rå yfinance** utan sanity — 164/426 negativa (NVDA −2,28, AAPL −1,72, EG −13,1) | data_fetcher.py:685 | "Billig"-signaler + felaktig display |
| R5 | **Ingen financials-branch** — banker/försäkring får gm/försäljnings-D/E/CR som är meningslösa/negativa (SEB gm −0,42, EG cr −1,08) | data_fetcher.py:694-706, grep "Financial" = 0 | F-score 0–4 för bra banker (SEB), F-score 4 för EG trots ROE 14 % |
| R6 | **Market cap i blanda valutor i size-score** — SEK (VOLV 580e9) vs USD (NVDA 5,45e12) utan FX | scoring.py:645-665, currency.py har FX-karta men används ej | Size-poäng felaktig för icke-USD |
| R7 | **MEWS sektorblind + fillna(0)-buggar** — `_f_low_ps`/`_f_operating_leverage`/`_f_clean_accruals` fillna(0) → percentil; `_f_clean_accruals` ascending=False → 0 = "ren" = HÖG poäng; `_f_small_size`/`_f_low_ps` belönar försäkringsstruktur (premieintäkts-P/S är strukturellt lågt) | smallcap/mews.py:30-122 | **Alla 4 mews-flaggor = Financial Services (3) + Consumer Defensive (1), alla med piotr ≤ 5** |
| R8 | **MEWS 3/6 signaler = median-fill** — EG's operating_leverage/revenue_accel/clean_accruals = 50,04 exakt (saknad data → `_percentile_score` median) | mews.py:61-105, smallcap/scoring.py:80 | Flagga sätts på 72,2 med 3/6 signaler som är "inga data" |
| R9 | **Ingen kvalitetsgate på mews-flaggan** — piotroski 4, roa −0,42 %, rev −21,6 % BLOCKERAR inte flagga | mews.py:147 (endast score ≥ 70) | Badge "Mångdubblar-kandidat" på usel fundamenta |
| R10 | **Mångdubblar-vyn sorteras på score_total** — sort_by deklareras (screener.py:35) men rad 44 hardkodar score_total; useMangdubblare.ts:29 → mews-vyn = RNR/PRU-ordning, inte mews-ordning | screener.py:35-44 | Vyn visar inte bästa mews-kandidater |
| R11 | **Renormalisering cap 3.0** — NaN-delscore → fillna(0) med vikt räknad → skala ×3 (scoring.py:867) | EG score_value=NULL | Saknad value-faktor blåser upp övriga |
| R12 | **Nyhets-bäring används ej i scoring** — news_events-bearing klassificeras (radarn) men kopplas aldrig in; aktiesidans nyheter är display-only (stocks.py:623-667) | grep-sweep bevis | "3 Reasons to Sell EG" påverkar INGET |
| R13 | **data_quality mäter närvaro, inte riktighet** — 0,875 för EG trots 6/8 skräpvärden; MIN_DATA_QUALITY=0.5 | config.py:182 | Skräpdata passerar kvalitetsporten |

## D. FIX-PLAN (reviderad efter reviewer-gate 2026-08-29; blockerande fynd inarbetade)

> **ENHETSBESLUT (låst): dividend_yield normaliseras till FRAKTION 0-1 i T1**
> (2.19 % → 0.0219). UI behåller ×100 (VerdictCard/formatPct) → visar 2.19 %.
> MAX_DIVIDEND_YIELD 0.15 (= 15 %) stämmer då. FilterRail(/100) + themes(0.02) konsistenta.

### P0 — Data-lagrets korrekthet
- **T1** `stock-scanner/core/data_fetcher.py` — sanity + enhetsnormalisering i
  `extract_metrics`:
  - `pe_trailing`/`pe_forward`: ≤ 1 eller icke-finit → NULL (fångar negativa OCH
    APP:s 0.39); övre gräns > 200 → NULL;
  - `dividend_yield`: `if v > 1: v = v/100` (2.19 → 0.0219); icke-finit → NULL
    (hädanefter fraktion 0-1 hela vägen);
  - `debt_to_equity`: `clip(lower=0)` (NEGATIV → 0, ej NULL — bevara legitima
    nettokassa-bolag/negativt eget kapital); övre gräns 200 → NULL; `current_ratio`
    clip(lower=0), övre gräns 20 → NULL;
  - `roa/roe/gm/om`: |v| > 5 → NULL (aldrig >100 %); icke-finit → NULL.
  Verifiering (CSV): 0 st negativa pe; 0 st de < 0; APP pe=24.x (ej 0.39);
  EG divYield=0.0219.
- **T2** `stock-scanner/core/data_fetcher.py` — financials-branch på RIKTIGT
  sektorfält: `info.get("sector")` hämtas redan (data_fetcher.py:677) och finns i
  score-universumet. För `sector in (Financial Services, Real Estate)`:
  `gross_margin=NaN`, `current_ratio=NaN`, `debt_to_equity` åsidosätts av en
  financials-variant; kvalitetsmått = ROE + profit_margin (bank/insurance-normal).
  INGEN ticker-suffix-heuristik (suffix = börs, inte sektor). Verifiering: SEB
  gm=NULL (ej −0.42), SEB roe > 0.
- **T3** `marketscan/backend_worker/db_loader.py` + `apps/api/routers/stocks.py`:
  (a) mappa `current_price` → `price` i SCAN_COLUMNS (price blir icke-NULL);
  (b) mock-candles (stocks.py:432-438) OCH mock score-history (stocks.py:442-459):
  kräv äkta data, annars 404/"ingen data" — inget fabrikat.
  Verifiering (DB, ej CSV): `/api/stocks/EG/price-history` slutar på 370.11;
  `SELECT count(*) FROM scan_results WHERE price IS NULL` = 0.
- **T3b** **DB-cleanup + backfill (semantisk datamigrering — kräver
  migration-vakt + användarens applikationsgodkännande, se Migrationsprotokollet)**:
  engångs-SQL: `pe_trailing=NULL WHERE pe_trailing<=1 OR pe_trailing>200`;
  `debt_to_equity=0 WHERE debt_to_equity<0`; `dividend_yield=dividend_yield/100
  WHERE dividend_yield>1`; + backfill `current_price→price`. Skäl: COALESCE-upsert
  (db_loader.py:180-225, replace=False) skriver ALDRIG NULL över befintligt skräp
  — gamla pe=−13.1/de=90.81 ligger kvar tills en full replace. Bakgrund: gamla
  rader → skräp till NULL → T12 visar "—".
- **T4** (reviderad — EJ "ta bort ×100"): efter T1-normalisering → verifiera att
  ALLA UI-konsumenter är konsistenta med FRAKTION: VerdictCard.tsx:98 (×100 ✓),
  StockView.tsx:418 (formatPct ✓ — Intl ×100), FilterRail.tsx:166-167 (/100 ✓),
  themes.ts:38 (0.02 ✓). EG visar 2.19 % (ej 219.00 %). Alla fyrar läses; ev.
  dubbel-division fixas; icke-finit → "—".
- **T5** `stock-scanner/core/scoring.py:678` — bekräfta MAX_DIVIDEND_YIELD=0.15
  mot fraktion (låst beslut ovan); ingen kodändring förväntas, enbart enhetstest
  (EG 0.0219 → inte clippad; spridning i score_dividend, ej konstant 67,74).
- **T9 (flyttad från P2 till P0)** Piotroski financials-variant: banker/försäkring/
  REIT — F6 (CR), F8 (gm), F9 (om) ersätts/neutraliseras och ROE/profit_margin-
  standard används (piotroski.py:207-260, sektor-medveten). Verifiering: SEB
  f-score ≥ 5, EG f-score ≥ 6 i ny CSV. (T2:s verifieringskriterium kräver denna.)

### P1 — MEWS-integritet + sektorrättvisa
- **T6** `stock-scanner/smallcap/mews.py`:
  (a) `_f_low_ps`: Financial Services exkluderas (premieintäkter ≠ försäljning);
      `ps <= 0` → median-fill i stället för fillna(0);
  (b) alla `fillna(0)`-sites (mews.py:36, 78, 105, 122) → `fillna(serie.median())`
      — median = neutral ~50, INTE 0 = "ren"/"billigt" (gäller särskilt
      `_f_clean_accruals` ascending=False: 0 = HÖG poäng idag). Ingen ändring i
      delade `_percentile_score` (smallcap/scoring.py:80) — blast radius;
  (c) `_f_operating_leverage`: teckenkoll på opinc_ttm (ej bara prev);
  (d) `_f_small_size` OCH `calc_size_score` (scoring.py:645-665): USD-normaliserad
      cap (återanvänd `_FX_TO_USD`-mönstret i db_loader.py:43-72) — blandvalutan
      kvarstår i size-signalerna annars.
  Verifiering: EG mews ≤ 65 (_f_low_ps exkluderad + neutrala medianer);
  mews_flag=False.
- **T7** `stock-scanner/smallcap/mews.py:147` — kvalitetsgate: flagga kräver
  `mews_score ≥ 70 AND piotroski_f ≥ 5 AND roa > 0 AND coverage ≥ 4/6 med äkta
  data, inklusive fcf_yield (vikt 0.25 — starkaste prediktorn får inte saknas)`.
  Verifiering: alla flagged har piotr ≥ 5, roa > 0, fcf_yield icke-neutral.
- **T8** `marketscan/apps/api/routers/screener.py:44` — sort_by-respekt
  (mews_score när mews_flag=true); `apps/web/hooks/useMangdubblare.ts:29`
  skickar `sort_by=mews_score`. Verifiering: /api/scan?mews_flag=true&sort_by=mews_score
  returnerar mews-desc.
- **T10** Nyhets-bäring → sentiment: `news_events.bearing` (nasdaq/gnews/ddgs,
  redan klassad) fogas in i sentiment-kedjan; 72 h-fönster, viktad direktbäring;
  EG (3 negativa artiklar aug) får sentiment_raw-minskning. UI-märkning
  "nyhetsbias" (aldrig "alpha"-claims — repo-textregel).
- **T11** `stock-scanner/core/scoring.py` — renormaliseringsclip cap 3.0 → 1.5
  på BÅDA site:na (rad 867 icke-sektorpathen OCH rad 886 sektorpathen — den
  senare är live: df har sector + SECTOR_FACTOR_WEIGHTS finns i config.py:115);
  logga när scale > 1.2 + UI-varning "N-data saknas" i stället för tyst uppblåst
  poäng.
- **T12** UI ärlighet (sista försvarslinjen): VerdictCard/StockView — om
  price/pe/de/gm saknas eller är omöjliga → "—" i stället för råvärdet.

### P2 — Proveniens + efterkontroll (top-5-mönstret "NOLL-fundamentals-meny")
- **T15 (NY) Proveniens-spårning .ST-rader**: VOLV-B.ST/SAND.ST/ALFA.ST har
  NULL-fundamentals + heltals-scores (84.0/77.0/75.0) + ml_rank (3/8/9) och
  saknas i scored_universe CSV:er (420 rader, 0 .ST) — de matas in från en ANNAN
  källa (smallcap_scored_*.csv? ML-ranker? qmj? seed_demo?). Uppdrag: identifiera
  exakt källa + vilken pipeline-rad som skrev dem; lägg till `source`/`coverage`-
  markör i scan_results (om bucket saknas: tyst nolla) och säkerställ att
  .ST-aktier är lika kompletta som övriga. Verifiering: VOLV-B.ST har
  roe/pe/price icke-NULL i DB + proveniens dokumenterad.
- **T13** Golden-sample-gate (regression-vakt): NVDA pe>0, SEB roe>0, EG divY
  0.01–0.05, VOLV price≠NULL, mews-flagga kräver piotr ≥ 5, ingen mock-priskurva.
  Verifiering MOT DB (ej CSV).
- **T14** Före/efter-regression av rankningen: DB-statistik-jämförelse per körning
  (negativa pe/de-räknare, NULL-räknare, mews-flagga-set) PLUS top-50-listan
  före/efter viktningsändringar (legitima kandidater får inte tappas) + avisering
  vid regression.

## E. VERIFIERING PER VÅG
- W1 (P0): py_compile stock-scanner; lokal `daily_pipeline` mot 5 tickers
  (SEB-A.ST, EG, NVDA, VOLV-B.ST, BLK) → CSV- OCH **DB**-granskning av
  T1/T2/T3-värden (COALESCE-fällan: CSV räcker inte).
- W2 (P1): unittest mews (fixturer: finansiella, växt med saknad data, negativa
  värden) + `python -c "from apps.api.main import app; print(len(app.routes))"`.
- W3 (P2/P3): `npx tsc --noEmit`; smoke-test mot staging; regression-vakt
  (golden-sample) 1×/milestone; top-50 före/efter-jämförelse.
- **Migrationsvakt:** T3b är en SEMANTISK datamigrering (ej schema) → enligt
  Migrationsprotokollet §2b krävs migration-vakt-granskning + användarens
  uttryckliga godkännande innan applicering. Schemaändringar: inga i denna rond.

## F. ROND 5 — STATUS 2026-08-29 (implementering klar; applikation väntar på DB-nyckel)

| Task | Status | Bevis |
|---|---|---|
| T1 sanity+enheter (data_fetcher) | ✅ | +152 rader; 5/5 test_data_fetcher; OK1/OK2 + edge-batteri; py_compile |
| T2 financials-branch (data_fetcher) | ✅ | sektor-fält använt (inget suffix); gm/cr NULL för Financial Services/Real Estate/Insurance |
| T3 price-mappning + mock-bort | ✅ | db_loader current_price→price (4 fall verifierade); stocks.py: `_generate_mock_candles`/`_generate_mock_score_history` HELT borttagna (grep 0 i kod); tom lista i stället för fabrikat |
| T3b DB-cleanup (054) | 🔴 **VÄNTAR APPLICERING** | 054 skriven + migration-vakt APPROVED (efter ml_rank-skärpning); kräver DATABASE_URL — `.env.local` har tom nyckel → **kräver användarens nyckel** |
| T4 UI-konsumenter fraktion | ✅ | VerdictCard ×100 / formatPct / FilterRail /100 / themes 0.02 alla konsekventa med fraktion — inga ändringar behövdes (utom displayValue-T12) |
| T5 MAX_DIVIDEND_YIELD 0.15 | ✅ | stämmer mot fraktion (enhetstest bevisar) |
| T6 mews-fix | ✅ | fillna(0)→median-flöde; low_ps-sektormask; opinc_ttm>0; median-fill avsiktlig; 9/9 test_mews; INSUR-block-mönstret bevisat (44.0 → flag False) |
| T7 kvalitetsgate | ✅ | piotr≥5 + roa>0/roe-fallback + coverage≥4 + **fcf_yield-krav** (reviewer-fynd); och **pipeline-ordningen fixad**: MEWS körs nu EFTER Piotroski (daily_pipeline 1259-1273) — annars var gaten alltid ofullständig |
| T8 sort_by | ✅ | screener.py:44 `.order(sort_by)`; useMangdubblare skickar `sort_by=mews_score` |
| T9 Piotroski financials | ✅ | SEB-lik bank: f-score 7 (var 0); industri-kontroll oförändrad (8) mot HEAD; 15/15 test_piotroski |
| T10 nyhets-bäring | ✅ | news_bias.py (5/5 tester; 229/229 och 224/224 backend_worker-suites vid respektive wave); entrypoint non-fatal-anrop; 053_news_bias.sql APPROVED |
| T11 renormalisering | ✅ | MAX_RENORMALIZATION=1.5 på BÅDA site:na (867+886); varningsprint >1.2; bevis: 1.21 för 9/10, 1.50-cap för 4/10 |
| T12 UI-ärlighet | ✅ | displayValue i format.ts; pe/de/gm-gränser i VerdictCard + StockView (gm sektor-villkorad); news_bias-badge; tsc + vitest gröna |
| T13 golden-sample | ✅ | `scripts/ranking_sanity_gate.py` — kördes: RÖD (korrekt nuläge: NVDA −2.28, SEB roe −0.07, EG 2.19, mock-100.0, 277 pe-anomalier, 151 de<0, 418 price NULL, 1 seed-rad kvar) |
| T14 före/efter | ✅ | baseline-JSON-param i gaten; top-50-jämförelse görs vid första applikation |
| T15 proveniens .ST-rader | ✅ | **rotorsak: `supabase/seed.sql` (hårdkodade demovärden, exekverad 2026-08-28)!** INTE pipelinen. VOLV-B.ST 84.0 = seed-rad som aldrig skrevs över (COALESCE + .ST-rate-limit). seed.sql fick VARNING-kommentar; raderna tas bort av 054-steget 6 |

**Gates körda (ledaren, faktisk utdata):** py_compile 6 filer OK · 29/29
(test_mews+piotroski+data_fetcher) · 9/9 test_mews efter ordningsfix · 229/229 +
224/224 backend_worker · 153 routes oförändrat · tsc via `npm run type-check`
EXIT=0 · vitest 13/13 · ruff clean · migration-vakt: 053 APPROVED / 054
NEEDS_REVISION → skärpt med ml_rank → APPROVED.

**LÄRDOM VÅG 1 (git-backförlust):** worker-spawnarna lämnade plötsligt 76
ändrade filer (30 850 deletioner i reports/ + data/*) — upptäckt av verify-gate,
återställt med `git checkout -- reports/ data/` + regenererad
scored_universe_2026-08-28.csv från parquet (420 rader, identiska data).
Orsak: oklar (worker-test-körning); lärdom: **kör `git status` före OCH efter
varje wave + commits av egna steg**. Inga data förlorade.

**KVASTAR (kräver dig):**
1. ~~Applicera migrationerna~~ ✅ **KLART 2026-08-30**: 053–059 applicerade +
   journalförda (001–059 komplett). Sanity-gate GRÖN.
2. ~~Lägg DATABASE_URL / applicera~~ ✅ **KLART**: DATABASE_URL i working_dsn +
   `.env.local`; alla migrationer körda via psql-poolem (6543).
- W1 (P0): ~~py_compile stock-scanner; lokal daily_pipeline~~ ✅ **KLART**:
   lokalt verifierat (NVDA pe -4.89→NULL, divY 0.44→0.0044, de -34.9→0).
- W2 (P1): ~~unittest mews/piotroski~~ ✅ **KLART**: 481/482 + 229/229.
- W3 (P2/P3): ~~tsc; smoke; regression-vakt~~ ✅ **KLART**: npm run type-check
  EXIT=0; sanity-gate GRÖN (pe<=1>200=0, de<0=0, seed=0, EG divY 0.0212).
- **Migrationsvakt:** T3b var SEMANTISK datamigrering → vakt-granskad +
  användarens explicita order → godkänd och applicerad. Schemaändringar: inga.
