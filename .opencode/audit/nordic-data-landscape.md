# Nordic Data Landscape — kartläggning för MarketScan (privat, låg budget)

> **Datum:** 2026-08-28 · **Typ:** webbresearch, inga kodändringar
> **Syfte:** hitta realistisk datastack för nordiska small caps (Sverige/Norge/Danmark/Finland)
> för ett privat aktieanalysverktyg med databudget < ~50 EUR/mån (gärna gratis).
> Alla priser verifierade mot faktiska prissidor där det anges; se källförteckning.

---

## 1. Verdict (kort)

**Primär källa: Börsdata Pro+ (59 EUR/mån ≈ 610 SEK/mån).** Det är den enda källan som
i ett enda REST-API ger nordisk small-cap-täckning (1 700+ bolag inkl. First North,
Spotlight, NGM), EOD-kurser med 20 års historik, rapportdata (års-/kvartals-/R12),
~300 nyckeltal, 2 000+ screener-värden, rapport- och utdelningskalender **samt**
insider-, blanknings- och återköpsdata. Priset ligger ~18 % över 50 EUR-målet, men
det finns **ingen bra mellannivå**: sedan 1 feb 2025 kräver REST-API:et Pro+ (Pro-nivån
har bara Excel/Sheets-plugin, inget REST-API för egen kod).

**Gratis-komplement (rekommenderas oavsett):**
- **Finansinspektionens PDMR-register** (marknadssok.fi.se) — insynshandel, sökbart, ingen API → scrape.
- **Oslo Børs NewsWeb** (newsweb.oslobors.no) — norska insider-/börsmeddelanden, sökbart.
- **mfn.se** — pressmeddelanden för nordiska bolag, gratis att bläddra (ingen publik API → scrape/RSS).
- **Avanza CSV-export** — egen portfölj/transaktioner, manuell export.
- **yfinance** — kvar som fallback för kurser, men med kända kvalitetsproblem (se §5).

**Om budgeten absolut måste hållas under 50 EUR:** enda rimliga alternativ är att stanna
på gratis-stacken (yfinance + Finnhub free + manuell/scrapad FI/mfn-data) och acceptera
sämre fundamentals och ingen insider/blankningsdata. EODHD ($19.99/mån) kan vara ett
pris-komplement för kurshistorik, men täcker inte First North/Spotlight (ej verifierat)
och har **inte** fundamentals i den billiga planen.

**Undvik som primär källa:** Alpha Vantage (25 req/dag gratis, fundamentals bara USA),
Tiingo/Polygon (USA-fokus), Nasdaq feeds (B2B, dyr), Millistream (B2B, ingen publik
prislista), Cision (B2B, dyr), Nordnet API (tar inte in nya kunder).

---

## 2. Datakällorna — detaljerat

### 2.1 Börsdata (borsdata.se) — ⭐ rekommenderad primär

| Aspekt | Fakta (verifierat) |
|---|---|
| Pris | Premium 10 EUR/mån · Pro 25 EUR/mån · **Pro+ 59 EUR/mån** (SEK: 99/249/599 kr). Gratis medlemskap finns (begränsad webbdata). |
| Täckning | "Alla bolag för Norden, över 1 700 bolag" — Nasdaq Stockholm, First North, Spotlight, NGM, Oslo, Helsingfors, Köpenhamn (bolagsantalet 1 700+ implicerar alternativa listor; ej explicit bekräftat per lista i källorna). |
| Kurshistorik | Endast EOD (ingen intraday), upp till 20 år. Uppdateras ~20:00 UTC. |
| Fundamentals | Rapportdata (års-/kvartals-/R12, max 20 rapporter), ~300 nyckeltal med historik, 2 000+ screener-värden, rapportkalender, utdelningskalender. |
| Insider/blankning | **Pro+:** Holdings Insider, Holdings Shorts, Holdings Buyback, Governance. |
| API | REST (JSON), `apiservice.borsdata.se`, officiella klienter (C#, Python, PHP, Java, JS). Rate limit: 100 anrop/10 s (429 + Retry-After), håll <10 000 anrop/24 h. |
| **KRITISKT** | **REST-API flyttat till Pro+ från 1 feb 2025.** Nya Pro-medlemmar kan inte få REST-API-nyckel; Excel-plugin och Google Sheets fungerar fortfarande på Pro. API-nyckel kan bara sökas av Pro-medlem i nordiskt land. |
| Licens | Endast privatpersoner, egen analys. Förbjudet: kommersiellt bruk, vidaredistribution, "bygga externa system/hemsidor/widgets som visar API-data". ⚠️ Gråzon för en privat webbapp — egen analys är tillåten, men formuleringen om externa system bör läsas noga. |

**Källor:** borsdata.se/en/pricetable (hämtad), borsdata.se/en/info/api/api_page (hämtad),
borsdata.se/info/api/changes-2025 (sökresultat), github.com/Borsdata-Sweden/API/wiki (hämtad).

### 2.2 EODHD (eodhd.com) — prisvärd sekundär för kurshistorik

| Aspekt | Fakta (verifierat) |
|---|---|
| Pris | Gratis: 20 anrop/dag, bara senaste året. **EOD All World $19.99/mån** ($199/år): EOD + splits/dividends, 100 000 anrop/dag, 1 000/min. **All-in-One $99.99/mån** (+ fundamentals, kalendrar, technicals, screener, WebSocket). **Fundamentals Data Feed $59.99/mån.** |
| Täckning | 150 000+ tickers, 70+ börser. Nordiska huvudbörser: Stockholm (XSTO), Köpenhamn (XCSE), Oslo (XOSL), Helsingfors (XHEL). **First North/Spotlight/NGM finns INTE i börslistan** — täckning av alternativa listor ej verifierad, sannolikt svag. |
| Historik | USA från 1985, icke-USA från 2000, "minor companies" bara senaste 6 åren. |
| Fundamentals | **Ingår INTE i $19.99-planen** — kräver All-in-One eller Fundamentals Feed. |
| Live | 15 min fördröjd live-data finns som tillägg. |

**Källor:** eodhd.com/pricing (hämtad), eodhd.com/list-of-stock-markets (hämtad), tradingdatacompare.com/providers/eod-historical-data/ (sökresultat).

### 2.3 Finnhub (finnhub.io) — redan i stacken, svag för nordiska small caps

| Aspekt | Fakta (verifierat) |
|---|---|
| Pris | Gratis: 60 anrop/min, realtidskurser USA + globala quotes, **fundamentals bara USA**. Betald: All-in-One $3 500/mån (institutionell); fundamentals säljs per marknad ("1 market per subscription", pris ej publicerat på sidan). |
| Norden | Internationella marknader: endast EOD-data. Nordisk fundamentals kräver betald per-marknads-prenumeration. |
| Bedömning | Behåll för nyheter/sentiment på gratis-nivån; lita inte på den för nordiska fundamentals. |

**Källor:** finnhub.io/pricing (sökresultat), finnhub.io/pricing-fundamental-data (sökresultat), finnhub.io (sökresultat).

### 2.4 Alpha Vantage (alphavantage.co) — ej lämplig som primär

- Gratis: **25 anrop/dag, 5/min** (sänkt från 500 → 100 → 25). Betald från $49.99/mån (realtids-USA från $99.99).
- Global EOD finns (TIME_SERIES_DAILY), men **fundamentals bara för USA**; nordisk small-cap-täckning fläckvis.
- **Källor:** alphavantage.co/support (sökresultat), macroption.com/alpha-vantage-api-limits (sökresultat), tradingtoolshub.com/review/alpha-vantage (sökresultat).

### 2.5 Tiingo (tiingo.com) — USA-fokus

- EOD + IEX-intraday + nyheter; "U.S. and Global Stocks" marknadsförs men global täckning är tunn.
- Ej lämplig för nordiska small caps. **Källa:** tiingo.com, tiingo.com/products/stock-api (sökresultat).

### 2.6 Polygon.io — USA-fokus

- Stark på USA-aktier + krypto; europeisk täckning begränsad (artikel: "Does Polygon.io Offer European Stock Data?" — begränsad).
- Ej lämplig för nordiska small caps. **Källa:** trading-strategies.academy/archives/47180 (sökresultat).

### 2.7 Nasdaq Nordic feeds — B2B, för dyr

- Direktfeeds kräver börsavtal/distributörslicenser; referens: US-filtered feeds har $500/mån distributörsavgift. Europeiska prislistor finns på nasdaq.com/solutions/data/european-pricing-policies men är B2B.
- Ej aktuellt för hobbybudget. **Källor:** nasdaq.com/products/data/market-data-feeds, nasdaqtrader.com (sökresultat).

### 2.8 Avanza — inofficiell API + CSV-export

- **Inofficiell API:** flera Python-bibliotek (python-avanza, Qluxzz/avanza, avanza-api, avanzapy, avanza-mcp). Alla varnar: odokumenterad, kan brytas när som helst, kan bryta mot Avanzas villkor, risk för blockering/rate-limit.
- **CSV-export:** manuell export av innehav/transaktioner till Excel/CSV under Analys → "Exportera data till Excel" (bekräftat via användarforum).
- **Avanza-screener:** gratis, grundläggande faktorer (P/E, direktavkastning, börsvärde m.m.).
- **Källor:** github.com/North14/avanza, pypi.org/project/python-avanza, github.com/Advance-xd/avanza-mcp, rikatillsammans.se/forum (sökresultat).

### 2.9 Nordnet — officiell API men stängd för nya kunder

- Nordnet API (nExt API v2) finns och är officiell (trading + marknadsdata-abonnemang), men sidan säger uttryckligen: **"Nordnet API is currently not onboarding new customers."**
- **Källa:** nordnet.se/externalapi/docs/getting_started (hämtad).

### 2.10 Millistream — B2B, ingen publik prislista

- Nordisk marknadsdataleverantör (realtid + historik, feeds, widgets, "Millistream Trader"). Ingen självbetjäningsprislista — "kontakta oss". B2B-kunder (t.ex. SAVR).
- Ej aktuellt för hobbybudget. **Källor:** millistream.com, millistreamtrader.com (sökresultat).

### 2.11 mfn.se / Cision — pressmeddelanden

- **MFN (Modular Finance):** distributionsplattform för nordiska noterade bolags pressmeddelanden/regulatoriska nyheter. mfn.se är gratis att bläddra; ingen publik API (scrape/RSS). Börsdata integrerar MFN-nyheter.
- **Cision:** B2B, dyr. Ej aktuellt.
- **Källor:** mfn.se, modularfinance.com/mfn (sökresultat).

### 2.12 Finansinspektionen PDMR (insynshandel) — gratis men utan API

- **Sverige:** FI:s publika PDMR-register (marknadssok.fi.se/publiceringsklient) — sökbart, publiceras direkt efter anmälan. Ingen API/CSV-export → scrape.
- **Norge:** Oslo Børs NewsWeb (newsweb.oslobors.no) — insider-/börsmeddelanden som publika annonser.
- **Danmark:** Finanstilsynets OAM-portal — men enligt portalen är **storaktieägares och ledande medarbetares indberetninger INTE offentligt tillgängliga** i OAM.
- **Finland:** ej verifierat i denna research (Euroclear Finlands insiderregister nämns i branschen).
- **Slutsats:** PDMR-data är fragmenterad per land, manuell/scrapad — ingen enhetlig gratis API.
- **Källor:** fi.se/en/our-registers/pdmr-transactions, portal.finanstilsynet.dk, newsweb.oslobors.no (sökresultat).

---

## 3. Rekommenderad stack för MarketScan

| Lager | Källa | Kostnad | Kommentar |
|---|---|---|---|
| **Primär: kurser + fundamentals + nyckeltal + screener** | **Börsdata Pro+** | 59 EUR/mån | 1 700+ nordiska bolag, 20 års EOD, ~300 KPI:er, rapport-/utdelningskalender |
| **Insider + blankning + återköp** | Börsdata Pro+ (Holdings) | ingår | Enda källan som ger allt i ett API |
| Pressmeddelanden | mfn.se (scrape) | gratis | Komplement; Börsdata har redan MFN-nyheter |
| PDMR/insyn (Sverige) | FI-registret (scrape) | gratis | Korsvalidering mot Börsdata insider |
| PDMR (Norge) | Oslo Børs NewsWeb (scrape) | gratis | |
| Egen portfölj | Avanza CSV-export | gratis | Manuell, vid behov |
| Kursfallback | yfinance | gratis | Kända kvalitetsproblem — använd bara som fallback |
| Nyheter/sentiment | Finnhub free | gratis | Behåll nuvarande integration |
| **Valfri sekundär kurshistorik** | EODHD All World | $19.99/mån | Korsvalidering + delisted-data; verifiera First North-täckning med demo-nyckel först |

**Budget:** 59 EUR/mån (Börsdata) + 0 = **~59 EUR/mån** — ~18 % över målet men enda
fungerande helhetslösning. Strikt <50 EUR-alternativ: gratis-stacken (yfinance + Finnhub
free + FI/mfn-scraping), med sämre fundamentals och ingen insider/blankning.

**Motivering:** Börsdata är byggt för nordiska småbolag (inkl. First North/Spotlight/NGM),
har nordisk språk- och rapporteringskontext, och kombinerar kurser + fundamentals +
insider + blankning i ett API med generösa rate limits (100 anrop/10 s, 10K/dag) — perfekt
för en daglig pipeline. EODHD är bästa sekundära pris-källa men saknar alternativa listor
och fundamentals i billigaste planen. Alpha Vantage/Tiingo/Polygon är USA-centrerade.
Nasdaq feeds/Millistream/Cision är B2B-prissatta långt över budget.

---

## 4. Nordiska screeners/rankningsverktyg

| Verktyg | Faktorer | Saknas/begränsningar |
|---|---|---|
| **Börsdata Screener** | 2 000+ screener-värden, strategier, teknisk analys, rapportdata | Kräver Pro/Pro+ för full data; ingen intraday |
| **Avanza Aktiescreener** | Grundläggande: P/E, direktavkastning, börsvärde, sektor | Få faktorer, ingen djup historik |
| **Indicatum** | Rankar på Kvalitet, Hälsa, Lönsamhet, Värdering, Kassaflöde, Tillväxt (3 tidsperspektiv) + teknisk (SMA, RSI, Bollinger); email-utskick; har First North-screener | Gratis-nivån: 6 kolumner, 1 sparat filter; Premium 149 kr/mån, Premium Plus 249 kr/mån, Pro 349 kr/mån |
| **NordPicks** | Gratis nordisk screener (2 728 aktier), fundamental + teknisk, AI-veckoanalys | Täckning/djup ej verifierat |
| **Nordscreen** | Gratis nordisk screener: P/E, RSI, MACD m.fl. | Grundläggande |
| **MarketScreener** | Global screener, fundamental + teknisk | Globalt fokus, nordisk small-cap-täckning svag |
| **DNB Carnegie småbolagsguide** | Screener av ~480 nordiska småbolag (professionell research) | Betald/kommissionerad research, ej API |
| **Raknerud** | ⚠️ **Kunde inte verifieras** — sajten svarade inte (transport error vid två försök) | — |

**Källa:** borsdata.se/info/screener/om-screener, indicatum.se, nordpicks.com/sv/screener,
nordscreen.se, avanza.se/aktier/hitta.html, placera.se (DNB Carnegie-podden, 2026-02-02).

---

## 5. Gotchas för nordiska small caps

1. **Likviditet/spread:** småbolag har tunna orderböcker och vida spreads; daglig volym är
   ofta låg och kursrörelser sker i kluster. EOD-data räcker för analys men var medveten om
   att "senaste kurs" kan vara gammal. (Allmän branschkunskap; ScreenerHero pekar på att
   200+ First North-bolag under 500 MEUR täcks dåligt av globala screeners.)
2. **Valutor:** SEK/NOK/DKK/EUR — jämförelser över länderna kräver FX-normalisering.
   Börsdata levererar per-bolag-valuta; EODHD har forex-data. Räkna om till en basvaluta i pipelinen.
3. **Gles analytikertäckning:** de flesta nordiska småbolag har ingen eller få analytiker;
   estimat saknas ofta. Börsdata har "Estimates" (egna/Börsdata/S&P) på högre nivåer, men
   för småbolag är estimatdata gles. DNB Carnegie screenar ~480 bolag — en bråkdel av marknaden.
4. **Indexeffekter:** OMX Stockholm Small Cap = bolag med börsvärde < 150 MEUR (Nasdaq-definition).
   Indexombalanseringar (in/ut ur Small Cap/Mid Cap) ger flöden som påverkar kursen kortsiktigt.
   First North-bolag ingår inte i huvudindexen — mindre indexflöde men också mindre synlighet.
5. **Nyemissioner/teckningsrätter:** vanligt i småbolag; utspädning och teckningsrättshandel
   påverkar både kurs och ägarandel. Kräver korrekt corporate-actions-data (Börsdata har
   stock splits; EODHD har splits/dividends). yfinance har kända problem med split-justeringar.
6. **Datakvalitet i gratis-källorna:** yfinance/Yahoo har dokumenterade fel — 100×-valutafel,
   dåliga split-justeringar, dubbelräknade utdelningar, saknade värden (go-yfinance "repair"
   existerar just för detta). First North/Spotlight tickers saknas eller är felaktiga hos
   många globala leverantörer.

**Källor:** indexes.nasdaqomx.com (Small Cap <150 MEUR), github.com/ranaroussi/yfinance
(discussions/2183), wnjoon.github.io/go-yfinance (repair-dokumentation), screenerhero.com
(First North-taggsida), aktieportfolj.se/nyemission, seb.se (nyemission/teckningsrätter).

---

## 6. Källförteckning (hämtade/verifierade)

**Hämtade direkt (fetch):**
- https://borsdata.se/en/pricetable — pristabell (Premium 10€ / Pro 25€ / Pro+ 59€)
- https://borsdata.se/en/info/api/api_page — REST-API → Pro+ (1 feb 2025), licensvillkor
- https://github.com/Borsdata-Sweden/API/wiki — API-data, rate limits (100/10 s, 10K/dag), EOD-only
- https://eodhd.com/pricing — planer: Free 20/dag, All World $19.99, All-in-One $99.99, Fundamentals $59.99
- https://eodhd.com/list-of-stock-markets — ST/CO/OL/HE finns; First North/Spotlight/NGM saknas i listan
- https://www.nordnet.se/externalapi/docs/getting_started — "currently not onboarding new customers"
- https://www.placera.se/externa-analyser/analyspodden-avsnitt-357-... — DNB Carnegie, ~480 nordiska småbolag screenade

**Sökresultat (ej djup-hämtade, markerade som sådana i texten):**
- borsdata.se/info/api/changes-2025 (REST → Pro+), borsdata.se (1 700+ bolag, 99/249/599 kr)
- finnhub.io/pricing + /pricing-fundamental-data (free = US fundamentals; per-market global)
- alphavantage.co/support (25 req/dag), macroption.com (limit-historik)
- tiingo.com, trading-strategies.academy (Polygon Europa begränsat)
- nasdaq.com/products/data/market-data-feeds, nasdaqtrader.com (feed-priser B2B)
- github.com/North14/avanza, pypi.org/project/python-avanza, github.com/Advance-xd/avanza-mcp (inofficiell Avanza-API)
- rikatillsammans.se/forum (Avanza CSV-export), mintradingjournal.com (Avanza CSV-guide)
- millistream.com, millistreamtrader.com (B2B, ingen prislista)
- mfn.se, modularfinance.com/mfn (pressmeddelandeplattform)
- fi.se/en/our-registers/pdmr-transactions, portal.finanstilsynet.dk (DK: insider ej offentligt i OAM), newsweb.oslobors.no
- indicatum.se (screeners + priser 149/249/349 kr), nordpicks.com/sv/screener, nordscreen.se, avanza.se/aktier/hitta.html
- indexes.nasdaqomx.com (Small Cap <150 MEUR), github.com/ranaroussi/yfinance, wnjoon.github.io/go-yfinance
- screenerhero.com/blog/tag/first-north (200+ First North-bolag täcks dåligt av globala screeners)
- aktieportfolj.se/nyemission, seb.se (teckningsrätter/utspädning)

**Ej verifierbart:** Raknerud (sajten svarade inte), EODHD:s First North-täckning (finns ej i
börslistan — testa med demo-nyckel), finskt insiderregister (ej undersökt).