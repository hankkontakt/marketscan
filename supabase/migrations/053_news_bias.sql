-- MarketScan — Migration 053: Nyhets-bäring → betyg (T10)
-- news_bias = klassad nyhetssentiment (72h) i [-1,1]; news_bias_n = antal klassade events i fönstret.
-- Skrivs av backend_worker/news_bias.py (apply_news_bias). Kör manuellt i Supabase SQL Editor.

ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS news_bias NUMERIC(5,4);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS news_bias_n INT;

COMMENT ON COLUMN scan_results.news_bias IS 'Klassad nyhets-bäring 72h (bearing*confidence), [-1..1]';
COMMENT ON COLUMN scan_results.news_bias_n IS 'Antal klassade news_events i 72h-fönstret';