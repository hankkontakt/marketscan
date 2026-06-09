# Spec 02 — #3: MEWS (Multi-Bagger Early Warning Score)

> **Repo:** `stock-scanner-fix` (scoring) + `marketscan` (DB-kolumn, API, frontend-badge).
> **Mål:** Ett separat, evidensbaserat 0–100-score som flaggar småbolag med
> mångdubblar-potential INNAN marknaden prissatt in dem — utan att störa nuvarande
> 8-faktors-score.
> **Evidensgrund:** Yartseva 2025 (BCU CAFÉ WP#33), 464 verkliga 10x-aktier 2009–2024.
> Starkaste prediktorer: **FCF-yield**, litet bolag (~348M USD), låg P/S (~0.6),
> **operativ hävstång** (rörelsevinst växer snabbare än intäkter), rena accruals (låg Sloan).
> Vinsttillväxt vid köp predikterade INTE — operativ hävstång gjorde.
> **Läs först:** master §2, §6. Läs sedan `smallcap/scoring.py` (HELT — grunden finns där),
> `core/scoring.py` (faktor-API), `core/data_fetcher.py` (vilka fundamenta hämtas),
> `smallcap/scanner.py`, `core/piotroski.py`.

---

## 0. Designprincip

MEWS är ett **kompletterande** score, inte en ändring av huvud-scoringen. Det beräknas
för hela universumet men är mest relevant för små/medelstora bolag. Det visas som en egen
badge/kort, och kan senare bli en ML-feature (#15).

`smallcap/scoring.py` har redan FCF-yield, insider, Piotroski, growth, valuation. MEWS
återanvänder de byggstenarna men lägger till de specifika mångdubblar-signalerna och en
egen viktning.

---

## 1. Delsteg A — Verifiera/komplettera fundamentaldata

MEWS kräver dessa fält per ticker. Kontrollera i `core/data_fetcher.py` vilka som redan
hämtas (flera finns: `free_cash_flow`, `market_cap`, `price_to_sales`, `revenue`,
`operatingMargins`, `grossMargins`, `revenue_growth`). Lägg till saknade:

| Fält | Källa (yfinance) | Används till |
|---|---|---|
| `free_cash_flow` | `cashflow` / `freeCashflow` | FCF-yield ✓ (finns) |
| `market_cap` | `info.marketCap` | storlek, FCF-yield ✓ |
| `price_to_sales` | `info.priceToSalesTrailing12Months` | värdering ✓ |
| `revenue_ttm` | `financials` Total Revenue | P/S, operativ hävstång |
| `revenue_growth` | beräknad YoY | acceleration ✓ |
| `operating_income_ttm` | `financials` Operating Income | operativ hävstång |
| `operating_income_prev` | föregående års Operating Income | operativ hävstång |
| `net_income_ttm` | `financials` Net Income | Sloan accruals |
| `operating_cashflow_ttm` | `cashflow` Operating Cash Flow | Sloan accruals |
| `total_assets` | `balance_sheet` Total Assets | Sloan accruals |
| `total_assets_prev` | föregående års Total Assets | Sloan accruals (snitt) |

> Om något fält saknas i `data_fetcher.py`: lägg till hämtning enligt befintligt mönster
> i filen (samma try/except + cache). Saknas data för en ticker → fältet blir NaN och
> MEWS-delfaktorn ger neutral poäng (gissa aldrig).

---

## 2. Delsteg B — Ny modul `smallcap/mews.py`

**Fil:** `stock-scanner-fix/smallcap/mews.py` (ny). Återanvänd `_percentile_score`,
`_winsorize` från `smallcap/scoring.py` (importera dem).

### Delfaktorer (varje 0–100, percentil-rankad cross-sectional)

```python
"""
mews.py — Multi-Bagger Early Warning Score.
Evidensbaserad (Yartseva 2025): hittar småbolag med 10x-potential tidigt.
Returnerar 0-100 + komponenter + boolean-flagga POTENTIAL_MANGDUBBLARE (>=70).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from smallcap.scoring import _percentile_score, _winsorize

# Vikter (summa = 1.0). Härledda ur studiens prediktorstyrka.
MEWS_WEIGHTS = {
    "fcf_yield":          0.25,  # starkaste prediktorn
    "small_size":         0.15,  # litet bolag = mer utrymme att växa
    "low_ps":             0.15,  # låg price/sales vid ingång
    "operating_leverage": 0.20,  # rörelsevinst växer snabbare än intäkter
    "revenue_accel":      0.15,  # intäktsacceleration
    "clean_accruals":     0.10,  # låg Sloan = ärliga vinster
}
MEWS_THRESHOLD = 70.0  # >= → POTENTIAL_MANGDUBBLARE
```

**Formler (cross-sectional, högre = bättre):**

1. **fcf_yield** = `free_cash_flow / market_cap` → `_percentile_score(asc=True)`.
   Negativ FCF → 0 (clip lower=0 före percentil).
2. **small_size** = invers av `market_cap` (mindre = högre poäng):
   `_percentile_score(market_cap, ascending=False)`. Men nollställ mikrobolag under
   likviditetsgräns (t.ex. market_cap < 100 MSEK ELLER avg daily turnover < 1 MSEK) →
   sätt small_size till `NaN`-neutral för att undvika oinvesterbara skräpbolag.
3. **low_ps** = `_percentile_score(price_to_sales, ascending=False)` (lägre P/S = bättre).
   Klipp bort P/S <= 0 (orimligt) → median-fill.
4. **operating_leverage**: kärnsignalen.
   ```
   rev_growth = (revenue_ttm / revenue_prev) - 1
   opinc_growth = (operating_income_ttm / operating_income_prev) - 1
   op_leverage_ratio = opinc_growth / rev_growth   # > 1 = expanderande marginal
   ```
   Hantera: `revenue_prev<=0` eller negativ→NaN. Bara meningsfullt när rev_growth>0.
   `_percentile_score(op_leverage_ratio, ascending=True)`; ratio>1.5 ges extra +.
5. **revenue_accel** = senaste kvartalets YoY-tillväxt minus tillväxten 4 kvartal sedan
   (kräver kvartalsdata; om bara årsdata finns: 1-årig − 2-årig CAGR). Positiv accel =
   högre poäng. `_percentile_score(asc=True)`.
6. **clean_accruals**: Sloan accrual ratio (LÄGRE = bättre):
   ```
   sloan = (net_income_ttm - operating_cashflow_ttm) / ((total_assets + total_assets_prev)/2)
   ```
   `_percentile_score(sloan, ascending=False)`. Saknad data → neutral 50.

### Huvudfunktion
```python
def score_mews(df: pd.DataFrame) -> pd.DataFrame:
    """Returnerar df med kolumner:
       mews_fcf_yield, mews_small_size, mews_low_ps, mews_operating_leverage,
       mews_revenue_accel, mews_clean_accruals,
       mews_score (0-100), mews_flag (bool)."""
    out = df.copy()
    out["mews_fcf_yield"]          = _f_fcf_yield(df)
    out["mews_small_size"]         = _f_small_size(df)
    out["mews_low_ps"]             = _f_low_ps(df)
    out["mews_operating_leverage"] = _f_operating_leverage(df)
    out["mews_revenue_accel"]      = _f_revenue_accel(df)
    out["mews_clean_accruals"]     = _f_clean_accruals(df)
    comp = sum(out[f"mews_{k}"] * w for k, w in MEWS_WEIGHTS.items()
               for f in [None])  # se nedan, explicit summa
    out["mews_score"] = (
        out["mews_fcf_yield"]          * MEWS_WEIGHTS["fcf_yield"] +
        out["mews_small_size"]         * MEWS_WEIGHTS["small_size"] +
        out["mews_low_ps"]             * MEWS_WEIGHTS["low_ps"] +
        out["mews_operating_leverage"] * MEWS_WEIGHTS["operating_leverage"] +
        out["mews_revenue_accel"]      * MEWS_WEIGHTS["revenue_accel"] +
        out["mews_clean_accruals"]     * MEWS_WEIGHTS["clean_accruals"]
    ).clip(0, 100).round(1)
    out["mews_flag"] = out["mews_score"] >= MEWS_THRESHOLD
    return out
```

**Acceptanstest B** (`tests/test_mews.py`): syntetisk df med 30 bolag. Verifiera:
ett bolag med hög FCF-yield + litet + låg P/S + op_leverage>1.5 + positiv accel + låg Sloan
hamnar i topp; ett stort dyrt bolag med negativ FCF hamnar i botten. Inga NaN i `mews_score`.

---

## 3. Delsteg C — Koppla in i pipelinen

**Fil:** `stock-scanner-fix/core/daily_pipeline.py`. Efter att faktor-scoringen körts och
fundamenta finns i df, anropa `score_mews(df)` och lägg kolumnerna i
`scored_universe.parquet`. (Hitta var `score_universe`/parquet skrivs och lägg MEWS direkt
efter, så kolumnerna flödar via `db_loader`.)

---

## 4. Delsteg D — DB + API + frontend (marketscan)

### D1. Migration 028
**Fil:** `marketscan/supabase/migrations/028_mews.sql`
Lägg kolumner på `scan_results` (eller separat tabell om scan_results är låst — kolla
hur db_loader skriver; troligen ALTER TABLE):
```sql
ALTER TABLE scan_results
  ADD COLUMN IF NOT EXISTS mews_score FLOAT,
  ADD COLUMN IF NOT EXISTS mews_flag BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS mews_fcf_yield FLOAT,
  ADD COLUMN IF NOT EXISTS mews_small_size FLOAT,
  ADD COLUMN IF NOT EXISTS mews_low_ps FLOAT,
  ADD COLUMN IF NOT EXISTS mews_operating_leverage FLOAT,
  ADD COLUMN IF NOT EXISTS mews_revenue_accel FLOAT,
  ADD COLUMN IF NOT EXISTS mews_clean_accruals FLOAT;
CREATE INDEX IF NOT EXISTS idx_scan_mews ON scan_results (mews_score DESC) WHERE mews_flag;
```

### D2. `backend_worker/db_loader.py`
Lägg de nya `mews_*`-kolumnerna i kolumn-mappningen som laddas parquet→scan_results.

### D3. API
- Utöka screener-endpointen (`apps/api/routers/screener.py` el. motsv.) med filter
  `mews_flag=true` och sortering på `mews_score`.
- Lägg fälten i scan-row-schemat (`apps/web/types/scan.ts` + Pydantic-schema).

### D4. Frontend
- **Badge** på aktiekortet/översikten: visa "⚡ Mångdubblar-kandidat" när `mews_flag`.
- **Tooltip** (använd `InfoTooltip`) som förklarar MEWS evidensbaserat (FCF-yield,
  storlek, P/S, operativ hävstång, accruals).
- **Screener-filter:** chip "Mångdubblar-kandidater" → `?mews=true`.
- **Egen vy (valfri men rekommenderad):** `apps/web/app/(app)/mangdubblare/` som listar
  topp-MEWS med komponentnedbrytning (de 6 delfaktorerna som mini-staplar).

---

## 5. Filer som rörs

| Repo | Fil | Åtgärd |
|---|---|---|
| stock-scanner-fix | `core/data_fetcher.py` | Lägg saknade fundamenta-fält |
| stock-scanner-fix | `smallcap/mews.py` | NY — MEWS-scoring |
| stock-scanner-fix | `core/daily_pipeline.py` | Anropa `score_mews` |
| stock-scanner-fix | `tests/test_mews.py` | NY — acceptanstest |
| marketscan | `supabase/migrations/028_mews.sql` | NY |
| marketscan | `backend_worker/db_loader.py` | Mappa mews_*-kolumner |
| marketscan | `apps/api/routers/screener.py` | Filter + sortering |
| marketscan | `apps/web/types/scan.ts` | Fälttyper |
| marketscan | `apps/web/components/stock/…` | Badge + tooltip |
| marketscan | `apps/web/app/(app)/mangdubblare/` | NY vy (valfri) |

## 6. Definition of Done
- [ ] `score_mews` ger 0–100 + flagga, test grönt, inga NaN i `mews_score`.
- [ ] Pipelinen skriver mews_* till parquet → scan_results.
- [ ] Screener kan filtrera/sortera på MEWS.
- [ ] Badge + tooltip + (valfri) vy visar MEWS evidensbaserat.
- [ ] Likviditets-/skräpfilter aktivt (inga oinvesterbara mikrobolag i topp).
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
