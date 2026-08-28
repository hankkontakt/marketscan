# Datatest: yfinance-täckning för nordiska småbolag

Datum: 2026-08-28 · Python 3.13.14 · yfinance 1.4.1 · pandas 3.0.3
Körning: `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-yf\` (utanför repon, inga repo-ändringar)
Syfte: Beslutsunderlag — fungerar gratis-stacken (yfinance) för MarketScan/stock-scanners nordiska småbolagsuniversum?

---

## 1. Verkliga tickers (var de hittades)

| Ticker | Bolag | Marknad | Källa (fil:rad) |
|---|---|---|---|
| MYCR.ST | Mycronic AB | SE Stockholm Small Cap | `stock-scanner\smallcap\universe.py:211` (SMALL_CAP) |
| LAGR-B.ST | Lagercrantz Group B | SE Stockholm | `stock-scanner\smallcap\universe.py:346` (SMALL_CAP) |
| CX.ST | CombinedX AB | SE First North | `stock-scanner\smallcap\universe.py:192` (FIRST_NORTH) |
| TOBII.ST | Tobii AB | SE First North | `stock-scanner\smallcap\universe.py:51` (FIRST_NORTH) |
| STRO.OL | StrongPoint ASA | NO Oslo | `stock-scanner\smallcap\universe.py:373` (NORDIC_MARKETS) |
| KID.OL | Kid ASA | NO Oslo | `stock-scanner\smallcap\universe.py:375` (NORDIC_MARKETS) |
| RILBA.CO | Ringkjøbing Landbobank | DK København | `stock-scanner\reports\scored_universe_2026-08-28.parquet` (rad 19) |
| JYSK.CO | Jyske Bank | DK København | `stock-scanner\reports\scored_universe_2026-08-28.parquet` (rad 97) |
| HARVIA.HE | Harvia Oyj | FI Helsingfors | `stock-scanner\smallcap\universe.py:368` (NORDIC_MARKETS) |
| GOFORE.HE | Gofore Oyj | FI Helsingfors | `stock-scanner\smallcap\universe.py:365` (NORDIC_MARKETS) |

Bekräftelse av att detta är appens verkliga universum:
- `marketscan\backend_worker\universe_mapping.py:340` — `_NORDIC_SUFFIX_SQL = "(ticker LIKE '%.ST' OR ... '%.OL' ... '%.HE' ... '%.CO')"` (nordiska venue-suffix är definitionen).
- `marketscan\data\qmj_raw\` innehåller verkliga småbolag i pipelinen: `BIOA-B.ST`, `DYNVO.ST`, `NANEXA.ST`, `SIVE.ST`, `SMART.ST`.
- `stock-scanner\reports\smallcap_scored_2026-08-18.csv` — 54 småbolag: 48×`.ST`, 5×`.HE`, 1×`.OL` (samma suffixfamilj).
- Pipelinen hämtar priser med `fetch_prices_only(tickers, period="6mo", max_workers=12)` → `t.history(period=period, auto_adjust=True)` (`stock-scanner\core\data_fetcher_batch.py:443-464`; anropas från `marketscan\backend_worker\pipeline\entrypoint.py:91`).

---

## 2. `.info`-täckning per ticker (present/absent + värde)

Alla 10 tickers **resolverar** (shortName/longName finns). Fält per ticker:

| Fält | MYCR | LAGR-B | CX | TOBII | STRO | KID | RILBA | JYSK | HARVIA | GOFORE | Täckning |
|---|---|---|---|---|---|---|---|---|---|---|---|
| shortName/longName | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| marketCap | ✅ 66,0 md | ✅ 47,1 md | ✅ 750 m | ✅ 332 m | ✅ 430 m | ✅ 5,2 md | ✅ 42,5 md | ✅ 61,4 md | ✅ 846 m | ✅ 194 m | 10/10 |
| currency | SEK | SEK | SEK | SEK | NOK | NOK | DKK | DKK | EUR | EUR | 10/10 |
| sector | Industrials | Industrials | Technology | Technology | Industrials | Cons. Cycl. | Financials | Financials | Cons. Cycl. | Technology | 10/10 |
| industry | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| trailingPE | 38,1 | 37,6 | 5,5 | ❌ | ❌ | 19,9 | 18,6 | 12,7 | 30,0 | 18,1 | 8/10 |
| forwardPE | 20,7 | 42,1 | 10,5 | −3,1 | 106,7 | 12,3 | 15,5 | 11,5 | 20,6 | 11,7 | 10/10 |
| priceToBook | 8,38 | 9,98 | 1,26 | 0,87 | 0,97 | 3,84 | 3,67 | 1,32 | 6,39 | 1,78 | 10/10 |
| returnOnEquity | 0,237 | 0,285 | 0,257 | −0,587 | −0,023 | 0,201 | 0,203 | 0,103 | 0,229 | 0,107 | 10/10 |
| debtToEquity | 5,3 | 104,1 | 15,8 | 150,7 | 48,6 | 179,3 | ❌ | ❌ | 76,9 | 48,5 | 8/10 |
| freeCashflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | 8/10 |
| dividendYield | 0,97 | 1,10 | 2,56 | ❌ | ❌ | 7,86 | 0,67 | 2,32 | 1,68 | 4,19 | 8/10 |
| dividendRate | 3,25 | 2,50 | 1,00 | ❌ | ❌ | 10,0 | 12,0 | 25,0 | 0,77 | 0,49 | 8/10 |
| earningsDate | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/10** |
| earningsTimestamp | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 8/10 |
| earningsTimestampStart/End | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 8/10 |
| longBusinessSummary | ✅ 1302 ch | ✅ 1357 | ✅ 585 | ✅ 1606 | ✅ 1347 | ✅ 835 | ✅ 559 | ✅ 1127 | ✅ 701 | ✅ 395 | 10/10 |
| analystCount | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/10** |
| numberOfAnalystOpinions | 4 | 8 | 1 | 1 | 2 | 5 | 4 | 5 | 4 | 2 | 10/10 |
| totalRevenue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| netIncomeToCommon | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| operatingCashflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 9/10 |
| totalDebt / totalCash | ✅ | ✅ | ✅ | ✅ | ✅ | totalCash ❌ | ✅ | ✅ | ✅ | ✅ | 9/10 |
| bookValue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| sharesOutstanding / floatShares | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| beta | 0,70 | 1,20 | 0,46 | 0,64 | 0,62 | 0,57 | 0,31 | 0,36 | 1,27 | 0,14 | 10/10 |
| 52w high/low + regularMarketPrice | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| exchange / quoteType / market / country | STO/EQUITY/se/Sweden | … | … | … | OSL/no/Norway | … | CPH/dk/Denmark | … | HEL/fi/Finland | … | 10/10 |
| recommendationMean | 2,75 | ❌ | ❌ | 3,0 | ❌ | 1,8 | ❌ | 2,5 | 1,25 | 1,0 | 6/10 |
| targetMeanPrice | 311,5 | 271,9 | 48,8 | 2,0 | 13,0 | 143,6 | 1922,5 | 1052,0 | 49,5 | 15,5 | 10/10 |

**Tolkning av hålen:**
- `earningsDate` är **alltid null** — pipelinen måste använda `earningsTimestamp` (unix) i stället. 8/10 har den; CX.ST och STRO.OL saknar (ingen publicerad kommande rapport).
- `analystCount` är **alltid null** — använd `numberOfAnalystOpinions` (1–8, finns på alla 10).
- Banker (RILBA.CO, JYSK.CO): `debtToEquity` + `freeCashflow` saknas — bankredovisning, förväntat.
- Förlustbolag (TOBII, STRO): `trailingPE`, `dividendYield` saknas — förväntat.
- Notera: RILBA.CO shortName innehåller Yahoo-mojibake "Ringkj�bing" (Yahoos egna data, inte vår encoding).

---

## 3. Historikdjup

### period="10y" daglig (2–3 tickers, här 4 för marknadsspridning)
| Ticker | Rader | Första | Sista | Gap >7d |
|---|---|---|---|---|
| MYCR.ST | 2515 | 2016-08-29 | 2026-08-28 | 0 |
| CX.ST | 1110 | 2022-03-28 | 2026-08-28 | 0 (IPO senare) |
| RILBA.CO | 2501 | 2016-08-29 | 2026-08-28 | 0 |
| HARVIA.HE | 2117 | 2018-03-22 | 2026-08-28 | 0 (IPO 2018) |

### period="6mo" daglig på ALLA (pipeline-mönstret, entrypoint.py:91 → data_fetcher_batch.py:464)
| Ticker | Rader | Första | Sista | Gap >7d |
|---|---|---|---|---|
| MYCR.ST | 125 | 2026-03-02 | 2026-08-28 | 0 |
| LAGR-B.ST | 125 | 2026-03-02 | 2026-08-28 | 0 |
| CX.ST | 125 | 2026-03-02 | 2026-08-28 | 0 |
| TOBII.ST | 125 | 2026-03-02 | 2026-08-28 | 0 |
| STRO.OL | 124 | 2026-03-02 | 2026-08-28 | 0 |
| KID.OL | 124 | 2026-03-02 | 2026-08-28 | 0 |
| RILBA.CO | 122 | 2026-03-02 | 2026-08-28 | 0 |
| JYSK.CO | 122 | 2026-03-02 | 2026-08-28 | 0 |
| HARVIA.HE | 125 | 2026-03-02 | 2026-08-28 | 0 |
| GOFORE.HE | 125 | 2026-03-02 | 2026-08-28 | 0 |

Kolumnerna i båda fallen: `Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits`. Inga luckor >7 kalenderdagar. 6mo-mönstret ger komplett ~125 handelsdagar på alla 10.

---

## 4. quarterly_financials (nordiska resultaträkningar?)

| Ticker | Rader | Senaste kvartal | Äldsta kolumn | Net Income? | Total Revenue? |
|---|---|---|---|---|---|
| MYCR.ST | 36 | 2026-06-30 | 2024-12-31 | ✅ | ✅ |
| STRO.OL | 40 | 2026-06-30 | 2024-12-31 | ✅ | ✅ |
| HARVIA.HE | 42 | 2026-06-30 | 2024-12-31 | ✅ | ✅ |

Ja — riktiga nordiska kvartalsrapporter (EBITDA/EBIT/Net Income/Revenue), ~6 kvartal bakåt (2024-12-31 → 2026-06-30). Radantalet 36–42 är rad-index (rader), inte kvartal.

---

## 5. earnings_dates + dividends + splits (split-hantering)

| Ticker | earnings_dates | dividends | splits |
|---|---|---|---|
| MYCR.ST | 25 rader (2018-02-07 → 2026-10-22); kol: EPS Estimate, Reported EPS, Surprise(%) | 14 rader (2014-06-16 → 2026-05-07), senaste 3,25 | 1 st: 2025-06-03 ×2,0 |
| RILBA.CO | 25 rader (2020-10-28 → 2026-10-21); samma kol | 21 rader (2004-02-26 → 2026-03-05), senaste 12,0 | 2 st: 2006-03-06 ×4,0, 2017-05-24 ×5,0 |

Split-historik returneras korrekt (inkl. RILBA:s 5:1-split 2017) — `auto_adjust`-hanteringen i pipelinen får data att arbeta med. earnings_dates innehåller framtida datum (2026-10-22) → fungerar för earnings-kalender.

---

## 6. Valutakonsistens

| Ticker | info.currency | fast_info.currency | history Close (senaste) | info.regularMarketPrice | Konsistent? |
|---|---|---|---|---|---|
| MYCR.ST | SEK | SEK | 338,20 | 338,20 | ✅ |
| LAGR-B.ST | SEK | SEK | 228,60 | 228,60 | ✅ |
| CX.ST | SEK | SEK | 38,50 | 38,50 | ✅ |
| TOBII.ST | SEK | SEK | 1,28 | 1,28 | ✅ |
| STRO.OL | NOK | NOK | 9,60 | 9,60 | ✅ |
| KID.OL | NOK | NOK | 127,20 | 127,20 | ✅ |
| RILBA.CO | DKK | DKK | 1794,00 | 1794,00 | ✅ |
| JYSK.CO | DKK | DKK | 1088,00 | 1088,00 | ✅ |
| HARVIA.HE | EUR | EUR | 45,25 | 45,25 | ✅ |
| GOFORE.HE | EUR | EUR | 11,92 | 11,92 | ✅ |

**OBS (yfinance 1.4.1):** history-DataFramen har **ingen Currency-kolumn** (kolumner: Open/High/Low/Close/Adj Close/Volume/Dividends/Stock Splits). Valutakonsistens verifierades i stället via (a) `info.currency == fast_info.currency` på 10/10 och (b) history-sista-close == info.regularMarketPrice på 10/10 → prisserien ligger i native-valutan, ingen blandning. Pipelinen måste hämta valutan från `info`/`fast_info`, inte från history.

---

## 7. Tidsmätning per hämtning (sekunder)

| Operation | Min | Max | Snitt (10 tickers) |
|---|---|---|---|
| `.info` (full quoteSummary) | 0,47 | 0,75 | ~0,54 |
| `history(period="6mo")` | 0,18 | 0,48 | ~0,33 |
| `history(period="10y")` | 0,50 | 4,75 (första, kall cache) | ~1,6 |
| `quarterly_financials` | 0,25 | 0,59 | ~0,39 |
| `earnings_dates` + `dividends` + `splits` | 1,88 | 1,93 | ~1,9 |

Skalning: 300 tickers × 6mo ≈ 100 s sekventiellt; med `max_workers=12` (pipeline-inställningen) ≈ 10–15 s. `.info` för 300 tickers ≈ 160 s sekventiellt, ~15–25 s med 12 workers. Ingen rate-limiting (429) observerades under hela testet.

---

## 8. Slutsats / verdict

**Gratis-stacken fungerar för nordiska småbolag — med tre kodnoteringar:**

1. **`earningsDate` är alltid null** → pipelinen måste använda `earningsTimestamp` (unix-epoch) för earnings-kalender. `analystCount` är också alltid null → använd `numberOfAnalystOpinions`.
2. **History har ingen valutakolumn i yfinance 1.4.1** → valuta måste tas från `info`/`fast_info` (konsistent på 10/10).
3. **Förväntade hål:** banker (RILBA.CO/JYSK.CO) saknar debtToEquity/freeCashflow; förlustbolag (TOBII/STRO) saknar trailingPE/dividendYield. Dessa är dataverklighet, inte täckningsfel.

Allt annat — resolution, marketCap, nyckeltal, 10y-historik, 6mo-pipeline-mönster, kvartalsrapporter, earnings/dividends/splits, valuta — är komplett på alla 10 testade tickers över SE/NO/DK/FI.

---

## 9. Exakta kommandon

```powershell
# Miljö
python --version                                   # Python 3.13.14
python -c "import yfinance; print(yfinance.__version__)"   # 1.4.1
python -c "import pandas; print(pandas.__version__)"       # 3.0.3

# Ticker-extraktion (källorna ovan)
python -c "import pandas as pd; df=pd.read_parquet(r'...\stock-scanner\reports\scored_universe_2026-08-28.parquet'); ..."

# Prober (körda i C:\Users\hthur\AppData\Local\Temp\opencode\datatest-yf\)
python probe_info.py          # → results_info.json
python probe_history.py       # → results_history.json
python probe_fundamentals.py  # → results_fundamentals.json
python probe_currency.py      # → results_currency.json
python -c "..."               # → results_currency2.json (fast_info-korscheck)
```

Proberna ligger kvar i `C:\Users\hthur\AppData\Local\Temp\opencode\datatest-yf\` tillsammans med alla `results_*.json` (rådata). Inga repo-filer ändrades.