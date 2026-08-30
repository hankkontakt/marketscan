# Ground Truth — Bottom-5 Ranked Stocks (MarketScan)

**Datum:** 2026-08-29
**Uppdrag:** Fastställa ground truth för SEB-A.ST, FFH.TO, BLK, UMG.AS, BURE.ST — jämföra mot MarketScan-systemets rådata och avgöra om aktierna är felaktigt nedrankade.
**Metod:** websearch + webfetch (stockanalysis.com, Morningstar, Simply Wall St, Yahoo Finance, bolagens egna pressmeddelanden, Reuters, MarketBeat, TipRanks, MarketScreener). Kritiska siffror korsverifierade mot ≥2 oberoende källor.

---

## 1. Task Report — Direkt svar

**JA — alla fem är felaktigt nedrankade. Systemets rådata för dessa fem är i huvudsak meningslös/felaktig, och felet är systematiskt: det applicerar industribolags-metrics (gross margin, ROA, D/E, F-score) på banker/försäkring/investmentbolag där de antingen är irrelevanta eller beräknas fel.**

| Ticker | Systemets värde | Verkligt värde (ground truth) | Dom |
|---|---|---|---|
| **SEB-A.ST** | pe −0.26, roa −0.02, gm −0.42, f-score 0 | P/E 13.5–14.3, fwd 12.1; ROE 14.1% TTM (15.7% Q2'26); ROA 0.74% (normalt för bank); D/E 5.1 (normalt för bank); direktavk. 4.9–5.2% | **Grovt fel.** Lönsam, väldigt kapitaliserad bank (CET1 17.2%), Q2-beat, köp av egna aktier. |
| **FFH.TO** | pe −17.51, roa 0.02, de −1.65 | P/E 7.5–8.4, fwd 8.3; P/B 1.02; ROE 16.5%; ROA 4.2%; direktavk. 0.9% (+34% shareholder yield via buybacks); BVPS $1,304 (+4.8% H1) | **Grovt fel.** Buffett-stil compounder till P/E ~8, ROE 16.5%, combined ratio 93.1%. |
| **BLK** | pe 7.28, de −54.41, gm −0.03, piot 4 | P/E 27.8 TTM, fwd 19.5; P/B 3.13; ROE 12.3%; D/E 0.23; GM 47.2%; F-score 6; direktavk. 2.0% | **Grovt fel.** Kvalitetsjätte, rekord-AUM $15.3T, Q2-beat, konsensus Buy. |
| **UMG.AS** | pe 64.54, de 90.81, roa 0.01, gm ~0 | P/E 82–84 TTM (distorderat av reavärderingsförluster), fwd ~18–20; D/E 0.73; ROA 7.0%; ROE 7.7% rapporterat / ~34% justerat; direktavk. 3.5% | **Delvis fel.** TTM-P/E distorderat (Spotify-reavärdering), D/E 90.81 är absurt fel (verkligt 0.73). Fwd-P/E ~18–20 på justerad EPS. |
| **BURE.ST** | pe n/a, de −50.01, roa −0.14, gm −0.42 | P/E meningslöst (investmentbolag); P/B 0.95; NAV/aktie SEK 342.9, aktien ~SEK 324 → ~5–6% rabatt mot NAV; D/E ~0 (netto kassa); direktavk. 0.9% | **Fel måttstock.** Investmentbolag ska värderas mot NAV, inte P/E/ROA/gm. Trades under NAV. |

**Mönster för ledarens downstream-analys:** Systemet ger banker/försäkring/investmentbolag f-score 0–4 och negativa fundamentals för att det (a) använder gross margin/ROA som om de vore industribolag (banker har ingen gm; ROA ~0.5–1% är normalt), (b) producerar absurda D/E-värden (90.81, −54.41, −50.01) — tecken på felaktig balansräkningsdata (troligen totala skulder/equity eller fel enhet/valuta), och (c) får negativa P/E när TTM-vinsten innehåller engångsposter (UMG reavärdering, Bure fair-value-svängningar). **Detta är systemets fel, inte aktiernas.**

---

## 2. Per-aktie ground truth

### 2.1 SEB-A.ST — Skandinaviska Enskilda Banken (systemranking 51.35)

| Mått | Systemet | Ground truth | Källa (verifierad) |
|---|---|---|---|
| P/E TTM | −0.26 | **13.5–14.3** | stockanalysis 13.52/14.30; wisesheets 13.94; TipRanks 13.6; Simply Wall St 13.4x |
| Forward P/E | — | **12.1–12.6** | stockanalysis 12.07/12.61 |
| P/S | — | 5.5–5.7 | stockanalysis |
| P/B | — | 1.83–1.88 | stockanalysis; TipRanks 1.69 |
| ROE | — | **14.1% TTM; 15.7% Q2'26 (17.4% justerat för pensionsöverskott)** | stockanalysis 14.08%; SEB pressrelease 15.7%; wisesheets 13.93% |
| ROA | −0.02 | 0.74% (normalt för bank) | stockanalysis |
| D/E | — | 5.13 (banknormalt; TipRanks ~4.46) | stockanalysis ratios; TipRanks |
| Direktavkastning | — | **SEK 11.00 → 4.9–5.2%** | stockanalysis 5.19%/4.91%; wisesheets 5.06%; Simply Wall St 5.2% |
| Senaste kvartal | — | **Q2'26: nettoresultat SEK 8.66B vs 7.68B förväntat (BEAT), EPS SEK 4.44, ROE 15.7%, CET1 17.2%, positiv operating jaws, rekord i provisionsintäkter** | SEB pressrelease 2026-07-15; Finimize 2026-07-15; dpa-AFX 2026-07-15 |
| Konsensus | — | **Hold/Neutral; snittriktkurs SEK 193.7–207.4 (≈ −5% till −0.4% mot kurs ~SEK 218–224)** | stockanalysis forecast (17 anl., 207.35); Investing.com (16 anl., 193.69); TargetWatch 3-mån konsensus 218.62 |
| Nyheter 30 dgr | — | **Positivt:** Q2-beat, nytt SEK 1.25B-återköpsprogram, UBS höjde riktkurs till SEK 230 (2026-08-27), Barclays till 188 (07-29), Morgan Stanley till 187 (07-27) | dpa-AFX 07-15; MarketScreener 08-27/07-29 |

**Slutsats:** Lönsam, väldigt kapitaliserad nordisk storbank (CET1 17.2%, buffert 250 bps) med ROE 15.7%, Q2-beat och 5% direktavkastning. P/E ~13.5 är rimligt–billigt för en bank med 15%-målsättning på ROE. Systemets f-score 0 och negativa P/E/ROA/gm är rena datafel. Aktien är dock inte "fynd" — analytikerkonsensus är Hold och snittriktkursen ligger strax under kursen.

---

### 2.2 FFH.TO — Fairfax Financial Holdings (systemranking 51.06)

| Mått | Systemet | Ground truth | Källa (verifierad) |
|---|---|---|---|
| P/E TTM | −17.51 | **7.5–8.4** | stockanalysis 7.51; macrotrends 8.17 (2026-07-17) |
| Forward P/E | — | 8.34 | stockanalysis |
| P/S | — | 0.82 | stockanalysis |
| P/B | — | **1.02** (P/TBV 1.76) | stockanalysis |
| ROE | — | **16.5%** (ROIC 12.7%) | stockanalysis |
| ROA | 0.02 | 4.22% | stockanalysis |
| D/E | −1.65 | Ej tillämpligt för försäkring; bolaget rapporterar **debt-to-total capital 28.0%** (exkl. non-insurance) | Fairfax Q2'26 pressrelease 2026-07-30 |
| Direktavkastning | — | **CAD 20.69 → 0.9%** (men buyback-yield 34% → total shareholder yield ~35%) | stockanalysis 0.92%; Morningstar TTM 0.88% |
| Senaste kvartal | — | **Q2'26: net earnings $1,392.7M ($63.38/diluted), BVPS $1,304.39 (+4.8% H1 justerat), combined ratio 93.1%, underwriting profit $458.6M, ~3.5% av aktierna återköpta i kvartalet** | Fairfax pressrelease 2026-07-30; Quartr 2026-08-06; Alpha Spread earnings call |
| Konsensus | — | **Moderate Buy; snittriktkurs C$2,751.57 → +21% upside** (7 anl.; NBF C$3,450, RBC C$3,197, CIBC C$2,350) | MarketBeat; stockanalysis forecast; TipRanks C$2,827 |
| Nyheter 30 dgr | — | **Positivt:** Poseidon-försäljning ($838M realiserad vinst), Kennedy Wilson-privatisering, aggressiva återköp, TRS-avveckling; ledningen: "we think it still remains undervalued" | Fairfax pressrelease 07-30; earnings call 07-31; Alexander Steinberg substack 08-03 |

**Slutsats:** Klassisk Buffett-stil compounder: P/E ~8, P/B ~1.0, ROE 16.5%, combined ratio 93.1%, BVPS växer ~15%/år-mål, massiva återköp (34% buyback-yield). Systemets pe −17.51 och de −1.65 är rena datafel. **Klar undervärdering enligt marknaden** — konsensus +21% upside, ledningen köper egna aktier aggressivt.

---

### 2.3 BLK — BlackRock (systemranking 50.99)

| Mått | Systemet | Ground truth | Källa (verifierad) |
|---|---|---|---|
| P/E TTM | 7.28 | **27.8** (2026-08-29); 25.4 (TipRanks); 21.3 (2026-07-16, historicalperatio) | stockanalysis 27.84; TipRanks 25.4 |
| Forward P/E | — | **19.5** | stockanalysis |
| P/S | — | 6.93 | stockanalysis |
| P/B | — | 3.13 | stockanalysis |
| ROE | — | **12.3%** (ROIC 11.5%) | stockanalysis; TipRanks "0.10" (10%) |
| ROA | — | 3.74% | stockanalysis |
| D/E | −54.41 | **0.23** (current ratio 2.45, net debt −$1.13B) | stockanalysis |
| Gross margin | −0.03 | **47.2%** | stockanalysis |
| Piotroski F-score | 4 | **6** | stockanalysis (S&P Global) |
| Direktavkastning | — | **$22.92 → 1.97%** (16 år av tillväxt, payout 55%) | stockanalysis; TipRanks 1.92% |
| Senaste kvartal | — | **Q2'26: EPS $12.19 GAAP / $13.91 justerat vs $12.59 förväntat (BEAT), revenue +31% YoY, AUM rekord $15.3T, net inflows $192B, adj. op-marginal 45.9% (högst på ~5 år)** | BlackRock pressrelease 2026-07-15; Reuters 2026-07-15; SEC 10-Q |
| Konsensus | — | **Buy/Strong Buy; snittriktkurs $1,301–1,321 → +13–20% upside** (17–18 anl.; MS $1,488, GS $1,389, JPM uppgraderad till Overweight $1,364) | stockanalysis forecast $1,320.81; MarketBeat $1,301.35; Barchart 08-25 |
| Nyheter 30 dgr | — | **Mycket positivt:** rekord-AUM, IBIT dominerar Bitcoin-ETF-flöden ($277.6M på en dag = 115% av marknaden, 08-27), flera riktkurshöjningar efter Q2 | Reuters 07-15; CryptoSlate 08-28; Barchart 08-25 |

**Slutsats:** Världens största kapitalförvaltare med rekord-AUM $15.3T, 10% organisk base fee-tillväxt, Q2-beat och konsensus Buy med +13–20% upside. Systemets pe 7.28, de −54.41, gm −0.03 och f-score 4 är **alla fel** (verkligt: 27.8 / 0.23 / 47.2% / 6). Grovt felaktigt nedrankad.

---

### 2.4 UMG.AS — Universal Music Group (systemranking 27.19)

| Mått | Systemet | Ground truth | Källa (verifierad) |
|---|---|---|---|
| P/E TTM | 64.54 | **82–84** (distorderat av reavärderingsförluster på Spotify-innehav); 25.1 (SharesGrow, USD-basis) | stockanalysis 84.41; Yahoo 82.17 |
| Forward P/E | — | **~18–20** (2026E: 17.6–19.1x; 2027E: 15.9–17.2x) | MarketScreener 17.6x/15.9x; Stocksguide 19.11x; SharesGrow 21.1 |
| P/S | — | ~2.1 (rev €12.8B, mcap ~€27B) | stockanalysis |
| P/B | — | 5.01 | MarketScreener |
| ROE | — | 7.7% rapporterat (distorderat) / **~34% på justerad basis** | stockanalysis 7.67%; Simply Wall St 33.7% |
| ROA | 0.01 | 7.03% | stockanalysis |
| D/E | 90.81 | **0.73** (net debt/equity 0.64; finansiell net debt €4,131M efter Downtown + återköp) | stockanalysis ratios; UMG pressrelease 07-30 |
| Gross margin | ~0 | ~42% (GM €5.34B / rev €12.82B) | stockanalysis |
| Direktavkastning | — | **€0.52/år → 3.5%** (interim €0.24 + final €0.28; policy ≥50% av justerad vinst) | stockanalysis 3.52%; Yahoo 3.50%; UMG pressrelease |
| Senaste kvartal | — | **Q2'26: revenue +13.3% cc (+6.4% ex-Downtown), adj. EBITDA €674M +1.5%, adj. diluted EPS €0.47 (+4.3% cc), rapporterad EPS €0.12 (reavärderingsförluster), H1 FCF €24M (svagt), interimdividend €0.24** | UMG pressrelease 2026-07-30; Investing.com transcript; TipRanks earnings |
| Konsensus | — | **Buy; snittriktkurs €21.85–29.31 → +32–47% upside** (19–25 anl.; stockanalysis €21.85 +46.9%, Investing.com €25.81 +32.3%, MarketScreener €29.31) | stockanalysis forecast; Investing.com; MarketScreener; ChartMill |
| Nyheter 30 dgr | — | **Blandat:** stark topline-tillväxt + Streaming 2.0 + AI-partnerskap (Spotify), men marginalpress, svag FCF, aktien −35% på ett år; Wells Fargo uppgraderade till Overweight (03-28), UBS höjde (02-10) | Investing.com 07-30; Simply Wall St 08-19; MarketScreener |

**Slutsats:** Världens största musikbolag (Taylor Swift, Drake, etc.) med 13% cc-tillväxt och AI-partnerskap, men TTM-vinsten är distorderad av reavärderingsförluster på Spotify-aktier → rapporterat P/E 82–84 är missvisande; på justerad basis ~18–20x forward. Systemets de 90.81 är absurt fel (verkligt 0.73). Konsensus Buy med +32–47% upside. **Felaktigt nedrankad** — men notera att aktien faktiskt har underpresterat (marginalpress, FCF-svaghet) så rankingen är inte helt utan grund.

---

### 2.5 BURE.ST — Bure Equity (systemranking 30.41)

| Mått | Systemet | Ground truth | Källa (verifierad) |
|---|---|---|---|
| P/E | n/a | **Meningslöst** (investmentbolag; rapporterat 4.79 på fair-value-vinster, negativt 2025) | stockanalysis 4.79; companiesmarketcap −3.89 |
| P/B | — | **0.95** (P/NAV ~0.94) | Yahoo 0.95; stockopedia 1.13 |
| NAV/aktie | — | **SEK 342.9 (30 juni 2026, +28.4% H1); SEK 341.4 (19 aug)** | Bure interim report H1'26; TipRanks 08-20 |
| Aktiekurs | — | ~SEK 324 (27 aug) → **~5–6% rabatt mot NAV** | stockanalysis 324.20; Yahoo mcap 24.15B/74.65M aktier |
| D/E | −50.01 | **~0** (netto finansiella tillgångar SEK 543M; equity/asset 86%) | Bure interim report |
| ROA/gm | −0.14/−0.42 | Ej tillämpligt (fair-value-baserat) | — |
| Direktavkastning | — | **SEK 2.75 → 0.85–1.0%** | Yahoo 0.85%; stockanalysis 0.95% |
| Senaste kvartal | — | **Q2'26: NAV +41% i kvartalet (Silex-IPO, Mycronic +49%, Yubico), EPS SEK 78.0 (vs −52.4), Silex noterat 7 maj, CEO Henrik Blomquist avgår senast juni 2027** | Bure interim report; TipRanks 08-20 |
| Konsensus | — | **Tunn täckning:** GuruFocus snittriktkurs SEK 316.81 (+19% från 266.30, 40 anl. i aggregat); TipRanks "no data"; Danelfin AI-target SEK 286.12 | GuruFocus; TipRanks; Danelfin |
| Nyheter 30 dgr | — | **Positivt:** NAV-surge på Silex-IPO + tech-gains, återhämtning efter svagt 2025 | TipRanks 08-20; Bure interim report |

**Slutsats:** Svenskt kvalitetsinvestmentbolag (Mycronic, Yubico, Silex, Atle) som handlas till ~5–6% rabatt mot NAV efter +28% NAV-tillväxt H1'26. P/E, ROA och gross margin är **fel måttstock** för investmentbolag — värderingen ska sättas mot NAV. Systemets de −50.01 är datafel. **Felaktigt nedrankad** — men tunn analytikertäckning och CEO-avgång är genuina osäkerheter.

---

## 3. Verification Receipts

| # | Källa | URL | Datum (åtkomst) | Stöder påstående |
|---|---|---|---|---|
| 1 | StockAnalysis — SEB.A statistics | https://stockanalysis.com/quote/sto/SEB.A/statistics/ | 2026-08-29 | SEB P/E 13.52, fwd 12.07, P/B 1.83, ROE 14.08%, ROA 0.74%, D/E 5.13, div 5.19% |
| 2 | StockAnalysis — SEB.A ratios | https://stockanalysis.com/quote/sto/SEB.A/financials/ratios/ | 2026-08-29 | SEB D/E 5.13, ROE-historik, payout 69% |
| 3 | SEB pressrelease Q2 2026 | https://sebgroup.com/press/press-releases/2026/sebs-results-for-the-second-quarter-2026 | 2026-08-29 | SEB Q2: net profit 8,664M, ROE 15.7%, CET1 17.2%, EPS 4.44 |
| 4 | Finimize — SEB Q2 beat | https://finimize.com/content/sebs-q2-beat-points-to-a-busy-nordic-banking-summer | 2026-08-29 | SEB beat: 8.66B vs 7.68B förväntat (LSEG) |
| 5 | StockAnalysis — SEB.A forecast | https://stockanalysis.com/quote/sto/SEB.A/forecast/ | 2026-08-29 | SEB konsensus Hold, snitt 207.35 (17 anl.) |
| 6 | Investing.com — SEB consensus | https://www.investing.com/equities/s.e.b-consensus-estimates | 2026-08-29 | SEB Neutral, snitt 193.69 (16 anl.) |
| 7 | MarketScreener — UBS höjer SEB | https://ae.marketscreener.com/news/ubs-raises-its-price-target-for-seb-to-230-kronor-215-reiterates-neutral-ce7858ded981f02c | 2026-08-29 | UBS riktkurs SEK 230 (2026-08-27) |
| 8 | Wisesheets — SEB P/E & ROE | https://www.wisesheets.io/pe-ratio/SEB-A.ST | 2026-08-29 | SEB P/E 13.94, ROE 13.93% (korsverifiering) |
| 9 | Simply Wall St — SEB | https://simplywall.st/stocks/se/banks/sto-seb-a/skandinaviska-enskilda-banken-shares | 2026-08-29 | SEB P/E 13.4x, P/B 1.9x, div 5.2% (korsverifiering) |
| 10 | StockAnalysis — FFH statistics | https://stockanalysis.com/quote/tsx/FFH/statistics/ | 2026-08-29 | FFH P/E 7.51, fwd 8.34, P/B 1.02, ROE 16.48%, ROA 4.22%, div 0.92% |
| 11 | Fairfax pressrelease Q2 2026 | https://www.fairfax.ca/press-releases/fairfax-financial-holdings-limited-financial-results-for-the-second-quarter-2/ | 2026-08-29 | FFH Q2: $1,392.7M, BVPS $1,304.39, combined 93.1%, debt/capital 28.0% |
| 12 | Macrotrends — FFH P/E | https://www.macrotrends.net/stocks/charts/FRFHF/fairfax-financial-holdings/pe-ratio | 2026-08-29 | FFH P/E 8.17 (2026-07-17) (korsverifiering) |
| 13 | Morningstar — FFH dividends | https://www.morningstar.com/stocks/xtse/ffh/dividends | 2026-08-29 | FFH div $15 (2026), TTM yield 0.88% (korsverifiering) |
| 14 | MarketBeat — FFH forecast | https://www.marketbeat.com/stocks/TSE/FFH/forecast/ | 2026-08-29 | FFH Moderate Buy, C$2,751.57, +21.1% (7 anl.) |
| 15 | StockAnalysis — FFH forecast | https://stockanalysis.com/quote/tsx/FFH/forecast/ | 2026-08-29 | FFH Hold, $2,630, +15.7% (korsverifiering) |
| 16 | Alpha Spread — FFH Q2 call | https://www.alphaspread.com/security/tsx/ffh/investor-relations/earnings-call/q2-2026 | 2026-08-29 | FFH buybacks 680k aktier $1.1B, Poseidon $838M gain |
| 17 | StockAnalysis — BLK statistics | https://stockanalysis.com/stocks/blk/statistics/ | 2026-08-29 | BLK P/E 27.84, fwd 19.47, P/B 3.13, ROE 12.28%, D/E 0.23, GM 47.15%, F-score 6, div 1.97% |
| 18 | BlackRock pressrelease Q2 2026 | https://www.blackrock.com/corporate/newsroom/media/press-releases/blackrock-reports-second-quarter-2026 | 2026-08-29 | BLK Q2: EPS $12.19/$13.91, AUM $15.3T, inflows $192B, op-marginal 45.9% |
| 19 | Reuters — BlackRock Q2 | https://www.reuters.com/business/blackrock-profit-jumps-buoyant-markets-boost-assets-2026-07-15/ | 2026-08-29 | BLK beat: $13.91 vs $12.59 förväntat (korsverifiering) |
| 20 | StockAnalysis — BLK forecast | https://stockanalysis.com/stocks/blk/forecast/ | 2026-08-29 | BLK Buy, $1,320.81, +13.4% (17 anl.) |
| 21 | MarketBeat — BLK forecast | https://www.marketbeat.com/stocks/NYSE/BLK/forecast/ | 2026-08-29 | BLK Moderate Buy, $1,301.35, +19.7% (korsverifiering) |
| 22 | Barchart — BLK targets | https://www.barchart.com/story/news/4019975/what-are-wall-street-analysts-target-price-for-blackrock-stock | 2026-08-29 | BLK Strong Buy, mean $1,319.94 (2026-08-25) |
| 23 | CryptoSlate — IBIT | https://cryptoslate.com/blackrock-just-pulled-in-115-of-all-bitcoin-etf-inflows-in-a-single-day-as-rival-funds-bleed-cash/ | 2026-08-29 | IBIT $277.6M = 115% av marknaden (2026-08-27) |
| 24 | StockAnalysis — UMG statistics | https://stockanalysis.com/quote/ams/UMG/statistics/ | 2026-08-29 | UMG P/E 84.41, fwd 14.17, ROE 7.67%, ROA 7.03%, div 3.52% |
| 25 | StockAnalysis — UMG ratios | https://stockanalysis.com/quote/ams/UMG/financials/ratios/ | 2026-08-29 | UMG D/E 0.73, net debt/equity 0.64 |
| 26 | UMG pressrelease Q2 2026 | https://www.universalmusic.com/universal-music-group-n-v-reports-financial-results-for-the-second-quarter-and-half-year-ended-june-30-2026/ | 2026-08-29 | UMG Q2: rev +13.3% cc, adj EBITDA €674M, adj EPS €0.47, net debt €4,131M, interim div €0.24 |
| 27 | Yahoo Finance — UMG.AS | https://finance.yahoo.com/quote/UMG.AS/ | 2026-08-29 | UMG P/E 82.17, div 3.50%, 1y target 21.85 (korsverifiering) |
| 28 | MarketScreener — UMG consensus | https://www.marketscreener.com/quote/stock/UNIVERSAL-MUSIC-GROUP-N-V-127080831/consensus/ | 2026-08-29 | UMG Outperform, snitt €29.31, fwd P/E 17.6x/15.9x |
| 29 | Investing.com — UMG consensus | https://uk.investing.com/equities/universal-music-nv-consensus-estimates | 2026-08-29 | UMG Buy, snitt €25.81, +32.3% (19 anl.) (korsverifiering) |
| 30 | Simply Wall St — UMG | https://simplywall.st/stocks/nl/media/ams-umg/universal-music-group-shares/past | 2026-08-29 | UMG ROE 33.7% justerat, FY25 EPS €0.84 |
| 31 | Bure interim report H1 2026 | https://storage.mfn.se/a/bure-equity/1bb45fb3-065f-40c9-b9ba-f465299acc3b/bure2026_en.pdf | 2026-08-29 | Bure NAV SEK 342.9/aktie, +28.4% H1, EPS 78.0, div 2.75, Silex-IPO |
| 32 | StockAnalysis — BURE | https://stockanalysis.com/quote/sto/BURE/ | 2026-08-29 | Bure P/E 4.79, P/B ~0.95, kurs 324.20 (27 aug), div 0.95% |
| 33 | Yahoo Finance — BURE key stats | https://finance.yahoo.com/quote/BURE.ST/key-statistics/ | 2026-08-29 | Bure P/B 0.95, mcap 24.15B, div 0.85% (korsverifiering) |
| 34 | GuruFocus — BURE forecast | https://www.gurufocus.com/stock/CHIX:BURES/forecast | 2026-08-29 | Bure snittriktkurs kr316.81, +19% |
| 35 | TipRanks — BURE news | https://www.tipranks.com/news/company-announcements/bure-equitys-net-asset-value-surges-on-silex-ipo-and-tech-gains | 2026-08-29 | Bure NAV +28.4% H1, Silex-IPO, CEO-avgång |

---

## 4. Blockers / Inte gjort

1. **UMG forward P/E spretar** (14.2–22x beroende på källa): stockanalysis anger 14.17 (troligen på annan EPS-bas), MarketScreener 17.6x (2026E), SharesGrow 21.1x, Simply Wall St 22x (vid högre kurs €19.87). Rapporterat intervall ~18–20x på konsensus-EPS €1.04 (2026E). Ej fullt korsverifierat — markera som intervall.
2. **Bure analytikertäckning är tunn och motstridig:** GuruFocus anger snittriktkurs kr316.81 (40 anl. i aggregat, +19% från kurs 266.30), medan TipRanks saknar data helt och Danelfin anger AI-target 286.12. Bure-kursen varierar mellan källorna (266–324 SEK beroende på datum) — använd stockanalysis 324.20 (27 aug) som aktuell.
3. **BLK P/E-historik spretar** (20.7–27.8) beroende på mätdatum och EPS-bas (GAAP vs justerat, aktieantal). Använt stockanalysis 27.84 (2026-08-29, senaste) som primär.
4. **FFH D/E:** försäkringsbolag rapporterar inte D/E på industribasis; bolagets eget mått är debt-to-total capital 28.0%. Systemets −1.65 kan inte verifieras som "fel siffra" mot en specifik källa — men är inte ett meningsfullt mått för bolaget.
5. **Nyhetssentiment** är kvalitativt bedömt från sökresultat (rubriker + datum), inte från ett formellt sentiment-API. Positivt/negativt/neutralt per aktie är en rimlig sammanfattning av de citerade källorna.
6. **Exa-sökning rate-limiterad** under sessionen — kompenserat med websearch + webfetch (stockanalysis.com direktläst).