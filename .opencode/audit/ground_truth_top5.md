# Ground Truth — MarketScan TOP 5 (2026-08-29)

> Syfte: fastställa verkliga nyckeltal för de fem rankade aktierna (VOLV-B.ST, DIVISLAB.NS, SAND.ST, ALFA.ST, APP) från ≥2 oberoende källor, jämföra mot systemets rådata och hitta felrankningsmönster. Alla priser/nyckeltal avser 2026-08-28/29 om inget annat anges.

---

## Task Report — direkt svar

**De tre svenska aktierna är legitima, fundamentalt sunda toppkandidater — systemets NULL-fundamentals är ett datahämtningsfel, inte en varningsflagga.** Verkliga nyckeltal: Volvo P/E 19,8 (fwd 14,1), ROE ~20 %, direktavkastning 3,8 %; Sandvik P/E 26–27 (fwd ~17–18), ROE ~18 %, yield 1,7 %; Alfa Laval P/E 29,1 (fwd 25,6), ROE ~19 %, yield 1,6 %. Alla tre rapporterade starka Q2 2026.

**APP:s P/E 0,39 är fel med ~60×** — verkligt TTM P/E är ~24,4 (fwd 17,4). D/E 27,94 är fel (verkligt 1,11), ROA 0,4 är fel (verkligt 46,5 %). Beta 2,53 är korrekt. Aktien är ett momentum-name i utdragning: −50 % från 2026-toppen, 52-veckors-lägsta efter Q2-intäktsmiss, nedgraderingar.

**DIVISLAB:s P/E 42,67 är fel** — verkligt TTM P/E ~84 (74–88 beroende på källa). D/E −24,76 är fel — bolaget är nettoskuldfritt (net debt/equity −0,19). F-score 4 ej verifierbar.

**Felrankningsmönster:** systemet gav kvalitetspoäng 78–88 till de tre svenska trots NULL-fundamentals → poängen bygger inte på fundamenta (sannolikt momentum/market cap-proxy). De två aktier där "fundamentals" finns är korrumperade (P/E 0,39, D/E −24,76, D/E 27,94) — sannolikt enhets-/valutamappningsfel. Båda dessa är de mest övervärderade/riskfyllda av de fem, vilket tyder på att rankingen inte drivs av fundamenta alls.

---

## 1. VOLV-B.ST — AB Volvo (Nasdaq Stockholm)

| Mått | Systemet | Ground truth | Källa (2+ oberoende) |
|---|---|---|---|
| P/E (TTM) | NULL | **19,77** | stockanalysis 19,77 · companiesmarketcap 19,68 · wisesheets 19,76 · allinvestview 19,49 |
| Forward P/E | NULL | **14,09** | stockanalysis |
| P/S | NULL | **1,50** | stockanalysis |
| P/B | NULL | **4,01** | stockanalysis |
| EV/EBITDA | NULL | **16,01** | stockanalysis |
| ROE | NULL | **20,88 %** | stockanalysis 20,88 % · wisesheets 19,98 % |
| ROA | NULL | **4,51 %** | stockanalysis |
| Bruttomarginal | NULL | **24,36 %** | stockanalysis |
| Rörelsemarginal | NULL | **10,38 %** (TTM); justerad **11,7 %** Q2'26 | stockanalysis · volvogroup.com |
| D/E | NULL | **1,47** (koncern, inkl. Volvo Financial Services); **Industrial Operations är nettokassa** (+SEK 34,7 mdr) | stockanalysis · Volvo AR 2025 ("debt-free Industrial Operations") · Quartr |
| Current ratio | NULL | **1,10** | stockanalysis |
| Direktavkastning | NULL | **3,82 %** | stockanalysis 3,82 % · wisesheets 3,72 % |
| Market cap | 580e9 SEK | **708,8 mdr SEK** (systemets siffra är inaktuell/underräknad; 348,40 × 2,03 mdr aktier) | stockanalysis |
| Beta | — | **0,98** | stockanalysis |
| Q2 2026 | — | Net sales SEK 126,3 mdr (+3 % rapp., **+7 % organiskt**), EPS **SEK 5,10** (3,64), justerad rörelsemarginal 11,7 % (11,0), ROCE Industrial Ops 26,8 % | volvogroup.com · Quartr |
| Analysts | — | **Buy**, medelriktkurs **SEK 355,27** (+2,0 %), 22 analytiker | stockanalysis |
| F-score | — | 5 | stockanalysis |

**Bild:** Legitim kvalitetsaktie och cyklisk compounder. Inte "P/E 12" som ledarens hypotes — TTM P/E är ~19,8 (fwd 14,1); P/E 12 var det historiska medianvärdet 2021–2025 (investing.com). ROE ~20 % (inte 25 %), D/E 1,47 på koncernnivå men industriella verksamheten är nettokassa — bankarmen Volvo Financial Services blåser upp skuldsiffran. Direktavkastning 3,8 % är hög för svensk industri. Q2 var starkt (EPS +40 % YoY, order +33 % på Group Trucks). **Legitim topp-5-kandidat** — dock snarare "solid kärninnehav" än mångdubblare. Analyst upside bara +2 %.

---

## 2. SAND.ST — Sandvik (Nasdaq Stockholm)

| Mått | Systemet | Ground truth | Källa (2+ oberoende) |
|---|---|---|---|
| P/E (TTM) | NULL | **26,1–26,8** | stockanalysis 26,06–26,77 · morningstar 26,22 (normaliserat) · simplywall.st 25,2× · wisesheets 29,71 |
| Forward P/E | NULL | **17,1–18,2** | stockanalysis 17,12–18,15 |
| P/S | NULL | **3,40–3,49** | stockanalysis 3,40 · morningstar 3,29 |
| P/B | NULL | **4,48** | stockanalysis 4,48 · morningstar 4,22 |
| EV/EBITDA | NULL | ej direkt fångad (P/FCF 25,14) | stockanalysis |
| ROE | NULL | **17,4–17,9 %** | stockanalysis 17,40–17,91 % · morningstar 18,50 % (norm.) |
| ROA | NULL | **8,1 %** | stockanalysis 8,12 % · morningstar 9,88 % (norm.) |
| Bruttomarginal | NULL | **~40,6 %** (FY25: 49,0/120,7 mdr) | stockanalysis · Reuters |
| Rörelsemarginal | NULL | justerad EBIT-marginal **21,4 %** Q2'26; EBITA-marginal 22,6 % | home.sandvik |
| D/E | NULL | **~0,40** (skuld 37,2 mdr / eget kapital ~93,2 mdr, beräknat) | stockanalysis (balansräkning) |
| Current ratio | NULL | **1,64** | stockanalysis · morningstar 1,64 |
| Direktavkastning | NULL | **1,67 %** | stockanalysis 1,67 % · morningstar 1,77 % · wisesheets 1,52 % |
| Market cap | — | **438,7 mdr SEK** (kurs 393,10) | stockanalysis |
| Q2 2026 | — | Order +17 % (org), **revenue 36,75 mdr (+24 %, org +23 %)**, justerad EBITA-marginal 22,6 % (19,0), EPS 4,17 (2,56) — rekordkvartal | home.sandvik |
| Analysts | — | **Hold**, medelriktkurs **SEK 389,48** (−0,9 % mot kurs 393,10), 21 analytiker; SEB uppgraderade till Buy PT 445 (24 aug), RBC Buy 460, UBS Sell 300, GS Sell 330 | stockanalysis · ad-hoc-news.de |
| F-score | — | ej publicerad för SAND hos stockanalysis | — |

**Bild:** Kvalitetsbolag med rekordmomentum (Q2 +24 % organiskt, YTD +30 %). Men efter rusningen handlas aktien på ~26× TTM med konsensus **Hold** och medelriktkurs *under* aktuell kurs — dvs. fullvärderad till något dyr. SEB:s uppgradering (24 aug) är den senaste positiva katalysatorn. **Legitim kandidat, men uppsidan i analystkonsensus är utraderad** efter årets rally.

---

## 3. ALFA.ST — Alfa Laval (Nasdaq Stockholm)

| Mått | Systemet | Ground truth | Källa (2+ oberoende) |
|---|---|---|---|
| P/E (TTM) | NULL | **29,1** | stockanalysis 29,12 · companiesmarketcap 29,5 |
| Forward P/E | NULL | **25,60** | stockanalysis |
| P/S | NULL | **3,39** | stockanalysis |
| P/B | NULL | **5,20** | stockanalysis |
| EV/EBITDA | NULL | **17,77** | stockanalysis |
| ROE | NULL | **19,06 %** | stockanalysis |
| ROA | NULL | **7,50 %** | stockanalysis |
| Bruttomarginal | NULL | **36,31 %** | stockanalysis |
| Rörelsemarginal | NULL | **16,68 %** (TTM); justerad EBITA-marginal **17,0 %** Q2'26 | stockanalysis · alfalaval.com |
| D/E | NULL | **0,46** | stockanalysis |
| Current ratio | NULL | **1,12** | stockanalysis |
| Direktavkastning | NULL | **1,64 %** | stockanalysis 1,64 % · investing.com 1,57 % · wisesheets 1,56 % |
| Market cap | — | **238,6 mdr SEK** (kurs 577,20) | stockanalysis |
| Q2 2026 | — | **Orderintag 22,2 mdr (+35 %, org +29 %)** — rekord, bl.a. största ordern någonsin (Biofuels); net sales 18,1 mdr (+8 %), EPS 4,91 (4,87), net debt/EBITDA 1,11 | alfalaval.com · morningstar/PR Newswire |
| Analysts | — | **Buy**, medelriktkurs **SEK 588,88** (+2,0 %), 17 analytiker; Pareto uppgraderade till Buy (aug) | stockanalysis · marketbeat |
| F-score | — | 6 | stockanalysis |

**Bild:** Kvalitetscompounder med rekordorderintag (+35 %) och 17 % EBITA-marginal. Betavärde 0,78 — lägst volatilitet av de fem. Handlas dock på premium (~29× TTM, PEG 2,49) med bara +2 % analystupside. **Legitim kandidat, men dyr** — marknaden har redan prisat in den starka orderboken.

---

## 4. DIVISLAB.NS — Divi's Laboratories (NSE, Indien)

| Mått | Systemet | Ground truth | Källa (2+ oberoende) |
|---|---|---|---|
| P/E (TTM) | **42,67** | **83,8** | stockanalysis 83,83 · companiesmarketcap 87,7 · wisesheets 74,35 · univest 77,14 |
| Forward P/E | — | **77,02** | stockanalysis |
| P/S | — | **21,84** | stockanalysis |
| P/B | — | **14,63** | stockanalysis |
| EV/EBITDA | — | **61,02** | stockanalysis |
| ROE | — | **16,19 %** | stockanalysis 16,19 % · wisesheets 16,42 % |
| ROA | — | **10,07 %** | stockanalysis |
| Bruttomarginal | — | **36,4 %** (Q1 FY27, från 25,6 %) | univest · sahi.com |
| Rörelsemarginal | — | ~31 % (beräknat från EV/EBIT 69,35) | stockanalysis |
| D/E | **−24,76** | **Net debt/equity −0,19** (nettokassa); current ratio **5,43** | stockanalysis · wisesheets |
| Direktavkastning | — | **0,35 %** | stockanalysis 0,35 % · wisesheets 0,42 % · tickertape 0,35 % |
| Market cap | — | **₹2,45 biljoner** (kurs ₹9 239) | stockanalysis |
| Q1 FY27 (jun-26) | — | Revenue ₹3 080 cr (**+27,8 %**), PAT ₹902 cr (**+65,5 %**), nettomarginal 29,3 % | univest · sahi.com · scanx.trade |
| Analysts | — | **Hold**, medelriktkurs **₹8 292** (29 analytiker) — **UNDER aktuell kurs ₹9 239**; Trendlyne PT ₹7 063 (−23,6 %); Citi ser "inflection year" med uppsida (från lägre kursnivå) | stockanalysis · trendlyne · CNBC-TV18 |
| F-score | **4** | **Ej verifierbar** (stockanalysis publicerar ej F-score för NSE) | — |

**Bild:** Utmärkt verksamhet — nettoskuldfri, ROE 16 %, PAT +65 % YoY, marginalexpansion. Men aktien handlas på **~84× TTM** efter en +50 %-rusning till all-time-high (₹9 239, 28 aug) — **ovanför analytikernas medelriktkurs** (₹8 292). Trump-tullar på generika är ett aktivt riskmoment (niftytrader). Detta är "quality at any price" — **övervärderad, inte värdefälla**, men prissatt för perfektion. Systemets P/E 42,67 underskattar värderingen med ~2×.

---

## 5. APP — AppLovin (Nasdaq, USA)

| Mått | Systemet | Ground truth | Källa (2+ oberoende) |
|---|---|---|---|
| P/E (TTM) | **0,39** | **24,4** | stockanalysis 24,43 · robinhood 24,03 · gurufocus 23,5 |
| Forward P/E | — | **17,43** | stockanalysis |
| P/S | — | **15,57** | stockanalysis |
| P/B | — | **33,68** | stockanalysis |
| EV/EBITDA | — | **19,72** | stockanalysis |
| ROE | — | **203,7 %** | stockanalysis |
| ROA | **0,4** | **46,46 %** | stockanalysis |
| Bruttomarginal | — | **88,46 %** | stockanalysis |
| Rörelsemarginal | — | **77,44 %**; justerad EBITDA-marginal **84 %** | stockanalysis · panabee |
| D/E | **27,94** | **1,11** | stockanalysis |
| Current ratio | — | **4,30** | stockanalysis |
| Direktavkastning | — | Ingen utdelning | stockanalysis |
| Beta | **2,53** | **2,53 ✓** | stockanalysis |
| Market cap | — | **$106,3 mdr** (kurs $317,76) | stockanalysis |
| Q2 2026 (5 aug) | — | Revenue **$1,92 mdr (+53 % YoY) — MISS mot $1,94 mdr estimat**; EPS $3,76 = estimat; aktien **−19 % till 52-veckors-lägsta**; Q3-guide: revenue-midpunkt $2,07 mdr (+7,8 % sekventiellt), adj EBITDA $1,71–1,74 mdr | CNBC · investors.applovin.com · Zacks |
| Analysts | — | **Moderate Buy**, medelriktkurs **$525–560** (33 analytiker, +65 % mot kurs); Piper Sandler nedgraderade till Neutral PT $665→$385; Benchmark $500→$440; BofA $430; RBC $575 | stockanalysis · marketbeat · clearank |
| F-score | — | 7 | stockanalysis |

**Bild:** Extremt lönsam tillväxtmaskin (53 % intäktstillväxt, 84 % EBITDA-marginal, FCF $863M/kvartal) men **momentum är brutet**: −50 % från 2026-toppen, 52-veckors-lägsta, intäktsmiss + svag Q3-guide, nedgraderingar, short interest 3,4 %, insiderägande 23,6 %, beta 2,53. **P/E 0,39 är fel med ~60×** — verkligt TTM P/E ~24 (fwd 17,4). Ledarens gissning "P/E ~60–150" stämmer inte heller för 2026: vid årets topp (~$600) var P/E ~46; 3-årssnittet är 86,6 (public.com). Fwd P/E 17,4 är inte dyrt *om* tillväxten reaccelererar — men beat-and-raise-kadensen är bruten. **Hot momentum-name i utdragning, hög risk/hög belöning — inte en värdefälla, men inte heller en trygg topp-5-placering.**

---

## Mönster för felranking (downstream-analys)

1. **NULL-fundamentals + höga kvalitetspoäng (78–88) för de svenska** → poängen kan inte komma från fundamenta. Sannolikt momentum/market-cap-proxy: alla tre är upp kraftigt (SAND +30 % YTD, ALFA +32 % på 52 v, VOLV +19 %).
2. **Korrumperade "fundamentals" där data finns** → P/E 0,39 (APP), D/E −24,76 (DIVISLAB), D/E 27,94 (APP), ROA 0,4 (APP). Mönstret (enheter/valutor blandade, per-share vs total, eller fel rad) gör att de två mest övervärderade namnen ser *billiga* ut: DIVISLAB 42,67 vs verkligt ~84; APP 0,39 vs verkligt ~24. Detta **inflaterar** deras poäng.
3. **Slutsats:** rankingens TOP 5 är inte fundamentdriven. De tre svenska är genuint bra bolag (så rankingen "råkar" vara rimlig där), men DIVISLAB (84×, ovanför konsensus) och APP (brutet momentum, −50 %) är de svagaste risk/avkastnings-profilerna — och de är de enda med "data". Systemet belönar momentum och straffar inte värdering.

---

## Verification Receipts (källor, hämtade 2026-08-29)

| # | Källa | URL | Stöder påståenden |
|---|---|---|---|
| 1 | StockAnalysis — VOLV.B statistik | https://stockanalysis.com/quote/sto/VOLV.B/statistics/ | Volvo P/E 19,77, fwd 14,09, ROE 20,88 %, yield 3,82 %, D/E 1,47, market cap 708,8 mdr, PT 355,27, F-score 5 |
| 2 | StockAnalysis — ALFA statistik | https://stockanalysis.com/quote/sto/ALFA/statistics/ | Alfa Laval P/E 29,12, fwd 25,60, ROE 19,06 %, yield 1,64 %, D/E 0,46, PT 588,88, F-score 6 |
| 3 | StockAnalysis — APP statistik | https://stockanalysis.com/stocks/app/statistics/ | AppLovin P/E 24,43, fwd 17,43, ROE 203,7 %, ROA 46,46 %, D/E 1,11, beta 2,53, PT $525,58, F-score 7 |
| 4 | StockAnalysis — DIVISLAB ratios | https://stockanalysis.com/quote/nse/DIVISLAB/financials/ratios/ | Divi's P/E 83,83, fwd 77,02, ROE 16,19 %, net debt/equity −0,19, current ratio 5,43, yield 0,35 % |
| 5 | StockAnalysis — SAND statistik | https://stockanalysis.com/quote/sto/SAND/statistics/ | Sandvik P/E 26,06–26,77, fwd 17,12–18,15, ROE 17,40–17,91 %, yield 1,67–1,72 %, current ratio 1,64 |
| 6 | StockAnalysis — SAND forecast | https://stockanalysis.com/quote/sto/SAND/forecast/ | Sandvik konsensus Hold, PT 389,48, 21 analytiker, SEB Buy 445, RBC 460, UBS Sell 300, GS Sell 330 |
| 7 | StockAnalysis — DIVISLAB forecast | https://stockanalysis.com/quote/nse/DIVISLAB/forecast/ | Divi's konsensus Hold, PT ₹8 292, 29 analytiker |
| 8 | Morningstar — SAND | https://www.morningstar.com/stocks/xsto/sand/quote | Sandvik P/E 26,22, ROE 18,50 %, yield 1,77 %, current ratio 1,64 |
| 9 | Simply Wall St — SAND | https://simplywall.st/stocks/se/capital-goods/sto-sand/sandvik-shares/valuation | Sandvik P/E 25,2×, market cap 424 mdr, PT 394,75 |
| 10 | CompaniesMarketCap — ALFA | https://companiesmarketcap.com/eur/alfa-laval/pe-ratio/ | Alfa Laval P/E 29,5 (aug 2026) |
| 11 | CompaniesMarketCap — DIVISLAB | https://companiesmarketcap.com/divis-laboratories/pe-ratio/ | Divi's P/E 87,7 (aug 2026) |
| 12 | CompaniesMarketCap — Volvo | https://companiesmarketcap.com/volvo/pe-ratio/ | Volvo P/E 19,68 (aug 2026) |
| 13 | Wisesheets — VOLV | https://www.wisesheets.io/dividend-yield/VOLV-B.ST | Volvo yield 3,72 %, P/E 19,76, ROE 19,98 % |
| 14 | Wisesheets — DIVISLAB | https://www.wisesheets.io/roe/DIVISLAB.NS | Divi's P/E 74,35, ROE 16,42 %, current ratio 5,43, yield 0,42 % |
| 15 | Volvo Group — Q2 2026 pressrelease | https://www.volvogroup.com/en/news-and-media/news/2026/jul/volvo-group--the-second-quarter-2026.html | Volvo Q2: sales 126,3 mdr, EPS 5,10, adj op-marginal 11,7 %, ROCE 26,8 % |
| 16 | Volvo Group — AR 2025 | https://www.volvogroup.com/content/dam/volvo-group/markets/master/events/2026/volvo-group%E2%80%93annual-report-2025.pdf | "debt-free Industrial Operations" |
| 17 | Quartr — Volvo Q2 2026 | https://quartr.com/events/volvo-volv-q2-2026_3saV1OH7 | Volvo Q2: net financial assets Industrial Ops +34,7 mdr, trucks order +33 % |
| 18 | Investing.com — Volvo P/E | https://www.investing.com/pro/SEP:VOLVB/explorer/pe_ltm | Volvo historisk median-P/E 12,0× (2021–2025), topp 19,5× juni 2026 |
| 19 | AllInvestView — VOLV | https://www.allinvestview.com/dashboard/stock/VOLV-B.ST/ | Volvo P/E 19,49, PT 355,27 |
| 20 | Sandvik — Q2 2026 | https://www.home.sandvik/en/news-and-media/news/2026/07/interim-report-second-quarter-2026/ | Sandvik Q2: revenue +24 %, EBITA-marginal 22,6 %, EPS 4,17 |
| 21 | Alfa Laval — Q2 2026 | https://www.alfalaval.com/media/news/investors/2026/alfa-laval-ab-publ-interim-report-1-april-30-june-2026/ | Alfa Laval Q2: order +35 %, sales +8 %, EBITA-marginal 17,0 %, EPS 4,91 |
| 22 | CNBC — AppLovin Q2 | https://www.cnbc.com/2026/08/06/applovin-stock-q2-earnings-revenue.html | APP Q2: EPS $3,76 = est, revenue $1,92 mdr vs $1,94 mdr (miss), −19 %, Piper nedgradering $665→$385 |
| 23 | AppLovin IR — Q2 2026 | https://investors.applovin.com/financials/quarterly-results/default.aspx | APP Q2: EPS $3,76, FCF $863M, återköp 1,1M aktier $551M |
| 24 | Zacks — APP Q3-guide | https://www.zacks.com/stock/news/2973733/applovin-q3-guidance-signals-reacceleration-after-a-mixed-q2-print | APP Q3: revenue-midpunkt $2,07 mdr, adj EBITDA $1,71–1,74 mdr |
| 25 | MarketBeat — APP | https://www.marketbeat.com/instant-alerts/applovin-nasdaqapp-trading-down-15-on-analyst-downgrade-2026-08-18/ | APP: Benchmark $500→$440, konsensus Moderate Buy, PT $557,83 |
| 26 | Univest — Divi's Q1 FY27 | https://univest.in/blogs/divis-laboratories-q1-results-fy27-pat-rs-902-cr | Divi's Q1: revenue ₹3 080 cr +27,8 %, PAT ₹902 cr +65,5 %, GM 36,4 % |
| 27 | Trendlyne — DIVISLAB | https://trendlyne.com/research-reports/stock/336/DIVISLAB/divi-s-laboratories-ltd/ | Divi's PT ₹7 063 (−23,6 %) |
| 28 | CNBC-TV18 — Divi's | https://www.cnbctv18.com/market/divis-laboratories-share-price-2026-an-inflection-year-key-drug-launch-triggers-buy-sell-upside-19814998.htm | Divi's: 32 analytiker (14 buy/6 hold/12 sell), Citi "inflection year" |
| 29 | Ad-hoc-news — Sandvik SEB | https://www.ad-hoc-news.de/boerse/news/corporate-news/sandvik-stock-climbs-after-seb-rating-upgrade-and-higher-price-target/69995909 | Sandvik: SEB Buy PT 445 (24 aug), konsensus 388,20 |
| 30 | MarketsMojo — Divi's | https://www.marketsmojo.com/news/stocks-in-action/divis-laboratories-ltd-hits-new-52-week-high-at-rs91496-4173025 | Divi's all-time-high ₹9 149,6 (28 aug), +49,7 % på 1 år |
| 31 | NiftyTrader — Divi's | https://www.niftytrader.in/markets/divis-labs-q1-fy27-results-preview/ | Trump-tullar på generika = riskmoment för Divi's |
| 32 | Public.com — APP P/E | https://public.com/stocks/app/pe-ratio | APP 3-årssnitt P/E 86,58 |
| 33 | Robinhood — APP | https://robinhood.com/us/en/stocks/APP/ | APP P/E 24,03 |
| 34 | GuruFocus — APP | https://www.gurufocus.com/stock/APP/data/pe-ratio | APP P/E 23,5 (23 aug 2026) |

**Korsverifierade kritiska siffror (≥2 källor):** Volvo P/E (4 källor) + yield (2) · Sandvik P/E (4) + yield (3) · Alfa Laval P/E (2) + yield (3) · Divi's P/E (4) + yield (3) · APP P/E (3) + beta (systemet vs stockanalysis).

---

## Blockers / Inte gjort

1. **Volvo Q2 2026 exakt konsensus-EPS** kunde inte verifieras (investing.com-transkriptet 403, Yahoo key-statistics 404). EPS SEK 5,10 vs 3,64 YoY är verifierat från bolaget; kvartalet beskrivs som starkt (Quartr, investing.com-rubrik) men exakt beat/miss-siffra saknas.
2. **Sandvik EV/EBITDA** fångades inte direkt i någon källa (P/FCF 25,14 finns; EV/EBITDA ej publicerad i hämtade sidor).
3. **DIVISLAB F-score 4** ej verifierbar — stockanalysis publicerar inte Piotroski F-score för NSE-noteringar.
4. **Ledarens hypotes "APP verkligt P/E ~60–150"** stöds inte för 2026: vid årets topp (~$600) var TTM P/E ~46; nuvarande ~24. P/E >100 förekom endast 2023–24 när vinsten var låg (3-årssnitt 86,6 enligt public.com).
5. **Ad-hoc-news.de Sandvik-artikel** innehåller ett uppenbart datafel (market cap "50,44 mdr SEK" — verkligt ~438 mdr); jag använde stockanalysis/simplywall.st för market cap.
6. Systemets market cap 580e9 SEK för Volvo matchar varken total (708,8 mdr) eller B-aktier enbart (554 mdr vid 348,40) — sannolikt inaktuell kurs eller felaktigt aktieantal.