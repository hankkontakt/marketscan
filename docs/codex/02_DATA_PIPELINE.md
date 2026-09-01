# 🔄 Kapitel 2: Data Pipeline & Ingestion Engine

> **Domän:** Automatiserad datainhämtning, scrapers, FI-register, Cision nyhetsströmmar och batch-uppdateringar.  
> **Status:** Aktiv produktion.

---

## 1. Executive Summary & TL;DR

Data Pipeline ansvarar för att hämta, deduplicera, normalisera och ladda finansiell data till Supabase. Den körs via schemalagda GitHub Actions och lokala skript, och matar både het databaslagring (`scan_results`) och historisk utfallsloggning.

---

## 2. Arkitektur & Dataflöde

```
  ┌────────────────────────────────────────────────────────────┐
  │                   Externa Datakällor                       │
  │  • Finansinspektionen (Insyn CSV & Blankningsregister)     │
  │  • Cision Wire (Realtids RSS / Pressmeddelanden)           │
  │  • Finnhub API (Universum & Basdata)                       │
  │  • Yahoo Finance (Prishistorik, Finansiella nyckeltal)     │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │                 backend_worker/pipeline/                   │
  │  1. entrypoint.py (Orkestrering per körningsläge)          │
  │  2. fi_insider_bulk.py (Paginering & deduplicering)        │
  │  3. news_stream_cision.py (Sentiment & event-taggning)     │
  │  4. universe_mapping.py (ISIN / LEI / Ticker-mappning)     │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │                 backend_worker/db_loader.py                │
  │  • Validering & UTF-8 / FX-normalisering (SEK->USD)        │
  │  • Upsert till Supabase Postgres via Session Pooler        │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │               backend_worker/outcome_filler.py             │
  │  • Fyller i faktiska utfall (+1v, +1m, +3m) för ML-audit   │
  └────────────────────────────────────────────────────────────┘
```

---

## 3. Primära Datakällor & Protokoll

| Datakälla | Modul | Protokoll / Format | Beskrivning |
|---|---|---|---|
| **FI Insynsregister** | `backend_worker/fi_insider_bulk.py` | HTTPS / CSV export | Bulk-hämtning av alla insynstransaktioner från Finansinspektionen. Dedupliceras mot Finnhub. |
| **FI Blankning** | `backend_worker/fi_short_positions.py` | HTTPS / CSV | Aktuella och historiska korta positioner $> 0.5\%$ i svenska bolag. |
| **Cision Nyheter** | `backend_worker/news_stream_cision.py` | RSS / JSON Stream | Svenska bolagsnyheter i realtid, kategoriserade i regulatoriska vs marknadsföring. |
| **Kvartalsrapporter** | `backend_worker/earnings_surprise.py` | REST API | Faktiska resultat vs konsensus (SUE - Standardized Unexpected Earnings). |
| **Priser & Nyckeltal** | `backend_worker/company_info_fetcher.py` | HTTP Scraping | Prishistorik, omsättning, EBITDA, balansräkningar. |

---

## 4. Normaliseringsregler & Gotchas

1. **FX-Normalisering:** Marknadsvärde (`market_cap`) och intäkter normaliseras alltid till gemensam valuta (USD/SEK) i `backend_worker/db_loader.py` före segmentindelning (Large/Mid/Small/Micro).
2. **Ticker & ISIN Resolver:** `backend_worker/universe_mapping.py` hanterar matchning mellan ISIN, LEI-kod och Yahoo-suffix (`.ST`, `.OL`, `.HE`, `.CO`).
3. **Encoding:** Alla CSV- och nätverksströmmar måste tvingas till `UTF-8` med `client_encoding="UTF8"` för att förhindra teckenfel i svenska å/ä/ö.
4. **Service Role:** Pipeline-körningar kräver `SUPABASE_SERVICE_ROLE_KEY` för att kunna skriva till tabeller med RLS aktiverat.
5. **Segment-klassificering & Guard:** Marknadsvärde (`market_cap`) lagras i absolut USD. `_derive_segment()` tillämpar enhetsguard ($0 < mc < 10^6 \implies mc \times 10^6$) och sätter saknade/icke-positiva värden till `"unknown"` (aldrig `micro_cap`), vilket förhindrar att stora bolag felaktigt klassas som mikrobolag.

---

## 5. Källkodskarta & Filankare

| Komponent | Fil | Kärnmetoder / Ansvar |
|---|---|---|
| Pipeline Entrypoint | `backend_worker/pipeline/entrypoint.py` | `main()`, `run_morning()`, `run_nightly()` |
| DB Loader | `backend_worker/db_loader.py` | `load_scan()`, `log_pipeline_run()`, `_prepare_df()` |
| FI Insyn Ingestion | `backend_worker/fi_insider_bulk.py` | `fetch_register()`, `parse_fi_csv()`, `upsert_trades()` |
| FI Blanknings Ingestion | `backend_worker/fi_short_positions.py` | `fetch_short_positions()`, `upsert_positions()` |
| Universumhantering | `backend_worker/universe_discovery.py` | `discover_universe()`, `resolve_ticker()` |
| Utfallsloggning | `backend_worker/outcome_filler.py` | `fill_outcomes()`, `calculate_forward_returns()` |

---

## 6. Körning & Felsökning

### Köra morgon-pipeline lokalt:
```bash
# Kör med begränsat universum för snabbtest
python backend_worker/pipeline/entrypoint.py --mode targeted --tickers "INVE-B.ST,VOLV-B.ST,EVO.ST"
```

### Ladda rådata direkt:
```bash
python load_data.py
```
