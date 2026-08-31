-- MarketScan — Migration 073: master_rank insider_source (ROND 9)
-- "real" (QMJ insiderkluster, nordiska) vs "proxy" (Piotroski-fallback, globala).
-- Proxy viktas 0.5× i master_rank.py. Kör manuellt i Supabase SQL Editor.

ALTER TABLE master_rank ADD COLUMN IF NOT EXISTS insider_source TEXT NOT NULL DEFAULT 'proxy';

COMMENT ON COLUMN master_rank.insider_source IS
    '"real" = QMJ-insiderkluster (endast nordiska), "proxy" = Piotroski-fallback
    (globala — viktad 0.5×). ROND 9. Diagnostic marker: migration_073_insider_source.';
