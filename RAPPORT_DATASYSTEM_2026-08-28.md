# MarketScan — Fullständig granskning, datastack-test och handlingsplan

**Rapportdatum:** 2026-08-28 · **Författare:** AI-analys (fleet-undersökning, reviewer-granskad)
**Kontext:** Privat aktieanalys-app för ägare + familj — ingen produkt, ingen extern användare.
**Uppdrag:** (1) Förklara hur rankningssystemet och "köpläge"-detekteringen fungerar. (2) Deepresearch på alla delar — behåll/ändra/ta bort/lägg till. (3) Frågan om AI verkligen kan göra skillnad. (4) Riktning: nordiska småbolag för bästa chans till alpha.

---

## 0. Sammanfattning (TL;DR)

Systemet är **mycket mer byggt än vad en familj behöver — och det är en styrka och en svaghet på samma gång**.

1. **Rankningen är två motorer som inte pratar med varandra:** huvudmotorn `score_total` (11 faktorer) lever i det externa repot `stock-scanner` på din enhet (Desktop\stock-scanner), medan QMJ/alpha_rank lever i detta repo. "Köpläget" (`entry_signal`) är en regelmaskin — score + RSI + trend, inget annat.
2. **Systemets verkliga värde är inte AI-funktionerna — det är mätningen.** Du har redan per-faktor Rank-IC i egen data, realiserade utfall och backtester. Vägen till alpha i nordiska small caps är att använda den infrastrukturen: behåll bara de delar som *bevisligen* funkar i din egen data.
3. **Datastacken — den fria stacken är empiriskt verifierad idag.** yfinance (kurser + färska kvartalsrapporter), FI-insyn + blankning (Sverige), mfn.se (pressmeddelanden), Nasdaq Nordics nya API (börslistor inkl. First North) och Avanza (nyckelfria kurser) täcker tillsammans ditt behov utan en enda krona. Börsdata (59 €/mån) avstås — både pga pris och licensvillkor som förbjuder webbappar. Finnhub har ingen täckning för nordiska småbolag — det påverkar sentiment-vikten (7,7 %) i rankningen.
4. **Akut just nu:** Supabase återskapades idag (08:37 UTC), workflows körs, men **FI Insider Bulk misslyckas** — migrationerna 049 (isin) och 052 (price) är inte applicerade på den nya instansen. Runbook i §8.1.
5. **AI kan göra skillnad — på två ställen, båda redan halvbyggda:** LLM-händelseextraktion ur pressmeddelanden (mfn + doc_intelligence-lagret) och PDMR-insiderflödet. Allt annat AI (prisprognoser, "AI-poäng", headlinesentiment på illikvida småbolag) är bevisad hype — och din ML-modell bekräftar det (Rank IC 0.027).

---

## 1. Bakgrund, stack och metod

**Stacken** (per `docs/AI_GUIDE.md`): Next.js-frontend (`apps/web`) + FastAPI (`apps/api`) + Python-pipeline (`backend_worker`, körs på GitHub Actions) + Supabase (Postgres/Auth/RLS) + Cloudflare R2 (parquet) + DeepSeek (LLM, narrativ) — deployat på två Vercel-projekt. **Scoring-motorn lever i ett externt repo** (`C:\Users\hthur\OneDrive\Desktop\stock-scanner`; `backend_worker/pipeline/entrypoint.py:145` importerar `core.daily_pipeline.run_pipeline` via PYTHONPATH).

**Metod:** 3 kodkartläggningar (file:line-verifierade, båda repon), 2 evidensrapporter (~60 citerade källor: faktorforskning + AI-evidens), 4 live-datatest (alla externa källor provade på riktigt idag 2026-08-28, inga konton skapade, inga nycklar använda), 1 reviewer-stresstest (P0/P1-fynd rättade), och nulägesverifiering via GitHub Actions + secrets (namn endast).

---

## 2. Så funkar rankningen — hela kedjan

### 2.1 Fyra separata motorer

| Motor | Var | Output | Körning |
|---|---|---|---|
| **score_total** | externa stock-scanner-repot (`core/scoring.py:827-919`) | `score_total` + 11 delscore, `entry_signal`, `trend_signal` | vardagar (snabb) + söndag (full) |
| **QMJ / alpha_rank** | detta repo (`backend_worker/qmj_scores.py`) | `qmj_scores`-tabell | fredagar |
| **MEWS** | externa repot (`smallcap/mews.py`) | `smallcap_results` | ⚠️ endast manuell dispatch — tisdags-jobbet `smallcap_scanner.py` skriver inget till DB (stdout only), tabellen kan vara inaktuell |
| **ML** | externa repot (`core/ml_predictor.py`, `core/ml_ranker.py`) | `ml_rank`, `predicted_return` | endast söndagar (hoppas över i vardagskörningar, `entrypoint.py:100-107`) |

### 2.2 score_total (huvudmotorn)

11 faktorer, percentile-normaliserade (winsorize 2/98 vardera), viktad summa (`core/config.py:86-97`):

| Faktor | Vikt | | Faktor | Vikt |
|---|---|---|---|---|
| value | 0.2134 | | size | 0.0485 |
| quality | 0.1746 | | dividend | 0.0485 |
| momentum | 0.1746 | | sentiment | 0.0770 |
| growth | 0.1261 | | short_interest | 0.0300 |
| risk | 0.0873 | | options_flow | 0.0200 |

Ovanpå: **regimdynamiska vikter** (tjurs/björnmarknad, `scoring.py:307-333`), **sektorvikter** (`config.py:115-127`), och **efterjusteringar**: Piotroski ±8, sektormomentum, holding-disk 0.85 / commodity-disk 0.90, insider-boost +20/+30 (180 dagar decay). Saknad data renormaliseras med cap 3.0 (`scoring.py:867`) — bolag med tunn data kan få resterande delscore uppvektade i stället för att exkluderas.

### 2.3 QMJ (in-repo, fredagar)

Vikter: quality 0.40, momentum 0.25, insider 0.15, value 0.10, payout 0.10 (`qmj_scores.py:43`). Punkt-i-tid-regel `fy_end + 5 månader` (`qmj_scores.py:76-84`) — **exakt rätt disciplin** och den riktiga grunden i systemet. GP/A (`gmar`) ingår redan i quality_z (`qmj_scores.py:270,568-573`).

### 2.4 ML-modellen

XGBoost-regressor (300 träd) + LightGBM LambdaRank (NDCG). **Dokumenterad prestanda: Rank IC 0.027, hit-rate 52,3 %, DSR 0.0** (`docs/plan/01a_ml_ranker_DEEP.md:23-24`) — i praktiken ingen edge. ML på ~700 aktier överanpassar som norm och LightGBM är särskilt känslig för exekveringsläckage (evidensrapporten). `qualitative_score` (den enda AI→siffra-bryggan) beräknas nattligen av RAG-pipelinen (`backend_worker/rag/extract_signals.py:287`) och visas i UI, men är rätt aldrig viktad in i rankningen.

### 2.5 Data in → signal ut

```
yfinance (kurser/fundamentals) + Finnhub (nyheter/shorts/analystrecs) + FMP (fallback)
+ FI insynsregister + Finviz/ETF (discovery)
   → stock-scanner scorer → parquet → db_loader → scan_results (Supabase)
   → QMJ (fredagar) + MEWS (manuell) + insider/shorts/dokument-flöden
   → API: /api/scan, /markets, /stocks/{ticker}, /market-intel/qmj/rank, /smallcap, /insider-radar …
   → UI: screener, daglig-briefing, aktie-sidan, insider-radar, kvalitetslista …
```

DeepSeek/Gemini används idag **endast för narrativ** (förklaringar, coacher, veckoanalys) — aldrig i sifforna. Det är faktiskt rätt enligt evidensen (§5).

---

## 3. Så funkar köpläget (entry_signal)

"Köpläge" = kolumnen `entry_signal`, beräknad i `core/filters.py:118-163` (externa repot). **Ren teknik** — score_total + RSI(14) + trend + avstånd till 52-vmax:

| Signal | Villkor |
|---|---|
| **STARK** | score ≥ 72 **och** RSI 35–68 **och** aktien står 5–18 % under 52-vmax |
| **OK** | score ≥ 65 **och** RSI 35–68 |
| **VÄNTA** | RSI saknas, RSI > 75 (överköpt) eller RSI < 30 (översålt) |
| **EJ AKTUELL** | under MA200 (trend_cap) eller score < 55 |
| DATA SAKNAS | score saknas/utanför 0–100 |

Trendfiltret (`filters.py:29-51`): under MA200 = NEDTREND (cappar signalen), under MA50 men över MA200 = VARNING, annars UPPTREND.

**Kända brister:**
- Trösklarna är aldrig backtestade (varken mot din egen historik eller i litteratur) — klassisk Larry Connors-stil RSI/pullback-regel, men helt oprövad.
- Kod och docstring motsäger varandra: docstring säger "score ≥ 65" och "pullback 3–20 %", koden använder 55 och 5–18 % (`filters.py:111-112` vs `:134,:152`).
- `"DATA SAKNAS"` finns inte i DB:s CHECK-constraint (`STARK/OK/VÄNTA/EJ_AKTUELL` i migration 001) — mappningen i `db_loader.py` bör verifieras.
- Guiden i UI lovar "bra värdering" som del av STARK — värdering finns bara indirekt via score_total; signalfunktionen själv är ren teknik.
- **Färskhet:** signalen räknas om vardagar från fräscha priser (`data_fetcher_batch.py:604-606`) — men bara för de ≤300 tickers som prishämtningen capar vid (`entrypoint.py:89`), och bara vid lyckad hämtning.

---

## 4. Inventering — behåll / ändra / skrota

### Behåll (kärnan — fungerar och är rätt byggd)
- score_total- och scan_results-flödet (hel kedja)
- **QMJ-motorn** (punkt-i-tid-disciplin, kvalitetssil)
- **score_tracker + signal_analytics** (`score_history`, per-faktor Rank-IC, decile-spread) — **appens guld: mäter vad som faktiskt funkar i din egen data**
- prediction_outcomes + ml_performance (realiserade utfall)
- FI-insider + kluster, FI-blankning (gratis, stark evidens)
- strategy_backtester/strategi-lab, risk_analyzer, digest, bevakningar
- doc_intelligence-lagret (company_documents, document_chunks, qualitative_signals, earnings_memos) — underutnyttjat, §5

### Ändra
| Del | Problem | Ändring |
|---|---|---|
| **Universum** | nominellt nordiskt, men globalt i praktiken (USD/INR/JPY, TSLA seedad); prishämtning cap 300 | renodla: nordisk lista från Nasdaq-API:er (411 + First North 332 + Oslo 400 + HEL 147 + CPH 118) med likviditetsgrind |
| **entry_signal** | trösklar oprövade, docstring fel | backtesta i strategi-lab **med spread-kostnad**; fixa docstring |
| **ML-rankern** | ingen edge (IC 0.027), bara weekly | shadow mode tills den slår F-Score-baseline i purged walk-forward; annars pensionera |
| **Momentum-vikt + regimväxling** | blandad evidens för svenska småbolag | låt factor_metrics avgöra vikterna |
| **Finnhub-sentimentet** | ingen nordisk småbolagstäckning | mät Rank-IC — troligen uteslut/vikta ned (7,7 %) |
| **Datakällor** | yfinance instabilt historiskt, Finnhub-US-only | fri stack enligt §6 |

### Skrota (dött, duplikat eller fel fokus)
- `sector_rotation.py`, `universe_discovery.py`, `smallcap_scanner.py` (− alla skriver inget till DB, stdout only; smallcap_scanner har t.o.m. SUPABASE-secrets injicerade i sitt workflow utan att använda dem)
- `ml_trainer.train_and_predict()` (död kod)
- Route-kollisionen `GET /api/alerts` (alerts.py skuggar smart_alerts.py) — en riktig bugg
- Dubletter: `notification_preferences` (012) vs `notification_prefs` (034); insider-endpoint i både `insider.py` och `stocks.py`
- `oversikt/page.tsx` (ren redirect-stub); options_flow-vikten (US-data); Finviz-discovery (US-centriskt)

---

## 5. Deepresearch — vad forskningen säger (källunderlag: `faktorer-och-ai.md`)

**Small cap-premien:** död som obetingad effekt sedan ~1983 (van Dijk 2011; Asness 2018) — den lever kvar som en **illikviditetspremie** och återuppstår bara med kvalitetssil. Men: *alla* faktorer är starkare i small caps — så din riktning är rätt, med kvalitet i centrum.

| Faktor | Evidens | Kommentar för din app |
|---|---|---|
| Piotroski F-Score | stark (~10 %/år internationellt, starkast i small) | finns som ±8-boost; som QMJ-filter saknas den |
| PEAD (earnings drift) | stark US small (3×), moderat dokumenterad i Sverige | behöver rapportdatum — mfn.se ger dem |
| Kvalitet (GP/A, ROIC) | stark, hedge mot value | finns redan i QMJ via `gmar` |
| Insider PDMR | CAR +1,9 % i svenska småbolag (2026-studie ifrågasätter längre horisont klar) | FI-data finns, gratis |
| Momentum 12-1 | stark globalt, **blandad i Sverige** (2024-studie finner reversal) | mät i egen data innan det väger 17 % |
| Short interest | stark US, svag nordisk | FI-blankning finns |
| Seasonality/indexeffekter | urholkade, ej tradeable | skippa |

**AI som mätbart tillför:** (1) earnings-call/report-NLP och händelseextraktion (evidens: tonanalys OOS ~2 %/mån; LLM-förståelse av nyheter är signifikant starkare i småbolag — Lopez-Lira & Tang). (2) PDMR-eventflöde med kontext. (3) **Verifierad RAG som beslutstöd** (aldrig signal — RAG hallucinerar i ~81 % av fallen utan verifieringspipeline).

**AI som är hype (avstå):** LLM-prisprognoser (alpha försvinner under bias-korrigerad backtesting), ogrundade "AI-poäng" i rankningen, headlinesentiment på illikvida småbolag (2–10 nyheter/kvartal = brus).

**Den stora idén:** din app har redan det som ingen privat aktör har — loggade prognoser, per-faktor Rank-IC i egen universum, signalföljsamhet och backtester. **Evidensloopen är strategin:** kandidatfaktor → mät i egen data (walk-forward, purged) → behåll bara det som bär → skala bort resten. 26 workflows och 45 tabeller för en familj är en underhållsrisk; snävare system, hårdare bevis.

---

## 6. Datastack-test — vad som faktiskt fungerar (live-testade idag)

**Metod:** fyra parallella tester mot riktiga endpoints. Inga konton registrerade, inga nycklar skapade/använda, ingen repo-kod ändrad. Sammanfattat här, detaljer i `datastack-verifierad-2026-08-28.md` + `datatest-*.md`.

### ✅ Verifierat fungerande — gratis

| Källa | Bevis | Värde | Hål/noteringar |
|---|---|---|---|
| **yfinance 1.4.1** | 10/10 nordiska tickers (SE main, SE First North, NO, DK, FI) resolve | 10 års dagliga kurser utan gap (MYCR 2 515 rader 2016→2026; CX 1 110 från IPO 2022; HARVIA 2 117 från IPO 2018); kvartalsrapporter **färska** (Q2-2026 på 3 av 4 testade; dansk bank Q1 — vanligt eftersläp); earnings/dividends/splits; 6mo-fetch 0,2–0,5 s/ticker | `earningsDate` alltid null → använd `earningsTimestamp`; `analystCount` null → `numberOfAnalystOpinions` (finns på alla 10); banker saknar debtToEquity/FCF; förlustbolag saknar PE/dividend; history saknar Currency-kolumn; RILBA.CO:n kortnamn har Yahoo-mojibake |
| **FI-insyn (PDMR)** | 200 rader live, 81 emittenter, datum 2026-06-18→08-28, huvudlista **+ First North** | svenska insidertransaktioner | ⚠️ koden skickar fel param-namn — se §8.2 |
| **FI-blankning** | 338 rader; SBB 15,16 %, Elekta 13,84 % | kortpositioner + LEI→ISIN-uppslag | — |
| **mfn.se** | JSON-feed: 1 440+ artiklar, fulltext gratis, ≥2 mån djup; artikel-JSON (title/slug/publish_date/html/text/attachments) | svenska pressmeddelanden **+ rapporter med datum** (punkt-i-tid!) | ⚠️ inget bolagsfilter i feeden; befintlig fetcher trasig — §8.2 |
| **Nasdaq Nordic** | `api.nasdaq.com/api/nordic/screener/shares`: STO Main 411, STO First North 332, OSL 400, HEL 147, CPH 118, ICE 27 | **den riktiga nordiska bolagslistan/universumkällan** | GET-only (POST → 403 WAF); ingen CSV — generera från JSON |
| **Avanza** | market-guide (t.ex. stock/5497 → 200 med full JSON) + price-chart OHLC (1 vecka–1 år, 200) | nyckelfria kurser | ⚠️ format ändrat: `timePeriod=one_week|one_month|…` + `resolution=day`; inofficiellt (ToS-risk, ändras utan förvarning); python-avanza kräver TOTP för auth-endpoints; CSV-import finns redan |

### ❌ Avstå / fungerar inte

| Källa | Resultat |
|---|---|
| **Börsdata** | 403 Cloudflare utan nyckel; REST kräver **Pro+ 59 €/mån** (ändrat 2025-02-01); ToS förbjuder externa system som visar API-data → **avstå** (dyrt + licens) |
| **Finnhub** | 401 utan nyckel; free tier US-only, ingen nordisk symboltäckning → sentiment-delen i din rankning vilar på svag grund |
| **EODHD** | 401; gratis 20 anrop/dag; inga First North i börslistan → behövs inte (yfinance täcker) |
| **Alpha Vantage** | demo-nyckel = IBM-only; 25/dag; US-centrerad → avstå |
| **FMP** | 401 utan nyckel; gratis 250/dag; fallback-kod finns men **nyckeln saknas i GH-secrets** → död gren idag |
| **Oslo Børs NewsWeb** | SPA-shell (3 715 B HTML) på alla endpoints; API-host utan DNS → kräver headless browser; ticket |

**Gaps i fri stack (erkänn dem):** analystestimater/consensus för nordiska småbolag (ingen fri källa), insider/blanks utanför Sverige, punkt-i-tid-release-datum (löses via mfn.se-datum för SE).

---

## 7. Nuläget — Supabase var borta, är återskapad, och ett akut schemafel finns

Du återskapade Supabase idag — bevis: SUPABASE_URL/DATABASE_URL/SUPABASE_ANON_KEY/SUPABASE_SERVICE_KEY uppdaterade 08:37 UTC, DEEPSEEK_API_KEY 14:37 UTC. Manuella dispatches körs nu:

| Workflow | Status idag |
|---|---|
| QMJ Scores | ✅ 12:53, 13:11, 15:10 |
| Universe Mapping | ✅ 14:57, 15:49 (efter fails 14:48, 15:39 — intermittent, se §8.2 #5) |
| News Pipeline | ✅ 14:48, 16:07 |
| **FI Insider Bulk** | ❌ **16:43** — `UndefinedColumn: column "price" does not exist` |
| Insider Trades (Finnhub) | ⏳ kördes 16:37 |
| Company Profiles | ⏳ kördes 16:52 |

**Rotorsaken till FI-felet (verifierad):** migrationerna **049** (`insider_trades_isin.sql`) och **052** (`insider_trades_price.sql`) finns i repot men är inte applicerade på den nya instansen. Migration 015 skapade `insider_trades` utan `isin`/`price`; koden (`fi_insider_bulk.py:262`, `insider_cluster.py:51,65`) skriver och läser dem. Koden är korrekt — schemat är efter. QMJ/Universe fungerar, alltså är majoriteten av migrationer applicerade; nya workflows kommer att yppa nästa saknade migration i turordning.

**Före borttagningen** (förklarar de äldre felen): Weekly Digest 7/10 misslyckade (e-post + saknad Supabase), Smart Alerts 0/10 success (7 skipped), Universe Mapping intermittent, MarketScan Pipeline fastnade i kö. **Lokala data överlever och är användbara:** `data/fi_raw`, `data/qmj_raw`, `stock-scanner/data` (bt_snapshots 19 parquet 05-14→08-15, senast 832 rader/91 nordiska tickers; piotroski_snapshots 1 198 rader). GH-secrets: 11 (APP_URL, DATABASE_URL, DEEPSEEK_API_KEY, EMAIL_FROM, FINNHUB_API_KEY, GEMINI_API_KEY, GH_CHECKOUT_TOKEN, RESEND_API_KEY, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_URL).

---

## 8. Handlingsplan

### 8.1 Migrationer — klistra-in-runbook (Supabase → SQL Editor)

Kör **hela filinnehållet** i ordning (filerna ligger i `supabase/migrations/`):

1. **`049_insider_trades_isin.sql`** — lägger till `isin`, ersätter dedup-nyckeln med unik-nyckel på (COALESCE(isin,ticker), name, trade_date, type), index på (isin, trade_date).
2. **`052_insider_trades_price.sql`** — lägger till `price`.

Om du får `42501 permission denied` någonstans: kör först **`023_grant_table_privileges.sql`** (innehåller GRANTs för alla tabeller).

**Verifieringsfråga** (kör när båda är applicerade):

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'insider_trades' ORDER BY ordinal_position;
-- Förväntat: id, ticker, name, role, type, shares, amount, trade_date, created_at, isin, price

SELECT count(*) FROM insider_trades;   -- om 0: inga trades har hunnit in ännu — kör om FI Insider Bulk
```

**Efter verifiering — kör om workflowet:** GitHub → Actions → FI Insider Bulk → Re-run all jobs, eller:
```
gh run rerun 33191319030 -R hankkontakt/marketscan
```

> ⚠️ **Fixa FI-param-buggen (§8.2 #1) innan du kör om jobbet** — annars hämtar det tyst bara "senaste 10" med dubbletter (fel param-namn ignoreras av FI utan felmeddelande).

### 8.2 Kodbrister (5 + 1) — alla små, alla oberoende av Supabase

| # | Bugg | Fil | Fix |
|---|---|---|---|
| 1 | **FI-insider param-namn** (allvarligast — tysta dubbletter) | `backend_worker/fi_insider_bulk.py` (FromDate/ToDate) + `stock-scanner/core/fi_insider_fetcher.py` (FrånDatum/TillDatum) | Byt till FI:s verkliga namn: `Transaktionsdatum.From` / `Transaktionsdatum.To` (live-verifierat) |
| 2 | **mfn-integrationen trasig** | `backend_worker/rag/document_fetcher.py` — anropar `mfn.se/api/feed?ticker=X&days=30` → `items: null` | Paginera `mfn.se/rss?limit=48&offset=N` + filtrera på `subjects[].slug/isin/tickers`; fulltext från `mfn.se/a/<author>/<slug>` |
| 3 | **Avanza prisformat ändrat** | grep `timePeriod=1_week` i backend_worker/apps/api | `one_week|one_month|three_months|one_year` + `resolution=day` |
| 4 | **yfinance-fältnamn bytt** | stock-scanner (data_provider/scoring) | `earningsTimestamp` i stället för `earningsDate` (alltid null); `numberOfAnalystOpinions` i stället för `analystCount` |
| 5 | **Nasdaq-migrering** (förklarar Universe Mapping-fails) | universe_mapping | Bygg om universumkälla mot `api.nasdaq.com/api/nordic/screener/shares` (GET-only) — ersätter finnhub-symbolvägen (ingen nordisk täckning) och gör First North-täckning komplett |
| +1 | **FMP-nyckel saknas i secrets** | — | Sätt en gratis FMP-nyckel eller ta bort fallback-grenen |

### 8.3 Därefter — prioriterad väg (detaljer i `SYNTES_rankning-koplage-ai.md` §7)

- **P0:** skrota död kod + fixa route-kollisionen + konsolidera duplikater; verifiera signal-täckning (300-ticker-cap); point-in-time-disciplin + purged walk-forward i evaluering.
- **P1:** entry_signal-backtest med spread-modell; vikter styrda av factor_metrics (börja: momentum + Finnhub-sentiment); F-Score-filter i QMJ.
- **P2 (AI där den betalar):** LLM-händelseextraktion ur mfn-dokument (JSON-schema + verifiering) → ny radarflöde; PDMR-eventflöde med LLM-sammanfattning; ML → shadow mode (purged walk-forward, `stock-scanner-fix/core/ml_validation.py` är utsedd destination — katalogen är medvetet tom, skrota den inte).
- **P3:** verifierad RAG per aktie; ren nordisk universe-lista med likviditetsgrind.

**Medvetet utanför scope (nämns för transparens):** skatt/ISK för utländska small caps (kupongskatt NO/DK/FI, valuta) — familjeekonomibeslut; säkerhet — 11 API-nycklar utan rotation (låg risk, rotera vid tillfälle).

---

## 9. Bilagor — alla underlagsfiler

| Fil | Innehåll |
|---|---|
| `.opencode/audit/SYNTES_rankning-koplage-ai.md` | Rankningen + köpläge detaljerat + keep/change/add + AI-analys (reviewer-granskad) |
| `.opencode/audit/datastack-verifierad-2026-08-28.md` | Datastack-testerna, matris, nuläge (Supabase) |
| `.opencode/audit/nordic-data-landscape.md` | 12 datakällor jämförda (priser, täckning) |
| `.opencode/audit/faktorer-och-ai.md` | Evidensrapport, ~60 källor (faktorer + AI-alpha/hype) |
| `.opencode/audit/datatest-yfinance.md` | yfinance live-test i detalj |
| `.opencode/audit/datatest-publik-norden.md` | FI/mfn/NewsWeb/Nasdaq live-test i detalj |
| `.opencode/audit/datatest-nyckelberoende.md` | Börsdata/Finnhub/EODHD/AV/FMP/Avanza live-test |
| `.opencode/audit/datatest-nulage.md` | GitHub Actions + secrets + lokala data |
