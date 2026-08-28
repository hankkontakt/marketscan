# Alpha-forskning för MarketScan — nordiska småbolag & gratis datapunkter

> **Forskningsrapport 2026-08-28.** Runda-för-runda-undersökning: (1) vad som har evidens
> för att ge alpha i nordiska/Europeiska aktier, (2) vilka datapunkter som krävs,
> (3) hur MarketScan får dem BILLIGAST (verifierade priser 2026-08-28).
> Alla påståenden är kopplade till källa. Gissningar är märkta.

---

## 0. Sammanfattning (verdict först)

| Fråga | Svar (evidensbaserat) |
|---|---|
| Ska vi specialisera oss i **nordiska småbolag**? | **JA** — men av rätt anledning: *informationsasymmetri/under-täckning* gör att faktorer och signalserier ger mer där, inte att småbolag i sig ger avkastning. |
| Ger "small cap" i sig alpha? | **NEJ i Norden.** Flera oberoende studier 1995–2025 (SSE 2020, Uppsala 2025, JYX 2025) hittar INGEN signifikant size-premie, inte ens kvalitetskontrollerad. |
| Vad ger då alpha i Norden? | **KVALITET (QMJ)** — mest robusta och bäst evidensbaserade (80–90 bps/mån alfa i nordiska mikro/small 1989–2025, NTNU 2025; AQR: fungerar i 23/24 länder, peer-reviewed). **Momentum 12-1** (+ volatilitetsskalad) — andra mest robusta. Resten: signaler (insiderkluster, shorts) och värde (svag, låg vikt). |
| Hur billigt kan vi göra det? | **0 kr/mån** för kärnan: yfinance (har), Finnhub free (har), FI-insider (byggd), **FI:s blankningsregister (ny, verifierad gratis)** + Q-rapport-extraktion via egen LLM-pipeline (Gemini free tier, planen finns redan). |
| När kostar det pengar? | Börsdata Pro+ 59 €/mån (~680 kr) ger ALLT på ett ställe (rapportdata+insider+shorts+buybacks+estimates) — kvalitetshöjaren om täckningen i småbolag sviker. |
| Största risken för "falsk alpha"? | **Survivorship-bias + transaktionskostnader** (84–100 bps spread i småbolag!). Motverkas av: plattformens EXISTERANDE prediction-outcomes-loop (forward-validering, inte historisk backtest) + kostnadsantagande ≥1 % per sida. |

---

## 1. Vad ligger bakom ett validerat alpha-anspråk?

Alpha = meravkastning riskjusterat som INTE förklaras av marknadsfaktorer.
Tre saker som avgör om ett påstående är genuint:

1. **Det överlever transaktionskostnader.** Nordiska småbolag har **~84 bps
   relativ spread (Nasdaq Nordic jan-2022, Swedish House of Finance 2023)**,
   stora bolag ~9 bps. Norska small/mid-cap: ~95–97 bps snitt, ökade efter
   MiFID II (-research-unbundling). Kombinerat med courtage ≈ **1 % per sida**
   är en realistisk kostnadsmodell. SHoF:s exempel: 5 omsättningar/år med 1 %
   kostnad per handel → halverad årsavkastning. **En screening-produkt som
   rekommenderar högfrekvent omsättning i småbolag äter upp sig själv.**
2. **Det är inte look-ahead/survivorship.** Historiska backtests på fri data
   (yfinance o.d.) saknar konsekventa avlistningshistorik → "tro på
   forward-testning" (se §7).
3. **Evidensen är oberoende och återkommande** — inte en enskild
   "hemlig faktor".

---

## 2. Faktorerna — evidens rangordnad för NORDEN/EUROPA

### 2.1 Kvalitet (QMJ) — KÄRNFAKTOREN ⭐⭐⭐⭐⭐

**Definition (Asness, Frazzini, Pedersen 2019, Review of Accounting Studies):**
- **Profitability:** ROE, ROA, CFOA (OCF/tillgångar), GMAR (gross margin /
  Novy-Marx bruttoresultat/tillgångar), låga accruals.
- **Growth:** 5-årig tillväxt i profitability-mått (småbolag: 3-årig pga datalängd).
- **Safety:** låg beta, låg idiosynkratisk vol, låg hävstång (DE, net debt/EBITDA),
  låg ROE-volatilitet, låg bankruptcy-risk (Z/O-Score).
- **Payout:** netto-utgivning (dilution: negativt), netto-payout/resultat.

**Evidens:**
- **NTNU 2025 (Heggli & Haugland, masteruppsats, 4 länder 1989–2025):**
  kvalitetsanpassat MSCI Nordic Micro & Small-Cap: **90 bps/mån alpha
  (micro), 80 bps/mån (small)** vs sina benchmarks; premien VÄXER när
  företaget blir mindre; robust över bransch/regim/storlek.
  *Caveat: masteruppsats, ej peer-reviewed — men i linje med*
- **AQR (peer-reviewed):** QMJ ger signifikant alfa 66 bps/mån (US 1-faktor),
  fungerar i 23/24 länder, även 20-årssubsamples. QMJ klappar positivt vid
  kriser (flight-to-quality), inte crash-risk.
- **Svenska oberoende studier bekräftar kvalitetspremien** (SSE 2020: "consistent
  quality premium in Sweden"; Uppsala 2025: kvalitet ökar R² från 0.028→0.120,
  "quality loads negative on size-portfolio" t=-5.3).
- **Size+Kvalitet = "Size matters if you control your junk"** (Asness m.fl. 2018,
  JFE): storlekspremien ÅTERKOMMER när man kvalitetskontrollerar — i USA.
  I Norden: kvalitetspremien finns, size-premeion gör det inte ens med kvalitet
  (SSE 2020: SMB-alfa −0.03 %/mån, ns; Uppsala 1995–2025: ns).

**Slutsats för produkten:** Scorebolagen på KVALITET i tvärsnittsskikt → det är
där premiens tyngdpunkt ligger. Small-cap är kontexten (starkare signal, mer
ineffektivt) — men sälj INTE "småbolag" som edge, sälj "kvalitet bland småbolag".

### 2.2 Momentum 12-1 (+ vol-skalad) — KÄRNFAKTORN NR 2 ⭐⭐⭐⭐

- **Evidens:** Jegadeesh–Titman-bas: robust i USA och Europa; **Nordic-studie 2026
  (UTU, 1 299 bolag DK/FI/NO, 1990–2025):** momentum ger signifikant positiv
  avkastning; "above-average momentum returns vs other developed markets";
  RESIDUAL momentum + volatilitetsskalning minskar risk/MaxDrawdown medan alfa
  behålls (semi-vol-skalad = bäst Sharpe); crash-risk koncentrerad till
  marknadsomslags-regimer. JYX 2025-tesis: **momentum mest stabila faktorn i
  Norden**, BAB och kvalitet också positiva (alla cykliska).
- **Produktimplementering:** 12-1 (hoppa senaste månaden), vol-skalad
  (avkastning/vol) för att kapa crash-risk; månadsvikt. KOMBINERBAR med kvalitet
  (låg korrelation, factor diversification > country diversification i Norden).

### 2.3 Insiderkluster — signalfaktor, GRATIS data ⭐⭐⭐

- **Svensk studie (Lund 2015, 125 657 transaktioner 2005–2014):** kluster
  (≥3 olika insiders, samma typ, kort tidsfönster) = **stark signalförstärkning**;
  **Mid- & Small-Cap ger högre abnormal avkastning än Large**; säljkluster har
  större förklaringskraft än köpkluster. (Redan byggt i spec 03.)
- **Svenska studier 2016–2024 (FI-data):** aggregerade insiderköp + titlar
  predikterar framtida meravkastning på 30/60-dagarshorisont — signifikant men
  varierande; long-only-portfölj presterar > OMXSGI men är till stor del
  marknadsbeta (FF3).
- **Svensk event-studie 2022–2024:** insiderköp → signifikanta CAR, **small-cap
  högre** (informationsasymmetri); position + handelsstorlek + volatilitet
  förklarar storleken.
- **Finland (2017–2021, 2019–2025):** köp ger signifikanta CAR (kort fönster,
  ekonomiskt måttliga, <1 %); CEO/CFO-handlar mest informativa; småbolag störst
  estimat. Ekonomisk betydelse för retail: begränsad, men som EN del av scoring
  medför den riktningsnytta.
- **Fönster:** klustersignalen verkar 1–3 mån; enskild trade 2–5 dagar.

### 2.4 Short-positions (EU-blankningsregistreringen) — GRATIS, riskfilter ⭐⭐⭐

- **Regelverk:** sedan 2012 (Reg. EU 236/2012): netto-short ≥0,5 % ska
  PUBLICERAS (+varje 0,1 % och vid nedgång under). ≥0,1 % rapporteras till
  regulator. ESMA hostar nationella länkar. **Data:
  Finansinspektionen publicerar "Current", "Historic" och "Aggregate
  positions"-Excel-filer + HTML-tabell — verifierat 2026-08-28, gratis,
  realtid, med LEI-koder.** (Se sidan med allt från SBB 15,16 % till Nanexa 0,31 %.)
- **Evidens (blandad — viktigt att vara ärlig):**
  - Jones, Reed & Waller (J. Finance 2016): efter stora disclosure-händelser
    är **90-dagars-CAR −5,23 %** (signifikant) — stora shortsäljare är välinformerade.
  - Jank–Smajlbegovic: hedgefonder tjänar ~5,5 %/år FF-alfa på sina korta positioner
    (från samma typ av data).
  - Della Corte m.fl.: "short conviction"-strategi >8 %/år brutto, överlever
    låne-/borrow-kostnader (15 EU-marknader 2012–2018).
  - **Ashby 2024 (UK, fri data):** naiva L/S-portföljer på samma signal → högst
    marginell signifikans; kortsidan förlorar.
- **Produktbeslut:** använd INSIDER-short-data som (a) **riskfilter** (undvik
  topp-5–10 % mest blankade, flagga plötsliga NYA disclosures: Jones-effekt),
  (b) sentiment-dämpare i scoringen. Inte som standalone-alpha-motor.

### 2.5 Värde — svag i Europa/Norden ⭐⭐ (använd försiktigt)

- Europa: HML ej signifikant / förklaras av size (Ghent 2002: europaregionens
  value-premium ~2 %/år ns; P/B-inslaget försvinner inom storleksskikt).
- Foye 2016: value & momentum finns på europeisk nivå, size är landsspecifik.
- Invesco/TalTech 2008–2019: **value var den SÄMSTA faktorn i Norden**
  (högst vol, lägst Sharpe).
- Kvalitets-Caveat: HML är "prisbaserad" — i Europa absorberas den av size/junk.
- **Produktbeslut:** EV/EBITDA (branschjusterat) + FCF-avkastning som
  SEKUNDÄR komponent (t.ex. 10–15 % vikt), aldrig P/B-ledd. Piotroski F-score
  finns redan — den hör hemma under kvalitet, inte "value".

### 2.6 PEAD / resultatöverraskelse — fas 2 ⭐⭐⭐

- PEAD är en av de mest persistenta anomalierna; Europa: signifikant (Aalto 2018:
  negativ överraskning → tydlig drift; positiv → initial överreaktion + korrektion;
  **större drift i mindre bolag**; Gerard 2012: stressad under info-osäkerhet;
  Eurozonen 2008–2017: ~0,5–0,9 %/mån, robust efter krisen).
- **Datacaveat:** klassisk PEAD kräver analytikerestimater (dyr data).
  **Fifte-fritt:** standardiserad överraskelse mot *seasonal random walk*
  (samma kvartal i fjol) — Livnat & Mendenhall: TS-forecasts fungerar; +
  abnormal volume som förstärkare. Kräver: rapporterdatum + tal ur rapporterna
  (vår Q-rapport-pipeline täcker).
- Fönster 20–60 dagar efter rapport; kvartalsvis rebalansering.

### 2.7 Övrigt som HAR evidens men INTE rekommenderas som kärnspår

| Faktor | Evidens | Varför inte kärna |
|---|---|---|
| Raw size/SMB | **Död i Norden** (flera studier) | Skulle vara ett falskt löfte |
| BAB/låg-vol | Positiv i Norden (JYX) | Finns gratis (vol) — kan in i "safety"-komponenten av kvalitet |
| Illikviditetspremie | Blandat (Butt-Virk: dollarnollretur-prefemium signifikant; senare studier ns) | Svår att fånga utan market-making; döljs i spread |
| Buybacks | Börsdata har data (Pro+); evidens i Europa generellt svag | Data-delikat + låg vikt |
| Säsongseffekter | Januari-effekt säsongstypiskt svagare i Norden | Regelefterlevnad av redan kända effekter |

---

## 3. Universumsbeslutet: först SMART NORDIC SMALL/MICRO — varför, och varför INTE heleuropa

**För "nordiska småbolag" som fokus:**
1. **Informationsasymmetri** är den gemensamma mekanismen bakom de starkaste
   signalerna (insider, PEAD, kvalitetsprisning). Den är störst där analytiker-
   täckning är lägst — nordiska small/micro (MiFID II minskade täckningen
   ytterligare, NO-studie: spread +~100 bps).
2. **Kvalitetspremien växer när storleken minskar** (NTNU 2025; AQR small/large
   jämförbara; Asness 2018: "small high-quality outperform large high-quality").
3. **Nordiska studier är enhetliga** (QMJ, momentum MOST, faktor-diversifiering >
   lands-diversifiering — JYX).
4. **Data-tillgång gratis är bäst i Sverige** (FI:s marknadssök för insyn +
   FI:s blankningsregister — båda centralt publicerade). Norge/Danmark/Finl:
   insider-disclosure via börsmeddelanden (svårare, fas 2).
5. **Produkt/logik:** svensk plattform, svenska användare, Avanza/Nordnet-kunder.

**Emot heleuropa:** (a) diversifiering över 15+ länder & valutor späder den
under-täckning som skapar signalen; (b) size/value-preemior beter sig olika per
land (Foye: value & momentum på EU-nivå, size landsspecifik); (c) insider- och
shorts-data kräver NCA-per-land-integrationer; (d) du tappar din
informationsfördel som svensk niche. **Europa = expansionsfas, inte start.**

**Universum-definition (förslag):** Nordiska börser (SE/NO/DK/FI, main + First
North/Oslo Børs/Børs-Market/Wall Street), market cap **~50 Mkr–5 000 Mkr** —
dvs. exkludera micro så illikvida att spredditen dödar, samt large caps där
signalerna är svagast. Implementera som FILTER, inte som "premium" — via
likviditetströsklar (turnover ≥ X mkr/dag, t.ex. 1–2 Mkr) + max-spread-proxy
(Amihud-ILLIQ från yfinance-volym) — det är din "rule of thumb" som skyddar
användare från omsättningsbarhetsfällan.

---

## 4. Datapunkterna — checklista per faktor + var de hämtas

| Faktor | Datapunkter | Källa (gratis) | Källa (betald) | Kostnad |
|---|---|---|---|---|
| **Kvalitet: Profitability** | ROE, ROA, bruttomarginal, OCF/tillgångar, accruals | yfinance .financials (delvis småbolag) + Q-rapport-extraktion (egen, punkt-i-tid!) | Börsdata Pro+ (KPI:er, 20 år) | 0 kr / 59 €/mån |
| **Kvalitet: Safety** | skuldsättning (DE, ND/EBITDA), räntetäckning, ROE-vol, beta/IVOL | yfinance (balansräkning + priser) — levererbar | Börsdata | 0 kr |
| **Kvalitet: Growth** | 3-5 års tillväxt: omsättning, EBIT, ROE | yfinance + Q-rapporter | Börsdata | 0 kr |
| **Kvalitet: Payout** | netto-utgivning (aktieantal-ändring), utdelningsandel | yfinance + rapporter (aktieantal i balansräkning) | Börsdata (Buyback) | 0 kr |
| **Momentum** | 12-1-månadsavkastning, vol-skalad (ev. residual), 50d/200d | yfinance EOD (har) | — | 0 kr |
| **Insidertransaktioner** | 3+ unika köpare/30 d, exekvsifilter, belopp/mcap, säljkluster | **FI marknadssök bulk (har/brand)** | Börsdata (Insider) | 0 kr |
| **Short-positions** | Total short %, Δ-positioner, NYA disclosures (händelse), antal innehavare | **FI blankningsregister — Excel + HTML (verifierat)** | Börsdata (Short selling) | 0 kr |
| **Värde (sekundärt)** | EV/EBITDA (sektorjust), FCF-avkastning | yfinance + egna beräkningar | Börsdata | 0 kr |
| **PEAD (fas 2)** | TS-SUE (jfr samma kvartal i fjol), abnormal vol, rapportdatum | **Egen Q-rapport-pipeline (rag/existing) + Finnhub earnings-calendar** | Börsdata (Estimates) | 0 kr |
| **Estimates (fas 2+/valfritt)** | konsensus EPS, revisions | Saknas gratis för nordiska small-caps i bulk | Börsdata Pro+ / Morningstar API (entitlement, dyr) | — |
| **Benchmark-backtest-data** | Faktorfaktorer (MKT/SMB/HML/UMD/QMJ) för Norden/Europa | **AQR Data Library (gratis!)** + Kenneth French Library (gratis) | — | 0 kr |

**Nyckeldesignval — hur vi får FUNDAMENTA billigt och rätt:**
- **Punkt-i-tid-korrekthet** är enda sättet att undvika look-ahead. yfinance ger
  SNAPSHOT-data (dagens siffror, ingen versionshistorik). **Vår Q-rapport-pipeline
  (redan planerad, spec 04: svensk dokumentintelligens) ger den riktiga
  egenskapen**: raden är giltig FRÅN PUBLICERINGSDATUM. Bygg en
  `company_financials_pit`-tabell: (ticker, metric, value, valid_from) —
  extrahera ~12-15 nyckeltal per rapport (omsättning, EBIT, netto,
  eget kapital, totala skulder, OCF, aktieantal, utdelning) med Gemini Flash
  (free tier, 1000 req/dygn — räcker för ~1000 bolag/kvartal) + template
  fallbacks. **Detta är den största enskilda värdeadderaren i hela planen.**
- **Kvalitets-bulkfallback:** för bolag där extraktion misslyckas helt →
  yfinance-fallback → om täckningen < ~70 % i small-cap-skiktet: överväg
  Börsdata Pro+ (59 €/mån) — se prisbilden.

---

## 5. Prisbild — VERIFIERAD 2026-08-28 (inga antaganden)

| Källa | Gratis? | Pris | Täckning | Anmärkning |
|---|---|---|---|---|
| **yfinance** | ✅ | 0 kr | Kurser/OHLCV + .info + financials | Litet småbolag hål i fundamentals (First North/NGM); bulk-rate-limit-risk (befintlig del av pipeline) |
| **Finnhub (free)** | ✅ | 0 kr | 60 calls/min; profile2, quote, insider-transactions | Ingen descriptions i free; insider-endpoint långsam/skral i Sverige (därför FI-bulk) |
| **FI marknadssök (insyn)** | ✅ | 0 kr | BULLK, svenska emittenter, allt från 2000-talet | Redan byggd (fi_insider_bulk.py). Realtid, JSON+HTML+Excel |
| **FI blankningsregister** | ✅ | 0 kr | Svenska emittenter; >0,1 % aggregerat, >0,5 % med innehavare; historisk Excel | **Verifierat live 2026-08-28.** Current + Historic + Aggregate positions (xlsx). Realtid och automatisk |
| **AQR Data Library** | ✅ | 0 kr | QMJ + MKT/SMB/HML/UMD månadsvis per land/region, inkl. Sverige/Norden | Används för validering: "spelar vår kvalitetspremie med?" |
| **Kenneth French Data Library** | ✅ | 0 kr | Europe-faktorer | Dito |
| **Börsdata Premium** | Delvis (webb) | **10 €/mån (~115 kr)** | 1 700 nordiska bolag, 10 års historia, screener, CSV-export max 50/dag | Ingen REST-API. Utmärkt för manuell kontroll, för dålig för automatisering av hela universum |
| **Börsdata Pro** | — | **25 €/mån (~290 kr)** | +20 års, global, estimates, insider/shorts/holdings/buyback-data i webb | API-status: officiella sidor anger "API-Key kräver Pro/Pro+" medan Feb-2025-ändringen flyttade REST-API till Pro+. **Verifiera innan köp** |
| **Börsdata Pro+** | — | **59 €/mån (~680 kr)** | REST-API (JSON) för Nordic + Global + Holdings; kommersiell licens; ~2000 KPI:er | "Allt på en gång" — den dyraste men kompletterande kvalitetslösningen. Årsavtal kan ge rabatt |
| **Financial Modeling Prep** | ✅ Basic (obegränsad passiv) | 0 kr (250 req/dag); Starter $22/mån | Profil + EOD-kurser + delvis fundamentals; betona US → **EU/nordisk småbolagstäckning svag; säkraste användningen är fallback** | Redan delvis i pipelinen (company_info_fetcher) |
| **Alpha Vantage** | ✅ men 25 req/dag | n/a | För lite volym för hela universumet | Rekommenderas ej |
| **Morningstar API / LSEG / Refinitiv** | Nej | Dyrt (entitlement) | Full täckning + estimates | Utanför budget; nämns bara som "vad som KOSTAR om du ville ha allt" |

> **Sammantagen kostnadsbild:**
> - **Nivå 1 (rekommenderad): 0 kr/mån** — allt gratis ovan, inkl. egen
>   Q-rapport-extraktion (Gemini free tier; DeepSeek-fallback redan i budgetramen
>   50–150 kr/mån vid behov). Detta täcker kvalitet+momentum+insider+shorts+PEAD.
> - **Nivå 2 (om fundamental-täckning sviker): +59 €/mån (~680 kr)** för
>   Börsdata Pro+ som bulk-berikning + estimates + buybacks. Beslut efter
>   mätbar täckningsstatistik (se §7 gate).

---

## 6. MARKETSCAN-IMPLEMENTERING (billigast väg) — förslag i faser

### Fas 0 — Mätning först (0 kr, 1-2 dagar)
- Utöka `prediction_outcomes` med 90/180-dagars-horisonter + per-faktor-loggning
  (vilket betyg gavs, vilket utfall). **Börja logga NU — historik kostar tid.**
- Lägg AQR-faktorer (gratis) som referensbenchmark.

### Fas 1 — Kärnan: Quality×Small-screener (0 kr; bygger på befintlig scorer)
- Bygg QMJ-z-score-komposit (cross-sectional ranks per
  large/small/sub-grupper) utöver befintlig Piotroski/FCF: lägg till GMAR,
  CFOA, accruals, leverage, ROE-vol, netto-utgivning.
- Viktingsstart **kvalitet 40 % / momentum 25 % / insider-cluster 15 % /
  värde 15 % / likviditetsfiltrering 5 %** — sedan VALIDERA loggar-först-
  och-vikt-om (se §7). (Evidensen ger riktning, plattformens egen
  walk-forward-IC ger vikterna.)
- Universumsfilter: 50 Mkr–5 000 mkr + likviditetströskel (turnover/Amihud).

### Fas 2 — Gratis signaler: shorts + insider-utbyggnad (0 kr; 2-4 dagar)
- Ny worker `fi_short_positions.py`: hämta FI:s Excel (Current/Historic/
  Aggregate) dagligen → `short_positions`-tabell (ticker/LEI, total_short_pct,
  datum, holder-nivå för >0,5 %). Idempotent + 0-rads-larm (efter mönstret från
  spec 03).
- Scoring-integration: riskfilter (`short % > tröskel` → poängavdrag/-flagga),
  händelseflagga på NYA disclosures (−vikt 90 dagar, Jones-effekt).
- Insiderkluster (spec 03, redan delvis byggd): lägg till säljkluster-
  varningssignal (säljkluster har större förklaringskraft i Sverige — Lund 2015).
- Norge/Danmark/Finland-insider: fas 2b via börsmeddelanden (news-parsing) —
  bygg om och endast om Sverige-signalen valideras.

### Fas 3 — PEAD (0 kr; bygger på Q-rapport-pipelinen)
- `company_financials_pit`-tabell + extraktion av 12-15 KPI:er per rapport
  (Gemini Flash free, template-fallback, punkt-i-tid `valid_from`).
- TS-SUE (samma kvartal i fjol ± volym-förstärkare) → drift-signal 20-60 d.

### Fas 4 (valfritt, kräver beslut) — Börsdata Pro+ 59 €/mån
- Om täckningsgate inte uppfylls: bulk-berikning estimates/buybacks/holdings.

---

## 7. VALIDERINGSAVTALET — det som skyddar pengarna (MÅSTE)

1. **Deploy-gate:** ny scoring slår nuvarande i walk-forward (purged CV, embargo;
   spec 01: ml_validation.py) på **både Rank IC och decil-spread**, **netto
   1 % per sida i kostnader**, annars ingen skarp lansering.
2. **Forward > backward:** historiska backtests på fri data är behäftade med
   survivorship. Plattformen HAR redan den robusta mekanismen:
   dagliga snapshots → R2-parquet-arkiv = punkt-i-tid-universum. **Kör
   skugg-/paper-validering live** (prediction_outcomes) och publicera en
   "track record"-sida — det är den ärligaste och mest differentierande
   produktegenskapen ("vi mäter oss själva").
3. **Täckningsgate:** om kvalitets-extraktion täcker < 70 % av
   small-cap-universum → antingen skär likviditetsfilter eller uppgradera data.
4. **Kommunikationsregel:** visa faktorpoäng + empirisk utfallshistorik, aldrig
   ett "alpha-löfte". Marknadsföringsclaim "ger alpha" = falsk exponering;
   "evidensbaserade signaler med mätbar track record" = hållbart.
   (Juridiskt: en generisk screening-tool med verktygskriterier räknas inte som
   personlig investeringsrekommendation enligt MiFID II — men onödiga
   "rekommendation"-formuleringar bör undvikas; detta är produktpositionering,
   inte juridisk rådgivning.)

---

## 8. Risker & begränsningar (ärligt)

| Risk | Verklighet |
|---|---|
| Alpha är inte garanterat | Även den robusta QMJ-premien är ~80-90 bps/mån GROSS (NTNU, akademisk konstruktion); netto efter 1 %/sida och kvartalsvis omsättning: betydligt mindre. Säg det. |
| Falsk precision | QMJ NR 1-studien är en masteruppsats (stark men ej peer-review). Därför vikta: multi-studie-konsensus (AQR peer-reviewed) + egen validering. |
| Småbolags-data är smutsig | yfinance hål; numrering/ticker-mappning skör (byte av ticker, klyvningar); kräver dedup + rekonstruerade kurser (split-adjusted). |
| Sammanfogad signal + tidsfönster | Momentum vs kvalitet kan konfliktera; insider fönster kortsiktigt; sätt signal-fönster per faktor och låt walk-forward avgöra. |
| Mässmodeller | Regimberoende (plan #15) kan vrida vikter — men först efter bevisad gynnelse. |
| Regulation | Produkten säger ALDRIG "köp" — bara odds-signaler med källor. |

---

## 9. KÄLLOR (alla valda: primära, aktuella)

1. Heggli, E. D. & Haugland, K. A. (2025). *Quality Matters: The Rising Importance of
   Quality as Firm Size Decreases in Nordic Markets.* NTNU. hdl.handle.net/11250/3211172
2. Asness, C., Frazzini, A., Pedersen, L. H. (2019). *Quality Minus Junk.*
   Review of Accounting Studies 24(1), 34-112. AQR-pdf: aqr.com/-/media/AQR/.../Quality-Minus-Junk.pdf
3. Asness, Frazzini, Israel, Moskowitz, Pedersen (2018). *Size Matters if You
   Control Your Junk.* JFE 129(3). SSRN 2553889
4. Tynkkynen, S.-P. (2025). *The size premium and firm quality: evidence from
   Nordic equity markets.* JYX, Jyväskylä. urn.fi/URN:NBN:fi:jyu-202506275829
5. Hansson & Westesson (2020). *Is there a Swedish Size Effect? Controlling for
   Quality.* Stockholm School of Economics. arc.hhs.se MediumId=4636
6. Gidhagen, M. (2025). *Does size matter? Evidence from the Swedish stock
   market.* Uppsala University. diva2:2037803
7. Johansson, H. (2026, UTU). *Enhanced momentum strategies in the Nordics —
   Denmark, Finland, Norway, 1990-2025.* utupub.fi/items/166fb22e-...
8. JYX (2019-ish) *Time-varying factor premia in Nordic equities.*
   jyx.jyu.fi/bitstreams/23cdeea2-... (BAB, momentum, quality; momentum mest stabil)
9. Ek, P. & Erlinder, K. (2015). *Insider trading and abnormal return on the
   Swedish stock market.* Lund University. lup.lub.lu.se/student-papers/record/7793807
10. *Predictive Power of Insider Trading on the Swedish Stock Market* (2024).
    DiVA. diva2:1878302 (FI-data 2016-2024)
11. *Explaining Abnormal Returns from Insider Purchases* (2025). Gothenburg.
    gupea.ub.gu.se/items/d213ae81-... (2022-2024, small > large)
12. *The Signaling Effect of Insider Trading on the Swedish Stock Market* (2018).
    DiVA diva2:1296843 (2014-2016; CAR 1,27 % dag(0;1) köp; starkare i småbolag)
13. Mankonen, A. (2025). *The Performance of Corporate Insider Transactions*
    + *Effects of Insider Trading on Abnormal Return: Evidence from Finland
    2017-2021.* Aalto/UTU.
14. Jones, Reed & Waller (2016). *Revealing Shorts: ... Large Short Position
    Disclosures.* Rev. Financial Studies 29(12). ideas.repec.org/a/oup/rfinst/...
15. Copenhagen Economics (2021-2022). *Market impact of short sale position
    disclosures* (herding + 0,06 %/dag-effekt; dansk dubbeldata).
16. Jank, S., Smajlbegovic, E. (2017). *Dissecting short-sale performance.*
    CF WP 1515. (hedge funds ≈ 5,5 %/år FF-alfa)
17. Ashby, M. (2024). *Is Regulatory Short Sale Data a Profitable Predictor of
    UK Stock Returns?* University of Cambridge. doi.org/10.17863/cam.110731
18. Foye, J. (2016). *A new perspective on the size, value, and momentum effects.*
    Review of Accounting and Finance. doi.org/10.1108/raf-05-2015-0065
19. Ghent WP 02/146. *Value and size effect* (europeisk cross-section 1974-2000;
    look-ahead-bias-demonstration).
20. Vuorela, S. (2018). *Post-earnings announcement drift: European evidence.*
    Aalto. (PEAD europeisk; småbolag mer drift)
21. Gerard, X. (2012). *Information Uncertainty and the PEAD in Europe.* FAJ 68(2).
22. Swedish House of Finance (2023). *The Retail Investment Boom and the Cost
    of Trading Small Stocks.* houseoffinance.se (84 bps småbolagsspread; 9,1 bps large)
23. Utkilen & Wakeford-Wesmann (2019). *Liquidity following MiFID II — Norwegian
    small and mid-cap.* hdl.handle.net/11250/2609729
24. FI — Blankningsregister: fi.se/en/our-registers/net-short-positions/
    (verifierat 2026-08-28; Current/Historic/Aggregate-positioner, xlsx, LEI)
25. Börsdata pristabell + API-sida: borsdata.se/en/pricetable;
    borsdata.se/en/info/api/changes2025 (REST-API → Pro+ från 1 feb 2025)
26. FMP pricing: site.financialmodelingprep.com/developer/docs/pricing
    (gratis 250 req/dag; Basic; Starter $22/mån)
27. AQR Data Library: aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly
28. ESMA short selling-sida: esma.europa.eu/.../short-selling (nationella länkar)

*Slut på rapport. Nästa steg är ditt beslut: nivå 1 (0 kr), nivå 2 (59 €/mån
om täckningen sviker), eller en hybrid (nivå 1 nu + Börsdata Premium 10 €/mån
för manuell datakontroll). Rekommendation: nivå 1 + fas 0-mätning omedelbart.*
