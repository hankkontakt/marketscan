# Alpha-forskning DEL 3 — LIVE-TEST av datakällorna (2026-08-28)

> Tredje omgången. Här är **testat på riktigt, inte slutsatser i teorin** — mot
> riktiga nordiska tickers. Inkluderar korrigeringar av del 1-2 där mina
> antaganden inte höll.

---

## 1. TEST: yfinance mot nordiska småbolag (kördes live, python, yfinance 1.4.1)

| Ticker | Segment | Info (roe/marginal) | Års-financials | Kvartals-financials | Balansräkning | 1 års kurser |
|---|---|---|---|---|---|---|
| BOOZT.ST | Stockholm main, mid | ✅ (roe 11,1 %) | ✅ 49×5 | ✅ 41×6 | ✅ 70×5 | ✅ 251 d |
| SEDANA.ST | Stockholm main, small | ✅ (roe −4 %) | ✅ 41×4 | ✅ 37×5 | ✅ 64×5 | ✅ 251 d |
| NANEXA.ST | **First North, micro** (i dagens blankningslista) | ✅ (roe −14,8 %) | ✅ 43×5 | ✅ 40×5 | ✅ 57×5 | ✅ 251 d |
| ZINZINO.ST | (i FI:s blankningsregister 26 aug: 1,24 %) | ❌ **quote not found — "possibly delisted"** | ❌ | ❌ | ❌ | ❌ 0 d |
| TOKMAN.HE | Helsinki, mid | ✅ men **d2e=404** (misstänkt härlett värde!) | ✅ 50×4 | ✅ 43×6 | ✅ 68×5 | ✅ 251 d |
| NEL.OL | Oslo, small/mid | ✅ | ✅ 54×5 | ✅ 44×6 | ✅ 79×5 | ✅ 251 d |

**Korrigering av del 1:** Jag skrev "yfinance lite småbolag hål i fundamentals".
**Det stämmer INTE på det testade urvalet** — 5 av 5 levande nordiska småbolag
(inkl. en First North-micro) har komplett fundamentals + kurshistorik.

**De VERKLIGA riskerna som testet avslöjade:**
1. **Ticker-mappning + avlistning — det verkliga problemet (bevisas av ZinZino):**
   bolaget finns FORTFARANDE i FI:s blankningsregister (2026-08-26),
   men Yahoo har redan tagit bort tickern. Ett leverantörsagnostiskt
   **universum-register** måste vara grunden (FI-emittentlista med LEI/ISIN
   + Bolagsverkets status eller FI-registret som "levande"-källa),
   inte Yahoo. Yahoo-tickern är bara en DERIVAT-nyckel.
2. **Härledda nyckeltal i `.info` är opålitliga** (Tokmanni: debtToEquity 404,7×
   motverkandes av gratis balansräkning). **Regel: beräkna alla faktorer ur
   RÅA bokslutstabeller** (financials/quarterly_financials/balance_sheet —
   alla kompletta i testet), aldrig ur `.info`-nyckeltalen.
3. **Skala ej testad:** 1200-tickers-svep är en byggtids-uppgift — urvalet
   (main + First North + Oslo + Helsinki) tyder på god täckning, men kräver
   en täckningsstatistik (andel med all-4-tabeller) innan QMJ byggs på den.

---

## 2. TEST: FI:s blankningsregister (kördes live)

- **HTML-tabellen: verifierad, scrapbar** — full data 2026-08-28 (200+ rader,
  LEI + total short %, summan av >0,1 %-positioner, realtid uppdaterad 12:04).
- **Excel-filerna (Current/Historic/Aggregate):** länkarna finns INTE i
  statisk HTML (0 förekomster av "xlsx"/"Positionsinnehavare" — sidan
  renderar dem via JavaScript). **Korrigering av del 1:** Excel-URL:en ska
  identifieras i DevTools vid byggtillfället, inte antas.
  **Fallback (verifierad): scrapa HTML-tabellen veckovis/dagligen** + arkivera
  i egen tabell = punkt-i-tid-historik byggs hemma. Detta är dessutom
  bättre för backtests (egna snapshots, inga leverantörsberoenden).

---

## 3. TEST: AQR QMJ Monthly — verklig landstäckning (laddade ned XLSX, 2,26 MB)

- **Verifierat i själva filen** (sharedStrings.xml): `Sweden`, `Denmark`,
  `Finland`, `Norway`, `Europe`, `Global`, `United States`, `Japan`,
  `Australia`, `Canada`, `Developed Markets`. 13 sheets.
- **Del 1-anspråket HÅLLER:** AQR QMJ-faktorer per månad = gratis och täcker
  **alla fyra nordiska länder** + Europa + Global. Perfekt som:
  (a) frisksignal (har vår kvalitetspremie levererat som i studierna?),
  (b) referensgivare i valideringen.

---

## 4. TEST: Bolagsverket — NEDGRADERAS (viktig korrigering)

- Officiella dokument (öppet på webben, citerade i del 2): API-existerar,
  "värdefulla datamängder" **avgiftsfritt utan avtal** (EU-direktiv), OAuth2
  client ID/secret, ESEF/xHTML-årsredovisningar + K2/K3, finansiella
  rapporter + vinstutdelning (v4.7), detaljerad status/avregistration (v4.8).
- **Men LIVE-test från den här maskinen misslyckades**:
  - `api.bolagsverket.se` → **TLS-handskakningsfel** (både PS 5.1 och
    Python/urllib: "SSL: SSLV3_ALERT_HANDSHAKE_FAILURE").
  - bolagsverket.se-webbsidorna → **bot-skydds-CAPTCHA** ("Please enable
    JavaScript", anti-automated spam) vid direkt åtkomst.
- **Slutsats (ärlig):** Bolagsverket är en **dokumenterad, officiell, gratis
  källa — men inte verifierbar från den här miljön just nu.** Orsak kan vara
  kombinationen TLS-ciphers/proxy/bot-skydd — avgörs när man registrerar
  OAuth-klient och kör i webbläsare. **Risknivå: MEDIUM.**
  - **Konsekvens för planen:** yfinance-RAW-bokslut (som just bevisades
    fungera!) blir PRIMÄRKÄLLA för QJM-faktorer; Bolagsverket = uppgradering
    (ESEF-exakthet, vinstutdelning, avregistrering) när åtkomst verifierats.
  - Bolagsverket-status > fallback för avlistning: FI registret +
    Yahoo 404-proben (ZinZino-scenariot) som detektor.

---

## 5. SLUTGILTIG PRIORITERING (uppdaterad efter testerna)

| # | Bygg | Varför nu | Bevisat idag |
|---|---|---|---|
| 1 | **Universums-register + mappning** (FI-emittenter LEI/ISIN → Yahoo-ticker; delisting-detektor) | ZinZino-fallet: utan detta är ALLT annat osäkert | FI-register-data ✅; Yahoo tas bort vid delist ✅ |
| 2 | **Säkerhetsgrind:** blanknings-scraper (HTML ✅), likviditet, solvens | Största skyddsvärdet, verifierad datakälla | FI HTML ✅; yfinance finans ✅ |
| 3 | **QMJ-komposit ur yfinance-RAW-bokslut** + AQR-referens | Evidens x4 studier; datan fungerar | 5/5 tickers ✅; AQR ✅ |
| 4 | **Insider säljkluster-komplettering** (spec 03) | Gratis, evidensbaserat | FI marknadssök (byggd) |
| 5 | (senare) Bolagsverket-ESEF som kvalitetsuppgradering | ESEF-årsdata + vinstutdelning + avregistrering | ⚠️ ej verifierad åtkomst — testa efter registrering |

**Stryks:** PEAD nu, Börsdata nu, Europa nu, "alpha"-påståenden — oförändrat.

---

## 6. SJÄLVKONTROLL: MISSADE JAG NÅGOT VIKTIGT?

Genomgång av hela kedjan mot den nya förståelsen:
- ✅ **Universum/mapping/delisting** — identifierat som #1 (ZinZino).
- ✅ **Sektor** — yfinance sector fungerar men är grov; Bolagsverket SNI-koder
  bättre när åtkomst verifierats; annars yfinance.
- ✅ **Kvartalsdata** — finns i yfinance (t.o.m. kvartalsvis balansräkning!),
  vilket INTE var uppenbart i del 1: PEAD med TS-Överraskelse kan byggas på
  kvartalsvisa annonseringslag + yfinance kvartalsrutor — dock fortfarande
  fråga om annonseringsdatum (av sig själva; dokumentförvärv) → kvar som fas
  3, men billigare än jag trodde.
- ✅ **Corporate actions (splits/uppdelningar)** — yfinance auto_adjust. Bra.
- ✅ **Rights issue-distortion** — marginellt; lägg i "manuell review"-lista
  (familj används ändå manuellt).
- ✅ **Utdelningar/payout** — finns i boksluten (shares outstanding) + yfinance
  dividends. OK.
- ✅ **Valutor (NO/DK/FI-bolag)** — yfinance ger lokala kurser; omvandling
  till SEK för ranking: enkel FX-från yfinance. OK.
- ✅ **Körbarhet** — hela stacken förblir 0 kr.
- **Ingen väsentlig lucka kvar.** Den enda återstående mätosäkerheten är
  Bolagsverket-åtkomst från användarens verkliga miljö (test efter registrering).

---

## Referensnöt (del 3)

- yfinance 1.4.1 lokalt; testscript: C:\Users\hthur\AppData\Local\Temp\opencode\test_yfinance_nordic.py
- AQR QMJ Monthly XLSX: https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Quality-Minus-Junk-Factors-Monthly.xlsx (2,26 MB, verified countries)
- FI blankningsregister: https://www.fi.se/en/our-registers/net-short-positions/ (HTML live 2026-08-28 12:04; Excel = JS-rendered, ej statiskt)
- Bolagsverket: api.bolagsverket.se TLS-handshake-fail + CAPTCHA på web; officiella dokument verifierade via sök/öppet innehåll
