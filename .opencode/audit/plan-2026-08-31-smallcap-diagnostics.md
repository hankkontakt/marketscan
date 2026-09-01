# Diagnostikrapport: Småbolag, Segmentering, ROE och Valuta (2026-08-31 / 2026-09-01)

## 1. Bakgrund & Syfte
Verifiering av rotorsaker till felaktigheter i småbolagsvyn:
1. Felaktig segmentklassificering (stora bolag som SAP.DE, Equinor, Investor AB, Hermes stämplade som `micro_cap`).
2. ROE-visning (median-neutraliserade residualer har visats som rå ROE när `roe_raw` saknats).
3. Valutahantering (.AX saknades i `_SUFFIX_CURRENCY`, GBp-pence orsakade fel/formateringsproblem).
4. Likviditetsflagga (`low_liquidity` saknade förklarande UX/tooltip).

## 2. Diagnostiska fynd (Live API & Databas)

### Tickersampling mot live `/api/scan`:
- `SAP.DE`: `market_cap=None`, `segment=micro_cap`, `roe=0.0335` (3.35 % residual), `roe_raw=None`, `currency=EUR`
- `EQNR.OL`: `market_cap=None`, `segment=micro_cap`, `roe=0.0687`, `roe_raw=None`, `currency=NOK`
- `INVE-B.ST`: `market_cap=None`, `segment=micro_cap`, `roe=0.0592`, `roe_raw=0.27254`, `currency=SEK`
- `RMS.PA`: `market_cap=None`, `segment=micro_cap`, `roe=0.0213`, `roe_raw=None`, `currency=EUR`
- `GMG.AX`: `market_cap=None`, `segment=micro_cap`, `roe=-0.0087`, `roe_raw=0.11516`, `currency=AUD`
- `DOL.TO`: `market_cap=None`, `segment=micro_cap`, `roe=0.8121`, `roe_raw=0.99466`, `currency=CAD`
- `EDP.LS`: `market_cap=None`, `segment=micro_cap`, `roe=-0.0015`, `roe_raw=None`, `currency=USD`

### Rotorsaker:
1. **Segment-fallback**: `backend_worker/db_loader.py:_derive_segment` returnerade `"micro_cap"` vid `market_cap is None or market_cap <= 0`. Bolag utan känt marknadsvärde dumpades därför i `micro_cap`.
2. **ROE-display**: `ResultTable.tsx`, `VerdictCard.tsx` och `StockView.tsx` använde `row.roe_raw ?? row.roe`. När `roe_raw` var `None` visades den neutraliserade residualen `roe` (t.ex. 3.35 % istället för SAP:s verkliga ~17 % ROE).
3. **Valuta**: `_SUFFIX_CURRENCY` saknade `.AX` (AUD), `.NZ` (NZD), `.SW` (CHF). `formatPrice` saknade säker felhantering mot `RangeError` samt specifik representation av brittiska pence (`GBp` -> t.ex. `2 864p`).
4. **DB Constraint**: `001_initial_schema.sql` definierade `CHECK (segment IN ('large_cap','mid_cap','small_cap','micro_cap'))`. Tillägget av `"unknown"` kräver uppdatering av CHECK-villkoret i databasen.

## 3. Beslut & Åtgärdsplan
- Ändra fallback vid okänt `market_cap` till `"unknown"`.
- Lägg till enhetsguard för `0 < market_cap < 1e6` (skala till miljoner).
- Skapa migration `079_fix_segment_classification.sql` för att uppdatera check-constraint och re-derive segment.
- Ändra ROE-visningskontrakt till att enbart visa `roe_raw` (`"—"` vid NULL).
- Uppdatera `roe_min`-filtret i `screener.py` till att filtrera på `roe_raw`.
- Utöka `_SUFFIX_CURRENCY` och uppdatera `formatPrice` med `try/catch` och GBp-pence.
- Förbättra UX för `low_liquidity` med förklarande tooltip.
