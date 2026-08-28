# Datatest: Publika nordiska datakällor (gratis, ingen API-nyckel)

> **Datum:** 2026-08-28 · **Typ:** empiriskt test — skript körda live mot källorna
> **Syfte:** utvärdera om FI-insyn, FI-blankning, mfn.se, Oslo Børs NewsWeb och
> Nasdaq Nordic går att scripta in i MarketScan-pipelinen utan API-nyckel.
> **Skript:** `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-pub\` (utanför repot)
> **Inga kodändringar i repot.** Inga konton skapade. Endast stdlib + requests.

---

## 1. FI insynsregister (PDMR) — marknadssok.fi.se

| Aspekt | Resultat |
|---|---|
| URL | `https://marknadssok.fi.se/publiceringsklient/sv/Search` |
| Metod | GET, HTML-tabell (JSON finns INTE — `format=json` + XHR-headers returnerar ändå HTML) |
| Status | 200 |
| Korrekta params | `SearchFunctionType=Insyn`, `Transaktionsdatum.From`, `Transaktionsdatum.To`, `Page`, `PageNumber` (hämtade från sökformulärets fältnamn) |
| Poster | 200 rader (20 sidor × 10) i 7-dagarsfönster; 81 unika emittenter |
| Datumtäckning | Publiceringsdatum 2026-08-27..28; transaktionsdatum 2026-06-18..2026-08-28 (inkluderar senanmälda trades) |
| Fält | Publiceringsdatum, Emittent, Person i ledande ställning, Befattning, Närstående, Karaktär, Instrumentnamn, Instrumenttyp, ISIN, Transaktionsdatum, Volym, Volymsenhet, Pris, Valuta, Status, Detaljer |
| Bolag/börser | Både huvudlistan (Tele2, ASSA ABLOY, Loomis) och First North (BONESUPPORT, Precise Biometrics, BrainCool, OncoZenge, Medclair, Saniona, Hunter Capital RTO 1). ISIN-prefix: enbart SE (svenska bolag) |
| Rate limit | **Anslutningen nollställs efter ~7–8 snabba anrop.** Med `requests.Session` + 2,5 s delay + backoff klarades 20 sidor (2 resets, återhämtade) |
| Verdict | **Scriptbar.** Kräver session + långsamma delays. |

**⚠️ Befintlig kod bugg:** `backend_worker/fi_insider_bulk.py` använder params `FromDate`/`ToDate` — dessa IGNORERAS av FI (rätt namn är `Transaktionsdatum.From`/`To`). Sökningen faller då tyst tillbaka till "senaste 10" och pagineringen ger dubbletter av samma fönster. `core/fi_insider_fetcher.py` (stock-scanner) använder `FrånDatum`/`TillDatum` — samma problem. Båda behöver uppdateras till de korrekta fältnamnen.

## 2. FI blankningsregister (net short positions) — fi.se

| Aspekt | Resultat |
|---|---|
| URL | `https://www.fi.se/en/our-registers/net-short-positions/` |
| Metod | GET, HTML-tabell (Excel/CSV-länkar är JS-renderade — finns inte i HTML:en) |
| Status | 200 |
| Poster | **338 rader** |
| Datumtäckning | `latest_position_date` 2019-12-19..2026-08-27 (varje emittents senaste positionsdatum; 57 rader med datum 2026-08-27 = igår) |
| Fält | `issuer_name`, `lei`, `latest_position_date`, `total_short_pct` |
| Topp | SBB 15,16 %, Elekta 13,84 %, JM 10,74 %, BONESUPPORT 10,51 %, Hemnet 10,30 % |
| LEI→ISIN | Detaljsidan `.../emittent?id=<LEI>` fungerar (verifierat: Dynavox LEI → SE0017105620) |
| Verdict | **Scriptbar och tillförlitlig.** Befintlig kod (`fi_short_positions.py`) fungerar som den är. |

## 3. mfn.se — pressmeddelanden

| Aspekt | Resultat |
|---|---|
| URL | `https://www.mfn.se/rss` (hela sajten är ett JSON Feed API — även `/sv/`, `/api/feed` etc. returnerar feed) |
| Metod | GET, JSON Feed v1 (`application/json`) |
| Status | 200 |
| Poster | 48 items/sida, paginerat via `next_url`; feeden går ≥2 månader bakåt (offset 5000 → 2026-06-30) |
| Fält per item | `news_id`, `group_id`, `url`, `author` (slug/name), `subjects` (bolag: slug, name, **ISINs, LEIs, tickers** t.ex. `XSTO:IRLAB A`), `properties` (lang, tags, type, scopes), `content` (title, slug, publish_date, **html, text**, attachments) |
| Inloggning | Ingen krävs. Artikel-URL (`https://mfn.se/a/<author>/<slug>`) returnerar fulltext (content.html + content.text) |
| Bolagsfilter | **INGET fungerande filterparam.** `ticker=`, `subject=`, `company=`, `slug=`, `isin=` → alla returnerar `items: null/0`. Måste paginera hela feeden och filtrera client-side på subject-slug/ISIN/ticker |
| Rate limit | Ingen observerad (många snabba anrop OK) |
| Verdict | **Scriptbar** (pagineringsloop + client-side-filter). |

**⚠️ Befintlig kod bugg:** `backend_worker/rag/document_fetcher.py` anropar `https://www.mfn.se/api/feed?ticker=X&days=30` — returnerar `items: null` (parametern finns inte). MFN-integrationen i RAG:n är trasig och hämtar aldrig något.

## 4. Oslo Børs NewsWeb — newsweb.oslobors.no

| Aspekt | Resultat |
|---|---|
| URL | `https://newsweb.oslobors.no/` |
| Metod | React SPA — **alla** paths (inkl. `/messages/search`, `/v1/newsreader/env`, `/obsvc/...`) returnerar samma 3 715-byte HTML-shell (index.html). Ingen server-side rendering |
| API | JS-bundlen avslöjar `/obsvc/`-prefix + `/v1/newsreader/{env,message,announcement,issuers,search}` och dev-host `obns-api.dev.euronext.cloud`. **Produktions-host `obns-api.euronext.cloud` resolverar INTE från denna maskin (DNS-fel)** |
| webfetch | Returnerar bara "NewsWeb" (renderar inte JS) |
| Verdict | **EJ scriptbar via vanlig HTTP från denna maskin.** Kräver headless-browser (JS-exekvering) eller åtkomst till den interna API-hosten. Manuell/headless-browser endast. |

## 5. Nasdaq Nordic — listade bolag + index

| Aspekt | Resultat |
|---|---|
| Gammal sajt | `nasdaqomxnordic.com/shares/listed-companies/*` → redirect till `nasdaq.com/european-market-activity/shares` (migrerad). `?download=1`-endpoints döda |
| Ny API | `https://api.nasdaq.com/api/nordic/screener/shares?lang=en&market=STO&category=MAIN_MARKET` |
| Market-koder | `STO` (Stockholm), `HEL` (Helsingfors), `CPH` (Köpenhamn), `ICE` (Island). `OSL` finns INTE (Oslo Børs är separat) |
| Category | `MAIN_MARKET`, `FIRST_NORTH` (OTHERS → 400) |
| **Stockholm Main Market** | **411 rader** (pagination.total=411, komplett) |
| **Stockholm First North** | **332 rader** |
| Övriga | HEL Main 147, CPH Main 118, ICE Main 27 |
| Kolumner (visade) | fullName, currency, lastSalePrice, netChange, percentageChange, bidPrice, askPrice, volume, turnover, greenEquityDesignation, sector |
| Radfält (rikare) | symbol, isin, orderbookId, assetClass, exchangeSymbol, high, low, reportedVolume, tradesCount, lastTraded, time m.fl. |
| CSV-download | Ingen server-side CSV (`/screener/shares/download` → 404). CSV genereras client-side från JSON |
| Indexkonstituenter | **Inte lätt nåbara.** `indexes.nasdaqomx.com/Index/Weighting/OMX_Stockholm_Small_Cap` → redirect till root; index-API-endpoints 404/400. Helsingfors/Köpenhamn-motsvarigheter finns på samma screener (market=HEL/CPH) |
| Rate limit | Ingen observerad. **POST blockeras av WAF (403 Akamai) — använd bara GET** |
| Verdict | **Scriptbar** (GET-only JSON). |

## 6. Sammanfattning per källa

| Källa | Scriptbar i pipeline? | Tillförlitlighet | Rate limit / hinder |
|---|---|---|---|
| FI insyn (PDMR) | ✅ Ja (HTML-scrape, session + delays) | Hög — officiellt register, publiceras inom 3 dagar | Anslutningsreset efter ~7–8 snabba anrop; 2,5 s delay krävs |
| FI blankning | ✅ Ja (HTML-scrape) | Hög — officiellt register, realtid | Ingen observerad; 1,2 s delay i befintlig kod |
| mfn.se | ✅ Ja (JSON Feed, paginera + client-side-filter) | Hög — fulltext utan login | Ingen observerad |
| Oslo Børs NewsWeb | ❌ Nej via vanlig HTTP (SPA + onåbar API-host) | — | Kräver headless-browser eller intern API-host |
| Nasdaq Nordic | ✅ Ja (JSON API, GET-only) | Hög — officiell lista | POST → 403 WAF; GET obegränsat |

**Rekommendation:** FI-insyn, FI-blankning, mfn.se och Nasdaq Nordic är alla värda att scripta in. NewsWeb kräver headless-browser (t.ex. Playwright) om norsk börsdata behövs. Två befintliga kodbuggar hittades: fel param-namn i `fi_insider_bulk.py`/`fi_insider_fetcher.py` och trasig MFN-URL i `document_fetcher.py`.

---

## Bilaga: exakta anrop som verifierats

```bash
# FI insyn (7 dagar, sida 1)
GET https://marknadssok.fi.se/publiceringsklient/sv/Search?SearchFunctionType=Insyn&Transaktionsdatum.From=2026-08-21&Transaktionsdatum.To=2026-08-28&Page=1&PageNumber=1
# → 200, 10 rader/sida, 200 rader totalt (20 sidor)

# FI blankning
GET https://www.fi.se/en/our-registers/net-short-positions/
# → 200, 338 rader

# mfn.se feed
GET https://mfn.se/rss?limit=48&offset=0
# → 200, JSON Feed, 48 items, next_url-paginering

# Nasdaq Stockholm Main Market
GET https://api.nasdaq.com/api/nordic/screener/shares?lang=en&market=STO&category=MAIN_MARKET
# → 200, 411 rader (pagination.total=411)

# Nasdaq Stockholm First North
GET https://api.nasdaq.com/api/nordic/screener/shares?lang=en&market=STO&category=FIRST_NORTH
# → 200, 332 rader
```

Provdata sparad i `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-pub\samples\`
(`fi_insider_sample.json`, `fi_shorts_sample.json`, `mfn_feed_sample.json`, `nasdaq_sto_main_sample.json`).