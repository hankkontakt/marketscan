# Datastack-test 2026-08-28 — verifierad fri stack för nordiska small caps

**Metod:** 4 parallella live-tester (yfinance, publika nordiska källor, nyckelberoende källor, nuläge).
Inga konton registrerade, inga API-nycklar skapade, ingen repo-kod ändrad. Allt verifierat mot riktiga endpoints.
**Viktig kontext:** Supabase togs bort från projektet (2026-04±) — alla tester av EXTERNA datakällor är oberoende av det; nulägetolkningen är reviderad nedan.

Underlag: `.opencode/audit/datatest-yfinance.md`, `datatest-publik-norden.md`, `datatest-nyckelberoende.md`, `datatest-nulage.md`.

---

## 1. Verifierad matris (live-testade 2026-08-28)

### ✅ Funka — testade med riktig data

| Källa | Bevis | Ger | Noteringar |
|---|---|---|---|
| **yfinance 1.4.1** | 10/10 nordiska tickers resolverar (SE main, SE First North, NO, DK, FI) | kurser 10y daglig utan hål (>7d); 6mo på 0.2–0.5 s/ticker; `.info` med marketCap/PE/ROE/D-E/FCF/dividend; **kvartalsrapporter färska (Q2-2026)** på 3/4 testade; earnings, dividends, splits (verifierat) | `earningsDate` alltid null → använd `earningsTimestamp` (8/10); `analystCount` null → `numberOfAnalystOpinions` (10/10); banker saknar debtToEquity/FCF; förlustbolag saknar PE/dividend; history saknar Currency-kolumn (info/fast_info konsistent 10/10); prestanda: 300 tickers 6mo ≈ 100 s sekventiellt, 10–15 s med max_workers=12 |
| **FI insynsregister (PDMR)** | 200 rader på 20 sidor live; 81 unika emittenter; handelsdatum 2026-06-18→08-28 | svenska insidertransaktioner, huvudlista **+ First North** | ⚠️ param-bugg i befintlig kod, se §2 |
| **FI blankningsregister** | 338 rader; SBB 15,16 %, Elekta 13,84 % | kortpositioner (SE), LEI→ISIN-uppslag fungerar | ingen bugg |
| **mfn.se** | JSON-feed: 1 440+ artiklar, fulltext gratis, ≥2 månaders djup, artikel-JSON (title/slug/publish_date/html/text/attachments) | svenska pressmeddelanden + rapporter m. datum | ⚠️ inget bolagsfilter i feeden — paginera + filtrera client-side; **befintlig integration trasig**, se §2 |
| **Nasdaq Nordic API** | `api.nasdaq.com/api/nordic/screener/shares` → STO Main **411** + STO First North **332** + HEL 147 + CPH 118 + ICE 27 + OSL 400 | **den riktiga universumkällan** (börslistor inkl. First North, alla nordiska börser) | GET-only (POST → 403 Akamai WAF); ingen CSV-nedladdning — generera från JSON; sök via screener |
| **Avanza (oautentiserad)** | market-guide/stock/5497 → 200 med full JSON (Small Cap Stockholm); price-chart → OHLC 1v/1m/3m/1år, 200 | nyckelfria kurser + bolagsinfo | ⚠️ format ändrat: `timePeriod=one_week` (inte `1_week`) + `resolution=day`; inofficiellt API (ToS-risk); python-avanza kräver TOTP för auth-endpoints; CSV-import finns redan i appen |

### ❌ Fungerar inte / avstå

| Källa | Testresultat | Verdict |
|---|---|---|
| **Börsdata** | 403 Cloudflare (no-key); 401 med syntaktisk nyckel (deterministiskt 3/3); REST kräver **Pro+ 59 €/mån** sedan 2025-02-01; ToS förbjuder externa system som visar API-data | **AVSTÅ** (dyrt + licensstridigt för webbapp) |
| **Finnhub (free)** | 401 utan nyckel; free tier = US-only enligt docs; ingen nordisk symboltäckning (kommenterat redan i universe_mapping.yml) | nyhetssentiment för nordiska small caps vilar på **svag grund** — mät Rank-IC innan det får väga 7,7 % |
| **Oslo Børs NewsWeb** | ALLA endpoints → 200 men SPA-shell (3 715 B HTML); API-host `obns-api.*.euronext.cloud` → DNS-fel | kräver headless-browser (Playwright) — ticket, inte nu |
| **EODHD** | 401 utan nyckel; gratis 20 req/dag; inga First North/Spotlight/NGM i börslistan | behövs inte — yfinance täcker; om något: $19.99 |
| **Alpha Vantage** | demo-nyckel = IBM-only; 25 req/dag; US-centrerad | AVSTÅ |
| **FMP** | 401 utan nyckel; gratis 250/dag; används som fallback i prod-kod | ⚠️ **ingen FMP-nyckel i GH-secrets** — fallback-koden är död idag. Sätt nyckel eller ta bort |

---

## 2. Kodbrister i befintliga integrationer (hittade av testen)

1. **FI-insider param-namn fel** (allvarligast — orsakar tysta dubbletter):
   - `backend_worker/fi_insider_bulk.py` använder `FromDate`/`ToDate`
   - `stock-scanner/core/fi_insider_fetcher.py` använder `FrånDatum`/`TillDatum`
   - FI vill ha `Transaktionsdatum.From`/`Transaktionsdatum.To` — fel namn ignoreras tyst, API:t returnerar alltid "senaste 10".
2. **mfn-integrationen trasig:** `backend_worker/rag/document_fetcher.py` anropar `https://www.mfn.se/api/feed?ticker=X&days=30` → `items: null`. Fungerande mönster: paginera `https://mfn.se/rss?limit=48&offset=N` + filtrera på `subjects[].slug/isin/tickers`, fulltext från `/a/<author>/<slug>`.
3. **Avanza price-chart-format:** `1_week` → 400; korrekt `one_week|one_month|three_months|one_year` + `resolution=day|week`.
4. **yfinance-fält:** `earningsTimestamp` i stället för `earningsDate` (alltid null); `numberOfAnalystOpinions` i stället för `analystCount`.
5. **Nasdaq-migrering:** universe_mapping bör byggas om mot det nya `api.nasdaq.com/api/nordic/screener/shares` (gamla nasdaqomxnordic-listorna gick sönder; Universe Mapping-failar 3/8 senaste).

---

## 3. Rekommenderad fri stack (allt gratis, allt verifierat idag)

| Lager | Källa | Not |
|---|---|---|
| Universum | Nasdaq Nordic screener (STO 411 + FN 332 + OSL 400 + HEL 147 + CPH 118) | daglig, GET-only |
| Kurser | yfinance (6mo daglig, batch-12) | 100 s / 300 tickers sekventiellt |
| Fundamentals | yfinance `.info` + `quarterly_financials` | färska; hål: banker/förlustbolag — kompletteras av mfn-rapporter |
| Insider | FI insynsregister (SE) | efter param-fix |
| Blankning | FI blankningsregister (SE) | funkar idag |
| Press/rapporter | mfn.se JSON-feed | efter fetcher-fix — **ger också rapportdatum = punkt-i-tid-disciplin** |
| Kalender | yfinance `earningsTimestamp` | |
| Portföljkurser | Avanza (keyless OHLC) + befintlig CSV-import | |

**Gaps i fri stack (erkänn dem):**
- Analystestimater/consensus (nordiska small caps) — ingen fri källa.
- Insider + blankning utanför Sverige (NO/DK/FI) — NewsWeb blockad; danska/finska register ej verifierade.
- Punkt-i-tid-*release*-datum från API: lösning = mfn.se publiční datum (SE), resten manuellt.

---

## 4. Nuläges-revidering (Supabase borta → återskapad 2026-08-28)

**Uppdaterat 2026-08-28 eftermiddag:** Supabase återskapades idag (SUPABASE_URL/DATABASE_URL/SUPABASE_*-secrets uppdaterade 08:37 UTC, DEEPSEEK_API_KEY 14:37 UTC). Manuella dispatches körs nu:
- ✅ QMJ Scores (12:53, 13:11, 15:10), Universe Mapping (14:57, 15:49 efter 2 fails), News Pipeline (14:48, 16:07)
- ❌ **FI Insider Bulk 16:43** — `psycopg2.errors.UndefinedColumn: column "price" does not exist` i steget "Calculate insider clusters" (`fi_insider.yml:51` → `backend_worker/insider_cluster.py:51,65`)
- ⏳ Insider Trades (Finnhub), Company Profiles: in_progress vid kontrolltillfället

**Rotorsak FI-felet (verifierat):** kod ⊃ schema. Migrationerna **049** (`insider_trades_isin`) och **052** (`insider_trades_price`) adderar `isin`/`price` — de finns i repot men är inte applicerade på nya instansen. Migration 015 skapade tabellen utan dem; `fi_insider_bulk.py:262` och `insider_cluster.py:51,65` läser/skriver kolumnerna. QMJ/Universe fungerar → majoriteten av migrationer är applicerade; efterhand som kören fortsätter kommer fler saknade migrationer att yppa sig (varje workflow är självdiagnostiserande).

**Åtgärd:** Supabase SQL Editor → kör `049_insider_trades_isin.sql` och därefter `052_insider_trades_price.sql` (den ordningen), kör om FI Insider Bulk. Om `42501` dyker upp först: kör `023_grant_table_privileges.sql`. **OBS innan:** `fi_insider_bulk.py` skickar fel FI-paramnamn (`FromDate`/`ToDate` i stället för `Transaktionsdatum.From/.To` — §2) → bulk-jobbet hämtar tyst bara "senaste 10" med dubbletter även när det funkar. Fixa koden först, applicera sen.

**Övriga bevis (från tidigare):** Weekly Digest 7/10 fail, Smart Alerts 0/10 success (7 skipped), Universe Mapping intermittent — bilan för sparandetiden; `universe_registry` (migr 040) lever däremot igen. Lokala data (`data/fi_raw`, `stock-scanner/data`-parquet) är kvar och användbara. GH-secrets har Fortfarande FMP-nyckel **saknad** (fallback-kod död); mo-jibake i gamla lokala data noterat.

---

## 5. Beslut att fatta (inget annat är byggt på dessa)

1. **Lagring/auth:** (a) Återskapa Supabase free-tier och återanvänd all kod as-is — snabbast, 0 kr, men behåller RLS-komplexiteten; eller (b) byt till enklare lagring (SQLite/Parquet + R2, enkel lösenordsauth) — mindre rörligt, men en riktig migrering. *Rekommendation: (a) först — bara återskapa, allt annat är felsökning som du redan betalat för; (b) är ett optimeringsprojekt för senare.*
2. **Fixa de 5 data-lagerbuggarna** (§2) — små, oberoende av Supabase, och de bevisar att den fria stacken håller. Gör dem nu?
