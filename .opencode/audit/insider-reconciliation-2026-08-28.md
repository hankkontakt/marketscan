# Insider-transaktioner SE/Norden — datakällsverifiering för same-day-rekonciliering

**Datum:** 2026-08-28
**Uppdrag:** Verifiera EXAKT nuvarande (2026) fria datakällor för insider-transaktioner i Sverige/Norden + fältsemantik för rekonciliering (Nasdaq vs FI).
**Metod:** Live-förfrågningar (webfetch) — varje källa nedan är verifierad med HTTP 200 + faktiska rader, om inte annat anges.

---

## Task Report — direkta svar

### 1. Nasdaq Nordic "Managers' Transactions"/insiderlista — **DEPLATTFORMAD (borta)**
- `https://www.nasdaqomxnordic.com/Insider`, `/insider`, `/insider/MainPage?languageId=1` och `/Admin/TransactionList` — **alla omdirigerar (redirect) till nya `nasdaq.com/european-market-activity`** (verifierat live 2026-08-28). Ingen insider-tabell finns på den nya sidan.
- Gamla data-proxyn `https://www.nasdaqomxnordic.com/webproxy/DataFeedProxy.aspx?SubSystem=Insider&...` — **död** (omdirigerar till nya sajten; verifierat live).
- **Nasdaq pekar nu själv bort från insider-data:** nya Company News-sidan (`nasdaq.com/european-market-activity/news/company-news`) säger ordagrant: *"All Prospectuses, Swedish issuers' flaggings and **Swedish and Danish management transactions are available on the relevant National Competent Authority's (FSA) webpage**"* och länkar "Insider transactions" → `marknadssok.fi.se/publiceringsklient` (FI:s register). För Danmark → `finanstilsynet.dk` (OAM).
- **Slutsats:** Nasdaq Nordic har slutat publicera en egen "Managers' Transactions"-lista. Det finns **ingen gratis Nasdaq-endpoint för nordiska insidertransaktioner idag**. Befintlig kod som bygger på Nasdaq-insidertabell (query.action-mönster) är bruten.
- Wayback/CDX gav inga snapshots av `/insider*` (exakt nedläggningsdatum ej fastställbart via arkiv; live-redirect + Nasdaqs egen hänvisning till NCA är tillräcklig bevisning).

### 2. Finansinspektionen (fi.se) — **JA, öppet register finns och är LIVE**
- FI:s **Insynsregister / PDMR transactions register** är offentligt och sökbart sedan 3 juli 2016 (MAR:s ikraftträdande). Äldre transaktioner (tillbaka till 1995) förvaras hos FI.
- **Verifierat live (200 + rader):** `https://marknadssok.fi.se/publiceringsklient/en-GB/Search/Start/Insyn` — 166 978 poster, rader daterade 2026-08-28 (samma dag), full fältuppsättning (ISIN, datum, volym, pris, valuta, karaktär, person, befattning, närstående, status).
- **CSV-export verifierad live (200 + rader):** `.../en-GB/Search/Search?SearchFunctionType=Insyn&Publiceringsdatum.From=2026-08-27&Publiceringsdatum.To=2026-08-28&button=export&Page=1` → UTF-16-CSV med **fler fält än HTML-tabellen**: LEI-code, Notifier, Amendment, Trading venue, Status m.fl.
- **Uppdateringsfrekvens:** löpande; anmälningar via e-legitimation publiceras direkt. **Gratis**, ingen API-nyckel. Export till Excel/CSV inbyggd.
- **Täckning:** emittenter med säte i Sverige + tredjelandsemittenter med Sverige som hemmedlemsstat (FI Q&A). Handelsplatser i data: NASDAQ STOCKHOLM AB, OMX NORDIC EXCHANGE STOCKHOLM AB, FIRST NORTH SWEDEN (- SME GROWTH MARKET), NORDIC GROWTH MARKET, NORDIC SME, SPOTLIGHT STOCK MARKET, "Outside a trading venue". **Inte** FI/DK/NO-emittenter.
- **Tröskel:** anmälningsplikt först vid ≥ 20 000 EUR ackumulerat per emittent och kalenderår (MAR art. 19.8) — transaktioner under tröskeln saknas i registret.

### 3. ESAP (Europe Single Access Point) — insider-data i **Fas 2 (10 januari 2028)**
- ESAP-förordningen (EU) 2023/2859; ESMA ska driva portalen från **10 juli 2027**.
- **Fas 1:** insamling från 10 juli 2026 (Transparency Directive, Prospectus, Short Selling) — publik åtkomst juli 2027.
- **Fas 2:** **10 januari 2028** — inkluderar **MAR (596/2014)** = insynstransaktioner (art. 19) och insiderinformation (art. 17). Insamling + publicering sker samtidigt.
- **Fas 2bis:** januari 2029. **Fas 3:** januari 2030 (om bekräftat efter review-rapport jan 2029). Frivillig inlämning från 10 januari 2030.
- **Nyans (Danmark):** DFSA anger att PDMR-transaktioner som publiceras via OAM räknas som "regulated information" enligt Transparency Directive och därmed ingår redan i **ESAP fas 1**. För Sverige är FI:s register vägen in.
- Konsekvens: **ESAP är inte en källa förrän tidigast jan 2028** — bygg inte på det nu.

### 4. Nasdaq Stockholm-insider = MAR-avslöjanden? — **Ja, men Nasdaq publicerar dem inte längre själv**
- Under MAR art. 19 anmäler PDMR till **både** FI **och** emittenten; emittenten offentliggör inom 2 arbetsdagar (Nasdaq "Guidelines for Insiders", dec 2024). Samma transaktion ska alltså finnas i FI:s register OCH i emittentens börsmeddelande (Nasdaq news-system) — men Nasdaq har **ingen strukturerad insider-tabell** längre.
- "Planned change"-flaggan fanns i Nasdaqs gamla tabell (Nasdaqs egen annotering). FI-registret har i stället fälten "Initial notification" och "Linked to share option programme" + karaktär (Förvärv/Avyttring/Teckning/…). Distinktionen planned-vs-utförd är alltså inte längre tillgänglig som Nasdaq-fält.

---

## Källförteckning (verifierad live 2026-08-28)

| # | Källa | URL | Status | Bär vilka påståenden |
|---|-------|-----|--------|----------------------|
| 1 | FI PDMR-sök (HTML) | https://marknadssok.fi.se/publiceringsklient/en-GB/Search/Start/Insyn | 200 + 166 978 rader, datum 28/08/2026 | Fältuppsättning, täckning, uppdatering, gratis |
| 2 | FI PDMR-export (CSV) | https://marknadssok.fi.se/publiceringsklient/en-GB/Search/Search?SearchFunctionType=Insyn&Publiceringsdatum.From=2026-08-27&Publiceringsdatum.To=2026-08-28&button=export&Page=1 | 200 + UTF-16-CSV-rader | CSV-fält (LEI, Trading venue, Status, Amendment…), korrekt datumfiltrering |
| 3 | FI sv-SE sök (kanoniska params) | https://marknadssok.fi.se/publiceringsklient/sv-SE/Search/Search?SearchFunctionType=Insyn&Publiceringsdatum.From=2026-08-27&Publiceringsdatum.To=2026-08-28&button=search&Page=1 | 200 + 115 rader (2-dagarsfönster) | Parameternamn `Publiceringsdatum.From/To` fungerar |
| 4 | FI sv/Search + FromDate/ToDate + format=json (repo:ns nuvarande mönster) | https://marknadssok.fi.se/publiceringsklient/sv/Search?SearchFunctionType=Insyn&FromDate=2026-08-27&ToDate=2026-08-28&Page=1&PageSize=5&format=json | 200 men **datumfilter ignorerat** (166 978 rader) + HTML ej JSON | **Bug i befintlig `fi_insider_bulk.py`** — fel paramnamn |
| 5 | Nasdaq Nordic insider (gammal) | https://www.nasdaqomxnordic.com/Insider, /insider, /insider/MainPage?languageId=1, /Admin/TransactionList, /webproxy/DataFeedProxy.aspx?SubSystem=Insider | Redirect → nya sajten, ingen insider-data | Nasdaq insiderlista deplattformad |
| 6 | Nasdaq Company News (ny) | https://www.nasdaq.com/european-market-activity/news/company-news | 200 | Nasdaqs egen hänvisning: SE/DK management transactions → NCA (FI/DFSA); länk till marknadssok.fi.se |
| 7 | FI Insynsregistret (info) | https://www.fi.se/sv/vara-register/insynsregistret/ + https://www.fi.se/en/our-registers/pdmr-transactions/ | 200 | Offentligt sedan 3 juli 2016, löpande uppdatering, Excel-export, 20 000 EUR-tröskel |
| 8 | FI Q&A insynshandel (PDF) | https://www.fi.se/contentassets/ee10c244dd51477ab830b5f235274acc/2024-12-04-fragor-och-svar-insynshandel.pdf | 200 | Täckning: svenska emittenter + tredjeland med SE som hemmedlemsstat; tröskel per emittent |
| 9 | ESMA ESAP-sida | https://www.esma.europa.eu/esmas-activities/data/european-single-access-point-esap | 200 | Tidsplan: insamling jul 2026, publik jul 2027, Fas 2 jan 2028, 2bis jan 2029, Fas 3 jan 2030 |
| 10 | AMF France ESAP | https://www.amf-france.org/en/news-publications/news/european-single-access-point-financial-and-non-financial-information-european-entities-esap-enters | 200 | **MAR = Fas 2 (10 jan 2028)**; Fas 1 = TD/Prospectus/SSR |
| 11 | ESAP-förordningen | https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32023R2859 | 200 | ESAP senast 10 juli 2027; frivilligt från 10 jan 2030 |
| 12 | DFSA OAM/ESAP FAQ | https://www.dfsa.dk/financial-themes/capital-market/submission-of-announcements-and-notifications-to-the-danish-fsa-via-the-oam-system/faq-about-oam-and-esap | 200 | DK: PDMR-transaktioner via OAM = TD "regulated information" → ESAP fas 1 |
| 13 | finsyn/insynsregistret-js (open source) | https://raw.githubusercontent.com/finsyn/insynsregistret-js/master/fetcher.js | 200 | Bekräftar export-mönstret (`button=export`, `Publiceringsdatum.From/To`, UTF-16-CSV) |
| 14 | Nasdaq Guidelines for Insiders | https://www.nasdaq.com/docs/2024/12/03/Unofficial-translation-Guidelines-for-Insiders-Dec-4-2024.pdf | 200 | PDMR anmäler till FI + emittent; emittent offentliggör inom 2 arbetsdagar |

---

## Fältsemantik per källa

### A. FI:s insynsregister — HTML-tabell (verifierad live)
| Fält (EN) | Fält (SV) | Exempel (live 28/08/2026) | Kommentar |
|---|---|---|---|
| Publication date | Publiceringsdatum | 28/08/2026 | När FI publicerade |
| Issuer | Emittent | Tele2 AB / Brock Milton Capital AB | Fritext, stavningsvariationer |
| Person discharging managerial responsibilities | Person i ledande ställning | Thomas Reynaud / Henrik Milton | |
| Position | Befattning | Chairman of the Board / CEO | |
| Closely associated | Närstående | Yes | |
| Nature of transaction | Karaktär | Acquisition/Förvärv, Disposal/Avyttring, Subscription, Exercise increase/decrease | Köp/sälj-klassificering görs härifrån |
| Instrument name | Instrumentnamn | Total Return Swap / BROCK MILTON CAPITAL AB | |
| Instrument type | Instrumenttyp | Swap, Share, Call option | |
| ISIN | ISIN | SE0022757860 | **Tom för derivat (swaps/optioner)** |
| Transaction date | Transaktionsdatum | 25/08/2026 | |
| Volume | Volym | 78 535 / 546 | |
| Unit | Volymsenhet | Quantity/Antal | |
| Price | Pris | 169.3696 / 98.282051 | |
| Currency | Valuta | SEK | |
| Status | Status | Current / Revised / History | Revideringar finns |
| Details | Detaljer | Länk till anmälan | |

### B. FI:s insynsregister — CSV-export (verifierad live; UTF-16, semikolonseparerad)
`Publication date; Issuer; LEI-code; Notifier; Person discharging managerial responsibilities; Position; Closely associated; Amendment; Details of amendment; Initial notification; Linked to share option programme; Nature of transaction; Intrument type; Instrument name; ISIN; Transaction date; Volume; Unit; Price; Currency; Trading venue; Status`
- **Extra fält vs HTML:** `LEI-code` (t.ex. 213800EKD193RVI9HL76), `Notifier`, `Amendment`/`Details of amendment`, `Initial notification`, `Linked to share option programme`, **`Trading venue`** (NASDAQ STOCKHOLM AB / FIRST NORTH SWEDEN / SPOTLIGHT STOCK MARKET / Outside a trading venue …).
- **`Trading venue` är rekoncilieringskritiskt** — gör det möjligt att filtrera FI-rader till Nasdaq-handlade instrument.
- **HTML-tabellen duplicerar varje rad 2×; CSV:n har 1 rad/transaktion** → använd CSV-exporten som primärkälla.

### C. Nasdaq Nordic insider (HISTORISK, ej längre tillgänglig)
Gamla tabellen (före deplatformering) hade: Datum, Tid, Bolag, Insider, Position, Instrument, ISIN, Marknad, Volym, Pris, Valuta, Transaktionstyp (Köp/Sälj), **Planned change**-flagga. Ingen av dessa är idag hämtbar från Nasdaq.

### D. Danmark (sekundärt, för Norden-täckning)
DFSA OAM (`dfsa.dk`) publicerar manager-transaktioner som **PDF-anmälningar** (ESMA art. 19-formulär), inte strukturerade fält. Nasdaq länkar dit för danska management transactions.

---

## Rekommenderad rekoncilieringsnyckel

**Primärnyckel (FI-registret som sanningskälla):**
`(ISIN, Transaktionsdatum, Volym, Karaktär/nature-of-transaction)` — och vid matchning mot annan källa även `(PDMR-namn, Pris)` som sekundärkontroll.

**Motivering:**
1. **ISIN + datum + volym** identifierar en transaktion unikt i praktiken: två olika PDMR:er kan inte göra exakt samma volym i samma ISIN samma dag utan att det är samma händelse (eller en flaggvärd diskrepans).
2. **Pris är en svag nyckel** (varierar med exekveringstidpunkt; FI visar anmält pris, Nasdaq visar annat pris vid delade trades) — använd pris som *verifiering*, inte som nyckel.
3. **Karaktär (Förvärv/Avyttring)** måste normaliseras till buy/sell innan jämförelse (FI använder MAR-kategorier: Acquisition, Disposal, Subscription, Exercise increase/decrease, Gift…).
4. **ISIN kan vara tomt för derivat** (swaps/optioner — se Tele2-raden) → fallback-nyckel: `(Instrumentnamn, Transaktionsdatum, Volym)`.
5. **Volym kan vara delad** (samma person, flera rader samma dag) → aggregera per (person, ISIN, datum) innan jämförelse.
6. **Status=Revised/History** → ersätt originalraden vid rekonciliering, räkna inte båda.

**Vad som INTE går att rekonciliera mot:** Nasdaq har ingen insider-tabell längre. Enda Nasdaq-sidan är ostrukturerade börsmeddelanden (company news). Rekonciliering Nasdaq-vs-FI i ursprunglig form är **inte längre möjlig** — se riskanalys.

---

## ESAP-tidsplan (anteckning)

| Fas | Datum | Innehåll |
|---|---|---|
| Fas 1 | Insamling 10 jul 2026; publik 10 jul 2027 | Transparency Directive, Prospectus, Short Selling |
| **Fas 2** | **10 jan 2028** | **MAR (596/2014) — insynstransaktioner + insiderinformation**, SFDR, UCITS, BMR, PRIIPs m.fl. |
| Fas 2bis | jan 2029 | (ESMA) |
| Review | senast 10 jan 2029 | Kommissionens rapport → ev. uppskov max 36 mån |
| Fas 3 | 10 jan 2030 (om bekräftat) | MiFIR, SFTR, CRR, MiCA m.fl. |
| Frivilligt | från 10 jan 2030 | Alla emittenter kan lämna in |

Källor: ESMA (9), AMF (10), förordningen (11), Regnology/Mondaq (sekundärt). **Nyans:** DFSA menar att PDMR-transaktioner publicerade via OAM räknas som TD "regulated information" → kan ingå redan i fas 1 för DK (12).

---

## Kritisk riskanalys

1. **Nasdaq-feeden finns inte längre.** "Planned change"-vs-MAR-distinktionen är akademisk — Nasdaqs insider-tabell är borta och Nasdaq hänvisar själv till FI. All kod som hämtar insider från nasdaqomxnordic.com är bruten och bör ersättas.
2. **FI-registret är den enda auktoritativa strukturerade källan för SE** — och den är komplett för anmälningspliktiga transaktioner (MAR art. 19). **Rekommendation: gör FI-registret till primärkälla** (CSV-exporten, `button=export`), med kvalitetsgrind:
   - dedup (HTML duplicerar rader; CSV gör det inte),
   - hantera Revised/History-status,
   - normalisera karaktär → buy/sell,
   - filtrera på `Trading venue` om bara börshandel ska räknas (annars inkluderas "Outside a trading venue"),
   - 20 000 EUR-tröskeln innebär att småtransaktioner saknas — dokumentera som känd bias.
3. **Befintlig `fi_insider_bulk.py` har en aktiv bugg:** parametrarna `FromDate`/`ToDate` + `format=json` på `sv/Search` **ignorerar datumfiltret** (verifierat live: returnerade hela registret, 166 978 rader, som HTML). Korrekta parametrar: `Publiceringsdatum.From`/`Publiceringsdatum.To` (och `Transaktionsdatum.From`/`Transaktionsdatum.To`), `button=search`/`button=export`. JSON-formatet verkar inte existera — HTML/CSV är de fungerande vägarna.
4. **Same-day-rekonciliering Nasdaq-vs-FI är inte genomförbar som tänkt.** Alternativ som FUNGERAR:
   - **FI som enda källa + kvalitetsgrind** (rekommenderat; FI publicerar direkt, e-legitimation → omedelbart),
   - **FI vs Finnhub** (repo:ns `insider_fetcher.py`) som oberoende korskälla — diskrepans → suspicious-flagga (Finnhub täcker dock inte alla svenska småbolag),
   - **FI vs Nasdaq company-news** (ostrukturerade PDF:er) — dyrt, låg avkastning,
   - **Danmark:** DFSA OAM (PDF) — ingen strukturerad jämförelse utan parsning.
5. **ESAP löser inte problemet nu** — MAR-data tidigast jan 2028. Planera för ESAP som framtida korskälla, inte dagens.
6. **Norden-täckning:** FI-registret = SE-emittenter. FI/DK/NO kräver egna NCA-källor (DFSA OAM för DK; finska FIN-FSA publicerar inte motsvarande öppet register — Nasdaq länkar inte ens dit).

---

## Blockers / Inte gjort
- **Exakt deplatformeringsdatum för Nasdaqs insider-sida** kunde inte fastställas (Wayback/CDX gav inga snapshots av `/insider*`). Live-redirect + Nasdaqs egen NCA-hänvisning är dock entydig bevisning för att sidan är borta.
- **Finnhub-täckning för svenska småbolag** ej verifierad (kräver API-nyckel; utanför uppdraget).
- **DFSA OAM:s exakta fältstruktur** ej verifierad rad-för-rad (PDF-baserad; sekundär källa för DK).
- **Motstridiga källor:** ingen direkt motsägelse hittad. Enda nyansen: DFSA (12) placerar PDMR-transaktioner i ESAP fas 1 via TD-definitionen, medan AMF/Regnology (10) placerar MAR som helhet i fas 2 — båda är korrekta ur sina perspektiv (TD-regulated info vs MAR-legal act); för SE gäller fas 2.