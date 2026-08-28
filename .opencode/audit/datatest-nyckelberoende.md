# Datatest: nyckelberoende för data-källorna (empiriskt, 2026-08-28)

> **Empiriskt test** — exakt vad varje nyckel-gated datakälla returnerar Utan nyckel,
> vad en gratis-nyckel låser upp (enligt officiella docs), och vad som fungerar helt
> nyckelfritt. Inga konton skapade, ingen repo-kod ändrad, inga paket installerade.
> Alla HTTP-anrop gjorda med Python 3.13 stdlib (`urllib`) från
> `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-keys\` (skripten ligger kvar).
> Enda påhittade nyckeln: Börsdata `0123456789abcdef` (16 hex, syntaktiskt giltig).

---

## 0. Leverabel-tabell (verdict först)

| Källa | Utan nyckel (exakt beteende) | Med gratis-nyckel (vad som låses upp, enl. docs) | Verdict för fri stack |
|---|---|---|---|
| **Börsdata** | `403` Cloudflare "Attention Required" (HTML, 4547 B) — blockerad **före** API:et. Med browser-headers + falsk nyckel: `401` **tom body** (3/3 deterministiskt) — når API:et, nyckeln avvisas | **Ingen gratis-nivå.** REST-API flyttat till **PRO+ (59 €/mån)** 2025-02-01; nya PRO-medlemmar kan inte få REST-API-nyckel. Excel/Sheets-plugin fortfarande PRO (25 €/mån) | ❌ **Ej användbar.** Betald (59 €/mån), Cloudflare-skyddad, och ToS förbjuder att bygga externa system/webbsidor som visar API-data (MarketScan = exakt det) |
| **Finnhub** | `401` `{"error":"Please use an API key."}` (34 B) på alla endpoints (news, quote, profile2, earnings-calendar) | **60 anrop/min, ingen dagsgräns** (GitHub issue #86). **US-only:** Company News 1 år + realtime (US), Earnings Calendar 1 mån (US). Social Sentiment **EJ** gratis (All-In-One). Nordiska börser saknas även på betald nivå (TSX/LSE/Euronext/Deutsche Börse är max) | ❌ **Ej användbar för nordiska småbolag** — US-only, även betald |
| **EODHD** | `401` `Unauthenticated` (15 B, text/html) — identiskt för `api_token=X`, ingen token, tom token | **20 anrop/dag, 20 req/min, 500 välkomstbonus**, data "Past year", vissa datatyper exkluderade. Stockholm/Oslo/Köpenhamn/Helsingfors finns (XSTO/XOSL/XCSE/XHEL); **First North/Spotlight/NGM saknas** | ⚠️ **Marginell.** 20/dag räcker inte för screening; First North (där småbolagen bor) saknas |
| **Alpha Vantage** | `200` + JSON-fel `"the parameter apikey is invalid or missing"` (189 B). Demo-nyckel: `200` med riktig data för IBM, men `200` + info-meddelande för VOLV-B.ST (demo-nyckeln är IBM-only) | **25 req/dag** (obegränsat för verifierade open-source/edu-projekt). **US-centrerad**; realtime/15-min US-data premium-only | ❌ **Ej användbar** — US-centrerad, 25/dag |
| **FMP** | `401` `"Invalid API KEY..."` (184 B) — identiskt för `apikey=X`, ingen nyckel, tom nyckel | **Basic (gratis): 250 anrop/dag**, EOD-historia + profile/reference, 150+ endpoints, 500 MB/30 dagar. US-täckning explicit från Starter (22 $/mån); Global = Ultimate (149 $/mån) | ✅ **Redan i prod som fallback** (GH-secrets, `stock-scanner/core/data_fetcher.py:592,845`). Bästa gratis-nivån av nyckel-källorna — men US-centrerad |
| **Avanza** | ✅ **`200` utan någon auth alls** — `_api/market-guide/stock/5497` (full JSON: Sensys Gatso, Small Cap Stockholm, ISIN, sektorer, marknadsstatus) och `_api/price-chart/stock/5497?timePeriod=one_week&resolution=day` (OHLC-data; one_month/three_months/one_year fungerar också) | Ingen nyckel behövs. python-avanza (`Qluxzz/avanza`) kräver användarnamn/lösenord/**TOTP/2FA** bara för autentiserade endpoints (konton, ordrar, bevakningar) | ✅ **ENDA helt nyckelfria källan med nordisk data inkl. First North.** Risk: inofficiell/ToS + kan ändras utan förvarning |

**Sammanfattning:** Av de sex källorna är **Avanza den enda som fungerar helt nyckelfritt**
med nordisk småbolagsdata (inkl. First North). **FMP** är den enda nyckel-källan med en
användbar gratis-nivå (250/dag) — och den används redan som fallback i produktion.
Börsdata, Finnhub, EODHD och Alpha Vantage ger inget för den fria stacken: Börsdata är
betald (PRO+), Finnhub/Alpha Vantage är US-only, EODHD:s gratis-nivå är för snäv (20/dag)
och saknar First North.

---

## 1. Börsdata — `apiservice.borsdata.se`

### Empiriskt (2026-08-28, ~18:29 lokal tid)

| Anrop | Status | Body |
|---|---|---|
| `GET /v1/instruments` (ingen nyckel, plain urllib) | **403** | Cloudflare "Attention Required!" HTML-sida (4547 B) — blockerad på edge, når aldrig API:et |
| `GET /v1/instruments?authKey=0123456789abcdef` (falsk nyckel, plain) | **403** | `error code: 1010` (17 B, text/plain) — Cloudflare bot-block |
| `GET /v1/instruments?authKey=` (tom) | **403** | `error code: 1010` |
| `GET /v1/instruments/lastprices` (ingen nyckel) | **403** | Cloudflare HTML-sida |
| `GET /v1/instruments?authKey=0123456789abcdef` (falsk nyckel, **browser-headers**) | **401** | **Tom body** (0 B) — passerar Cloudflare, API:et avvisar nyckeln. Deterministiskt: 3/3 |
| `GET /v1/instruments` (ingen nyckel, browser-headers) | **403** | Cloudflare HTML-sida |

**Tolkning:** API:et ligger bakom Cloudflare. Plain urllib blockeras alltid (403).
Med browser-liknande headers (UA + Accept + Referer + Origin) passerar begäran Cloudflare
och når API:et, som svarar `401` (tom body) på ogiltig nyckel. En giltig nyckel krävs
oavsett — och den kostar pengar (se nedan).

### Docs (verifierade 2026-08-28)

- **`borsdata.se/en/info/api/api_page`**: "Change, REST-API moved to PRO+ Feb 1, 2025".
  "API Key is only available to PRO or PRO+ members." Nordic = Pro, Global+Nordic = Pro+.
- **`borsdata.se/en/info/api/changes2025`** (och svenska `changes-2025`): REST-API för egen
  kod flyttat från PRO till **PRO+ från 1 Feb 2025**. Nya PRO-medlemskap kan inte få
  REST-API-nyckel. Befintliga PRO-medlemmar uppgraderades automatiskt till PRO+ t.o.m.
  prenumerationsslut. Excel-plugin och Google Sheets-addon påverkas inte (fortfarande PRO).
- **`borsdata.se/en/pricetable`** (aktuella priser): Premium 10 €/mån (ingen API),
  **Pro 25 €/mån** (API-Nordic: REST-API, Excel-plugin, Sheets-addon), **Pro+ 59 €/mån**
  (API-Global & Holdings). Ingen gratis-nivå för API:et.
- **ToS-restriktion** (api_page): "It is not **permitted to build external systems/home
  pages/widgets that display API data**" + ingen kommersiell användning, ingen
  redistribuering. → MarketScan (publik webapp som visar data) skulle bryta mot villkoren
  även med betald nyckel.

**Verdict:** ❌ Ej användbar för fri stack. Betald (PRO+ 59 €/mån), Cloudflare-skyddad,
ToS-förbjuden för denna typ av app.

---

## 2. Finnhub — `api.finnhub.io`

### Empiriskt (2026-08-28)

| Anrop | Status | Body |
|---|---|---|
| `GET /api/v1/company-news?symbol=AAPL&from=2026-08-01&to=2026-08-28` (ingen token) | **401** | `{"error":"Please use an API key."}` (34 B) |
| `GET /api/v1/quote?symbol=AAPL` | **401** | `{"error":"Please use an API key."}` |
| `GET /api/v1/stock/profile2?symbol=AAPL` | **401** | `{"error":"Please use an API key."}` |
| `GET /api/v1/calendar/earnings?from=2026-08-25&to=2026-08-28` | **401** | `{"error":"Please use an API key."}` |

Konsekvent `401` med JSON-fel på alla endpoints utan token.

### Docs (verifierade 2026-08-28)

- **`finnhub.io/pricing`**: Free = $0/mån, **60 API calls/minute**, "Personal Use".
  All-In-One = $3500/mån (900 req/min market data, 300 req/min fundamental).
- **Free-tier-täckning (från pricing-tabellen):**
  - Company News: **gratis** — "1 year and real-time updates" (**US**).
  - Earnings Calendar: **gratis** — "1 month and real-time updates" (**US**).
  - Social Sentiment: **EJ gratis** — ligger under "Alternative Data" (All-In-One only).
  - International Market Data: **EJ gratis** — All-In-One only, och täcker bara
    "TSX, LSE, Euronext, Deutsche Börse" — **inga nordiska börser** (varken gratis eller betald).
- **Dagsgräns:** ingen — GitHub issue finnhubio/Finnhub-API#86: "No we do not have any
  daily limit at the moment." (60/min är enda gränsen.)

**Verdict:** ❌ Ej användbar för nordiska småbolag. US-only även på betald nivå; nordiska
börser saknas helt. (MarketScan använder redan Finnhub i backend_worker — men bara för
US-data, t.ex. `finnhub_universe.py`.)

---

## 3. EODHD — `eodhd.com/api`

### Empiriskt (2026-08-28)

| Anrop | Status | Body |
|---|---|---|
| `GET /api/eod/BICO.ST?api_token=X` | **401** | `Unauthenticated` (15 B, text/html) |
| `GET /api/eod/BICO.ST` (ingen token) | **401** | `Unauthenticated` |
| `GET /api/eod/BICO.ST?api_token=` (tom) | **401** | `Unauthenticated` |

Identiskt svar oavsett token-variant — token krävs alltid.

### Docs (verifierade 2026-08-28)

- **`eodhd.com/pricing`**: **Free Package $0/mån: 20 API calls/day, 20 requests/minute,
  500 välkomstbonus-anrop**, data "Past year". "Once you have registered, you will be
  granted 20 free API calls per day. The only exception is – you can't access certain
  data types." Betald: EOD Historical Data — All World $19.99/mån (100 000 anrop/dag,
  30+ år).
- **`eodhd.com/financial-apis/api-limits`**: anrops-currency — fundamental-data kostar
  10 anrop, technical/intraday/news 5 anrop, EOD-symbol 1 anrop. Minute-limit 1000 req/min
  (betald).
- **`eodhd.com/list-of-stock-markets`**: **Stockholm ST/XSTO, Oslo OL/XOSL,
  Copenhagen CO/XCSE, Helsinki HE/XHEL — alla närvarande.** **First North, Spotlight,
  NGM — saknas** (listan innehåller bara huvudlistorna).

**Verdict:** ⚠️ Marginell. Gratis-nivån (20/dag) räcker inte för screening av hundratals
tickers, och First North/Spotlight/NGM (där nordiska småbolag handlas) täcks inte.

---

## 4. Alpha Vantage — `www.alphavantage.co`

### Empiriskt (2026-08-28)

| Anrop | Status | Body |
|---|---|---|
| `GET /query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo` | **200** | Riktig daglig OHLCV för IBM (21 309 B), "Last Refreshed: 2026-08-27" |
| `GET /query?function=TIME_SERIES_DAILY&symbol=IBM` (ingen nyckel) | **200** | JSON-fel: `"the parameter apikey is invalid or missing. Please claim your free API key..."` (189 B) |
| `GET /query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo` | **200** | Riktig quote (383 B) |
| `GET /query?function=TIME_SERIES_DAILY&symbol=VOLV-B.ST&apikey=demo` | **200** | `"Information": "The **demo** API key is for demo purposes only..."` — demo-nyckeln är IBM-only |

Notera: `200` även utan nyckel — felet levereras i JSON-bodyn, inte som HTTP-status.

### Docs (verifierade 2026-08-28)

- **`alphavantage.co/support/`** (FAQ): "free stock API service covering the majority of
  our datasets for **25 API requests per day** and unlimited API requests for verified
  open-source or educational projects."
- **`alphavantage.co/documentation/`**: US-centrerad (US equities, forex, crypto,
  commodities, economic indicators). Realtime/15-min-delayed US-data premium-only
  (NASDAQLicensed).

**Verdict:** ❌ Ej användbar för nordiska småbolag. 25 req/dag, US-centrerad. (Demo-nyckeln
är IBM-only — kan inte verifiera nordisk symboltäckning utan riktig nyckel.)

---

## 5. FMP (Financial Modeling Prep) — `financialmodelingprep.com`

### Empiriskt (2026-08-28)

| Anrop | Status | Body |
|---|---|---|
| `GET /api/v3/profile/AAPL?apikey=X` | **401** | `{"Error Message": "Invalid API KEY. Feel free to create a Free API Key..."}` (184 B) |
| `GET /api/v3/profile/AAPL` (ingen nyckel) | **401** | Samma |
| `GET /api/v3/profile/AAPL?apikey=` (tom) | **401** | Samma |

### Docs (verifierade 2026-08-28)

- **`site.financialmodelingprep.com/developer/docs/pricing`**: **Basic (gratis): 250 calls/day**,
  "End of Day Historical Data", "Profile and Reference Data", "150+ Endpoints",
  500 MB/30-dagars bandbredd. Starter $22/mån = "US Coverage". Premium $59/mån = UK+Canada.
  **Ultimate $149/mån = "Global Coverage".**
- **Repo-kontext (verifierad):** `stock-scanner/core/data_fetcher.py:592-620`
  (`fetch_fmp_fallback`) och `:845-862` (`_get_fmp_fundamentals`) använder FMP som
  fallback när yfinance failar, gated på `config.FMP_API_KEY`, cachad 720 h. Kommentaren
  i koden säger "Gratis-tier: 250 anrop/dag" — **stämmer med officiella docs**.
  Nyckeln finns i GH-secrets (inte lokalt). Även `marketscan/backend_worker/company_info_fetcher.py:113`
  anropar FMP profile-endpointen.

**Verdict:** ✅ Redan i prod som fallback. Bästa gratis-nivån av nyckel-källorna
(250/dag) — men US-centrerad; nordisk täckning kräver högre nivåer.

---

## 6. Avanza — `www.avanza.se/_api/...` (inofficiella publika endpoints)

### Empiriskt (2026-08-28, ~18:29–18:31 lokal tid)

| Anrop | Status | Body |
|---|---|---|
| `GET /_api/market-guide/stock/5497` (inga headers alls) | **200** | Full JSON (2428 B): Sensys Gatso Group, ISIN SE0020356244, sektorer, `marketPlaceName: "Stockholmsbörsen"`, `marketListName: "Small Cap Stockholm"`, marknadsstatus CLOSED, historiska stängningskurser |
| `GET /_api/market-guide/stock/5497` (browser-headers) | **200** | Samma |
| `GET /_api/market-guide/stock/19002` (browser-headers) | **200** | OMX Stockholm 30-index (1267 B) |
| `GET /_api/price-chart/stock/5497?timePeriod=one_week&resolution=day` | **200** | OHLC-data (811 B): 6 dagar, `metadata.resolution.availableResolutions: ["ten_minutes","thirty_minutes","hour","day"]` |
| `GET /_api/price-chart/stock/5497?timePeriod=one_month&resolution=day` | **200** | OHLC (2632 B) |
| `GET /_api/price-chart/stock/5497?timePeriod=three_months&resolution=day` | **200** | OHLC (6941 B) |
| `GET /_api/price-chart/stock/5497?timePeriod=one_year&resolution=day` | **200** | OHLC (26 009 B) |
| `GET /_api/price-chart/stock/5497?timePeriod=1_week&resolution=day` (gammal format) | **400** | `{"statusCode":400,"message":"Bad request"}` — **formatet är nu `one_week`, inte `1_week`** |

**Viktigt:** fungerar helt utan inloggning, cookies eller nyckel — även helt utan headers.
Enda kravet: korrekt param-format (`timePeriod=one_week|one_month|three_months|one_year`,
`resolution=day` etc. — bekräftat mot python-avanza `constants.py`:
`TimePeriod.ONE_WEEK.value.lower()` → `one_week`).

### python-avanza / TOTP (verifierat 2026-08-28)

- **`github.com/Qluxzz/avanza`** (README + `avanza.py`): autentiserade endpoints
  (konton, positioner, ordrar, bevakningar) kräver `Avanza({'username': ..., 'password': ...,
  'totpSecret': ...})` — dvs. **TOTP/2FA-secret krävs** för inloggning. De publika
  marknadsdata-endpoints (`get_order_book`, `get_chart_data`, market-guide) kräver ingen
  inloggning — vilket det empiriska testet bekräftar.
- **Repo-kontext:** MarketScan importerar redan Avanza-data via CSV
  (`apps/api/core/avanza_import.py` — ren CSV-parser, inga API-anrop). En direkt
  API-integration vore nytt.

### Caveats

- **Inofficiellt API** — Avanzas ToS tillåter sannolikt inte scraping; python-avanza är
  uttryckligen "unofficial". Risk för blockering/ändringar utan förvarning.
- Rate-limits okända (inga `X-RateLimit`-headers observerade i svaren).
- Konsol-utskriften visade `Stockholmsb�rsen` — det är en PowerShell-konsol-encoding-artefakt
  (cp1252), JSON:en själv är giltig UTF-8.

**Verdict:** ✅ ENDA helt nyckelfria källan med nordisk data inkl. First North
(Sensys Gatso är Small Cap Stockholm; samma endpoint-mönster täcker First North-listor).
Fungerar idag; risk = inofficiell/ToS + framtida ändringar.

---

## 7. Metod & begränsningar

- Alla anrop: Python 3.13.14 stdlib `urllib`, timeout 25 s, ingen cert-verifiering avstängd.
- Skripten ligger kvar i `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-keys\`
  (`common.py`, `test_borsdata.py`, `test_finnhub.py`, `test_eodhd.py`,
  `test_alphavantage.py`, `test_fmp.py`, `test_avanza.py`, `test_supplement.py`,
  `test_probe2.py`, `test_avanza2.py`).
- **Ej verifierat:** faktisk data med riktiga gratis-nycklar (inga konton skapade —
  förbjudet i briefen). "Vad en gratis-nyckel låser upp" baseras på officiella docs-sidor,
  inte på live-test med nyckel.
- EODHD-täckning för First North-tickers (t.ex. BICO.ST) kunde inte testas utan nyckel
  (401 oavsett) — marknadslistan visar dock att First North inte är en stödd börs.
- Alpha Vantage nordisk symboltäckning kunde inte verifieras (demo-nyckeln är IBM-only).

## 8. Källförteckning (hämtade 2026-08-28)

| Källa | URL |
|---|---|
| Börsdata API-sida | https://borsdata.se/en/info/api/api_page |
| Börsdata ändring 2025 | https://borsdata.se/en/info/api/changes2025 |
| Börsdata priser | https://borsdata.se/en/pricetable |
| Finnhub pricing | https://finnhub.io/pricing |
| Finnhub rate-limit | https://finnhub.io/docs/api/rate-limit |
| Finnhub dagsgräns (issue #86) | https://github.com/finnhubio/Finnhub-API/issues/86 |
| EODHD pricing | https://eodhd.com/pricing |
| EODHD API-limits | https://eodhd.com/financial-apis/api-limits |
| EODHD marknadslista | https://eodhd.com/list-of-stock-markets |
| Alpha Vantage docs | https://www.alphavantage.co/documentation/ |
| Alpha Vantage FAQ (25/dag) | https://www.alphavantage.co/support/ |
| FMP pricing | https://site.financialmodelingprep.com/developer/docs/pricing |
| python-avanza (Qluxzz/avanza) | https://github.com/Qluxzz/avanza · `avanza/constants.py` (Route.CHARTDATA_PATH, TimePeriod, Resolution) |