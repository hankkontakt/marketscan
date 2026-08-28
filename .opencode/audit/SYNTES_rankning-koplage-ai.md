# MarketScan — Rankning, köpläge och vägen mot nordiska small caps

**Syntesrapport 2026-08-28** · Underlag: 3 kodkartläggningar (file:line-verifierade), 2 evidensrapporter
(`nordic-data-landscape.md`, `faktorer-och-ai.md`) · Kontext: privat app för ägare + familj, ingen produkt.
Mål: max chans till alpha via nordiska small caps, AI bara där den mätbart bidrar.

---

## 1. Så funkar rankningen idag — hela kedjan

### 1.1 Fyra separata motorer (inte en)

| Motor | Ligger i | Output | Körning |
|---|---|---|---|
| **score_total** (huvudmotor) | externt repo `C:\Users\hthur\OneDrive\Desktop\stock-scanner` (`core\scoring.py:827-919`) | `score_total` + 11 delscore, `entry_signal`, `trend_signal` | vardagar (snabb banan) + söndag (full) |
| **QMJ / alpha_rank** | MarketScan-repot (`backend_worker/qmj_scores.py`) | `qmj_scores`-tabell | fredagar |
| **MEWS** (smallcap) | stock-scanner (`smallcap\mews.py`) | `smallcap_results` | ⚠️ **endast vid manuell `--mode smallcap`-dispatch** — tisdags-jobbet `smallcap_scanner.py` skriver inget till DB (stdout only), så tabellen kan vara inaktuell |
| **ML** (XGBoost + LightGBM LambdaRank) | stock-scanner (`core\ml_predictor.py`, `core\ml_ranker.py`) | `ml_rank`, `predicted_return` | **endast söndagar** (hoppas över i dagliga körningar, MarketScan-repot `backend_worker\pipeline\entrypoint.py:100-107`; dess docstring säger fortfarande "run ML predictions" — inaktuell) |

### 1.2 score_total-formeln (stock-scanner)

11 faktorer, percentile-normaliserade (winsorize 2/98), viktad summa (`core\config.py:86-97`):

| Faktor | Vikt |
|---|---|
| value | 0.2134 |
| quality | 0.1746 |
| momentum | 0.1746 |
| growth | 0.1261 |
| risk | 0.0873 |
| sentiment | 0.0770 |
| size | 0.0485 |
| dividend | 0.0485 |
| short_interest | 0.0300 |
| options_flow | 0.0200 |

På toppen av det:
- **Regimdynamiska vikter** (`scoring.py:307-333`): TJÖRN-marknad → momentum +0.05/growth +0.05/value −0.05; BJÖRN → quality +0.15/risk +0.10/value +0.10/momentum −0.20. Renormaliseras till 1.0.
- **Sektorvikter** (`config.py:115-127`) justerar vissa faktorer per sektor.
- **Efterjusteringar**: Piotroski ±8 poäng (`piotroski.py:323-325`), sektormomentum-add (`sector_momentum.py:231`), holding-disc 0.85 / commodity-disc 0.90 (`scoring.py:36-37`), insider-boost +20/+30 med 180 d decay (`scoring.py:821-822`).

**Kända svagheter i formeln:**
1. **Saknad data renormaliseras med cap 3.0** (`scoring.py:867`): ett bolag med bara ett fåtal giltiga delscore får kvarvarande delscore uppvektade upp till 3× — tunna data kan ge vilseledande poäng i stället för exkludering.
2. **Momentum-vikten (0.1746) är inte evidens-stödd för svenska small caps** — svensk smallcap-forskning är blandad, en 2024-studie finner till och med reversal (se §4).
3. `options_flow` (2 %) och `short_interest` (3 %) är US-tunga datakällor — svag grund i Norden.
4. Massor av godtyckliga magiska tal (RSI-band 35–68, pullback 5–18 %, boosts ±8/+20/+30) — ingen av dem är backtestad mot egen data så vart synes.

### 1.3 Köpläget — exakt logik (`core\filters.py:118-163`)

"Köpläge" = kolumnen `entry_signal`, beräknad **enbart av teknik**: score_total + RSI(14) + läge mot MA200 + avstånd till 52v-max.

```
DATA SAKNAS   score saknas eller < 0 / > 100
EJ AKTUELL    under MA200 (trend_cap)  ELLER  score < 55
VÄNTA         RSI saknas, RSI > 75 (överköpt) eller RSI < 30 (översålt)
STARK         score ≥ 72  +  RSI 35–68  +  pullback 5–18 % under 52v-max
OK            score ≥ 65  +  RSI 35–68
```

Trendfilter (`filters.py:29-51`): under MA200 = NEDTREND (cappar signalen), under MA50 men över MA200 = VARNING, annars UPPTREND.

**Observationer:**
- Docstringen säger "score ≥ 65" och "pullback 3–20 %" där koden använder 55 respektive 5–18 % (`filters.py:111-112` vs `:134`, `:152`) — dokumentationen ljuger.
- `"DATA SAKNAS"` finns inte i DB:s CHECK-constraint (`STARK/OK/VÄNTA/EJ_AKTUELL`) — db_loader mappar strängarna, men mappningen av just "DATA SAKNAS" bör verifieras.
- UI-texten i guiden lovar "bra värdering" som del av STARK — värdering finns bara indirekt via score_total. Signalfunktionen i sig är ren teknik.
- **Färskhet (delvis besvarad av koden):** vardagsbanan räknar OM `entry_signal` från fräscha priser (`data_fetcher_batch.py:604-606`) — men bara för de ≤300 tickers som prishämtningen capar vid (`entrypoint.py:89`), och bara vid lyckad hämtning. Risk: universum >300 bolag → svansen får veckogamla signaler; misslyckad fetch → stale. Åtgärd: verifiera täckning, inte bygga om.

### 1.4 ML-motorn — ärliga siffrorna

- XGBoost-regressor (300 träd) + LightGBM LambdaRank, 35 features, walk-forward.
- **Dokumenterad prestanda: Rank IC 0.027, hit-rate 52,3 %, DSR 0.0** (`docs/plan/01a_ml_ranker_DEEP.md`) — det är i praktiken ingen edge.
- ML hoppas över i alla vardagskörningar; `ml_rank` uppdateras bara söndagar.
- Evidensrapporten varnar specifikt: ML på ~700 aktier överanpassar som norm, och LightGBM är *särskilt* känslig för exekveringsläckage — direkt relevant här.
- `qualitative_score` **beräknas redan nattligen** av MarketScans RAG-pipeline (`backend_worker/rag/extract_signals.py:287,294` → tabellen `qualitative_signals`, schemalagt i `orchestrator.yml:185-188` + `doc_intelligence.yml:58`, visas via stocks-API:et `stocks.py:1009,1037`). Det som **ej är kopplat** är stock-scanner-sidan: där är ML-featuren deklarerad (`ml_ranker.py:83`) men ingen kod räknar den där. Rätt fråga är alltså inte "död eller levande?" utan "ska AI-signalen viktas in i rankningen?" — mät dess Rank-IC i `factor_metrics` först.
- `ml_trainer.train_and_predict()` i MarketScan-repot är död kod; bara `build_training_dataset` används.

### 1.5 Data in → signal ut (helheten)

```
yfinance (priser/fundamentals) + Finnhub (nyhetssentiment, short interest, analystrecs)
+ FMP (fallback fundamentals) + FI (svenska insider PDMR) + Finviz/ETF (discovery)
   → stock-scanner scorer → parquet → db_loader → scan_results (Supabase)
   → QMJ (fre) + MEWS (endast manuell dispatch) + insider/shorts/dokument-flöden
   → API: /api/scan (screener), /markets/top-movers, /stocks/{ticker},
          /market-intel/qmj/rank, /smallcap, /regime, /insider-radar
   → UI: screener, daglig-briefing, aktie/[ticker], insider-radar, kvalitetslista …
```

DeepSeek/Gemini används idag **bara för narrativ** (förklaringar, coacher, veckoanalys) — aldrig i sifforna. Det är faktiskt rätt enligt evidensen, men det finns två ställen där AI *borde* vara med (§5).

---

## 2. Inventering — alla delar, behåll/ändra/skrota

### Behåll (kärnan som funkar och är rätt byggd)

| Del | Varför |
|---|---|
| score_total + scan_results-flödet | funkar, hel kedja pipeline→DB→UI |
| **QMJ-motorn** | punkt-i-tid-regel (fy_end+5 mån) är exakt rätt disciplin; viktarna (kvalitet 0.40) stöds av evidens |
| **score_tracker + signal_analytics** | `score_history` + per-faktor Rank-IC + decile-spread — detta är appens guld: den kan mäta vad som faktiskt funkar i EGEN data |
| prediction_outcomes + ml_performance | realiserade 30-d utfall loggas — förutsättningen för allt evidensarbete |
| insider (FI PDMR + kluster) + shorts (FI blankning) | stark evidens för insider i svenska small caps; data gratis |
| strategy_backtester / strategi-lab | låter dig testa entry_signal-trösklar och faktorkombinationer på egen data |
| risk_analyzer, digest, bevakningar/alarm | vardagsnytta för familjen |
| doc_intelligence-flödet (company_documents, document_chunks, qualitative_signals, earnings_memos) | **redan byggt** AI-lager med rätt design (extraktion, inte prognos) — underutnyttjat |

### Ändra

| Del | Problem | Ändring |
|---|---|---|
| **Universe** | nominellt nordiskt (suffix .ST/.OL/.HE/.CO) men globalt i praktiken (USD/INR/JPY i FX-tabellen, TSLA seedad); prishämtning cap 300 tickers | renodla: explicit nordiskt small-cap-universum med likviditetsfilter (≈ ≥1 Mkr daglig omsättning), genererat från Börsdata/Avanza-listor — inte Finviz |
| **entry_signal** | trösklar (55/65/72, RSI 35–68, pullback 5–18 %) aldrig backtestade; docstring fel | backtesta i strategi-lab mot signal_persistence/egen data; justera eller behåll med skäl; fixa docstring |
| **ML-rankern** | Rank IC 0.027 = ingen edge; bara weekly; leakage-känslig | degradera till "shadow mode" (loggas, visas inte) tills den slår en enkel F-Score-baseline walk-forward; annars skrota |
| **Datakällor** | yfinance är känd instabil (split/valuta-buggar), Finnhub free har inga nordiska fundamentals | se §6 (Börsdata Pro+ eller gratis-stack) |
| **Momentum-vikt + regimväxling** | blandad svensk evidens | låt factor_metrics (egen Rank-IC) avgöra vikterna — mekanismen finns redan |
| **Daglig färskhet** | entry_signal räknas om vardagar, men bara för ≤300 tickers och bara vid lyckad fetch | verifiera täckningen mot det nya nordiska universumet: höj capet eller snäva universum |

### Skrota (dött, duplikat eller fel fokus)

| Del | Varför |
|---|---|
| `sector_rotation.py` + `universe_discovery.py` + `smallcap_scanner.py` (backend_worker) | skriver inget till DB — deras output kastas bort i orchestratorn (stdout only). Identiskt mönster i alla tre; smallcap_scanner har dessutom SUPABASE-secrets injicerade i sitt workflow utan att använda dem |
| `ml_trainer.train_and_predict()` | död kod |
| Route-kollision `GET /api/alerts` (alerts.py skuggar smart_alerts.py) | riktig bugg — en GET är osynlig |
| Dubletter: `notification_preferences` (012) vs `notification_prefs` (034); `insider.py` vs `stocks.py insider-trades`; portfolio/risk-prefix-split | konsolidera |
| `oversikt/page.tsx` | ren redirect-stub |
| options_flow-vikten (US-data) | 2 % vikt, ingen nordisk grund — ta bort ur score eller skrota options-scan |
| Finviz-discovery | US-centrerat, ersätts av nordisk universe-lista |

---

## 3. Tänk stort: vad är det här systemet egentligen?

Rätt fråga är inte "fler AI-funktioner?" utan: **appens edge är mätningen.** MarketScan har redan, unikt för ett privatsystem:

1. loggade prognoser (`prediction_outcomes`),
2. per-faktor Rank-IC i **egen** universum (`factor_metrics`),
3. signalföljsamhet + utfall (`signal_persistence_cache`),
4. backtester på egen historik.

Nästan ingen privat aktör har det. Vägen till alpha i nordiska small caps är därför **en evidensloop**: kandidatfaktor → mät Rank-IC i egen data i walk-forward → behåll bara det som funkar → skala ner komplexiteten tills varje kvarvarande del har bevis. 26 workflows och 45 tabeller för en familj är tvärtom en underhållsrisk — snävare system, hårdare beviskrav.

Forskningen (se `faktorer-och-ai.md`) stöder riktningen: small-cap-premien är död som obetingad effekt sedan ~1983, men *alla* faktorer är starkare i small caps, plus illikviditetspremie — **förutsatt** kvalitetssil och punkt-i-tid-data. QMJ:s kvalitetsfokus (0.40) är rätt; den billigaste förstärkningen är ett F-Score-filter (GP/A finns redan via `gmar`).

---

## 4. Evidens för faktorerna (sammanfattning — detaljer i `faktorer-och-ai.md`)

| Faktor | Evidens | I nordiska small caps | Kostnad att bygga |
|---|---|---|---|
| Piotroski F-Score | stark (~10 %/år intl., starkast i small cap) | bra | finns redan som ±8-boost i score_total (`piotroski.py`); som QMJ-filter saknas den |
| PEAD / earnings drift | stark US small (3×), dokumenterad men modest i Sverige/Norden | ok | medel (behöver rapportdatum) |
| Kvalitet (GP/A, ROIC) | stark; hedge mot value | bra | GP/A finns redan i QMJ (`gmar`, `qmj_scores.py:270`) |
| Insider (PDMR) | CAR +1,9 % i svenska small, 2026-studie ifrågasätter längre horisont | bra (FI-data finns redan) | låg |
| Momentum 12-1 | stark globalt i small, **blandat i Sverige** (2024-studie: reversal) | osäkert — mät i egen data | gratis |
| Short interest | stark US, svag nordisk data | svag | FI finns |
| Seasonality/index-inkludering | urholkat/ej tradeable | nej | skippa |

---

## 5. Var AI faktiskt gör skillnad (och var den är hype)

**Ger mätbart värde:**
1. **Rapport- och earnings-NLP** — extrahera händelser (vinstvarningar, orderintag, ledarskiften) ur pressmeddelanden/rapporter; evidens: earnings-call-ton OOS ~2 %/mån i studier; LLM-nyhetsförståelse starkare just i small caps (Lopez-Lira & Tang). Appen har redan flaskhalsen byggd (doc_intelligence + chunk-tabeller) — **detta är den största outnyttjade tillgången**. DeepSeek är perfekt för detta (billig, strukturerad extraktion med JSON-schema + verifieringsregel).
2. **PDMR-eventflöde** — LLMSummera insiderkluster med kontext (vem, hur mycket, vid vilken värdering) till en rankad händelseström; FI-data finns redan.
3. **Verifierad RAG som beslutstöd** — "vad säger Q3-rapporten om marginaler?" med källcitat. RAG hallucinerar (81 % fel/refusering i studier) utan verifieringspipeline — gör den till beslutstöd, aldrig signal.

**Hype (avstå):**
- LLM-prisprognoser (alpha försvinner under bias-korrigerad backtesting — FINSABER).
- Ogrundade "AI-score" som blandas i rankningen — här gör systemet redan rätt: `qualitative_score` beräknas och *visas*, men är aldrig viktad in i score_total. Behåll den disciplinen: mät dess Rank-IC i `factor_metrics` först, vikt in aldrig innan den bär.
- Headline-sentiment på illikvida small caps (2–10 nyheter/kvartal = brus —Finnhub-sentimentet på små nordiska bolag är troligen mest brus; mät det i factor_metrics innan det får väga 7,7 %).

**Punkten-på-tåket som är AI:s verkliga roll här:** point-in-time-data + purged walk-forward (forskningens #1-rekommendation) är förutsättningen för allt — utan den är varje signal, ML inkluderat, en illusion.

---

## 6. Datastack — beslut att fatta

> ⚠️ **UPPDATERAT 2026-08-28 av live-testen:** se `.opencode/audit/datastack-verifierad-2026-08-28.md` — den fria stacken är empiriskt verifierad (yfinance + FI-insyn/blankning + mfn.se + Nasdaq Nordic-API + Avanza keyless). Börsdata Pro+ **avstås** (59 €/mån + ToS förbjuder webbappar). Nedanstående alternativ A är därmed överspelat.

**Alternativ A (rekommenderad om budgeten tillåter): Börsdata Pro+ (59 EUR/mån ≈ 610 SEK)**
- Enda källan med REST-API som täcker 1 700+ nordiska bolag (inkl. First North/Spotlight/NGM), 20 år EOD, rapportdata + ~300 nyckeltal **+ insider, blankning, återköp, kalendrar**.
- OBS: REST-API kräver Pro+ sedan 1 feb 2025 (Pro = bara Excel-plugin). Rate 100/10 s, <10K/dag — passar daglig pipeline.
- ⚠️ **Licensgråzon — öppen fråga, inte avgjord:** villkoren förbjuder "externa system/hemsidor som visar API-data". MarketScan är en webbapp som visar screener-data, och familjemedlemmar kan räknas som externa användare. **Mejla Börsdata och få det skriftligen** innan du betalar — frågan kostar inget, brottet kan kosta åtkomsten.
- ⚠️ **Migrationskostnaden är veckor, inte dagar:** QMJ, score_total och piotroski konsumerar yfinance-format (engelska radnamn, kolumn=period). Börsdata har annat schema (R12/kvartal, svenska nyckeltal) → adapterlager behövs för 3–4 motorer. Räkna med det i beslutet.
- Ersätter på sikt yfinance (instabila split/valutor) + Finnhub-fundamentals (saknas för Norden) + delar av FI-scrapet.

**Alternativ B (gratis, sämre):** FI PDMR-scrape + NewsWeb (NO) + mfn.se + Avanza CSV (manuell kvartalsimport) + yfinance priser. Fungerar men: ingen bra fundamentals-källa för Norden, ingen blankning/insider för NO/DK/FI, mer skör kod.

**Komplement i båda:** EODHD $19.99/mån som sekundär kurshistorik (verifiera First North-täckning med demo-nyckel först). Nordnet API: stängt för nya. Behåll Finnhub enbart för nyheter/kalender (US-fundamentals är värdelösa här).

Full jämförelsetabell: `nordic-data-landscape.md`.

---

## 7. Prioriterad plan (om du vill köra vidare)

**P0 — grund (gör allt annat möjligt/ärligt)**
1. Skrota död kod (sector_rotation, universe_discovery, smallcap_scanner stdout-jobb, ml_trainer-trään) + fixa route-kollisionen + konsolidera duplikater (½ dag).
2. Verifiera signal-täckning: `entry_signal` räknas redan om vardagar, men bara för ≤300 tickers — höj capet eller snäva universum så att hela det nordiska small-cap-universumet har färska signaler.
3. Point-in-time-disciplin i score-pipelinen (rapportdatum, inte räkenskapsår) + purged walk-forward i all evaluering.

**P1 — evidensloopen**
4. Backtesta entry_signal-trösklarna i strategi-lab — **med transaktionskostnads-/spread-modell** (i illikvida small caps är spreaden ofta skillnaden mellan på papper och på riktigt); justera med skäl.
5. Låt factor_metrics avgöra score_total-vikter (börja med momentum-frågan); mät Finnhub-sentimentets Rank-IC i Norden — ta bort det som inte bär.
6. F-Score-filter i QMJ-pipelinen (GP/A finns redan via `gmar`; Piotroski finns idag bara som ±8-boost i score_total).

**P2 — AI där den betalar sig**
7. Bygg vidare på doc_intelligence: LLM-händelseextraktion ur pressmeddelanden med JSON-schema + verifiering → ny signal-/radarflöde.
8. PDMR-eventflöde med LLM-sammanfattning till insider-radarn.
9. ML → shadow mode: implementera den purged walk-forward-validering som redan är planerad till `stock-scanner-fix/core/ml_validation.py` (enligt `docs/plan/01a_ml_ranker_DEEP.md:306-308` — katalogen är medvetet tom och utsedd destination, skrota den inte). Pensionera rankern om den inte slår F-Score-baseline.

**P3 — polish**
10. Verifierad RAG-fråga per aktie (beslutstöd). 11. Universe: ren nordisk lista med likviditetsgrind.

**Medvetet utanför scope (nämn det ändå):** skatt/ISK-konsekvenser av utländska small caps (kupongskatt NO/DK/FI, valutaspel) — påverkar "riktig" alpha efter kostnader men är ett familiekonomi-beslut, inte systemarbete. Säkerhet: 12+ API-nycklar i orchestrator-secrets utan rotationsrutin — låg risk för familjeapp, men rotera vid tillfälle.

**Beslut du måste fatta:** datastack A (Börsdata ~610 SEK/mån, efter skriftligt licenssvar) eller B (gratis). Allt annat följer av det.
