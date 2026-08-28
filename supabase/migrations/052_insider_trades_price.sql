-- MarketScan — Migration 052: price-kolumn i insider_trades
-- Rotorsak: migration 015 skapade insider_trades UTAN price-kolumn, men
-- backend_worker/insider_cluster.py (rader 51/65/221/232) och
-- backend_worker/fi_insider_bulk.py (rad 262) förväntar sig den:
--   SELECT ticker, name, role, shares, price, amount, trade_date ...
--   INSERT INTO insider_trades (ticker, name, trade_date, type, shares, price, amount, isin, role) ...
-- Resultat: FI-jobbet kraschar med 'column "price" does not exist'
-- (insider_cluster.py:57) och FI-bulk-priming skriver aldrig kluster.
-- Kör manuellt i Supabase SQL Editor. Idempotent — säker att köra om.

ALTER TABLE insider_trades
    ADD COLUMN IF NOT EXISTS price NUMERIC(14,2);

COMMENT ON COLUMN insider_trades.price IS
    'Kurs vid transaktion (kr/valuta). Krävs av insider_cluster.py och fi_insider_bulk.py.';
