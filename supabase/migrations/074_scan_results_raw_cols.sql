-- MarketScan — Migration 074: scan_results raw-kolumner (ROND 10)
-- Bevara RÅ yfinance-värden (roe/pe_trailing/pe_forward/roa/revenue_growth/
-- earnings_growth) före median-neutralisering i stock-scanner. Neutraliserade
-- residualer behålls i de befintliga kolumnerna (intern scoring), medan *_raw
-- visar sanna värden i UI/API (MSFT ROE 32 % istället för 18 % residual).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS roe_raw             NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS roa_raw             NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS pe_trailing_raw     NUMERIC(12,4);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS pe_forward_raw      NUMERIC(12,4);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS revenue_growth_raw  NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS earnings_growth_raw NUMERIC(10,6);

COMMENT ON COLUMN scan_results.roe_raw IS
    'RÅ ROE (yfinance returnOnEquity) före region/sektor-median-neutralisering.
    Neutraliserad residual ligger i roe. ROND 10. Migration 074.
    Diagnostic marker: migration_074_scan_results_raw_cols.';
