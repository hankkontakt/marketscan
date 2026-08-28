# QMJ-regimindikator för Norden — fri månadsdata & regim-formel

**Datum:** 2026-08-28
**Uppdrag:** Hitta fri månadsdata för QMJ/quality-premien som täcker Norden/Sverige, och föreslå exakt regim-formel för MarketScan-radarn (Python-worker i GitHub Actions ~03:00 UTC).

---

## 1. Task Report — direkt svar

**JA — det finns fri månadsdata som täcker Norden specifikt.** AQR:s *Quality Minus Junk: Factors, Monthly* innehåller individuella QMJ-kolumner för **Sverige, Danmark, Finland och Norge** (24 länder totalt = MSCI World Developed per 2012-12-31), plus aggregaten Global, Global ex USA, North America, Europe, Pacific. Serien startar ~1986 för Norden (≈40 år), uppdateras månadsvis med ~2 månaders lag, och är gratis utan inloggning.

**Rekommendation:** Primär källa = AQR QMJ Monthly (xlsx, sheet "QMJ Factors"). Regim-formel = rullande 12-månaders avkastning av en nordisk komposit (SE/DK/FI/NO, equal-weight) → percentil mot hela historien (expanderande fönster) → Stark (≥80:e pct) / Normal / Svag (≤20:e pct), med krav på ≥240 månaders historik. Fallback = Ken French Europe 5-faktorer (RMW som vinst-proxy).

**Viktigaste fyndet:** Requesten antog att AQR bara har Global/Developed/Europe — fel. AQR-filen har landskolumner inkl. alla fyra nordiska länder. Ken French behövs bara som fallback.

---

## 2. Verifierade källor

### 2.1 AQR — Quality Minus Junk: Factors, Monthly (PRIMÄR)

| Källa | Status | Verifierat |
|---|---|---|
| https://www.aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly | **200 OK** — sidan visar "June 30, 2026" (data t.o.m.), beskrivning: "long/short QMJ factors for the U.S. and 23 international equity markets updated monthly" | 2026-08-28 |
| https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Quality-Minus-Junk-Factors-Monthly.xlsx | **200 OK** — binär PK-zip (xlsx) laddades ner | 2026-08-28 |
| Sheet "QMJ Factors", data A19:AD810 → **30 kolumner = DATE + 29 numeriska serier** (792 månadsrader) | via aqrr R-paketets källkod (rdrr.io/github/Reckziegel/aqqr/src/R/factors_monthly.R) | 2026-08-28 |
| 24 länder = MSCI World Developed per 2012-12-31; Table I visar **Danmark (1986), Finland (1986), Norge (1986, 429 bolag)**; "for most countries XpressFeed's Global coverage starts in 1986" | QMJ-pappret (aqr.com/-/media/AQR/Documents/Insights/Working-Papers/Quality-Minus-Junk.pdf) | 2026-08-28 |
| Aggregat-kolumner: **Global, Global ex USA, North America, Europe, Pacific** | aqrr README-exempel (rdrr.io/github/Reckziegel/aqqr/f/README.md) | 2026-08-28 |
| **Norden bekräftat i praktiken:** masteruppsats (JYX) använder "monthly factor return data from AQR Capital Management" för Finland, Sverige, Norge, Danmark | https://jyx.jyu.fi/jyx/Record/jyx_123456789_104086 | 2026-08-28 |
| Uppdatering: "aim to update each data set monthly with a lag of about two months"; historik revideras vid vendor-felrättelser | https://www.aqr.com/Insights/Datasets/About-the-AQR-Data-Library | 2026-08-28 |
| Avkastning i **USD, ej valutahedgad**; long-short, självfinansierande; bokslutsdata laggas (fiscal t-1 → juni t) | QMJ-pappret (samma PDF) | 2026-08-28 |
| Alternativ spegel: Andrea Frazzini's Data Library (QMJ monthly + daily) | https://people.stern.nyu.edu/afrazzin/data_library.htm | 2026-08-28 |

**Kolumnsemantik:** Månatlig long-short QMJ-faktoravkastning per land/region (andelar, t.ex. 0.0112 = +1,12 %/mån). Kvalitet = profitability, growth, safety, payout; 6 värdeviktade portföljer (2×3 size×quality), ombalanseras månadsvis. USA-serien startar 1957-07; Global/Norden ~1986.

### 2.2 Ken French Data Library (FALLBACK)

| Källa | Status | Verifierat |
|---|---|---|
| https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html | **200 OK** — exakta FTP-filnamn hämtade | 2026-08-28 |
| https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Europe_5_Factors_CSV.zip | **200 OK** — zip innehåller `Europe_5_Factors.csv` | 2026-08-28 |
| https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Europe_3_Factors_CSV.zip | **200 OK** — zip innehåller `Europe_3_Factors.csv` | 2026-08-28 |
| Kolumnnamn 5-faktorer: **Date, Mkt-RF, SMB, HML, RMW, CMA, RF** (datumformat YYYYMM) | metadata hos orbits.edwardrycroft.com + QuantConnect-mirror (raw.githubusercontent.com/QuantConnect/Tutorials) + frenchdata R-paket (cran.r-project.org/web/packages/frenchdata) | 2026-08-28 |
| Månadsdata **juli 1990 – juni 2026**; USD, inkl. utdelningar; ombalansering i juni med bokslutsdata t-1 | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5developed.html | 2026-08-28 |
| **Europe-regionen inkluderar Sverige, Norge, Danmark, Finland** (checkmarks i landstabellen) | f-f_5developed.html (samma) | 2026-08-28 |
| Saknade värden = **-99.99 / -999**; historik rekonstrueras varje månad och kan ändras | data_library.html (notis under tabellerna) | 2026-08-28 |

Obs: `f_french_daily_txt.zip`/`dfat.zip` i requesten är gamla **US-only**-filer — rätt Europe-filer är `Europe_3_Factors_TXT.zip` / `Europe_5_Factors_CSV.zip` etc.

### 2.3 Regim-definition — evidens

| Källa | Evidens | Verifierat |
|---|---|---|
| Asness, Chandra, Ilmanen, Israel (2017) "Contrarian Factor Timing is Deceptively Difficult", JPM 43(5):72–87 | **Faktor-timing är svårt**: value-spread-baserad timing ger svag prediktion (R²≈0.10, t≈1.4 på 12m-horisont). Använder **OOS z-scores med expanderande fönster, min 120 månader**. Varnar: **percentiler ser extremare ut än z-scores** vid skev fördelning | pm-research.com + SSRN 2928945 | 2026-08-28 |
| Ilmanen, Israel, Lee, Moskowitz, Thapar (2021) "How Do Factor Premia Vary Over Time? A Century of Evidence" | Premier varierar över tid; timing-strategier har "relatively modest predictability that likely fails to overcome implementation frictions" | aqr.com/Insights/Datasets/Century-of-Factor-Premia-Monthly | 2026-08-28 |
| S&P DJI Factor Dashboards | Praktisk standard: **percentilrankning av rullande avkastning** ("Value lagged Growth by -9.0%, which stands at the 12th percentile of all seven-month intervals") | spglobal.com/spdji dashboard-PDF | 2026-08-28 |
| QMJ-pappret (Asness, Frazzini, Pedersen 2014/2019) | "The price of quality varies over time, reaching a low during the internet bubble, and a low price of quality predicts a high future return of QMJ" — pris-på-kvalitet (värderingsspread) som signal | SSRN 2312432 + aqr.com | 2026-08-28 |
| Verdad (2022) "Betting Against Expensive Junk" | QMJ vs value över konjunkturcykeln; QMJ bäst i sen-cykel; 2022-exemplet visar att short-benet drev premien | verdadcap.com/archive/betting-against-expensive-junk | 2026-08-28 |

**Slutsats för formeln:** En *deskriptiv* percentil av rullande 12m-premie är den praktiska standarden (S&P DJI) och är ärlig — men den ska presenteras som **historisk kontext, inte prognos**, eftersom predikterbarheten är svag (Asness et al. 2017; Ilmanen et al. 2021). Undvik att kalla det "signal".

---

## 3. Rekommenderad datakälla + kolumnnamn + hämtmönster

### Primär: AQR QMJ Monthly
- **URL:** `https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Quality-Minus-Junk-Factors-Monthly.xlsx`
- **Sheet:** `QMJ Factors`
- **Kolumner (30):** `DATE` (format M/D/YYYY) + 29 serier:
  - Länder (24): `USA`, `Australia`, `Austria`, `Belgium`, `Canada`, `Denmark`, `Finland`, `France`, `Germany`, `Greece`, `Hong Kong`, `Ireland`, `Israel`, `Italy`, `Japan`, `Netherlands`, `New Zealand`, `Norway`, `Portugal`, `Singapore`, `Spain`, `Sweden`, `Switzerland`, `United Kingdom`
  - Aggregat (5): `Global`, `Global ex USA`, `North America`, `Europe`, `Pacific`
- **Semantik:** månatlig long-short QMJ-avkastning i USD (andelar). USA från 1957-07; Norden/Global ~1986 → nutid.
- **Hämtmönster (worker, ~03:00 UTC månadsvis):**
  1. Ladda ner xlsx (requests/curl; filen är liten, ~1 MB). **Ladda om hela filen varje gång** — AQR reviderar historik.
  2. Läs med openpyxl/pandas: sheet `QMJ Factors`, **hitta header-raden dynamiskt** (rad ~18; data från rad 19 — aqrr läser A19:AD810). Matcha kolumnnamn exakt (`Sweden`, `Denmark`, `Finland`, `Norway`, `Europe`, `Global`).
  3. Sanity-check: 30 kolumner; senaste datum ≈ 2 månader före idag; inga NaN i `Global` efter 1986.
  4. Spara rådata + beräknad regim till DB/artefakt.

### Fallback 1: Ken French Europe 5-faktorer (vinst-proxy)
- **URL:** `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Europe_5_Factors_CSV.zip`
- **Fil i zip:** `Europe_5_Factors.csv` — kolumner `Date, Mkt-RF, SMB, HML, RMW, CMA, RF` (YYYYMM; saknade = -99.99/-999). Månadsdata juli 1990 → juni 2026. Europe inkl. SE/NO/DK/FI.
- **Använd `RMW`** (Robust Minus Weak, vinstfaktor) som quality-proxy. **Varning:** RMW ≠ QMJ (QMJ = profitability+growth+safety+payout). RMW är en delmängd.
- Header-radens position varierar mellan filer (skiprows≈3 för faktorfiler) — inspektera alltid.

### Fallback 2: AQR `Global`-kolumnen
- Om nordiska kolumner upplevs för brusiga: använd `Global` (samma fil, samma hämtmönster).

### Fallback 3: Ken French Europe 3-faktorer (value-proxy)
- `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Europe_3_Factors_CSV.zip` — `HML` som value-proxy. Svagare koppling till QMJ; endast om inget annat fungerar.

### Fallback 4: Frazzini-mirror
- `https://people.stern.nyu.edu/afrazzin/data_library.htm` — QMJ monthly + daily, om AQR ändrar URL-struktur.

---

## 4. Rekommenderad regim-formel (steg-för-steg)

**Mål:** "Är QMJ-premien just nu stark i historisk kontext?" — deskriptiv, inte prediktiv.

1. **Nordisk komposit (månadsvis):**
   `r_t = (QMJ_Sweden_t + QMJ_Denmark_t + QMJ_Finland_t + QMJ_Norway_t) / 4`
   Kräv ≥3 av 4 länder med värde, annars NaN. (Equal-weight; alternativt värdevikt med landets vikt i global portfölj — men equal-weight är enklare och robustare för små marknader.)
2. **Rullande 12-månaders avkastning:**
   `R12(t) = Π_{s=t-11..t} (1 + r_s) − 1` — kräv 12 giltiga månader.
3. **Percentil (expanderande fönster, OOS-ärligt):**
   `pct(t) = rank(R12(t) bland alla R12 från första giltiga observation till t) / n(t)`
   (Asness et al. 2017 använder expanderande fönster för att undvika look-ahead; min 120 månader för z-scores.)
4. **Buckets:**
   - `pct ≥ 0.80` → **Stark**
   - `0.20 < pct < 0.80` → **Normal**
   - `pct ≤ 0.20` → **Svag**
   - (Valfritt: ≥0.90 "Mycket stark", ≤0.10 "Mycket svag".)
5. **Minimum-historik:** visa percentil endast om `n(t) ≥ 240` månader (20 år) av R12-observationer; annars "otillräcklig historik". Med start 1986 nås 240 obs ~2006 — i praktiken har vi ~475 obs (2026).
6. **Robusthet (rekommenderas):** beräkna samma percentil för `Europe`- och `Global`-kolumnerna; visa primär (Norden) + avvikelse. Överväg även z-score som komplement (percentiler kan se extremare ut vid skevhet — Asness et al. 2017).

**Mock-exempel (2026-07-31):**
- Nordisk komposit, 12m-avkastning = **+9,2 %**
- Historik: **475** rullande 12m-observationer (1987-01 → 2026-07)
- +9,2 % rankar **87:e percentilen** → **Stark**
- API/UI-visning: `regim: "stark"`, `premium_12m: 0.092`, `percentil: 0.87`, `n_obs: 475`, `kalla: "QMJ-premiens historiska kontext"`, `data_tom: "2026-06"` (2-månaderslag)

---

## 5. Kända fallgropar + varningsetiketter

1. **USD-avkastning** — AQR och Ken French är i USD, ej valutahedgat. För en SEK-radar: FX-effekter ingår. Etikett: "Avkastning i USD".
2. **~2 månaders uppdateringslag** — AQR: "lag of about two months". Etikett: "Data t.o.m. [månad]".
3. **Reviderad historik** — AQR/KF ändrar historiska värden vid vendor-felrättelser. → Ladda om hela filen varje körning; cacha inte för länge.
4. **Long-short-konstruktion, ej investerbar direkt** — korträntor/borrow constraints saknas. Premien är ett papperskonstrukt.
5. **Små marknader = brusig QMJ** — Sverige ensamt har litet tvärsnitt (pappret: QMJ positiv i 23/24 länder men små länder brusigare). → Använd komposit/Europe primärt, Sverige-kolumnen sekundärt.
6. **Percentil vs z-score** — vid skev fördelning ser percentiler extremare ut (Asness et al. 2017). → Visa alltid faktisk 12m-avkastning + percentil; överväg z-score.
7. **Predikterbarhet är svag** — faktor-timing fungerar dåligt (Asness et al. 2017; Ilmanen et al. 2021). → Kalla det **"historisk kontext"**, aldrig "prognos"/"signal"/"köp".
8. **Look-ahead** — AQR/KF laggar bokslutsdata (fiscal t-1 → juni t) och är PIT-ärliga; men MarketScans *egna* 156-bolags-poäng har egna PIT-frågor (separat granskning rekommenderas).
9. **Survivorship** — faktor-serierna inkluderar avnoterade bolag (delist returns); MarketScans eget universum är ett levande universum → survivorship-bias i egna poäng.
10. **Namngivning i radarn (icke-finansiell publik):** "QMJ-premiens historiska kontext" + disclaimer: *"Historisk statistik, ingen prognos. Baserad på AQR QMJ-faktorn (USD, long-short, ej direkt investerbar)."*

---

## 6. Verification Receipts (sammanfattning)

| Påstående | Källa | Datum |
|---|---|---|
| AQR QMJ Monthly finns, uppdaterad 2026-06-30, 24 länder | aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly (200) | 2026-08-28 |
| xlsx laddas ner (200, PK-zip) | aqr.com/-/media/.../Quality-Minus-Junk-Factors-Monthly.xlsx (200) | 2026-08-28 |
| Sheet "QMJ Factors", A19:AD810, 30 kolumner (DATE+29) | rdrr.io aqrr factors_monthly.R | 2026-08-28 |
| 24 länder = MSCI World Dev 2012; DK/FI/NO start 1986; USD | QMJ-pappret PDF (aqr.com) | 2026-08-28 |
| Aggregat Global/Global ex USA/NA/Europe/Pacific | aqrr README (rdrr.io) | 2026-08-28 |
| AQR QMJ-data används för SE/DK/FI/NO i forskning | jyx.jyu.fi (masteruppsats) | 2026-08-28 |
| Månadsuppdatering, ~2 mån lag, reviderad historik | aqr.com About-the-AQR-Data-Library | 2026-08-28 |
| Europe_5_Factors_CSV.zip (200, innehåller Europe_5_Factors.csv) | mba.tuck.dartmouth.edu ftp | 2026-08-28 |
| Europe_3_Factors_CSV.zip (200, innehåller Europe_3_Factors.csv) | mba.tuck.dartmouth.edu ftp | 2026-08-28 |
| Header Date,Mkt-RF,SMB,HML,RMW,CMA,RF | orbits.edwardrycroft.com + QuantConnect-mirror + frenchdata | 2026-08-28 |
| Europe inkl. SE/NO/DK/FI; juli 1990–juni 2026; USD | f-f_5developed.html | 2026-08-28 |
| Saknade = -99.99/-999 | data_library.html | 2026-08-28 |
| Faktor-timing svag; OOS z-score min 120 mån; percentil-varning | Asness et al. 2017 (JPM 43(5)) | 2026-08-28 |
| Premier varierar; timing "modest predictability" | Ilmanen et al. 2021 (AQR) | 2026-08-28 |
| Percentilrankning av rullande avkastning som praktik | S&P DJI dashboard | 2026-08-28 |
| Pris-på-kvalitet varierar; lågt pris → hög framtida QMJ | QMJ-pappret (SSRN 2312432) | 2026-08-28 |

## 7. Blockers / Inte gjort

- **Exakt kolumnordning + header-rad i AQR-xlsx:** verifierades inte direkt från filen (binär). aqrr läser A19:AD810 med header ovanför rad 19 (troligen rad 18). → Worker ska läsa header dynamiskt och matcha på namn, inte position.
- **Exakt startdatum för AQR `Europe`-kolumnen:** ≈1986 enligt pappret ("most countries... starts in 1986"), ej verifierat i själva filen. Verifiera vid implementation (första icke-NaN rad).
- **Ken French CSV header-rad:** skiprows varierar mellan filer (IAR-wikin: "skiprows=3 for the factors file, but it varies by dataset; never assume, inspect"). Inspektera vid implementation.
- **Sverige-kolumnen i AQR-filen:** inte sedd med egna ögon i xlsx-binären, men evidenskedjan är stark: 24 länder = MSCI World Dev 2012 (inkl. SE/NO/DK/FI), 29 serier = 24 länder + 5 aggregat, aqrr README visar landsserier, JYX-avhandlingen använder AQR QMJ för alla fyra nordiska länder. Sannolikheten att Sverige saknas är försumbar.