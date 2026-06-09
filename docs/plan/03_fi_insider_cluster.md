# Spec 03 — #5: FI Insider Cluster (robust bulk-ingestion)

> **Repo:** `marketscan` (worker + DB + API + frontend). Återanvänder logik från
> `stock-scanner-fix/core/fi_insider_fetcher.py`.
> **Mål:** En ROBUST, Sverige-specifik insider-signal: dagligt hämta HELA
> Finansinspektionens insynsregister per datumintervall (inte per ticker), lagra,
> och beräkna **klustersignaler** (≥3 olika insiders köper inom 30 dagar) som
> akademiskt är den starkaste insider-signalen.
> **Användaren bad specifikt om robusthet här — prioritera felresiliens.**
> **Läs först:** master §2, §6.2, §6.5. Läs `stock-scanner-fix/core/fi_insider_fetcher.py`
> (HELT — innehåller FI-parsing + routine/opportunistic-logik att återanvända),
> `marketscan/backend_worker/insider_fetcher.py` (nuvarande Finnhub-version),
> migration `015_insider_trades.sql` + `027_insider_trades_dedup.sql`.

---

## 0. Varför nuvarande lösning inte räcker

- `core/fi_insider_fetcher.py`: söker FI **per bolagsnamn** → 1 HTTP-anrop × 1160 aktier,
  namnmatchning är skör (yfinance longName ≠ FI-emittentnamn), returnerar bara booleans.
- `backend_worker/insider_fetcher.py`: Finnhub per-ticker, 60 calls/min (≈20 min för hela
  universumet), och Finnhubs svenska insider-täckning är ofullständig.

**Robust lösning:** FI-registret är en enda källa. Hämta hela registret för de senaste
N dagarna i EN paginerad/exporterad fråga (ingen ticker-loop, ingen namnmatchning per
bolag). Mappa ISIN→ticker. Lagra rått. Beräkna kluster i DB/Python.

---

## 1. Delsteg A — Bulk-ingestion av FI-registret

**Fil:** `marketscan/backend_worker/fi_insider_bulk.py` (ny)

### A1. Hämtning (datumintervall, inte ticker)
FI:s register: `https://marknadssok.fi.se/publiceringsklient/sv/Search` med
`SearchFunctionType=Insyn`, `FromDate`, `ToDate`, `Page`, `PageSize`. Det finns en
"Exportera"-knapp (xlsx). Två vägar — implementera **A1a**, med **A1b** som fallback:

- **A1a (rekommenderas): paginerad Search.** Loopa `Page=1..N` med `PageSize=100`
  för intervallet `[idag - days, idag]`. Återanvänd `_parse_fi_json` / `_parse_fi_html`
  från `core/fi_insider_fetcher.py` (kopiera in eller importera). Stanna när en sida
  ger 0 rader. Mellan sidor: `time.sleep(0.4)` + browser-headers (finns i den filen).
- **A1b: Excel-export.** Inspektera "Exportera"-knappens nätverksanrop (DevTools) för att
  hitta export-URL:en (sannolikt `…/Search/Export?…` med samma datum-params, returnerar
  `.xlsx`). Ladda ner och parsa med `pandas.read_excel(BytesIO(resp.content))`.
  > Tills export-URL:en är bekräftad: använd A1a. Skriv `# TODO(fråga)` om osäker.

### A2. Normalisering (en rad per transaktion)
Mappa FI-fält → vårt schema. FI ger bl.a.: Emittent, Person, Befattning, Karaktär
(förvärv/avyttring), ISIN, Instrumentnamn, Volym, Pris, Valuta, Transaktionsdatum.
Normalisera till:
```python
{
  "isin": str, "issuer": str, "name": str, "role": str,
  "type": "buy"|"sell",          # via _BUY_KEYWORDS i fi_insider_fetcher.py
  "shares": float, "price": float, "amount": float,  # amount = shares*price om saknas
  "trade_date": "YYYY-MM-DD",
}
```

### A3. ISIN → ticker-mappning
FI ger ISIN, vårt `insider_trades` använder ticker. Bygg en mappning:
- Kolla om `scan_results` (eller `company_profiles`, migration 026) har en `isin`-kolumn.
  Om ja: bygg dict `{isin: ticker}` därifrån (en DB-query).
- Om nej: lägg till `isin`-kolumn i `company_profiles` och fyll via yfinance `info.isin`
  i `company_info_fetcher.py` (befintlig worker). Tills dess: skriv trades vars ISIN inte
  kan mappas till en separat `insider_trades_unmapped`-logg (skrota inte data).
> Verifiera vilka tabeller som har ISIN innan du bygger. Skriv valet i koden.

### A4. Skrivning (idempotent)
Upsert till `insider_trades` med `ON CONFLICT (ticker, name, trade_date, type) DO NOTHING`
(constraint finns via migration 027). Lägg till `isin`, `price` om kolumnerna saknas (se A5).

### A5. Robusthet (KRITISKT — detta är hela poängen)
- **0-rader-larm:** Om en körning ger 0 transaktioner totalt för ett intervall där FI
  rimligen borde ha data (vardagar) → logga `ERROR` och skriv en rad i en
  `worker_health`-logg / sätt exit-kod ≠ 0 så GitHub Actions failar synligt. Detta
  upptäcker när FI ändrar HTML/endpoint.
- **Dubbel parser:** JSON-först, HTML-fallback (finns redan i fi_insider_fetcher.py).
- **Rå-arkiv:** spara varje dags rå-respons till `data/fi_raw/YYYY-MM-DD.json` (eller R2 via
  `r2_uploader.py`) så historik kan återuppspelas om parsing måste fixas i efterhand.
- **Idempotent + överlappande fönster:** kör med `--days 7` dagligen (överlappar) så
  enstaka missade dagar fylls i; dedup hindrar dubbletter.

---

## 2. Delsteg B — Klusterscoring

**Fil:** `marketscan/backend_worker/insider_cluster.py` (ny)

Beräkna per ticker (rullande 30 dagar) ur `insider_trades`:
```python
cluster_score(ticker) =
    unique_buyers_30d                # antal OLIKA insiders som KÖPT senaste 30d
  × log1p(total_buy_amount_30d / market_cap)   # conviction relativt storlek
  × exec_weight                      # ×1.5 om VD/CFO/ordförande bland köparna
```
Flaggor:
- `INSIDERCLUSTER` = `unique_buyers_30d >= 3`
- `EXEC_BUY` = någon exec-roll köpt senaste 90d

Återanvänd `_EXEC_TITLES`, `_BUY_KEYWORDS` och routine/opportunistic-filtret
(`_is_routine_trader`) från `core/fi_insider_fetcher.py` — routine-köp (samma person,
samma månad/belopp varje år) ska INTE räknas i klustret.

> Akademisk grund: kluster av samtidiga insiderköp är den persistenta signalen
> (1–3 mån), enskilda trades har bara 2–5 dagars fönster.

### Lagring
**Migration 028 (eller nästa lediga):** `marketscan/supabase/migrations/0NN_insider_cluster.sql`
```sql
CREATE TABLE IF NOT EXISTS insider_cluster_signals (
  ticker TEXT PRIMARY KEY,
  unique_buyers_30d INTEGER NOT NULL DEFAULT 0,
  total_buy_amount_30d NUMERIC(16,2) DEFAULT 0,
  cluster_score FLOAT DEFAULT 0,
  is_cluster BOOLEAN DEFAULT FALSE,
  exec_buy_90d BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE insider_cluster_signals ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON insider_cluster_signals TO anon, authenticated;
CREATE POLICY "insider_cluster_public_read" ON insider_cluster_signals FOR SELECT USING (true);
```
Worker upsertar hela tabellen efter varje ingestion.

---

## 3. Delsteg C — Schemaläggning

**Fil:** `.github/workflows/fi_insider.yml` (ny). Ersätter/komplementerar den gamla
`insider_trades.yml` (Finnhub). Daglig 03:40 UTC (efter pipeline):
1. `python -m backend_worker.fi_insider_bulk --days 7`
2. `python -m backend_worker.insider_cluster`

Registrera i `apps/api/routers/admin.py` `_WORKFLOW_INPUTS` + admin-panelen.
Behåll Finnhub-workern som valfri sekundärkälla (eller pensionera — skriv vilket).

---

## 4. Delsteg D — API + frontend

### D1. API
- `apps/api/routers/insider.py` (finns troligen för Insider Radar — verifiera): lägg
  endpoint `GET /api/insider/clusters` → topp cluster-signaler (join mot scan_results
  för namn/score/pris).
- Lägg `is_cluster` / `cluster_score` i scan-row-enrichment så aktiekortet kan visa det.

### D2. Frontend
- **Insider Radar-sidan** (`apps/web/app/(app)/insider-radar/`): lyft fram
  `INSIDERCLUSTER`-aktier överst med antal köpare + belopp + exec-flagga.
- **Daglig Briefing:** "Insiderköp"-kortet använder redan `useInsiderRadar` — peka det mot
  klustersignalerna så det visar de starkaste klustren.
- **Aktiekort:** badge "👁 Insiderkluster (N köpare)" + tooltip (evidens: samtidiga
  insiderköp = stark signal).

---

## 5. Filer som rörs

| Fil | Åtgärd |
|---|---|
| `backend_worker/fi_insider_bulk.py` | NY — bulk-ingestion |
| `backend_worker/insider_cluster.py` | NY — klusterscoring |
| `supabase/migrations/0NN_insider_cluster.sql` | NY — signal-tabell (+ev. isin-kolumn) |
| `backend_worker/company_info_fetcher.py` | Ev. fylla isin i company_profiles |
| `.github/workflows/fi_insider.yml` | NY — daglig cron |
| `apps/api/routers/admin.py` | Registrera workflow |
| `apps/api/routers/insider.py` | Endpoint för kluster |
| `apps/web/app/(app)/insider-radar/` | Lyft fram kluster |
| `apps/web/components/stock/…` | Badge + tooltip |

## 6. Definition of Done
- [ ] Bulk-ingestion hämtar HELA registret per datumintervall (ingen ticker-loop).
- [ ] ISIN→ticker mappas; omappade trades tappas inte (loggas separat).
- [ ] Idempotent upsert; överlappande 7-dagarsfönster.
- [ ] **0-rader-larm** failar körningen synligt (robusthetskravet).
- [ ] Rå-arkiv sparas för återuppspelning.
- [ ] `insider_cluster_signals` fylls; INSIDERCLUSTER-flagga korrekt (≥3 köpare, routine
      bortfiltrerat).
- [ ] Insider Radar + Daglig Briefing + aktiekort visar kluster.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
