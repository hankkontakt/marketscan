# Datatest — nulägesinventering (read-only)

Datum: 2026-08-28. Läs-only-uppdrag: ingen kod ändrad, inga workflows triggade,
inga secret-värden lästa (endast namn). Allt nedan är verifierat mot faktisk
utdata från gh/git/python/filsystemet.

## 1. Repo

- `git remote -v` → `origin https://github.com/hankkontakt/marketscan.git`
- Owner/repo: **hankkontakt/marketscan**, branch `master`.

## 2. Workflow-runs (senaste 30) — vad systemet faktiskt levererar

`gh run list -R hankkontakt/marketscan -L 30` (2026-08-28, alla på master):

| Status | Antal |
|---|---|
| success | 22 |
| failure | 7 |
| queued | 1 |
| skipped | 1 |

**Misslyckade workflows (i fönstret):**

| Workflow | Failures i fönstret | Senaste 10 per workflow |
|---|---|---|
| Universe Mapping | 3 (15:39, 14:48, 12:16 idag) | 3/8 misslyckade (endast 8 körningar finns) |
| QMJ Scores | 1 (12:40 idag) | 1/5 misslyckade |
| Smart Alerts — nightly alert engine | 2 (09:21 idag, 08-10) | 3/10 misslyckade, 7 skipped, **0 success** |
| Weekly Digest — send email summaries | 1 (08-10) | **7/10 misslyckade** (06-29 → 08-10), 3 success (06-10 → 06-22) |

Övrigt i fönstret:
- **MarketScan Pipeline-körning 33156202321 ligger i kö i 7h48m50s** (queued sedan 08:39 UTC) — fastnat i kön.
- Score Tracker 08-10: skipped.
- Senaste 30 innehåller 8 körningar av Universe Mapping, 5 av QMJ Scores, 3 av FI Short Positions, 2 av News Pipeline — alla workflow_dispatch (manuella/automatiska idag).

**Workflow-inventering** (`gh workflow list`): 27 aktiva workflows — Backtest Runner, Check Supabase Connection Pooler, Company Profiles, Weekly Digest, Doc Intelligence, FI Insider Bulk, Insider Trades, ML Retraining, ML Training, News Pipeline, Options Scanner, Orchestrator (kör allt), MarketScan Pipeline, PR CI, QMJ Scores, Risk Analysis, Score Tracker, Sector Rotation, FI Short Positions, Signal Analytics, Smallcap Scan, Smart Alerts, Strategy Backtester, Universe Discovery, Universe Mapping, Watchlist Alerts, Dependency Graph.

## 3. Secrets — NAMN ENDAST (12 st)

`gh secret list -R hankkontakt/marketscan`:

```
APP_URL, DATABASE_URL, DEEPSEEK_API_KEY, EMAIL_FROM, FINNHUB_API_KEY,
GEMINI_API_KEY, GH_CHECKOUT_TOKEN, RESEND_API_KEY, SUPABASE_ANON_KEY,
SUPABASE_SERVICE_KEY, SUPABASE_URL
```

API-nycklar i produktion: **Finnhub** (FINNHUB_API_KEY), **DeepSeek**
(DEEPSEEK_API_KEY), **Gemini** (GEMINI_API_KEY), **Resend** (RESEND_API_KEY —
e-post), GH_CHECKOUT_TOKEN. **Ingen FMP-nyckel** finns trots att
`company_info_fetcher.py` har FMP-fallback-kod. DATABASE_URL/SUPABASE-*
uppdaterade 2026-08-28 (08:37), DEEPSEEK_API_KEY 2026-08-28 (14:37).

## 4. Lokala datakataloger

### marketscan\data\ (gitignored — `.gitignore:25 data/` "never commit market data")

| Katalog | Filer | Storlek | Innehåll |
|---|---|---|---|
| `fi_raw` | 3 | ~14 KB | `emittent_candidates.json` (11 KB, **112 FI-härledda emittentkandidater**, source=insyn, t.ex. Duroc, Ellos Holding, Norion Bank), `isin_symbol_cache.json` (147 B, 2 ISIN → båda `symbol: null` = missar), `lei_isin_cache.json` (2,6 KB, ~75 LEI→ISIN, ~30 mappade till SE-ISIN) |
| `qmj_raw` | 5 | 0,1 MB | Per-ticker yfinance-JSON (frame_fin/frame_bal/frame_cash årsvis 2021–2025, close_last, returns_1y): BIOA-B.ST (31 KB), NANEXA.ST (31 KB), SIVE.ST (37 KB) — full data; **DYNVO.ST + SMART.ST (140 B vardera) = tomma frames, fetch-fel**. Skrivna idag 12:48–15:08 |
| `cache` | 0 | — | Tom |

### stock-scanner\data\ (320 filer, 2,5 MB)

- `universe.json`: 10 universum — US_LARGE_CAP 512, ASIA_PACIFIC 230, EUROPE 186, OMX_SE 70, UK 71, NORDIC 58, GERMANY 57, CANADA 53, BRAZIL 42, **SMALLCAP 0**. Suffixfördelning: NORDIC = CO 20 / OL 22 / HE 16; OMX_SE = ST 70.
- `universe_smabolag.txt`: 379 rader, "Totalt: 318 aktier" (exkluderingslista, uppdaterad 2026-05-19).
- `universe_stora_scannen.txt`: 321 rader, "Totalt: 1220 aktier".
- `universe_europa_smabolag.txt`: 98 rader, "Totalt: 220 aktier".
- `scan_log.json`: 90 poster, 2026-07-29 → 2026-08-21, **alla OK** (evening 25, refresh_missing 28, portfolio_refresh 14, morning 14, weekly 3, retry_rate_limited 3, smallcap 3).
- `smallcap_scores_prev.json`: 54 tickers (CX.ST 68,11; TAGM-B.ST 65,61; MAGI.ST 61,9 …).
- `piotroski_snapshots.parquet`: 1198 rader, kolumner [_date, _ticker, roa, debt_to_equity, current_ratio, gross_margin, operating_margin], datum 2026-05-31.
- `bt_snapshots\`: 19 parquet, 2026-05-14 → 2026-08-15, 158 → 832 rader (se §6).
- `paper_trades.json`: 264 trades (week 2026-05-31, universe smallcap, alla OPEN).
- `ml_paper_smallcap.json`: 130 trades, 2026-05-31 → 2026-08-17, alla öppna.
- `metrics\` 107 filer, `health\` 67 filer (från 2026-06-02), `ai_cache\` 87 filer (ai_evening_*.md från 2026-06-01), `insider_history\` 1, `ml_backtest_results\` 1, `custom_universe.json` 40 tickers, `blacklist.json` 50 nycklar, `discovery_candidates.json` (version/last_updated/candidates/auto_added/auto_removed). `cache\` och `logs\` tomma.

## 5. Universum som pipelinen faktiskt använder

- **Ingen statisk universumfil i marketscan-repot** (glob `**/universe*.{json,txt,csv}` → 0 träffar). Universumet lever i **Supabase-tabellen `universe_registry`** (ingen lokal DB).
- `backend_worker/universe_mapping.py`: FI marknadssök-insynsregister (180-dagarsfönster) är "sanningen"; ISIN→ticker via Finnhub `profile2?isin=` + yfinance `Lookup` (keyless). Endast nordiska venue-suffix: `.ST/.OL/.HE/.CO`. Delisting-detektor via Yahoo-presence (cachad 7 d).
- `backend_worker/qmj_scores.py` (rad 442–447): `SELECT ticker FROM universe_registry WHERE status IN ('listed','verify') AND ticker LIKE %.ST/%.OL/%.HE/%.CO ORDER BY ticker LIMIT 120` — fallback till `scan_results`. Batch-limit 120/natt (yfinance-rate-limit).
- `backend_worker/finnhub_universe.py`: **Finnhub /stock/symbol har INGEN nordisk täckning på free tier** (verifierat 2026-08-28, kommenterat i universe_mapping.yml) — modulen kvar för framtida betald tier.
- Lokal evidens för universumstorlek: 112 FI-emittentkandidater (idag), ~75 LEI i cachen, 2 ISIN→symbol-träffar (båda missar). **Småbolag per börsvärde: ej härledbart lokalt** — varken bt_snapshots eller piotroski har market_cap-kolumn; smallcap_scanner.py *skriver* market_cap men ingen lokal scan_results-fil med det finns. Närmaste proxy: smabolag-universumet i stock-scanner = 318 aktier (exkluderingslista).

## 6. scan_results-liknande data — datumintervall & radantal

| Fil | Rader | Datumintervall |
|---|---|---|
| `bt_snapshots\*.parquet` (19 st) | 158 → 832 per snapshot (~12 000 totalt) | 2026-05-14 → 2026-08-15 |
| Senaste snapshot (2026-08-15) | 832 | schema: score_total, score_value, score_quality, score_momentum, score_growth, score_risk, score_dividend, score_sentiment, entry_signal, current_price, sector, name, return_12m/6m/3m, snapshot_date. Suffix: NO_SUFFIX 360, L 61, T 54, **ST 53**, TO 41, DE 34, HK 30, NS 27, PA 18, SA 16, KS 16, **OL 14, CO 14**, SW 14, AS 13, TW 12, **HE 10**, MI 9, AX 9, MX 6 → **91 nordiska tickers** (ST+OL+CO+HE). STARK-signaler: 2 |
| `piotroski_snapshots.parquet` | 1198 | 2026-05-31 (en datumstämpel) |
| `smallcap_scores_prev.json` | 54 | — |
| `paper_trades.json` | 264 | week 2026-05-31, alla OPEN |
| `ml_paper_smallcap.json` | 130 | 2026-05-31 → 2026-08-17 |

## 7. Dataquality-observationer (empiriskt)

- **Mojibake** i stock-scanner-filer: `paper_trades.json` har `"sector": "�vrigt"` (Övrigt) och `"entry_signal": "�"`; bt_snapshot-parquet har `"V�NTA"` (VÄNTA). Teckenkorruption i äldre data.
- **qmj_raw**: 2 av 5 filer (DYNVO.ST, SMART.ST) är 140 B-fetchfel med tomma frames — QMJ-kedjan tappar dessa tickers.
- **isin_symbol_cache**: 2 poster, båda null (ISIN→ticker-missar).
- **Weekly Digest**: 7/10 senaste misslyckade (e-postkedjan trasig sedan 2026-06-29).
- **Smart Alerts**: 3/10 misslyckade, 7 skipped, 0 success.
- **MarketScan Pipeline**: en körning fastnat i kö 7h48m50s.
- Universe Mapping: 3 misslyckade idag (12:16, 14:48, 15:39) — intermittent (marknadssök rate-limit/connection, se backoff-koden i universe_mapping.py).

## 8. Slutsats (vad systemet levererar idag)

- **Produktion (GitHub Actions)**: 22/30 senaste körningar gröna; kärnkedjan (Universe Mapping → QMJ → FI Short Positions → News) körs aktivt och skriver till Supabase. Men e-post (Weekly Digest) och Smart Alerts är konsekvent trasiga, och en pipeline-körning sitter fast i kön.
- **Lokalt**: ingen DB; data finns som små JSON/parquet-cacher. Universumet (FI-registret, 112 kandidater idag) är litet jämfört med stock-scanner-appens 318/1220/220-aktierslistor. QMJ har bara 5 tickers i qmj_raw-cachen lokalt (2 var fetch-fel).
- **API-nycklar i prod**: Finnhub, DeepSeek, Gemini, Resend — alla närvarande. Ingen FMP trots kod som refererar den.