# MARKETSCAN — MASTERRANK R14: SEGMENTINTEGRITET & SEGMENTDIFFERENTIERING · ANTIGRAVITY-HANDOFF

> **ARKIVERAD 2026-09-01:** Denna plan är IMPLEMENTERAD (commits 9469c5b..7c4f1ee). Arkiverad från PLAN.md innan R15-planen skrev över den (R14 var ej committad). Efterföljande plan: R15 (DRIFTÅTERSTÄLLNING & STREET-PARITET).

> **Vem:** Google Antigravity (eller annan coding-agent). **Vad:** kör hela programmet nedan i task-ordning 1→8.
> **Var:** Windows. Workspace-root: `C:\Users\hthur\OneDrive\Desktop\marketscan`. Alla sökvägar relativa roten om inget annat sägs.
> **Denna plan ersätter** tidigare AI-usage-reduction-plan som låg i PLAN.md (återfinns i git-historiken: `git show HEAD:PLAN.md`).
> **Utfärdad:** 2026-09-01 av plan-agent (opencode/GLM-5.3) efter live-verifiering mot produktions-API, kodgranskning och 2 research-rapporter. Godkänd av ägaren.

---

## REGELVERK (gäller alla tasks — bryt aldrig)

**Regel 0 — Code wins over book:** Om radnummer förskjutits, filer flyttats eller en gate fejar: verifiera själv, anpassa, dokumentera avvikelsen i slutrapporten. Planen är ett recept, inte en religiös text. "Koden vinner över boken vinner över gamla dokument."

**Regel 1 — Kör aldrig en gate du inte kört:** Rapportera FAKTISK kommandoutdata (kommando + resultat) i slutrapporten. "NEVER claim a check you did not run." Svep alltid nya/ändrade symboler med grep (call sites + display sites) och uppdatera varje träff — inget funnet ska sägas explicit.

**Regel 2 — Windows-encoding (kritisk):** PowerShell 5.1 `Set-Content`/`Get-Content`/`Out-File` dubbelkorrumperar svenska tecken (å/ä/ö → `â€"`). Skriv/editera ALLTID UTF-8-filer via edit-verktyget eller .NET: `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`. Misstänkt korruption: `git grep -l "Ã¤\|â€\|Ã¶" -- <sökväg>`.

**Regel 3 — Git:** Conventional commits (feat/fix/chore/docs + scope), EN commit per avslutad task. Ingen push utan uttrycklig tillåtelse. Committa aldrig `.env`, secrets, tokens eller PII.

**Regel 4 — Projektlagar (från CLAUDE.md, absoluta):**
1. `backend_worker/` får ALDRIG importeras av `apps/api/`. `pandas`, `xgboost`, `scipy`, `yfinance` är förbjudna i API-bundeln (Vercel 500MB-tak).
2. Synkrona Supabase-handlers i FastAPI = vanliga `def` (ALDRIG `async def` — annars blockeras event-loopen).
3. Migrationer körs MANUELLT i Supabase Dashboard SQL Editor — skapa filen i `supabase/migrations/`, kör den INTE själv. Nya kolumner kräver explicit `GRANT SELECT ON ... TO anon, authenticated;` (mönster: `supabase/migrations/023_grant_table_privileges.sql`).
4. Inga emojis i UI — linjeikoner från `lucide-react`. Alla finansiella värden renderas med `<InfoTooltip>`.
5. React 18.3-låsning (uppgradera ej till 19 — Radix UI bryts). Next.js 15: route-params är async promises (`const { ticker } = await params`).
6. Codex-dokument (`docs/codex/`) uppdateras IN-PLACE när kod ändras (Task 7 sköter detta).
7. `service_role`-klienten (`get_supabase_admin`) endast bakom `require_admin`.
8. `DATABASE_URL` i produktion = Supabase Session Pooler (port 6543).

**Regel 5 — STOP-villkor:** En gate misslyckas → stoppa, rapportera exakt utdata, vänta på mänskligt beslut. Live-fynden F1–F8 (§1) reproduceras inte vid omverifiering → dokumentera avvikelsen innan du fortsätter. Radera aldrig data — arkivera. Flytta aldrig, ändra aldrig i `docs/codex/`-innehåll utöver Task 7.

---

## 0. BAKGRUND & MÅL

MarketScan är en aktieanalysplattform (Next.js 15.5 frontend på Vercel + FastAPI API på Vercel + Supabase Postgres eu-north-1 + GitHub Actions-worker `backend_worker/`). Kärnan är **MasterRank** (0–100): 8 viktade block — quality 25 %, value 15 %, momentum 15 %, analyst 15 %, insider 10 %, catalyst 10 %, payout 5 %, growth 5 % — med anti-bubbelgrind, PIT-softblock och segment-relaterade tier-trösklar (småbolag T1 ≥ 62, storbolag T1 ≥ 75). Universum ~800 aktier (nordiskt + globala storbolag).

**Problem (verifierat live 2026-09-01):** systemets segmentdifferentiering — skillnaden mellan småbolag och stora/medelstora — är rätt designad i motorn men matas med korrupt data. Mega-caps klassas som mikro-bolag och får småbolagströsklar; flera block är döda eller degenererade för globala tickers; småbolagstabellen är tom; en skyddsmotor är död kod.

**Mål:** (1) återställa korrekt segment-/blockdata, (2) implementera research-baserad segmentdifferentiering enligt besluten D1–D8, (3) validera historiskt och med sanity-gates.

**Scope/boundaries — detta görs INTE:** ny datakälla (Börsdata/Millistream-licens), ML-omträning, React/Next-uppgradering, portfölj-/riskmoduler, globala fundamentalia-korruptionen F6 (namnges som P3 i §6), warrant/TO-utspädning (finns redan i `backend_worker/alpha_discovery/warrant_detector.py`).

---

## 1. VERIFIERADE FYND (live 2026-09-01) — varje task löser minst ett F

Live-källor: `https://marketscan-api.vercel.app/api/market-intel/master/rank`, `/api/scan`, `/api/smallcap`. Topp-listan just nu: MU 71.3 · PETR4.SA 70.5 · BMY 69.4 · 2914.T 68.0 · MSFT 66.2 · 2330.TW 65.9 — **alla T2, ingen T1 i hela storbolagsuniversumet** (orsak: döda block, F2/F7).

| # | Fynd | Bevis (file:line / live) | Lösas i |
|---|---|---|---|
| **F1** | **Segmentdata korrupt:** SAP SE (€300B) och Equinor klassas `micro_cap` med `market_cap: null` → SAP får T1 "STARK" (63.4) via småbolagströskeln 62 som storbolag aldrig når (75). GMG.AX likaså micro_cap. | Live: `scan?segments=micro_cap` (SAP.DE `segment=micro_cap, market_cap=null, tier=T1, entry_signal=STARK`; EQNR.OL `low_liquidity=true`). Kod: `backend_worker/db_loader.py:173` `_derive_segment`; `backend_worker/pipeline/entrypoint.py:29-34`; `backend_worker/tests/test_roe_pe_raw.py:101-104` bevisar SAP → large_cap *när* mc finns. Docs kap 2 §4.5 hävdar "unknown, aldrig micro_cap" — live bryter mot detta. Rotorsak i null-mc-sökvägen: `not verified` (diagnos i Task 1). | T1 |
| **F2** | **Katalysatorblocket (10 % vikt) är en konstant:** `catalyst_z = 15.5555` för alla utdelningsaktier = dividend-proxy `(45−17)/45×100×0.25`, och etiketten `:earnings` är hårdkodad fel — alla topp-aktier visar identiska `"2026-09-16:earnings"`. | Matematik: `(45−17)/45×100×0.25 = 15.5556` matchar live exakt. Kod: `backend_worker/catalyst_fetcher.py:57` (dividend-approx `today.replace(day=15)+32d` → 16 sep när fetchern körde ~30 aug; `days_until=17` ✓), `:95` (conf_mult 0.25 för "low"), `:97` (ramp); `backend_worker/master_rank.py:863` (`f"{next_ev[0]}:earnings"` oavsett event_type). Äkta earnings-snapshots saknas för globala tickers. | T3+T4 |
| **F3** | **Screenerns MasterRank-sort är falsk:** `sort_by=master_rank` för-sorterar i DB på `score_total`, sedan Python-omsortering → aktier med hög MasterRank utanför top-N på `score_total` syns aldrig. | `apps/api/routers/screener.py:146` (`db_sort = … else "score_total"`), `:152` (`.order(db_sort, desc=True)`), `:164-165` (Python re-sort efter pre-selection). Live: Keyence (mr 65.3) listas före BMY (69.4) — ordning följer score_total (76.26 > 74.48). | T2 |
| **F4** | **Småbolags-endpoint död:** `/api/smallcap` returnerar `[]` — läser tabellen `smallcap_results` som är tom i produktion. | Live: `/api/smallcap?limit=10` → `[]`. Kod: `apps/api/routers/smallcap.py:39`. | T6 |
| **F5** | **Docs/kod-drift:** docs kap 1 §4 säger "T1 kräver ≥6/8 block"; koden cappar bara vid <4 (stora) / <3 (små). | `backend_worker/master_rank.py:511` (`min_blocks = 3 if is_small else 4`). | T7 |
| **F6** | **Globala fundamentalia korrupta/NULL:** Keyence gross_margin 17.9 % (real ~80 %), TSMC 7.2 % (real ~57 %); `roe_raw: null` medan `roe` finns (BMY 0.3491); `change_pct`/`vol_20d`/`currency` null i många rader; MEWS-komponenterna `operating_leverage`/`revenue_accel`/`clean_accruals` konstanta 50.0419 (aldrig beräknade). | Live-svar (Keyence/TSMC/BMY-rader). Rotorsak ej utredd: `not verified` → P3 (§6). | P3 |
| **F7** | **Analytikerblocket partiellt dött globalt:** `analyst_z: null` för MU/MSFT/BMY/PETR4/2914.T/7733.T/NEM trots att yfinance har riktkurser — men non-null för 2330.TW (33 analytiker), 000660.KS (38), DIVISLAB.NS (29), GMG.AX (14), EQNR.OL (25). Partiell täckning = batch-/timeout-/retry-gap, inte nordisk-only-scope. | Live master/rank + scan-svar. | T3 |
| **F8** | **Runway-skölden är död kod i produktion:** `fuse()` läser `cash_runway_months` men `master_rank_run` sätter aldrig fältet i values-dict → Smallcap Runway & Dilution Shield triggar aldrig live (endast enhetstestet). Dataproducent finns: `fundamentals_fetcher.py:232` → `smallcap_scanner.py:50` → `smallcap_results` (tom, F4). | `backend_worker/master_rank.py:468-479` (sköld) vs `:889-930` (values.append utan fältet); `backend_worker/fundamentals_fetcher.py:232`; `backend_worker/smallcap_scanner.py:50`; `backend_worker/tests/test_master_rank.py:499-503` (enda triggern). | T4+T6 |

---

## 2. LÅSTA DESIGNBESLUT (D1–D8) — genomför i Task 4–6

Grundade på research-rapporterna (§3). Dessa beslut är låsta; öppna endast vid verifierade nya fakta.

- **D1 — Basvikter identiska alla segment; enda undantag value i småbolag:** small/micro: `value 0.15→0.18`, `growth 0.05→0.02` (summa förblir 1.00). Evidens: value-premien är koncentrerad till småbolag (Israel & Moskowitz 2013, JFE; Fama-French 2012). INTE fulla per-segment-viktuppsättningar (överfittningsrisk; institutionell norm är normalisering, inte vikter).
- **D2 — Kvalitets-junk-gate i small/micro:** `quality_z < 55` → kan aldrig nå T1 (rank cappas 61.999, flagg `junk_gate`). Gate, inte viktändring. Evidens: Asness m.fl. 2018 (JFE) — size-premien existerar bara kvalitetskontrollerad.
- **D3 — Normalisering inom segment×sektor** för fundamentalblock (value/quality/growth/payout); **momentum normaliseras inom segment** (prisbaserade faktorer är inte sektor-relativa). Fallback-kedja: (segment,sektor)-grupp < 5 namner → sektornivå (nuvarande krav ≥15 peers); sektor < 3 → global percentil. Evidens: MSCI FaCS (lokal medel + global std), FTSE Russell (<3 → ingen normalisering).
- **D4 — Mid_cap grupperas med large i tier-trösklar** (oförändrat; `tier_of`: `is_small = segment in ("small_cap","micro_cap")`). Momentum är storleksneutralt; mid beter sig storbolagslikt — men får automatiskt egna peer-grupper via D3.
- **D5 — Likviditet som gate + badge, aldrig poängfaktor:** grade A–F per segment; E/F i small/micro → cappas från topprank (max T3). INTE Amihud som avkastningsfaktor (friktionsanomalier replikerar inte — Hou-Xue-Zhang 2020; premien sitter i ohandelsbara namn).
- **D6 — Coverage-skalad analytikerhantering:** `analyst_count` 1–2 → shrinka analyst_z mot 50 med faktor `count/3`; 0/saknas → nuvarande renormalisering. Dispersion-straffet (finns, `master_rank.py:846-851`) behålls. Evidens: JP Morgan neutral 50.5 / MSCI 0-z-mönster; Diether m.fl. 2002.
- **D7 — Tier-trösklar behålls** (small 62/50/38 vs large 75/65/50; thin-cap 61.999/64.999) men motiveras distributionellt i docs (småbolagsfördelningar är brusigare — HXZ 2020).
- **D8 — `master_rank_pctl` (percentil inom segment, finns redan i `compute_table`) blir primära jämförelsetalet mellan segment i UI**; likviditet/utspädning/runway visas som separata badges — viks ALDRIG tyst in i composite.

---

## 3. RESEARCH-UNDERLAG (läs vid behov — innehåller alla källor)

1. `.opencode/audit/smallcap-factor-scoring-2026-09-01.md` — institutionell praxis (MSCI, FTSE Russell, JP Morgan, RAFI, AQR, Dimensional), faktoreffektivitet per storlek, normaliserings-fallbacks, likviditet, analytikertäckning. Rekommendationer R1–R6.
2. `.opencode/audit/small-cap-ranking-nordic-2026-09-01.md` — nordiska trösklar: micro_cap €30–150M / small_cap €150M–1B; omsättningsgolv SEK 500K/dag (micro) resp SEK 2M/dag (small), 20-dagars median; spread >2 % flagga; prisgolv ≥1 SEK; fritt float ≥10 %; utspädning >10 % flagga / >25 % straff / >50 % svår; runway <12 mån flagga / <6 mån svår; yfinance opålitlig för First North/NGM/Spotlight; presentationsregler (percentil inom segment×sektor, medianaer, separata badges).

Båda finns på disk (untracked i git). Citat-URL:er i rapporterna.

---

## 4. TASKS (kör i denna ordning: T1 → [T2 ∥ T3 ∥ T5] → T4 → T6 → T7 → T8)

### TASK 1 — Segmentintegritet: äkta segmentdata (P0, löser F1)

**Files:** Modify `backend_worker/db_loader.py` · Modify `backend_worker/pipeline/entrypoint.py` (endast om diagnosen pekar dit) · Create `supabase/migrations/080_segment_integrity.sql` (verifiera nästa lediga nummer först: `Get-ChildItem supabase\migrations | Sort-Object Name | Select-Object -Last 3`; docs anger 79 migrationer).

**Evidence:** F1 ovan. `_derive_segment` vid `db_loader.py:173` (läs hela funktionen + `:208-212` enhetsguard); anropare: `entrypoint.py:29-34` (`_segment_from_market_cap`, multiplicerar med 1M — kontrollera att alla anropare passerar millions); `test_roe_pe_raw.py:101-104`.

**Interfaces:**
- Consumes: `scan_results.market_cap` (USD), `_derive_segment(market_cap_usd, ticker)`.
- Produces: `_derive_segment(None)` → `"unknown"` (ALDRIG `"micro_cap"`); `"unknown"` arver storbolagströsklar automatiskt via `tier_of` (`master_rank.py:312`: `is_small = segment in ("small_cap","micro_cap")` → False).

**Acceptance criteria:**
1. Ingen rad med `market_cap ≥ $10e9` har segment `small_cap`/`micro_cap`.
2. Ingen rad med `market_cap IS NULL` har segment `small_cap`/`micro_cap` (→ `unknown`).
3. SAP.DE visas som `large_cap` (om mc återhämtats) ELLER `unknown` → storbolagströsklar → 63.4 = T3 "VÄNTA" (ej T1 "STARK").
4. `python -m pytest backend_worker/tests/test_roe_pe_raw.py -q` grönt.

**Verification** (`not run` — bygg-agenten kör): `python -m pytest backend_worker/tests/test_roe_pe_raw.py -q` → 0 fail. Efter nästa pipeline-körning: `curl "https://marketscan-api.vercel.app/api/scan?search=SAP"` → segment large_cap/unknown, tier ≤ T3.

- [ ] Diagnosera varför null-mc-rader fick micro_cap (läs `_derive_segment` + alla anropare; kontrollera gamla rader som aldrig re-derive:ats)
- [ ] Diagnosera varför `market_cap` är null för globala tickers (SAP.DE/EDP.LS/EQNR.OL — sökväg `company_info_fetcher.py`/db_loader-skrivning); fixa skrivvägen om möjligt, annars dokumentera som känd begränsning
- [ ] Fixa guard: None/icke-positiv mc → `"unknown"`
- [ ] Skapa backfill-migration (samma band + enhetsguard som `_derive_segment`: `0 < mc < 10^6 → mc × 10^6`; återderive där mc finns; null-mc → `unknown`) — påminnelse: körs MANUELLT av människan (Regel 4.3)
- [ ] Verifiera mot live efter pipeline-körning

### TASK 2 — Sann MasterRank-sort + pctl-exponering i screener (P0, löser F3)

**Files:** Modify `apps/api/routers/screener.py` · Modify `apps/api/schemas/scan.py`.

**Evidence:** F3 ovan; `screener.py:142-165`; `_enrich_with_master_rank` `screener.py:60-123`; `master_rank_pctl` beräknas i `compute_table` (`master_rank.py:564-580`).

**Interfaces:**
- Consumes: `master_rank`-tabellen (befintlig enrichment), `ScanRow` (läs `apps/api/schemas/scan.py` först).
- Produces: `ScanRow.master_rank_pctl: float | None = None`; `ScanRow.liquidity_grade: str | None = None` (kolumn från Task 5, nullable nu); true top-N-sort.

**Acceptance criteria:**
1. `GET /api/scan?sort_by=master_rank&limit=10` returnerar exakt de 10 högsta master_rank i universumet — konsistent med `/api/market-intel/master/rank` topp (ingen score_total-bias).
2. `master_rank_pctl` finns i svaret för alla rader med rank.

**Implementation note:** när `sort_by == "master_rank"`: hämta filtrerade rader UTAN DB-order (`.limit(2000)` — universum ~800), enricha, sortera i Python på `master_rank` (fallback `score_total` för rader utan rank), beskör till `limit`. `def` inte `async def` (Regel 4.2).

**Verification** (`not run`): `PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"` → tal > 0; live-curl ovan.

- [ ] Rätta sort-vägen för `sort_by=master_rank`
- [ ] Lägg till `master_rank_pctl` + `liquidity_grade` i `ScanRow`
- [ ] Verifiera top-10-paritet mot `/api/market-intel/master/rank`

### TASK 3 — Globala blockdata: äkta earnings-datum + analykertäckning (P0, löser F2+F7)

**Files:** Modify `backend_worker/earnings_surprise.py` · Modify `backend_worker/catalyst_fetcher.py` · Modify `backend_worker/analyst_fetcher.py`.

**Evidence:** F2+F7 ovan. `catalyst_fetcher.py:121-139` (`load_surprises` läser endast `earnings_surprises`-snapshots — globala tickers saknas där); `:137` (earnings conf max "medium"); `analyst_fetcher.py` scope ej läst — `not verified`, diagnosen ingår i tasken.

**Interfaces:**
- Consumes: yfinance `earnings_dates` (befintlig väg i earnings_surprise.py) och riktkursdata (befintlig väg i analyst_fetcher.py).
- Produces: populerade `catalyst_events` med äkta `event_type`/`event_date`/`confidence` för hela universumet; `analyst_estimates`-rader för globala tickers; `catalyst_z` med varians över tickers.

**Acceptance criteria:**
1. ≥80 % av large_cap-tickers har ett äkta earnings-event inom 120 dagar.
2. `catalyst_z` varierar mellan tickers (ej konstant).
3. `analyst_z` non-null för ≥70 % av large_cap efter körning (MU/MSFT/BMY ska ha data).
4. Earnings-snapshot age ≤ 45 dagar → confidence `"high"` (multiplier 1.0) så äkta earnings dominerar dividend-proxyn; dividend-proxy behålls endast som lågconf-fallback när earnings saknas.

**Verification** (`not run`): `python -m backend_worker.catalyst_fetcher --dry-run` → OK; efter pipeline-körning: live `/api/market-intel/master/rank` visar olika `catalyst_next`-datum och `analyst_z` för MU/MSFT.

- [ ] Diagnosera earnings_surprise.py:s tickerscope (varför globala snapshots saknas) och analyst_fetcher.py:s partiella täckning (batch-/timeout-/retry-gap)
- [ ] Utöka båda hämtningarna till hela universumet med retry
- [ ] Höj earnings-confidence enligt AC4
- [ ] Enhetstest: dividend-proxy utan earnings → låg z; äkta earnings ≤45d dominerar

### TASK 4 — Segment-aware MasterRank (P1, kärnan; löser F2-etikett, F8-wiring; implementerar D1–D6)

**Files:** Modify `backend_worker/master_rank.py` · Modify `backend_worker/resources/weights.json` · Modify `backend_worker/macro_regime.py` (regime-merge v2-kompat) · Test `backend_worker/tests/test_master_rank.py`.

**Evidence:** `master_rank.py:43-50` (trösklar), `:309-324` (`tier_of`), `:327-531` (`fuse`), `:549-582` (`compute_table` + pctl), `:754-757` (`build_sector_z_maps` — sektor-neutral men INTE storleksneutral), `:794` (`sector_neutral_z`-anrop), `:836-837` (momentum_z-blend), `:843-851` (analyst_z + dispersion), `:863` (`:earnings`-hardcode), `:889-930` (values.append — saknar `cash_runway_months`/`insider_buying`/`liquidity_grade`), `:1076-1077` (dubbel `fetchall()`-bugg i reweight). `weights.json` (v1, en global uppsättning).

**Interfaces:**
- Consumes: `segment` (Task 1), `liquidity_grade` (Task 5, defensivt optionell), `catalyst_events.event_type` (Task 3), `smallcap_results.cash_runway_months`/`insider_buying` (Task 6, när populerad).
- Produces: `load_weights(path, regime=None, segment=None)` med v2-schema; `resolve_weights(weights_config, segment) -> dict`; `group_percentile_z(value, peers, min_peers) -> Optional[float]`; nya flaggor i `data_missing`: `junk_gate`, `liquidity_gate`.

**Deländringar (a–i):**
- **a) Segment×sector-normalisering (D3):** ersätt `val_peers_z`-beräkningen (`master_rank.py:794`) med kedjan: (segment,sektor)-grupp ≥5 peers → percentil inom gruppen; annars sektor ≥15 (nuvarande); annars global. Ny helper `group_percentile_z` (mönster: `sector_neutral_z`, `master_rank.py:224-242`, inverted för P/E: billig → hög z).
- **b) Momentum segment-percentil (D3):** två-pass i `compute_table`: pass 1 samla `momentum_z` per segment; pass 2: för segment med ≥10 icke-null-värden, ersätt varje rows `momentum_z` med inom-segment-percentil (`pct = mean([1.0 if own >= x else 0.0 for x in peers]) * 100` — samma mönster som `master_rank_pctl`, `master_rank.py:577`); annars behåll råvärde. Sker FÖRE `fuse`.
- **c) Vikt-delta (D1):** `weights.json` v2 (exakt innehåll nedan). `resolve_weights` slår samman `segment_overrides` med bas och renormaliserar till sum 1.0. Bakåtkompat: v1-fil utan `"weights"`-nyckel hanteras som idag (`master_rank.py:347`).
- **d) Junk-gate (D2):** i `fuse`, efter Smallcap Runway Shield: `if is_small and qz is not None and float(qz) < 55.0 and rank is not None and rank >= 62.0: rank = min(rank, 61.999); missing.append("junk_gate")`.
- **e) Coverage-skalning (D6):** i `master_rank_run` efter az-beräkning (~rad 851): `tc = a.get("target_count"); if az is not None and tc is not None and 1 <= int(tc) <= 2: az = 50.0 + (float(az) - 50.0) * (int(tc) / 3.0)`.
- **f) Katalysator-etikett (F2):** `catalyst_next = f"{next_ev[0]}:{event_type}"` — bärd med verkligt event_type från evs.
- **g) Likviditetsgate (D5):** i `fuse`: `grade = row.get("liquidity_grade"); if is_small and grade in ("E","F") and rank is not None and rank >= 50.0: rank = min(rank, 49.999); missing.append("liquidity_gate")`. Grade "D" → badge endast, ingen cap. "unknown"/None → ingen cap.
- **h) Reweight-bugg:** `main()` rad 1076-1077 — en `fetchall()`, bygg båda mappningarna från samma resultat.
- **i) F8-wiring:** `master_rank_run` hämtar `cash_runway_months` + `insider_buying` från `smallcap_results` (LEFT JOIN eller andra query) NAR tabellen är populerad (Task 6); om tom → skölden förblir vilande, dokumenterat.
- **Regime-kompat:** `macro_regime.compute_smoothed_regime_weights` måste applicera merge på `config["weights"]` och passera `segment_overrides` oändrat. Testa: `load_weights(regime=...)` returnerar dict med båda nycklar.

**weights.json v2 (exakt):**
```json
{
  "version": 2,
  "comment": "MasterRank weights v2 (ROND 14). segment_overrides slås samman med basvikter per rad i compute_table; regime-merge (macro_regime) appliceras endast på 'weights' och bevarar segment_overrides.",
  "weights": {
    "quality": 0.25, "value": 0.15, "momentum": 0.15, "analyst": 0.15,
    "insider": 0.10, "catalyst": 0.10, "payout": 0.05, "growth": 0.05
  },
  "segment_overrides": {
    "small_cap": {"value": 0.18, "growth": 0.02},
    "micro_cap": {"value": 0.18, "growth": 0.02}
  },
  "caps": {"analyst_max_share": 0.15, "renormalize_max": 1.5},
  "hysteresis": {"ic_up": 0.03, "ic_down": -0.02}
}
```

**Acceptance criteria:**
1. a) `val_peers_z` för en small_cap jämförs mot (small_cap, sektor)-peers när gruppen ≥5; fallback-kedjan testbar.
2. b) momentum_z = inom-segment-percentil för segment med ≥10 medlemmar.
3. c) Effektiva vikter för small/micro: value 0.18, growth 0.02; large/mid oförändrade; sum 1.00.
4. d) small/micro med `quality_z < 55` kan aldrig nå T1 (cap 61.999, flagg `junk_gate`).
5. e) analyst_z med 1–2 analytiker shrunkas mot 50; ≥3 oförändrat.
6. f) `catalyst_next` visar verklig event-typ.
7. g) small/micro + grade E/F → max T3 (flagg `liquidity_gate`).
8. h+i) Rewight mappar båda korrekt; runway-skölden triggar med data från `smallcap_results`.
9. Regime-merge bevarar `segment_overrides`.
10. `python -m pytest backend_worker/tests/test_master_rank.py -q` grönt med NYA tester per criterion.

**Verification** (`not run`): `python -m pytest backend_worker/tests/test_master_rank.py -q` → 0 fail; `python -m backend_worker.master_rank --dry-run` → demo-rader utskrivna.

- [ ] a–i implementerade + nya enhetstester per acceptance criterion
- [ ] Regime-kompattest för v2-schema
- [ ] Grep-svep: `resolve_weights`, `group_percentile_z`, `junk_gate`, `liquidity_gate` — alla call sites/tester uppdaterade

### TASK 5 — Likviditetsmotor: grader A–F (P1, implementerar D5)

**Files:** Create `backend_worker/liquidity.py` · Modify `backend_worker/technical_snapshot.py` (ENDAST om volume saknas i historik-cachen — verifiera `_read_history`/`fetch_price_history` först) · Create `supabase/migrations/081_liquidity_columns.sql` · Create `backend_worker/tests/test_liquidity.py`.

**Evidence:** Research-rapport 2 §2 (trösklar). Live: EQNR.OL `low_liquidity: true` (absurt för ~$70B-bolag — nuvarande flaggning trasig). Prishistorik-infrastruktur: `technical_snapshot._read_history`/`fetch_price_history` (cachad 7 d, återanvänds i `master_rank.py:759-779`).

**Interfaces:**
- Consumes: price/volume-historik (technical_snapshot-hjälpare), `segment` (Task 1), `compute_free_float_quality` (`backend_worker/smart_money.py`, om float behövs).
- Produces: `compute_liquidity_grade(...) -> str` ("A"…"F"|"unknown"); kolumner `liquidity_grade text`, `turnover_20d_median numeric` (SEK) i `scan_results`; omdefinierad `low_liquidity` (= grade ∈ {D,E,F}); standalone `main()` + anropas från `master_rank_run` (wiring i Task 4).

**Grade-tabell (20-dagars MEDIAN-omsättning, omvandlad till SEK):**
- Golv per segment (SEK/dag): `micro_cap` 500K · `small_cap` 2M · `mid_cap` 10M · `large_cap` 20M.
- **F:** pris < 1 (quote-valuta) ELLER <10 aktiva handelsdagar av 20 ELLER omsättning <10 % av golv.
- **E:** <50 % av golv. **D:** < golv. **C:** ≥ golv. **B:** ≥5× golv. **A:** ≥20× golv.
- **unknown:** volume-data saknas → ingen straff, badge "—".
- FX till SEK: statisk approximativ karta i modulen (dokumenterad, uppdateras kvartalsvis): USD 10.5, EUR 11.5, NOK 1.0, DKK 1.5, GBP 13.5, JPY 0.07, TWD 0.33, KRW 0.008, BRL 2.0, AUD 7.0, SGD 8.0, CAD 8.0, CHF 12.0, NZD 6.5, INR 0.13, HKD 1.35. (Märk `approximativa` i docstring.)

**Acceptance criteria:**
1. SAP.DE/Equinor → grade A; First North-namn med €5–50K/dag → E/F; volume saknas → "unknown".
2. `low_liquidity` = grade ∈ {D, E, F} (EQNR slutar vara low_liquidity).
3. `python -m pytest backend_worker/tests/test_liquidity.py -q` grönt (tröskelbandstester).

**Verification** (`not run`): pytest ovan; efter pipeline: live `scan?search=Equinor` → `liquidity_grade: "A"`, `low_liquidity: false`.

- [ ] Verifiera volume i historik-cachen; utöka cache-format bakåtkompatibelt om det saknas
- [ ] Implementera grade-logik + FX-karta + standalone main()
- [ ] Migration med GRANT SELECT till anon/authenticated (Regel 4.3)
- [ ] Enhetstester för banden

### TASK 6 — Smallcap-data & segmentrelativ presentation (P1, löser F4; kompletterar F8)

**Files:** Modify `backend_worker/smallcap_scanner.py` (primär väg) · Modify `apps/api/routers/smallcap.py` (fallback-väg) · Modify `apps/web/lib/api.ts` · Modify `apps/web/app/(app)/screener/ScreenerView.tsx`.

**Evidence:** F4+F8. `smallcap.py:31-43` läser tomma `smallcap_results`; `smallcap_scanner.py:50` producerar `cash_runway_months`/`insider_buying` dit. Scanner-rotorsak (ej schemalagd/kraschar) `not verified` — diagnosen ingår.

**Primär väg (root-cause):** diagnostisera varför `smallcap_results` är tom (kontrollera GitHub Actions-workflows: `Get-ChildItem .github\workflows` + leta smallcap-scanner-jobb; kör `python -m backend_worker.smallcap_scanner --help`/lokal testkörning om entrypoint finns) → fixa schedule/krasch → tabellen populeras → `/api/smallcap` fungerar som designad → Task 4:i får runway-data.
**Fallback-väg (om scanner beror på otillgänglig källa):** re-sourca `smallcap.py` till `scan_results` (`in_("segment", ["small_cap","micro_cap"])`), skriv om `SmallcapResultOut` till fält som finns i scan_results + master_rank-enrichment (`master_rank`, `master_rank_pctl`, `liquidity_grade`, `mews_score`, `piotroski_f`, `dividend_yield`); dokumentera att runway-skölden förblir vilande (P3).

**Frontend (båda vägarna):** `ScreenerView.tsx`: ny kolumn "Percentil i segment" (`master_rank_pctl`) med `<InfoTooltip>`; likviditetsbadge (Lucide-ikon + tooltip med grade); `lib/api.ts`: typer för nya ScanRow-fält. Inga emojis (Regel 4.4).

**Acceptance criteria:**
1. `GET /api/smallcap?limit=10` returnerar >0 rader.
2. Screener visar pctl-kolumn + likviditetsbadge; `npx tsc --noEmit` 0 fel.
3. Primär väg: `smallcap_results` populerad → Task 4:i runway-wiring aktiv.

**Verification** (`not run`): `cd apps/web; npx tsc --noEmit` → 0 fel; live-curl smallcap >0 rader.

- [ ] Diagnos + primär/fallback-väg beslutad och dokumenterad
- [ ] Endpoint levererar data
- [ ] Frontend pctl + badge med InfoTooltip

### TASK 7 — Codex-dokumentation in-place (P2, löser F5; uppfyller CLAUDE.md prime directive 5)

**Files:** Modify `docs/codex/01_QUANT_MASTERRANK.md` · Modify `docs/codex/02_DATA_PIPELINE.md` · Modify `docs/codex/05_DATABASE_SCHEMA.md`.

**Evidence:** F5 (docs 6/8 vs kod 4/3, `master_rank.py:511`); docs kap 2 §4.5 vs live F1; nya regler D1–D8; migrationsantal 79 → 81.

**Innehåll (uppdatera till KODVERKLIGHETEN efter Task 1–6):**
- Kap 1: vikttabell med `segment_overrides` (v2), junk-gate, segment×sector-normalisering + fallback-kedja, momentum segment-percentil, coverage-skalning, likviditetsgrader + gates, thin-data-regeln (≥4/3 block — rättad från 6/8), katalysatorsemantik (dividend-proxy = low confidence, äkta etikett), tier-trösklar motiverade distributionellt (D7).
- Kap 2: segment-integritetsregeln (null-mc → `unknown`, aldrig micro_cap; enhetsguard).
- Kap 5: migrationsantal, nya kolumner (`liquidity_grade`, `turnover_20d_median`) + GRANT.

**Acceptance criteria:** `python scripts/verify_codex.py` → grönt; inget codex-kapitel motsäger koden.

- [ ] Kap 1/2/5 uppdaterade mot faktiskt beteende
- [ ] verify_codex grönt

### TASK 8 — Historisk validering & sanity-gates (P2)

**Files:** Modify `backend_worker/backtest_runner.py` · Modify `scripts/ranking_sanity_gate.py`.

**Evidence:** Docs kap 1 §7 (recept: backtest + sanity gate vid viktändring). F-klassens degenererade block (F2, F6-MEWS-konstanter) upptäcks inte idag.

**Sanity-gate-påståenden (nya):**
1. `SELECT count(*) FROM scan_results WHERE market_cap >= 10e9 AND segment IN ('small_cap','micro_cap')` → 0.
2. `SELECT count(*) FROM scan_results WHERE market_cap IS NULL AND segment IN ('small_cap','micro_cap')` → 0.
3. Degenererad block-detektor: `var_samp(catalyst_z) > 0` i master_rank-tabellen; samma test för MEWS-komponenter (`mews_operating_leverage` etc.) — larmar tills P3 åtgärdats.
4. T1-fördelning per segment ∈ [0.5 %, 20 %] av segmentets medlemmar; 0 T1 i large_cap EFTER Task 3 (analytiker/value återupplivade) = varning "block fortfarande döda".
5. Ingen large_cap med liquidity_grade E/F.

**Backtest:** per-segment IC (180-dagars horisont) före/efter D1-viktdeltat. **Fallback-beslut (dokumenteras):** om value 0.18 degraderar small/micro-IC → sätt `segment_overrides` tomma (`{}`) i weights.json (av-på-läge) och notera i rapporten.

**Acceptance criteria:** sanity-gate grönt mot live-DB; backtestrapport med per-segment IC före/efter + fallback-beslut dokumenterat.

**Verification** (`not run`): `python scripts/ranking_sanity_gate.py` → grönt; `python backend_worker/backtest_runner.py` → rapport.

- [ ] Gate-påståenden 1–5 implementerade
- [ ] Före/efter-backtest per segment + fallback-beslut

---

## 5. GLOBALA SLUTGATES (kör ALLA efter Task 8 — rapportera FAKTISK utdata)

```powershell
python scripts/verify_codex.py
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
python scripts/smoke_test.py
PYTHONPATH=. python -m pytest apps/api/tests backend_worker/tests -q
cd apps/web; npx tsc --noEmit
python scripts/ranking_sanity_gate.py
python -m backend_worker.master_rank --dry-run
```

**Live-före/efter-referens (efter nästa pipeline-körning):**
- `curl "https://marketscan-api.vercel.app/api/scan?search=SAP"` → large_cap/unknown, tier ≤ T3 (före: micro_cap T1 STARK)
- `curl "https://marketscan-api.vercel.app/api/scan?sort_by=master_rank&limit=10"` → topp matchar `/api/market-intel/master/rank`
- `curl "https://marketscan-api.vercel.app/api/smallcap?limit=10"` → >0 rader (före: `[]`)
- `/api/market-intel/master/rank` → varierande `catalyst_next`, `analyst_z` för MU/MSFT, minst en äkta T1-storbolagskandidat

**Commit-plan (conventional, en per task):**
- `fix(worker): segment integrity guard + backfill migration`
- `fix(api): true master_rank sort + pctl/liquidity exposure in scan`
- `fix(worker): real earnings dates + analyst coverage for global universe`
- `feat(worker): segment-aware masterrank (weights v2, junk gate, seg-sector normalization)`
- `feat(worker): liquidity grades A-F with segment floors`
- `feat(api,web): smallcap data path + segment-relative presentation`
- `docs(codex): R14 segment rules in-place`
- `chore(scripts): segment sanity gates + per-segment backtest`

---

## 6. UTANFÖR SCOPE — P3-FÖRSLAG (namngivna med evidens; EGEN session)

1. **F6-globala fundamentalia:** gross_margin/roe_raw-mappning i `company_info_fetcher.py` (Keyence 17.9 % vs ~80 % real; `roe_raw` null medan `roe` finns) + `change_pct`/`vol_20d`/`currency`-null.
2. **MEWS-komponenter äkta:** `operating_leverage`/`revenue_accel`/`clean_accruals` beräknas (idag konstant 50.04) — Task 8:s detektor larmar tills dess.
3. **Börsdata/Millistream** för First North-fundamentalia (yfinance opålitlig där — research-rapport 2).
4. **January/momentum-säsongshantering** i rebalancing (research-rapport 2: momentum byter tecken i januari; mikro-kap kvartalsvis rebalancing).

---

## 7. CHECKLISTA (gå igenom i slutet)

- [ ] T1: Ingen mega-cap/null-mc-rad i small/micro; SAP visar T3 (ej T1 STARK)
- [ ] T2: scan-sort master_rank == master/rank-topp; pctl i svar
- [ ] T3: catalyst_z varierar; analyst_z för MU/MSFT; ≥80 % large_cap med earnings-event
- [ ] T4: alla acceptance a–i + nya tester gröna; regime-merge bevarar segment_overrides
- [ ] T5: EQNR grade A; low_liquidity = D/E/F; bandtester gröna
- [ ] T6: /api/smallcap >0 rader; pctl-kolumn + badge i UI; tsc 0 fel
- [ ] T7: verify_codex grönt; docs == kod (thin-data 4/3, segmentguard, v2-vikter)
- [ ] T8: sanity-gate grönt; per-segment IC före/efter + fallback-beslut dokumenterat
- [ ] Alla globala slutgates körda med FAKTISK utdata i slutrapporten
- [ ] Grep-svep av alla nya/ändrade symboler genomfört; call sites + display sites uppdaterade
- [ ] Inga secrets/PII i committat material (`git grep -i "sk-\|api[_-]?key\|token" -- <nya filer>`)

**Slutrapport:** skriv `.opencode/audit/r14-implementation-report.md` med: per task — vad som gjordes, faktisk gate-utdata, avvikelser från planen (Regel 0), kvarvarande P3-punkter.
