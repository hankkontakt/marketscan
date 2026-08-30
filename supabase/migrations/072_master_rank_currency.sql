-- MarketScan — Migration 072: master_rank currency (ROND 9)
-- Visar korrekt valuta för pris i UI ("kr" på USD-aktier var felaktigt).
-- currency härleds från analyst_estimates.currency (tickerns quote-valuta).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE master_rank ADD COLUMN IF NOT EXISTS currency TEXT;

COMMENT ON COLUMN master_rank.currency IS
    'Quote-valuta för tickern (USD/JPY/BRL/TWD/SEK...) — från analyst_estimates.
    ROND 9. Diagnostic marker: migration_072_master_rank_currency.';
