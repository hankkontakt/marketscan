-- MarketScan — Migration 049: ISIN-kolumn i insider_trades
-- Korsnyckel (ISIN, datum, volym, typ) för FI↔Finnhub-rekonciliering.
-- FI:s insynsregister (marknadssok.fi.se) är sanningskälla; Nasdaq-insidertabellen
-- är avplattformad (verifierat 2026-08-28).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE insider_trades
    ADD COLUMN IF NOT EXISTS isin TEXT;

-- Felaktig upsert-nyckel (027): utan volym/isin tappas splittrade transaktioner
-- och Revised skriver aldrig över originalet. Nyckel: (COALESCE(isin, ticker),
-- name, trade_date, type) — aggregerad pre-insert (delad volym → summa).
ALTER TABLE insider_trades
    DROP CONSTRAINT IF EXISTS insider_trades_dedup_key;

CREATE UNIQUE INDEX IF NOT EXISTS insider_trades_reconcile_key
    ON insider_trades (COALESCE(isin, ticker), name, trade_date, type);

CREATE INDEX IF NOT EXISTS idx_insider_trades_isin_date
    ON insider_trades (isin, trade_date);

COMMENT ON TABLE insider_trades IS
    'Insider transactions (PDMR) — FI primary source, Finnhub cross-source.
    Migration 049 adds isin for reconciliation key (isin, trade_date, shares, type).';
